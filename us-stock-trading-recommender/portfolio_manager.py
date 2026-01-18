"""
保有株式を管理するモジュール
"""
from datetime import datetime
import logging
from data_fetcher import USStockDataFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioManager:
    """保有株式管理クラス"""
    
    def __init__(self, data_fetcher: USStockDataFetcher):
        """
        初期化
        
        Args:
            data_fetcher: データ取得オブジェクト
        """
        self.data_fetcher = data_fetcher
        self.portfolio: list[dict] = []
    
    def add_stock(self, ticker: str, shares: float, purchase_price_per_share: float, 
                  purchase_date: str | None = None) -> dict:
        """
        保有株式を追加
        
        Args:
            ticker: ティッカーシンボル
            shares: 保有株数
            purchase_price_per_share: 取得単価
            purchase_date: 取得日（YYYY-MM-DD形式、省略時は今日）
        
        Returns:
            dict: 追加された株式情報
        """
        try:
            # 現在価格を取得
            current_price = self.data_fetcher.get_current_price(ticker)
            
            purchase_date = purchase_date or datetime.now().strftime('%Y-%m-%d')
            purchase_value = purchase_price_per_share * shares
            current_value = current_price * shares
            profit_loss = current_value - purchase_value
            profit_loss_rate = (profit_loss / purchase_value) * 100 if purchase_value > 0 else 0
            
            stock_data = {
                'ticker': ticker.upper(),
                'shares': shares,
                'purchase_price_per_share': purchase_price_per_share,
                'purchase_date': purchase_date,
                'purchase_value': purchase_value,
                'current_price': current_price,
                'current_value': current_value,
                'profit_loss': profit_loss,
                'profit_loss_rate': profit_loss_rate,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 既存の銘柄を更新または新規追加
            existing_index = None
            for i, stock in enumerate(self.portfolio):
                if stock['ticker'] == ticker.upper():
                    existing_index = i
                    break
            
            if existing_index is not None:
                self.portfolio[existing_index] = stock_data
                logger.info(f"保有株式を更新しました: {ticker}")
            else:
                self.portfolio.append(stock_data)
                logger.info(f"保有株式を追加しました: {ticker}")
            
            return stock_data
        except Exception as e:
            logger.error(f"保有株式追加エラー ({ticker}): {str(e)}")
            raise
    
    def remove_stock(self, ticker: str) -> bool:
        """
        保有株式を削除
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            bool: 削除成功時True
        """
        ticker = ticker.upper()
        original_length = len(self.portfolio)
        self.portfolio = [s for s in self.portfolio if s['ticker'] != ticker]
        
        if len(self.portfolio) < original_length:
            logger.info(f"保有株式を削除しました: {ticker}")
            return True
        else:
            logger.warning(f"保有株式が見つかりませんでした: {ticker}")
            return False
    
    def update_prices(self) -> list[dict]:
        """
        全保有株式の現在価格を更新
        
        Returns:
            list[dict]: 更新された保有株式リスト
        """
        updated_stocks = []
        
        for stock in self.portfolio:
            try:
                ticker = stock['ticker']
                current_price = self.data_fetcher.get_current_price(ticker)
                
                stock['current_price'] = current_price
                stock['current_value'] = current_price * stock['shares']
                stock['profit_loss'] = stock['current_value'] - stock['purchase_value']
                stock['profit_loss_rate'] = (stock['profit_loss'] / stock['purchase_value']) * 100 if stock['purchase_value'] > 0 else 0
                stock['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                updated_stocks.append(stock)
                logger.info(f"価格を更新しました: {ticker} = ${current_price:.2f}")
            except Exception as e:
                logger.error(f"価格更新エラー ({stock['ticker']}): {str(e)}")
                # エラーが発生しても他の銘柄の更新は続行
                continue
        
        self.portfolio = updated_stocks
        return self.portfolio
    
    def get_portfolio(self) -> list[dict]:
        """
        保有株式リストを取得
        
        Returns:
            list[dict]: 保有株式リスト
        """
        return self.portfolio.copy()
    
    def get_stock(self, ticker: str) -> dict | None:
        """
        特定の銘柄情報を取得
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            dict: 銘柄情報、見つからない場合はNone
        """
        ticker = ticker.upper()
        for stock in self.portfolio:
            if stock['ticker'] == ticker:
                return stock.copy()
        return None
    
    def get_total_value(self) -> dict:
        """
        ポートフォリオ全体の価値を計算
        
        Returns:
            dict: 合計情報
        """
        total_purchase_value = sum(s['purchase_value'] for s in self.portfolio)
        total_current_value = sum(s['current_value'] for s in self.portfolio)
        total_profit_loss = total_current_value - total_purchase_value
        total_profit_loss_rate = (total_profit_loss / total_purchase_value) * 100 if total_purchase_value > 0 else 0
        
        return {
            'total_purchase_value': total_purchase_value,
            'total_current_value': total_current_value,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_rate': total_profit_loss_rate,
            'stock_count': len(self.portfolio)
        }
    
    def load_from_list(self, portfolio_list: list[dict]):
        """
        外部から保有株式リストを読み込み
        
        Args:
            portfolio_list: 保有株式リスト
        """
        self.portfolio = portfolio_list.copy()
        logger.info(f"保有株式リストを読み込みました: {len(self.portfolio)}件")
