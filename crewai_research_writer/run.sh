#!/bin/bash
# CrewAI プロジェクト実行スクリプト
# 使用方法: ./run.sh "トピック"

cd "$(dirname "$0")"

# トピックが指定されていない場合のデフォルト
TOPIC="${1:-40代の男性がチャレンジすべき、農業ビジネスのフロンティア}"

echo "=========================================="
echo "CrewAI プロジェクト実行"
echo "=========================================="
echo "トピック: $TOPIC"
echo "=========================================="
echo ""

# Ollamaが起動しているか確認
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠ Ollamaが起動していません。起動中..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# プロジェクトを実行
python3 main.py "$TOPIC"
