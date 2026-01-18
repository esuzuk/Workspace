"""
FX自動売買システム - トレード戦略モジュール

複数のトレード戦略を実装し、シグナル生成を行います。
戦略は抽象基底クラスを継承して実装され、組み合わせも可能です。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from api_client import CurrencyPair, OHLCV, OrderSide, Tick
from config import StrategyConfig
from indicators import TechnicalIndicators, calculate_all_indicators, ohlcv_to_dataframe


class SignalType(Enum):
    """シグナルタイプ"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    NEUTRAL = "neutral"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """トレードシグナル"""
    signal_type: SignalType
    currency_pair: CurrencyPair
    timestamp: datetime
    confidence: float  # 0.0 - 1.0
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    strategy_name: str = ""
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_buy_signal(self) -> bool:
        return self.signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]
    
    @property
    def is_sell_signal(self) -> bool:
        return self.signal_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]
    
    @property
    def order_side(self) -> Optional[OrderSide]:
        if self.is_buy_signal:
            return OrderSide.BUY
        elif self.is_sell_signal:
            return OrderSide.SELL
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "currency_pair": self.currency_pair.value,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "strategy_name": self.strategy_name,
            "reason": self.reason,
        }


class TradingStrategy(ABC):
    """トレード戦略の抽象基底クラス"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        """
        シグナルを生成
        
        Args:
            currency_pair: 通貨ペア
            ohlcv_data: ローソク足データ
            current_tick: 現在のティックデータ
        
        Returns:
            トレードシグナル
        """
        pass
    
    def _create_signal(
        self,
        signal_type: SignalType,
        currency_pair: CurrencyPair,
        confidence: float,
        reason: str,
        entry_price: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        metadata: Dict[str, Any] = None
    ) -> TradingSignal:
        """シグナルを作成するヘルパーメソッド"""
        return TradingSignal(
            signal_type=signal_type,
            currency_pair=currency_pair,
            timestamp=datetime.now(),
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=self.name,
            reason=reason,
            metadata=metadata or {}
        )


class MovingAverageCrossStrategy(TradingStrategy):
    """
    移動平均線クロス戦略
    
    短期MAと長期MAのクロスでエントリー・エグジットを判断します。
    ゴールデンクロス（短期>長期）で買い、デッドクロス（短期<長期）で売り。
    """
    
    def __init__(self, config: StrategyConfig, short_period: int = 20, long_period: int = 50):
        super().__init__(config)
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        if len(ohlcv_data) < self.long_period + 1:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                "データ不足"
            )
        
        df = ohlcv_to_dataframe(ohlcv_data)
        indicators = TechnicalIndicators(df)
        
        short_ma = indicators.sma(self.short_period)
        long_ma = indicators.sma(self.long_period)
        
        # 現在と前回の値
        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]
        
        # ゴールデンクロス検出
        if prev_short <= prev_long and current_short > current_long:
            confidence = min(abs(current_short - current_long) / current_long * 100, 1.0)
            entry_price = Decimal(str(df["close"].iloc[-1]))
            atr = indicators.atr(14).iloc[-1]
            
            return self._create_signal(
                SignalType.BUY,
                currency_pair,
                confidence,
                f"ゴールデンクロス発生（SMA{self.short_period} > SMA{self.long_period}）",
                entry_price=entry_price,
                stop_loss=entry_price - Decimal(str(atr * 2)),
                take_profit=entry_price + Decimal(str(atr * 4)),
                metadata={"short_ma": current_short, "long_ma": current_long}
            )
        
        # デッドクロス検出
        if prev_short >= prev_long and current_short < current_long:
            confidence = min(abs(current_long - current_short) / current_long * 100, 1.0)
            entry_price = Decimal(str(df["close"].iloc[-1]))
            atr = indicators.atr(14).iloc[-1]
            
            return self._create_signal(
                SignalType.SELL,
                currency_pair,
                confidence,
                f"デッドクロス発生（SMA{self.short_period} < SMA{self.long_period}）",
                entry_price=entry_price,
                stop_loss=entry_price + Decimal(str(atr * 2)),
                take_profit=entry_price - Decimal(str(atr * 4)),
                metadata={"short_ma": current_short, "long_ma": current_long}
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            "クロスなし",
            metadata={"short_ma": current_short, "long_ma": current_long}
        )


class RSIMeanReversionStrategy(TradingStrategy):
    """
    RSI平均回帰戦略
    
    RSIの買われすぎ・売られすぎを利用した逆張り戦略です。
    RSI < 30 で買い、RSI > 70 で売り。
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0
    ):
        super().__init__(config)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        if len(ohlcv_data) < self.rsi_period + 1:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                "データ不足"
            )
        
        df = ohlcv_to_dataframe(ohlcv_data)
        indicators = TechnicalIndicators(df)
        
        rsi = indicators.rsi(self.rsi_period)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        entry_price = Decimal(str(df["close"].iloc[-1]))
        atr = indicators.atr(14).iloc[-1]
        
        # 売られすぎからの反発（買いシグナル）
        if current_rsi < self.oversold:
            # RSIが上昇に転じた場合、より強いシグナル
            if current_rsi > prev_rsi:
                signal_type = SignalType.BUY
                confidence = (self.oversold - current_rsi) / self.oversold
            else:
                signal_type = SignalType.WEAK_BUY
                confidence = (self.oversold - current_rsi) / self.oversold * 0.7
            
            return self._create_signal(
                signal_type,
                currency_pair,
                min(confidence, 1.0),
                f"RSI売られすぎ（RSI={current_rsi:.1f}）",
                entry_price=entry_price,
                stop_loss=entry_price - Decimal(str(atr * 2)),
                take_profit=entry_price + Decimal(str(atr * 3)),
                metadata={"rsi": current_rsi}
            )
        
        # 買われすぎからの反落（売りシグナル）
        if current_rsi > self.overbought:
            # RSIが下落に転じた場合、より強いシグナル
            if current_rsi < prev_rsi:
                signal_type = SignalType.SELL
                confidence = (current_rsi - self.overbought) / (100 - self.overbought)
            else:
                signal_type = SignalType.WEAK_SELL
                confidence = (current_rsi - self.overbought) / (100 - self.overbought) * 0.7
            
            return self._create_signal(
                signal_type,
                currency_pair,
                min(confidence, 1.0),
                f"RSI買われすぎ（RSI={current_rsi:.1f}）",
                entry_price=entry_price,
                stop_loss=entry_price + Decimal(str(atr * 2)),
                take_profit=entry_price - Decimal(str(atr * 3)),
                metadata={"rsi": current_rsi}
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            f"RSI中立（RSI={current_rsi:.1f}）",
            metadata={"rsi": current_rsi}
        )


