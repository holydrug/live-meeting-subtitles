#!/bin/bash
# Voice Analyzer Server
# Works in: Git Bash (Windows), WSL, Linux
#
# Usage:
#   ./server.sh                    # Interactive mode
#   ./server.sh -t parakeet        # Parakeet transcriber
#   ./server.sh --stop             # Stop server

set -e

# Detect environment
detect_env() {
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*) echo "gitbash" ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        *) echo "unknown" ;;
    esac
}

ENV=$(detect_env)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9876}"
TRANSCRIBER="${TRANSCRIBER:-}"
MODEL="${MODEL:-large-v3}"
DEVICE="${DEVICE:-cuda}"
TRANSLATOR="${TRANSLATOR:-}"
TARGET_LANG="${TARGET_LANG:-RU}"
SOURCE_LANG="${SOURCE_LANG:-en}"
INTERACTIVE=false

show_menu() {
    local title="$1"
    shift
    local options=("$@")
    local default=0

    # Output menu to stderr so it displays (stdout is captured)
    echo -e "\n${YELLOW}${title}${NC}" >&2
    for i in "${!options[@]}"; do
        if [ $i -eq $default ]; then
            echo -e "  ${GREEN}> [$((i+1))] ${options[$i]}${NC}" >&2
        else
            echo "    [$((i+1))] ${options[$i]}" >&2
        fi
    done

    read -p "Choose [1-${#options[@]}, default=1]: " choice </dev/tty
    if [ -z "$choice" ]; then
        echo $default
    else
        echo $((choice - 1))
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interactive) INTERACTIVE=true; shift ;;
        -t|--transcriber) TRANSCRIBER="$2"; shift 2 ;;
        --translator) TRANSLATOR="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --stop)
            echo -e "${YELLOW}Stopping server...${NC}"
            if [ "$ENV" = "gitbash" ]; then
                wsl bash -c "pkill -f 'python -m server.main'" 2>/dev/null || true
            else
                pkill -f "python -m server.main" 2>/dev/null || true
            fi
            echo -e "${GREEN}Done.${NC}"
            exit 0
            ;;
        -h|--help)
            echo "Usage: ./server.sh [options]"
            echo "  -i, --interactive   Interactive mode (choose settings)"
            echo "  -t, --transcriber   whisper | parakeet"
            echo "  --translator        google | deepl | local | none"
            echo "  --port              Server port (default: 9876)"
            echo "  --stop              Stop running server"
            echo ""
            echo "Environment: $ENV"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Interactive mode if no transcriber/translator specified
if [ "$INTERACTIVE" = true ] || { [ -z "$TRANSCRIBER" ] && [ -z "$TRANSLATOR" ]; }; then
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Voice Analyzer Server - Setup${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo -e "  Environment: ${GREEN}$ENV${NC}"

    # Transcriber selection
    transcribers=("parakeet  - NVIDIA NeMo (2x faster, recommended)" "whisper   - OpenAI Whisper large-v3")
    t_idx=$(show_menu "Select Transcriber:" "${transcribers[@]}")
    case $t_idx in
        0) TRANSCRIBER="parakeet" ;;
        1) TRANSCRIBER="whisper" ;;
        *) TRANSCRIBER="parakeet" ;;
    esac

    # Translator selection
    translators=("google - Google Translate (free, fast)" "deepl  - DeepL API (needs key)" "local  - NLLB local model (offline)" "none   - No translation")
    tr_idx=$(show_menu "Select Translator:" "${translators[@]}")
    case $tr_idx in
        0) TRANSLATOR="google" ;;
        1) TRANSLATOR="deepl" ;;
        2) TRANSLATOR="local" ;;
        3) TRANSLATOR="none" ;;
        *) TRANSLATOR="google" ;;
    esac

    echo ""
fi

# Apply defaults
[ -z "$TRANSCRIBER" ] && TRANSCRIBER="whisper"
[ -z "$TRANSLATOR" ] && TRANSLATOR="google"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Voice Analyzer Server${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  Host:        $HOST:$PORT"
if [ "$TRANSCRIBER" = "parakeet" ]; then
    echo -e "  Transcriber: ${GREEN}$TRANSCRIBER${NC}"
else
    echo -e "  Transcriber: $TRANSCRIBER"
fi
echo -e "  Translator:  $TRANSLATOR → $TARGET_LANG"
echo -e "  Environment: $ENV"
echo "========================================"
echo ""

# Build command
SERVER_CMD="python -m server.main \
    --host $HOST \
    --port $PORT \
    --transcriber $TRANSCRIBER \
    --model $MODEL \
    --device $DEVICE \
    --translator $TRANSLATOR \
    --target-lang $TARGET_LANG \
    --source-lang $SOURCE_LANG"

# Run based on environment
case $ENV in
    gitbash)
        # Convert Git Bash path to WSL path
        WIN_PATH=$(cygpath -w "$SCRIPT_DIR")
        WSL_PATH=$(wsl wslpath -u "'$WIN_PATH'" | tr -d '\r')
        echo -e "${YELLOW}Running server in WSL...${NC}"
        wsl bash -c "cd '$WSL_PATH' && source venv/bin/activate 2>/dev/null; $SERVER_CMD"
        ;;
    wsl|linux)
        cd "$SCRIPT_DIR"
        [ -d "venv" ] && source venv/bin/activate
        exec $SERVER_CMD
        ;;
    *)
        echo -e "${RED}Unknown environment: $ENV${NC}"
        exit 1
        ;;
esac
