"""
FX自動売買システム - バックテストエンジン

過去データを使用して戦略のパフォーマンスを検証します。
リアルな取引条件（スプレッド、スリッページ等）をシミュレートします。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import random

import numpy as np
import pandas as pd

from api_client import (
    CurrencyPair, MockBrokerClient, OHLCV, Order, OrderSide,
    OrderType, Position, Tick
)
from config import RiskConfig, StrategyConfig, TradingConfig
from indicators import ohlcv_to_dataframe
from risk_management import RiskManager, TradeRecord
from strategy import TradingStrategy, TradingSignal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """バックテスト設定"""
    initial_balance: Decimal = Decimal("1000000")  # 初期資金（円）
    spread_pips: float = 0.3  # スプレッド（pips）
    slippage_pips: float = 0.1  # スリッページ（pips）
    commission_per_lot: Decimal = Decimal("0")  # 手数料（1ロットあたり）
    leverage: int = 25  # レバレッジ
    min_trade_interval_bars: int = 1  # 最小取引間隔（バー数）


@dataclass
class BacktestTrade:
    """バックテスト取引記録"""
    trade_id: int
    currency_pair: CurrencyPair
    side: OrderSide
    entry_time: datetime
    entry_price: Decimal
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    quantity: int = 1000
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    pnl_pips: Optional[float] = None
    exit_reason: str = ""
    strategy_name: str = ""
    signal_confidence: float = 0.0
    
    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None
    
    @property
    def is_winning(self) -> bool:
        return self.pnl is not None and self.pnl > 0
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "currency_pair": self.currency_pair.value,
            "side": self.side.value,
            "entry_time": self.entry_time.isoformat(),
            "entry_price": float(self.entry_price),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "quantity": self.quantity,
            "pnl": float(self.pnl) if self.pnl else None,
            "pnl_pips": self.pnl_pips,
            "exit_reason": self.exit_reason,
            "strategy_name": self.strategy_name
        }


@dataclass
class BacktestResult:
    """バックテスト結果"""
    # 基本情報
    strategy_name: str
    currency_pair: CurrencyPair
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal
    final_balance: Decimal
    
    # パフォーマンス指標
    total_return: float  # 総リターン（%）
    annualized_return: float  # 年率リターン（%）
    max_drawdown: float  # 最大ドローダウン（%）
    sharpe_ratio: float  # シャープレシオ
    sortino_ratio: float  # ソルティノレシオ
    calmar_ratio: float  # カルマーレシオ
    
    # 取引統計
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 勝率（%）
    profit_factor: float
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    average_trade_duration: timedelta
    
    # 詳細データ
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "strategy_name": self.strategy_name,
            "currency_pair": self.currency_pair.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_balance": float(self.initial_balance),
            "final_balance": float(self.final_balance),
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "average_win": float(self.average_win),
            "average_loss": float(self.average_loss),
            "largest_win": float(self.largest_win),
            "largest_loss": float(self.largest_loss),
            "monthly_returns": self.monthly_returns
        }
    
    def print_summary(self) -> None:
        """結果サマリーを表示"""
        print("=" * 70)
        print(f"バックテスト結果: {self.strategy_name}")
        print("=" * 70)
        print(f"期間: {self.start_date.date()} 〜 {self.end_date.date()}")
        print(f"通貨ペア: {self.currency_pair.value}")
        print()
        print("【パフォーマンス】")
        print(f"  初期資金: ¥{self.initial_balance:,.0f}")
        print(f"  最終資金: ¥{self.final_balance:,.0f}")
        print(f"  総リターン: {self.total_return:+.2f}%")
        print(f"  年率リターン: {self.annualized_return:+.2f}%")
        print(f"  最大ドローダウン: {self.max_drawdown:.2f}%")
        print()
        print("【リスク指標】")
        print(f"  シャープレシオ: {self.sharpe_ratio:.2f}")
        print(f"  ソルティノレシオ: {self.sortino_ratio:.2f}")
        print(f"  カルマーレシオ: {self.calmar_ratio:.2f}")
        print()
        print("【取引統計】")
        print(f"  総取引数: {self.total_trades}")
        print(f"  勝ち: {self.winning_trades} / 負け: {self.losing_trades}")
        print(f"  勝率: {self.win_rate:.1f}%")
        print(f"  プロフィットファクター: {self.profit_factor:.2f}")
        print(f"  平均利益: ¥{self.average_win:,.0f}")
        print(f"  平均損失: ¥{self.average_loss:,.0f}")
        print(f"  最大利益: ¥{self.largest_win:,.0f}")
        print(f"  最大損失: ¥{self.largest_loss:,.0f}")
        print("=" * 70)


class BacktestEngine:
    """バックテストエンジン"""
    
    def __init__(
        self,
        strategy: TradingStrategy,
        risk_config: RiskConfig = None,
        backtest_config: BacktestConfig = None
    ):
        self.strategy = strategy
        self.risk_config = risk_config or RiskConfig()
        self.config = backtest_config or BacktestConfig()
        self.risk_manager = RiskManager(self.risk_config)
        
        # 状態管理
        self.balance = self.config.initial_balance
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
        self.trades: List[BacktestTrade] = []
        self.open_trades: List[BacktestTrade] = []
        self.trade_counter = 0
        self.last_trade_bar = -100
    
    def run(
        self,
        ohlcv_data: List[OHLCV],
        currency_pair: CurrencyPair,
        position_size: int = 10000
    ) -> BacktestResult:
        """
        バックテストを実行
        
        Args:
            ohlcv_data: ローソク足データ
            currency_pair: 通貨ペア
            position_size: ポジションサイズ（通貨単位）
        
        Returns:
            BacktestResult
        """
        if len(ohlcv_data) < 100:
            raise ValueError("バックテストには最低100本のローソク足が必要です")
        
        logger.info(f"バックテスト開始: {self.strategy.name}, {len(ohlcv_data)}本のバー")
        
        # 初期化
        self.balance = self.config.initial_balance
        self.equity_curve = []
        self.trades = []
        self.open_trades = []
        self.trade_counter = 0
        self.last_trade_bar = -100
        
        peak_balance = self.balance
        max_drawdown = 0.0
        
        # ウォームアップ期間（指標計算に必要な最小期間）
        warmup_period = 50
        
        # 各バーをループ
        for bar_idx in range(warmup_period, len(ohlcv_data)):
            current_bar = ohlcv_data[bar_idx]
            historical_data = ohlcv_data[:bar_idx + 1]
            
            # 現在のティック（模擬）
            pip_value = Decimal("0.01") if "JPY" in currency_pair.value else Decimal("0.0001")
            spread = pip_value * Decimal(str(self.config.spread_pips))
            
            current_tick = Tick(
                currency_pair=currency_pair,
                bid=current_bar.close - spread / 2,
                ask=current_bar.close + spread / 2,
                timestamp=current_bar.timestamp
            )
            
            # オープンポジションをチェック
            self._check_open_trades(current_bar, current_tick)
            
            # 新規シグナルを生成
            if bar_idx - self.last_trade_bar >= self.config.min_trade_interval_bars:
                signal = self.strategy.generate_signal(
                    currency_pair, historical_data, current_tick
                )
                
                # シグナルに基づいてエントリー
                if signal.is_buy_signal or signal.is_sell_signal:
                    if len(self.open_trades) < self.risk_config.max_open_positions:
                        self._open_trade(
                            signal, current_tick, current_bar.timestamp,
                            position_size, bar_idx
                        )
            
            # エクイティを記録
            current_equity = self._calculate_equity(current_tick)
            self.equity_curve.append((current_bar.timestamp, current_equity))
            
            # ドローダウンを更新
            if current_equity > peak_balance:
                peak_balance = current_equity
            
            current_drawdown = float((peak_balance - current_equity) / peak_balance * 100)
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
        
        # 残りのオープンポジションを強制決済
        final_bar = ohlcv_data[-1]
        final_tick = Tick(
            currency_pair=currency_pair,
            bid=final_bar.close - Decimal("0.003"),
            ask=final_bar.close + Decimal("0.003"),
            timestamp=final_bar.timestamp
        )
        
        for trade in list(self.open_trades):
            self._close_trade(trade, final_tick, final_bar.timestamp, "バックテスト終了")
        
        # 結果を集計
        return self._compile_results(
            currency_pair,
            ohlcv_data[0].timestamp,
            ohlcv_data[-1].timestamp,
            max_drawdown
        )
    
    def _open_trade(
        self,
        signal: TradingSignal,
        tick: Tick,
        timestamp: datetime,
        position_size: int,
        bar_idx: int
    ) -> None:
        """新規トレードをオープン"""
        self.trade_counter += 1
        
        # エントリー価格（スリッページ込み）
        slippage = Decimal(str(random.uniform(0, self.config.slippage_pips)))
        pip_value = Decimal("0.01") if "JPY" in signal.currency_pair.value else Decimal("0.0001")
        slippage_amount = slippage * pip_value
        
        if signal.is_buy_signal:
            entry_price = tick.ask + slippage_amount
            side = OrderSide.BUY
        else:
            entry_price = tick.bid - slippage_amount
            side = OrderSide.SELL
        
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            currency_pair=signal.currency_pair,
            side=side,
            entry_time=timestamp,
            entry_price=entry_price,
            quantity=position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy_name=signal.strategy_name,
            signal_confidence=signal.confidence
        )
        
        self.open_trades.append(trade)
        self.last_trade_bar = bar_idx
        
        logger.debug(f"トレードオープン: {trade.trade_id} {side.value} @ {entry_price}")
    
    def _close_trade(
        self,
        trade: BacktestTrade,
        tick: Tick,
        timestamp: datetime,
        reason: str
    ) -> None:
        """トレードをクローズ"""
        # 出口価格（スリッページ込み）
        slippage = Decimal(str(random.uniform(0, self.config.slippage_pips)))
        pip_value = Decimal("0.01") if "JPY" in trade.currency_pair.value else Decimal("0.0001")
        slippage_amount = slippage * pip_value
        
        if trade.side == OrderSide.BUY:
            exit_price = tick.bid - slippage_amount
        else:
            exit_price = tick.ask + slippage_amount
        
        # 損益計算
        if trade.side == OrderSide.BUY:
            pnl_pips = float((exit_price - trade.entry_price) / pip_value)
        else:
            pnl_pips = float((trade.entry_price - exit_price) / pip_value)
        
        # 金額ベースの損益（JPYペアの場合）
        if "JPY" in trade.currency_pair.value:
            pnl = Decimal(str(pnl_pips)) * pip_value * trade.quantity
        else:
            # 非JPYペアの場合、円換算が必要（簡略化のため固定レート使用）
            pnl = Decimal(str(pnl_pips * 0.01 * trade.quantity * 150))
        
        # 手数料を差し引く
        commission = self.config.commission_per_lot * Decimal(str(trade.quantity / 10000))
        pnl -= commission
        
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_pips = pnl_pips
        trade.exit_reason = reason
        
        # 残高を更新
        self.balance += pnl
        
        # オープンから移動
        if trade in self.open_trades:
            self.open_trades.remove(trade)
        self.trades.append(trade)
        
        logger.debug(f"トレードクローズ: {trade.trade_id} @ {exit_price} "
                    f"PnL: {pnl_pips:.1f}pips ({pnl:+,.0f}円) [{reason}]")
    
    def _check_open_trades(self, bar: OHLCV, tick: Tick) -> None:
        """オープンポジションをチェック（SL/TP）"""
        for trade in list(self.open_trades):
            # ストップロスチェック
            if trade.stop_loss:
                if trade.side == OrderSide.BUY:
                    if bar.low <= trade.stop_loss:
                        self._close_trade(trade, tick, bar.timestamp, "損切り")
                        continue
                else:
                    if bar.high >= trade.stop_loss:
                        self._close_trade(trade, tick, bar.timestamp, "損切り")
                        continue
            
            # テイクプロフィットチェック
            if trade.take_profit:
                if trade.side == OrderSide.BUY:
                    if bar.high >= trade.take_profit:
                        self._close_trade(trade, tick, bar.timestamp, "利確")
                        continue
                else:
                    if bar.low <= trade.take_profit:
                        self._close_trade(trade, tick, bar.timestamp, "利確")
                        continue
    
    def _calculate_equity(self, tick: Tick) -> Decimal:
        """現在のエクイティを計算"""
        equity = self.balance
        
        pip_value = Decimal("0.01") if "JPY" in tick.currency_pair.value else Decimal("0.0001")
        
        for trade in self.open_trades:
            if trade.side == OrderSide.BUY:
                unrealized_pips = (tick.bid - trade.entry_price) / pip_value
            else:
                unrealized_pips = (trade.entry_price - tick.ask) / pip_value
            
            unrealized_pnl = unrealized_pips * pip_value * trade.quantity
            equity += unrealized_pnl
        
        return equity
    
    def _compile_results(
        self,
        currency_pair: CurrencyPair,
        start_date: datetime,
        end_date: datetime,
        max_drawdown: float
    ) -> BacktestResult:
        """結果を集計"""
        closed_trades = [t for t in self.trades if t.is_closed]
        
        if not closed_trades:
            return BacktestResult(
                strategy_name=self.strategy.name,
                currency_pair=currency_pair,
                start_date=start_date,
                end_date=end_date,
                initial_balance=self.config.initial_balance,
                final_balance=self.balance,
                total_return=0.0,
                annualized_return=0.0,
                max_drawdown=max_drawdown,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                average_win=Decimal("0"),
                average_loss=Decimal("0"),
                largest_win=Decimal("0"),
                largest_loss=Decimal("0"),
                average_trade_duration=timedelta(0),
                trades=self.trades,
                equity_curve=self.equity_curve
            )
        
        winning_trades = [t for t in closed_trades if t.is_winning]
        losing_trades = [t for t in closed_trades if not t.is_winning and t.pnl is not None]
        
        # リターン計算
        total_return = float(
            (self.balance - self.config.initial_balance) / self.config.initial_balance * 100
        )
        
        days = (end_date - start_date).days
        years = days / 365.25 if days > 0 else 1
        annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 勝率・プロフィットファクター
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        total_profit = sum(t.pnl for t in winning_trades if t.pnl)
        total_loss = abs(sum(t.pnl for t in losing_trades if t.pnl))
        profit_factor = float(total_profit / total_loss) if total_loss > 0 else float("inf")
        
        # 平均値
        average_win = total_profit / len(winning_trades) if winning_trades else Decimal("0")
        average_loss = (
            abs(sum(t.pnl for t in losing_trades if t.pnl)) / len(losing_trades)
            if losing_trades else Decimal("0")
        )
        
        largest_win = max((t.pnl for t in winning_trades if t.pnl), default=Decimal("0"))
        largest_loss = min((t.pnl for t in losing_trades if t.pnl), default=Decimal("0"))
        
        # 取引時間
        durations = [
            (t.exit_time - t.entry_time) for t in closed_trades
            if t.exit_time and t.entry_time
        ]
        average_duration = (
            sum(durations, timedelta(0)) / len(durations) if durations else timedelta(0)
        )
        
        # シャープレシオ計算
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1][1]
            curr_equity = self.equity_curve[i][1]
            if prev_equity > 0:
                returns.append(float((curr_equity - prev_equity) / prev_equity))
        
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
            
            # ソルティノレシオ（下方偏差のみ）
            negative_returns = [r for r in returns if r < 0]
            downside_std = np.std(negative_returns) if negative_returns else std_return
            sortino_ratio = (avg_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0
        
        # カルマーレシオ
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # 月次リターン
        monthly_returns = {}
        for timestamp, equity in self.equity_curve:
            month_key = timestamp.strftime("%Y-%m")
            monthly_returns[month_key] = float(equity)
        
        return BacktestResult(
            strategy_name=self.strategy.name,
            currency_pair=currency_pair,
            start_date=start_date,
            end_date=end_date,
            initial_balance=self.config.initial_balance,
            final_balance=self.balance,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=len(closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            average_trade_duration=average_duration,
            trades=self.trades,
            equity_curve=self.equity_curve,
            monthly_returns=monthly_returns
        )


def generate_sample_data(
    currency_pair: CurrencyPair = CurrencyPair.USDJPY,
    bars: int = 1000,
    timeframe_hours: int = 1,
    trend: float = 0.0,
    volatility: float = 0.001
) -> List[OHLCV]:
    """
    サンプルデータを生成（バックテストテスト用）
    
    Args:
        currency_pair: 通貨ペア
        bars: バー数
        timeframe_hours: 時間足（時間）
        trend: トレンド成分（正=上昇、負=下落）
        volatility: ボラティリティ
    
    Returns:
        OHLCVリスト
    """
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
    
    for i in range(bars):
        timestamp = now - timedelta(hours=(bars - i) * timeframe_hours)
        
        # ランダムウォーク + トレンド
        change = random.gauss(trend, volatility) * base_price
        current_price += change
        
        # OHLC生成
        open_price = current_price + random.gauss(0, volatility * 0.3) * base_price
        high_price = current_price + abs(random.gauss(0, volatility * 0.5)) * base_price
        low_price = current_price - abs(random.gauss(0, volatility * 0.5)) * base_price
        close_price = current_price + random.gauss(0, volatility * 0.3) * base_price
        
        # 整合性を保証
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


class StrategyOptimizer:
    """戦略パラメータ最適化クラス"""
    
    def __init__(
        self,
        strategy_class: type,
        param_ranges: Dict[str, List[Any]],
        risk_config: RiskConfig = None,
        backtest_config: BacktestConfig = None
    ):
        """
        Args:
            strategy_class: 最適化する戦略クラス
            param_ranges: パラメータ範囲
                例: {"period": [10, 20, 30], "threshold": [0.5, 0.7, 0.9]}
            risk_config: リスク設定
            backtest_config: バックテスト設定
        """
        self.strategy_class = strategy_class
        self.param_ranges = param_ranges
        self.risk_config = risk_config or RiskConfig()
        self.backtest_config = backtest_config or BacktestConfig()
    
    def optimize(
        self,
        ohlcv_data: List[OHLCV],
        currency_pair: CurrencyPair,
        optimization_metric: str = "sharpe_ratio"
    ) -> Tuple[Dict[str, Any], BacktestResult]:
        """
        グリッドサーチで最適なパラメータを探索
        
        Args:
            ohlcv_data: ローソク足データ
            currency_pair: 通貨ペア
            optimization_metric: 最適化指標
        
        Returns:
            (最適パラメータ, 最良結果)
        """
        from itertools import product
        
        # パラメータの組み合わせを生成
        param_names = list(self.param_ranges.keys())
        param_values = list(self.param_ranges.values())
        
        best_params = None
        best_result = None
        best_metric_value = float("-inf")
        
        total_combinations = 1
        for values in param_values:
            total_combinations *= len(values)
        
        logger.info(f"最適化開始: {total_combinations}通りの組み合わせをテスト")
        
        for i, combination in enumerate(product(*param_values)):
            params = dict(zip(param_names, combination))
            
            # 戦略インスタンスを作成
            strategy_config = StrategyConfig()
            strategy = self.strategy_class(strategy_config, **params)
            
            # バックテスト実行
            engine = BacktestEngine(
                strategy,
                self.risk_config,
                self.backtest_config
            )
            
            try:
                result = engine.run(ohlcv_data, currency_pair)
                
                # 指標を取得
                metric_value = getattr(result, optimization_metric, 0)
                
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_params = params
                    best_result = result
                
                logger.debug(f"パラメータ {params}: {optimization_metric}={metric_value:.4f}")
            
            except Exception as e:
                logger.warning(f"パラメータ {params} でエラー: {e}")
        
        logger.info(f"最適化完了: 最良パラメータ={best_params}, {optimization_metric}={best_metric_value:.4f}")
        
        return best_params, best_result


if __name__ == "__main__":
    # テスト実行
    from config import StrategyConfig
    from strategy import MovingAverageCrossStrategy, RSIMeanReversionStrategy, CombinedStrategy
    
    print("=" * 70)
    print("バックテストエンジン テスト")
    print("=" * 70)
    
    # サンプルデータ生成
    print("\nサンプルデータ生成中...")
    data = generate_sample_data(
        currency_pair=CurrencyPair.USDJPY,
        bars=1000,
        timeframe_hours=1,
        trend=0.00005,  # 弱い上昇トレンド
        volatility=0.0008
    )
    print(f"データ期間: {data[0].timestamp.date()} 〜 {data[-1].timestamp.date()}")
    
    # 戦略をテスト
    strategies = [
        ("移動平均クロス", MovingAverageCrossStrategy(StrategyConfig())),
        ("RSI平均回帰", RSIMeanReversionStrategy(StrategyConfig())),
        ("複合戦略", CombinedStrategy(StrategyConfig())),
    ]
    
    for name, strategy in strategies:
        print(f"\n{'-' * 50}")
        print(f"戦略: {name}")
        print(f"{'-' * 50}")
        
        engine = BacktestEngine(
            strategy,
            RiskConfig(),
            BacktestConfig(initial_balance=Decimal("1000000"))
        )
        
        result = engine.run(data, CurrencyPair.USDJPY)
        result.print_summary()