class BollingerBandStrategy(TradingStrategy):
    """
    ボリンジャーバンド戦略
    
    価格がボリンジャーバンドの上限・下限に到達した際の反発を狙います。
    下限タッチで買い、上限タッチで売り。
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        period: int = 20,
        std_dev: float = 2.0
    ):
        super().__init__(config)
        self.period = period
        self.std_dev = std_dev
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        if len(ohlcv_data) < self.period + 1:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                "データ不足"
            )
        
        df = ohlcv_to_dataframe(ohlcv_data)
        indicators = TechnicalIndicators(df)
        
        upper, middle, lower = indicators.bollinger_bands(self.period, self.std_dev)
        
        current_close = df["close"].iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        current_middle = middle.iloc[-1]
        
        entry_price = Decimal(str(current_close))
        band_width = current_upper - current_lower
        
        # 下限バンドを下回った（買いシグナル）
        if current_close <= current_lower:
            # どれだけ下回ったかで信頼度を計算
            penetration = (current_lower - current_close) / band_width
            confidence = min(0.5 + penetration * 2, 1.0)
            
            return self._create_signal(
                SignalType.BUY,
                currency_pair,
                confidence,
                f"ボリンジャーバンド下限タッチ",
                entry_price=entry_price,
                stop_loss=entry_price - Decimal(str(band_width * 0.3)),
                take_profit=Decimal(str(current_middle)),
                metadata={
                    "upper": current_upper,
                    "middle": current_middle,
                    "lower": current_lower
                }
            )
        
        # 上限バンドを上回った（売りシグナル）
        if current_close >= current_upper:
            penetration = (current_close - current_upper) / band_width
            confidence = min(0.5 + penetration * 2, 1.0)
            
            return self._create_signal(
                SignalType.SELL,
                currency_pair,
                confidence,
                f"ボリンジャーバンド上限タッチ",
                entry_price=entry_price,
                stop_loss=entry_price + Decimal(str(band_width * 0.3)),
                take_profit=Decimal(str(current_middle)),
                metadata={
                    "upper": current_upper,
                    "middle": current_middle,
                    "lower": current_lower
                }
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            "バンド内で推移",
            metadata={
                "upper": current_upper,
                "middle": current_middle,
                "lower": current_lower
            }
        )


class MACDStrategy(TradingStrategy):
    """
    MACD戦略
    
    MACDラインとシグナルラインのクロスでエントリーを判断します。
    ゼロライン上でのクロスを重視します。
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        min_periods = self.slow_period + self.signal_period + 1
        if len(ohlcv_data) < min_periods:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                "データ不足"
            )
        
        df = ohlcv_to_dataframe(ohlcv_data)
        indicators = TechnicalIndicators(df)
        
        macd_line, signal_line, histogram = indicators.macd(
            self.fast_period, self.slow_period, self.signal_period
        )
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        prev_hist = histogram.iloc[-2]
        
        entry_price = Decimal(str(df["close"].iloc[-1]))
        atr = indicators.atr(14).iloc[-1]
        
        # MACDラインがシグナルラインを上抜け（買いシグナル）
        if prev_macd <= prev_signal and current_macd > current_signal:
            # ゼロライン上でのクロスはより強いシグナル
            if current_macd > 0:
                signal_type = SignalType.STRONG_BUY
                confidence = 0.8
            else:
                signal_type = SignalType.BUY
                confidence = 0.6
            
            return self._create_signal(
                signal_type,
                currency_pair,
                confidence,
                f"MACDゴールデンクロス",
                entry_price=entry_price,
                stop_loss=entry_price - Decimal(str(atr * 2)),
                take_profit=entry_price + Decimal(str(atr * 4)),
                metadata={
                    "macd": current_macd,
                    "signal": current_signal,
                    "histogram": current_hist
                }
            )
        
        # MACDラインがシグナルラインを下抜け（売りシグナル）
        if prev_macd >= prev_signal and current_macd < current_signal:
            if current_macd < 0:
                signal_type = SignalType.STRONG_SELL
                confidence = 0.8
            else:
                signal_type = SignalType.SELL
                confidence = 0.6
            
            return self._create_signal(
                signal_type,
                currency_pair,
                confidence,
                f"MACDデッドクロス",
                entry_price=entry_price,
                stop_loss=entry_price + Decimal(str(atr * 2)),
                take_profit=entry_price - Decimal(str(atr * 4)),
                metadata={
                    "macd": current_macd,
                    "signal": current_signal,
                    "histogram": current_hist
                }
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            "シグナルなし",
            metadata={
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_hist
            }
        )


