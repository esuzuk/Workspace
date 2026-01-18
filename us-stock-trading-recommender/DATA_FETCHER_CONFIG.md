# Data Fetcher 追加設定マニュアル

## 概要

`data_fetcher.py`は、Yahoo Financeから米国株データを取得するモジュールです。このマニュアルでは、パフォーマンス調整やエラーハンドリングのカスタマイズに必要な追加設定について説明します。

## 設定方法

### 1. 環境変数ファイル（.env）の作成・編集

プロジェクトルートに`.env`ファイルを作成（または既存の`.env`ファイルを編集）し、以下の設定を追加します。

```bash
# ============================================
# Data Fetcher 設定
# ============================================

# リトライ回数（デフォルト: 3）
# データ取得に失敗した場合の最大リトライ回数
DATA_FETCHER_MAX_RETRIES=3

# レート制限対策の待機時間（秒）（デフォルト: 0.5）
# Yahoo Finance APIのレート制限を回避するための待機時間
# 値を大きくすると安全ですが、処理時間が長くなります
DATA_FETCHER_RATE_LIMIT_DELAY=0.5

# リトライ時の初期待機時間（秒）（デフォルト: 1.0）
# リトライ時の待機時間の基準値（指数バックオフで増加）
DATA_FETCHER_RETRY_INITIAL_DELAY=1.0

# ログレベル（デフォルト: INFO）
# DEBUG, INFO, WARNING, ERROR, CRITICAL から選択
DATA_FETCHER_LOG_LEVEL=INFO

# データ取得期間のデフォルト値（デフォルト: 6mo）
# 使用可能な値: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
DATA_FETCHER_DEFAULT_PERIOD=6mo
```

## 設定項目の詳細説明

### DATA_FETCHER_MAX_RETRIES

**説明**: データ取得に失敗した場合の最大リトライ回数

**推奨値**:
- **通常使用**: `3`（デフォルト）
- **不安定なネットワーク環境**: `5`
- **安定した環境で高速化**: `2`

**注意事項**:
- 値を大きくしすぎると、エラー時の処理時間が長くなります
- Yahoo Finance APIのレート制限に達している場合、リトライしても成功しません

**例**:
```bash
DATA_FETCHER_MAX_RETRIES=5
```

### DATA_FETCHER_RATE_LIMIT_DELAY

**説明**: Yahoo Finance APIのレート制限を回避するための待機時間（秒）

**推奨値**:
- **通常使用**: `0.5`（デフォルト）
- **レート制限エラーが頻発する場合**: `1.0` または `1.5`
- **高速化が必要な場合**: `0.3`（ただしレート制限のリスクあり）

**注意事項**:
- 値を小さくしすぎると、レート制限エラーが発生する可能性があります
- 複数の銘柄を連続して取得する場合、この待機時間が累積されます
- 10銘柄取得する場合、0.5秒 × 10 = 5秒の待機時間が発生します

**例**:
```bash
DATA_FETCHER_RATE_LIMIT_DELAY=1.0
```

### DATA_FETCHER_RETRY_INITIAL_DELAY

**説明**: リトライ時の初期待機時間（秒）。指数バックオフで増加します

**計算式**: `待機時間 = DATA_FETCHER_RETRY_INITIAL_DELAY × (試行回数)`

**推奨値**:
- **通常使用**: `1.0`（デフォルト）
- **ネットワークが不安定**: `2.0`
- **高速化が必要**: `0.5`

**リトライ時の待機時間例**:
- 1回目のリトライ: 1.0秒
- 2回目のリトライ: 2.0秒
- 3回目のリトライ: 3.0秒

**例**:
```bash
DATA_FETCHER_RETRY_INITIAL_DELAY=2.0
```

### DATA_FETCHER_LOG_LEVEL

**説明**: ログ出力レベル

**使用可能な値**:
- `DEBUG`: 詳細なデバッグ情報（開発時のみ推奨）
- `INFO`: 通常の情報（デフォルト、推奨）
- `WARNING`: 警告のみ
- `ERROR`: エラーのみ
- `CRITICAL`: 重大なエラーのみ

**推奨値**:
- **通常使用**: `INFO`（デフォルト）
- **デバッグ時**: `DEBUG`
- **本番環境**: `WARNING` または `ERROR`

