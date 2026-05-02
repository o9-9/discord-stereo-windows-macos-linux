#!/usr/bin/env bash
###############################################################################
# Discord Voice Quality Patcher - Linux
# 48 kHz | 384 kbps | Stereo
# Made by: Oracle | Shaun | Hallow | Ascend | Sentry | Sikimzo | Cypher
#
# v8.2 (Discord 0.0.135 / discord_voice.node MD5 fb6684...649a9):
#   * Bumped amplifier injection size 0x100 -> 0x180 (256 -> 384 bytes).
#     Empirically, gcc/clang -O2 produce hp_cutoff/dc_reject bodies of
#     ~250-320 bytes - the old 256-byte cap could truncate the function's
#     `ret` and let execution fall through into the original opus body.
#     0x180 fits both target slots (hp_cutoff=431 B, dc_reject=398 B).
#   * Final IDA pass against MD5 fb6684...649a9 confirmed all 14 patch
#     sites still match stock signatures and disassemble to the expected
#     instructions. No additional patches required for stereo/bitrate/SR.
#
# v8.1 (Discord 0.0.135 / discord_voice.node MD5 fb6684...649a9):
#   * Re-introduced MonoDownmixer patch in CapturedAudioProcessor::Process
#     (NOP sled + JMP rel32 at 0x35ECFC, 13 bytes). This was the missing piece
#     that caused the previous build to still come through as mono - without
#     it the captured mic audio was downmixed to mono BEFORE reaching
#     CreateAudioFrameToProcess, defeating the other stereo patches.
#   * Cross-validated every offset against IDA Pro decompilation:
#       - EmulateStereoSuccess1 @ 0x39C300 -> CommitAudioCodec stereo SDP cmp imm
#       - EmulateStereoSuccess2 @ 0x398665 -> CreateAudioStream stereo SDP cmp imm
#       - CreateAudioFrameStereo @ 0x390070 -> EngineAudioTransport channel clamp
#       - MonoDownmixer @ 0x35ECFC -> CapturedAudioProcessor mono-collapse path
#       - Emulate48Khz @ 0x39005A -> sample rate constant in CreateAudioFrameToProcess
#       - HighPassFilter @ 0x71F110 -> webrtc::HighPassFilter::Process
#       - HighpassCutoffFilter @ 0x762640 -> opus hp_cutoff()
#       - DcReject @ 0x7627F0 -> opus dc_reject()
#       - DownmixFunc @ 0x98E420 -> opus downmix_and_resample()
#       - AudioEncoderOpusConfig {SetChannels @ 0x7699D5, EncoderConfigInit1 @ 0x7699DF}
#       - AudioEncoderMultiChannelOpus  {Ch @ 0x7693AE, EncoderConfigInit2 @ 0x7693B8}
#       - AudioEncoderOpusConfigIsOk @ 0x769B70
#
# v8.0 (initial 0.0.135 rewrite):
#   * AudioFrame.num_channels_ forced to 2 via 7-byte mov r12, 2.
#   * SDP "stereo=1" flipped via cmp imm 0x02 -> 0x00 (CommitAudioCodec +
#     CreateAudioStream).
#   * Encoder ctor bitrate (32k -> 384k) and channels (1 -> 2) patched in both
#     AudioEncoderOpusConfig and AudioEncoderMultiChannelOpus.
#   * 48 kHz floor patches the default sample rate immediate (32k -> 48k).
###############################################################################

# Re-exec under bash if invoked via sh/dash/zsh.
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_VERSION="8.2"
SKIP_BACKUP=false
RESTORE_MODE=false

# region Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
WHITE='\033[1;37m'; DIM='\033[0;90m'; BOLD='\033[1m'; NC='\033[0m'
# endregion Colors

# region Config
SAMPLE_RATE=48000
BITRATE=384

# With sudo, use invoking user's home so we find their Discord.
DETECT_HOME="${HOME:-}"
if [[ -n "${SUDO_USER:-}" ]] && [[ "$(id -u 2>/dev/null)" -eq 0 ]]; then
    _dh=$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)
    [[ -n "${_dh:-}" ]] && DETECT_HOME="$_dh"
fi
[[ -z "${DETECT_HOME:-}" ]] && DETECT_HOME="${HOME:-}"

CACHE_DIR="$DETECT_HOME/.cache/DiscordVoicePatcher"
BACKUP_DIR="$CACHE_DIR/Backups"
LOG_FILE="$CACHE_DIR/patcher.log"
TEMP_DIR="$CACHE_DIR/build"
# Each backup is a full discord_voice.node (~tens–100+ MB); cap count per client + age.
MAX_BACKUPS_PER_CLIENT="${MAX_BACKUPS_PER_CLIENT:-3}"
MAX_BACKUP_AGE_DAYS="${MAX_BACKUP_AGE_DAYS:-45}"
# Unpatched Linux voice bundle (same tree as Windows; Linux subfolder):
# https://github.com/o9-9/discord-stereo-windows-macos-linux/tree/main/Updates/Nodes/Unpatched%20Nodes%20(For%20Patcher)/Linux
VOICE_BACKUP_DIR="${VOICE_BACKUP_DIR:-$CACHE_DIR/VoiceBackupLinux}"
VOICE_BACKUP_API="${VOICE_BACKUP_API:-https://api.github.com/repos/o9-9/discord-stereo-windows-macos-linux/contents/Updates%2FNodes%2FUnpatched%20Nodes%20%28For%20Patcher%29%2FLinux}"
# endregion Config

# --- Build fingerprint (update when targeting a new Discord build) ------------
# Linux Stable 0.0.135 (discord_voice.node)
# Verified MD5 / size from `md5sum` & `stat -c%s` on the GitHub bundle node.
EXPECTED_MD5="fb6684a550a7b5c0fdfe65ec954649a9"
EXPECTED_SIZE=104160072

# --- Linux/ELF patch offsets (Discord 0.0.135) -------------------------------
# Stereo channel signaling (CommitAudioCodec + CreateAudioStream):
#   These are the immediate byte of `cmp dword [rbx+0xF0], 2` followed by
#   `cmovnb rdx, rax` that picks the "stereo=1" SDP fmtp string.
#   Patching imm 0x02 -> 0x00 makes the comparison "always >= 0", so the
#   stereo branch is always taken (SDP advertises stereo=1).
OFFSET_EmulateStereoSuccess1=0x39C300   # CommitAudioCodec cmp imm  -> 0x00
OFFSET_EmulateStereoSuccess2=0x398665   # CreateAudioStream cmp imm -> 0x00

# AudioFrame channel-count clamp in CreateAudioFrameToProcess:
#   cmp r12, rax ; cmovnb r12, rax     (clamps stream-channels to mic-channels)
#   We replace the whole 7-byte sequence with `mov r12, 2` so that
#   AudioFrame.num_channels_ is forced to 2 regardless of mic input.
#   webrtc::voe::RemixAndResample then transparently upmixes mono->stereo.
OFFSET_CreateAudioFrameStereo=0x390070

# Mono-downmix bypass in CapturedAudioProcessor::Process:
#   test al, al ; jz +0xD ; cmp dword [rbx+0x80], 9 ; jg +0xB3
#   We replace the 13-byte block with 12 NOPs + JMP rel32 (E9 8F B3 00 00...
#   wait, the disp32 of the JMP is left as the original jg's disp, so the
#   jmp lands on the same target as the original jg). This unconditionally
#   takes the "skip mono downmix" branch so captured audio stays multi-channel
#   all the way through to the Opus encoder.
OFFSET_MonoDownmixer=0x35ECFC

# Opus encoder default channels (constructor field at +8):
OFFSET_AudioEncoderOpusConfigSetChannels=0x7699D5   # byte 0x01 -> 0x02
OFFSET_AudioEncoderMultiChannelOpusCh=0x7693AE      # byte 0x01 -> 0x02

# Opus encoder default bitrate (high dword of `mov rax, 0x7D0000000000`):
OFFSET_EncoderConfigInit1=0x7699DF    # 00 7D 00 00 (32k) -> 00 DC 05 00 (384k)
OFFSET_EncoderConfigInit2=0x7693B8    # 00 7D 00 00 (32k) -> 00 DC 05 00 (384k)

# Sample rate floor in CreateAudioFrameToProcess (default 32k -> default 48k):
OFFSET_Emulate48Khz=0x39005A          # mov r13d, 7D00h -> mov r13d, 0BB80h

# WebRTC HighPassFilter::Process (in-place high-pass) -> ret immediately:
OFFSET_HighPassFilter=0x71F110

# Custom amplifier injection (replaces upstream Opus hp_cutoff & dc_reject):
OFFSET_HighpassCutoffFilter=0x762640  # opus hp_cutoff()
OFFSET_DcReject=0x7627F0              # opus dc_reject()

# Opus mono-downmix path inside `tonality_analysis` -> ret immediately:
OFFSET_DownmixFunc=0x98E420           # downmix_and_resample()

# Opus encoder config validator -> always returns true (skips error throw):
OFFSET_AudioEncoderOpusConfigIsOk=0x769B70

