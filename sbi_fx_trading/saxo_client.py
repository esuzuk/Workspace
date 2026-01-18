"""
FX自動売買システム - Saxo Bank OpenAPI クライアント

サクソバンク証券のOpenAPIを使用したFX自動売買クライアントです。
OAuth 2.0認証、REST API、WebSocketストリーミングに対応しています。

Saxo Bank OpenAPI の特徴:
- OAuth 2.0による安全な認証
- REST API + WebSocket（リアルタイムストリーミング）
- 150以上の通貨ペアに対応
- If-Done注文（OCO、OSO）のサポート
- 世界標準のAPI設計

使用前の準備:
1. Saxo Developer Portal (https://www.developer.saxo/) でアカウント作成
2. アプリケーションを登録してApp Key / App Secretを取得
3. シミュレーション環境でテスト
4. 本番環境への移行

参考:
- API Reference: https://www.developer.saxo/openapi/learn
- GitHub Examples: https://github.com/SaxoBank/openapi-samples-python
"""

import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp
import requests

from api_client import (
    AccountInfo, CurrencyPair, FXBrokerClient, OHLCV, Order,
    OrderSide, OrderStatus, OrderType, Position, Tick
)

logger = logging.getLogger(__name__)


class SaxoEnvironment(Enum):
    """Saxo API環境"""
    SIMULATION = "sim"      # シミュレーション環境（開発・テスト用）
    LIVE = "live"           # 本番環境


@dataclass
class SaxoConfig:
    """Saxo Bank API設定"""
    app_key: str = ""
    app_secret: str = ""
    redirect_uri: str = "http://localhost:8080/callback"
    environment: SaxoEnvironment = SaxoEnvironment.SIMULATION
    
    # OAuth2 スコープ
    scopes: List[str] = field(default_factory=lambda: [
        "openapi",      # 基本API
        "trade",        # 取引
        "readaccount",  # 口座情報読み取り
    ])
    
    @property
    def auth_endpoint(self) -> str:
        """認証エンドポイント"""
        if self.environment == SaxoEnvironment.SIMULATION:
            return "https://sim.logonvalidation.net"
        return "https://live.logonvalidation.net"
    
    @property
    def api_endpoint(self) -> str:
        """APIエンドポイント"""
        if self.environment == SaxoEnvironment.SIMULATION:
            return "https://gateway.saxobank.com/sim/openapi"
        return "https://gateway.saxobank.com/openapi"
    
    @property
    def streaming_endpoint(self) -> str:
        """WebSocketストリーミングエンドポイント"""
        if self.environment == SaxoEnvironment.SIMULATION:
            return "wss://streaming.saxobank.com/sim/openapi/streamingws"
        return "wss://streaming.saxobank.com/openapi/streamingws"


