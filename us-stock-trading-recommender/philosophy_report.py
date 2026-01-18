"""
投資哲学レポート生成モジュール
各投資家の哲学に基づいた詳細レポートを生成
"""
import logging
from datetime import datetime
from fundamental_analyzer import FundamentalAnalyzer
from investment_philosophy import InvestmentPhilosophyAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PhilosophyReportGenerator:
    """投資哲学レポート生成クラス"""
    
    def __init__(self):
        """初期化"""
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.philosophy_analyzer = InvestmentPhilosophyAnalyzer(self.fundamental_analyzer)
    
    def generate_full_report(self, ticker: str, price_data: dict) -> str:
        """
        完全な投資哲学レポートを生成
        
        Args:
            ticker: ティッカーシンボル
            price_data: 価格データ
        
        Returns:
            str: レポート文字列
        """
        try:
            # 財務データを取得
            financial_data = self.fundamental_analyzer.get_financial_data(ticker)
            
            # 各投資哲学で分析
            philosophy_results = self.philosophy_analyzer.analyze_all_philosophies(
                ticker, financial_data, price_data
            )
            
            # レポートを生成
            report = f"""
╔═══════════════════════════════════════════════════════════╗
║        投資哲学統合レポート - {ticker}                    ║
╚═══════════════════════════════════════════════════════════╝

企業名: {financial_data.get('company_name', 'N/A')}
業種: {financial_data.get('sector', 'N/A')} / {financial_data.get('industry', 'N/A')}
現在価格: ${financial_data.get('current_price', 0):.2f}

【統合判定】
推奨: {philosophy_results['overall_recommendation']}
信頼度: {philosophy_results['overall_confidence']:.1%}

{'='*60}

【ベンジャミン・グレアム - バリュー投資】
推奨: {philosophy_results['analyses']['graham']['recommendation']}
信頼度: {philosophy_results['analyses']['graham']['confidence']:.1%}

推奨理由:
"""
            
            for reason in philosophy_results['analyses']['graham']['reasons']:
                report += f"  ✓ {reason}\n"
            
            if philosophy_results['analyses']['graham']['warnings']:
                report += "\n警告:\n"
                for warning in philosophy_results['analyses']['graham']['warnings']:
                    report += f"  ⚠ {warning}\n"
            
            report += f"""
主要指標:
  - PER: {philosophy_results['analyses']['graham']['data'].get('pe_ratio', 'N/A')}
  - PBR: {philosophy_results['analyses']['graham']['data'].get('pb_ratio', 'N/A')}
  - ROE: {philosophy_results['analyses']['graham']['data'].get('roe', 'N/A')}%
  - 安全余裕（PER法）: {philosophy_results['analyses']['graham']['data'].get('margin_of_safety_pe', 'N/A')}%
  - 安全余裕（PBR法）: {philosophy_results['analyses']['graham']['data'].get('margin_of_safety_pb', 'N/A')}%

{'='*60}

【ウォーレン・バフェット - 長期投資】
推奨: {philosophy_results['analyses']['buffett']['recommendation']}
信頼度: {philosophy_results['analyses']['buffett']['confidence']:.1%}

推奨理由:
"""
            
            for reason in philosophy_results['analyses']['buffett']['reasons']:
                report += f"  ✓ {reason}\n"
            
            if philosophy_results['analyses']['buffett']['warnings']:
                report += "\n警告:\n"
                for warning in philosophy_results['analyses']['buffett']['warnings']:
                    report += f"  ⚠ {warning}\n"
            
            report += f"""
主要指標:
  - ROE: {philosophy_results['analyses']['buffett']['data'].get('roe', 'N/A')}%
  - 利益成長率: {philosophy_results['analyses']['buffett']['data'].get('earnings_growth', 'N/A')}%
  - 営業CF: ${philosophy_results['analyses']['buffett']['data'].get('operating_cashflow', 0):,.0f}
  - フリーCF: ${philosophy_results['analyses']['buffett']['data'].get('free_cashflow', 0):,.0f}

{'='*60}

【ウィリアム・J・オニール - CAN SLIM】
推奨: {philosophy_results['analyses']['can_slim']['recommendation']}
信頼度: {philosophy_results['analyses']['can_slim']['confidence']:.1%}

推奨理由:
"""
            
            for reason in philosophy_results['analyses']['can_slim']['reasons']:
                report += f"  ✓ {reason}\n"
            
            if philosophy_results['analyses']['can_slim']['warnings']:
                report += "\n警告:\n"
                for warning in philosophy_results['analyses']['can_slim']['warnings']:
                    report += f"  ⚠ {warning}\n"
            
            report += f"""
主要指標:
  - 四半期利益成長: {philosophy_results['analyses']['can_slim']['data'].get('quarterly_earnings_growth', 'N/A')}%
  - 年間利益成長: {philosophy_results['analyses']['can_slim']['data'].get('earnings_growth', 'N/A')}%
  - 52週高値比: {philosophy_results['analyses']['can_slim']['data'].get('price_to_52w_high', 'N/A')}%

{'='*60}

【広瀬隆雄 - 広瀬のプロトコル】
推奨: {philosophy_results['analyses']['hirose']['recommendation']}
信頼度: {philosophy_results['analyses']['hirose']['confidence']:.1%}

推奨理由:
"""
            
            for reason in philosophy_results['analyses']['hirose']['reasons']:
                report += f"  ✓ {reason}\n"
            
            if philosophy_results['analyses']['hirose']['warnings']:
                report += "\n警告:\n"
                for warning in philosophy_results['analyses']['hirose']['warnings']:
                    report += f"  ⚠ {warning}\n"
            
            report += f"""
主要指標:
  - 営業CFマージン: {philosophy_results['analyses']['hirose']['data'].get('operating_cf_margin', 'N/A')}%
  - EPS成長率: {philosophy_results['analyses']['hirose']['data'].get('eps_growth', 'N/A')}%
  - 営業CF成長（3年）: {philosophy_results['analyses']['hirose']['data'].get('operating_cf_growth_3y', 'N/A')}%
  - 売上高成長（3年）: {philosophy_results['analyses']['hirose']['data'].get('revenue_growth_3y', 'N/A')}%

{'='*60}

【賢人の総合アドバイス】
"""
            
            if philosophy_results['philosopher_advice']:
                for advice in philosophy_results['philosopher_advice']:
                    report += f"\n{advice['philosopher']}:\n"
                    report += f"  {advice['advice']}\n"
            else:
                report += "  現在、明確な推奨はありません。\n"
            
            report += f"""
{'='*60}

レポート生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

※ 本レポートは投資判断の支援ツールです。最終的な投資判断はご自身で行ってください。
"""
            
            return report
            
        except Exception as e:
            logger.error(f"レポート生成エラー ({ticker}): {str(e)}")
            return f"レポート生成エラー: {str(e)}"
