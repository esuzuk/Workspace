"""
各投資家の哲学に基づいた投資判定モジュール
"""
import logging
from datetime import datetime
from fundamental_analyzer import FundamentalAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InvestmentPhilosophyAnalyzer:
    """投資哲学分析クラス"""
    
    def __init__(self, fundamental_analyzer: FundamentalAnalyzer):
        """
        初期化
        
        Args:
            fundamental_analyzer: ファンダメンタル分析オブジェクト
        """
        self.fundamental_analyzer = fundamental_analyzer
    
    def analyze_graham_value(self, ticker: str, financial_data: dict) -> dict:
        """
        ベンジャミン・グレアムのバリュー投資判定
        
        Args:
            ticker: ティッカーシンボル
            financial_data: 財務データ
        
        Returns:
            dict: 判定結果
        """
        reasons = []
        confidence_factors = []
        warnings = []
        
        current_price = financial_data.get('current_price', 0)
        
        # 1. 安全余裕の計算
        intrinsic_value_pe = self.fundamental_analyzer.calculate_intrinsic_value(financial_data, 'pe')
        intrinsic_value_pb = self.fundamental_analyzer.calculate_intrinsic_value(financial_data, 'pb')
        
        margin_of_safety_pe = None
        margin_of_safety_pb = None
        
        if intrinsic_value_pe:
            margin_of_safety_pe = self.fundamental_analyzer.calculate_margin_of_safety(current_price, intrinsic_value_pe)
            if margin_of_safety_pe and margin_of_safety_pe > 30:
                reasons.append(f"安全余裕が十分（PER法: {margin_of_safety_pe:.1f}%）")
                confidence_factors.append(0.8)
            elif margin_of_safety_pe and margin_of_safety_pe > 0:
                reasons.append(f"安全余裕あり（PER法: {margin_of_safety_pe:.1f}%）")
                confidence_factors.append(0.6)
            elif margin_of_safety_pe and margin_of_safety_pe < 0:
                warnings.append(f"割高（PER法による安全余裕: {margin_of_safety_pe:.1f}%）")
        
        if intrinsic_value_pb:
            margin_of_safety_pb = self.fundamental_analyzer.calculate_margin_of_safety(current_price, intrinsic_value_pb)
            if margin_of_safety_pb and margin_of_safety_pb > 30:
                reasons.append(f"安全余裕が十分（PBR法: {margin_of_safety_pb:.1f}%）")
                confidence_factors.append(0.75)
        
        # 2. P/E判定（15倍以下が理想）
        pe_ratio = financial_data.get('pe_ratio')
        if pe_ratio:
            if pe_ratio < 15:
                reasons.append(f"PERが割安（{pe_ratio:.1f}倍）")
                confidence_factors.append(0.7)
            elif pe_ratio > 25:
                warnings.append(f"PERが割高（{pe_ratio:.1f}倍）")
        
        # 3. P/B判定（1.5倍以下が理想）
        pb_ratio = financial_data.get('pb_ratio')
        if pb_ratio:
            if pb_ratio < 1.5:
                reasons.append(f"PBRが割安（{pb_ratio:.2f}倍）")
                confidence_factors.append(0.65)
            elif pb_ratio > 3.0:
                warnings.append(f"PBRが割高（{pb_ratio:.2f}倍）")
        
        # 4. ROE判定（15%以上が理想）
        roe = financial_data.get('roe')
        if roe:
            if roe >= 15:
                reasons.append(f"ROEが高い（{roe:.1f}%）")
                confidence_factors.append(0.7)
            elif roe < 10:
                warnings.append(f"ROEが低い（{roe:.1f}%）")
        
        # 5. 財務健全性（負債比率）
        debt_to_equity = financial_data.get('debt_to_equity', 0)
        if debt_to_equity > 100:
            warnings.append(f"負債比率が高い（{debt_to_equity:.1f}%）")
        elif debt_to_equity < 50:
            reasons.append(f"財務健全性良好（負債比率: {debt_to_equity:.1f}%）")
            confidence_factors.append(0.5)
        
        # 6. 流動比率（2.0以上が理想）
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio >= 2.0:
            reasons.append(f"流動比率が良好（{current_ratio:.2f}）")
            confidence_factors.append(0.5)
        elif current_ratio < 1.0:
            warnings.append(f"流動比率が低い（{current_ratio:.2f}）")
        
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        
        return {
            'philosophy': 'Graham Value Investing',
            'recommendation': 'BUY' if confidence >= 0.6 and not warnings else 'HOLD' if confidence >= 0.4 else 'AVOID',
            'confidence': min(0.95, confidence),
            'reasons': reasons,
            'warnings': warnings,
            'data': {
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'roe': roe,
                'margin_of_safety_pe': margin_of_safety_pe,
                'margin_of_safety_pb': margin_of_safety_pb,
                'intrinsic_value_pe': intrinsic_value_pe,
                'intrinsic_value_pb': intrinsic_value_pb,
            }
        }
    
    def analyze_buffett_value(self, ticker: str, financial_data: dict) -> dict:
        """
        ウォーレン・バフェットの長期投資判定
        
        Args:
            ticker: ティッカーシンボル
            financial_data: 財務データ
        
        Returns:
            dict: 判定結果
        """
        reasons = []
        confidence_factors = []
        warnings = []
        
        # 1. 優良企業の判定（ROE 15%以上、利益率向上）
        roe = financial_data.get('roe')
        if roe and roe >= 15:
            reasons.append(f"優良企業（ROE: {roe:.1f}%）")
            confidence_factors.append(0.8)
        elif roe and roe < 10:
            warnings.append(f"ROEが低い（{roe:.1f}%）")
        
        # 2. 利益成長の持続性
        earnings_growth = financial_data.get('earnings_growth')
        if earnings_growth and earnings_growth > 10:
            reasons.append(f"利益成長が持続（{earnings_growth:.1f}%）")
            confidence_factors.append(0.75)
        elif earnings_growth and earnings_growth < 0:
            warnings.append(f"利益が減少傾向（{earnings_growth:.1f}%）")
        
        # 3. キャッシュフロー生成能力
        operating_cashflow = financial_data.get('operating_cashflow', 0)
        free_cashflow = financial_data.get('free_cashflow', 0)
        
        if operating_cashflow > 0:
            reasons.append(f"営業キャッシュフローが良好（${operating_cashflow:,.0f}）")
            confidence_factors.append(0.7)
        
        if free_cashflow > 0:
            reasons.append(f"フリーキャッシュフローが良好（${free_cashflow:,.0f}）")
            confidence_factors.append(0.7)
        
        # 4. 負債の少なさ
        debt_to_equity = financial_data.get('debt_to_equity', 0)
        if debt_to_equity < 50:
            reasons.append(f"財務健全性良好（負債比率: {debt_to_equity:.1f}%）")
            confidence_factors.append(0.6)
        
        # 5. 長期保有推奨
        if len(reasons) >= 3:
            reasons.append("長期保有に適した優良企業")
            confidence_factors.append(0.8)
        
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        
        return {
            'philosophy': 'Buffett Long-term Value',
            'recommendation': 'BUY_AND_HOLD' if confidence >= 0.7 else 'HOLD' if confidence >= 0.5 else 'AVOID',
            'confidence': min(0.95, confidence),
            'reasons': reasons,
            'warnings': warnings,
            'data': {
                'roe': roe,
                'earnings_growth': earnings_growth,
                'operating_cashflow': operating_cashflow,
                'free_cashflow': free_cashflow,
            }
        }
    
    def analyze_can_slim(self, ticker: str, financial_data: dict, price_data: dict) -> dict:
        """
        ウィリアム・J・オニールのCAN SLIM判定
        
        Args:
            ticker: ティッカーシンボル
            financial_data: 財務データ
            price_data: 価格データ（52週高値など）
        
        Returns:
            dict: 判定結果
        """
        reasons = []
        confidence_factors = []
        warnings = []
        
        # C: Current quarterly earnings（四半期利益）
        quarterly_earnings_growth = financial_data.get('quarterly_earnings_growth')
        if quarterly_earnings_growth and quarterly_earnings_growth > 25:
            reasons.append(f"四半期利益成長率が高い（{quarterly_earnings_growth:.1f}%）")
            confidence_factors.append(0.8)
        elif quarterly_earnings_growth and quarterly_earnings_growth < 0:
            warnings.append(f"四半期利益が減少（{quarterly_earnings_growth:.1f}%）")
        
        # A: Annual earnings growth（年間利益成長）
        earnings_growth = financial_data.get('earnings_growth')
        if earnings_growth and earnings_growth > 25:
            reasons.append(f"年間利益成長率が高い（{earnings_growth:.1f}%）")
            confidence_factors.append(0.75)
        
        # N: New products, new management, new highs（新高値）
        current_price = financial_data.get('current_price', 0)
        week_52_high = financial_data.get('52_week_high', 0)
        
        if week_52_high > 0:
            price_to_high_ratio = (current_price / week_52_high) * 100
            if price_to_high_ratio >= 95:
                reasons.append(f"52週高値に近い（{price_to_high_ratio:.1f}%）")
                confidence_factors.append(0.7)
            elif price_to_high_ratio < 70:
                warnings.append(f"52週高値から大きく下落（{price_to_high_ratio:.1f}%）")
        
        # S: Supply and demand（需給）- 出来高で判断
        volume = price_data.get('volume', 0)
        volume_ma = price_data.get('volume_ma', 0)
        if volume and volume_ma and volume > volume_ma * 1.5:
            reasons.append(f"出来高が急増（平均の{volume/volume_ma:.1f}倍）")
            confidence_factors.append(0.6)
        
        # L: Leader or laggard（リーダーかラガードか）
        # 業界内での相対的なパフォーマンスを評価（簡易版）
        roe = financial_data.get('roe')
        if roe and roe >= 20:
            reasons.append(f"業界リーダー（ROE: {roe:.1f}%）")
            confidence_factors.append(0.65)
        
        # I: Institutional sponsorship（機関投資家の支持）
        # Yahoo Financeでは直接取得できないため、スキップ
        
        # M: Market direction（市場の方向性）
        # 市場全体の方向性は別途評価が必要
        
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        
        return {
            'philosophy': 'CAN SLIM',
            'recommendation': 'BUY' if confidence >= 0.65 else 'HOLD' if confidence >= 0.5 else 'AVOID',
            'confidence': min(0.95, confidence),
            'reasons': reasons,
            'warnings': warnings,
            'data': {
                'quarterly_earnings_growth': quarterly_earnings_growth,
                'earnings_growth': earnings_growth,
                'price_to_52w_high': (current_price / week_52_high * 100) if week_52_high > 0 else None,
            }
        }
    
    def analyze_hirose_protocol(self, ticker: str, financial_data: dict) -> dict:
        """
        広瀬隆雄のプロトコル判定
        
        Args:
            ticker: ティッカーシンボル
            financial_data: 財務データ
        
        Returns:
            dict: 判定結果
        """
        reasons = []
        confidence_factors = []
        warnings = []
        
        # 1. 営業キャッシュフロー・マージン15%以上
        operating_cashflow = financial_data.get('operating_cashflow', 0)
        market_cap = financial_data.get('market_cap', 0)
        
        if operating_cashflow > 0 and market_cap > 0:
            operating_cf_margin = (operating_cashflow / market_cap) * 100
            if operating_cf_margin >= 15:
                reasons.append(f"営業CFマージンが良好（{operating_cf_margin:.1f}%）")
                confidence_factors.append(0.8)
            else:
                warnings.append(f"営業CFマージンが15%未満（{operating_cf_margin:.1f}%）")
        
        # 2. 過去3年のEPS成長
        eps_growth = financial_data.get('eps_growth')
        if eps_growth and eps_growth > 0:
            reasons.append(f"EPS成長率が良好（{eps_growth:.1f}%）")
            confidence_factors.append(0.7)
        else:
            warnings.append("EPS成長率が不明またはマイナス")
        
        # 3. 過去3年の営業キャッシュフロー成長
        operating_cf_growth_3y = financial_data.get('operating_cf_growth_3y')
        if operating_cf_growth_3y and operating_cf_growth_3y > 0:
            reasons.append(f"営業CFが3年間成長（{operating_cf_growth_3y:.1f}%）")
            confidence_factors.append(0.7)
        
        # 4. 過去3年の売上高成長
        revenue_growth_3y = financial_data.get('revenue_growth_3y')
        if revenue_growth_3y and revenue_growth_3y > 0:
            reasons.append(f"売上高が3年間成長（{revenue_growth_3y:.1f}%）")
            confidence_factors.append(0.65)
        
        # 5. 一株あたり営業キャッシュフロー > EPS の検証
        trailing_eps = financial_data.get('trailing_eps', 0)
        shares_outstanding = financial_data.get('shares_outstanding', 0)
        
        if operating_cashflow > 0 and shares_outstanding > 0:
            operating_cf_per_share = operating_cashflow / shares_outstanding
            if trailing_eps > 0 and operating_cf_per_share > trailing_eps:
                reasons.append(f"営業CF/株 > EPS（CF/株: ${operating_cf_per_share:.2f}, EPS: ${trailing_eps:.2f}）")
                confidence_factors.append(0.75)
            elif trailing_eps > 0:
                warnings.append(f"営業CF/株 < EPS（粉飾リスク）")
        
        # 6. 過去最高値更新の検出
        current_price = financial_data.get('current_price', 0)
        week_52_high = financial_data.get('52_week_high', 0)
        
        if week_52_high > 0:
            price_to_high_ratio = (current_price / week_52_high) * 100
            if price_to_high_ratio >= 98:
                reasons.append(f"過去最高値に近い（新しい評価が生まれている）")
                confidence_factors.append(0.7)
        
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        
        return {
            'philosophy': 'Hirose Protocol',
            'recommendation': 'BUY' if confidence >= 0.65 else 'HOLD' if confidence >= 0.4 else 'AVOID',
            'confidence': min(0.95, confidence),
            'reasons': reasons,
            'warnings': warnings,
            'data': {
                'operating_cf_margin': (operating_cashflow / market_cap * 100) if market_cap > 0 else None,
                'eps_growth': eps_growth,
                'operating_cf_growth_3y': operating_cf_growth_3y,
                'revenue_growth_3y': revenue_growth_3y,
            }
        }
    
    def analyze_all_philosophies(self, ticker: str, financial_data: dict, price_data: dict) -> dict:
        """
        すべての投資哲学を統合して分析
        
        Args:
            ticker: ティッカーシンボル
            financial_data: 財務データ
            price_data: 価格データ
        
        Returns:
            dict: 統合判定結果
        """
        results = {
            'ticker': ticker,
            'analyses': {},
            'overall_recommendation': 'HOLD',
            'overall_confidence': 0.0,
            'philosopher_advice': []
        }
        
        # 各投資哲学で分析
        graham_result = self.analyze_graham_value(ticker, financial_data)
        results['analyses']['graham'] = graham_result
        
        buffett_result = self.analyze_buffett_value(ticker, financial_data)
        results['analyses']['buffett'] = buffett_result
        
        can_slim_result = self.analyze_can_slim(ticker, financial_data, price_data)
        results['analyses']['can_slim'] = can_slim_result
        
        hirose_result = self.analyze_hirose_protocol(ticker, financial_data)
        results['analyses']['hirose'] = hirose_result
        
        # 統合判定
        all_confidence = [
            graham_result['confidence'],
            buffett_result['confidence'],
            can_slim_result['confidence'],
            hirose_result['confidence']
        ]
        
        results['overall_confidence'] = sum(all_confidence) / len(all_confidence)
        
        # 推奨の集計
        buy_count = sum(1 for r in [graham_result, buffett_result, can_slim_result, hirose_result] 
                       if r['recommendation'] in ['BUY', 'BUY_AND_HOLD'])
        
        if buy_count >= 3:
            results['overall_recommendation'] = 'STRONG_BUY'
        elif buy_count >= 2:
            results['overall_recommendation'] = 'BUY'
        elif buy_count >= 1:
            results['overall_recommendation'] = 'CONSIDER'
        else:
            results['overall_recommendation'] = 'AVOID'
        
        # 賢人のアドバイスを生成
        if graham_result['confidence'] >= 0.6:
            results['philosopher_advice'].append({
                'philosopher': 'ベンジャミン・グレアム',
                'advice': ' | '.join(graham_result['reasons'])
            })
        
        if buffett_result['confidence'] >= 0.6:
            results['philosopher_advice'].append({
                'philosopher': 'ウォーレン・バフェット',
                'advice': ' | '.join(buffett_result['reasons'])
            })
        
        if can_slim_result['confidence'] >= 0.6:
            results['philosopher_advice'].append({
                'philosopher': 'ウィリアム・J・オニール',
                'advice': ' | '.join(can_slim_result['reasons'])
            })
        
        if hirose_result['confidence'] >= 0.6:
            results['philosopher_advice'].append({
                'philosopher': '広瀬隆雄',
                'advice': ' | '.join(hirose_result['reasons'])
            })
        
        return results
