"""
米国株売買タイミング推奨アプリ - メイン実行ファイル
"""
import argparse
import sys
import logging
from datetime import datetime

from data_fetcher import USStockDataFetcher
from spreadsheet_manager import SpreadsheetManager
from portfolio_manager import PortfolioManager
from trading_signal import TradingSignalGenerator
from notification import NotificationManager
from philosophy_report import PhilosophyReportGenerator
from utils import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockTradingRecommender:
    """米国株売買推奨アプリのメインクラス"""
    
    def __init__(self):
        """初期化"""
        config = load_config()
        
        self.data_fetcher = USStockDataFetcher()
        self.portfolio_manager = PortfolioManager(self.data_fetcher)
        self.signal_generator = TradingSignalGenerator(self.data_fetcher)
        self.notification_manager = NotificationManager()
        self.philosophy_report_generator = PhilosophyReportGenerator()
        
        # Google Spreadsheet連携（オプション）
        self.spreadsheet_manager = None
        if config['spreadsheet_id']:
            try:
                self.spreadsheet_manager = SpreadsheetManager(
                    config['spreadsheet_id'],
                    config['credentials_path']
                )
                # Spreadsheetから既存のポートフォリオを読み込み
                portfolio_data = self.spreadsheet_manager.load_portfolio()
                if portfolio_data:
                    self.portfolio_manager.load_from_list(portfolio_data)
                    logger.info(f"Spreadsheetからポートフォリオを読み込みました: {len(portfolio_data)}件")
            except Exception as e:
                logger.warning(f"Google Spreadsheet連携をスキップします: {str(e)}")
    
    def register_stock(self, ticker: str, shares: float, purchase_price: float, 
                      purchase_date: str = None):
        """
        保有株式を登録
        
        Args:
            ticker: ティッカーシンボル
            shares: 保有株数
            purchase_price: 取得単価
            purchase_date: 取得日（YYYY-MM-DD形式）
        """
        try:
            stock_data = self.portfolio_manager.add_stock(
                ticker, shares, purchase_price, purchase_date
            )
            
            print(f"\n保有株式を登録しました:")
            print(f"  銘柄: {stock_data['ticker']}")
            print(f"  保有株数: {stock_data['shares']}")
            print(f"  取得単価: ${stock_data['purchase_price_per_share']:.2f}")
            print(f"  現在価格: ${stock_data['current_price']:.2f}")
            print(f"  損益: ${stock_data['profit_loss']:.2f} ({stock_data['profit_loss_rate']:.2f}%)")
            
            # Spreadsheetに保存
            if self.spreadsheet_manager:
                portfolio = self.portfolio_manager.get_portfolio()
                self._save_portfolio_to_spreadsheet(portfolio)
            
        except Exception as e:
            logger.error(f"株式登録エラー: {str(e)}")
            print(f"エラー: {str(e)}")
            sys.exit(1)
    
    def update_prices(self):
        """全保有株式の価格を更新"""
        try:
            logger.info("価格更新を開始します...")
            updated_portfolio = self.portfolio_manager.update_prices()
            
            print(f"\n価格更新が完了しました: {len(updated_portfolio)}銘柄")
            
            # Spreadsheetに保存
            if self.spreadsheet_manager:
                self._save_portfolio_to_spreadsheet(updated_portfolio)
            
        except Exception as e:
            logger.error(f"価格更新エラー: {str(e)}")
            print(f"エラー: {str(e)}")
            sys.exit(1)
    
    def check_signals(self, watch_list: list[str] | None = None):
        """
        売買シグナルをチェック
        
        Args:
            watch_list: 買いシグナルをチェックする銘柄リスト（省略時は保有銘柄のみ）
        """
        try:
            logger.info("売買シグナルをチェックします...")
            
            # 価格を更新
            self.update_prices()
            
            # 売りシグナルチェック（保有株式）
            portfolio = self.portfolio_manager.get_portfolio()
            sell_recommendations = self.signal_generator.check_portfolio_sell_signals(portfolio)
            
            # 買いシグナルチェック
            buy_recommendations = []
            if watch_list:
                buy_recommendations = self.signal_generator.check_buy_signals(watch_list)
            
            # 通知を送信
            output_file = f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.notification_manager.send_notifications(
                sell_recommendations,
                buy_recommendations,
                output_file
            )
            
            # Spreadsheetに保存
            if self.spreadsheet_manager:
                for rec in sell_recommendations + buy_recommendations:
                    self.spreadsheet_manager.save_recommendation(rec)
            
            # ポートフォリオサマリーを表示
            if portfolio:
                summary = self.portfolio_manager.get_total_value()
                summary_message = self.notification_manager.format_portfolio_summary(summary)
                print(summary_message)
            
        except Exception as e:
            logger.error(f"シグナルチェックエラー: {str(e)}")
            print(f"エラー: {str(e)}")
            sys.exit(1)
    
    def show_portfolio(self):
        """保有株式一覧を表示"""
        portfolio = self.portfolio_manager.get_portfolio()
        
        if not portfolio:
            print("\n保有株式がありません。")
            return
        
        print("\n" + "="*80)
        print("保有株式一覧")
        print("="*80)
        print(f"{'銘柄':<10} {'株数':>10} {'取得単価':>12} {'現在価格':>12} {'損益':>12} {'損益率':>10}")
        print("-"*80)
        
        for stock in portfolio:
            print(f"{stock['ticker']:<10} "
                  f"{stock['shares']:>10.2f} "
                  f"${stock['purchase_price_per_share']:>11.2f} "
                  f"${stock['current_price']:>11.2f} "
                  f"${stock['profit_loss']:>11.2f} "
                  f"{stock['profit_loss_rate']:>9.2f}%")
        
        summary = self.portfolio_manager.get_total_value()
        print("-"*80)
        print(f"{'合計':<10} {'':>10} {'':>12} "
              f"${summary['total_current_value']:>11.2f} "
              f"${summary['total_profit_loss']:>11.2f} "
              f"{summary['total_profit_loss_rate']:>9.2f}%")
        print("="*80)
    
    def generate_philosophy_report(self, ticker: str):
        """
        投資哲学レポートを生成
        
        Args:
            ticker: ティッカーシンボル
        """
        try:
            # 価格データを取得
            indicators = self.data_fetcher.get_latest_indicators(ticker)
            
            # レポートを生成
            report = self.philosophy_report_generator.generate_full_report(ticker, indicators)
            
            print(report)
            
            # ファイルに保存
            output_file = f"philosophy_report_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"\nレポートを保存しました: {output_file}")
            
        except Exception as e:
            logger.error(f"レポート生成エラー: {str(e)}")
            print(f"エラー: {str(e)}")
            sys.exit(1)
    
    def _save_portfolio_to_spreadsheet(self, portfolio: list[dict]):
        """ポートフォリオをSpreadsheetに保存"""
        try:
            # Spreadsheet用の形式に変換
            spreadsheet_data = []
            for stock in portfolio:
                spreadsheet_data.append({
                    'ticker': stock['ticker'],
                    'shares': stock['shares'],
                    'purchase_price_per_share': stock['purchase_price_per_share'],
                    'purchase_date': stock['purchase_date'],
                    'current_price': stock['current_price'],
                    'current_value': stock['current_value'],
                    'profit_loss': stock['profit_loss'],
                    'profit_loss_rate': stock['profit_loss_rate'],
                    'last_updated': stock['last_updated']
                })
            
            self.spreadsheet_manager.save_portfolio(spreadsheet_data)
        except Exception as e:
            logger.warning(f"Spreadsheet保存エラー（処理は続行します）: {str(e)}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='米国株売買タイミング推奨アプリ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 保有株式を登録
  python main.py --register AAPL 10 150.0
  
  # 価格を更新
  python main.py --update
  
  # 売買シグナルをチェック
  python main.py --check
  
  # 買いシグナルをチェック（特定銘柄）
  python main.py --check --watch AAPL MSFT GOOGL
  
  # 保有株式一覧を表示
  python main.py --portfolio
        """
    )
    
    parser.add_argument('--register', nargs=3, metavar=('TICKER', 'SHARES', 'PRICE'),
                       help='保有株式を登録（ティッカー、株数、取得単価）')
    parser.add_argument('--purchase-date', metavar='DATE',
                       help='取得日（YYYY-MM-DD形式、--registerと併用）')
    parser.add_argument('--update', action='store_true',
                       help='全保有株式の価格を更新')
    parser.add_argument('--check', action='store_true',
                       help='売買シグナルをチェック')
    parser.add_argument('--watch', nargs='+', metavar='TICKER',
                       help='買いシグナルをチェックする銘柄リスト')
    parser.add_argument('--portfolio', action='store_true',
                       help='保有株式一覧を表示')
    parser.add_argument('--daily-check', action='store_true',
                       help='定期実行用（価格更新＋シグナルチェック）')
    parser.add_argument('--philosophy-report', metavar='TICKER',
                       help='投資哲学レポートを生成（ティッカーシンボル）')
    
    args = parser.parse_args()
    
    # 引数が何もない場合はヘルプを表示
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    app = StockTradingRecommender()
    
    try:
        if args.register:
            ticker, shares, price = args.register
            app.register_stock(
                ticker,
                float(shares),
                float(price),
                args.purchase_date
            )
        
        elif args.update:
            app.update_prices()
        
        elif args.check:
            watch_list = args.watch if args.watch else None
            app.check_signals(watch_list)
        
        elif args.portfolio:
            app.show_portfolio()
        
        elif args.daily_check:
            # 定期実行: 価格更新とシグナルチェック
            app.check_signals()
        
        elif args.philosophy_report:
            # 投資哲学レポートを生成
            app.generate_philosophy_report(args.philosophy_report)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}", exc_info=True)
        print(f"エラー: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
