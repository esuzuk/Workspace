"""
レポート生成モジュール
分析結果を整形してレポートとして出力
"""

import json
from datetime import datetime
from typing import Dict, Any


class ReportGenerator:
    """分析レポートを生成するクラス"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_markdown_report(self, analysis_results: Dict[str, Any], symbol: str) -> str:
        """
        Markdown形式のレポートを生成
        
        Args:
            analysis_results: 分析結果の辞書
            symbol: 株式シンボル
            
        Returns:
            Markdown形式のレポート文字列
        """
        report = f"""# 米国株式売買推奨レポート

**銘柄**: {symbol}  
**生成日時**: {self.timestamp}

---

## 📊 エグゼクティブサマリー

{analysis_results.get('summary', '分析結果がありません')}

---

## 📈 テクニカル分析結果

{analysis_results.get('technical_analysis', 'テクニカル分析結果がありません')}

---

## 💼 ファンダメンタル分析結果

{analysis_results.get('fundamental_analysis', 'ファンダメンタル分析結果がありません')}

---

## 🎯 統合推奨事項

{analysis_results.get('trading_recommendation', '推奨事項がありません')}

---

## ⚠️ リスク要因

{analysis_results.get('risks', 'リスク要因の記載がありません')}

---

## 📝 結論

{analysis_results.get('conclusion', '結論がありません')}

---

*このレポートは自動生成されたものです。投資判断は自己責任で行ってください。*
"""
        return report
    
    def save_report(self, report: str, symbol: str, output_dir: str = "reports") -> str:
        """
        レポートをファイルに保存
        
        Args:
            report: レポート文字列
            symbol: 株式シンボル
            output_dir: 出力ディレクトリ
            
        Returns:
            保存されたファイルパス
        """
        import os
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(output_dir, exist_ok=True)
        
        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{symbol}_{timestamp}.md"
        
        # ファイルに書き込み
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filename
    
    def generate_json_report(self, analysis_results: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        JSON形式のレポートを生成
        
        Args:
            analysis_results: 分析結果の辞書
            symbol: 株式シンボル
            
        Returns:
            JSON形式のレポート辞書
        """
        return {
            "symbol": symbol,
            "timestamp": self.timestamp,
            "summary": analysis_results.get('summary', ''),
            "technical_analysis": analysis_results.get('technical_analysis', ''),
            "fundamental_analysis": analysis_results.get('fundamental_analysis', ''),
            "trading_recommendation": analysis_results.get('trading_recommendation', ''),
            "risks": analysis_results.get('risks', ''),
            "conclusion": analysis_results.get('conclusion', '')
        }
