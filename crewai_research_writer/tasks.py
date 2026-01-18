"""
tasks.py - タスク定義モジュール

このモジュールでは、各エージェントに割り当てるタスクを定義します。
タスクは具体的な指示内容と期待される成果物を含みます。

【タスク構成（階層順）】
1. CEO指示解釈タスク: 人間からの指示を理解し、組織全体の方向性を決定
2. PM進捗管理タスク: プロジェクト全体の計画と品質管理
3. 戦略策定タスク: ソーシャルインパクトの視点を設定
4. 調査タスク: トピックに関する包括的な情報収集
5. 企画立案タスク: 調査結果を基に具体的な企画を提案
6. 執筆タスク: すべての成果物を統合した記事・レポート作成
7. 最終レビュータスク: CEOによる最終承認
"""

from crewai import Task, Agent


# =============================================================================
# Level 1: CEO タスク
# =============================================================================

def create_ceo_direction_task(topic: str, user_requirements: str, ceo: Agent) -> Task:
    """
    CEO指示解釈タスクを作成する
    
    人間からの指示を理解し、組織全体の方向性を決定します。
    
    Args:
        topic: 対象トピック
        user_requirements: 人間からの追加要件や指示
        ceo: CEOエージェント
    
    Returns:
        Task: CEO指示解釈タスクのインスタンス
    """
    ceo_direction_task = Task(
        description=f"""あなたはCEOとして、人間からの指示を受け取り、
組織全体の方向性を決定してください。

【人間からの指示】
トピック: {topic}

追加要件・指示:
{user_requirements if user_requirements else "（特になし）"}

【あなたの役割】
1. 人間からの指示の本質を理解する
2. 指示の背後にある真の意図を洞察する
3. 組織全体が目指すべきゴールを明確化する
4. プロジェクトの成功基準を定義する
5. チームへの期待値を設定する

【決定すべき事項】
1. **ビジョンステートメント**
   - このプロジェクトで実現したい未来像
   - 社会に対してどのような価値を提供するか

2. **成功の定義**
   - 何をもってこのプロジェクトを成功とするか
   - 人間が満足する成果物とは何か

3. **重点領域**
   - 特に力を入れるべき領域
   - 絶対に外してはならないポイント

4. **品質基準**
   - 成果物に求める品質レベル
   - 妥協してはならない点

5. **プロジェクトマネージャーへの指示**
   - PMに期待する役割
   - 進捗報告で重視する点
   - リスク管理の方針

【CEOとしての視点】
- 長期的な社会的インパクトを考慮
- ステークホルダー全体の利益を考慮
- 実現可能性と野心的な目標のバランス
- 人間の期待を超える価値の創造""",
        expected_output="""以下の構成でCEO指示書をまとめてください：

# CEO Executive Direction（経営方針書）

## 1. ビジョンステートメント
[このプロジェクトで実現したい未来像を力強く宣言]

## 2. 人間からの指示の解釈
- 明示された要求
- 暗黙の期待
- 真の意図

## 3. 成功の定義
- 最低限達成すべき成果
- 期待を超えるための要素
- 測定可能な成功指標

## 4. 重点領域と優先順位
1. [最優先事項]
2. [高優先事項]
3. [中優先事項]

## 5. 品質基準
- 必須要件
- 推奨事項
- 禁止事項

## 6. プロジェクトマネージャーへの指示
- 役割と責任
- 報告ルール
- 意思決定権限
- エスカレーション基準

## 7. チーム全体へのメッセージ
[リーダーとしての激励と期待]

---
CEO承認: ✓""",
        agent=ceo,
    )
    
    return ceo_direction_task