FILE_OFFSET_ADJUSTMENT=0

# Required offset names; validate before build.
REQUIRED_OFFSET_NAMES=(
    EmulateStereoSuccess1 EmulateStereoSuccess2
    CreateAudioFrameStereo
    MonoDownmixer
    AudioEncoderOpusConfigSetChannels AudioEncoderMultiChannelOpusCh
    EncoderConfigInit1 EncoderConfigInit2
    Emulate48Khz
    HighPassFilter HighpassCutoffFilter DcReject DownmixFunc
    AudioEncoderOpusConfigIsOk
)

# region Validation bytes (anchors)
# CreateAudioFrameStereo: cmp r12,rax ; cmovnb r12,rax (Clang ELF, REX.W).
ORIG_CreateAudioFrameStereo='{0x49, 0x39, 0xC4, 0x4C, 0x0F, 0x43, 0xE0}'
# MonoDownmixer: test al,al ; jz +0xD ; cmp dword [rbx+0x80], 9 ; jg rel32 (start).
# We validate the first 13 bytes (test+jz+cmp+jg-opcode) — the patch overwrites
# bytes 0..12, leaving the jg's disp32 in place to act as the JMP rel32 disp.
ORIG_MonoDownmixer='{0x84, 0xC0, 0x74, 0x0D, 0x83, 0xBB, 0x80, 0x00, 0x00, 0x00, 0x09, 0x0F, 0x8F}'
# Emulate48Khz: mov r13d, 7D00h (default sample rate = 32 kHz).
ORIG_Emulate48Khz='{0x41, 0xBD, 0x00, 0x7D, 0x00, 0x00}'
# AudioEncoderOpusConfigIsOk prologue (Clang).
ORIG_AudioEncoderOpusConfigIsOk='{0x55, 0x48, 0x89, 0xE5, 0x8B, 0x0F, 0x31, 0xC0}'
# downmix_and_resample prologue (Clang, push rbp; mov rbp,rsp; push r15; push r14).
ORIG_DownmixFunc='{0x55, 0x48, 0x89, 0xE5, 0x41, 0x57, 0x41, 0x56}'
# HighPassFilter::Process prologue (Clang).
ORIG_HighPassFilter='{0x55, 0x48, 0x89, 0xE5, 0x41, 0x57, 0x41, 0x56}'
# Generic Clang prologue match for hp_cutoff / dc_reject targets.
ORIG_HighpassCutoffFilter='{0x55, 0x48, 0x89, 0xE5}'
ORIG_DcReject='{0x55, 0x48, 0x89, 0xE5}'
# Encoder bitrate immediate (00 7D 00 00 = 32000 bps in LE high dword of mov rax, imm64).
ORIG_EncoderConfigInit1='{0x00, 0x7D, 0x00, 0x00}'
ORIG_EncoderConfigInit2='{0x00, 0x7D, 0x00, 0x00}'
# endregion Validation bytes (anchors)

# Track overall success for conditional cleanup
PATCH_SUCCESS=false

# region Logging
log_info()  { echo -e "${WHITE}[--]${NC} $1"; echo "[INFO] $1" >> "$LOG_FILE" 2>/dev/null; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; echo "[OK] $1" >> "$LOG_FILE" 2>/dev/null; }
log_warn()  { echo -e "${YELLOW}[!!]${NC} $1"; echo "[WARN] $1" >> "$LOG_FILE" 2>/dev/null; }
log_error() { echo -e "${RED}[XX]${NC} $1"; echo "[ERROR] $1" >> "$LOG_FILE" 2>/dev/null; }
# endregion Logging

banner() {
    echo ""
    echo -e "${CYAN}===== Discord Voice Quality Patcher v${SCRIPT_VERSION} =====${NC}"
    echo -e "${CYAN}      48 kHz | 384 kbps | Stereo${NC}"
    echo -e "${CYAN}      Platform: Linux | Multi-Client${NC}"
    echo -e "${CYAN}===============================================${NC}"
    echo ""
}

show_settings() {
    echo -e "Config: ${SAMPLE_RATE}Hz, ${BITRATE}kbps, Stereo (Linux)"
    if $PATCH_LOCAL_ONLY; then
        echo -e "Voice bundle: ${YELLOW}local node only (--patch-local)${NC}"
    else
        echo -e "Voice bundle: ${GREEN}download stock module from GitHub, then patch${NC}"
    fi
    echo ""
}

# region CLI
SILENT_MODE=false
PATCH_ALL=false
PATCH_LOCAL_ONLY=false

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "  --skip-backup   Don't create backup before patching"
    echo "  --restore       Restore from backup"
    echo "  --list-backups  Show available backups"
    echo "  --silent        No prompts, patch all clients"
    echo "  --patch-all     Patch all clients (no selection menu)"
    echo "  --patch-local   Do not download the stock voice bundle from GitHub; patch"
    echo "                  the discord_voice.node already on disk (advanced)"
    echo "  --help          Show this help"
    echo ""
    echo "By default the patcher downloads the unpatched Linux voice module bundle from"
    echo "GitHub (same source as the Windows patcher, Linux folder), installs it over"
    echo "each client's voice folder, then applies patches. Override VOICE_BACKUP_API"
    echo "or set DISCORD_VOICE_PATCHER_GITHUB_TOKEN / GITHUB_TOKEN for private forks or API limits."
    echo ""
    echo "Examples:"
    echo "  $0              # Patch with stereo, 48kHz, 384kbps"
    echo "  $0 --restore    # Restore from backup"
    echo "  $0 --silent     # Silently patch all clients"
    exit 0
}

for arg in "$@"; do
    case "$arg" in
        --skip-backup) SKIP_BACKUP=true ;;
        --restore) RESTORE_MODE=true ;;
        --list-backups) mkdir -p "$BACKUP_DIR"; ls -la "$BACKUP_DIR/" 2>/dev/null || echo "No backups found"; exit 0 ;;
        --silent|-s) SILENT_MODE=true; PATCH_ALL=true ;;
        --patch-all) PATCH_ALL=true ;;
        --patch-local) PATCH_LOCAL_ONLY=true ;;
        --help|-h) usage ;;
        *)
            echo "Unknown option: $arg"
            usage
            ;;
    esac
done
# endregion CLI

# region Init
mkdir -p "$CACHE_DIR" "$BACKUP_DIR" "$TEMP_DIR"
echo "=== Discord Voice Patcher Log ===" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "Platform: Linux" >> "$LOG_FILE"
# endregion Init

