#!/bin/bash
# Voice Analyzer Client
# Works in: Git Bash (Windows), WSL
# Note: Client requires Windows for WASAPI audio capture
#
# Usage:
#   ./client.sh                    # Interactive mode
#   ./client.sh --list-devices     # List audio devices
#   ./client.sh --no-overlay       # Console only

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
HOST="${HOST:-localhost}"
PORT="${PORT:-9876}"
DEVICE=""
NO_OVERLAY=false
LIST_DEVICES=false
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

show_yesno() {
    local question="$1"
    local default="${2:-y}"

    if [ "$default" = "y" ]; then
        read -p "$question [Y/n]: " answer </dev/tty
        [ -z "$answer" ] && answer="y"
    else
        read -p "$question [y/N]: " answer </dev/tty
        [ -z "$answer" ] && answer="n"
    fi

    [[ "$answer" =~ ^[Yy] ]]
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interactive) INTERACTIVE=true; shift ;;
        --host) HOST="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --device) DEVICE="$2"; shift 2 ;;
        --no-overlay) NO_OVERLAY=true; shift ;;
        --list-devices) LIST_DEVICES=true; shift ;;
        -h|--help)
            echo "Usage: ./client.sh [options]"
            echo "  -i, --interactive   Interactive mode (choose settings)"
            echo "  --host              Server host (default: localhost)"
            echo "  --port              Server port (default: 9876)"
            echo "  --device            Audio device name (partial match)"
            echo "  --no-overlay        Console only mode"
            echo "  --list-devices      List available audio devices"
            echo ""
            echo "Environment: $ENV"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Check environment
if [ "$ENV" = "linux" ]; then
    echo -e "${RED}Error: Client requires Windows for WASAPI audio capture.${NC}"
    echo "Run this from Git Bash or WSL on Windows."
    exit 1
fi

# Helper function to run Windows Python
run_win_python() {
    local args="$@"
    case $ENV in
        gitbash)
            cd "$SCRIPT_DIR"
            if [ -f "venv_win/Scripts/activate" ]; then
                source venv_win/Scripts/activate
            fi
            python -m client.main $args
            ;;
        wsl)
            WIN_PATH=$(wslpath -w "$SCRIPT_DIR")
            # Use cmd.exe to run Python in Windows context
            cmd.exe /c "cd /d \"$WIN_PATH\" && venv_win\\Scripts\\activate.bat && python -m client.main $args" 2>/dev/null || \
            powershell.exe -Command "cd '$WIN_PATH'; if (Test-Path venv_win/Scripts/Activate.ps1) { . ./venv_win/Scripts/Activate.ps1 }; python -m client.main $args"
            ;;
    esac
}

# List devices mode
if [ "$LIST_DEVICES" = true ]; then
    run_win_python --list-devices
    exit 0
fi

# Interactive mode
if [ "$INTERACTIVE" = true ] || [ -z "$DEVICE" ]; then
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Voice Analyzer Client - Setup${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo -e "  Environment: ${GREEN}$ENV${NC}"

    # Get available audio devices
    echo -e "\n${YELLOW}Detecting audio devices...${NC}"

    # Capture device list
    DEVICE_OUTPUT=$(run_win_python --list-devices 2>&1) || true

    # Parse device names (format: "  - Device Name [Loopback]")
    mapfile -t DEVICES < <(echo "$DEVICE_OUTPUT" | grep -E '^\s*-\s+' | sed 's/^\s*-\s*//' | sed 's/\s*\[Loopback\]\s*$//')

    if [ ${#DEVICES[@]} -gt 0 ]; then
        # Find default loopback device (prefer virtual cables, then any)
        DEFAULT_IDX=0
        for i in "${!DEVICES[@]}"; do
            if [[ "${DEVICES[$i]}" =~ (CABLE|VB-Audio|Virtual) ]]; then
                DEFAULT_IDX=$i
                break
            fi
        done

        # Show menu
        echo -e "\n${YELLOW}Select Audio Device:${NC}"
        for i in "${!DEVICES[@]}"; do
            if [ $i -eq $DEFAULT_IDX ]; then
                echo -e "  ${GREEN}> [$((i+1))] ${DEVICES[$i]}${NC}"
            else
                echo "    [$((i+1))] ${DEVICES[$i]}"
            fi
        done

        read -p "Choose [1-${#DEVICES[@]}, default=$((DEFAULT_IDX+1))]: " choice </dev/tty
        if [ -z "$choice" ]; then
            DEV_IDX=$DEFAULT_IDX
        else
            DEV_IDX=$((choice - 1))
        fi

        if [ $DEV_IDX -ge 0 ] && [ $DEV_IDX -lt ${#DEVICES[@]} ]; then
            DEVICE="${DEVICES[$DEV_IDX]}"
            echo -e "  Selected: ${GREEN}$DEVICE${NC}"
        fi
    else
        echo -e "  ${YELLOW}No audio devices found. Using default.${NC}"
    fi

    # Overlay option
    echo ""
    if show_yesno "Enable overlay window?" "y"; then
        NO_OVERLAY=false
    else
        NO_OVERLAY=true
    fi

    echo ""
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Voice Analyzer Client${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  Server:      $HOST:$PORT"
if [ -n "$DEVICE" ]; then
    echo -e "  Device:      ${GREEN}$DEVICE${NC}"
fi
echo -e "  Overlay:     $([ "$NO_OVERLAY" = true ] && echo 'OFF' || echo 'ON')"
echo -e "  Environment: $ENV"
echo "========================================"
echo ""

# Build arguments array
CLIENT_ARGS=(--host "$HOST" --port "$PORT")
[ -n "$DEVICE" ] && CLIENT_ARGS+=(--device "$DEVICE")
[ "$NO_OVERLAY" = true ] && CLIENT_ARGS+=(--no-overlay)

# Run client
case $ENV in
    gitbash)
        cd "$SCRIPT_DIR"
        if [ -f "venv_win/Scripts/activate" ]; then
            source venv_win/Scripts/activate
        fi
        python -m client.main "${CLIENT_ARGS[@]}"
        ;;
    wsl)
        WIN_PATH=$(wslpath -w "$SCRIPT_DIR")
        # Escape device name for PowerShell
        ESCAPED_DEVICE="${DEVICE//\'/\'\'}"
        PS_ARGS="-Host '$HOST' -Port $PORT"
        [ -n "$DEVICE" ] && PS_ARGS="$PS_ARGS -Device '$ESCAPED_DEVICE'"
        [ "$NO_OVERLAY" = true ] && PS_ARGS="$PS_ARGS -NoOverlay"
        powershell.exe -Command "cd '$WIN_PATH'; if (Test-Path venv_win/Scripts/Activate.ps1) { . ./venv_win/Scripts/Activate.ps1 }; python -m client.main $PS_ARGS"
        ;;
esac
