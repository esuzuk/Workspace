"""
Kindle本のスクリーンショット自動取得スクリプト
3秒ごとにスクリーンショットを撮り、右矢印キーでページをめくる
"""
import time
import os
from datetime import datetime
import pyautogui
from PIL import Image

# セーフティ機能：マウスを画面の端に移動すると緊急停止
pyautogui.FAILSAFE = True
# 各操作の間に短い待機時間を追加（デフォルト0.1秒）
pyautogui.PAUSE = 0.5


def capture_screenshots(output_dir: str = "screenshots", num_pages: int = 200, interval: float = 3.0):
    """
    スクリーンショットを自動で取得し、ページをめくる
    
    Args:
        output_dir: 画像を保存するディレクトリ
        num_pages: 取得するページ数
        interval: スクリーンショット間隔（秒）
    """
    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"スクリーンショット取得を開始します...")
    print(f"保存先: {output_dir}")
    print(f"取得ページ数: {num_pages}")
    print(f"間隔: {interval}秒")
    print(f"\n5秒後に開始します。Kindleアプリを前面に表示してください。")
    print("緊急停止する場合は、マウスを画面の左上角に移動してください。\n")
    
    # 5秒のカウントダウン
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("開始！\n")
    
    try:
        for page_num in range(1, num_pages + 1):
            # スクリーンショットを撮る
            screenshot = pyautogui.screenshot()
            
            # ファイル名を生成（連番、ゼロ埋め）
            filename = f"page_{page_num:04d}.png"
            filepath = os.path.join(output_dir, filename)
            
            # 画像を保存
            screenshot.save(filepath)
            print(f"ページ {page_num}/{num_pages} を保存: {filename}")
            
            # 最後のページでなければ、右矢印キーを押してページをめくる
            if page_num < num_pages:
                time.sleep(interval)
                pyautogui.press('right')
                # ページめくりの反映を待つ
                time.sleep(0.5)
        
        print(f"\n完了！{num_pages}ページのスクリーンショットを取得しました。")
        print(f"保存先: {os.path.abspath(output_dir)}")
        
    except KeyboardInterrupt:
        print("\n\nユーザーによって中断されました。")
    except pyautogui.FailSafeException:
        print("\n\nフェイルセーフ機能により停止されました（マウスが画面端に移動）。")
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Kindle本のスクリーンショットを自動取得します'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='screenshots',
        help='画像を保存するディレクトリ（デフォルト: screenshots）'
    )
    parser.add_argument(
        '--num-pages',
        type=int,
        default=200,
        help='取得するページ数（デフォルト: 200）'
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=3.0,
        help='スクリーンショット間隔（秒）（デフォルト: 3.0）'
    )
    
    args = parser.parse_args()
    
    capture_screenshots(
        output_dir=args.output_dir,
        num_pages=args.num_pages,
        interval=args.interval
    )


if __name__ == "__main__":
    main()
