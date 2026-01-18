"""
FX自動売買システム - APIクライアントモジュール

SBI証券FXトレード向けのAPIクライアントを提供します。
注意: SBI証券は現在、個人向けの公式FX APIを一般公開していません。
このモジュールは将来のAPI公開に備えた設計と、バックテスト用のモック実装を含みます。

実際の自動売買を行う場合は、以下の代替手段を検討してください：
1. SBI証券が将来公開する公式API
2. 他のFXブローカー（OANDA、外為オンライン等）のAPI
3. MetaTrader 4/5を介した接続
"""

import asyncio
import hashlib
import hmac
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiohttp
import requests

from config import CurrencyPair, TradingConfig, TradingMode, config

# ロガーの設定
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """注文方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """注文タイプ"""
    MARKET = "market"  # 成行注文
    LIMIT = "limit"    # 指値注文
    STOP = "stop"      # 逆指値注文
    STOP_LIMIT = "stop_limit"  # ストップリミット注文


class OrderStatus(Enum):
    """注文ステータス"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Tick:
    """ティックデータ（価格情報）"""
    currency_pair: CurrencyPair
    bid: Decimal  # 売値
    ask: Decimal  # 買値
    timestamp: datetime
    
    @property
    def spread(self) -> Decimal:
        """スプレッド（pips）"""
        pip_multiplier = Decimal("100") if "JPY" in self.currency_pair.value else Decimal("10000")
        return (self.ask - self.bid) * pip_multiplier
    
    @property
    def mid(self) -> Decimal:
        """中値"""
        return (self.bid + self.ask) / 2


@dataclass
class OHLCV:
    """ローソク足データ"""
    currency_pair: CurrencyPair
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": self.volume
        }


@dataclass
class Order:
    """注文データ"""
    order_id: str
    currency_pair: CurrencyPair
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[Decimal] = None  # 指値の場合
    stop_price: Optional[Decimal] = None  # 逆指値の場合
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "currency_pair": self.currency_pair.value,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": float(self.price) if self.price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": float(self.filled_price) if self.filled_price else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Position:
    """ポジションデータ"""
    position_id: str
    currency_pair: CurrencyPair
    side: OrderSide
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    opened_at: datetime = field(default_factory=datetime.now)
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """未実現損益（pips）"""
        pip_multiplier = Decimal("100") if "JPY" in self.currency_pair.value else Decimal("10000")
        if self.side == OrderSide.BUY:
            return (self.current_price - self.entry_price) * pip_multiplier
        else:
            return (self.entry_price - self.current_price) * pip_multiplier
    
    @property
    def unrealized_pnl_jpy(self) -> Decimal:
        """未実現損益（円）"""
        if self.side == OrderSide.BUY:
            diff = self.current_price - self.entry_price
        else:
            diff = self.entry_price - self.current_price
        return diff * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "currency_pair": self.currency_pair.value,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": float(self.entry_price),
            "current_price": float(self.current_price),
            "unrealized_pnl_pips": float(self.unrealized_pnl),
            "unrealized_pnl_jpy": float(self.unrealized_pnl_jpy),
            "opened_at": self.opened_at.isoformat(),
        }


@dataclass
class AccountInfo:
    """口座情報"""
    account_id: str
    balance: Decimal  # 口座残高
    equity: Decimal   # 有効証拠金
    margin_used: Decimal  # 使用証拠金
    margin_available: Decimal  # 余剰証拠金
    unrealized_pnl: Decimal  # 未実現損益
    margin_level: Optional[Decimal] = None  # 証拠金維持率（%）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "balance": float(self.balance),
            "equity": float(self.equity),
            "margin_used": float(self.margin_used),
            "margin_available": float(self.margin_available),
            "unrealized_pnl": float(self.unrealized_pnl),
            "margin_level": float(self.margin_level) if self.margin_level else None,
        }