def create_ceo_final_review_task(topic: str, ceo: Agent, all_previous_tasks: list) -> Task:
    """
    CEO最終レビュータスクを作成する
    
    すべての成果物を確認し、最終承認を行います。
    
    Args:
        topic: 対象トピック
        ceo: CEOエージェント
        all_previous_tasks: すべての先行タスク
    
    Returns:
        Task: CEO最終レビュータスクのインスタンス
    """
    ceo_final_review_task = Task(
        description=f"""あなたはCEOとして、チームが作成したすべての成果物を
レビューし、最終承認を行ってください。

【トピック】
{topic}

【レビュー対象】
- プロジェクトマネージャーの進捗報告
- 戦略ディレクターの戦略策定結果
- リサーチャーの調査レポート
- プランナーの企画書
- ライターの最終記事

【レビューの観点】
1. **人間の指示との整合性**
   - 当初の指示に応えているか
   - 期待を超える価値を提供しているか

2. **品質基準の達成**
   - 設定した品質基準を満たしているか
   - 改善すべき点はないか

3. **ソーシャルインパクト**
   - 社会的価値が明確か
   - 持続可能性は担保されているか

4. **実現可能性**
   - 提案は現実的か
   - リスクは適切に管理されているか

5. **統一性と整合性**
   - 各成果物間で矛盾はないか
   - 全体として一貫したストーリーになっているか

【最終判断】
- 承認：人間に提出可能な品質である
- 条件付き承認：軽微な修正後に提出可能
- 差し戻し：大幅な改善が必要""",
        expected_output="""以下の構成でCEO最終レビュー報告書をまとめてください：

# CEO Final Review Report（最終レビュー報告書）

## Executive Summary
[プロジェクト全体の評価を3行で要約]

## 1. レビュー結果サマリー

| 成果物 | 評価 | コメント |
|--------|------|----------|
| 戦略策定 | ⭐⭐⭐⭐⭐ | ... |
| 調査レポート | ⭐⭐⭐⭐⭐ | ... |
| 企画書 | ⭐⭐⭐⭐⭐ | ... |
| 最終記事 | ⭐⭐⭐⭐⭐ | ... |

## 2. 人間の指示への対応評価
- 達成度: [%]
- 特筆すべき点
- 期待を超えた点

## 3. 品質評価
- 強み
- 改善点
- 次回への提言

## 4. ソーシャルインパクト評価
- 社会的価値の明確性
- 持続可能性
- スケーラビリティ

## 5. CEOコメント
[経営者としての総括コメント]

## 6. 最終判断

**判定: ✅ 承認**

[承認理由と人間へのメッセージ]

---
CEO署名: [CEO Name]
日付: [Date]""",
        agent=ceo,
        context=all_previous_tasks,
    )
    
    return ceo_final_review_task


# =============================================================================
# Level 2: プロジェクトマネージャー タスク
# =============================================================================

def create_pm_planning_task(topic: str, pm: Agent, ceo_direction_task: Task) -> Task:
    """
    PM進捗管理・計画タスクを作成する
    
    CEOの方針に基づき、プロジェクト全体の計画を策定します。
    
    Args:
        topic: 対象トピック
        pm: プロジェクトマネージャーエージェント
        ceo_direction_task: CEO指示解釈タスク
    
    Returns:
        Task: PM計画タスクのインスタンス
    """
    pm_planning_task = Task(
        description=f"""あなたはプロジェクトマネージャーとして、CEOの方針に基づき
プロジェクト全体の実行計画を策定してください。

【トピック】
{topic}

【あなたの役割】
1. CEOの方針を実行可能な計画に落とし込む
2. 各チームメンバーへのタスク割り当て
3. 品質管理基準の設定
4. リスク管理計画の策定
5. 進捗管理の方法を定義

【計画に含めるべき内容】

1. **プロジェクト概要**
   - 目的と目標
   - スコープ定義
   - 成功基準

2. **WBS（Work Breakdown Structure）**
   - 戦略策定フェーズ
   - 調査フェーズ
   - 企画立案フェーズ
   - 執筆フェーズ
   - レビューフェーズ

3. **役割分担**
   - Strategic Director: 戦略策定
   - Researcher: 情報収集
   - Planner: 企画立案
   - Writer: 記事作成

4. **品質管理計画**
   - 各成果物の品質基準
   - レビュープロセス
   - 品質チェックリスト

5. **リスク管理計画**
   - 想定されるリスク
   - 軽減策
   - コンティンジェンシープラン

6. **コミュニケーション計画**
   - CEOへの報告タイミング
   - チーム間の連携方法

【Big4パートナーとしての視点】
- 構造化されたアプローチ
- リスクの先読み
- 品質へのこだわり
- 効率的なリソース配分""",
        expected_output="""以下の構成でプロジェクト計画書をまとめてください：

# Project Management Plan（プロジェクト管理計画書）

## 1. プロジェクト概要
- **プロジェクト名**: [トピックに基づく名称]
- **目的**: 
- **スコープ**: 
- **成功基準**: 

## 2. WBS（Work Breakdown Structure）

### Phase 1: 戦略策定
- タスク内容
- 担当: Strategic Director
- 期待成果物

### Phase 2: 調査
- タスク内容
- 担当: Researcher
- 期待成果物

### Phase 3: 企画立案
- タスク内容
- 担当: Planner
- 期待成果物

### Phase 4: 執筆
- タスク内容
- 担当: Writer
- 期待成果物

### Phase 5: 最終レビュー
- タスク内容
- 担当: CEO
- 期待成果物

## 3. 役割と責任（RACI）

| タスク | CEO | PM | SD | RS | PL | WR |
|--------|-----|----|----|----|----|------|
| 方針決定 | A | R | C | I | I | I |
| 戦略策定 | I | A | R | C | C | I |
| 調査 | I | A | C | R | C | I |
| 企画立案 | I | A | C | C | R | I |
| 執筆 | I | A | C | C | C | R |
| 最終承認 | R | A | I | I | I | I |

※ R:実行責任 A:説明責任 C:相談 I:報告

## 4. 品質管理計画
- 品質基準
- レビュープロセス
- チェックリスト

## 5. リスク管理計画

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| ... | 高/中/低 | 高/中/低 | ... |

## 6. チームへの指示事項
[各チームメンバーへの具体的な指示]

---
PM承認: ✓""",
        agent=pm,
        context=[ceo_direction_task],
    )
    
    return pm_planning_task