**例**:
```bash
DATA_FETCHER_LOG_LEVEL=DEBUG
```

### DATA_FETCHER_DEFAULT_PERIOD

**説明**: テクニカル指標計算に使用するデータ取得期間のデフォルト値

**使用可能な値**:
- `1d`: 1日
- `5d`: 5日
- `1mo`: 1ヶ月
- `3mo`: 3ヶ月
- `6mo`: 6ヶ月（デフォルト、推奨）
- `1y`: 1年
- `2y`: 2年
- `5y`: 5年
- `10y`: 10年
- `ytd`: 年初来
- `max`: 最大期間

**推奨値**:
- **通常使用**: `6mo`（デフォルト）
- **長期トレンド分析**: `1y` または `2y`
- **短期分析**: `3mo`

**注意事項**:
- 期間が長いほど、移動平均線（特に200日移動平均）の計算に必要なデータが揃います
- 期間が短いほど、データ取得が高速になります

**例**:
```bash
DATA_FETCHER_DEFAULT_PERIOD=1y
```

## 設定例

### 例1: 高速化設定（レート制限のリスクあり）

```bash
DATA_FETCHER_MAX_RETRIES=2
DATA_FETCHER_RATE_LIMIT_DELAY=0.3
DATA_FETCHER_RETRY_INITIAL_DELAY=0.5
DATA_FETCHER_LOG_LEVEL=WARNING
DATA_FETCHER_DEFAULT_PERIOD=3mo
```

**用途**: 少数の銘柄を高速に取得したい場合

### 例2: 安定性重視設定

```bash
DATA_FETCHER_MAX_RETRIES=5
DATA_FETCHER_RATE_LIMIT_DELAY=1.0
DATA_FETCHER_RETRY_INITIAL_DELAY=2.0
DATA_FETCHER_LOG_LEVEL=INFO
DATA_FETCHER_DEFAULT_PERIOD=6mo
```

**用途**: ネットワークが不安定な環境や、多数の銘柄を取得する場合

### 例3: デバッグ設定

```bash
DATA_FETCHER_MAX_RETRIES=3
DATA_FETCHER_RATE_LIMIT_DELAY=0.5
DATA_FETCHER_RETRY_INITIAL_DELAY=1.0
DATA_FETCHER_LOG_LEVEL=DEBUG
DATA_FETCHER_DEFAULT_PERIOD=6mo
```

**用途**: 問題の調査やデバッグ時

## 設定の確認方法

### 1. ログで確認

アプリ起動時に、以下のようなログが出力されます：

```
INFO - USStockDataFetcher初期化完了 - リトライ: 3回, レート制限待機: 0.5秒
```

このログで、現在の設定値を確認できます。

### 2. 環境変数の確認

```bash
# Linux/Mac
cat .env | grep DATA_FETCHER

# Windows
type .env | findstr DATA_FETCHER
```

## トラブルシューティング

### 問題1: レート制限エラーが頻発する

**症状**: `429 Too Many Requests` エラーや `データ取得エラー` が頻繁に発生

**解決方法**:
1. `DATA_FETCHER_RATE_LIMIT_DELAY` を増やす（例: `1.0` または `1.5`）
2. 複数の銘柄を取得する場合は、処理を分散させる

**設定例**:
```bash
DATA_FETCHER_RATE_LIMIT_DELAY=1.5
```

### 問題2: データ取得がタイムアウトする

**症状**: データ取得に時間がかかりすぎる、またはタイムアウトエラー

**解決方法**:
1. `DATA_FETCHER_MAX_RETRIES` を減らす（例: `2`）
2. `DATA_FETCHER_RETRY_INITIAL_DELAY` を減らす（例: `0.5`）
3. ネットワーク接続を確認

**設定例**:
```bash
DATA_FETCHER_MAX_RETRIES=2
DATA_FETCHER_RETRY_INITIAL_DELAY=0.5
```

### 問題3: ログが多すぎる/少なすぎる

**症状**: ログ出力が多すぎて見づらい、または情報が不足している

**解決方法**:
1. `DATA_FETCHER_LOG_LEVEL` を調整
   - ログが多い場合: `WARNING` または `ERROR`
   - ログが少ない場合: `DEBUG` または `INFO`

