"""
使用例とサンプルコード
"""
from data_fetcher import USStockDataFetcher
from portfolio_manager import PortfolioManager
from trading_signal import TradingSignalGenerator
from notification import NotificationManager
from fundamental_analyzer import FundamentalAnalyzer
from investment_philosophy import InvestmentPhilosophyAnalyzer
from philosophy_report import PhilosophyReportGenerator


def example_basic_usage():
    """基本的な使用例"""
    print("=== 基本的な使用例 ===\n")
    
    # 1. データ取得
    print("1. データ取得の例")
    fetcher = USStockDataFetcher()
    
    try:
        # 現在価格を取得
        price = fetcher.get_current_price("AAPL")
        print(f"AAPLの現在価格: ${price:.2f}\n")
        
        # テクニカル指標を取得
        indicators = fetcher.get_latest_indicators("AAPL")
        print("AAPLのテクニカル指標:")
        print(f"  RSI: {indicators.get('rsi', 'N/A')}")
        print(f"  MACD: {indicators.get('macd', 'N/A')}")
        print(f"  20日移動平均: ${indicators.get('ma_20', 0):.2f}\n")
    except Exception as e:
        print(f"エラー: {str(e)}\n")
    
    # 2. ポートフォリオ管理
    print("2. ポートフォリオ管理の例")
    portfolio_manager = PortfolioManager(fetcher)
    
    try:
        # 株式を追加
        stock = portfolio_manager.add_stock("AAPL", 10, 150.0, "2024-01-15")
        print(f"保有株式を追加: {stock['ticker']} - {stock['shares']}株")
        print(f"  現在価格: ${stock['current_price']:.2f}")
        print(f"  損益: ${stock['profit_loss']:.2f} ({stock['profit_loss_rate']:.2f}%)\n")
    except Exception as e:
        print(f"エラー: {str(e)}\n")
    
    # 3. 売買シグナル（テクニカル + ファンダメンタル統合）
    print("3. 売買シグナルの例（統合分析）")
    signal_generator = TradingSignalGenerator(fetcher)
    
    try:
        # 買いシグナルをチェック
        buy_signal = signal_generator.analyze_buy_signal("AAPL")
        if buy_signal:
            print(f"買いシグナル検出: {buy_signal['ticker']}")
            print(f"  理由: {buy_signal['reason']}")
            print(f"  信頼度: {buy_signal['confidence']:.1%}")
            
            # 賢人のアドバイスを表示
            if buy_signal.get('philosopher_advice'):
                print("  賢人のアドバイス:")
                for advice in buy_signal['philosopher_advice']:
                    print(f"    • {advice}")
            print()
        else:
            print("買いシグナルなし\n")
    except Exception as e:
        print(f"エラー: {str(e)}\n")
    
    # 4. 投資哲学分析
    print("4. 投資哲学分析の例")
    fundamental_analyzer = FundamentalAnalyzer()
    philosophy_analyzer = InvestmentPhilosophyAnalyzer(fundamental_analyzer)
    
    try:
        financial_data = fundamental_analyzer.get_financial_data("AAPL")
        indicators = fetcher.get_latest_indicators("AAPL")
        
        # 各投資哲学で分析
        graham_result = philosophy_analyzer.analyze_graham_value("AAPL", financial_data)
        print(f"グレアム（バリュー投資）: {graham_result['recommendation']} (信頼度: {graham_result['confidence']:.1%})")
        
        buffett_result = philosophy_analyzer.analyze_buffett_value("AAPL", financial_data)
        print(f"バフェット（長期投資）: {buffett_result['recommendation']} (信頼度: {buffett_result['confidence']:.1%})")
        
        can_slim_result = philosophy_analyzer.analyze_can_slim("AAPL", financial_data, indicators)
        print(f"オニール（CAN SLIM）: {can_slim_result['recommendation']} (信頼度: {can_slim_result['confidence']:.1%})")
        
        hirose_result = philosophy_analyzer.analyze_hirose_protocol("AAPL", financial_data)
        print(f"広瀬（プロトコル）: {hirose_result['recommendation']} (信頼度: {hirose_result['confidence']:.1%})\n")
    except Exception as e:
        print(f"エラー: {str(e)}\n")


def example_portfolio_analysis():
    """ポートフォリオ分析の例"""
    print("=== ポートフォリオ分析の例 ===\n")
    
    fetcher = USStockDataFetcher()
    portfolio_manager = PortfolioManager(fetcher)
    signal_generator = TradingSignalGenerator(fetcher)
    notification_manager = NotificationManager()
    
    # サンプルポートフォリオを作成
    sample_stocks = [
        ("AAPL", 10, 150.0),
        ("MSFT", 5, 300.0),
        ("GOOGL", 8, 120.0),
    ]
    
    print("サンプルポートフォリオを作成中...")
    for ticker, shares, price in sample_stocks:
        try:
            portfolio_manager.add_stock(ticker, shares, price)
            print(f"  {ticker}: {shares}株 @ ${price:.2f}")
        except Exception as e:
            print(f"  {ticker}: エラー - {str(e)}")
    
    print("\nポートフォリオサマリー:")
    summary = portfolio_manager.get_total_value()
    print(f"  保有銘柄数: {summary['stock_count']}")
    print(f"  合計取得価格: ${summary['total_purchase_value']:,.2f}")
    print(f"  合計現在価格: ${summary['total_current_value']:,.2f}")
    print(f"  合計損益: ${summary['total_profit_loss']:,.2f}")
    print(f"  合計損益率: {summary['total_profit_loss_rate']:.2f}%\n")
    
    # 売りシグナルをチェック
    print("売りシグナルをチェック中...")
    portfolio = portfolio_manager.get_portfolio()
    sell_signals = signal_generator.check_portfolio_sell_signals(portfolio)
    
    if sell_signals:
        print(f"売りシグナル: {len(sell_signals)}件検出\n")
        for signal in sell_signals:
            message = notification_manager.format_sell_recommendation(signal)
            print(message)
    else:
        print("売りシグナル: なし\n")


def example_philosophy_report():
    """投資哲学レポートの例"""
    print("=== 投資哲学レポートの例 ===\n")
    
    report_generator = PhilosophyReportGenerator()
    
    try:
        # 価格データを取得
        fetcher = USStockDataFetcher()
        indicators = fetcher.get_latest_indicators("AAPL")
        
        # レポートを生成
        report = report_generator.generate_full_report("AAPL", indicators)
        print(report)
    except Exception as e:
        print(f"エラー: {str(e)}\n")


if __name__ == '__main__':
    print("米国株売買タイミング推奨アプリ - 使用例\n")
    print("="*60 + "\n")
    
    # 基本的な使用例
    example_basic_usage()
    
    print("\n" + "="*60 + "\n")
    
    # ポートフォリオ分析の例
    # example_portfolio_analysis()  # コメントアウト（時間がかかるため）
    
    # 投資哲学レポートの例
    # example_philosophy_report()  # コメントアウト（時間がかかるため）