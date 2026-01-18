"""
使用例スクリプト
"""
from data_fetcher import JapaneseStockDataFetcher
from backtester import Backtester
from strategy_optimizer import StrategyOptimizer
import pandas as pd


def example_basic_backtest():
    """基本的なバックテストの例"""
    print("=== 基本的なバックテスト例 ===")
    
    # データ取得
    fetcher = JapaneseStockDataFetcher()
    ticker = "7203"  # トヨタ自動車
    print(f"\n{ticker}のデータを取得中...")
    
    data = fetcher.get_stock_data(ticker, period="1y")
    data = fetcher.add_technical_indicators(data)
    
    print(f"データ取得成功: {len(data)}件")
    print(f"期間: {data.index[0]} ～ {data.index[-1]}")
    
    # 移動平均を計算
    data['MA5'] = data['Close'].rolling(window=5).mean()
    data['MA25'] = data['Close'].rolling(window=25).mean()
    
    # 買い・売り条件
    def buy_condition(row):
        if pd.isna(row['MA5']) or pd.isna(row['MA25']):
            return False
        return row['MA5'] > row['MA25']
    
    def sell_condition(row):
        if pd.isna(row['MA5']) or pd.isna(row['MA25']):
            return False
        return row['MA5'] < row['MA25']
    
    # バックテスト実行
    backtester = Backtester(initial_capital=1000000)
    results = backtester.run_backtest(data, buy_condition, sell_condition)
    
    # 結果表示
    print("\n=== バックテスト結果 ===")
    print(f"総リターン: ¥{results['total_return']:,.0f} ({results['total_return_pct']:.2f}%)")
    print(f"取引回数: {results['num_trades']}回")
    print(f"勝率: {results['win_rate']:.1f}%")
    print(f"平均利益: ¥{results['avg_profit']:,.0f}")
    print(f"平均損失: ¥{results['avg_loss']:,.0f}")
    print(f"プロフィットファクター: {results['profit_factor']:.2f}")
    print(f"最大ドローダウン: {results['max_drawdown']:.2f}%")
    print(f"シャープレシオ: {results['sharpe_ratio']:.2f}")


def example_optimization():
    """戦略最適化の例"""
    print("\n=== 戦略最適化例 ===")
    
    # データ取得
    fetcher = JapaneseStockDataFetcher()
    ticker = "7203"
    print(f"\n{ticker}のデータを取得中...")
    
    data = fetcher.get_stock_data(ticker, period="1y")
    data = fetcher.add_technical_indicators(data)
    
    # 最適化実行（範囲を狭めて実行時間を短縮）
    optimizer = StrategyOptimizer(initial_capital=1000000)
    print("\n移動平均クロス戦略の最適化を実行中...")
    
    results = optimizer.optimize_ma_cross_strategy(
        data,
        short_ma_range=(5, 15),
        long_ma_range=(20, 40),
        rsi_low_range=(20, 30),
        rsi_high_range=(70, 80)
    )
    
    if not results.empty:
        print(f"\n最適化完了: {len(results)}件の利益が出る戦略が見つかりました")
        print("\n=== トップ5の戦略 ===")
        print(results.head(5).to_string())
        
        # 利益条件分析
        analysis = optimizer.analyze_profitable_conditions(results)
        print("\n=== 利益条件分析 ===")
        print(f"テストした戦略数: {analysis['total_tested_strategies']}")
        print(f"利益が出た戦略数: {analysis['total_profitable_strategies']}")
        
        if analysis['best_strategy']:
            print("\n最良の戦略:")
            best = analysis['best_strategy']
            print(f"  短期MA: {best.get('short_ma', 'N/A')}")
            print(f"  長期MA: {best.get('long_ma', 'N/A')}")
            print(f"  総リターン: {best['total_return_pct']:.2f}%")
            print(f"  勝率: {best['win_rate']:.1f}%")
    else:
        print("利益が出る戦略が見つかりませんでした")


if __name__ == "__main__":
    try:
        example_basic_backtest()
        # example_optimization()  # コメントアウト（実行時間がかかるため）
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