class CombinedStrategy(TradingStrategy):
    """
    複合戦略
    
    複数の戦略を組み合わせて、より信頼性の高いシグナルを生成します。
    複数の戦略が同じ方向を示している場合にのみエントリーします。
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        strategies: List[TradingStrategy] = None,
        min_agreement: int = 2
    ):
        super().__init__(config)
        self.strategies = strategies or [
            MovingAverageCrossStrategy(config),
            RSIMeanReversionStrategy(config),
            MACDStrategy(config),
        ]
        self.min_agreement = min_agreement
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        signals = []
        
        for strategy in self.strategies:
            signal = strategy.generate_signal(currency_pair, ohlcv_data, current_tick)
            signals.append(signal)
        
        # 買いシグナルと売りシグナルをカウント
        buy_signals = [s for s in signals if s.is_buy_signal]
        sell_signals = [s for s in signals if s.is_sell_signal]
        
        # 合意が取れた場合
        if len(buy_signals) >= self.min_agreement:
            # 平均信頼度を計算
            avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
            reasons = [s.reason for s in buy_signals]
            
            # 最も信頼度の高いシグナルからエントリー価格などを取得
            best_signal = max(buy_signals, key=lambda s: s.confidence)
            
            signal_type = SignalType.STRONG_BUY if len(buy_signals) >= 3 else SignalType.BUY
            
            return self._create_signal(
                signal_type,
                currency_pair,
                avg_confidence,
                f"複合シグナル（買い{len(buy_signals)}件）: " + "; ".join(reasons),
                entry_price=best_signal.entry_price,
                stop_loss=best_signal.stop_loss,
                take_profit=best_signal.take_profit,
                metadata={"individual_signals": [s.to_dict() for s in signals]}
            )
        
        if len(sell_signals) >= self.min_agreement:
            avg_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
            reasons = [s.reason for s in sell_signals]
            best_signal = max(sell_signals, key=lambda s: s.confidence)
            
            signal_type = SignalType.STRONG_SELL if len(sell_signals) >= 3 else SignalType.SELL
            
            return self._create_signal(
                signal_type,
                currency_pair,
                avg_confidence,
                f"複合シグナル（売り{len(sell_signals)}件）: " + "; ".join(reasons),
                entry_price=best_signal.entry_price,
                stop_loss=best_signal.stop_loss,
                take_profit=best_signal.take_profit,
                metadata={"individual_signals": [s.to_dict() for s in signals]}
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            "戦略間で合意なし",
            metadata={"individual_signals": [s.to_dict() for s in signals]}
        )


class TrendFollowingStrategy(TradingStrategy):
    """
    トレンドフォロー戦略
    
    ADXでトレンド強度を確認し、移動平均線の方向でエントリー方向を決定します。
    強いトレンドが確認された場合にのみエントリーします。
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        ma_period: int = 50
    ):
        super().__init__(config)
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.ma_period = ma_period
    
    def generate_signal(
        self,
        currency_pair: CurrencyPair,
        ohlcv_data: List[OHLCV],
        current_tick: Optional[Tick] = None
    ) -> TradingSignal:
        min_periods = max(self.adx_period * 2, self.ma_period) + 1
        if len(ohlcv_data) < min_periods:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                "データ不足"
            )
        
        df = ohlcv_to_dataframe(ohlcv_data)
        indicators = TechnicalIndicators(df)
        
        adx, plus_di, minus_di = indicators.adx(self.adx_period)
        ma = indicators.sma(self.ma_period)
        
        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]
        current_ma = ma.iloc[-1]
        current_close = df["close"].iloc[-1]
        
        entry_price = Decimal(str(current_close))
        atr = indicators.atr(14).iloc[-1]
        
        # トレンドが弱い場合はシグナルなし
        if current_adx < self.adx_threshold:
            return self._create_signal(
                SignalType.NEUTRAL,
                currency_pair,
                0.0,
                f"トレンドが弱い（ADX={current_adx:.1f}）",
                metadata={
                    "adx": current_adx,
                    "plus_di": current_plus_di,
                    "minus_di": current_minus_di
                }
            )
        
        # トレンド強度に基づく信頼度
        confidence = min((current_adx - self.adx_threshold) / 25 + 0.5, 1.0)
        
        # 上昇トレンド（+DI > -DI かつ 価格 > MA）
        if current_plus_di > current_minus_di and current_close > current_ma:
            signal_type = SignalType.STRONG_BUY if current_adx > 40 else SignalType.BUY
            
            return self._create_signal(
                signal_type,
                currency_pair,
                confidence,
                f"上昇トレンド確認（ADX={current_adx:.1f}、+DI>{int(current_plus_di)}）",
                entry_price=entry_price,
                stop_loss=entry_price - Decimal(str(atr * 2)),
                take_profit=entry_price + Decimal(str(atr * 4)),
                metadata={
                    "adx": current_adx,
                    "plus_di": current_plus_di,
                    "minus_di": current_minus_di
                }
            )
        
        # 下降トレンド（-DI > +DI かつ 価格 < MA）
        if current_minus_di > current_plus_di and current_close < current_ma:
            signal_type = SignalType.STRONG_SELL if current_adx > 40 else SignalType.SELL
            
            return self._create_signal(
                signal_type,
                currency_pair,
                confidence,
                f"下降トレンド確認（ADX={current_adx:.1f}、-DI>{int(current_minus_di)}）",
                entry_price=entry_price,
                stop_loss=entry_price + Decimal(str(atr * 2)),
                take_profit=entry_price - Decimal(str(atr * 4)),
                metadata={
                    "adx": current_adx,
                    "plus_di": current_plus_di,
                    "minus_di": current_minus_di
                }
            )
        
        return self._create_signal(
            SignalType.NEUTRAL,
            currency_pair,
            0.0,
            "トレンド方向不明確",
            metadata={
                "adx": current_adx,
                "plus_di": current_plus_di,
                "minus_di": current_minus_di
            }
        )