class FXBrokerClient(ABC):
    """FXブローカーAPIクライアントの抽象基底クラス"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """APIに接続"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """API接続を切断"""
        pass
    
    @abstractmethod
    async def get_tick(self, currency_pair: CurrencyPair) -> Tick:
        """現在のティックデータを取得"""
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self,
        currency_pair: CurrencyPair,
        timeframe: str,
        count: int = 100
    ) -> List[OHLCV]:
        """ローソク足データを取得"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> Order:
        """注文を発注"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """注文をキャンセル"""
        pass
    
    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """未約定注文一覧を取得"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """保有ポジション一覧を取得"""
        pass
    
    @abstractmethod
    async def close_position(self, position_id: str) -> bool:
        """ポジションを決済"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """口座情報を取得"""
        pass


class SBIFXClient(FXBrokerClient):
    """
    SBI証券FXトレード APIクライアント
    
    注意: これはSBI証券が将来公式APIを公開した場合に備えた
    インターフェース設計です。現時点では実際のAPI呼び出しは
    行いません。
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """SBI FX APIに接続（認証）"""
        logger.info("SBI FX APIへの接続を開始...")
        
        if self.config.api.mode == TradingMode.DEMO:
            logger.warning("デモモードで実行中 - 実際のAPI呼び出しは行いません")
            self._connected = True
            return True
        
        # 本番モードの場合の認証フロー（将来の実装用）
        # 現時点ではSBI証券の公式APIが公開されていないため、
        # 実装は保留としています
        raise NotImplementedError(
            "SBI証券の公式FX APIは現在一般公開されていません。"
            "デモモードで実行するか、代替のブローカーAPIを使用してください。"
        )
    
    async def disconnect(self) -> None:
        """API接続を切断"""
        if self._session:
            await self._session.close()
        self._connected = False
        logger.info("SBI FX APIから切断しました")
    
    async def get_tick(self, currency_pair: CurrencyPair) -> Tick:
        """現在のティックデータを取得"""
        self._ensure_connected()
        
        # デモモードではモックデータを返す
        if self.config.api.mode == TradingMode.DEMO:
            return self._generate_mock_tick(currency_pair)
        
        raise NotImplementedError("本番API未実装")
    
    async def get_ohlcv(
        self,
        currency_pair: CurrencyPair,
        timeframe: str,
        count: int = 100
    ) -> List[OHLCV]:
        """ローソク足データを取得"""
        self._ensure_connected()
        
        if self.config.api.mode == TradingMode.DEMO:
            return self._generate_mock_ohlcv(currency_pair, count)
        
        raise NotImplementedError("本番API未実装")
    
    async def place_order(self, order: Order) -> Order:
        """注文を発注"""
        self._ensure_connected()
        logger.info(f"注文発注: {order.to_dict()}")
        
        if self.config.api.mode == TradingMode.DEMO:
            # デモモードでは即座に約定したとみなす
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            tick = await self.get_tick(order.currency_pair)
            order.filled_price = tick.ask if order.side == OrderSide.BUY else tick.bid
            order.updated_at = datetime.now()
            logger.info(f"注文約定（デモ）: {order.order_id} @ {order.filled_price}")
            return order
        
        raise NotImplementedError("本番API未実装")
    
    async def cancel_order(self, order_id: str) -> bool:
        """注文をキャンセル"""
        self._ensure_connected()
        logger.info(f"注文キャンセル: {order_id}")
        
        if self.config.api.mode == TradingMode.DEMO:
            return True
        
        raise NotImplementedError("本番API未実装")
    
    async def get_open_orders(self) -> List[Order]:
        """未約定注文一覧を取得"""
        self._ensure_connected()
        
        if self.config.api.mode == TradingMode.DEMO:
            return []  # デモでは未約定注文なし
        
        raise NotImplementedError("本番API未実装")
    
    async def get_positions(self) -> List[Position]:
        """保有ポジション一覧を取得"""
        self._ensure_connected()
        
        if self.config.api.mode == TradingMode.DEMO:
            return []  # デモではポジションなし
        
        raise NotImplementedError("本番API未実装")
    
    async def close_position(self, position_id: str) -> bool:
        """ポジションを決済"""
        self._ensure_connected()
        logger.info(f"ポジション決済: {position_id}")
        
        if self.config.api.mode == TradingMode.DEMO:
            return True
        
        raise NotImplementedError("本番API未実装")
    
    async def get_account_info(self) -> AccountInfo:
        """口座情報を取得"""
        self._ensure_connected()
        
        if self.config.api.mode == TradingMode.DEMO:
            return AccountInfo(
                account_id="DEMO-001",
                balance=Decimal("1000000"),  # 100万円
                equity=Decimal("1000000"),
                margin_used=Decimal("0"),
                margin_available=Decimal("1000000"),
                unrealized_pnl=Decimal("0"),
                margin_level=None
            )
        
        raise NotImplementedError("本番API未実装")
    
    def _ensure_connected(self) -> None:
        """接続状態を確認"""
        if not self._connected:
            raise ConnectionError("APIに接続されていません。connect()を先に呼び出してください。")
    
    def _generate_mock_tick(self, currency_pair: CurrencyPair) -> Tick:
        """モックのティックデータを生成"""
        # 基準価格（実際の市場価格に近い値）
        base_prices = {
            CurrencyPair.USDJPY: Decimal("150.000"),
            CurrencyPair.EURJPY: Decimal("163.000"),
            CurrencyPair.GBPJPY: Decimal("188.000"),
            CurrencyPair.AUDJPY: Decimal("98.000"),
            CurrencyPair.EURUSD: Decimal("1.08500"),
            CurrencyPair.GBPUSD: Decimal("1.25500"),
            CurrencyPair.AUDUSD: Decimal("0.65500"),
        }
        
        base_price = base_prices.get(currency_pair, Decimal("100.000"))
        
        # ランダムな変動を追加
        variation = Decimal(str(random.uniform(-0.05, 0.05)))
        mid_price = base_price + variation
        
        # スプレッドを設定（クロス円は0.3銭〜、ドルストレートは0.3pips〜）
        if "JPY" in currency_pair.value:
            spread = Decimal("0.003")  # 0.3銭
        else:
            spread = Decimal("0.00003")  # 0.3pips
        
        return Tick(
            currency_pair=currency_pair,
            bid=mid_price - spread / 2,
            ask=mid_price + spread / 2,
            timestamp=datetime.now()
        )
    
    def _generate_mock_ohlcv(
        self,
        currency_pair: CurrencyPair,
        count: int
    ) -> List[OHLCV]:
        """モックのローソク足データを生成"""
        # 基準価格
        base_prices = {
            CurrencyPair.USDJPY: 150.0,
            CurrencyPair.EURJPY: 163.0,
            CurrencyPair.GBPJPY: 188.0,
            CurrencyPair.AUDJPY: 98.0,
            CurrencyPair.EURUSD: 1.085,
            CurrencyPair.GBPUSD: 1.255,
            CurrencyPair.AUDUSD: 0.655,
        }
        
        base_price = base_prices.get(currency_pair, 100.0)
        ohlcv_list = []
        
        current_price = base_price
        now = datetime.now()
        
        for i in range(count):
            timestamp = now - timedelta(hours=count - i)
            
            # ランダムウォークで価格を生成
            change = random.gauss(0, 0.001) * base_price
            current_price += change
            
            # OHLCV生成
            open_price = current_price
            high_price = current_price + abs(random.gauss(0, 0.0005)) * base_price
            low_price = current_price - abs(random.gauss(0, 0.0005)) * base_price
            close_price = current_price + random.gauss(0, 0.0003) * base_price
            
            # 高値・安値の整合性を保証
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            ohlcv = OHLCV(
                currency_pair=currency_pair,
                timestamp=timestamp,
                open=Decimal(str(round(open_price, 5))),
                high=Decimal(str(round(high_price, 5))),
                low=Decimal(str(round(low_price, 5))),
                close=Decimal(str(round(close_price, 5))),
                volume=random.randint(1000, 10000)
            )
            ohlcv_list.append(ohlcv)
            
            current_price = close_price
        
        return ohlcv_list


