"""
Yahooファイナンスから日本株のデータを取得するモジュール
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List


class JapaneseStockDataFetcher:
    """日本株データ取得クラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def get_stock_data(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        指定されたティッカーシンボルの株価データを取得
        
        Args:
            ticker: ティッカーシンボル（例: "7203.T" はトヨタ自動車）
            period: 取得期間（"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"）
            interval: データ間隔（"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"）
        
        Returns:
            DataFrame: 株価データ（Open, High, Low, Close, Volume）
        """
        try:
            # 日本株のティッカーは .T を付ける必要がある
            if not ticker.endswith('.T'):
                ticker = f"{ticker}.T"
            
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)
            
            if data.empty:
                raise ValueError(f"データが取得できませんでした: {ticker}")
            
            return data
        except Exception as e:
            raise Exception(f"データ取得エラー ({ticker}): {str(e)}")
    
    def get_multiple_stocks(self, tickers: List[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        複数の銘柄のデータを一度に取得
        
        Args:
            tickers: ティッカーシンボルのリスト
            period: 取得期間
            interval: データ間隔
        
        Returns:
            DataFrame: 複数銘柄のデータ（マルチインデックス）
        """
        data_dict = {}
        for ticker in tickers:
            try:
                data = self.get_stock_data(ticker, period, interval)
                data_dict[ticker] = data
            except Exception as e:
                print(f"警告: {ticker} のデータ取得に失敗しました: {str(e)}")
                continue
        
        if not data_dict:
            raise ValueError("有効なデータが取得できませんでした")
        
        # 複数のDataFrameを結合
        combined = pd.concat(data_dict, axis=1)
        return combined
    
    def add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を追加
        
        Args:
            data: 株価データ
        
        Returns:
            DataFrame: テクニカル指標が追加されたデータ
        """
        df = data.copy()
        
        # 移動平均線
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA25'] = df['Close'].rolling(window=25).mean()
        df['MA75'] = df['Close'].rolling(window=75).mean()
        
        # RSI（相対力指数）
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # ボリンジャーバンド
        df['BB_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        # 出来高移動平均
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        
        return df
