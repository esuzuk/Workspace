"""
戦略最適化と利益条件分析モジュール
"""
import pandas as pd
import numpy as np
from itertools import product
from typing import Dict, List, Tuple, Optional
from backtester import Backtester
import warnings
warnings.filterwarnings('ignore')


class StrategyOptimizer:
    """戦略最適化クラス"""
    
    def __init__(self, initial_capital: float = 1000000):
        """
        初期化
        
        Args:
            initial_capital: 初期資金
        """
        self.backtester = Backtester(initial_capital)
        self.initial_capital = initial_capital
    
    def optimize_ma_cross_strategy(
        self,
        data: pd.DataFrame,
        short_ma_range: Tuple[int, int] = (3, 20),
        long_ma_range: Tuple[int, int] = (20, 100),
        rsi_low_range: Tuple[int, int] = (20, 40),
        rsi_high_range: Tuple[int, int] = (60, 80)
    ) -> pd.DataFrame:
        """
        移動平均クロス戦略の最適化
        
        Args:
            data: 株価データ
            short_ma_range: 短期移動平均の範囲（最小値, 最大値）
            long_ma_range: 長期移動平均の範囲（最小値, 最大値）
            rsi_low_range: RSIの買いシグナル範囲
            rsi_high_range: RSIの売りシグナル範囲
        
        Returns:
            DataFrame: 最適化結果
        """
        results = []
        
        # パラメータの組み合わせを生成
        short_ma_values = range(short_ma_range[0], short_ma_range[1] + 1, 2)
        long_ma_values = range(long_ma_range[0], long_ma_range[1] + 1, 5)
        rsi_low_values = range(rsi_low_range[0], rsi_high_range[0], 5)
        rsi_high_values = range(rsi_low_range[1], rsi_high_range[1] + 1, 5)
        
        total_combinations = len(list(product(short_ma_values, long_ma_values, rsi_low_values, rsi_high_values)))
        print(f"総組み合わせ数: {total_combinations}")
        
        count = 0
        for short_ma, long_ma, rsi_low, rsi_high in product(short_ma_values, long_ma_values, rsi_low_values, rsi_high_values):
            if short_ma >= long_ma:
                continue
            
            count += 1
            if count % 100 == 0:
                print(f"進捗: {count}/{total_combinations}")
            
            # 移動平均を計算
            data_copy = data.copy()
            data_copy[f'MA{short_ma}'] = data_copy['Close'].rolling(window=short_ma).mean()
            data_copy[f'MA{long_ma}'] = data_copy['Close'].rolling(window=long_ma).mean()
            
            # RSIが既に計算されているか確認
            if 'RSI' not in data_copy.columns:
                delta = data_copy['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                data_copy['RSI'] = 100 - (100 / (1 + rs))
            
            # 買い条件: 短期MAが長期MAを上抜け、かつRSIが低い
            def buy_condition(row):
                if pd.isna(row[f'MA{short_ma}']) or pd.isna(row[f'MA{long_ma}']) or pd.isna(row['RSI']):
                    return False
                return (row[f'MA{short_ma}'] > row[f'MA{long_ma}']) and (row['RSI'] < rsi_high)
            
            # 売り条件: 短期MAが長期MAを下抜け、またはRSIが高い
            def sell_condition(row):
                if pd.isna(row[f'MA{short_ma}']) or pd.isna(row[f'MA{long_ma}']) or pd.isna(row['RSI']):
                    return False
                return (row[f'MA{short_ma}'] < row[f'MA{long_ma}']) or (row['RSI'] > rsi_high)
            
            # バックテスト実行
            try:
                result = self.backtester.run_backtest(data_copy, buy_condition, sell_condition)
                result['short_ma'] = short_ma
                result['long_ma'] = long_ma
                result['rsi_low'] = rsi_low
                result['rsi_high'] = rsi_high
                results.append(result)
            except Exception as e:
                continue
        
        if not results:
            return pd.DataFrame()
        
        # 結果をDataFrameに変換
        df_results = pd.DataFrame(results)
        
        # 不要な列を削除
        df_results = df_results.drop(columns=['equity_curve', 'dates', 'trades'], errors='ignore')
        
        # 利益が出る条件のみフィルタ
        profitable_results = df_results[df_results['total_return_pct'] > 0].copy()
        
        return profitable_results.sort_values('total_return_pct', ascending=False)
    
    def optimize_rsi_strategy(
        self,
        data: pd.DataFrame,
        rsi_oversold_range: Tuple[int, int] = (20, 40),
        rsi_overbought_range: Tuple[int, int] = (60, 80),
        ma_period_range: Tuple[int, int] = (5, 50)
    ) -> pd.DataFrame:
        """
        RSI戦略の最適化
        
        Args:
            data: 株価データ
            rsi_oversold_range: RSIの買いシグナル範囲
            rsi_overbought_range: RSIの売りシグナル範囲
            ma_period_range: 移動平均の期間範囲
        
        Returns:
            DataFrame: 最適化結果
        """
        results = []
        
        rsi_oversold_values = range(rsi_oversold_range[0], rsi_oversold_range[1] + 1, 2)
        rsi_overbought_values = range(rsi_overbought_range[0], rsi_overbought_range[1] + 1, 2)
        ma_period_values = range(ma_period_range[0], ma_period_range[1] + 1, 5)
        
        total_combinations = len(list(product(rsi_oversold_values, rsi_overbought_values, ma_period_values)))
        print(f"総組み合わせ数: {total_combinations}")
        
        count = 0
        for rsi_oversold, rsi_overbought, ma_period in product(rsi_oversold_values, rsi_overbought_values, ma_period_values):
            if rsi_oversold >= rsi_overbought:
                continue
            
            count += 1
            if count % 50 == 0:
                print(f"進捗: {count}/{total_combinations}")
            
            # 移動平均とRSIを計算
            data_copy = data.copy()
            data_copy[f'MA{ma_period}'] = data_copy['Close'].rolling(window=ma_period).mean()
            
            if 'RSI' not in data_copy.columns:
                delta = data_copy['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                data_copy['RSI'] = 100 - (100 / (1 + rs))
            
            # 買い条件: RSIがオーバーソールドで、価格が移動平均より上
            def buy_condition(row):
                if pd.isna(row['RSI']) or pd.isna(row[f'MA{ma_period}']):
                    return False
                return (row['RSI'] < rsi_oversold) and (row['Close'] > row[f'MA{ma_period}'])
            
            # 売り条件: RSIがオーバーボート
            def sell_condition(row):
                if pd.isna(row['RSI']):
                    return False
                return row['RSI'] > rsi_overbought
            
            try:
                result = self.backtester.run_backtest(data_copy, buy_condition, sell_condition)
                result['rsi_oversold'] = rsi_oversold
                result['rsi_overbought'] = rsi_overbought
                result['ma_period'] = ma_period
                results.append(result)
            except Exception as e:
                continue
        
        if not results:
            return pd.DataFrame()
        
        df_results = pd.DataFrame(results)
        df_results = df_results.drop(columns=['equity_curve', 'dates', 'trades'], errors='ignore')
        
        profitable_results = df_results[df_results['total_return_pct'] > 0].copy()
        
        return profitable_results.sort_values('total_return_pct', ascending=False)
    
    def analyze_profitable_conditions(self, optimization_results: pd.DataFrame) -> Dict:
        """
        利益が出る条件を分析
        
        Args:
            optimization_results: 最適化結果のDataFrame
        
        Returns:
            Dict: 分析結果
        """
        if optimization_results.empty:
            return {
                'best_strategy': None,
                'avg_profitable_params': {},
                'parameter_ranges': {}
            }
        
        # 最も利益率の高い戦略
        best_strategy = optimization_results.iloc[0].to_dict()
        
        # 利益が出た戦略の平均パラメータ
        profitable = optimization_results[optimization_results['total_return_pct'] > 0]
        
        avg_params = {}
        param_ranges = {}
        
        # 各パラメータの統計を計算
        for col in optimization_results.columns:
            if col not in ['total_return', 'total_return_pct', 'num_trades', 'win_rate', 
                          'avg_profit', 'avg_loss', 'profit_factor', 'max_drawdown', 'sharpe_ratio']:
                if col in profitable.columns:
                    avg_params[col] = profitable[col].mean()
                    param_ranges[col] = {
                        'min': profitable[col].min(),
                        'max': profitable[col].max(),
                        'median': profitable[col].median()
                    }
        
        return {
            'best_strategy': best_strategy,
            'avg_profitable_params': avg_params,
            'parameter_ranges': param_ranges,
            'total_profitable_strategies': len(profitable),
            'total_tested_strategies': len(optimization_results)
        }
