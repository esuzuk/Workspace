"""
FX自動売買システム - テクニカル指標モジュール

各種テクニカル指標の計算を行います。
numpy/pandasを使用した高速な計算を実現しています。
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from api_client import OHLCV


def ohlcv_to_dataframe(ohlcv_list: List[OHLCV]) -> pd.DataFrame:
    """OHLCVリストをDataFrameに変換"""
    data = {
        "timestamp": [o.timestamp for o in ohlcv_list],
        "open": [float(o.open) for o in ohlcv_list],
        "high": [float(o.high) for o in ohlcv_list],
        "low": [float(o.low) for o in ohlcv_list],
        "close": [float(o.close) for o in ohlcv_list],
        "volume": [o.volume for o in ohlcv_list],
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


@dataclass
class IndicatorResult:
    """テクニカル指標の計算結果"""
    name: str
    values: pd.Series
    signal: Optional[str] = None  # "buy", "sell", None


class TechnicalIndicators:
    """テクニカル指標計算クラス"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: OHLCV DataFrameopen, high, low, close, volumeカラムを含む）
        """
        self.df = df.copy()
        self._validate_dataframe()
    
    def _validate_dataframe(self) -> None:
        """DataFrameの検証"""
        required_columns = ["open", "high", "low", "close"]
        for col in required_columns:
            if col not in self.df.columns:
                raise ValueError(f"必須カラム '{col}' が見つかりません")
    
    # ==================== 移動平均 ====================
    
    def sma(self, period: int, column: str = "close") -> pd.Series:
        """
        単純移動平均（SMA: Simple Moving Average）
        
        Args:
            period: 期間
            column: 計算対象カラム
        
        Returns:
            SMA系列
        """
        return self.df[column].rolling(window=period).mean()
    
    def ema(self, period: int, column: str = "close") -> pd.Series:
        """
        指数移動平均（EMA: Exponential Moving Average）
        
        Args:
            period: 期間
            column: 計算対象カラム
        
        Returns:
            EMA系列
        """
        return self.df[column].ewm(span=period, adjust=False).mean()
    
    def wma(self, period: int, column: str = "close") -> pd.Series:
        """
        加重移動平均（WMA: Weighted Moving Average）
        
        Args:
            period: 期間
            column: 計算対象カラム
        
        Returns:
            WMA系列
        """
        weights = np.arange(1, period + 1)
        return self.df[column].rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
    
    # ==================== トレンド指標 ====================
    
    def macd(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD（Moving Average Convergence Divergence）
        
        Args:
            fast_period: 短期EMA期間
            slow_period: 長期EMA期間
            signal_period: シグナル線期間
        
        Returns:
            (MACD線, シグナル線, ヒストグラム)
        """
        ema_fast = self.ema(fast_period)
        ema_slow = self.ema(slow_period)
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def adx(self, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        ADX（Average Directional Index）- トレンド強度指標
        
        Args:
            period: 期間
        
        Returns:
            (ADX, +DI, -DI)
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    # ==================== オシレーター ====================
    
    def rsi(self, period: int = 14) -> pd.Series:
        """
        RSI（Relative Strength Index）
        
        Args:
            period: 期間
        
        Returns:
            RSI系列（0-100）
        """
        delta = self.df["close"].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        ストキャスティクス
        
        Args:
            k_period: %K期間
            d_period: %D期間
        
        Returns:
            (%K, %D)
        """
        low_min = self.df["low"].rolling(window=k_period).min()
        high_max = self.df["high"].rolling(window=k_period).max()
        
        stoch_k = 100 * (self.df["close"] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()
        
        return stoch_k, stoch_d
    
    def cci(self, period: int = 20) -> pd.Series:
        """
        CCI（Commodity Channel Index）
        
        Args:
            period: 期間
        
        Returns:
            CCI系列
        """
        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        tp_sma = tp.rolling(window=period).mean()
        tp_mad = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        
        cci = (tp - tp_sma) / (0.015 * tp_mad)
        return cci
    
    def williams_r(self, period: int = 14) -> pd.Series:
        """
        ウィリアムズ%R
        
        Args:
            period: 期間
        
        Returns:
            Williams %R系列（-100〜0）
        """
        high_max = self.df["high"].rolling(window=period).max()
        low_min = self.df["low"].rolling(window=period).min()
        
        wr = -100 * (high_max - self.df["close"]) / (high_max - low_min)
        return wr
    
    # ==================== ボラティリティ指標 ====================
    
    def bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        ボリンジャーバンド
        
        Args:
            period: 期間
            std_dev: 標準偏差の倍率
        
        Returns:
            (上バンド, 中央線, 下バンド)
        """
        middle = self.sma(period)
        std = self.df["close"].rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def atr(self, period: int = 14) -> pd.Series:
        """
        ATR（Average True Range）- ボラティリティ指標
        
        Args:
            period: 期間
        
        Returns:
            ATR系列
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def keltner_channel(
        self,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        ケルトナーチャネル
        
        Args:
            ema_period: EMA期間
            atr_period: ATR期間
            multiplier: ATR倍率
        
        Returns:
            (上バンド, 中央線, 下バンド)
        """
        middle = self.ema(ema_period)
        atr_values = self.atr(atr_period)
        
        upper = middle + (atr_values * multiplier)
        lower = middle - (atr_values * multiplier)
        
        return upper, middle, lower
    
    # ==================== 出来高指標 ====================
    
    def obv(self) -> pd.Series:
        """
        OBV（On Balance Volume）
        
        Returns:
            OBV系列
        """
        if "volume" not in self.df.columns:
            raise ValueError("volumeカラムが必要です")
        
        close_diff = self.df["close"].diff()
        direction = np.where(close_diff > 0, 1, np.where(close_diff < 0, -1, 0))
        
        obv = (self.df["volume"] * direction).cumsum()
        return pd.Series(obv, index=self.df.index)
    
    def vwap(self) -> pd.Series:
        """
        VWAP（Volume Weighted Average Price）
        
        Returns:
            VWAP系列
        """
        if "volume" not in self.df.columns:
            raise ValueError("volumeカラムが必要です")
        
        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        vwap = (tp * self.df["volume"]).cumsum() / self.df["volume"].cumsum()
        
        return vwap
    
    # ==================== サポート・レジスタンス ====================
    
    def pivot_points(self) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        ピボットポイント
        
        Returns:
            (ピボット, R1, R2, S1, S2)
        """
        pivot = (self.df["high"].shift(1) + self.df["low"].shift(1) + self.df["close"].shift(1)) / 3
        
        r1 = 2 * pivot - self.df["low"].shift(1)
        s1 = 2 * pivot - self.df["high"].shift(1)
        r2 = pivot + (self.df["high"].shift(1) - self.df["low"].shift(1))
        s2 = pivot - (self.df["high"].shift(1) - self.df["low"].shift(1))
        
        return pivot, r1, r2, s1, s2
    
    # ==================== パターン認識 ====================
    
    def is_golden_cross(self, short_period: int = 20, long_period: int = 50) -> pd.Series:
        """
        ゴールデンクロスを検出
        
        Args:
            short_period: 短期MA期間
            long_period: 長期MA期間
        
        Returns:
            ゴールデンクロス発生フラグ
        """
        short_ma = self.sma(short_period)
        long_ma = self.sma(long_period)
        
        # 前日は短期MA < 長期MA、当日は短期MA > 長期MA
        golden_cross = (short_ma.shift(1) < long_ma.shift(1)) & (short_ma > long_ma)
        
        return golden_cross
    
    def is_dead_cross(self, short_period: int = 20, long_period: int = 50) -> pd.Series:
        """
        デッドクロスを検出
        
        Args:
            short_period: 短期MA期間
            long_period: 長期MA期間
        
        Returns:
            デッドクロス発生フラグ
        """
        short_ma = self.sma(short_period)
        long_ma = self.sma(long_period)
        
        # 前日は短期MA > 長期MA、当日は短期MA < 長期MA
        dead_cross = (short_ma.shift(1) > long_ma.shift(1)) & (short_ma < long_ma)
        
        return dead_cross
    
    def is_bullish_divergence(self, rsi_period: int = 14, lookback: int = 5) -> pd.Series:
        """
        ブリッシュダイバージェンス（強気の乖離）を検出
        価格は安値更新、RSIは安値更新せず → 上昇転換のサイン
        
        Args:
            rsi_period: RSI期間
            lookback: 比較期間
        
        Returns:
            ブリッシュダイバージェンス発生フラグ
        """
        rsi = self.rsi(rsi_period)
        price = self.df["close"]
        
        price_lower_low = price < price.rolling(window=lookback).min().shift(1)
        rsi_higher_low = rsi > rsi.rolling(window=lookback).min().shift(1)
        
        return price_lower_low & rsi_higher_low
    
    def is_bearish_divergence(self, rsi_period: int = 14, lookback: int = 5) -> pd.Series:
        """
        ベアリッシュダイバージェンス（弱気の乖離）を検出
        価格は高値更新、RSIは高値更新せず → 下落転換のサイン
        
        Args:
            rsi_period: RSI期間
            lookback: 比較期間
        
        Returns:
            ベアリッシュダイバージェンス発生フラグ
        """
        rsi = self.rsi(rsi_period)
        price = self.df["close"]
        
        price_higher_high = price > price.rolling(window=lookback).max().shift(1)
        rsi_lower_high = rsi < rsi.rolling(window=lookback).max().shift(1)
        
        return price_higher_high & rsi_lower_high


def calculate_all_indicators(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    全ての主要テクニカル指標を計算してDataFrameに追加
    
    Args:
        df: OHLCV DataFrame
        config: 指標のパラメータ設定（オプション）
    
    Returns:
        指標が追加されたDataFrame
    """
    if config is None:
        config = {}
    
    indicators = TechnicalIndicators(df)
    result = df.copy()
    
    # 移動平均
    result["sma_20"] = indicators.sma(config.get("sma_short", 20))
    result["sma_50"] = indicators.sma(config.get("sma_long", 50))
    result["ema_21"] = indicators.ema(config.get("ema_period", 21))
    
    # MACD
    macd, signal, hist = indicators.macd(
        config.get("macd_fast", 12),
        config.get("macd_slow", 26),
        config.get("macd_signal", 9)
    )
    result["macd"] = macd
    result["macd_signal"] = signal
    result["macd_hist"] = hist
    
    # RSI
    result["rsi"] = indicators.rsi(config.get("rsi_period", 14))
    
    # ストキャスティクス
    stoch_k, stoch_d = indicators.stochastic(
        config.get("stoch_k", 14),
        config.get("stoch_d", 3)
    )
    result["stoch_k"] = stoch_k
    result["stoch_d"] = stoch_d
    
    # ボリンジャーバンド
    bb_upper, bb_middle, bb_lower = indicators.bollinger_bands(
        config.get("bb_period", 20),
        config.get("bb_std", 2.0)
    )
    result["bb_upper"] = bb_upper
    result["bb_middle"] = bb_middle
    result["bb_lower"] = bb_lower
    
    # ATR
    result["atr"] = indicators.atr(config.get("atr_period", 14))
    
    # ADX
    adx, plus_di, minus_di = indicators.adx(config.get("adx_period", 14))
    result["adx"] = adx
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di
    
    # パターン検出
    result["golden_cross"] = indicators.is_golden_cross()
    result["dead_cross"] = indicators.is_dead_cross()
    
    return result


if __name__ == "__main__":
    # テスト用のサンプルデータ生成
    import random
    from datetime import datetime, timedelta
    
    # ダミーデータ作成
    dates = [datetime.now() - timedelta(hours=i) for i in range(200, 0, -1)]
    base_price = 150.0
    prices = []
    
    for i in range(200):
        base_price += random.gauss(0, 0.1)
        prices.append({
            "open": base_price + random.gauss(0, 0.05),
            "high": base_price + abs(random.gauss(0, 0.1)),
            "low": base_price - abs(random.gauss(0, 0.1)),
            "close": base_price + random.gauss(0, 0.05),
            "volume": random.randint(1000, 10000)
        })
    
    df = pd.DataFrame(prices, index=dates)
    
    # 指標計算
    result = calculate_all_indicators(df)
    
    print("計算された指標:")
    print(result.tail(10))
    
    print("\n最新の指標値:")
    latest = result.iloc[-1]
    print(f"  SMA(20): {latest['sma_20']:.3f}")
    print(f"  SMA(50): {latest['sma_50']:.3f}")
    print(f"  RSI(14): {latest['rsi']:.1f}")
    print(f"  MACD: {latest['macd']:.4f}")
    print(f"  ATR(14): {latest['atr']:.4f}")
    print(f"  ADX(14): {latest['adx']:.1f}")
