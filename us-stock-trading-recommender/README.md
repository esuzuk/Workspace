# 米国株売買タイミング推奨アプリ

米国株式の売買タイミングを推奨するアプリケーションです。Yahoo Financeからデータを取得し、テクニカル分析に基づいて売買のタイミングを推奨します。

## 主な機能

1. **Yahoo Financeデータ取得**: 米国株のリアルタイム価格とテクニカル指標を取得
2. **保有株式管理**: 銘柄、取得数、取得単価、現在価格、損益をトラッキング
3. **Google Spreadsheet連携**: データを透明性を持って管理
4. **売りタイミング推奨**: 保有株式の売りタイミングを通知
5. **買いタイミング推奨**: 保有していない株式の買いタイミングを通知
6. **根拠の明確な提示**: 使用したデータと判定ロジックを詳細に表示
7. **投資哲学統合分析**: 4人の投資家の哲学に基づいた包括的な分析
   - **ベンジャミン・グレアム**: バリュー投資・安全余裕
   - **ウォーレン・バフェット**: 長期投資・優良企業の選別
   - **ウィリアム・J・オニール**: CAN SLIMメソッド
   - **広瀬隆雄**: 広瀬のプロトコル
8. **ファンダメンタル分析**: 財務指標（P/E、P/B、ROE、EPS、キャッシュフロー等）の分析
9. **投資哲学レポート**: 各投資家の視点からの詳細レポート生成

## 判定ロジック

### 売りシグナル
- 利益確定目標達成（デフォルト: +20%）
- 損切りライン到達（デフォルト: -10%）
- RSI過買い状態（RSI ≥ 70）
- MACD売りシグナル
- 移動平均線デッドクロス
- ボリンジャーバンド上限到達

### 買いシグナル
- RSI過売り状態（RSI ≤ 30）
- MACD買いシグナル
- 移動平均線ゴールデンクロス
- 200日移動平均を上回る
- ボリンジャーバンド下限到達
- 出来高急増

## セットアップ

詳細なセットアップ手順は [SETUP.md](SETUP.md) を参照してください。

### Data Fetcher の追加設定

Yahoo Finance APIのレート制限対策やパフォーマンス調整が必要な場合は、[DATA_FETCHER_CONFIG.md](DATA_FETCHER_CONFIG.md) を参照してください。

## 利用マニュアル

詳細な利用マニュアルは [USER_MANUAL.md](USER_MANUAL.md) を参照してください。

### クイックスタート

1. **依存ライブラリのインストール**
```bash
pip install -r requirements.txt
```

2. **環境変数の設定（オプション）**
`.env`ファイルを作成：
```
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_PATH=credentials.json
```

3. **基本的な使用**
```bash
# 保有株式の登録
python main.py --register AAPL 10 150.0

# 価格を更新
python main.py --update

# 売買推奨の確認
python main.py --check

# 特定銘柄の買いシグナルをチェック
python main.py --check --watch AAPL MSFT GOOGL

# 保有株式一覧を表示
python main.py --portfolio

# 投資哲学レポートを生成
python main.py --philosophy-report AAPL

# 定期実行（cron等で設定）
python main.py --daily-check
```

## プロジェクト構造

```
us-stock-trading-recommender/
├── SOW.md                          # 要件定義書
├── README.md                       # このファイル
├── SETUP.md                        # セットアップガイド
├── USER_MANUAL.md                  # 利用マニュアル
├── INVESTMENT_PHILOSOPHY_VERIFICATION.md  # 投資哲学検証レポート
├── requirements.txt                # 依存ライブラリ
├── .gitignore                      # Git除外ファイル
├── main.py                         # メイン実行ファイル
├── data_fetcher.py                 # Yahoo Financeデータ取得
├── fundamental_analyzer.py         # ファンダメンタル分析
├── investment_philosophy.py        # 投資哲学分析
├── philosophy_report.py            # 投資哲学レポート生成
├── spreadsheet_manager.py          # Google Spreadsheet連携
├── portfolio_manager.py           # 保有株式管理
├── trading_signal.py               # 売買タイミング判定（統合版）
├── notification.py                 # 通知機能
├── utils.py                        # ユーティリティ関数
└── example_usage.py                # 使用例
```

## 使用例

詳細な使用例は `example_usage.py` を参照してください。

```bash
python example_usage.py
```

## 技術スタック

- **Python 3.10+** (推奨: Python 3.12+)
  - Python 3.10以降の型ヒント構文（`list[str]`, `dict[str, int]`, `| None`）を使用
  - 最新のPython機能を活用
- **yfinance**: Yahoo Financeデータ取得
- **gspread**: Google Spreadsheet連携
- **pandas**: データ処理
- **pandas-ta**: テクニカル分析

## 注意事項

- Yahoo Finance APIは無料ですが、レート制限があります
- データの正確性については保証しません
- 本アプリは投資判断の支援ツールであり、投資の最終判断はユーザー自身が行う必要があります
- 投資損失について一切の責任を負いません

## ライセンス

このプロジェクトは個人利用を目的としています。

## 要件定義書

詳細な要件定義は [SOW.md](SOW.md) を参照してください。