def get_strategy(strategy_name: str, config: StrategyConfig) -> TradingStrategy:
    """戦略名から戦略インスタンスを取得"""
    strategies = {
        "ma_cross": MovingAverageCrossStrategy(config),
        "rsi_reversal": RSIMeanReversionStrategy(config),
        "bollinger": BollingerBandStrategy(config),
        "macd": MACDStrategy(config),
        "trend_following": TrendFollowingStrategy(config),
        "combined": CombinedStrategy(config),
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")
    
    return strategies[strategy_name]


if __name__ == "__main__":
    # テスト
    import random
    from datetime import datetime, timedelta
    from config import StrategyConfig
    from api_client import CurrencyPair, OHLCV
    
    # テストデータ生成
    def generate_test_data(count: int = 200) -> List[OHLCV]:
        ohlcv_list = []
        base_price = 150.0
        
        for i in range(count):
            timestamp = datetime.now() - timedelta(hours=count - i)
            
            # トレンドを含むランダムウォーク
            trend = 0.01 if i > count // 2 else -0.01
            base_price += random.gauss(trend, 0.1)
            
            open_price = base_price + random.gauss(0, 0.05)
            high_price = base_price + abs(random.gauss(0, 0.1))
            low_price = base_price - abs(random.gauss(0, 0.1))
            close_price = base_price + random.gauss(0, 0.05)
            
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            ohlcv = OHLCV(
                currency_pair=CurrencyPair.USDJPY,
                timestamp=timestamp,
                open=Decimal(str(round(open_price, 3))),
                high=Decimal(str(round(high_price, 3))),
                low=Decimal(str(round(low_price, 3))),
                close=Decimal(str(round(close_price, 3))),
                volume=random.randint(1000, 10000)
            )
            ohlcv_list.append(ohlcv)
        
        return ohlcv_list
    
    # 戦略テスト
    config = StrategyConfig()
    test_data = generate_test_data()
    
    strategies = [
        MovingAverageCrossStrategy(config),
        RSIMeanReversionStrategy(config),
        BollingerBandStrategy(config),
        MACDStrategy(config),
        TrendFollowingStrategy(config),
        CombinedStrategy(config),
    ]
    
    print("=" * 60)
    print("戦略シグナルテスト")
    print("=" * 60)
    
    for strategy in strategies:
        signal = strategy.generate_signal(CurrencyPair.USDJPY, test_data)
        print(f"\n【{strategy.name}】")
        print(f"  シグナル: {signal.signal_type.value}")
        print(f"  信頼度: {signal.confidence:.2f}")
        print(f"  理由: {signal.reason}")
        if signal.entry_price:
            print(f"  エントリー: {signal.entry_price}")
            print(f"  損切り: {signal.stop_loss}")
            print(f"  利確: {signal.take_profit}")