class MockBrokerClient(FXBrokerClient):
    """
    モックブローカークライアント（バックテスト・開発用）
    
    実際のAPIを呼び出さず、ローカルでシミュレーションを行います。
    """
    
    def __init__(self, initial_balance: Decimal = Decimal("1000000")):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        self.position_counter = 0
        self._connected = False
        self._current_prices: Dict[CurrencyPair, Tick] = {}
    
    async def connect(self) -> bool:
        self._connected = True
        logger.info("モックブローカーに接続しました")
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
        logger.info("モックブローカーから切断しました")
    
    def update_price(self, tick: Tick) -> None:
        """価格を更新（バックテスト用）"""
        self._current_prices[tick.currency_pair] = tick
        
        # ポジションの現在価格も更新
        for position in self.positions.values():
            if position.currency_pair == tick.currency_pair:
                if position.side == OrderSide.BUY:
                    position.current_price = tick.bid
                else:
                    position.current_price = tick.ask
    
    async def get_tick(self, currency_pair: CurrencyPair) -> Tick:
        if currency_pair in self._current_prices:
            return self._current_prices[currency_pair]
        
        # デフォルト価格を返す
        return Tick(
            currency_pair=currency_pair,
            bid=Decimal("150.000"),
            ask=Decimal("150.003"),
            timestamp=datetime.now()
        )
    
    async def get_ohlcv(
        self,
        currency_pair: CurrencyPair,
        timeframe: str,
        count: int = 100
    ) -> List[OHLCV]:
        # バックテストエンジンから直接データを注入する想定
        return []
    
    async def place_order(self, order: Order) -> Order:
        self.order_counter += 1
        order.order_id = f"ORD-{self.order_counter:06d}"
        
        if order.order_type == OrderType.MARKET:
            # 成行注文は即座に約定
            tick = await self.get_tick(order.currency_pair)
            fill_price = tick.ask if order.side == OrderSide.BUY else tick.bid
            
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = fill_price
            order.updated_at = datetime.now()
            
            # ポジションを作成
            self.position_counter += 1
            position = Position(
                position_id=f"POS-{self.position_counter:06d}",
                currency_pair=order.currency_pair,
                side=order.side,
                quantity=order.quantity,
                entry_price=fill_price,
                current_price=fill_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                opened_at=datetime.now()
            )
            self.positions[position.position_id] = position
            logger.info(f"ポジション作成: {position.to_dict()}")
        else:
            # 指値・逆指値注文は保留
            order.status = OrderStatus.OPEN
            self.orders[order.order_id] = order
        
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            del self.orders[order_id]
            return True
        return False
    
    async def get_open_orders(self) -> List[Order]:
        return [o for o in self.orders.values() if o.status == OrderStatus.OPEN]
    
    async def get_positions(self) -> List[Position]:
        return list(self.positions.values())
    
    async def close_position(self, position_id: str) -> bool:
        if position_id not in self.positions:
            return False
        
        position = self.positions[position_id]
        pnl = position.unrealized_pnl_jpy
        self.balance += pnl
        
        logger.info(f"ポジション決済: {position_id}, 損益: {pnl:,.0f}円")
        del self.positions[position_id]
        return True
    
    async def get_account_info(self) -> AccountInfo:
        # 未実現損益を計算
        unrealized_pnl = sum(
            p.unrealized_pnl_jpy for p in self.positions.values()
        )
        
        # 使用証拠金を計算（レバレッジ25倍想定）
        margin_used = sum(
            p.entry_price * p.quantity / 25 for p in self.positions.values()
        )
        
        equity = self.balance + unrealized_pnl
        margin_available = equity - margin_used
        
        margin_level = None
        if margin_used > 0:
            margin_level = (equity / margin_used) * 100
        
        return AccountInfo(
            account_id="MOCK-001",
            balance=self.balance,
            equity=equity,
            margin_used=Decimal(str(margin_used)),
            margin_available=Decimal(str(margin_available)),
            unrealized_pnl=Decimal(str(unrealized_pnl)),
            margin_level=Decimal(str(margin_level)) if margin_level else None
        )