# =============================================================================
# Level 3: 実行チーム タスク
# =============================================================================

def create_strategy_task(topic: str, strategic_director: Agent, pm_planning_task: Task) -> Task:
    """
    戦略策定タスクを作成する
    
    Args:
        topic: 対象トピック
        strategic_director: 戦略策定を担当するエージェント
        pm_planning_task: PM計画タスク
    
    Returns:
        Task: 戦略策定タスクのインスタンス
    """
    strategy_task = Task(
        description=f"""CEOの方針とPMの計画に基づき、以下のトピックについて
ソーシャルインパクトを最大化するための戦略的な方向性を策定してください。

【トピック】
{topic}

【策定すべき内容】
1. **社会課題の特定**
   - このトピックに関連する主要な社会課題
   - 誰が困っているのか（ターゲット層）
   - 課題の規模と深刻度

2. **ソーシャルインパクトの方向性**
   - どのような変化（アウトカム）を生み出したいか
   - 短期的・中期的・長期的なインパクト
   - 関連するSDGsゴール

3. **ステークホルダー分析**
   - 主要なステークホルダー
   - それぞれの利害関係と期待
   - 巻き込むべきキープレイヤー

4. **成功の定義**
   - 測定可能な指標（KPI）
   - インパクト評価の観点

5. **調査・企画への指示事項**
   - 重点的に調査すべき項目
   - 企画立案で重視すべきポイント""",
        expected_output="""以下の構成で戦略的方向性をまとめてください：

## 戦略サマリー
[200文字程度で方向性を要約]

## 1. 社会課題の分析
- 特定した課題
- ターゲット層
- 課題の規模感

## 2. 目指すソーシャルインパクト
- 変化の理論（Theory of Change）の概要
- 関連SDGsゴール
- 期待するアウトカム

## 3. ステークホルダーマップ
- 主要プレイヤーと役割

## 4. 成功指標（KPI案）
- 定量指標
- 定性指標

## 5. 調査・企画への指示事項
- 調査で重点的に調べる項目
- 企画で重視するポイント""",
        agent=strategic_director,
        context=[pm_planning_task],
    )
    
    return strategy_task


