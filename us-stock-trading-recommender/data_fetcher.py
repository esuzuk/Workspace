"""
Yahoo Financeから米国株のデータを取得するモジュール
"""
import yfinance as yf
import pandas as pd
import time
import logging
import numpy as np
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()


class USStockDataFetcher:
    """米国株データ取得クラス"""
    
    def __init__(self):
        """
        初期化
        環境変数から設定を読み込む
        """
        # リトライ設定
        self.max_retries = int(os.getenv('DATA_FETCHER_MAX_RETRIES', '3'))
        
        # レート制限対策の待機時間（秒）
        self.rate_limit_delay = float(os.getenv('DATA_FETCHER_RATE_LIMIT_DELAY', '0.5'))
        
        # リトライ時の初期待機時間（秒）
        self.retry_initial_delay = float(os.getenv('DATA_FETCHER_RETRY_INITIAL_DELAY', '1.0'))
        
        # ログレベル
        log_level = os.getenv('DATA_FETCHER_LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # データ取得期間のデフォルト
        self.default_period = os.getenv('DATA_FETCHER_DEFAULT_PERIOD', '6mo')
        
        logger.info(f"USStockDataFetcher初期化完了 - リトライ: {self.max_retries}回, レート制限待機: {self.rate_limit_delay}秒")
    
    def get_stock_data(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        指定されたティッカーシンボルの株価データを取得
        
        Args:
            ticker: ティッカーシンボル（例: "AAPL", "MSFT"）
            period: 取得期間（"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"）
            interval: データ間隔（"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"）
        
        Returns:
            DataFrame: 株価データ（Open, High, Low, Close, Volume）
        """
        try:
            logger.info(f"データ取得中: {ticker}")
            stock = yf.Ticker(ticker)
            
            # リトライロジック
            for attempt in range(self.max_retries):
                try:
                    data = stock.history(period=period, interval=interval)
                    
                    if data.empty:
                        if attempt < self.max_retries - 1:
                            delay = self.retry_initial_delay * (attempt + 1)
                            logger.warning(f"データが空です。リトライ中... ({ticker}, 試行 {attempt + 1}/{self.max_retries}, {delay}秒待機)")
                            time.sleep(delay)  # 指数バックオフ
                            continue
                        else:
                            raise ValueError(f"データが取得できませんでした: {ticker}")
                    
                    # レート制限対策
                    time.sleep(self.rate_limit_delay)
                    
                    return data
                except Exception as retry_error:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_initial_delay * (attempt + 1)
                        logger.warning(f"データ取得エラー。リトライ中... ({ticker}, 試行 {attempt + 1}/{self.max_retries}, {delay}秒待機): {str(retry_error)}")
                        time.sleep(delay)
                        continue
                    else:
                        raise
            
            # ここには到達しないはずだが、念のため
            raise ValueError(f"データ取得に失敗しました: {ticker}")
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"データ取得エラー ({ticker}): {str(e)}")
            raise Exception(f"データ取得エラー ({ticker}): {str(e)}")
    
    def get_current_price(self, ticker: str) -> float:
        """
        現在の株価を取得
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            float: 現在の株価
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 複数のキーを試行
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose'))
            
            if current_price is None:
                # フォールバック: 最新の履歴データから取得
                try:
                    data = self.get_stock_data(ticker, period="5d", interval="1d")
                    if not data.empty:
                        current_price = data['Close'].iloc[-1]
                    else:
                        raise ValueError(f"現在価格が取得できませんでした: {ticker}")
                except Exception as fallback_error:
                    logger.warning(f"フォールバック方法も失敗 ({ticker}): {str(fallback_error)}")
                    raise ValueError(f"現在価格が取得できませんでした: {ticker}")
            
            time.sleep(self.rate_limit_delay)
            return float(current_price)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"現在価格取得エラー ({ticker}): {str(e)}")
            raise
    
    def get_stock_info(self, ticker: str) -> dict:
        """
        銘柄の基本情報を取得
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            dict: 銘柄情報
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            time.sleep(self.rate_limit_delay)
            return info
        except Exception as e:
            logger.error(f"銘柄情報取得エラー ({ticker}): {str(e)}")
            raise
    
    def add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を追加
        
        Args:
            data: 株価データ
        
        Returns:
            DataFrame: テクニカル指標が追加されたデータ
        """
        try:
            import pandas_ta as ta
            
            df = data.copy()
            
            # 移動平均線
            df['MA_20'] = ta.sma(df['Close'], length=20)
            df['MA_50'] = ta.sma(df['Close'], length=50)
            df['MA_200'] = ta.sma(df['Close'], length=200)
            
            # RSI（相対力指数）
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # MACD
            macd = ta.macd(df['Close'])
            if macd is not None and not macd.empty:
                df = pd.concat([df, macd], axis=1)
            
            # ボリンジャーバンド
            bbands = ta.bbands(df['Close'], length=20)
            if bbands is not None and not bbands.empty:
                df = pd.concat([df, bbands], axis=1)
            
            # 出来高移動平均
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            
            return df
        except ImportError:
            logger.warning("pandas_taが利用できないため、簡易版のテクニカル指標を計算します")
            return self._add_technical_indicators_simple(data)
        except Exception as e:
            logger.error(f"テクニカル指標計算エラー: {str(e)}")
            return self._add_technical_indicators_simple(data)
    
    def _add_technical_indicators_simple(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        簡易版テクニカル指標（pandas_taが使えない場合）
        """
        df = data.copy()
        
        # 移動平均線
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['MA_50'] = df['Close'].rolling(window=50).mean()
        df['MA_200'] = df['Close'].rolling(window=200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        # ゼロ除算を防ぐ
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)  # NaNの場合は50（中立）を設定
        
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
    
    def get_latest_indicators(self, ticker: str) -> dict:
        """
        最新のテクニカル指標を取得
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            dict: 最新のテクニカル指標
        """
        try:
            data = self.get_stock_data(ticker, period=self.default_period, interval="1d")
            
            if data.empty:
                raise ValueError(f"データが空です: {ticker}")
            
            data_with_indicators = self.add_technical_indicators(data)
            
            if data_with_indicators.empty:
                raise ValueError(f"指標計算後のデータが空です: {ticker}")
            
            latest = data_with_indicators.iloc[-1]
            
            # ボリンジャーバンドのキー名を安全に取得
            bb_upper = None
            bb_lower = None
            
            # pandas_taのバージョンによって異なるキー名に対応
            possible_bb_upper_keys = ['BBU_20_2.0', 'BB_upper', 'BBUPPER_20_2.0']
            possible_bb_lower_keys = ['BBL_20_2.0', 'BB_lower', 'BBLOWER_20_2.0']
            
            for key in possible_bb_upper_keys:
                if key in latest.index:
                    value = latest[key]
                    if pd.notna(value):
                        bb_upper = float(value)
                        break
            
            for key in possible_bb_lower_keys:
                if key in latest.index:
                    value = latest[key]
                    if pd.notna(value):
                        bb_lower = float(value)
                        break
            
            # フォールバック: 簡易版のボリンジャーバンドを使用
            if bb_upper is None and 'BB_upper' in latest.index:
                value = latest['BB_upper']
                if pd.notna(value):
                    bb_upper = float(value)
            
            if bb_lower is None and 'BB_lower' in latest.index:
                value = latest['BB_lower']
                if pd.notna(value):
                    bb_lower = float(value)
            
            indicators = {
                'current_price': float(latest['Close']),
                'ma_20': float(latest['MA_20']) if pd.notna(latest.get('MA_20')) else None,
                'ma_50': float(latest['MA_50']) if pd.notna(latest.get('MA_50')) else None,
                'ma_200': float(latest['MA_200']) if pd.notna(latest.get('MA_200')) else None,
                'rsi': float(latest['RSI']) if pd.notna(latest.get('RSI')) else None,
                'macd': float(latest['MACD']) if pd.notna(latest.get('MACD')) else None,
                'macd_signal': float(latest['MACD_signal']) if pd.notna(latest.get('MACD_signal')) else None,
                'macd_hist': float(latest['MACD_hist']) if pd.notna(latest.get('MACD_hist')) else None,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'volume': float(latest['Volume']) if pd.notna(latest.get('Volume')) else 0.0,
                'volume_ma': float(latest['Volume_MA']) if pd.notna(latest.get('Volume_MA')) else None,
            }
            
            return indicators
        except KeyError as e:
            logger.error(f"必要な列が見つかりません ({ticker}): {str(e)}")
            raise ValueError(f"データ構造エラー ({ticker}): {str(e)}")
        except Exception as e:
            logger.error(f"指標取得エラー ({ticker}): {str(e)}")
            raise