# region Backup retention
# Drops backups older than MAX_BACKUP_AGE_DAYS, then keeps at most MAX_BACKUPS_PER_CLIENT
# per client (filename: discord_voice.node.<client>.<YYYYMMDD_HHMMSS>.backup).
prune_voice_backups() {
    [[ -d "$BACKUP_DIR" ]] || return 0
    local removed=0 f bn k i j
    local -a list odd

    while IFS= read -r -d '' f; do
        [[ -f "$f" ]] || continue
        rm -f "$f" 2>/dev/null && removed=$((removed + 1)) || true
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'discord_voice.node.*.backup' -mtime "+${MAX_BACKUP_AGE_DAYS}" -print0 2>/dev/null)

    declare -A seen=()
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        bn=$(basename "$f")
        if [[ "$bn" =~ ^discord_voice\.node\.(.+)\.[0-9]{8}_[0-9]{6}\.backup$ ]]; then
            seen["${BASH_REMATCH[1]}"]=1
        fi
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'discord_voice.node.*.backup' 2>/dev/null)

    for k in "${!seen[@]}"; do
        list=()
        mapfile -t list < <(ls -1t "$BACKUP_DIR"/discord_voice.node."${k}".*.backup 2>/dev/null || true)
        local n=${#list[@]}
        if (( n > MAX_BACKUPS_PER_CLIENT )); then
            for (( i = MAX_BACKUPS_PER_CLIENT; i < n; i++ )); do
                rm -f "${list[$i]}" 2>/dev/null && removed=$((removed + 1)) || true
            done
        fi
    done

    odd=()
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        bn=$(basename "$f")
        [[ "$bn" =~ ^discord_voice\.node\.(.+)\.[0-9]{8}_[0-9]{6}\.backup$ ]] && continue
        odd+=("$f")
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'discord_voice.node.*.backup' 2>/dev/null)

    if (( ${#odd[@]} > MAX_BACKUPS_PER_CLIENT )); then
        mapfile -t odd < <(for f in "${odd[@]}"; do stat -c $'%Y\t%n' "$f" 2>/dev/null; done | sort -rn | cut -f2-)
        for (( j = MAX_BACKUPS_PER_CLIENT; j < ${#odd[@]}; j++ )); do
            rm -f "${odd[$j]}" 2>/dev/null && removed=$((removed + 1)) || true
        done
    fi

    if (( removed > 0 )); then
        log_info "Pruned old voice backups: removed $removed file(s) (max $MAX_BACKUPS_PER_CLIENT per client, max age ${MAX_BACKUP_AGE_DAYS}d)."
    fi
}

prune_voice_backups
# endregion Backup retention

# region Voice bundle (GitHub)
# Downloads the same unpatched Linux bundle the Windows patcher uses (Linux folder).
download_linux_voice_bundle_from_github() {
    local py=""
    if command -v python3 &>/dev/null; then
        py="python3"
    elif command -v python &>/dev/null && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 6) else 1)" 2>/dev/null; then
        py="python"
    fi
    if [[ -z "$py" ]]; then
        log_error "Python 3.6+ is required to download the voice bundle from GitHub."
        log_error "  Install python3, or re-run with --patch-local to patch your existing node only."
        return 1
    fi

    log_info "Downloading voice bundle from GitHub..."
    log_info "  API: ${VOICE_BACKUP_API:0:80}..."
    log_info "  Dest: $VOICE_BACKUP_DIR"

    if ! VOICE_BACKUP_DIR="$VOICE_BACKUP_DIR" VOICE_BACKUP_API="$VOICE_BACKUP_API" "$py" - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def main() -> None:
    dest = os.environ.get("VOICE_BACKUP_DIR", "").strip()
    api = os.environ.get("VOICE_BACKUP_API", "").strip()
    if not dest or not api:
        die("VOICE_BACKUP_DIR / VOICE_BACKUP_API must be set")
    token = (
        os.environ.get("DISCORD_VOICE_PATCHER_GITHUB_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip()
    )
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(dest):
        p = os.path.join(dest, name)
        if os.path.isdir(p):
            import shutil
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError:
                pass

    req = urllib.request.Request(api)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "DiscordVoicePatcher-Linux")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            payload = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 403:
            die("GitHub API returned 403 (rate limit or auth). Set DISCORD_VOICE_PATCHER_GITHUB_TOKEN or GITHUB_TOKEN, or try again later.")
        die(f"GitHub API HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        die(f"GitHub API request failed: {e}")

    try:
        items = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        die(f"Invalid JSON from GitHub API: {e}")

    if not isinstance(items, list):
        die("Unexpected GitHub API response (expected a list of directory entries)")

    n = 0
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "file":
            continue
        name = item.get("name")
        url = item.get("download_url")
        if not name or not url:
            continue
        out = os.path.join(dest, name)
        freq = urllib.request.Request(url)
        freq.add_header("User-Agent", "DiscordVoicePatcher-Linux")
        if token:
            freq.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(freq, timeout=120) as fr:
                data = fr.read()
        except urllib.error.HTTPError as e:
            die(f"Failed to download {name}: HTTP {e.code}")
        except urllib.error.URLError as e:
            die(f"Failed to download {name}: {e}")
        if len(data) == 0:
            die(f"Downloaded empty file: {name}")
        with open(out, "wb") as f:
            f.write(data)
        n += 1

    if n == 0:
        die("No files downloaded from the voice bundle folder (empty listing or API error).")
    print(n)

if __name__ == "__main__":
    main()
PY
    then
        log_error "Voice bundle download failed."
        return 1
    fi

    local node="$VOICE_BACKUP_DIR/discord_voice.node"
    if [[ ! -f "$node" ]]; then
        log_error "discord_voice.node missing after download: $node"
        return 1
    fi

    local sz md5
    sz=$(stat -c%s "$node" 2>/dev/null || echo "0")
    if [[ "$sz" != "$EXPECTED_SIZE" ]]; then
        log_error "Downloaded discord_voice.node size $sz != expected $EXPECTED_SIZE"
        log_error "  Refresh offsets in this script for your repo bundle, or fix VOICE_BACKUP_API."
        return 1
    fi

    if command -v md5sum &>/dev/null; then
        md5=$(md5sum "$node" | cut -d' ' -f1)
    elif command -v md5 &>/dev/null; then
        md5=$(md5 -q "$node")
    else
        log_warn "Could not verify MD5 (no md5sum/md5); continuing with size check only."
        log_ok "Voice bundle downloaded ($(basename "$VOICE_BACKUP_DIR"))"
        return 0
    fi

    if [[ "${md5,,}" != "${EXPECTED_MD5,,}" ]]; then
        log_error "Downloaded discord_voice.node MD5 $md5 != patcher stock $EXPECTED_MD5"
        log_error "  Update EXPECTED_MD5 / offsets in this script to match your GitHub bundle."
        return 1
    fi

    log_ok "Voice bundle verified (stock MD5) — $(ls -1 "$VOICE_BACKUP_DIR" 2>/dev/null | wc -l) file(s)"
    return 0
}

# Replaces the client's discord_voice/ folder contents with the cached GitHub bundle (Windows-style).
install_linux_voice_bundle_for_client() {
    local node_path="$1"
    local voice_dir
    voice_dir=$(dirname "$node_path")

    if [[ ! -d "$VOICE_BACKUP_DIR" ]] || [[ -z "$(ls -A "$VOICE_BACKUP_DIR" 2>/dev/null)" ]]; then
        log_error "Voice bundle cache empty: $VOICE_BACKUP_DIR"
        return 1
    fi

    log_info "Installing stock voice module from bundle into:"
    log_info "  $voice_dir"

    if [[ ! -d "$voice_dir" ]]; then
        log_error "Voice directory does not exist: $voice_dir"
        return 1
    fi

    find "$voice_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    if ! cp -a "$VOICE_BACKUP_DIR"/. "$voice_dir"/; then
        log_error "Failed to copy voice bundle into $voice_dir"
        return 1
    fi

    if [[ ! -f "$node_path" ]]; then
        log_error "discord_voice.node not present after bundle install: $node_path"
        return 1
    fi

    log_ok "Stock voice files installed"
    return 0
}
# endregion Voice bundle (GitHub)

# region Discord process detection
# Returns 0 if Discord is running, 1 if not.
# Sets DISCORD_PIDS to the list of matching PIDs.
DISCORD_PIDS=""

check_discord_running() {
    DISCORD_PIDS=""
    local pids pid cmdline filtered_pids=""
    pids=$(pgrep -f '[D]iscord' 2>/dev/null | head -50 || true)
    [[ -z "$pids" ]] && return 1

    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
        [[ -z "$cmdline" ]] && continue

        # Skip our own patcher invocation - pgrep '[D]iscord' picked it up because
        # it has "discord" in its filename.
        [[ "$cmdline" =~ discord_voice_patcher ]] && continue

        # Match real Discord electron clients (any channel) and known install layouts.
        if [[ "$cmdline" =~ (^|/)(Discord|DiscordCanary|DiscordPTB|DiscordDevelopment)(/| |$) ]] ||
           [[ "$cmdline" =~ /opt/discord[^_] ]] ||
           [[ "$cmdline" =~ /usr/(share|lib)/discord ]] ||
           [[ "$cmdline" =~ com\.discordapp\.Discord ]] ||
           [[ "$cmdline" =~ /snap/discord/ ]]; then
            filtered_pids+="$pid "
        fi
    done <<< "$pids"

    filtered_pids="${filtered_pids% }"
    if [[ -n "$filtered_pids" ]]; then
        DISCORD_PIDS="$filtered_pids"
        return 0
    fi
    return 1
}

# Prompt user to close Discord (or terminate in silent mode).
handle_discord_running() {
    if ! check_discord_running; then
        return 0
    fi

    echo ""
    log_warn "Discord is currently running."
    log_warn "Patching while Discord is running can cause:"
    log_warn "  - Crashes if the voice module is in use"
    log_warn "  - Patches being overwritten when Discord restarts"
    echo ""

    if $SILENT_MODE; then
        log_info "Silent mode: Attempting to close Discord..."
        terminate_discord
        return $?
    fi

    echo -e "  [${WHITE}1${NC}] Close Discord and continue patching"
    echo -e "  [${WHITE}2${NC}] Continue without closing (not recommended)"
    echo -e "  [${WHITE}3${NC}] Cancel"
    echo ""

    read -rp "  Choice [1]: " choice
    case "${choice:-1}" in
        1)
            terminate_discord
            return $?
            ;;
        2)
            log_warn "Continuing with Discord running - patches may not take effect until restart"
            return 0
            ;;
        3)
            log_info "Cancelled. Close Discord manually and re-run."
            exit 0
            ;;
        *)
            terminate_discord
            return $?
            ;;
    esac
}
# endregion Discord process detection

terminate_discord() {
    log_info "Closing Discord processes..."

    local pid killed=false
    if check_discord_running && [[ -n "$DISCORD_PIDS" ]]; then
        for pid in $DISCORD_PIDS; do
            kill "$pid" 2>/dev/null && killed=true || true
        done
    fi

    if ! $killed; then
        log_ok "No Discord processes to close"
        return 0
    fi

    # Wait up to 10 seconds for graceful SIGTERM.
    local attempts=0
    while (( attempts < 20 )); do
        if ! check_discord_running; then
            log_ok "Discord closed successfully"
            sleep 1
            return 0
        fi
        sleep 0.5
        attempts=$(( attempts + 1 ))
    done

    log_warn "Discord didn't shut down gracefully, forcing..."
    if check_discord_running && [[ -n "$DISCORD_PIDS" ]]; then
        for pid in $DISCORD_PIDS; do
            kill -9 "$pid" 2>/dev/null || true
        done
    fi

    sleep 1

    if check_discord_running; then
        log_error "Failed to close Discord. Please close it manually."
        return 1
    fi

    log_ok "Discord closed"
    return 0
}

