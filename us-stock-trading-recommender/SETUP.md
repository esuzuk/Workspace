# セットアップガイド

## 1. 必要な環境

- **Python 3.10以上**（推奨: Python 3.12以上）
  - Python 3.10以降の型ヒント構文を使用しているため、3.10以上が必要です
  - 最新のPython機能（`list[str]`, `dict[str, int]`, `| None`など）を活用しています
- pip（Pythonパッケージマネージャー）

## 2. インストール手順

### 2.1 リポジトリのクローンまたはダウンロード

```bash
cd /Users/esuzuki/Documents/Workspace/06_Project/us-stock-trading-recommender
```

### 2.2 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2.3 Google Spreadsheet APIの設定（オプション）

Google Spreadsheet連携を使用する場合は、以下の手順を実行してください。

#### ステップ1: Google Cloud Consoleでプロジェクトを作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）

#### ステップ2: Google Sheets APIを有効化

1. 「APIとサービス」→「ライブラリ」に移動
2. "Google Sheets API"を検索して有効化
3. "Google Drive API"も有効化

#### ステップ3: サービスアカウントを作成

1. 「APIとサービス」→「認証情報」に移動
2. 「認証情報を作成」→「サービスアカウント」を選択
3. サービスアカウント名を入力して作成
4. 作成したサービスアカウントをクリック
5. 「キー」タブ→「キーを追加」→「JSONを作成」
6. ダウンロードしたJSONファイルを`credentials.json`としてプロジェクトルートに配置

#### ステップ4: スプレッドシートを作成と共有設定

1. [Google Sheets](https://sheets.google.com/)で新しいスプレッドシートを作成
2. スプレッドシートのURLからIDを取得（例: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`）
3. スプレッドシートの「共有」ボタンをクリック
4. サービスアカウントのメールアドレス（`credentials.json`内の`client_email`）を入力
5. 「編集者」権限を付与して共有

### 2.4 環境変数の設定

`.env`ファイルを作成し、以下を設定：

```bash
# Google Spreadsheet ID（スプレッドシートのURLから取得）
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here

# Google Service Account JSON Key File Path（デフォルト: credentials.json）
GOOGLE_CREDENTIALS_PATH=credentials.json

# Data Fetcher 設定（オプション）
# 詳細は DATA_FETCHER_CONFIG.md を参照
DATA_FETCHER_MAX_RETRIES=3
DATA_FETCHER_RATE_LIMIT_DELAY=0.5
DATA_FETCHER_RETRY_INITIAL_DELAY=1.0
DATA_FETCHER_LOG_LEVEL=INFO
DATA_FETCHER_DEFAULT_PERIOD=6mo
```

**注意**: Data Fetcherの設定はオプションです。デフォルト値で動作しますが、パフォーマンス調整が必要な場合は [DATA_FETCHER_CONFIG.md](DATA_FETCHER_CONFIG.md) を参照してください。

## 3. 使用方法

### 3.1 基本的な使い方

#### 保有株式を登録

```bash
python main.py --register AAPL 10 150.0
```

オプション: 取得日を指定

```bash
python main.py --register AAPL 10 150.0 --purchase-date 2024-01-15
```

#### 価格を更新

```bash
python main.py --update
```

#### 売買シグナルをチェック

```bash
python main.py --check
```

#### 特定銘柄の買いシグナルをチェック

```bash
python main.py --check --watch AAPL MSFT GOOGL
```

#### 保有株式一覧を表示

```bash
python main.py --portfolio
```

#### 投資哲学レポートを生成

```bash
python main.py --philosophy-report AAPL
```

このコマンドは、指定した銘柄について4人の投資家（グレアム、バフェット、オニール、広瀬）の視点から詳細な分析レポートを生成します。

### 3.2 定期実行の設定

cronジョブまたはタスクスケジューラーで定期実行を設定できます。

#### Linux/Mac (cron)

```bash
# 毎日午後6時（市場終了後）に実行
0 18 * * * cd /path/to/us-stock-trading-recommender && python main.py --daily-check >> daily_check.log 2>&1
```

#### Windows (タスクスケジューラー)

1. タスクスケジューラーを開く
2. 「基本タスクの作成」を選択
3. トリガーを「毎日」に設定
4. 操作を「プログラムの開始」に設定
5. プログラム: `python`
6. 引数: `main.py --daily-check`
7. 開始場所: プロジェクトのパス

## 4. トラブルシューティング

### 4.1 Yahoo Finance APIのエラー

- レート制限に達している可能性があります。しばらく待ってから再試行してください。
- ティッカーシンボルが正しいか確認してください（例: AAPL, MSFT, GOOGL）

### 4.2 Google Spreadsheet接続エラー

- `credentials.json`ファイルが正しい場所にあるか確認
- サービスアカウントにスプレッドシートへのアクセス権限があるか確認
- `GOOGLE_SPREADSHEET_ID`が正しく設定されているか確認

### 4.3 ライブラリのインポートエラー

```bash
pip install --upgrade -r requirements.txt
```

## 5. 注意事項

- 本アプリは投資判断の支援ツールであり、投資の最終判断はユーザー自身が行う必要があります
- Yahoo Finance APIは無料ですが、レート制限があります
- データの正確性については保証しません
- 投資損失について一切の責任を負いません
