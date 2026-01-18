"""
通知機能を管理するモジュール
"""
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationManager:
    """通知管理クラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def format_sell_recommendation(self, recommendation: dict) -> str:
        """
        売り推奨をフォーマット
        
        Args:
            recommendation: 売り推奨データ
        
        Returns:
            str: フォーマットされた通知メッセージ
        """
        ticker = recommendation.get('ticker', 'Unknown')
        current_price = recommendation.get('current_price', 0)
        recommended_price = recommendation.get('recommended_price', 0)
        reason = recommendation.get('reason', '')
        logic = recommendation.get('logic', '')
        confidence = recommendation.get('confidence', 0)
        data_source = recommendation.get('data_source', {})
        
        message = f"""
╔═══════════════════════════════════════════════════════════╗
║              【売り推奨通知】                              ║
╚═══════════════════════════════════════════════════════════╝

銘柄: {ticker}
現在価格: ${current_price:.2f}
推奨売却価格: ${recommended_price:.2f}
信頼度: {confidence:.1%}

【推奨理由】
{reason}

【判定ロジック】
{logic}

【使用したデータ】
"""
        
        # データソースの詳細を追加
        if data_source.get('rsi'):
            message += f"  - RSI: {data_source['rsi']:.2f}\n"
        if data_source.get('macd'):
            message += f"  - MACD: {data_source['macd']:.2f}\n"
            if data_source.get('macd_signal'):
                message += f"  - MACD Signal: {data_source['macd_signal']:.2f}\n"
        if data_source.get('ma_20'):
            message += f"  - 20日移動平均: ${data_source['ma_20']:.2f}\n"
        if data_source.get('ma_50'):
            message += f"  - 50日移動平均: ${data_source['ma_50']:.2f}\n"
        if data_source.get('ma_200'):
            message += f"  - 200日移動平均: ${data_source['ma_200']:.2f}\n"
        if data_source.get('bb_upper'):
            message += f"  - ボリンジャーバンド上限: ${data_source['bb_upper']:.2f}\n"
        
        # 賢人のアドバイスを追加
        philosopher_advice = recommendation.get('philosopher_advice', [])
        if philosopher_advice:
            message += "\n【賢人のアドバイス】\n"
            for advice in philosopher_advice:
                message += f"  • {advice}\n"
        
        message += f"\n通知日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += "\n※ 本通知は投資判断の支援ツールです。最終的な投資判断はご自身で行ってください。\n"
        
        return message
    
    def format_buy_recommendation(self, recommendation: dict) -> str:
        """
        買い推奨をフォーマット
        
        Args:
            recommendation: 買い推奨データ
        
        Returns:
            str: フォーマットされた通知メッセージ
        """
        ticker = recommendation.get('ticker', 'Unknown')
        current_price = recommendation.get('current_price', 0)
        recommended_price = recommendation.get('recommended_price', 0)
        reason = recommendation.get('reason', '')
        logic = recommendation.get('logic', '')
        confidence = recommendation.get('confidence', 0)
        data_source = recommendation.get('data_source', {})
        
        message = f"""
╔═══════════════════════════════════════════════════════════╗
║              【買い推奨通知】                              ║
╚═══════════════════════════════════════════════════════════╝

銘柄: {ticker}
現在価格: ${current_price:.2f}
推奨購入価格: ${recommended_price:.2f}
信頼度: {confidence:.1%}

【推奨理由】
{reason}

【判定ロジック】
{logic}

【使用したデータ】
"""
        
        # データソースの詳細を追加
        if data_source.get('rsi'):
            message += f"  - RSI: {data_source['rsi']:.2f}\n"
        if data_source.get('macd'):
            message += f"  - MACD: {data_source['macd']:.2f}\n"
            if data_source.get('macd_signal'):
                message += f"  - MACD Signal: {data_source['macd_signal']:.2f}\n"
        if data_source.get('ma_20'):
            message += f"  - 20日移動平均: ${data_source['ma_20']:.2f}\n"
        if data_source.get('ma_50'):
            message += f"  - 50日移動平均: ${data_source['ma_50']:.2f}\n"
        if data_source.get('ma_200'):
            message += f"  - 200日移動平均: ${data_source['ma_200']:.2f}\n"
        if data_source.get('bb_lower'):
            message += f"  - ボリンジャーバンド下限: ${data_source['bb_lower']:.2f}\n"
        if data_source.get('volume'):
            message += f"  - 出来高: {data_source['volume']:,.0f}\n"
            if data_source.get('volume_ma'):
                message += f"  - 出来高平均: {data_source['volume_ma']:,.0f}\n"
        
        # 賢人のアドバイスを追加
        philosopher_advice = recommendation.get('philosopher_advice', [])
        if philosopher_advice:
            message += "\n【賢人のアドバイス】\n"
            for advice in philosopher_advice:
                message += f"  • {advice}\n"
        
        message += f"\n通知日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += "\n※ 本通知は投資判断の支援ツールです。最終的な投資判断はご自身で行ってください。\n"
        
        return message
    
    def send_notifications(self, sell_recommendations: list[dict], 
                          buy_recommendations: list[dict], 
                          output_file: str | None = None):
        """
        通知を送信（現在はコンソール出力とファイル出力）
        
        Args:
            sell_recommendations: 売り推奨リスト
            buy_recommendations: 買い推奨リスト
            output_file: 出力ファイルパス（オプション）
        """
        messages = []
        
        # 売り推奨通知
        if sell_recommendations:
            messages.append(f"\n{'='*60}")
            messages.append(f"売り推奨: {len(sell_recommendations)}件")
            messages.append(f"{'='*60}\n")
            
            for rec in sell_recommendations:
                message = self.format_sell_recommendation(rec)
                messages.append(message)
                print(message)
        else:
            messages.append("\n売り推奨: なし\n")
            print("売り推奨: なし")
        
        # 買い推奨通知
        if buy_recommendations:
            messages.append(f"\n{'='*60}")
            messages.append(f"買い推奨: {len(buy_recommendations)}件")
            messages.append(f"{'='*60}\n")
            
            for rec in buy_recommendations:
                message = self.format_buy_recommendation(rec)
                messages.append(message)
                print(message)
        else:
            messages.append("\n買い推奨: なし\n")
            print("買い推奨: なし")
        
        # ファイル出力
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(messages))
                logger.info(f"通知をファイルに保存しました: {output_file}")
            except Exception as e:
                logger.error(f"ファイル保存エラー: {str(e)}")
    
    def format_portfolio_summary(self, portfolio_summary: dict) -> str:
        """
        ポートフォリオサマリーをフォーマット
        
        Args:
            portfolio_summary: ポートフォリオサマリーデータ
        
        Returns:
            str: フォーマットされたメッセージ
        """
        message = f"""
╔═══════════════════════════════════════════════════════════╗
║              【ポートフォリオサマリー】                    ║
╚═══════════════════════════════════════════════════════════╝

保有銘柄数: {portfolio_summary.get('stock_count', 0)}
合計取得価格: ${portfolio_summary.get('total_purchase_value', 0):,.2f}
合計現在価格: ${portfolio_summary.get('total_current_value', 0):,.2f}
合計損益: ${portfolio_summary.get('total_profit_loss', 0):,.2f}
合計損益率: {portfolio_summary.get('total_profit_loss_rate', 0):.2f}%

更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
