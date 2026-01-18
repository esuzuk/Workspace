# SBI FX α 自動売買ボット（最小実装 / Python）

このフォルダは **SBI証券公式API（REST + WebSocket + OAuth）** を使ったFX自動売買の「土台」を提供します。  
ただし、SBI公式APIの **正確なエンドポイント/メッセージ仕様は環境や契約により異なる** ため、本実装は **URL/パス/購読メッセージを `.env` で差し替え可能** にし、まずは **ペーパーモード（擬似レート）** で動作確認できる構成にしています。

## できること

- OAuthでアクセストークン取得（`client_credentials`想定、設定で変更可）
- WebSocketからティックを受信（接続/再接続/購読送信）
- ティックから足（デフォルト1分）を生成
- SMAクロス（短期SMA > 長期SMAで買い、逆で売り）のシグナル生成
- **paper**: 注文は出さずログに記録  
- **live**: RESTで注文を送信（エンドポイント/ペイロードは最小の雛形）

## セットアップ

```bash
cd /workspace/06_Project/sbi_fx_alpha_trader
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 実行（まずはペーパーモード推奨）

```bash
cd /workspace/06_Project/sbi_fx_alpha_trader
source .venv/bin/activate
python -m sbi_fx_trader run
```

`TRADER_MODE=paper` の場合、擬似的なレート（ランダムウォーク）で足を作り、売買判断と「仮想注文」をログに出します。

## Live接続（SBI公式仕様に合わせて調整が必要）

1. `.env` の以下を **SBI公式APIの仕様に合わせて** 設定
   - `SBI_TOKEN_URL`
   - `SBI_API_BASE_URL` と各 `*_PATH`
   - `SBI_WS_URL`
   - `SBI_WS_SUBSCRIBE_JSON`（購読メッセージ）
2. `TRADER_MODE=live` に変更
3. 実行

```bash
TRADER_MODE=live python -m sbi_fx_trader run
```

## 重要（安全運用の前提）

- **最小数量（例: 1,000通貨）** で開始し、ログと約定状況を必ず確認してください。
- **メンテナンス時間**（SBIの公開情報に従う）を `MAINTENANCE_WINDOWS_JST` に設定してください。
  - 例: `MAINTENANCE_WINDOWS_JST=05:55-06:10,23:55-00:10`
- 本コードは教育/検証用の骨組みです。**損失の可能性**があり、運用責任は利用者にあります。