def create_research_task(topic: str, researcher: Agent, strategy_task: Task) -> Task:
    """
    調査タスクを作成する
    
    Args:
        topic: 調査対象のトピック
        researcher: 調査を担当するエージェント
        strategy_task: 戦略策定タスク
    
    Returns:
        Task: 調査タスクのインスタンス
    """
    research_task = Task(
        description=f"""戦略的方向性を踏まえて、以下のトピックについて包括的な調査を実施してください。

【調査トピック】
{topic}

【調査の進め方】
1. 戦略ディレクターが設定した方向性と指示事項を確認
2. トピックの基本的な定義と概要を調査
3. 関連する社会課題の現状と背景を調査
4. 最新のニュースや動向を検索
5. 先進的な取り組み事例（国内外）を調査
6. 関連する統計データを収集
7. 専門家の意見や分析を探索

【収集すべき情報】
- トピックの背景と現状
- 関連する社会課題の詳細
- 主要なプレイヤーや関係者
- 成功事例と失敗事例
- 最新のトレンドと将来の展望
- 政策動向と規制環境
- 具体的な数字やデータ""",
        expected_output="""以下の構成で調査結果をまとめてください：

## 調査サマリー
[200文字程度でトピックの本質を説明]

## 1. 基本情報
- 定義と背景
- 歴史的経緯

## 2. 社会課題の現状
- 課題の詳細
- 影響を受けている人々
- 課題の規模（データ）

## 3. 現状分析
- 最新の動向
- 主要なプレイヤー
- 統計データ

## 4. 先進事例
- 国内の注目事例（3-5件）
- 海外の注目事例（3-5件）

## 5. トレンドと展望
- 現在のトレンド
- 将来の予測

## 6. 情報源リスト
- 参照した情報源""",
        agent=researcher,
        context=[strategy_task],
    )
    
    return research_task


def create_planning_task(topic: str, planner: Agent, strategy_task: Task, research_task: Task) -> Task:
    """
    企画立案タスクを作成する
    
    Args:
        topic: 企画のテーマ
        planner: 企画立案を担当するエージェント
        strategy_task: 戦略策定タスク
        research_task: 調査タスク
    
    Returns:
        Task: 企画立案タスクのインスタンス
    """
    planning_task = Task(
        description=f"""戦略的方向性と調査結果を踏まえて、
ソーシャルインパクトを生み出す革新的な企画を立案してください。

【企画テーマ】
{topic}

【企画に含めるべき要素】
1. **企画コンセプト**
   - 企画の名称とキャッチコピー
   - コンセプトの説明
   - ターゲット

2. **解決する課題**
   - 具体的な課題の定義
   - なぜこの課題に取り組むのか

3. **ソリューション**
   - 具体的な施策・サービス
   - イノベーションのポイント

4. **実行計画**
   - フェーズ分け
   - 必要なリソース
   - マイルストーン

5. **インパクト設計**
   - 期待するアウトカム
   - KPI

6. **リスクと対策**
   - 想定されるリスク
   - 軽減策""",
        expected_output="""以下の構成で企画書をまとめてください：

# 企画書: [企画名]
**キャッチコピー**: [一言で伝わる価値]

## エグゼクティブサマリー
[300文字程度で企画全体を要約]

## 1. 企画コンセプト
- 背景
- ターゲット
- 提供価値

## 2. 解決する社会課題
- 課題の定義
- 取り組む意義

## 3. ソリューション詳細
- 施策の概要
- イノベーションポイント

## 4. 実行計画
### Phase 1（0-6ヶ月）
### Phase 2（6-18ヶ月）
### Phase 3（18ヶ月以降）

## 5. インパクト設計
- 変化の理論
- KPI

## 6. リスクと対策

| リスク | 対策 |
|--------|------|
| ... | ... |""",
        agent=planner,
        context=[strategy_task, research_task],
    )
    
    return planning_task


