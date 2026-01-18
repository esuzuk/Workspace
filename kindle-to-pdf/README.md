# Kindle本をPDF化するツール

Kindleで購入した本をPDF化するための自動化ツールです。サードパーティ製の専用ツール（CalibreやDeDRMなど）を使用せず、生成AIを活用してKindle本をPDF化します。

## 特徴

- **自動スクリーンショット取得**: 指定した間隔で自動的にスクリーンショットを撮影し、ページをめくります
- **画像からPDF変換**: 取得した画像を1つのPDFファイルに結合します
- **OCR機能**: ローカルOCR（Tesseract、APIキー不要）またはAI（GPT-4o/Gemini）を使用してテキストを抽出し、検索可能なPDFを作成します

## セットアップ

### 1. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. Tesseract OCRのインストール（ローカルOCRを使用する場合、推奨）

ローカルOCRを使用する場合、Tesseract本体のインストールが必要です（APIキー不要）：

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

**Windows:**
[GitHubのTesseractリリースページ](https://github.com/UB-Mannheim/tesseract/wiki)からインストーラーをダウンロード

### 3. APIキーの準備（AI OCRを使用する場合のみ）

AI OCRを使用する場合のみ、以下のAPIキーが必要です：

- **OpenAI APIキー**: [OpenAI Platform](https://platform.openai.com/api-keys) で取得
- **Google APIキー**: [Google AI Studio](https://makersuite.google.com/app/apikey) で取得

**注意**: ローカルOCR（Tesseract）を使用する場合は、APIキーは不要です。

## 使用方法

### ステップ1: スクリーンショットの自動取得

1. Kindleアプリを開き、PDF化したい本を表示します
2. 以下のコマンドを実行します：

```bash
python screenshot_capture.py --num-pages 200 --interval 3.0
```

**パラメータ説明:**
- `--num-pages`: 取得するページ数（デフォルト: 200）
- `--interval`: スクリーンショット間隔（秒）（デフォルト: 3.0）
- `--output-dir`: 画像を保存するディレクトリ（デフォルト: screenshots）

**注意事項:**
- 実行開始の5秒前にカウントダウンが表示されます
- その間にKindleアプリを前面に表示してください
- 緊急停止する場合は、マウスを画面の左上角に移動してください

### ステップ2: 画像をPDFに変換

スクリーンショット取得が完了したら、以下のコマンドでPDFに変換します：

```bash
python images_to_pdf.py --input-dir screenshots --output output.pdf
```

**パラメータ説明:**
- `--input-dir`: 画像が保存されているディレクトリ（デフォルト: screenshots）
- `--output`: 出力PDFファイル名（デフォルト: output.pdf）

### ステップ3（オプション）: OCRで検索可能なPDFを作成

テキスト検索ができるPDFを作成する場合：

#### ローカルOCRを使用（推奨、APIキー不要）

```bash
# Tesseract OCRを使用（デフォルト、APIキー不要）
python ocr_pdf.py --input-dir screenshots --output output_searchable.pdf
```

#### AI OCRを使用（APIキー必要）

```bash
# OpenAI GPT-4oを使用する場合
python ocr_pdf.py --input-dir screenshots --output output_searchable.pdf --api-key YOUR_OPENAI_API_KEY --provider openai

# Google Gemini 1.5 Proを使用する場合
python ocr_pdf.py --input-dir screenshots --output output_searchable.pdf --api-key YOUR_GOOGLE_API_KEY --provider gemini

# 環境変数からAPIキーを読み取る場合
export OPENAI_API_KEY="your-api-key"
python ocr_pdf.py --input-dir screenshots --output output_searchable.pdf --provider openai
```

**パラメータ説明:**
- `--input-dir`: 画像が保存されているディレクトリ（デフォルト: screenshots）
- `--output`: 出力PDFファイル名（デフォルト: output_searchable.pdf）
- `--api-key`: APIキー（AI OCRを使用する場合のみ必要、ローカルOCRの場合は不要）
- `--provider`: 使用するOCRプロバイダー（`tesseract`（デフォルト、APIキー不要）、`openai`、`gemini`）

## 実行例

### 基本的な使用例

```bash
# 1. 200ページのスクリーンショットを取得（3秒間隔）
python screenshot_capture.py --num-pages 200 --interval 3.0

# 2. 画像をPDFに変換
python images_to_pdf.py --input-dir screenshots --output my_book.pdf
```

### OCR機能を使用する例

#### ローカルOCRを使用（APIキー不要）

```bash
# 1. スクリーンショット取得
python screenshot_capture.py --num-pages 200

# 2. ローカルOCRで検索可能なPDFを作成（APIキー不要）
python ocr_pdf.py --input-dir screenshots --output my_book_searchable.pdf
```

#### AI OCRを使用（APIキー必要）

```bash
# 1. スクリーンショット取得
python screenshot_capture.py --num-pages 200

# 2. AI OCRで検索可能なPDFを作成
python ocr_pdf.py --input-dir screenshots --output my_book_searchable.pdf --api-key sk-... --provider openai
```

## トラブルシューティング

### スクリーンショットが正しく取得できない場合

- Kindleアプリが前面に表示されていることを確認してください
- 間隔（`--interval`）を長くしてみてください（例: 5.0秒）
- 画面の解像度やズームレベルを確認してください

### OCRがうまく動作しない場合

**ローカルOCR（Tesseract）の場合:**
- Tesseractが正しくインストールされているか確認してください
- 日本語を含む場合は、日本語データパック（tesseract-ocr-jpn）がインストールされているか確認してください
- `pytesseract`がTesseractのパスを見つけられない場合、環境変数`TESSDATA_PREFIX`を設定してください

**AI OCRの場合:**
- APIキーが正しく設定されているか確認してください
- APIの利用制限に達していないか確認してください
- 環境変数からAPIキーを読み取る場合は、正しく設定されているか確認してください

**共通:**
- 画像の品質が低い場合は、スクリーンショットの解像度を上げてください

### PDFのテキストが検索できない場合

- PDFビューアによっては、透明テキストレイヤーの実装が異なる場合があります
- Adobe Acrobat Readerなど、標準的なPDFビューアを使用してください

## 注意事項

- **著作権**: このツールは個人利用を想定しています。著作権法を遵守してください
- **APIコスト**: AI OCRを使用する場合、APIの使用量に応じてコストが発生します（ローカルOCRは無料）
- **処理時間**: OCR処理は時間がかかる場合があります（ローカルOCR: 1ページあたり数秒、AI OCR: 1ページあたり数秒〜数十秒）
- **推奨**: ローカルOCR（Tesseract）を使用することで、APIキー不要で無料でOCR機能を利用できます

## ライセンス

このプロジェクトは個人利用を目的としています。
