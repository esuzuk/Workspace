# FX自動売買システム

Python製のFX自動売買システムです。複数のトレード戦略、リスク管理、バックテスト機能を備えています。

## 🎯 対応ブローカー

| ブローカー | ステータス | 特徴 |
|-----------|----------|------|
| **Saxo Bank (サクソバンク証券)** | ✅ 推奨 | OAuth 2.0認証、WebSocket対応、150+通貨ペア |
| SBI証券 | ⏳ API未公開 | 将来対応予定 |

## ⚠️ 重要な注意事項

1. **Saxo Bank Developer Portal**: 本番利用前に [Saxo Developer Portal](https://www.developer.saxo/) でアカウント作成が必要です
2. **シミュレーション環境**: 必ずシミュレーション環境で十分なテストを行ってください
3. **投資リスク**: FX取引には元本を失うリスクがあります。自己責任でご利用ください

## 🚀 クイックスタート

### 1. セットアップ

```bash
cd 06_Project/sbi_fx_trading

# 仮想環境を作成（推奨）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .envファイルを編集
```

### 2. Saxo Bank 認証情報の取得

1. [Saxo Developer Portal](https://www.developer.saxo/) にアクセス
2. アカウントを作成（シミュレーション用は無料）
3. 新しいアプリケーションを登録
4. App Key と App Secret を取得
5. `.env` ファイルに設定:

```env
BROKER=saxo
SAXO_APP_KEY=your_app_key
SAXO_APP_SECRET=your_app_secret
SAXO_ENVIRONMENT=sim  # シミュレーション環境
```

### 3. 実行

```bash
# デモモードでテスト
python3 main.py --mode demo --broker saxo --strategy combined

# バックテスト
python3 main.py --mode backtest --strategy combined --bars 2000

# 利用可能なオプションを確認
python3 main.py --help
```

## 📊 機能

### トレード戦略

| 戦略 | コマンド | 説明 |
|------|---------|------|
| 移動平均クロス | `ma_cross` | ゴールデンクロス/デッドクロスでエントリー |
| RSI平均回帰 | `rsi_reversal` | RSIの買われすぎ/売られすぎを利用 |
| ボリンジャーバンド | `bollinger` | バンドタッチでの反発を狙う |
| MACD | `macd` | MACDラインとシグナルラインのクロス |
| トレンドフォロー | `trend_following` | ADXでトレンド強度を確認 |
| **複合戦略（推奨）** | `combined` | 複数の戦略を組み合わせた高信頼性シグナル |

### テクニカル指標

- **トレンド**: SMA, EMA, WMA, MACD, ADX
- **オシレーター**: RSI, ストキャスティクス, CCI, ウィリアムズ%R
- **ボラティリティ**: ボリンジャーバンド, ATR, ケルトナーチャネル
- **出来高**: OBV, VWAP

### リスク管理

- 1トレードあたりのリスク制限（口座残高の1-2%）
- 最大ドローダウン制限
- 最大同時ポジション数制限
- ATRベースの動的ストップロス
- トレーリングストップ
- 部分決済

## 📁 プロジェクト構造

```
sbi_fx_trading/
├── main.py              # メインエントリーポイント（CLI）
├── config.py            # 設定管理（ブローカー・リスク・戦略設定）
├── api_client.py        # 汎用APIクライアント
├── saxo_client.py       # Saxo Bank OpenAPI クライアント
├── indicators.py        # テクニカル指標（15種類以上）
├── strategy.py          # トレード戦略（6種類）
├── risk_management.py   # リスク管理
├── backtester.py        # バックテストエンジン
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数サンプル
└── README.md            
```

## 🔧 Saxo Bank OpenAPI について

### 認証フロー（OAuth 2.0）

1. アプリケーションが認証URLを生成
2. ユーザーがブラウザでSaxo Bankにログイン
3. 認証コードがリダイレクトURLに返される
4. 認証コードをアクセストークンと交換
5. アクセストークンを使用してAPIにアクセス
6. トークンは自動的にリフレッシュされます

### API エンドポイント

| 機能 | エンドポイント |
|------|---------------|
| 価格取得 | `GET /trade/v1/infoprices` |
| ローソク足 | `GET /chart/v1/charts` |
| 注文発注 | `POST /trade/v2/orders` |
| ポジション | `GET /port/v1/positions/me` |
| 口座情報 | `GET /port/v1/balances` |

### WebSocket ストリーミング

リアルタイム価格データはWebSocketで受信します：

```python
# 価格ストリーミングの開始
await client.start_price_streaming(
    currency_pairs=[CurrencyPair.USDJPY],
    on_tick=handle_tick
)
```

## 📈 バックテスト結果の例

```
======================================================================
バックテスト結果: CombinedStrategy
======================================================================
期間: 2025-09-20 〜 2026-01-11
通貨ペア: USD/JPY

【パフォーマンス】
  初期資金: ¥1,000,000
  最終資金: ¥1,156,320
  総リターン: +15.63%
  年率リターン: +42.85%
  最大ドローダウン: 5.23%

【リスク指標】
  シャープレシオ: 1.85
  ソルティノレシオ: 2.41
  カルマーレシオ: 8.19

【取引統計】
  総取引数: 87
  勝ち: 52 / 負け: 35
  勝率: 59.8%
  プロフィットファクター: 1.72
======================================================================
```

## 🔒 セキュリティ

- OAuth 2.0 + PKCE による安全な認証
- アクセストークンの自動リフレッシュ
- 機密情報は環境変数で管理
- `.env` ファイルはGitにコミットしない

## 📋 コマンドリファレンス

```bash
# デモモード（シミュレーション）
python3 main.py --mode demo --broker saxo

# バックテスト（過去データでテスト）
python3 main.py --mode backtest --strategy combined --bars 3000

# ライブトレード（本番）
python3 main.py --mode live --broker saxo --force

# オプション一覧
python3 main.py --help

# 利用可能な戦略
python3 main.py --list-strategies

# 利用可能なブローカー
python3 main.py --list-brokers
```

## 🔗 参考リンク

- [Saxo Developer Portal](https://www.developer.saxo/)
- [Saxo OpenAPI Documentation](https://www.developer.saxo/openapi/learn)
- [Saxo OpenAPI Python Samples (GitHub)](https://github.com/SaxoBank/openapi-samples-python)

## 📜 免責事項

- 本システムは教育・研究目的で作成されています
- FX取引には元本を失うリスクがあります
- 本システムの使用による損失について、開発者は一切の責任を負いません
- 投資判断は自己責任で行ってください
- 必ずシミュレーション環境で十分なテストを行ってからライブトレードを開始してください

## 📝 ライセンス

このプロジェクトは個人利用を目的としています。
