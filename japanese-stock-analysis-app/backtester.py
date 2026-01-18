"""
バックテストエンジン
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """取引情報"""
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    shares: int
    position_type: str  # 'long' or 'short'
    profit: Optional[float] = None
    profit_pct: Optional[float] = None


class Backtester:
    """バックテストエンジン"""
    
    def __init__(self, initial_capital: float = 1000000):
        """
        初期化
        
        Args:
            initial_capital: 初期資金（円）
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
    
    def reset(self):
        """バックテストをリセット"""
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.dates = []
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        buy_condition: Callable,
        sell_condition: Callable,
        position_size: float = 1.0,
        commission: float = 0.0015,  # 0.15%の手数料
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        バックテストを実行
        
        Args:
            data: 株価データ（テクニカル指標含む）
            buy_condition: 買い条件の関数（DataFrameの行を受け取り、boolを返す）
            sell_condition: 売り条件の関数（DataFrameの行を受け取り、boolを返す）
            position_size: ポジションサイズ（資金の割合、0.0-1.0）
            commission: 手数料率
            stop_loss: ストップロス率（例: 0.05 = 5%）
            take_profit: 利確率（例: 0.10 = 10%）
        
        Returns:
            Dict: バックテスト結果
        """
        self.reset()
        
        position = None  # 現在のポジション
        current_trade = None
        
        for i, (date, row) in enumerate(data.iterrows()):
            self.dates.append(date)
            
            # ポジションを持っている場合
            if position is not None:
                current_price = row['Close']
                entry_price = position['entry_price']
                
                # ストップロス・利確チェック
                if stop_loss:
                    if current_price <= entry_price * (1 - stop_loss):
                        # ストップロス
                        self._close_position(date, current_price, commission)
                        position = None
                        current_trade = None
                        continue
                
                if take_profit:
                    if current_price >= entry_price * (1 + take_profit):
                        # 利確
                        self._close_position(date, current_price, commission)
                        position = None
                        current_trade = None
                        continue
                
                # 売り条件チェック
                if sell_condition(row):
                    self._close_position(date, current_price, commission)
                    position = None
                    current_trade = None
            
            # ポジションを持っていない場合、買い条件チェック
            else:
                if buy_condition(row):
                    # 買いエントリー
                    entry_price = row['Close']
                    available_capital = self.capital * position_size
                    shares = int(available_capital / entry_price)
                    
                    if shares > 0:
                        cost = shares * entry_price * (1 + commission)
                        if cost <= self.capital:
                            self.capital -= cost
                            position = {
                                'entry_date': date,
                                'entry_price': entry_price,
                                'shares': shares
                            }
                            current_trade = Trade(
                                entry_date=date,
                                exit_date=None,
                                entry_price=entry_price,
                                exit_price=None,
                                shares=shares,
                                position_type='long'
                            )
                            self.trades.append(current_trade)
            
            # エクイティカーブを更新
            equity = self.capital
            if position:
                equity += position['shares'] * row['Close']
            self.equity_curve.append(equity)
        
        # 最終的にポジションが残っている場合は決済
        if position:
            final_price = data.iloc[-1]['Close']
            self._close_position(data.index[-1], final_price, commission)
        
        # 結果を計算
        return self._calculate_results()
    
    def _close_position(self, date: datetime, price: float, commission: float):
        """ポジションを決済"""
        if not self.trades or self.trades[-1].exit_date is not None:
            return
        
        trade = self.trades[-1]
        trade.exit_date = date
        trade.exit_price = price
        
        proceeds = trade.shares * price * (1 - commission)
        self.capital += proceeds
        
        trade.profit = proceeds - (trade.shares * trade.entry_price * (1 + commission))
        trade.profit_pct = (trade.exit_price / trade.entry_price - 1) * 100
    
    def _calculate_results(self) -> Dict:
        """バックテスト結果を計算"""
        if not self.trades:
            return {
                'total_return': 0,
                'total_return_pct': 0,
                'num_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': []
            }
        
        completed_trades = [t for t in self.trades if t.exit_date is not None]
        
        if not completed_trades:
            return {
                'total_return': 0,
                'total_return_pct': 0,
                'num_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': []
            }
        
        total_return = self.capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        profits = [t.profit for t in completed_trades]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0
        avg_profit = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        total_profit = sum(winning_trades) if winning_trades else 0
        total_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 最大ドローダウン
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) * 100
        
        # シャープレシオ（簡易版）
        returns = np.diff(equity_array) / equity_array[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        return {
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'num_trades': len(completed_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'equity_curve': self.equity_curve,
            'dates': self.dates,
            'trades': completed_trades
        }