def create_broker_client(config: TradingConfig) -> FXBrokerClient:
    """設定に応じたブローカークライアントを作成"""
    from config import Broker
    
    if config.api.mode == TradingMode.BACKTEST:
        return MockBrokerClient()
    
    if config.api.broker == Broker.SAXO:
        # Saxo Bank クライアントを使用
        from saxo_client import SaxoBankClient, SaxoConfig, SaxoEnvironment
        
        saxo_config = SaxoConfig(
            app_key=config.api.saxo_app_key,
            app_secret=config.api.saxo_app_secret,
            redirect_uri=config.api.saxo_redirect_uri,
            environment=(
                SaxoEnvironment.LIVE if config.api.saxo_environment == "live"
                else SaxoEnvironment.SIMULATION
            )
        )
        
        demo_mode = config.api.mode == TradingMode.DEMO
        return SaxoBankClient(saxo_config, demo_mode=demo_mode)
    
    elif config.api.broker == Broker.SBI:
        return SBIFXClient(config)
    
    else:
        # デフォルトはモック
        return MockBrokerClient()


if __name__ == "__main__":
    # テスト実行
    import asyncio
    
    async def test_client():
        client = create_broker_client(config)
        await client.connect()
        
        # ティックデータ取得テスト
        tick = await client.get_tick(CurrencyPair.USDJPY)
        print(f"USD/JPY: Bid={tick.bid}, Ask={tick.ask}, Spread={tick.spread:.1f}pips")
        
        # 口座情報取得テスト
        account = await client.get_account_info()
        print(f"口座残高: {account.balance:,.0f}円")
        
        await client.disconnect()
    
    asyncio.run(test_client())
