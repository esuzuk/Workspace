"""
ファンダメンタル分析モジュール
各投資家の哲学に基づいた財務分析を実装
"""
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """ファンダメンタル分析クラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def get_financial_data(self, ticker: str) -> dict:
        """
        財務データを取得
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            dict: 財務データ
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 財務諸表を取得
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow
            quarterly_financials = stock.quarterly_financials
            quarterly_cashflow = stock.quarterly_cashflow
            
            # 主要財務指標を抽出
            financial_data = {
                # 基本情報
                'ticker': ticker,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                
                # 価格関連
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                'market_cap': info.get('marketCap', 0),
                'enterprise_value': info.get('enterpriseValue', 0),
                
                # バリュー指標
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook', 0),
                'peg_ratio': info.get('pegRatio'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                
                # 収益性指標
                'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None,
                'roa': info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else None,
                'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else None,
                'operating_margin': info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else None,
                
                # 成長性指標
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else None,
                'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else None,
                'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth', 0) * 100 if info.get('earningsQuarterlyGrowth') else None,
                
                # 財務健全性
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0),
                
                # キャッシュフロー
                'operating_cashflow': info.get('operatingCashflow', 0),
                'free_cashflow': info.get('freeCashflow', 0),
                'total_cash': info.get('totalCash', 0),
                
                # 配当
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else None,
                'payout_ratio': info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else None,
                
                # EPS関連
                'trailing_eps': info.get('trailingEps', 0),
                'forward_eps': info.get('forwardEps', 0),
                'eps_growth': None,  # 後で計算
                
                # その他
                'beta': info.get('beta', 1.0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
            }
            
            # 財務諸表から追加データを取得
            if not financials.empty:
                try:
                    # 過去3年の売上高と利益を取得
                    revenue_data = financials.loc['Total Revenue'] if 'Total Revenue' in financials.index else None
                    net_income_data = financials.loc['Net Income'] if 'Net Income' in financials.index else None
                    
                    if revenue_data is not None and len(revenue_data) >= 3:
                        financial_data['revenue_3y'] = revenue_data.iloc[:3].tolist()
                        financial_data['revenue_growth_3y'] = self._calculate_growth_rate(revenue_data.iloc[:3].values)
                    
                    if net_income_data is not None and len(net_income_data) >= 3:
                        financial_data['net_income_3y'] = net_income_data.iloc[:3].tolist()
                        financial_data['net_income_growth_3y'] = self._calculate_growth_rate(net_income_data.iloc[:3].values)
                except Exception as e:
                    logger.warning(f"財務諸表データの取得に失敗: {str(e)}")
            
            # 四半期データから成長率を計算
            if not quarterly_financials.empty:
                try:
                    quarterly_revenue = quarterly_financials.loc['Total Revenue'] if 'Total Revenue' in quarterly_financials.index else None
                    quarterly_net_income = quarterly_financials.loc['Net Income'] if 'Net Income' in quarterly_financials.index else None
                    
                    if quarterly_revenue is not None and len(quarterly_revenue) >= 4:
                        # 最新四半期の前年同期比成長率
                        if len(quarterly_revenue) >= 5:
                            current_q = quarterly_revenue.iloc[0]
                            last_year_q = quarterly_revenue.iloc[4]
                            if last_year_q != 0:
                                financial_data['quarterly_revenue_growth'] = ((current_q - last_year_q) / abs(last_year_q)) * 100
                    
                    if quarterly_net_income is not None and len(quarterly_net_income) >= 4:
                        if len(quarterly_net_income) >= 5:
                            current_q = quarterly_net_income.iloc[0]
                            last_year_q = quarterly_net_income.iloc[4]
                            if last_year_q != 0:
                                financial_data['quarterly_earnings_growth'] = ((current_q - last_year_q) / abs(last_year_q)) * 100
                except Exception as e:
                    logger.warning(f"四半期データの取得に失敗: {str(e)}")
            
            # キャッシュフローデータ
            if not cashflow.empty:
                try:
                    operating_cf = cashflow.loc['Total Cash From Operating Activities'] if 'Total Cash From Operating Activities' in cashflow.index else None
                    if operating_cf is not None and len(operating_cf) >= 3:
                        financial_data['operating_cf_3y'] = operating_cf.iloc[:3].tolist()
                        financial_data['operating_cf_growth_3y'] = self._calculate_growth_rate(operating_cf.iloc[:3].values)
                except Exception as e:
                    logger.warning(f"キャッシュフローデータの取得に失敗: {str(e)}")
            
            # EPS成長率を計算
            if financial_data.get('trailing_eps') and financial_data.get('forward_eps'):
                if financial_data['trailing_eps'] != 0:
                    financial_data['eps_growth'] = ((financial_data['forward_eps'] - financial_data['trailing_eps']) / abs(financial_data['trailing_eps'])) * 100
            
            return financial_data
            
        except Exception as e:
            logger.error(f"財務データ取得エラー ({ticker}): {str(e)}")
            raise
    
    def _calculate_growth_rate(self, values: list[float]) -> float | None:
        """
        成長率を計算（複利成長率）
        
        Args:
            values: 過去3年の値のリスト（最新が先頭）
        
        Returns:
            float: 成長率（%）
        """
        try:
            if len(values) < 2:
                return None
            
            # 最新年と最古年の値を使用
            latest = values[0]
            oldest = values[-1]
            
            if oldest == 0 or oldest < 0:
                return None
            
            # 複利成長率を計算
            years = len(values) - 1
            if years > 0:
                growth_rate = ((latest / oldest) ** (1 / years) - 1) * 100
                return growth_rate
            
            return None
        except Exception as e:
            logger.warning(f"成長率計算エラー: {str(e)}")
            return None
    
    def calculate_intrinsic_value(self, financial_data: dict, method: str = 'dcf') -> float | None:
        """
        内在価値を計算
        
        Args:
            financial_data: 財務データ
            method: 計算方法（'dcf', 'pe', 'pb'）
        
        Returns:
            float: 内在価値
        """
        try:
            current_price = financial_data.get('current_price', 0)
            if current_price == 0:
                return None
            
            if method == 'pe':
                # PER法
                pe_ratio = financial_data.get('pe_ratio')
                trailing_eps = financial_data.get('trailing_eps', 0)
                
                if pe_ratio and trailing_eps > 0:
                    # 適正PERを15倍と仮定（業種によって異なる）
                    fair_pe = 15
                    intrinsic_value = trailing_eps * fair_pe
                    return intrinsic_value
            
            elif method == 'pb':
                # PBR法
                pb_ratio = financial_data.get('pb_ratio')
                if pb_ratio and pb_ratio > 0:
                    # 適正PBRを1.5倍と仮定
                    fair_pb = 1.5
                    book_value = current_price / pb_ratio
                    intrinsic_value = book_value * fair_pb
                    return intrinsic_value
            
            elif method == 'dcf':
                # DCF法（簡易版）
                free_cashflow = financial_data.get('free_cashflow', 0)
                if free_cashflow > 0:
                    # 簡易計算：FCFを10倍（WACC 10%と仮定）
                    intrinsic_value = free_cashflow * 10
                    return intrinsic_value
            
            return None
            
        except Exception as e:
            logger.error(f"内在価値計算エラー: {str(e)}")
            return None
    
    def calculate_margin_of_safety(self, current_price: float, intrinsic_value: float) -> float | None:
        """
        安全余裕（マージン・オブ・セーフティ）を計算
        
        Args:
            current_price: 現在価格
            intrinsic_value: 内在価値
        
        Returns:
            float: 安全余裕（%）
        """
        try:
            if intrinsic_value == 0:
                return None
            
            margin = ((intrinsic_value - current_price) / intrinsic_value) * 100
            return margin
            
        except Exception as e:
            logger.error(f"安全余裕計算エラー: {str(e)}")
            return None
