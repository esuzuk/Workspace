#!/usr/bin/env python3
"""
クイック実行スクリプト - Cursorから簡単に実行できるようにする
使用方法: python3 quick_run.py "トピック"
"""

import sys
import subprocess
import os

def main():
    # デフォルトトピック
    default_topic = "40代の男性がチャレンジすべき、農業ビジネスのフロンティア"
    
    # コマンドライン引数からトピックを取得
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = default_topic
    
    print("=" * 70)
    print("CrewAI プロジェクト - クイック実行")
    print("=" * 70)
    print(f"トピック: {topic}")
    print("=" * 70)
    print()
    
    # プロジェクトディレクトリに移動
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # main.pyを実行
    try:
        subprocess.run([sys.executable, "main.py", topic], check=True)
    except KeyboardInterrupt:
        print("\n\n⚠ 実行が中断されました")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
