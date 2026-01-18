"""
main.py - CrewAI 自律型AIエージェントシステム 実行エントリーポイント

このスクリプトは、階層構造を持つAIエージェントチームを協調させて、
指定されたトピックについて調査・企画立案・記事作成を自動で行います。

【組織階層構造】
┌─────────────────────────────────────────────────────────────┐
│  Level 1: CEO（最高経営責任者）                              │
│           └─ 人間からの指示を受ける唯一のルート              │
├─────────────────────────────────────────────────────────────┤
│  Level 2: Project Manager（プロジェクトマネージャー）        │
│           └─ 全体の進捗管理と品質保証                        │
├─────────────────────────────────────────────────────────────┤
│  Level 3: 実行チーム                                         │
│           ├─ Strategic Director（戦略ディレクター）          │
│           ├─ Researcher（調査員）                            │
│           ├─ Planner（企画立案者）                           │
│           └─ Writer（ライター）                              │
└─────────────────────────────────────────────────────────────┘

使用方法:
    python main.py

必要な環境変数:
    - OPENAI_API_KEY: OpenAI APIキー
    - SERPER_API_KEY: Serper APIキー（Google検索用）
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from crewai import Crew, Process

from agents import get_all_agents, get_ceo
from tasks import create_all_tasks


def setup_llm():
    """
    LLMを設定する（Ollama優先、なければOpenAI）
    CrewAIは環境変数からLLM設定を読み込む
    """
    load_dotenv()
    
    # Ollamaが利用可能か確認
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✓ Ollamaが検出されました（ローカルLLMモード）")
            # CrewAIでOllamaを使用するための環境変数設定
            # CrewAIはOPENAI_API_BASEとOPENAI_MODEL_NAMEを使用してOllamaに接続できる
            os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
            os.environ["OPENAI_MODEL_NAME"] = "llama3.2"
            # ダミーのAPIキーを設定（Ollamaは実際には使用しないが、CrewAIが要求する場合がある）
            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = "ollama"  # ダミーキー
            return True
    except Exception as e:
        print(f"⚠ Ollama接続エラー: {e}")
    
    # OpenAI APIキーが設定されている場合
    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "ollama":
        print("✓ OpenAI APIキーが設定されています")
        return True
    
    # どちらも利用できない場合
    print("⚠ 警告: APIキーが設定されておらず、Ollamaも利用できません")
    print("   ローカルLLM（Ollama）を使用することを推奨します")
    return False


def load_environment():
    """
    環境変数を読み込み、設定を確認する
    """
    load_dotenv()
    
    # LLM設定
    setup_llm()
    
    # 検索APIキーはオプショナル
    if not os.getenv("SERPER_API_KEY"):
        print("⚠ 警告: SERPER_API_KEYが設定されていません")
        print("   検索機能は使用できませんが、事前定義された情報で動作します")
    
    print("✓ 環境設定を読み込みました")


def print_header():
    """
    アプリケーションヘッダーを表示する
    """
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  CrewAI 自律型AIエージェントシステム".center(60) + "        ║")
    print("║" + "  ～ ソーシャルインパクト企画 AI チーム ～".center(56) + "        ║")
    print("║" + " " * 68 + "║")
    print("╠" + "═" * 68 + "╣")
    print("║" + " " * 68 + "║")
    print("║  【組織階層構造】" + " " * 50 + "║")
    print("║" + " " * 68 + "║")
    print("║  Level 1: 👔 CEO（最高経営責任者）" + " " * 32 + "║")
    print("║          └─ Forbes500級のビジョナリーリーダー" + " " * 21 + "║")
    print("║          └─ 人間からの指示を受ける唯一のルート" + " " * 18 + "║")
    print("║" + " " * 68 + "║")
    print("║  Level 2: 📊 Project Manager" + " " * 38 + "║")
    print("║          └─ Big4パートナー級のプロジェクト管理" + " " * 19 + "║")
    print("║" + " " * 68 + "║")
    print("║  Level 3: 実行チーム" + " " * 47 + "║")
    print("║          ├─ 🎯 Strategic Director（戦略ディレクター）" + " " * 14 + "║")
    print("║          ├─ 🔍 Researcher（調査員）" + " " * 30 + "║")
    print("║          ├─ 💡 Planner（企画立案者）" + " " * 28 + "║")
    print("║          └─ ✍️  Writer（ライター）" + " " * 30 + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()


def get_topic_from_user() -> str:
    """
    ユーザーからトピックを入力させる
    
    Returns:
        str: 入力されたトピック
    """
    print("-" * 70)
    print()
    print("【CEOへの指示】")
    print("調査・企画立案したいトピックを入力してください。")
    print("CEOがあなたの指示を解釈し、チーム全体を動かします。")
    print()
    print("例:")
    print("  ・「フードロス削減のための新しい取り組み」")
    print("  ・「高齢者の孤立を防ぐコミュニティづくり」")
    print("  ・「地方創生とテクノロジーの活用」")
    print("  ・「子どもの教育格差を解消する方法」")
    print()
    
    while True:
        topic = input("📝 トピック: ").strip()
        if topic:
            return topic
        print("⚠ トピックを入力してください")


def get_additional_requirements() -> str:
    """
    追加の要件・指示を入力させる
    
    Returns:
        str: 追加要件（なければ空文字）
    """
    print()
    print("-" * 70)
    print()
    print("【追加の要件・指示】（任意）")
    print("特に重視してほしい点や、追加の要件があれば入力してください。")
    print("（なければEnterキーを押してスキップ）")
    print()
    
    requirements = input("📋 追加要件: ").strip()
    return requirements


def select_process_mode() -> Process:
    """
    実行モードを選択させる
    
    Returns:
        Process: 選択されたプロセスモード
    """
    print()
    print("-" * 70)
    print()
    print("【実行モード選択】")
    print()
    print("  [1] Sequential（順次実行）- 推奨")
    print("      → 各エージェントが順番にタスクを実行")
    print("      → CEOの指示 → PM計画 → 実行 → CEOレビュー")
    print()
    print("  [2] Hierarchical（階層的実行）")
    print("      → CEOがマネージャーとして全体を動的に監督")
    print("      → より柔軟だが、トークン消費が多い")
    print()
    
    while True:
        choice = input("選択 (1 または 2、デフォルト: 1): ").strip()
        if choice == "" or choice == "1":
            print("→ Sequential モードを選択しました")
            return Process.sequential
        elif choice == "2":
            print("→ Hierarchical モードを選択しました")
            return Process.hierarchical
        else:
            print("⚠ 1 または 2 を入力してください")


def run_crew(topic: str, user_requirements: str, process_mode: Process) -> str:
    """
    CrewAIを実行してタスクを遂行する
    
    Args:
        topic: 調査・企画対象のトピック
        user_requirements: 人間からの追加要件
        process_mode: 実行プロセスモード
    
    Returns:
        str: 生成されたレポート
    """
    print()
    print("=" * 70)
    print("【プロジェクト情報】")
    print("=" * 70)
    print(f"  トピック: {topic}")
    if user_requirements:
        print(f"  追加要件: {user_requirements}")
    print(f"  実行モード: {process_mode.value}")
    
    # LLM設定を表示
    if os.getenv("OPENAI_API_BASE") and "localhost:11434" in os.getenv("OPENAI_API_BASE", ""):
        print(f"  LLM: Ollama (llama3.2)")
    elif os.getenv("OPENAI_API_KEY"):
        print(f"  LLM: OpenAI ({os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')})")
    else:
        print(f"  LLM: デフォルト設定")
    
    print("=" * 70)
    print()
    print("🚀 AIエージェントチームを起動しています...")
    print()
    
    # すべてのエージェントを作成
    agents = get_all_agents()
    
    print("✓ エージェント準備完了:")
    print()
    print("  【Level 1: 経営層】")
    print(f"    👔 CEO: {agents['ceo'].role}")
    print()
    print("  【Level 2: 管理層】")
    print(f"    📊 PM: {agents['project_manager'].role}")
    print()
    print("  【Level 3: 実行チーム】")
    print(f"    🎯 {agents['strategic_director'].role}")
    print(f"    🔍 {agents['researcher'].role}")
    print(f"    💡 {agents['planner'].role}")
    print(f"    ✍️  {agents['writer'].role}")
    print()
    
    # タスクを作成
    tasks = create_all_tasks(topic, agents, user_requirements)
    print(f"✓ タスク準備完了: {len(tasks)}個のタスク")
    print()
    print("  【実行フロー】")
    task_names = [
        "1. CEO方針決定",
        "2. PM計画策定",
        "3. 戦略策定",
        "4. 調査",
        "5. 企画立案",
        "6. 執筆",
        "7. CEO最終レビュー"
    ]
    for name in task_names:
        print(f"    {name}")
    print()
    
    # Crewを作成（タイムアウト設定を追加）
    if process_mode == Process.hierarchical:
        ceo = get_ceo()
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.hierarchical,
            manager_agent=ceo,
            verbose=True,
            max_iter=15,  # 最大反復回数を増やす
            max_execution_time=3600,  # 最大実行時間を1時間に設定
        )
        print("✓ Crew作成完了（Hierarchicalモード、マネージャー: CEO）")
    else:
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            max_iter=15,  # 最大反復回数を増やす
            max_execution_time=3600,  # 最大実行時間を1時間に設定
        )
        print("✓ Crew作成完了（Sequentialモード）")
    
    print()
    print("=" * 70)
    print("タスク実行開始")
    print("=" * 70)
    print()
    print("💼 CEOが人間からの指示を受け取りました...")
    print()
    
    # Crewを実行
    result = crew.kickoff()
    
    return str(result)


def save_result(topic: str, user_requirements: str, result: str, process_mode: Process) -> str:
    """
    結果をファイルに保存する
    
    Args:
        topic: トピック名
        user_requirements: 追加要件
        result: 生成された内容
        process_mode: 使用したプロセスモード
    
    Returns:
        str: 保存したファイルのパス
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "hierarchical" if process_mode == Process.hierarchical else "sequential"
    safe_topic = "".join(c if c.isalnum() or c in "ぁ-んァ-ン一-龥" else "_" for c in topic[:30])
    filename = f"{output_dir}/report_{timestamp}_{mode_suffix}_{safe_topic}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# ソーシャルインパクト企画レポート\n\n")
        f.write(f"## プロジェクト情報\n\n")
        f.write(f"- **トピック**: {topic}\n")
        if user_requirements:
            f.write(f"- **追加要件**: {user_requirements}\n")
        f.write(f"- **生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
        f.write(f"- **実行モード**: {process_mode.value}\n")
        f.write(f"- **AIチーム構成**: CEO → PM → Strategic Director, Researcher, Planner, Writer\n\n")
        f.write("---\n\n")
        f.write(result)
    
    print(f"✓ レポートを保存しました: {filename}")
    return filename


def main():
    """
    メイン実行関数
    """
    try:
        # 環境変数を読み込む
        load_environment()
        
        # ヘッダーを表示
        print_header()
        
        # コマンドライン引数からトピックを取得（指定されている場合）
        if len(sys.argv) > 1:
            topic = " ".join(sys.argv[1:])
            print(f"📝 トピック（コマンドライン引数から）: {topic}")
            user_requirements = ""
            process_mode = Process.sequential
            print("→ Sequential モードで実行します")
        else:
            # ユーザーからトピックを取得
            topic = get_topic_from_user()
            
            # 追加要件を取得
            user_requirements = get_additional_requirements()
            
            # 実行モードを選択
            process_mode = select_process_mode()
        
        # Crewを実行
        result = run_crew(topic, user_requirements, process_mode)
        
        # 結果を表示
        print()
        print("=" * 70)
        print("📝 生成されたレポート")
        print("=" * 70)
        print()
        print(result)
        print()
        
        # 結果を保存
        filename = save_result(topic, user_requirements, result, process_mode)
        
        print()
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║  ✅ プロジェクト完了！".ljust(67) + "║")
        print("║" + " " * 68 + "║")
        print(f"║  📄 ファイル: {filename}".ljust(67) + "║")
        print("║" + " " * 68 + "║")
        print("║  CEOからのメッセージ:" + " " * 45 + "║")
        print("║  「チーム全員の努力により、素晴らしい成果物が完成しました。」" + " " * 2 + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "═" * 68 + "╝")
        
    except KeyboardInterrupt:
        print("\n\n⚠ 処理が中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()
