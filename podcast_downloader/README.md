# Podcast Downloader

## 概要

このアプリケーションは、指定したポッドキャストのRSSフィードから音声データをダウンロードするためのコマンドラインツールです。

## インストール方法

1.  **リポジトリのクローン:**
    ```bash
    git clone https://github.com/your_username/podcast_downloader.git
    cd podcast_downloader
    ```

2.  **必要なライブラリのインストール:**
    ```bash
    python3 -m pip install feedparser requests
    ```

## 使い方

以下のコマンドを実行します。

```bash
python3 podcast_downloader.py [RSSフィードのURL] [オプション]
```

### オプション

*   `--list-episodes`: エピソードの一覧だけを表示して終了します。
*   `--download-episodes <番号,番号,...>`: ダウンロードしたいエピソードの番号をカンマ区切りで指定します。このオプションを使用しない場合、エピソード一覧表示後に手動で番号を入力するプロンプトが表示されます。

### 実行例

```bash
python3 podcast_downloader.py https://www.nhk.or.jp/radio/rss/r-gogaku.xml
```

実行すると、ダウンロード可能なエピソードの一覧が表示され、ダウンロードしたいエピソードの番号をカンマ区切りで入力するプロンプトが表示されます。

```
ダウンロード可能なエピソード:
1: まいにちハングル講座
2: まいにち中国語
3: 基礎英語
...
ダウンロードしたいエピソードの番号をカンマ区切りで入力してください (例: 1,3,5): 1,2
```

ダウンロードが完了すると、`downloads`フォルダに音声ファイルが保存されます。

## 使用事例: COTEN RADIOのダウンロード

「歴史を面白く学ぶコテンラジオ （COTEN RADIO）」のエピソードをダウンロードする手順を説明します。

1.  **COTEN RADIOのRSSフィードURLの確認**
    COTEN RADIOのRSSフィードURLは `https://anchor.fm/s/8c2088c/podcast/rss` です。

2.  **エピソード一覧の表示**
    まず、ダウンロード可能なエピソードの一覧を確認します。以下のコマンドを実行してください。
    ```bash
    python3 podcast_downloader.py https://anchor.fm/s/8c2088c/podcast/rss --list-episodes
    ```
    これにより、エピソードのタイトルと番号が一覧で表示されます。

3.  **特定のエピソードのダウンロード**
    例えば、「1-1 吉田松陰が脱藩した衝撃の理由！」（番号649）をダウンロードしたい場合、以下のコマンドを実行します。
    ```bash
    python3 podcast_downloader.py https://anchor.fm/s/8c2088c/podcast/rss --download-episodes 649
    ```
    複数のエピソードをダウンロードしたい場合は、番号をカンマ区切りで指定します。例えば、エピソード649、648、646をダウンロードする場合は以下のようになります。
    ```bash
    python3 podcast_downloader.py https://anchor.fm/s/8c2088c/podcast/rss --download-episodes 649,648,646
    ```

ダウンロードが完了すると、`downloads`フォルダに音声ファイルが保存されます。