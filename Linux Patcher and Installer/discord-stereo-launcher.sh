#!/usr/bin/env bash
################################################################################
# Discord Stereo Linux Launcher
# Updates three files in "Linux Stereo Installer/" then runs the Python GUI.
# No backups: old files are replaced when content differs.
################################################################################

if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
INSTALL_DIR_NAME="Linux Stereo Installer"
BASE_URL="https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Linux%20Patcher%20and%20Installer/Updates"

# Format: "filename|url_path" (url_path is the filename under BASE_URL)
FILES=(
    "Discord_Stereo_Installer_For_Linux.py|Discord_Stereo_Installer_For_Linux.py"
    "Stereo-Installer-Linux.sh|Stereo-Installer-Linux.sh"
    "discord_voice_patcher_linux.sh|discord_voice_patcher_linux.sh"
)

# ------------------------------------------------------------------------------
# Colors (ANSI; no Unicode)
# ------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[0;90m'
NC='\033[0m'

# ------------------------------------------------------------------------------
# Flags
# ------------------------------------------------------------------------------
NO_UPDATE=false
FORCE=false

# ------------------------------------------------------------------------------
# Usage
# ------------------------------------------------------------------------------
usage() {
    echo -e "${BOLD}Discord Stereo Linux Launcher${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --no-update, -n   Skip download; run existing files only"
    echo "  --force, -f       Force redownload and overwrite all three files"
    echo "  --help, -h        Show this help"
    echo ""
    echo "Files are stored in: $INSTALL_DIR_NAME/ (next to this script)"
    exit 0
}

for arg in "$@"; do
    case "$arg" in
        --no-update|-n) NO_UPDATE=true ;;
        --force|-f)     FORCE=true ;;
        --help|-h)      usage ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}" >&2
            usage
            ;;
    esac
done

# Script directory (works with symlinks and any cwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/${INSTALL_DIR_NAME}"

# ------------------------------------------------------------------------------
# Hash helper (sha256sum on most distros; shasum -a 256 on Alpine/macOS)
# ------------------------------------------------------------------------------
get_sha256() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum < "$file" 2>/dev/null | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 < "$file" 2>/dev/null | cut -d' ' -f1
    else
        echo ""
    fi
}

# ------------------------------------------------------------------------------
# Download with retries; validate size and content before replacing
# ------------------------------------------------------------------------------
CURL_CONNECT_TIMEOUT=15
CURL_MAX_TIME=120
CURL_RETRIES=3
MIN_FILE_SIZE=100

download_file() {
    local url="$1"
    local tmp="$2"
    local ret=1
    local i=1
    while [ "$i" -le "$CURL_RETRIES" ]; do
        if curl -sSfL --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" \
            -o "$tmp" "$url" 2>/dev/null; then
            ret=0
            break
        fi
        i=$(( i + 1 ))
        [ "$i" -le "$CURL_RETRIES" ] && sleep 2
    done
    return $ret
}

# Ensure downloaded file is valid (non-empty, minimum size, not HTML error page)
validate_download() {
    local tmp="$1"
    local filename="$2"
    local size
    size=$(wc -c < "$tmp" 2>/dev/null || echo 0)
    if [ -z "$size" ] || [ "$size" -lt "$MIN_FILE_SIZE" ]; then
        return 1
    fi
    if head -1 "$tmp" 2>/dev/null | grep -qi '<html\|<!doctype'; then
        return 1
    fi
    case "$filename" in
        *.py) head -1 "$tmp" 2>/dev/null | grep -q 'python\|Python\|#' || return 1 ;;
        *.sh) head -1 "$tmp" 2>/dev/null | grep -q '^#!' || return 1 ;;
    esac
    return 0
}

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}${BOLD}===== Discord Stereo Linux Launcher =====${NC}"
echo -e "${DIM}48 kHz | 384 kbps | Stereo${NC}"
echo ""

mkdir -p "$INSTALL_DIR"

# ------------------------------------------------------------------------------
# Update step (unless --no-update)
# ------------------------------------------------------------------------------
if $NO_UPDATE; then
    echo -e "${DIM}[--no-update] Skipping update check.${NC}"
else
    echo -e "${CYAN}Checking for updates...${NC}"
    HAVE_NET=false
    UPDATED=0
    TOTAL=${#FILES[@]}

    for entry in "${FILES[@]}"; do
        IFS='|' read -r filename url_path <<< "$entry"
        url="${BASE_URL}/${url_path}"
        dest="${INSTALL_DIR}/${filename}"

        # Portable temp file (Linux: mktemp; fallback for older systems)
        tmp=""
        if tmp=$(mktemp 2>/dev/null); then
            :
        elif tmp=$(mktemp -t "discord-stereo.XXXXXX" 2>/dev/null); then
            :
        else
            tmp="${INSTALL_DIR}/.tmp.$$.${filename}"
        fi

        if ! download_file "$url" "$tmp"; then
            rm -f "$tmp"
            echo -e "${YELLOW}  [!] Could not download: $filename (network error or timeout)${NC}" >&2
            continue
        fi
        HAVE_NET=true

        if ! validate_download "$tmp" "$filename"; then
            rm -f "$tmp"
            echo -e "${YELLOW}  [!] Download invalid or truncated: $filename (skipping)${NC}" >&2
            continue
        fi

        replace=false
        if [ ! -f "$dest" ]; then
            replace=true
        elif $FORCE; then
            replace=true
        else
            old_hash=$(get_sha256 "$dest")
            new_hash=$(get_sha256 "$tmp")
            if [ -z "$new_hash" ] || [ "$old_hash" != "$new_hash" ]; then
                replace=true
            fi
        fi

        if $replace; then
            rm -f "$dest"
            mv "$tmp" "$dest"
            case "$filename" in
                *.sh) chmod +x "$dest" ;;
            esac
            UPDATED=$(( UPDATED + 1 ))
            echo -e "${GREEN}  [OK] Updated: $filename${NC}"
        else
            rm -f "$tmp"
            echo -e "${DIM}  [skip] Unchanged: $filename${NC}"
        fi
    done

    if ! $HAVE_NET; then
        echo -e "${YELLOW}[!] No internet - using existing files if present.${NC}"
    elif [ "$UPDATED" -gt 0 ]; then
        echo -e "${GREEN}Updated $UPDATED/$TOTAL file(s).${NC}"
    else
        echo -e "${DIM}All files up to date.${NC}"
    fi
    echo ""
fi

# ------------------------------------------------------------------------------
# Launch (must run from install dir so Python finds the .sh scripts)
# ------------------------------------------------------------------------------
cd "$INSTALL_DIR"

if [ ! -f "Discord_Stereo_Installer_For_Linux.py" ]; then
    echo -e "${RED}${BOLD}Error: Discord_Stereo_Installer_For_Linux.py not found.${NC}"
    echo -e "  Path: ${INSTALL_DIR}"
    echo -e "  Run without --no-update to download, or check your network."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}${BOLD}Error: python3 not found.${NC}"
    echo -e "  Install: sudo apt install python3 python3-tk"
    echo -e "  (or equivalent for your distribution)"
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${RED}${BOLD}Error: Python tkinter not available.${NC}"
    echo -e "  Install: sudo apt install python3-tk"
    echo -e "  Then run this launcher again."
    exit 1
fi

echo -e "${CYAN}Launching GUI...${NC}"
echo ""
exec python3 Discord_Stereo_Installer_For_Linux.py
