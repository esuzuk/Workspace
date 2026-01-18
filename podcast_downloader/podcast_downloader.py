import feedparser
import requests
import argparse
import os
import re
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence

def fetch_and_parse_feed(feed_url):
    """
    RSSフィードを解析して、エピソードのリストを返す
    """
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            raise Exception("無効なRSSフィードURLです。")
        return feed.entries
    except Exception as e:
        print(f"エラー: {e}")
        return None

def display_episodes(episodes):
    """
    エピソードの一覧を表示する
    """
    if not episodes:
        print("エピソードが見つかりませんでした。")
        return
    
    print("ダウンロード可能なエピソード:")
    for i, entry in enumerate(episodes):
        print(f"{i + 1}: {entry.title}")

def select_episodes(episodes):
    """
    ユーザーにダウンロードしたいエピソードを選択させる
    """
    while True:
        try:
            selection = input("ダウンロードしたいエピソードの番号をカンマ区切りで入力してください (例: 1,3,5): ")
            selected_indices = [int(s.strip()) - 1 for s in selection.split(',')]
            
            if all(0 <= i < len(episodes) for i in selected_indices):
                return [episodes[i] for i in selected_indices]
            else:
                print("無効な番号が入力されました。")
        except ValueError:
            print("数値を入力してください。")

def sanitize_filename(filename):
    """
    ファイル名として使えない文字を削除または置換する
    """
    return re.sub(r'[\/*?:"<>|]',"", filename)

def download_episode(episode, download_dir="downloads"):
    """
    選択されたエピソードをダウンロードする
    """
    topic_match = re.search(r"【COTEN RADIO (.+?)編", episode.title)
    if topic_match:
        topic = sanitize_filename(topic_match.group(1))
        topic_dir = os.path.join(download_dir, topic)
    else:
        topic_dir = os.path.join(download_dir, "その他")

    if not os.path.exists(topic_dir):
        os.makedirs(topic_dir)

    for link in episode.links:
        if link.get('rel') == 'enclosure':
            url = link.get('href')
            if url:
                try:
                    print(f"「{episode.title}」をダウンロードしています...")
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    sanitized_title = sanitize_filename(episode.title)
                    filename = os.path.join(topic_dir, f"{sanitized_title}.mp3")

                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"「{episode.title}」のダウンロードが完了しました。")
                    return
                except requests.exceptions.RequestException as e:
                    print(f"ダウンロードエラー: {e}")
                    return
    
    print(f"「{episode.title}」の音声ファイルが見つかりませんでした。")

def transcribe_audio_files(download_dir="downloads", transcript_dir="transcriptions"):
    """
    ダウンロードされた音声ファイルを文字起こしする
    """
    if not os.path.exists(transcript_dir):
        os.makedirs(transcript_dir)

    r = sr.Recognizer()

    audio_files_found = False
    for root, _, files in os.walk(download_dir):
        for filename in files:
            if not filename.endswith(".mp3") or filename == ".DS_Store":
                continue

            audio_files_found = True
            audio_path = os.path.join(root, filename)
            text_filename = os.path.splitext(filename)[0] + ".txt"
            text_path = os.path.join(transcript_dir, text_filename)

            print(f"\n--- 「{filename}」の文字起こしを開始します --- (時間がかかる場合があります)")
            try:
                audio = AudioSegment.from_mp3(audio_path)
                print(f"  音声ファイルを読み込みました。長さ: {len(audio) / 1000:.2f}秒")
                
                # large files are split into chunks
                chunks = split_on_silence(audio, min_silence_len=500, silence_thresh=-16, keep_silence=True)
                print(f"  音声を {len(chunks)} 個のチャンクに分割しました。")

                full_text = ""
                for i, chunk in enumerate(chunks):
                    chunk_filename = f"chunk_{i}.wav"
                    chunk.export(chunk_filename, format="wav")
                    print(f"  チャンク {i+1}/{len(chunks)} を処理中...")
                    with sr.AudioFile(chunk_filename) as source:
                        audio_listened = r.record(source)
                        try:
                            text = r.recognize_google(audio_listened, language="ja-JP") # 日本語を指定
                            full_text += text + "\n"
                            print(f"    認識結果 (チャンク {i+1}): {text[:50]}...") # 最初の50文字を表示
                        except sr.UnknownValueError:
                            print(f"    [警告] 音声が認識できませんでした (チャンク {i+1})")
                        except sr.RequestError as e:
                            print(f"    [エラー] Google Speech Recognitionサービスに接続できませんでした; {e}")
                    os.remove(chunk_filename) # チャンクファイルを削除
                
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                print(f"--- 「{filename}」の文字起こしが完了し、「{text_filename}」に保存されました。---")

            except Exception as e:
                print(f"[致命的なエラー] 文字起こしエラー: 「{filename}」 - {e}")
    
    if not audio_files_found:
        print("downloads フォルダにMP3ファイルが見つかりませんでした。")

def main():
    """
    メイン処理
    """
    parser = argparse.ArgumentParser(description="ポッドキャストの音源をダウンロードし、文字起こしします。")
    parser.add_argument("feed_url", nargs='?', help="ポッドキャストのRSSフィードURL")
    parser.add_argument("--list-episodes", action="store_true", help="エピソードの一覧を表示して終了します。")
    parser.add_argument("--download-episodes", help="ダウンロードしたいエピソードの番号をカンマ区切りで指定します。")
    parser.add_argument("--download-all", action="store_true", help="すべてのエピソードをダウンロードします。")
    parser.add_argument("--transcribe", action="store_true", help="ダウンロード済みの音声ファイルを文字起こしします。")
    args = parser.parse_args()

    if args.transcribe:
        transcribe_audio_files()
        return

    if not args.feed_url:
        parser.error("feed_url が指定されていません。文字起こしのみを行う場合は --transcribe オプションを使用してください。")

    episodes = fetch_and_parse_feed(args.feed_url)
    if not episodes:
        return

    if args.list_episodes:
        display_episodes(episodes)
        return

    selected_episodes = []
    if args.download_all:
        selected_episodes = episodes
    elif args.download_episodes:
        try:
            selected_indices = [int(s.strip()) - 1 for s in args.download_episodes.split(',')]
            if all(0 <= i < len(episodes) for i in selected_indices):
                selected_episodes = [episodes[i] for i in selected_indices]
            else:
                print("無効な番号が入力されました。")
                return
        except ValueError:
            print("数値を入力してください。")
            return
    else:
        display_episodes(episodes)
        selected_episodes = select_episodes(episodes)

    for episode in selected_episodes:
        download_episode(episode)

if __name__ == "__main__":
    main()