# region Discord Client Detection
declare -a CLIENT_NAMES=()
declare -a CLIENT_NODES=()

find_discord_clients() {
    log_info "Scanning for Discord installations..."

    # Comprehensive search paths
    # discord_voice.node lives inside per-user config dirs in
    # app-*/modules/discord_voice*/discord_voice/
    # System paths (/opt, /usr/share, /usr/lib, /snap) also searched.
    local search_bases=(
        "$DETECT_HOME/.config/discord"
        "$DETECT_HOME/.config/discordcanary"
        "$DETECT_HOME/.config/discordptb"
        "$DETECT_HOME/.config/discorddevelopment"
        "$DETECT_HOME/.var/app/com.discordapp.Discord/config/discord"
        "$DETECT_HOME/.var/app/com.discordapp.DiscordCanary/config/discordcanary"
        "/snap/discord/current/usr/share/discord/resources"
        "/opt/discord/resources"
        "/opt/discord-canary/resources"
        "/opt/discord-ptb/resources"
        "/usr/share/discord/resources"
        "/usr/lib/discord/resources"
    )
    local search_names=(
        "Discord Stable"
        "Discord Canary"
        "Discord PTB"
        "Discord Development"
        "Discord (Flatpak)"
        "Discord Canary (Flatpak)"
        "Discord (Snap)"
        "Discord (/opt)"
        "Discord Canary (/opt)"
        "Discord PTB (/opt)"
        "Discord (/usr/share)"
        "Discord (/usr/lib)"
    )

    local found_paths=()
    local i base name found_nodes latest resolved dup fp fsize

    for i in "${!search_bases[@]}"; do
        base="${search_bases[$i]}"
        name="${search_names[$i]}"

        [[ -d "$base" ]] || continue

        # Search up to depth 10 for system-wide install layouts.
        found_nodes=$(find "$base" -maxdepth 10 -name "discord_voice.node" -type f 2>/dev/null | head -5 || true)
        [[ -z "$found_nodes" ]] && continue

        # Pick the most recently modified hit (newest install).
        latest=$(echo "$found_nodes" | while read -r f; do
            stat -c '%Y %n' "$f" 2>/dev/null || echo "0 $f"
        done | sort -rn | head -1 | cut -d' ' -f2-)

        if [[ -n "$latest" && -f "$latest" ]]; then
            resolved=$(readlink -f "$latest" 2>/dev/null || echo "$latest")
            dup=false
            for fp in "${found_paths[@]+"${found_paths[@]}"}"; do
                [[ "$fp" == "$resolved" ]] && { dup=true; break; }
            done
            $dup && continue

            if [[ ! -r "$latest" ]]; then
                log_warn "Found but unreadable: $latest"
                continue
            fi
            fsize=$(stat -c%s "$latest" 2>/dev/null || echo "0")
            if (( fsize == 0 )); then
                log_warn "Found but empty (0 bytes): $latest"
                continue
            fi

            CLIENT_NAMES+=("$name")
            CLIENT_NODES+=("$latest")
            found_paths+=("$resolved")
            log_ok "Found: $name"
            log_info "  Path: $latest"
            log_info "  Size: $(numfmt --to=iec "$fsize" 2>/dev/null || echo "${fsize} bytes")"
        fi
    done

    if [[ ${#CLIENT_NAMES[@]} -eq 0 ]]; then
        log_error "No Discord installations found!"
        echo ""
        echo "Expected discord_voice.node in one of:"
        echo "  ~/.config/discord/app-*/modules/discord_voice-*/discord_voice/"
        echo "  ~/.config/discordcanary/app-*/modules/discord_voice-*/discord_voice/"
        echo "  ~/.config/discordptb/app-*/modules/discord_voice-*/discord_voice/"
        echo "  ~/.config/discorddevelopment/app-*/modules/discord_voice-*/discord_voice/"
        echo "  ~/.var/app/com.discordapp.Discord/config/discord/..."
        echo "  /opt/discord/... /usr/share/discord/... /snap/discord/..."
        echo ""
        echo "Make sure Discord has been opened and you've joined a voice channel"
        echo "at least once so the voice module gets downloaded."
        if [[ -n "${SUDO_USER:-}" ]] && [[ "$(id -u 2>/dev/null)" -eq 0 ]]; then
            echo ""
            echo "Tip: Checked config for user $SUDO_USER ($DETECT_HOME)."
            echo "If Discord is installed for another user, run without sudo as that user."
        fi
        return 1
    fi

    log_ok "Found ${#CLIENT_NAMES[@]} client(s)"
    return 0
}
# endregion Discord Client Detection


# region Binary Verification
verify_binary() {
    local node_path="$1"
    local name="$2"

    # Check file exists and is readable
    if [[ ! -f "$node_path" ]]; then
        log_error "Binary not found: $node_path"
        return 1
    fi
    if [[ ! -r "$node_path" ]]; then
        log_error "Binary not readable: $node_path"
        log_error "  Try: chmod +r '$node_path'"
        return 1
    fi

    local fsize
    fsize=$(stat -c%s "$node_path" 2>/dev/null || echo "0")

    # Size check first (fast)
    if [[ "$fsize" -ne "$EXPECTED_SIZE" ]]; then
        log_error "Binary size mismatch for $name"
        log_error "  Expected: $EXPECTED_SIZE bytes"
        log_error "  Got:      $fsize bytes"
        log_error "  This version of discord_voice.node is not supported by these offsets."
        log_error "  The offsets in this script are for MD5: $EXPECTED_MD5"
        return 1
    fi

    # MD5 check
    local actual_md5
    if command -v md5sum &>/dev/null; then
        if ! actual_md5=$(md5sum "$node_path" 2>/dev/null | cut -d' ' -f1); then
            log_error "Failed to compute md5 for $name"
            return 1
        fi
    elif command -v md5 &>/dev/null; then
        if ! actual_md5=$(md5 -q "$node_path" 2>/dev/null); then
            log_error "Failed to compute md5 for $name"
            return 1
        fi
    else
        log_error "No md5sum or md5 found - cannot verify binary integrity"
        log_error "  Install coreutils: sudo apt install coreutils"
        return 1
    fi

    if [[ "$actual_md5" == "$EXPECTED_MD5" ]]; then
        log_ok "Binary verified (stock MD5)"
        return 0
    fi

    # Patched node: same size, different MD5 — patcher validates bytes at sites.
    log_warn "MD5 != stock (often already patched). Continuing; patcher validates sites."
    return 0
}
# endregion Binary Verification


# region Backup Management
backup_node() {
    local source="$1"
    local client_name="$2"

    if $SKIP_BACKUP; then
        log_warn "Skipping backup (--skip-backup)"
        return 0
    fi

    if [[ ! -f "$source" ]]; then
        log_error "Cannot backup: file not found: $source"
        return 1
    fi

    local sanitized
    sanitized=$(echo "$client_name" | tr ' ' '_' | tr -d '()[]')

    # Check if we already have an identical backup (avoid flooding disk)
    local latest_backup
    latest_backup=$(ls -1t "$BACKUP_DIR"/discord_voice.node."${sanitized}".*.backup 2>/dev/null | head -1 || true)

    if [[ -n "$latest_backup" && -f "$latest_backup" ]]; then
        if cmp -s "$source" "$latest_backup"; then
            log_ok "Backup already exists and is identical (skipping)"
            return 0
        fi
    fi

    local backup_path="$BACKUP_DIR/discord_voice.node.${sanitized}.$(date +%Y%m%d_%H%M%S).backup"
    if ! cp "$source" "$backup_path" 2>/dev/null; then
        log_error "Failed to create backup at $backup_path"
        log_error "  Check disk space and permissions on $BACKUP_DIR"
        return 1
    fi
    log_ok "Backup: $(basename "$backup_path")"

    # Verify backup integrity
    if ! cmp -s "$source" "$backup_path"; then
        log_error "Backup verification failed! Backup does not match source."
        rm -f "$backup_path"
        return 1
    fi

    prune_voice_backups
    return 0
}

restore_from_backup() {
    banner
    log_info "Available backups:"
    echo ""

    local backups=()
    while IFS= read -r f; do
        backups+=("$f")
    done < <(ls -1t "$BACKUP_DIR"/*.backup 2>/dev/null)

    if [[ ${#backups[@]} -eq 0 ]]; then
        log_error "No backups found in $BACKUP_DIR"
        exit 1
    fi

    for i in "${!backups[@]}"; do
        local bk="${backups[$i]}"
        local bsize
        bsize=$(stat -c%s "$bk" 2>/dev/null || echo "?")
        local bdate
        bdate=$(stat -c%y "$bk" 2>/dev/null | cut -d. -f1 || echo "unknown")
        echo -e "  [$(( i + 1 ))] ${bdate} - $(numfmt --to=iec "$bsize" 2>/dev/null || echo "$bsize") - $(basename "$bk")"
    done
    echo ""

    read -rp "Select backup (1-${#backups[@]}, Enter for most recent): " sel
    if [[ -z "$sel" ]]; then sel=1; fi
    if [[ ! "$sel" =~ ^[0-9]+$ ]] || (( sel < 1 || sel > ${#backups[@]} )); then
        log_error "Invalid selection"; exit 1
    fi
    local backup_file="${backups[$(( sel - 1 ))]}"

    # Verify backup file integrity
    local bfsize
    bfsize=$(stat -c%s "$backup_file" 2>/dev/null || echo "0")
    if (( bfsize == 0 )); then
        log_error "Selected backup is empty (0 bytes) - possibly corrupted"
        exit 1
    fi

    # Ensure Discord is not running before restore
    if check_discord_running; then
        log_warn "Discord is running. It should be closed before restoring."
        handle_discord_running
    fi

    find_discord_clients || exit 1
    echo ""
    for i in "${!CLIENT_NAMES[@]}"; do
        echo -e "  [$(( i + 1 ))] ${CLIENT_NAMES[$i]}"
        echo -e "      ${DIM}${CLIENT_NODES[$i]}${NC}"
    done
    echo ""
    read -rp "Restore to which client? (1-${#CLIENT_NAMES[@]}): " csel
    if [[ -z "$csel" ]]; then csel=1; fi
    if [[ ! "$csel" =~ ^[0-9]+$ ]] || (( csel < 1 || csel > ${#CLIENT_NAMES[@]} )); then
        log_error "Invalid client selection"; exit 1
    fi
    local target="${CLIENT_NODES[$(( csel - 1 ))]}"
    local target_name="${CLIENT_NAMES[$(( csel - 1 ))]}"

    echo ""
    log_info "Backup:  $(basename "$backup_file")"
    log_info "Target:  $target"
    log_info "Client:  $target_name"
    echo ""
    read -rp "Replace target with backup? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_warn "Cancelled"; exit 0
    fi

    if ! cp "$backup_file" "$target" 2>/dev/null; then
        log_error "Failed to restore! Check permissions on $target"
        exit 1
    fi

    # Verify restore
    if ! cmp -s "$backup_file" "$target"; then
        log_error "Restore verification failed! File may be corrupted."
        exit 1
    fi

    log_ok "Restored successfully! Restart Discord to apply."
    exit 0
}
# endregion Backup Management


# region Compiler Detection
COMPILER=""
COMPILER_TYPE=""

find_compiler() {
    log_info "Searching for C++ compiler..."
    if command -v g++ &>/dev/null; then
        COMPILER="g++"
        COMPILER_TYPE="GCC"
        local ver
        ver=$(g++ --version 2>/dev/null | head -1 || echo 'g++ (version unknown)')
        log_ok "Found g++ ($ver)"
        return 0
    elif command -v clang++ &>/dev/null; then
        COMPILER="clang++"
        COMPILER_TYPE="Clang"
        local ver
        ver=$(clang++ --version 2>/dev/null | head -1 || echo 'clang++ (version unknown)')
        log_ok "Found clang++ ($ver)"
        return 0
    fi
    log_error "No C++ compiler found!"
    echo ""
    echo "Install one with:"
    echo "  Ubuntu/Debian:  sudo apt install g++"
    echo "  Fedora/RHEL:    sudo dnf install gcc-c++"
    echo "  Arch:           sudo pacman -S gcc"
    echo "  openSUSE:       sudo zypper install gcc-c++"
    return 1
}
# endregion Compiler Detection


# region Source Code Generation

# 1x gain amplifier matching the Windows patcher's 1x/2x path.
# Uses SSE rsqrt for channel normalization: out = in * 1 * (1/sqrt(channels))
# This is the same formula the Windows patcher uses at GAIN_MULTIPLIER=1.
# The state manipulation ensures the encoder state machine stays consistent.
generate_amplifier_source() {
    cat > "$TEMP_DIR/amplifier.cpp" << 'AMPEOF'
#define GAIN_MULTIPLIER 1

#include <cstdint>
#include <xmmintrin.h>

extern "C" void hp_cutoff(const float* in, int cutoff_Hz, float* out, int* hp_mem, int len, int channels, int Fs, int arch)
{
    int* st = (hp_mem - 3553);
    *(int*)(st + 3557) = 1002;
    *(int*)((char*)st + 160) = -1;
    *(int*)((char*)st + 164) = -1;
    *(int*)((char*)st + 184) = 0;

    float scale = 1.0f;
    if (channels > 0) {
        __m128 v = _mm_cvtsi32_ss(_mm_setzero_ps(), channels);
        v = _mm_rsqrt_ss(v);
        scale = _mm_cvtss_f32(v);
    }
    for (unsigned long i = 0; i < (unsigned long)(channels * len); i++) out[i] = in[i] * GAIN_MULTIPLIER * scale;
}

extern "C" void dc_reject(const float* in, float* out, int* hp_mem, int len, int channels, int Fs)
{
    int* st = (hp_mem - 3553);
    *(int*)(st + 3557) = 1002;
    *(int*)((char*)st + 160) = -1;
    *(int*)((char*)st + 164) = -1;
    *(int*)((char*)st + 184) = 0;

    float scale = 1.0f;
    if (channels > 0) {
        __m128 v = _mm_cvtsi32_ss(_mm_setzero_ps(), channels);
        v = _mm_rsqrt_ss(v);
        scale = _mm_cvtss_f32(v);
    }
    for (int i = 0; i < channels * len; i++) out[i] = in[i] * GAIN_MULTIPLIER * scale;
}
AMPEOF
}

validate_required_offsets() {
    local missing=()
    for name in "${REQUIRED_OFFSET_NAMES[@]}"; do
        local var="OFFSET_$name"
        local val="${!var:-}"
        if [[ -z "$val" ]]; then
            missing+=("$var")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing or empty required offset(s): ${missing[*]}"
        log_error "Refresh the build fingerprint block at the top of this script."
        return 1
    fi
    return 0
}

generate_patcher_source() {
    validate_required_offsets || exit 1

    cat > "$TEMP_DIR/patcher.cpp" << 'PATCHEOF'
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <errno.h>

#define SAMPLE_RATE SAMPLERATE_VAL
#define BITRATE BITRATE_VAL

extern "C" void dc_reject(const float*, float*, int*, int, int, int);
extern "C" void hp_cutoff(const float*, int, float*, int*, int, int, int, int);

namespace Offsets {
    constexpr uint32_t EmulateStereoSuccess1             = OFFSET_VAL_EmulateStereoSuccess1;
    constexpr uint32_t EmulateStereoSuccess2             = OFFSET_VAL_EmulateStereoSuccess2;
    constexpr uint32_t CreateAudioFrameStereo            = OFFSET_VAL_CreateAudioFrameStereo;
    constexpr uint32_t MonoDownmixer                     = OFFSET_VAL_MonoDownmixer;
    constexpr uint32_t AudioEncoderOpusConfigSetChannels = OFFSET_VAL_AudioEncoderOpusConfigSetChannels;
    constexpr uint32_t AudioEncoderMultiChannelOpusCh    = OFFSET_VAL_AudioEncoderMultiChannelOpusCh;
    constexpr uint32_t EncoderConfigInit1                = OFFSET_VAL_EncoderConfigInit1;
    constexpr uint32_t EncoderConfigInit2                = OFFSET_VAL_EncoderConfigInit2;
    constexpr uint32_t Emulate48Khz                      = OFFSET_VAL_Emulate48Khz;
    constexpr uint32_t HighPassFilter                    = OFFSET_VAL_HighPassFilter;
    constexpr uint32_t HighpassCutoffFilter              = OFFSET_VAL_HighpassCutoffFilter;
    constexpr uint32_t DcReject                          = OFFSET_VAL_DcReject;
    constexpr uint32_t DownmixFunc                       = OFFSET_VAL_DownmixFunc;
    constexpr uint32_t AudioEncoderOpusConfigIsOk        = OFFSET_VAL_AudioEncoderOpusConfigIsOk;
    constexpr uint32_t FILE_OFFSET_ADJUSTMENT            = OFFSET_VAL_FileAdjustment;
};

class DiscordPatcher {
private:
    std::string modulePath;

    bool ApplyPatches(void* fileData, long long fileSize) {
        printf("Validating binary before patching...\n");

        // File size range check - catches completely wrong files early
        constexpr long long MIN_EXPECTED_SIZE = 70LL * 1024 * 1024;   // 70 MB
        constexpr long long MAX_EXPECTED_SIZE = 110LL * 1024 * 1024;  // 110 MB
        if (fileSize < MIN_EXPECTED_SIZE || fileSize > MAX_EXPECTED_SIZE) {
            printf("ERROR: File size %.2f MB is outside expected range (70-110 MB)\n",
                   fileSize / (1024.0 * 1024.0));
            printf("This may not be the correct discord_voice.node for these offsets.\n");
            return false;
        }

        auto CheckBytes = [&](uint32_t offset, const unsigned char* expected, size_t len) -> bool {
            uint32_t fileOffset = offset - Offsets::FILE_OFFSET_ADJUSTMENT;
            if ((long long)(fileOffset + len) > fileSize) return false;
            return memcmp((char*)fileData + fileOffset, expected, len) == 0;
        };

        auto PatchBytes = [&](uint32_t offset, const char* bytes, size_t len) -> bool {
            uint32_t fileOffset = offset - Offsets::FILE_OFFSET_ADJUSTMENT;
            if ((long long)(fileOffset + len) > fileSize) {
                printf("ERROR: Patch at 0x%X (len %zu) exceeds file size!\n", offset, len);
                return false;
            }
            memcpy((char*)fileData + fileOffset, bytes, len);
            return true;
        };

        auto ReadU32LE = [&](uint32_t offset, uint32_t& value) -> bool {
            uint32_t fileOffset = offset - Offsets::FILE_OFFSET_ADJUSTMENT;
            if ((long long)(fileOffset + 4) > fileSize) return false;
            memcpy(&value, (char*)fileData + fileOffset, 4);
            return true;
        };

        auto OrigOrAlt = [&](uint32_t off,
                             const unsigned char* orig, size_t origLen,
                             const unsigned char* alt, size_t altLen) -> bool {
            return CheckBytes(off, orig, origLen) || CheckBytes(off, alt, altLen);
        };

        // ---- Pre-patch validation: each site must be either stock or already-patched ----
        const unsigned char orig_caf[]      = ORIG_VAL_CreateAudioFrameStereo;
        const unsigned char patch_caf[]     = {0x49, 0xC7, 0xC4, 0x02, 0x00, 0x00, 0x00};   // mov r12, 2

        // MonoDownmixer: 12 NOPs + JMP rel32 opcode (E9). The disp32 at [+13..+16]
        // is left untouched - it holds the original jg's disp, so the JMP lands
        // on the same target the original jg would have (the "skip downmix" path).
        const unsigned char orig_mdm[]      = ORIG_VAL_MonoDownmixer;
        const unsigned char patch_mdm[]     = {0x90, 0x90, 0x90, 0x90, 0x90, 0x90,
                                               0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0xE9};

        const unsigned char orig_48[]       = ORIG_VAL_Emulate48Khz;
        const unsigned char patch_48[]      = {0x41, 0xBD, 0x80, 0xBB, 0x00, 0x00};         // mov r13d, 48000

        const unsigned char orig_isok[]     = ORIG_VAL_AudioEncoderOpusConfigIsOk;
        const unsigned char patch_isok[]    = {0x48, 0xC7, 0xC0, 0x01, 0x00, 0x00, 0x00, 0xC3};

        const unsigned char orig_dnmix[]    = ORIG_VAL_DownmixFunc;
        const unsigned char patch_ret[]     = {0xC3};

        const unsigned char orig_hp[]       = ORIG_VAL_HighPassFilter;

        const unsigned char orig_hpcut[]    = ORIG_VAL_HighpassCutoffFilter;
        const unsigned char orig_dcrej[]    = ORIG_VAL_DcReject;

        const unsigned char orig_enc1[]     = ORIG_VAL_EncoderConfigInit1;
        const unsigned char orig_enc2[]     = ORIG_VAL_EncoderConfigInit2;
        const unsigned char patch_enc384[]  = {0x00, 0xDC, 0x05, 0x00};                     // 384000 LE

        const unsigned char orig_ch_one[]   = {0x01};
        const unsigned char patch_ch_two[]  = {0x02};

        // SDP "stereo=1": cmp imm byte (0x02 -> 0x00)
        const unsigned char orig_sdp[]      = {0x02};
        const unsigned char patch_sdp[]     = {0x00};

        // First 24 bytes of compiled hp_cutoff / dc_reject act as a probe for
        // detecting an already-injected node (size+md5 already match patched one).
        constexpr size_t injProbe = 24;

        bool o_caf  = OrigOrAlt(Offsets::CreateAudioFrameStereo, orig_caf, sizeof(orig_caf), patch_caf, sizeof(patch_caf));
        bool o_mdm  = OrigOrAlt(Offsets::MonoDownmixer, orig_mdm, sizeof(orig_mdm), patch_mdm, sizeof(patch_mdm));
        bool o_48   = OrigOrAlt(Offsets::Emulate48Khz, orig_48, sizeof(orig_48), patch_48, sizeof(patch_48));
        bool o_isok = OrigOrAlt(Offsets::AudioEncoderOpusConfigIsOk, orig_isok, sizeof(orig_isok), patch_isok, sizeof(patch_isok));
        bool o_dn   = OrigOrAlt(Offsets::DownmixFunc, orig_dnmix, sizeof(orig_dnmix), patch_ret, sizeof(patch_ret));
        bool o_hp   = OrigOrAlt(Offsets::HighPassFilter, orig_hp, sizeof(orig_hp), patch_ret, sizeof(patch_ret));
        bool o_hpc  = CheckBytes(Offsets::HighpassCutoffFilter, orig_hpcut, sizeof(orig_hpcut))
                   || CheckBytes(Offsets::HighpassCutoffFilter, (const unsigned char*)hp_cutoff, injProbe);
        bool o_dcr  = CheckBytes(Offsets::DcReject, orig_dcrej, sizeof(orig_dcrej))
                   || CheckBytes(Offsets::DcReject, (const unsigned char*)dc_reject, injProbe);
        bool o_e1   = OrigOrAlt(Offsets::EncoderConfigInit1, orig_enc1, sizeof(orig_enc1), patch_enc384, sizeof(patch_enc384));
        bool o_e2   = OrigOrAlt(Offsets::EncoderConfigInit2, orig_enc2, sizeof(orig_enc2), patch_enc384, sizeof(patch_enc384));
        bool o_ch1  = OrigOrAlt(Offsets::AudioEncoderOpusConfigSetChannels, orig_ch_one, 1, patch_ch_two, 1);
        bool o_ch2  = OrigOrAlt(Offsets::AudioEncoderMultiChannelOpusCh, orig_ch_one, 1, patch_ch_two, 1);
        bool o_ess1 = OrigOrAlt(Offsets::EmulateStereoSuccess1, orig_sdp, 1, patch_sdp, 1);
        bool o_ess2 = OrigOrAlt(Offsets::EmulateStereoSuccess2, orig_sdp, 1, patch_sdp, 1);

        printf("  CreateAudioFrameStereo (0x%06X): %s\n", Offsets::CreateAudioFrameStereo, o_caf ? "OK" : "MISMATCH");
        printf("  MonoDownmixer          (0x%06X): %s\n", Offsets::MonoDownmixer, o_mdm ? "OK" : "MISMATCH");
        printf("  Emulate48Khz           (0x%06X): %s\n", Offsets::Emulate48Khz, o_48 ? "OK" : "MISMATCH");
        printf("  AudioEncoderConfigIsOk (0x%06X): %s\n", Offsets::AudioEncoderOpusConfigIsOk, o_isok ? "OK" : "MISMATCH");
        printf("  DownmixFunc            (0x%06X): %s\n", Offsets::DownmixFunc, o_dn ? "OK" : "MISMATCH");
        printf("  HighPassFilter         (0x%06X): %s\n", Offsets::HighPassFilter, o_hp ? "OK" : "MISMATCH");
        printf("  HighpassCutoffFilter   (0x%06X): %s\n", Offsets::HighpassCutoffFilter, o_hpc ? "OK" : "MISMATCH");
        printf("  DcReject               (0x%06X): %s\n", Offsets::DcReject, o_dcr ? "OK" : "MISMATCH");
        printf("  EncoderConfigInit1     (0x%06X): %s\n", Offsets::EncoderConfigInit1, o_e1 ? "OK" : "MISMATCH");
        printf("  EncoderConfigInit2     (0x%06X): %s\n", Offsets::EncoderConfigInit2, o_e2 ? "OK" : "MISMATCH");
        printf("  OpusConfigSetChannels  (0x%06X): %s\n", Offsets::AudioEncoderOpusConfigSetChannels, o_ch1 ? "OK" : "MISMATCH");
        printf("  MultiChannelOpusCh     (0x%06X): %s\n", Offsets::AudioEncoderMultiChannelOpusCh, o_ch2 ? "OK" : "MISMATCH");
        printf("  EmulateStereoSuccess1  (0x%06X): %s\n", Offsets::EmulateStereoSuccess1, o_ess1 ? "OK" : "MISMATCH");
        printf("  EmulateStereoSuccess2  (0x%06X): %s\n", Offsets::EmulateStereoSuccess2, o_ess2 ? "OK" : "MISMATCH");

        if (!o_caf || !o_mdm || !o_48 || !o_isok || !o_dn || !o_hp || !o_hpc || !o_dcr ||
            !o_e1 || !o_e2 || !o_ch1 || !o_ch2 || !o_ess1 || !o_ess2) {
            printf("\nERROR: Binary validation FAILED - unexpected bytes at patch sites.\n");
            printf("This discord_voice.node does not match the expected build.\n");
            printf("These offsets cannot be safely applied to a different version.\n");
            return false;
        }
        printf("  Validation OK.\n\n");

        int patchCount = 0;
        printf("Applying patches...\n");

        printf("  [1/5] Enabling stereo audio...\n");
        // SDP fmtp "stereo=1" in CommitAudioCodec / CreateAudioStream:
        //   cmp dword [rbx+0xF0], 2 ; cmovnb rdx, rax (where rax = "1", rdx = "0")
        //   Patching imm 0x02 -> 0x00 makes it cmp X, 0 which is always >=, so
        //   the "1" branch is always taken.
        if (!PatchBytes(Offsets::EmulateStereoSuccess1, "\x00", 1)) return false;
        patchCount++;
        if (!PatchBytes(Offsets::EmulateStereoSuccess2, "\x00", 1)) return false;
        patchCount++;
        // Force AudioFrame.num_channels_ = 2 in CreateAudioFrameToProcess:
        //   cmp r12, rax ; cmovnb r12, rax  -> mov r12, 2 (7-byte replacement).
        //   webrtc::voe::RemixAndResample then upmixes mono->stereo when needed.
        if (!PatchBytes(Offsets::CreateAudioFrameStereo, "\x49\xC7\xC4\x02\x00\x00\x00", 7)) return false;
        patchCount++;
        // Bypass mono-collapse in CapturedAudioProcessor::Process:
        //   test al,al ; jz +D ; cmp [rbx+0x80], 9 ; jg +B3
        //   -> 12 NOPs + jmp rel32 (using the original jg disp) so the
        //   "skip downmix" branch is unconditionally taken. Without this,
        //   the captured mic audio is downmixed to mono before reaching the
        //   AudioFrame, defeating the CreateAudioFrameStereo patch above.
        if (!PatchBytes(Offsets::MonoDownmixer,
                        "\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\xE9", 13)) return false;
        patchCount++;
        // Opus encoder default channels = 2 (constructor field at this+8 imm8).
        if (!PatchBytes(Offsets::AudioEncoderOpusConfigSetChannels, "\x02", 1)) return false;
        patchCount++;
        if (!PatchBytes(Offsets::AudioEncoderMultiChannelOpusCh, "\x02", 1)) return false;
        patchCount++;

        printf("  [2/5] Enabling 48kHz sample rate...\n");
        // Default sample rate floor 32000 -> 48000 in CreateAudioFrameToProcess.
        if (!PatchBytes(Offsets::Emulate48Khz, "\x41\xBD\x80\xBB\x00\x00", 6)) return false;
        patchCount++;

        printf("  [3/5] Setting bitrate to %dkbps...\n", BITRATE);
        // Opus encoder default bitrate = 384000 (high dword of mov rax, imm64).
        if (!PatchBytes(Offsets::EncoderConfigInit1, "\x00\xDC\x05\x00", 4)) return false;
        patchCount++;
        if (!PatchBytes(Offsets::EncoderConfigInit2, "\x00\xDC\x05\x00", 4)) return false;
        patchCount++;

        printf("  [4/5] Disabling audio filters...\n");
        // webrtc::HighPassFilter::Process -> ret (void function, safe).
        if (!PatchBytes(Offsets::HighPassFilter, "\xC3", 1)) return false;
        patchCount++;
        // discord uses opus's tonality_analysis -> downmix_and_resample; ret early.
        if (!PatchBytes(Offsets::DownmixFunc, "\xC3", 1)) return false;
        patchCount++;
        // Opus encoder validator -> always returns true (skips error throws).
        if (!PatchBytes(Offsets::AudioEncoderOpusConfigIsOk, "\x48\xC7\xC0\x01\x00\x00\x00\xC3", 8)) return false;
        patchCount++;

        printf("  [5/5] Injecting amplifier (1x gain, channel-normalized)...\n");
        // Replace opus hp_cutoff & dc_reject with our amplifier bodies.
        // Empirical compiled sizes: gcc/clang -O2 emit ~250-320 B per function.
        // 0x180 (384 B) is large enough to capture the full body+ret for any
        // reasonable compiler output, and still safely within both target slots:
        //   hp_cutoff: 431 B available (47 B safety margin)
        //   dc_reject: 398 B available (14 B safety margin)
        // Bytes copied past the function's own `ret` are harmless (never executed).
        if (!PatchBytes(Offsets::HighpassCutoffFilter, (const char*)hp_cutoff, 0x180)) return false;
        patchCount++;
        if (!PatchBytes(Offsets::DcReject, (const char*)dc_reject, 0x180)) return false;
        patchCount++;

        // ---- Post-patch verification ----
        {
            uint32_t bitrate1 = 0, bitrate2 = 0;
            if (!ReadU32LE(Offsets::EncoderConfigInit1, bitrate1) ||
                !ReadU32LE(Offsets::EncoderConfigInit2, bitrate2)) {
                printf("ERROR: Failed to read back bitrate value for verification.\n");
                return false;
            }
            if (bitrate1 != 384000 || bitrate2 != 384000) {
                printf("ERROR: Bitrate mismatch after patching (got %u / %u, expected 384000)\n",
                       bitrate1, bitrate2);
                return false;
            }
            printf("  Verified bitrate (Opus & MultiChannelOpus): %u / %u bps\n", bitrate1, bitrate2);
        }
        {
            uint32_t ch1 = 0, ch2 = 0;
            (void)ReadU32LE(Offsets::AudioEncoderOpusConfigSetChannels, ch1);
            (void)ReadU32LE(Offsets::AudioEncoderMultiChannelOpusCh, ch2);
            printf("  Verified Opus channels byte: 0x%02X\n", (unsigned)(ch1 & 0xFF));
            printf("  Verified MultiChannel Opus channels byte: 0x%02X\n", (unsigned)(ch2 & 0xFF));
        }

        printf("\n  Applied %d patches successfully!\n", patchCount);
        return true;
    }

public:
    DiscordPatcher(const std::string& path) : modulePath(path) {}

    bool PatchFile() {
        printf("\n================================================\n");
        printf("  Discord Voice Quality Patcher (Linux)\n");
        printf("================================================\n");
        printf("  Target:  %s\n", modulePath.c_str());
        printf("  Config:  %dkHz, %dkbps, Stereo\n", SAMPLE_RATE/1000, BITRATE);
        printf("================================================\n\n");

        printf("Opening file for patching...\n");
        int fd = open(modulePath.c_str(), O_RDWR);
        if (fd < 0) {
            printf("ERROR: Cannot open file: %s (errno=%d: %s)\n",
                   modulePath.c_str(), errno, strerror(errno));
            if (errno == EACCES)
                printf("Check file permissions. You may need: chmod +w <file>\n");
            else if (errno == ETXTBSY)
                printf("File is in use by another process. Close Discord first.\n");
            return false;
        }

        struct stat st;
        if (fstat(fd, &st) < 0) {
            printf("ERROR: Cannot stat file (errno=%d: %s)\n", errno, strerror(errno));
            close(fd);
            return false;
        }
        long long fileSize = st.st_size;
        printf("File size: %.2f MB\n", fileSize / (1024.0 * 1024.0));

        void* fileData = mmap(NULL, fileSize, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (fileData == MAP_FAILED) {
            printf("ERROR: Cannot mmap file (errno=%d: %s)\n", errno, strerror(errno));
            close(fd);
            return false;
        }

        if (!ApplyPatches(fileData, fileSize)) {
            munmap(fileData, fileSize);
            close(fd);
            return false;
        }

        printf("\nSyncing patched file to disk...\n");
        if (msync(fileData, fileSize, MS_SYNC) != 0) {
            printf("WARNING: msync failed (errno=%d: %s) - data may not be fully written\n",
                   errno, strerror(errno));
        }
        munmap(fileData, fileSize);
        close(fd);

        printf("\n================================================\n");
        printf("  SUCCESS! Patching Complete!\n");
        printf("  Audio: %dkHz | %dkbps | Stereo\n", SAMPLE_RATE/1000, BITRATE);
        printf("================================================\n\n");
        return true;
    }
};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <path_to_discord_voice.node>\n", argv[0]);
        return 1;
    }
    DiscordPatcher patcher(argv[1]);
    return patcher.PatchFile() ? 0 : 1;
}
PATCHEOF

    # Substitute values into the generated source.
    sed -i "s/SAMPLERATE_VAL/$SAMPLE_RATE/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/BITRATE_VAL/$BITRATE/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_EmulateStereoSuccess1/${OFFSET_EmulateStereoSuccess1}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_EmulateStereoSuccess2/${OFFSET_EmulateStereoSuccess2}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_CreateAudioFrameStereo/${OFFSET_CreateAudioFrameStereo}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_MonoDownmixer/${OFFSET_MonoDownmixer}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_AudioEncoderOpusConfigSetChannels/${OFFSET_AudioEncoderOpusConfigSetChannels}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_AudioEncoderMultiChannelOpusCh/${OFFSET_AudioEncoderMultiChannelOpusCh}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_EncoderConfigInit1/${OFFSET_EncoderConfigInit1}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_EncoderConfigInit2/${OFFSET_EncoderConfigInit2}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_Emulate48Khz/${OFFSET_Emulate48Khz}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_HighPassFilter/${OFFSET_HighPassFilter}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_HighpassCutoffFilter/${OFFSET_HighpassCutoffFilter}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_DcReject/${OFFSET_DcReject}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_DownmixFunc/${OFFSET_DownmixFunc}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_AudioEncoderOpusConfigIsOk/${OFFSET_AudioEncoderOpusConfigIsOk}/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/OFFSET_VAL_FileAdjustment/$FILE_OFFSET_ADJUSTMENT/g" "$TEMP_DIR/patcher.cpp"

    # Substitute original-byte validation arrays
    sed -i "s/ORIG_VAL_CreateAudioFrameStereo/$ORIG_CreateAudioFrameStereo/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_MonoDownmixer/$ORIG_MonoDownmixer/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_Emulate48Khz/$ORIG_Emulate48Khz/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_AudioEncoderOpusConfigIsOk/$ORIG_AudioEncoderOpusConfigIsOk/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_DownmixFunc/$ORIG_DownmixFunc/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_HighPassFilter/$ORIG_HighPassFilter/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_HighpassCutoffFilter/$ORIG_HighpassCutoffFilter/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_DcReject/$ORIG_DcReject/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_EncoderConfigInit1/$ORIG_EncoderConfigInit1/g" "$TEMP_DIR/patcher.cpp"
    sed -i "s/ORIG_VAL_EncoderConfigInit2/$ORIG_EncoderConfigInit2/g" "$TEMP_DIR/patcher.cpp"
}
# endregion Source Code Generation


# region Compilation
compile_patcher() {
    # All log output goes to stderr so stdout is ONLY the exe path
    log_info "Compiling patcher with $COMPILER_TYPE..." >&2

    local exe="$TEMP_DIR/DiscordVoicePatcher"
    rm -f "$exe"

    # Compile both source files together with the C++ compiler
    if ! $COMPILER -O2 -std=c++17 \
        "$TEMP_DIR/patcher.cpp" \
        "$TEMP_DIR/amplifier.cpp" \
        -o "$exe" 2>"$TEMP_DIR/build.log"; then
        log_error "Compilation failed! Build log:" >&2
        echo "" >&2
        cat "$TEMP_DIR/build.log" >&2
        echo "" >&2
        log_info "Source files preserved in $TEMP_DIR for debugging" >&2
        return 1
    fi

    # Verify the exe was actually created and is non-trivial
    if [[ ! -f "$exe" ]]; then
        log_error "Compilation produced no output binary" >&2
        return 1
    fi
    local exe_size
    exe_size=$(stat -c%s "$exe" 2>/dev/null || echo "0")
    if (( exe_size < 4096 )); then
        log_error "Compiled binary is suspiciously small (${exe_size} bytes)" >&2
        return 1
    fi

    chmod +x "$exe"
    log_ok "Compilation successful ($(numfmt --to=iec "$exe_size" 2>/dev/null || echo "${exe_size}B"))" >&2
    # Only the exe path goes to stdout (captured by caller)
    echo "$exe"
    return 0
}
# endregion Compilation


# region Client Selection
SELECTED_CLIENTS=""  # "all" or space-separated indices

select_clients() {
    echo ""
    echo -e "${CYAN}  Installed Discord clients:${NC}"
    echo ""
    for i in "${!CLIENT_NAMES[@]}"; do
        echo -e "  [$(( i + 1 ))] ${WHITE}${CLIENT_NAMES[$i]}${NC}"
        echo -e "      ${DIM}${CLIENT_NODES[$i]}${NC}"
    done
    echo ""
    echo -e "  [${WHITE}A${NC}] Patch all clients"
    echo -e "  [${WHITE}C${NC}] Cancel"
    echo ""

    read -rp "  Choice: " choice

    case "${choice^^}" in
        C) log_warn "Cancelled"; exit 0 ;;
        A|"") SELECTED_CLIENTS="all"; return 0 ;;
        [0-9]*)
            if [[ ! "$choice" =~ ^[0-9]+$ ]]; then
                log_error "Invalid selection"; exit 1
            fi
            if (( choice >= 1 && choice <= ${#CLIENT_NAMES[@]} )); then
                SELECTED_CLIENTS="$(( choice - 1 ))"
                return 0
            fi
            log_error "Selection out of range (1-${#CLIENT_NAMES[@]})"; exit 1
            ;;
        *) log_error "Invalid selection"; exit 1 ;;
    esac
}
# endregion Client Selection


# region Patch a single client
patch_client() {
    local idx="$1"
    local name="${CLIENT_NAMES[$idx]}"
    local node_path="${CLIENT_NODES[$idx]}"

    echo ""
    log_info "=== Processing: $name ==="
    log_info "Node: $node_path"

    if ! $PATCH_LOCAL_ONLY; then
        if ! backup_node "$node_path" "$name"; then
            if ! $SKIP_BACKUP; then
                log_error "Backup failed, aborting patch for safety"
                return 1
            fi
        fi
        if ! install_linux_voice_bundle_for_client "$node_path"; then
            return 1
        fi
    fi

    if ! verify_binary "$node_path" "$name"; then
        return 1
    fi

    if $PATCH_LOCAL_ONLY; then
        if ! backup_node "$node_path" "$name"; then
            if ! $SKIP_BACKUP; then
                log_error "Backup failed, aborting patch for safety"
                return 1
            fi
        fi
    fi

    # Ensure writable
    if [[ ! -w "$node_path" ]]; then
        log_warn "File not writable, attempting chmod..."
        chmod +w "$node_path" 2>/dev/null || {
            log_error "Cannot make file writable. Try: sudo chmod +w '$node_path'"
            return 1
        }
    fi

    # Check file is not currently open/locked by another process
    if command -v fuser &>/dev/null; then
        if fuser "$node_path" &>/dev/null; then
            log_warn "File is currently open by another process"
            log_warn "  This is expected if Discord was recently closed. Proceeding..."
        fi
    fi

    # Generate source
    log_info "Generating source files..."
    generate_amplifier_source
    generate_patcher_source
    log_ok "Source files generated"

    # Compile
    local exe
    exe=$(compile_patcher) || return 1

    # Run patcher
    log_info "Applying binary patches..."
    if "$exe" "$node_path"; then
        log_ok "Successfully patched $name!"
        return 0
    else
        log_error "Patcher failed for $name"
        log_info "Source files preserved in $TEMP_DIR for debugging"
        return 1
    fi
}
# endregion Patch a single client


# region Cleanup
cleanup() {
    # Guard: don't clean if temp dir was never created
    [[ -d "${TEMP_DIR:-}" ]] || return 0

    # Only clean up source/binary on success - preserve on failure for debugging
    if [[ "$PATCH_SUCCESS" == "true" ]]; then
        rm -f "$TEMP_DIR/patcher.cpp" "$TEMP_DIR/amplifier.cpp" \
              "$TEMP_DIR/DiscordVoicePatcher" "$TEMP_DIR/build.log" 2>/dev/null
    else
        # Keep source + build log for debugging, just remove the binary
        rm -f "$TEMP_DIR/DiscordVoicePatcher" 2>/dev/null
    fi
}
# endregion Cleanup


# region Main
main() {
    banner

    # Handle restore mode
    if $RESTORE_MODE; then
        restore_from_backup
        exit 0
    fi

    show_settings

    # Find Discord
    find_discord_clients || exit 1

    # Find compiler
    find_compiler || exit 1

    if ! $PATCH_LOCAL_ONLY; then
        download_linux_voice_bundle_from_github || exit 1
    else
        log_info "Patch-local mode: skipping GitHub voice bundle download."
    fi

    # Select clients (skip menu in silent/patch-all mode)
    if $PATCH_ALL; then
        SELECTED_CLIENTS="all"
    else
        select_clients
    fi

    # Handle Discord running - prompt to close (matches Windows behavior)
    handle_discord_running

    local success=0
    local failed=0
    local total=0
    local i

    if [[ "$SELECTED_CLIENTS" == "all" ]]; then
        total=${#CLIENT_NAMES[@]}
        for i in "${!CLIENT_NAMES[@]}"; do
            if patch_client "$i"; then
                success=$(( success + 1 ))
            else
                failed=$(( failed + 1 ))
            fi
        done
    else
        total=1
        if patch_client "$SELECTED_CLIENTS"; then
            success=1
        else
            failed=1
        fi
    fi

    if [[ "$failed" -eq 0 ]]; then
        PATCH_SUCCESS=true
    fi

    cleanup

    echo ""
    echo -e "${CYAN}===============================================${NC}"
    if [[ "$failed" -eq 0 ]]; then
        echo -e "${GREEN}  [OK] PATCHING COMPLETE: $success/$total successful${NC}"
    else
        echo -e "${YELLOW}  PATCHING: $success/$total successful, $failed failed${NC}"
    fi
    echo -e "${CYAN}===============================================${NC}"
    echo ""
    echo "Restart Discord to apply changes."
}

trap cleanup EXIT
main "$@"
# endregion Main