def create_writing_task(topic: str, writer: Agent, all_context_tasks: list) -> Task:
    """
    記事執筆タスクを作成する
    
    Args:
        topic: 記事のトピック
        writer: 執筆を担当するエージェント
        all_context_tasks: コンテキストとなるすべてのタスク
    
    Returns:
        Task: 執筆タスクのインスタンス
    """
    writing_task = Task(
        description=f"""すべての成果物を統合して、CEOが求める品質基準を満たす
高品質な記事・レポートを作成してください。

【記事トピック】
{topic}

【記事の目的】
- 社会課題とその解決策への理解を深める
- 提案された企画の価値と実現可能性を伝える
- 読者のアクションを促す

【記事の要件】
1. **読者ターゲット**: 社会課題に関心のあるビジネスパーソン、行政関係者
2. **文体**: プロフェッショナルかつ親しみやすい
3. **長さ**: 3000〜4000文字程度
4. **言語**: 日本語

【記事の構成】
- タイトル: 社会的意義とインパクトが伝わる魅力的なタイトル
- リード文: 課題と解決策の核心を伝える導入
- 社会課題セクション
- 調査結果セクション
- 企画提案セクション
- インパクトセクション
- アクションセクション
- まとめ""",
        expected_output="""以下の形式で記事を作成してください：

# [社会的意義が伝わるタイトル]
**サブタイトル**: [企画の核心を一言で]

## リード文
[150-200文字で、課題と解決策の核心を伝える]

---

## 私たちが直面する課題
[社会課題を「自分ごと化」させる導入]

## 現状を知る：調査から見えてきたこと
[調査結果の要点]

## 解決への道筋：[企画名]の提案
[企画の概要と価値]

## 期待されるインパクト
[この企画が実現したときの変化]

## あなたにできること
[読者へのアクション提案]

## おわりに
[希望あるメッセージ]

---

### 参考情報
[情報源リスト]""",
        agent=writer,
        context=all_context_tasks,
    )
    
    return writing_task


# =============================================================================
# タスク生成関数
# =============================================================================

def create_all_tasks(topic: str, agents: dict, user_requirements: str = "") -> list:
    """
    すべてのタスクを作成して実行順にリストで返す
    
    Args:
        topic: 調査・企画・執筆対象のトピック
        agents: エージェントの辞書
        user_requirements: 人間からの追加要件
    
    Returns:
        list: タスクのリスト（実行順）
    """
    # Level 1: CEO指示解釈
    ceo_direction_task = create_ceo_direction_task(
        topic, user_requirements, agents["ceo"]
    )
    
    # Level 2: PM計画策定
    pm_planning_task = create_pm_planning_task(
        topic, agents["project_manager"], ceo_direction_task
    )
    
    # Level 3: 実行チームタスク
    strategy_task = create_strategy_task(
        topic, agents["strategic_director"], pm_planning_task
    )
    
    research_task = create_research_task(
        topic, agents["researcher"], strategy_task
    )
    
    planning_task = create_planning_task(
        topic, agents["planner"], strategy_task, research_task
    )
    
    writing_task = create_writing_task(
        topic, agents["writer"], 
        [pm_planning_task, strategy_task, research_task, planning_task]
    )
    
    # Level 1: CEO最終レビュー
    ceo_final_review_task = create_ceo_final_review_task(
        topic, agents["ceo"],
        [pm_planning_task, strategy_task, research_task, planning_task, writing_task]
    )
    
    # 実行順にリストで返す
    return [
        ceo_direction_task,      # 1. CEO方針決定
        pm_planning_task,        # 2. PM計画策定
        strategy_task,           # 3. 戦略策定
        research_task,           # 4. 調査
        planning_task,           # 5. 企画立案
        writing_task,            # 6. 執筆
        ceo_final_review_task,   # 7. CEO最終レビュー
    ]


def create_execution_tasks(topic: str, agents: dict, pm_planning_task: Task) -> list:
    """
    実行チームのタスクのみを作成する
    
    Args:
        topic: 対象トピック
        agents: エージェントの辞書
        pm_planning_task: PM計画タスク（コンテキスト）
    
    Returns:
        list: 実行チームのタスクリスト
    """
    strategy_task = create_strategy_task(
        topic, agents["strategic_director"], pm_planning_task
    )
    
    research_task = create_research_task(
        topic, agents["researcher"], strategy_task
    )
    
    planning_task = create_planning_task(
        topic, agents["planner"], strategy_task, research_task
    )
    
    writing_task = create_writing_task(
        topic, agents["writer"],
        [pm_planning_task, strategy_task, research_task, planning_task]
    )
    
    return [strategy_task, research_task, planning_task, writing_task]
