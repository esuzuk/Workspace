"""
米国株式売買タイミング推奨アプリケーション
CrewAIを使用して複数のエージェントが協力して分析を行う
"""

import os
import yfinance as yf
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from prompts import (
    TECHNICAL_ANALYST_PROMPT,
    FUNDAMENTAL_ANALYST_PROMPT,
    TRADING_ADVISOR_PROMPT,
    REPORT_WRITER_PROMPT
)
from report_generator import ReportGenerator
from dotenv import load_dotenv

# オプション: SerperDevTool（検索機能を使用する場合）
try:
    from crewai_tools import SerperDevTool
    SERPER_AVAILABLE = True
except ImportError:
    SERPER_AVAILABLE = False
    SerperDevTool = None

# 環境変数を読み込み
load_dotenv()


class StockTradingAdvisor:
    """株式売買推奨システム"""
    
    def __init__(self):
        """初期化"""
        # OpenAI APIキーを環境変数から取得
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 検索ツール（オプション）
        self.search_tool = None
        if SERPER_AVAILABLE and os.getenv("SERPER_API_KEY"):
            try:
                self.search_tool = SerperDevTool()
            except Exception:
                self.search_tool = None
        
        # レポート生成器
        self.report_generator = ReportGenerator()
        
        # エージェントを初期化
        self._initialize_agents()
    
    def _initialize_agents(self):
        """エージェントを初期化"""
        tools = []
        if self.search_tool:
            tools.append(self.search_tool)
        
        # テクニカルアナリスト
        self.technical_analyst = Agent(
            role='テクニカルアナリスト',
            goal='株式の価格チャートとテクニカル指標を分析し、売買タイミングを判断する',
            backstory='20年以上の経験を持つテクニカル分析の専門家。チャートパターン、指標、トレンド分析に精通している。',
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=tools
        )
        
        # ファンダメンタルアナリスト
        self.fundamental_analyst = Agent(
            role='ファンダメンタルアナリスト',
            goal='企業の財務状況と業績を分析し、長期的な投資価値を評価する',
            backstory='CFA資格を持つファンダメンタル分析の専門家。財務諸表分析、業界比較、企業評価に精通している。',
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=tools
        )
        
        # トレーディングアドバイザー
        self.trading_advisor = Agent(
            role='トレーディングアドバイザー',
            goal='テクニカル分析とファンダメンタル分析を統合し、具体的な売買戦略を推奨する',
            backstory='15年以上の実務経験を持つトレーディングの専門家。リスク管理とポジションサイジングに精通している。',
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=tools
        )
        
        # レポートライター
        self.report_writer = Agent(
            role='金融レポートライター',
            goal='分析結果を分かりやすく構造化されたレポートとしてまとめる',
            backstory='金融メディアで10年以上の経験を持つライター。複雑な分析を分かりやすく説明する専門家。',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def fetch_stock_data(self, symbol: str, period: str = "1y") -> dict:
        """
        株式データを取得
        
        Args:
            symbol: 株式シンボル（例: 'AAPL', 'MSFT'）
            period: 取得期間（'1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'）
            
        Returns:
            株式データの辞書
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period=period)
            
            # 最新の価格データ
            latest_price = hist['Close'].iloc[-1]
            price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
            price_change_pct = (price_change / hist['Close'].iloc[-2]) * 100
            
            # 移動平均
            ma_20 = hist['Close'].tail(20).mean()
            ma_50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else None
            
            # ボリューム
            avg_volume = hist['Volume'].tail(20).mean()
            latest_volume = hist['Volume'].iloc[-1]
            
            data = {
                'symbol': symbol,
                'company_name': info.get('longName', 'N/A'),
                'current_price': float(latest_price),
                'price_change': float(price_change),
                'price_change_pct': float(price_change_pct),
                'ma_20': float(ma_20),
                'ma_50': float(ma_50) if ma_50 else None,
                'avg_volume': float(avg_volume),
                'latest_volume': float(latest_volume),
                'market_cap': info.get('marketCap', 'N/A'),
                'pe_ratio': info.get('trailingPE', 'N/A'),
                'dividend_yield': info.get('dividendYield', 'N/A'),
                '52_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
                '52_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
                'price_history': hist.to_dict('records')[-30:]  # 直近30日分
            }
            
            return data
        except Exception as e:
            print(f"データ取得エラー: {e}")
            return None
    
    def analyze_stock(self, symbol: str) -> dict:
        """
        株式を分析して推奨を生成
        
        Args:
            symbol: 株式シンボル
            
        Returns:
            分析結果の辞書
        """
        print(f"\n{'='*60}")
        print(f"📊 {symbol} の分析を開始します...")
        print(f"{'='*60}\n")
        
        # 株式データを取得
        stock_data = self.fetch_stock_data(symbol)
        if not stock_data:
            return {"error": "データの取得に失敗しました"}
        
        # データサマリーを作成
        data_summary = f"""
銘柄情報:
- シンボル: {stock_data['symbol']}
- 会社名: {stock_data['company_name']}
- 現在価格: ${stock_data['current_price']:.2f}
- 価格変動: ${stock_data['price_change']:.2f} ({stock_data['price_change_pct']:.2f}%)
- 20日移動平均: ${stock_data['ma_20']:.2f}
- 50日移動平均: ${stock_data['ma_50']:.2f if stock_data['ma_50'] else 'N/A'}
- 平均出来高: {stock_data['avg_volume']:,.0f}
- 時価総額: {stock_data['market_cap']:,.0f if isinstance(stock_data['market_cap'], (int, float)) else 'N/A'}
- P/E比率: {stock_data['pe_ratio'] if isinstance(stock_data['pe_ratio'], (int, float)) else 'N/A'}
- 配当利回り: {stock_data['dividend_yield']*100 if isinstance(stock_data['dividend_yield'], float) else 'N/A'}%
- 52週高値: ${stock_data['52_week_high'] if isinstance(stock_data['52_week_high'], (int, float)) else 'N/A'}
- 52週安値: ${stock_data['52_week_low'] if isinstance(stock_data['52_week_low'], (int, float)) else 'N/A'}
"""
        
        # タスクを定義
        technical_task = Task(
            description=f"""
以下の株式データを分析し、テクニカル分析を行ってください。

{data_summary}

{TECHNICAL_ANALYST_PROMPT}

分析結果には以下を含めてください：
- 現在のトレンド（上昇/下降/横ばい）
- 主要なテクニカル指標の評価
- サポート・レジスタンスレベル
- 売買シグナル（買い/売り/保持）
- エントリーポイントの推奨
""",
            agent=self.technical_analyst,
            expected_output="テクニカル分析結果（トレンド、指標評価、売買シグナル、エントリーポイント）"
        )
        
        fundamental_task = Task(
            description=f"""
以下の株式データを分析し、ファンダメンタル分析を行ってください。

{data_summary}

{FUNDAMENTAL_ANALYST_PROMPT}

分析結果には以下を含めてください：
- 財務状況の評価
- 業績トレンド
- 業界内での位置づけ
- 長期的な成長性
- 投資価値の評価
""",
            agent=self.fundamental_analyst,
            expected_output="ファンダメンタル分析結果（財務評価、業績トレンド、成長性、投資価値）"
        )
        
        trading_task = Task(
            description=f"""
テクニカル分析とファンダメンタル分析の結果を統合し、具体的な売買戦略を推奨してください。

{TRADING_ADVISOR_PROMPT}

推奨事項には以下を含めてください：
- 総合的な判断（買い/売り/保持）
- エントリーポイント（具体的な価格帯）
- エグジットポイント（利確目標価格）
- ストップロス価格
- 推奨ポジションサイズ
- 投資期間（短期/中期/長期）
- リスク要因
""",
            agent=self.trading_advisor,
            expected_output="統合された売買推奨事項（判断、エントリー/エグジットポイント、リスク管理）",
            context=[technical_task, fundamental_task]
        )
        
        report_task = Task(
            description=f"""
テクニカル分析、ファンダメンタル分析、売買推奨の結果を統合し、
分かりやすいレポートを作成してください。

{REPORT_WRITER_PROMPT}

レポートには以下を含めてください：
1. エグゼクティブサマリー（要約）
2. テクニカル分析結果
3. ファンダメンタル分析結果
4. 統合推奨事項
5. リスク要因
6. 結論
""",
            agent=self.report_writer,
            expected_output="構造化された分析レポート（Markdown形式）",
            context=[technical_task, fundamental_task, trading_task]
        )
        
        # クルーを作成して実行
        crew = Crew(
            agents=[
                self.technical_analyst,
                self.fundamental_analyst,
                self.trading_advisor,
                self.report_writer
            ],
            tasks=[
                technical_task,
                fundamental_task,
                trading_task,
                report_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # 分析を実行
        result = crew.kickoff()
        
        # 結果を辞書形式で整理
        analysis_results = {
            'summary': str(result),
            'technical_analysis': technical_task.output.raw if hasattr(technical_task, 'output') else '',
            'fundamental_analysis': fundamental_task.output.raw if hasattr(fundamental_task, 'output') else '',
            'trading_recommendation': trading_task.output.raw if hasattr(trading_task, 'output') else '',
            'risks': '',
            'conclusion': str(result)
        }
        
        return analysis_results
    
    def generate_and_save_report(self, symbol: str) -> str:
        """
        分析を実行してレポートを生成・保存
        
        Args:
            symbol: 株式シンボル
            
        Returns:
            保存されたレポートファイルのパス
        """
        # 分析を実行
        analysis_results = self.analyze_stock(symbol)
        
        if 'error' in analysis_results:
            print(f"❌ エラー: {analysis_results['error']}")
            return None
        
        # レポートを生成
        report = self.report_generator.generate_markdown_report(analysis_results, symbol)
        
        # レポートを保存
        filepath = self.report_generator.save_report(report, symbol)
        
        print(f"\n{'='*60}")
        print(f"✅ レポートが生成されました: {filepath}")
        print(f"{'='*60}\n")
        
        # コンソールにも表示
        print(report)
        
        return filepath


def main():
    """メイン関数"""
    print("=" * 60)
    print("🚀 米国株式売買タイミング推奨アプリケーション")
    print("=" * 60)
    print()
    
    # APIキーの確認
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: OPENAI_API_KEYが設定されていません。")
        print("   .envファイルにOPENAI_API_KEYを設定してください。")
        print()
    
    # アプリケーションを初期化
    advisor = StockTradingAdvisor()
    
    # ユーザー入力を受け取る
    print("分析したい株式シンボルを入力してください（例: AAPL, MSFT, GOOGL）")
    print("終了するには 'exit' と入力してください。")
    print()
    
    while True:
        symbol = input("株式シンボル: ").strip().upper()
        
        if symbol.lower() == 'exit':
            print("\n👋 アプリケーションを終了します。")
            break
        
        if not symbol:
            print("⚠️  シンボルを入力してください。")
            continue
        
        try:
            # 分析とレポート生成
            advisor.generate_and_save_report(symbol)
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()
