#!/bin/bash
# Run transcription server in WSL

cd "$(dirname "$0")"

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Default args
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9876}"
MODEL="${MODEL:-large-v3}"
TRANSLATOR="${TRANSLATOR:-google}"
TARGET_LANG="${TARGET_LANG:-RU}"

echo "================================"
echo "Voice Analyzer Server"
echo "================================"
echo "Host: $HOST:$PORT"
echo "Model: $MODEL"
echo "Translator: $TRANSLATOR"
echo "Target: $TARGET_LANG"
echo "================================"
echo ""

python -m server.main \
    --host "$HOST" \
    --port "$PORT" \
    --model "$MODEL" \
    --translator "$TRANSLATOR" \
    --target-lang "$TARGET_LANG" \
    "$@"