**設定例**:
```bash
# ログを減らす
DATA_FETCHER_LOG_LEVEL=WARNING

# ログを増やす（デバッグ用）
DATA_FETCHER_LOG_LEVEL=DEBUG
```

### 問題4: 200日移動平均が計算できない

**症状**: `ma_200` が `None` になる

**解決方法**:
1. `DATA_FETCHER_DEFAULT_PERIOD` を長くする（例: `1y` または `2y`）
2. 200日移動平均には最低でも200営業日分のデータが必要です

**設定例**:
```bash
DATA_FETCHER_DEFAULT_PERIOD=1y
```

## パフォーマンス最適化のヒント

### 1. 複数銘柄を取得する場合

多数の銘柄を取得する場合は、以下の設定を推奨します：

```bash
DATA_FETCHER_RATE_LIMIT_DELAY=1.0
DATA_FETCHER_MAX_RETRIES=3
```

### 2. 定期実行時の設定

cronジョブなどで定期実行する場合は、以下の設定を推奨します：

```bash
DATA_FETCHER_RATE_LIMIT_DELAY=0.5
DATA_FETCHER_LOG_LEVEL=WARNING
DATA_FETCHER_MAX_RETRIES=3
```

### 3. 開発・テスト時の設定

開発やテスト時は、以下の設定を推奨します：

```bash
DATA_FETCHER_LOG_LEVEL=DEBUG
DATA_FETCHER_RATE_LIMIT_DELAY=0.5
DATA_FETCHER_MAX_RETRIES=2
```

## ネクストアクション

### ステップ1: .envファイルの作成

プロジェクトルートに`.env`ファイルを作成し、必要な設定を追加してください。

```bash
cd /Users/esuzuki/Documents/Workspace/06_Project/us-stock-trading-recommender
touch .env
```

### ステップ2: 基本設定の追加

`.env`ファイルに、以下の基本設定を追加してください：

```bash
# Data Fetcher 基本設定
DATA_FETCHER_MAX_RETRIES=3
DATA_FETCHER_RATE_LIMIT_DELAY=0.5
DATA_FETCHER_RETRY_INITIAL_DELAY=1.0
DATA_FETCHER_LOG_LEVEL=INFO
DATA_FETCHER_DEFAULT_PERIOD=6mo
```

### ステップ3: 動作確認

設定を反映させるため、アプリを再起動してください：

```bash
python main.py --help
```

起動時に以下のログが表示されれば、設定は正常に読み込まれています：

```
INFO - USStockDataFetcher初期化完了 - リトライ: 3回, レート制限待機: 0.5秒
```

### ステップ4: 必要に応じて調整

実際の使用状況に応じて、設定値を調整してください：

- **レート制限エラーが発生する場合**: `DATA_FETCHER_RATE_LIMIT_DELAY` を増やす
- **処理が遅い場合**: `DATA_FETCHER_RATE_LIMIT_DELAY` を減らす（ただしレート制限のリスクあり）
- **エラーが多い場合**: `DATA_FETCHER_MAX_RETRIES` を増やす

## 注意事項

1. **環境変数の優先順位**: `.env`ファイルの設定が、コード内のデフォルト値を上書きします

2. **設定の反映**: 設定を変更した場合は、アプリを再起動してください

3. **レート制限**: Yahoo Finance APIは無料ですが、レート制限があります。過度なリクエストは避けてください

4. **.envファイルの管理**: `.env`ファイルは`.gitignore`に含まれているため、Gitにはコミットされません。本番環境では別途設定が必要です

## 関連ドキュメント

- [SETUP.md](SETUP.md) - 基本的なセットアップ手順
- [USER_MANUAL.md](USER_MANUAL.md) - 利用マニュアル
- [README.md](README.md) - プロジェクト概要

## サポート

問題が発生した場合は、以下を確認してください：

1. `.env`ファイルが正しい場所にあるか（プロジェクトルート）
2. 環境変数の名前が正しいか（大文字・小文字を区別）
3. 値の形式が正しいか（数値は文字列として記述不要、文字列は引用符不要）
4. アプリを再起動したか

それでも解決しない場合は、ログレベルを`DEBUG`に設定して、詳細なログを確認してください。