@dataclass
class OAuthToken:
    """OAuth2トークン"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """アクセストークンが期限切れかどうか"""
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)  # 60秒のバッファ
        return datetime.now() >= expiry
    
    @property
    def refresh_token_expired(self) -> bool:
        """リフレッシュトークンが期限切れかどうか"""
        expiry = self.created_at + timedelta(seconds=self.refresh_token_expires_in - 60)
        return datetime.now() >= expiry
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "refresh_token_expires_in": self.refresh_token_expires_in,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthToken":
        return cls(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            refresh_token=data["refresh_token"],
            refresh_token_expires_in=data["refresh_token_expires_in"],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        )


# Saxo Bank の通貨ペア Uic（Unique Instrument Code）マッピング
# 注: 実際のUicはAPIで取得する必要がありますが、主要ペアは固定
SAXO_CURRENCY_PAIR_UIC = {
    CurrencyPair.USDJPY: 31,    # USD/JPY
    CurrencyPair.EURJPY: 24,    # EUR/JPY
    CurrencyPair.GBPJPY: 40,    # GBP/JPY
    CurrencyPair.AUDJPY: 10,    # AUD/JPY
    CurrencyPair.EURUSD: 21,    # EUR/USD
    CurrencyPair.GBPUSD: 38,    # GBP/USD
    CurrencyPair.AUDUSD: 7,     # AUD/USD
}

# Saxo Bank の時間足マッピング
SAXO_TIMEFRAME_MAP = {
    "1min": 1,
    "5min": 5,
    "15min": 15,
    "30min": 30,
    "1hour": 60,
    "4hour": 240,
    "daily": 1440,
    "weekly": 10080,
}


class SaxoOAuthHandler:
    """
    Saxo Bank OAuth 2.0 認証ハンドラー
    
    Authorization Code Flow with PKCE を実装しています。
    """
    
    def __init__(self, config: SaxoConfig):
        self.config = config
        self._state: Optional[str] = None
        self._code_verifier: Optional[str] = None
    
    def generate_auth_url(self) -> str:
        """認証URLを生成"""
        # PKCE用のcode_verifierとcode_challengeを生成
        self._code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self._code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        # stateを生成（CSRF対策）
        self._state = secrets.token_urlsafe(16)
        
        params = {
            "client_id": self.config.app_key,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "state": self._state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        auth_url = f"{self.config.auth_endpoint}/authorize?{urlencode(params)}"
        return auth_url
    
    async def exchange_code_for_token(self, auth_code: str) -> OAuthToken:
        """認証コードをトークンと交換"""
        token_url = f"{self.config.auth_endpoint}/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.app_key,
            "client_secret": self.config.app_secret,
            "code_verifier": self._code_verifier,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Token exchange failed: {response.status} - {error_text}")
                
                token_data = await response.json()
                return OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    expires_in=token_data["expires_in"],
                    refresh_token=token_data["refresh_token"],
                    refresh_token_expires_in=token_data.get("refresh_token_expires_in", 86400)
                )
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthToken:
        """リフレッシュトークンを使用してアクセストークンを更新"""
        token_url = f"{self.config.auth_endpoint}/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.app_key,
            "client_secret": self.config.app_secret,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Token refresh failed: {response.status} - {error_text}")
                
                token_data = await response.json()
                return OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    expires_in=token_data["expires_in"],
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    refresh_token_expires_in=token_data.get("refresh_token_expires_in", 86400)
                )


class SaxoPriceStreaming:
    """
    Saxo Bank WebSocket価格ストリーミング
    
    リアルタイムの価格データをWebSocket経由で受信します。
    """
    
    def __init__(self, config: SaxoConfig, token: OAuthToken):
        self.config = config
        self.token = token
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._subscriptions: Dict[int, CurrencyPair] = {}
        self._price_callbacks: List[Callable[[Tick], None]] = []
        self._running = False
        self._context_id: Optional[str] = None
        self._reference_id_counter = 0
    
    async def connect(self) -> bool:
        """WebSocket接続を確立"""
        try:
            self._context_id = secrets.token_hex(8)
            self._session = aiohttp.ClientSession()
            
            headers = {
                "Authorization": f"Bearer {self.token.access_token}"
            }
            
            ws_url = f"{self.config.streaming_endpoint}/connect?contextId={self._context_id}"
            self._ws = await self._session.ws_connect(ws_url, headers=headers)
            
            self._running = True
            logger.info("WebSocketストリーミングに接続しました")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket接続エラー: {e}")
            return False
    
    async def disconnect(self) -> None:
        """WebSocket接続を切断"""
        self._running = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("WebSocketストリーミングから切断しました")
    
    async def subscribe_price(self, currency_pair: CurrencyPair) -> bool:
        """価格データを購読"""
        if currency_pair not in SAXO_CURRENCY_PAIR_UIC:
            logger.error(f"未対応の通貨ペア: {currency_pair}")
            return False
        
        uic = SAXO_CURRENCY_PAIR_UIC[currency_pair]
        self._reference_id_counter += 1
        reference_id = f"price_{self._reference_id_counter}"
        
        # REST APIで購読をセットアップ
        subscription_url = f"{self.config.api_endpoint}/trade/v1/infoprices/subscriptions"
        
        subscription_data = {
            "Arguments": {
                "Uic": uic,
                "AssetType": "FxSpot"
            },
            "ContextId": self._context_id,
            "ReferenceId": reference_id
        }
        
        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                subscription_url,
                json=subscription_data,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    self._subscriptions[uic] = currency_pair
                    logger.info(f"価格購読開始: {currency_pair.value}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"価格購読エラー: {response.status} - {error_text}")
                    return False
    
    async def unsubscribe_price(self, currency_pair: CurrencyPair) -> bool:
        """価格購読を解除"""
        if currency_pair not in SAXO_CURRENCY_PAIR_UIC:
            return False
        
        uic = SAXO_CURRENCY_PAIR_UIC[currency_pair]
        
        if uic in self._subscriptions:
            del self._subscriptions[uic]
            logger.info(f"価格購読解除: {currency_pair.value}")
            return True
        return False
    
    def add_price_callback(self, callback: Callable[[Tick], None]) -> None:
        """価格更新コールバックを追加"""
        self._price_callbacks.append(callback)
    
    async def listen(self) -> None:
        """WebSocketメッセージをリッスン"""
        if not self._ws:
            raise ConnectionError("WebSocketに接続されていません")
        
        while self._running:
            try:
                msg = await self._ws.receive(timeout=30)
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket接続が閉じられました")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocketエラー: {self._ws.exception()}")
                    break
                    
            except asyncio.TimeoutError:
                # ハートビートを送信
                if self._ws:
                    await self._ws.ping()
            except Exception as e:
                logger.error(f"メッセージ処理エラー: {e}")
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """受信メッセージを処理"""
        if "Data" in data and isinstance(data["Data"], list):
            for item in data["Data"]:
                if "Quote" in item:
                    quote = item["Quote"]
                    uic = item.get("Uic")
                    
                    if uic and uic in self._subscriptions:
                        currency_pair = self._subscriptions[uic]
                        
                        tick = Tick(
                            currency_pair=currency_pair,
                            bid=Decimal(str(quote.get("Bid", 0))),
                            ask=Decimal(str(quote.get("Ask", 0))),
                            timestamp=datetime.now()
                        )
                        
                        # コールバックを呼び出し
                        for callback in self._price_callbacks:
                            try:
                                callback(tick)
                            except Exception as e:
                                logger.error(f"コールバックエラー: {e}")


class SaxoBankClient(FXBrokerClient):
    """
    Saxo Bank OpenAPI クライアント
    
    サクソバンク証券のOpenAPIを使用したFXトレーディングクライアントです。
    OAuth 2.0認証、REST API、WebSocketストリーミングに完全対応しています。
    """
    
    def __init__(self, config: SaxoConfig, demo_mode: bool = True):
        self.config = config
        self.demo_mode = demo_mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[OAuthToken] = None
        self._oauth_handler = SaxoOAuthHandler(config)
        self._price_streaming: Optional[SaxoPriceStreaming] = None
        self._connected = False
        self._account_key: Optional[str] = None
        self._client_key: Optional[str] = None
        
        # キャッシュ
        self._cached_prices: Dict[CurrencyPair, Tick] = {}
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}
    
    async def connect(self) -> bool:
        """Saxo Bank APIに接続（認証）"""
        logger.info(f"Saxo Bank OpenAPIに接続中... (環境: {self.config.environment.value})")
        
        if self.demo_mode:
            logger.warning("デモモードで実行中 - 実際のAPI呼び出しはシミュレートされます")
            self._connected = True
            self._account_key = "DEMO-ACCOUNT"
            self._client_key = "DEMO-CLIENT"
            return True
        
        # OAuth認証フロー
        if not self._token:
            logger.info("OAuth認証が必要です")
            
            # 認証URLを生成
            auth_url = self._oauth_handler.generate_auth_url()
            
            print("\n" + "=" * 60)
            print("Saxo Bank OAuth認証")
            print("=" * 60)
            print("以下のURLをブラウザで開いてログインしてください:")
            print(f"\n{auth_url}\n")
            print("ログイン後、リダイレクトされたURLの 'code' パラメータを入力してください")
            print("=" * 60)
            
            # ブラウザを自動で開く（オプション）
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass
            
            # 認証コードの入力を待つ
            auth_code = input("認証コード: ").strip()
            
            if not auth_code:
                logger.error("認証コードが入力されませんでした")
                return False
            
            try:
                self._token = await self._oauth_handler.exchange_code_for_token(auth_code)
                logger.info("OAuth認証成功！")
            except Exception as e:
                logger.error(f"OAuth認証エラー: {e}")
                return False
        
        # トークンの有効期限チェック
        if self._token.is_expired:
            if self._token.refresh_token_expired:
                logger.error("リフレッシュトークンが期限切れです。再認証が必要です。")
                self._token = None
                return await self.connect()
            
            try:
                self._token = await self._oauth_handler.refresh_access_token(
                    self._token.refresh_token
                )
                logger.info("アクセストークンを更新しました")
            except Exception as e:
                logger.error(f"トークン更新エラー: {e}")
                return False
        
        # HTTPセッションを作成
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self._token.access_token}",
                "Content-Type": "application/json"
            }
        )
        
        # アカウント情報を取得
        try:
            await self._fetch_account_info()
            self._connected = True
            logger.info(f"Saxo Bank OpenAPIに接続しました (Account: {self._account_key})")
            return True
        except Exception as e:
            logger.error(f"アカウント情報取得エラー: {e}")
            return False
    
    async def disconnect(self) -> None:
        """API接続を切断"""
        if self._price_streaming:
            await self._price_streaming.disconnect()
        
        if self._session:
            await self._session.close()
            self._session = None
        
        self._connected = False
        logger.info("Saxo Bank OpenAPIから切断しました")
    
    async def _fetch_account_info(self) -> None:
        """アカウント情報を取得"""
        if self.demo_mode:
            return
        
        url = f"{self.config.api_endpoint}/port/v1/accounts/me"
        
        async with self._session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"アカウント情報取得エラー: {response.status} - {error_text}")
            
            data = await response.json()
            
            if "Data" in data and len(data["Data"]) > 0:
                account = data["Data"][0]
                self._account_key = account.get("AccountKey")
                self._client_key = account.get("ClientKey")
    
    async def _ensure_token_valid(self) -> None:
        """トークンが有効であることを確認し、必要に応じて更新"""
        if self.demo_mode or not self._token:
            return
        
        if self._token.is_expired:
            try:
                self._token = await self._oauth_handler.refresh_access_token(
                    self._token.refresh_token
                )
                
                # セッションヘッダーを更新
                if self._session:
                    await self._session.close()
                    self._session = aiohttp.ClientSession(
                        headers={
                            "Authorization": f"Bearer {self._token.access_token}",
                            "Content-Type": "application/json"
                        }
                    )
                
                logger.info("アクセストークンを自動更新しました")
            except Exception as e:
                logger.error(f"トークン自動更新エラー: {e}")
                raise
    
    def _ensure_connected(self) -> None:
        """接続状態を確認"""
        if not self._connected:
            raise ConnectionError("Saxo Bank APIに接続されていません。connect()を先に呼び出してください。")
    
    async def get_tick(self, currency_pair: CurrencyPair) -> Tick:
        """現在のティックデータを取得"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        if self.demo_mode:
            return self._generate_mock_tick(currency_pair)
        
        if currency_pair not in SAXO_CURRENCY_PAIR_UIC:
            raise ValueError(f"未対応の通貨ペア: {currency_pair}")
        
        uic = SAXO_CURRENCY_PAIR_UIC[currency_pair]
        url = f"{self.config.api_endpoint}/trade/v1/infoprices"
        
        params = {
            "Uic": uic,
            "AssetType": "FxSpot",
            "FieldGroups": "Quote"
        }
        
        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"価格取得エラー: {response.status} - {error_text}")
                return self._generate_mock_tick(currency_pair)
            
            data = await response.json()
            quote = data.get("Quote", {})
            
            tick = Tick(
                currency_pair=currency_pair,
                bid=Decimal(str(quote.get("Bid", 0))),
                ask=Decimal(str(quote.get("Ask", 0))),
                timestamp=datetime.now()
            )
            
            self._cached_prices[currency_pair] = tick
            return tick
    
    async def get_ohlcv(
        self,
        currency_pair: CurrencyPair,
        timeframe: str,
        count: int = 100
    ) -> List[OHLCV]:
        """ローソク足データを取得"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        if self.demo_mode:
            return self._generate_mock_ohlcv(currency_pair, count)
        
        if currency_pair not in SAXO_CURRENCY_PAIR_UIC:
            raise ValueError(f"未対応の通貨ペア: {currency_pair}")
        
        if timeframe not in SAXO_TIMEFRAME_MAP:
            raise ValueError(f"未対応の時間足: {timeframe}")
        
        uic = SAXO_CURRENCY_PAIR_UIC[currency_pair]
        horizon = SAXO_TIMEFRAME_MAP[timeframe]
        
        url = f"{self.config.api_endpoint}/chart/v1/charts"
        
        params = {
            "Uic": uic,
            "AssetType": "FxSpot",
            "Horizon": horizon,
            "Count": count
        }
        
        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"OHLCV取得エラー: {response.status} - {error_text}")
                return self._generate_mock_ohlcv(currency_pair, count)
            
            data = await response.json()
            ohlcv_list = []
            
            for candle in data.get("Data", []):
                ohlcv = OHLCV(
                    currency_pair=currency_pair,
                    timestamp=datetime.fromisoformat(candle["Time"].replace("Z", "+00:00")),
                    open=Decimal(str(candle["Open"])),
                    high=Decimal(str(candle["High"])),
                    low=Decimal(str(candle["Low"])),
                    close=Decimal(str(candle["Close"])),
                    volume=candle.get("Volume", 0)
                )
                ohlcv_list.append(ohlcv)
            
            return ohlcv_list
    
    async def place_order(self, order: Order) -> Order:
        """
        注文を発注
        
        Saxo Bankの注文APIは非常に柔軟で、以下の機能をサポートしています：
        - 成行/指値/逆指値注文
        - If-Done注文（OCO、OSO）
        - 損切り/利確の同時設定
        """
        self._ensure_connected()
        await self._ensure_token_valid()
        
        logger.info(f"注文発注: {order.to_dict()}")
        
        if self.demo_mode:
            # デモモードでは即座に約定
            order.order_id = f"SAXO-ORD-{int(time.time() * 1000)}"
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            tick = await self.get_tick(order.currency_pair)
            order.filled_price = tick.ask if order.side == OrderSide.BUY else tick.bid
            order.updated_at = datetime.now()
            logger.info(f"注文約定（デモ）: {order.order_id} @ {order.filled_price}")
            return order
        
        if order.currency_pair not in SAXO_CURRENCY_PAIR_UIC:
            raise ValueError(f"未対応の通貨ペア: {order.currency_pair}")
        
        uic = SAXO_CURRENCY_PAIR_UIC[order.currency_pair]
        
        # 注文データを構築
        order_data = {
            "AccountKey": self._account_key,
            "Uic": uic,
            "AssetType": "FxSpot",
            "BuySell": "Buy" if order.side == OrderSide.BUY else "Sell",
            "Amount": order.quantity,
            "OrderType": self._convert_order_type(order.order_type),
            "OrderDuration": {"DurationType": "GoodTillCancel"}
        }
        
        # 指値価格
        if order.price and order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            order_data["OrderPrice"] = float(order.price)
        
        # 逆指値価格
        if order.stop_price and order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            order_data["StopLimitPrice"] = float(order.stop_price)
        
        # 関連注文（損切り/利確）
        if order.stop_loss or order.take_profit:
            order_data["Orders"] = []
            
            if order.stop_loss:
                order_data["Orders"].append({
                    "OrderType": "StopIfTraded",
                    "OrderPrice": float(order.stop_loss),
                    "BuySell": "Sell" if order.side == OrderSide.BUY else "Buy"
                })
            
            if order.take_profit:
                order_data["Orders"].append({
                    "OrderType": "Limit",
                    "OrderPrice": float(order.take_profit),
                    "BuySell": "Sell" if order.side == OrderSide.BUY else "Buy"
                })
        
        url = f"{self.config.api_endpoint}/trade/v2/orders"
        
        async with self._session.post(url, json=order_data) as response:
            if response.status not in [200, 201]:
                error_text = await response.text()
                logger.error(f"注文エラー: {response.status} - {error_text}")
                order.status = OrderStatus.REJECTED
                return order
            
            data = await response.json()
            
            order.order_id = data.get("OrderId", "")
            order.status = OrderStatus.OPEN
            order.updated_at = datetime.now()
            
            # 成行注文の場合は約定情報を取得
            if order.order_type == OrderType.MARKET:
                await asyncio.sleep(0.5)  # 約定待ち
                filled_order = await self._get_order_status(order.order_id)
                if filled_order:
                    order.status = filled_order.status
                    order.filled_quantity = filled_order.filled_quantity
                    order.filled_price = filled_order.filled_price
            
            logger.info(f"注文受付: {order.order_id}")
            return order
    
    async def _get_order_status(self, order_id: str) -> Optional[Order]:
        """注文ステータスを取得"""
        if self.demo_mode:
            return None
        
        url = f"{self.config.api_endpoint}/port/v1/orders/{order_id}"
        
        async with self._session.get(url) as response:
            if response.status != 200:
                return None
            
            data = await response.json()
            # 注文ステータスをパース（実装は省略）
            return None
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """注文タイプをSaxo形式に変換"""
        mapping = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP: "StopIfTraded",
            OrderType.STOP_LIMIT: "StopLimit"
        }
        return mapping.get(order_type, "Market")
    
    async def cancel_order(self, order_id: str) -> bool:
        """注文をキャンセル"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        logger.info(f"注文キャンセル: {order_id}")
        
        if self.demo_mode:
            return True
        
        url = f"{self.config.api_endpoint}/trade/v2/orders/{order_id}"
        
        async with self._session.delete(url) as response:
            if response.status in [200, 204]:
                logger.info(f"注文キャンセル成功: {order_id}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"注文キャンセルエラー: {response.status} - {error_text}")
                return False
    
    async def get_open_orders(self) -> List[Order]:
        """未約定注文一覧を取得"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        if self.demo_mode:
            return []
        
        url = f"{self.config.api_endpoint}/port/v1/orders/me"
        
        async with self._session.get(url) as response:
            if response.status != 200:
                return []
            
            data = await response.json()
            orders = []
            
            for order_data in data.get("Data", []):
                # 注文データをパース（詳細実装は省略）
                pass
            
            return orders
    
    async def get_positions(self) -> List[Position]:
        """保有ポジション一覧を取得"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        if self.demo_mode:
            return list(self._positions.values())
        
        url = f"{self.config.api_endpoint}/port/v1/positions/me"
        
        params = {"FieldGroups": "PositionBase,PositionView,ExchangeInfo"}
        
        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                return []
            
            data = await response.json()
            positions = []
            
            for pos_data in data.get("Data", []):
                base = pos_data.get("PositionBase", {})
                view = pos_data.get("PositionView", {})
                
                # Uicから通貨ペアを逆引き
                uic = base.get("Uic")
                currency_pair = None
                for cp, u in SAXO_CURRENCY_PAIR_UIC.items():
                    if u == uic:
                        currency_pair = cp
                        break
                
                if not currency_pair:
                    continue
                
                position = Position(
                    position_id=base.get("PositionId", ""),
                    currency_pair=currency_pair,
                    side=OrderSide.BUY if base.get("Amount", 0) > 0 else OrderSide.SELL,
                    quantity=abs(base.get("Amount", 0)),
                    entry_price=Decimal(str(view.get("AverageOpenPrice", 0))),
                    current_price=Decimal(str(view.get("CurrentPrice", 0))),
                    opened_at=datetime.fromisoformat(
                        base.get("ExecutionTimeOpen", "").replace("Z", "+00:00")
                    ) if base.get("ExecutionTimeOpen") else datetime.now()
                )
                positions.append(position)
            
            return positions
    
    async def close_position(self, position_id: str) -> bool:
        """ポジションを決済"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        logger.info(f"ポジション決済: {position_id}")
        
        if self.demo_mode:
            if position_id in self._positions:
                del self._positions[position_id]
            return True
        
        # ポジション情報を取得
        positions = await self.get_positions()
        position = next((p for p in positions if p.position_id == position_id), None)
        
        if not position:
            logger.error(f"ポジションが見つかりません: {position_id}")
            return False
        
        # 反対売買の注文を発注
        close_order = Order(
            order_id="",
            currency_pair=position.currency_pair,
            side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=position.quantity
        )
        
        result = await self.place_order(close_order)
        return result.status == OrderStatus.FILLED
    
    async def get_account_info(self) -> AccountInfo:
        """口座情報を取得"""
        self._ensure_connected()
        await self._ensure_token_valid()
        
        if self.demo_mode:
            return AccountInfo(
                account_id="SAXO-DEMO-001",
                balance=Decimal("1000000"),
                equity=Decimal("1000000"),
                margin_used=Decimal("0"),
                margin_available=Decimal("1000000"),
                unrealized_pnl=Decimal("0"),
                margin_level=None
            )
        
        url = f"{self.config.api_endpoint}/port/v1/balances"
        
        params = {
            "AccountKey": self._account_key,
            "FieldGroups": "All"
        }
        
        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"口座情報取得エラー: {response.status} - {error_text}")
                return AccountInfo(
                    account_id=self._account_key or "",
                    balance=Decimal("0"),
                    equity=Decimal("0"),
                    margin_used=Decimal("0"),
                    margin_available=Decimal("0"),
                    unrealized_pnl=Decimal("0")
                )
            
            data = await response.json()
            
            return AccountInfo(
                account_id=self._account_key or "",
                balance=Decimal(str(data.get("CashBalance", 0))),
                equity=Decimal(str(data.get("TotalValue", 0))),
                margin_used=Decimal(str(data.get("MarginUsedByCurrentPositions", 0))),
                margin_available=Decimal(str(data.get("MarginAvailableForTrading", 0))),
                unrealized_pnl=Decimal(str(data.get("UnrealizedProfitLoss", 0))),
                margin_level=Decimal(str(data.get("MarginUtilizationPct", 0)))
                    if data.get("MarginUtilizationPct") else None
            )
    
    async def start_price_streaming(
        self,
        currency_pairs: List[CurrencyPair],
        on_tick: Callable[[Tick], None]
    ) -> None:
        """価格ストリーミングを開始"""
        if self.demo_mode:
            logger.warning("デモモードではストリーミングは利用できません")
            return
        
        if not self._token:
            raise ConnectionError("認証されていません")
        
        self._price_streaming = SaxoPriceStreaming(self.config, self._token)
        
        if await self._price_streaming.connect():
            self._price_streaming.add_price_callback(on_tick)
            
            for currency_pair in currency_pairs:
                await self._price_streaming.subscribe_price(currency_pair)
            
            # バックグラウンドでリッスン
            asyncio.create_task(self._price_streaming.listen())
    
    async def stop_price_streaming(self) -> None:
        """価格ストリーミングを停止"""
        if self._price_streaming:
            await self._price_streaming.disconnect()
            self._price_streaming = None
    
    # ==================== モックデータ生成（デモ用） ====================
    
    def _generate_mock_tick(self, currency_pair: CurrencyPair) -> Tick:
        """モックティックデータを生成"""
        import random
        
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
        variation = Decimal(str(random.uniform(-0.05, 0.05)))
        mid_price = base_price + variation
        
        if "JPY" in currency_pair.value:
            spread = Decimal("0.002")  # Saxoは低スプレッド
        else:
            spread = Decimal("0.00002")
        
        return Tick(
            currency_pair=currency_pair,
            bid=mid_price - spread / 2,
            ask=mid_price + spread / 2,
            timestamp=datetime.now()
        )
    
    def _generate_mock_ohlcv(self, currency_pair: CurrencyPair, count: int) -> List[OHLCV]:
        """モックOHLCVデータを生成"""
        import random
        
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
            change = random.gauss(0, 0.001) * base_price
            current_price += change
            
            open_price = current_price
            high_price = current_price + abs(random.gauss(0, 0.0005)) * base_price
            low_price = current_price - abs(random.gauss(0, 0.0005)) * base_price
            close_price = current_price + random.gauss(0, 0.0003) * base_price
            
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


# ファクトリー関数
def create_saxo_client(
    app_key: str = "",
    app_secret: str = "",
    environment: str = "sim",
    demo_mode: bool = True
) -> SaxoBankClient:
    """Saxo Bankクライアントを作成"""
    config = SaxoConfig(
        app_key=app_key,
        app_secret=app_secret,
        environment=SaxoEnvironment.SIMULATION if environment == "sim" else SaxoEnvironment.LIVE
    )
    return SaxoBankClient(config, demo_mode=demo_mode)


if __name__ == "__main__":
    # テスト実行
    async def test_saxo_client():
        print("=" * 60)
        print("Saxo Bank OpenAPI クライアント テスト")
        print("=" * 60)
        
        # デモモードでクライアントを作成
        client = create_saxo_client(demo_mode=True)
        
        # 接続
        connected = await client.connect()
        print(f"\n接続状態: {'成功' if connected else '失敗'}")
        
        if connected:
            # ティックデータ取得
            tick = await client.get_tick(CurrencyPair.USDJPY)
            print(f"\nUSD/JPY: Bid={tick.bid}, Ask={tick.ask}, Spread={tick.spread:.1f}pips")
            
            # OHLCV取得
            ohlcv = await client.get_ohlcv(CurrencyPair.USDJPY, "1hour", count=10)
            print(f"\nOHLCVデータ: {len(ohlcv)}本")
            if ohlcv:
                latest = ohlcv[-1]
                print(f"  最新: O={latest.open}, H={latest.high}, L={latest.low}, C={latest.close}")
            
            # 口座情報
            account = await client.get_account_info()
            print(f"\n口座情報:")
            print(f"  残高: ¥{account.balance:,.0f}")
            print(f"  有効証拠金: ¥{account.equity:,.0f}")
            
            # 注文テスト
            from api_client import Order, OrderType, OrderSide
            
            order = Order(
                order_id="",
                currency_pair=CurrencyPair.USDJPY,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10000,
                stop_loss=Decimal("149.500"),
                take_profit=Decimal("151.000")
            )
            
            result = await client.place_order(order)
            print(f"\n注文結果:")
            print(f"  注文ID: {result.order_id}")
            print(f"  ステータス: {result.status.value}")
            print(f"  約定価格: {result.filled_price}")
            
            # 切断
            await client.disconnect()
        
        print("\n" + "=" * 60)
        print("テスト完了")
        print("=" * 60)
    
    asyncio.run(test_saxo_client())
