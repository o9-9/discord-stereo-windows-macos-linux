#!/usr/bin/env python3
"""Minimal Stereo Hub: Patch (download patched module) / Revert (UNPATCHED backup). Stdlib + Tk only."""

# region Imports And Optional Modules

from __future__ import annotations

import io
import json
import math
import os
import platform
import shutil
import sys
import time
import traceback
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import subprocess
import re
import queue
import threading


try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:  # pragma: no cover
    tk = None  # type: ignore

try:  # pragma: no cover
    from . import discord_stereo_hub_DEV as devhub  # type: ignore
except Exception:  # pragma: no cover
    try:
        import discord_stereo_hub_DEV as devhub  # type: ignore
    except Exception:
        devhub = None  # type: ignore

# endregion Imports And Optional Modules

# region App Metadata


APP_NAME = "Discord Stereo Hub"
APP_VERSION = "1.2"

# endregion App Metadata

# region UI Helpers


def _lerp_rgb(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, float(t)))

    def parse(h: str) -> Tuple[int, int, int]:
        h = h.strip()
        if h.startswith("#") and len(h) >= 7:
            return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return 0, 0, 0

    a = parse(c1)
    b = parse(c2)
    r = int(a[0] + (b[0] - a[0]) * t)
    g = int(a[1] + (b[1] - a[1]) * t)
    b_ = int(a[2] + (b[2] - a[2]) * t)
    return "#%02x%02x%02x" % (r, g, b_)

# endregion UI Helpers

# region Remote Configuration


PATCHED_WINDOWS_GITHUB_CONTENTS_API = (
    "https://api.github.com/repos/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/contents/"
    "Updates%2FNodes%2FPatched%20Nodes%20%28for%20Installer%29%2FWindows"
)
PATCHED_LINUX_GITHUB_CONTENTS_API = (
    "https://api.github.com/repos/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/contents/"
    "Updates%2FNodes%2FPatched%20Nodes%20%28for%20Installer%29%2FLinux"
)
PATCHED_MACOS_ZIP_URL = "https://example.invalid/Updates/Nodes/Patched/macOS/latest.zip"

OFFLINE_SKIP_REMOTE_ENV = "DISCORD_STEREO_SKIP_REMOTE"
SKIP_HUB_SELF_UPDATE_ENV = "DISCORD_STEREO_SKIP_HUB_SELF_UPDATE"
HUB_SELF_UPDATE_RAW_URL = (
    "https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/"
    "main/STEREO%20HUB/discord_stereo_hub.py"
)

_RE_APP_VERSION_ASSIGN = re.compile(r"^\s*APP_VERSION\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)

# endregion Remote Configuration

# region Hub Auto Update


def _version_tuple_for_cmp(ver: str) -> Tuple[int, ...]:
    parts = [int(x) for x in re.findall(r"\d+", ver or "")]
    return tuple(parts) if parts else (0,)


def _compare_semver_like(a: str, b: str) -> int:
    ta = _version_tuple_for_cmp(a)
    tb = _version_tuple_for_cmp(b)
    n = max(len(ta), len(tb))
    ta_x = ta + (0,) * (n - len(ta))
    tb_x = tb + (0,) * (n - len(tb))
    if ta_x < tb_x:
        return -1
    if ta_x > tb_x:
        return 1
    return 0


def _parse_app_version_from_hub_source(src: str) -> Optional[str]:
    m = _RE_APP_VERSION_ASSIGN.search(src)
    if not m:
        return None
    return (m.group(1) or "").strip()


def _hub_script_fs_path() -> Optional[Path]:
    try:
        p = Path(__file__).resolve()
        if p.suffix.lower() == ".py" and p.is_file():
            return p
    except Exception:
        pass
    return None


def _raw_download_looks_like_error_page(data: bytes) -> bool:
    head = data[:512].lstrip()
    return head.startswith(b"<!DOCTYPE") or head.startswith(b"<html") or b"<title>" in head[:220].lower()


def _looks_like_stereo_hub_py(src: str) -> bool:
    if len(src) < 800:
        return False
    if APP_NAME not in src:
        return False
    if _parse_app_version_from_hub_source(src) is None:
        return False
    if "def main()" not in src:
        return False
    return True


def _atomic_replace_hub_py(hub_path: Path, new_text: str) -> None:
    tmp_path = hub_path.with_name(hub_path.name + ".self_update.tmp")
    try:
        tmp_path.write_text(new_text, encoding="utf-8", newline="\n")
        os.replace(tmp_path, hub_path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _restart_hub_program(hub_path: Path) -> None:
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    hub_rp = hub_path.resolve()
    cwd = str(hub_rp.parent)
    exe = sys.executable
    child_args = [exe, str(hub_rp)] + sys.argv[1:]

    def _spawn_detach_and_hard_exit() -> None:
        subprocess.Popen(child_args, cwd=cwd, close_fds=False)
        os._exit(0)

    if sys.platform == "win32":
        try:
            _spawn_detach_and_hard_exit()
        except Exception as exc_win:
            try:
                subprocess.Popen(child_args, cwd=cwd, close_fds=False)
                os._exit(0)
            except Exception as exc2:
                sys.stderr.write(
                    "%s failed to restart after self-update (%s); %s. Re-open manually.\n"
                    % (APP_NAME, human_exc(exc_win), human_exc(exc2))
                )
                sys.exit(1)

    try:
        try:
            os.chdir(cwd)
        except Exception:
            pass
        os.execv(exe, child_args)
    except OSError as exc:
        try:
            _spawn_detach_and_hard_exit()
        except Exception as exc2:
            sys.stderr.write(
                "%s failed to restart after self-update (%s); %s. Re-open manually.\n"
                % (APP_NAME, human_exc(exc), human_exc(exc2))
            )
            sys.exit(1)


def _hub_self_update_skip_reason_or_ready_path() -> Tuple[Optional[str], Optional[Path]]:
    if os.environ.get(SKIP_HUB_SELF_UPDATE_ENV, "").strip() == "1":
        return (SKIP_HUB_SELF_UPDATE_ENV + "=1", None)
    if os.environ.get(OFFLINE_SKIP_REMOTE_ENV, "").strip() == "1":
        return (OFFLINE_SKIP_REMOTE_ENV + "=1", None)
    if getattr(sys, "frozen", False):
        return ("frozen executable bundle (updates require a newer build or python script)", None)
    hub_path = _hub_script_fs_path()
    if hub_path is None:
        return ("script location unavailable — run discord_stereo_hub.py as a file", None)
    try:
        probe = hub_path.stat()
        if sys.platform != "win32" and not (probe.st_mode & 0o200):
            return ("hub script path is read-only (%s)" % hub_path, hub_path)
    except Exception as exc:
        return ("cannot stat hub script: %s" % human_exc(exc), hub_path)
    return (None, hub_path)

# endregion Hub Auto Update

# region Platform And Paths


def detect_platform_key() -> str:
    sp = sys.platform.lower()
    if sp.startswith("win"):
        return "windows"
    if sp.startswith("darwin"):
        return "macos"
    if sp.startswith("linux"):
        return "linux"
    return sp or "unknown"


def hub_data_dir() -> Path:
    pf = detect_platform_key()
    if pf == "windows":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(root) / "DiscordStereoHubSimple"
    if pf == "macos":
        return Path.home() / "Library" / "Application Support" / "DiscordStereoHubSimple"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg) / "DiscordStereoHubSimple"
    return Path.home() / ".local" / "share" / "DiscordStereoHubSimple"


def log_path() -> Path:
    return hub_data_dir() / "discord_stereo_hub.log"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def human_exc(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"

# endregion Platform And Paths

# region Discord Paths And Labels


def _readable_os() -> str:
    try:
        return f"{platform.system()} {platform.release()} ({platform.machine()})"
    except Exception:
        return sys.platform


def _platform_label(key: str) -> str:
    k = (key or "").strip().lower()
    return {"windows": "Windows", "macos": "macOS", "linux": "Linux"}.get(k, k.title() or "Unknown")


def _default_discord_roots() -> Tuple[Path, ...]:
    pf = detect_platform_key()
    home = Path.home()
    if pf == "windows":
        la = os.environ.get("LOCALAPPDATA") or ""
        return tuple(
            Path(p)
            for p in (
                os.path.join(la, "Discord"),
                os.path.join(la, "DiscordCanary"),
                os.path.join(la, "DiscordPTB"),
                os.path.join(la, "DiscordDevelopment"),
                os.path.join(la, "Lightcord"),
                os.path.join(la, "Vencord"),
                os.path.join(la, "Equicord"),
                os.path.join(la, "BetterVencord"),
            )
            if p
        )
    if pf == "macos":
        return (
            home / "Library" / "Application Support" / "discord",
            home / "Library" / "Application Support" / "discordcanary",
            home / "Library" / "Application Support" / "discordptb",
        )
    return (
        home / ".config" / "discord",
        home / ".config" / "discordcanary",
        home / ".config" / "discordptb",
        home / ".config" / "discorddevelopment",
        home / ".var" / "app" / "com.discordapp.Discord" / "config" / "discord",
    )


def infer_discord_release_channel_from_root(discord_root: Path) -> Optional[str]:
    try:
        name = (discord_root.name or "").strip().lower()
    except Exception:
        return None
    if not name:
        return None
    if name == "discorddevelopment":
        return "Development"
    if name == "discordcanary":
        return "Canary"
    if name == "discordptb":
        return "PTB"
    if name == "discord":
        return "Stable"
    return None


_QUICK_HUB_CLIENT_FOLDER_ALIASES = {
    "lightcord": "Lightcord",
    "lightchord": "Lightcord",
}


def quick_hub_client_prefix_for_badge(discord_root: Path) -> str:
    try:
        leaf = (discord_root.name or "").strip().lower()
    except Exception:
        leaf = ""

    if leaf in ("discord", "vencord", "equicord", "bettervencord"):
        return "Stable"

    ch = infer_discord_release_channel_from_root(discord_root)
    if ch:
        return ch

    try:
        raw = (discord_root.name or "").strip()
    except Exception:
        return ""
    if not raw:
        return ""
    low = raw.lower()
    if low in _QUICK_HUB_CLIENT_FOLDER_ALIASES:
        return _QUICK_HUB_CLIENT_FOLDER_ALIASES[low]
    return raw.replace("_", " ").title()


def quick_hub_badge_text(root_s: str) -> str:
    p = (root_s or "").strip()
    if not p:
        return "--"
    root = Path(p)
    if not root.is_dir():
        return "--"
    prefix = quick_hub_client_prefix_for_badge(root)
    ad = quick_hub_resolve_app_dir_for_root(root_s)
    build = discord_client_build_label(root, ad, None) if ad else ""
    if prefix and build:
        return "%s %s" % (prefix, build)
    if prefix:
        return prefix
    if build:
        return build
    return "--"

# endregion Discord Paths And Labels

# region Voice Module Discovery


def _looks_like_discord_voice_dir(p: Path) -> bool:
    return p.is_dir() and (p / "discord_voice.node").is_file()


def find_discord_voice_dir_under(root: Path) -> Optional[Path]:
    if not root or not root.is_dir():
        return None
    try:
        app_dirs = sorted([p for p in root.glob("app-*") if p.is_dir()], reverse=True)
        for app in app_dirs[:6]:
            mods = app / "modules"
            if not mods.is_dir():
                continue
            for m in sorted(mods.glob("discord_voice*"))[:8]:
                cand = m / "discord_voice"
                if _looks_like_discord_voice_dir(cand):
                    return cand
                if _looks_like_discord_voice_dir(m):
                    return m
    except Exception:
        pass
    try:
        hits = []
        for p in root.rglob("discord_voice.node"):
            try:
                if p.is_file():
                    hits.append(p)
            except Exception:
                continue
            if len(hits) >= 8:
                break
        ranked = sorted(hits, key=lambda x: x.stat().st_mtime, reverse=True)
        for node in ranked:
            if node.parent.name.lower() == "discord_voice":
                return node.parent
        if ranked:
            return ranked[0].parent
    except Exception:
        return None
    return None


class Target:
    def __init__(
        self,
        discord_root: Path,
        voice_dir: Path,
        app_dir: Optional[Path] = None,
        exe_name: Optional[str] = None,
        diagnostics: Optional[str] = None,
    ):
        self.discord_root = discord_root
        self.voice_dir = voice_dir
        self.app_dir = app_dir
        self.exe_name = exe_name
        self.diagnostics = diagnostics


def _windows_client_exe_for_root(root: Path) -> str:
    low = (root.name or "").strip().lower()
    if low == "lightcord":
        return "Lightcord.exe"
    if "discordcanary" in low:
        return "DiscordCanary.exe"
    if "discordptb" in low:
        return "DiscordPTB.exe"
    if "discorddevelopment" in low:
        return "DiscordDevelopment.exe"
    return "Discord.exe"


def _parse_app_version_from_dirname(name: str) -> Tuple[int, int, int, int]:
    m = re.search(r"(?i)\bapp-([\d\.]+)\b", name or "")
    if not m:
        return (0, 0, 0, 0)
    parts = []
    for p in m.group(1).split("."):
        try:
            parts.append(int(p))
        except Exception:
            return (0, 0, 0, 0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def find_discord_app_dir(discord_root: Path) -> Optional[Path]:
    try:
        apps = [p for p in discord_root.glob("app-*") if p.is_dir()]
    except Exception:
        return None
    apps.sort(key=lambda p: _parse_app_version_from_dirname(p.name), reverse=True)
    return apps[0] if apps else None


def _find_app_dir_from_voice_dir(voice_dir: Path) -> Optional[Path]:
    try:
        p = voice_dir.resolve()
    except Exception:
        p = voice_dir
    for _ in range(12):
        name = (p.name or "").strip()
        if name.lower().startswith("app-") and p.is_dir():
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent
    return None


def discord_client_build_label(
    discord_root: Path,
    app_dir: Optional[Path] = None,
    voice_dir: Optional[Path] = None,
) -> str:
    app = app_dir
    if app is None and voice_dir is not None:
        app = _find_app_dir_from_voice_dir(voice_dir)
    if app is None:
        app = find_discord_app_dir(discord_root)
    if app is None:
        return ""
    m = re.search(r"(?i)^app-([\d\.]+)\s*$", (app.name or "").strip())
    if not m:
        return ""
    ver = m.group(1).strip()
    parts = [x for x in ver.split(".") if x.isdigit()]
    if not parts:
        return ver
    return parts[-1]


def quick_hub_resolve_app_dir_for_root(root_s: str) -> Optional[Path]:
    p = (root_s or "").strip()
    if not p:
        return None
    root = Path(p)
    if not root.is_dir():
        return None
    vd, app_dir, _diag = find_voice_dir_with_diagnostics(root)
    if vd:
        if app_dir:
            return app_dir
        return _find_app_dir_from_voice_dir(vd)
    vd2 = find_discord_voice_dir_under(root)
    if vd2:
        ad = _find_app_dir_from_voice_dir(vd2)
        if ad:
            return ad
    return find_discord_app_dir(root)


def quick_hub_badge_label_for_discord_root(root_s: str) -> str:
    root = (root_s or "").strip()
    if not root:
        return ""
    ad = quick_hub_resolve_app_dir_for_root(root_s)
    if not ad:
        return ""
    return discord_client_build_label(Path(root), ad, None)


def find_voice_dir_from_app_dir(app_dir: Path) -> Optional[Path]:
    mods = app_dir / "modules"
    if not mods.is_dir():
        return None
    try:
        for mdir in sorted(mods.glob("discord_voice*")):
            cand = mdir / "discord_voice"
            if _looks_like_discord_voice_dir(cand):
                return cand
            if _looks_like_discord_voice_dir(mdir):
                return mdir
    except Exception:
        return None
    return None


def find_voice_dir_with_diagnostics(discord_root: Path) -> Tuple[Optional[Path], Optional[Path], str]:
    if not discord_root or not discord_root.is_dir():
        return None, None, "Discord root folder not found."
    app_dir = find_discord_app_dir(discord_root)
    if not app_dir:
        return None, None, "No app-* folders found. Discord may not be fully installed."
    mods = app_dir / "modules"
    if not mods.is_dir():
        return None, app_dir, f"No 'modules' folder found in: {app_dir.name} (Discord may be corrupted)."
    voice_dirs = list(mods.glob("discord_voice*"))
    if not voice_dirs:
        return None, app_dir, "No discord_voice module folder found. Join a voice channel once so Discord downloads modules."
    vd = find_voice_dir_from_app_dir(app_dir)
    if not vd:
        return None, app_dir, "discord_voice module found, but discord_voice.node was not found inside it."
    return vd, app_dir, ""


def resolve_target(preferred_root: Optional[Path] = None) -> Tuple[Optional[Target], str]:
    roots = []
    if preferred_root:
        roots.append(preferred_root)
    roots.extend([p for p in _default_discord_roots() if p not in roots])

    last_diag = ""
    for r in roots:
        vd, app_dir, diag = find_voice_dir_with_diagnostics(r)
        if vd:
            exe_name = _windows_client_exe_for_root(r) if detect_platform_key() == "windows" else None
            return Target(discord_root=r, voice_dir=vd, app_dir=app_dir, exe_name=exe_name, diagnostics=None), ""
        if diag:
            last_diag = f"{r}: {diag}"
        vd2 = find_discord_voice_dir_under(r)
        if vd2:
            exe_name = _windows_client_exe_for_root(r) if detect_platform_key() == "windows" else None
            return Target(discord_root=r, voice_dir=vd2, app_dir=app_dir, exe_name=exe_name, diagnostics=None), ""
    msg = "Could not find `discord_voice.node`. Open Discord once (join a voice channel), then try again, or use Browse."
    if last_diag:
        msg += "\n\nDetails:\n" + last_diag
    return None, msg

# endregion Voice Module Discovery

# region Backup And Metadata


def permanent_backup_dir(target: Target) -> Path:
    key = str(target.discord_root).replace("\\", "_").replace("/", "_").replace(":", "")
    return hub_data_dir() / "backups" / key / "UNPATCHED"


def quick_hub_meta_path(discord_root: Path) -> Path:
    key = str(discord_root).replace("\\", "_").replace("/", "_").replace(":", "")
    return hub_data_dir() / "backups" / key / "quick_hub_meta.json"


def record_quick_hub_last_patch(discord_root: Path) -> None:
    path = quick_hub_meta_path(discord_root)
    safe_mkdir(path.parent)
    payload = {
        "last_patch_utc": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_last_patch_utc_for_ui(iso_utc: str) -> str:
    s = (iso_utc or "").strip()
    if not s:
        return ""
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()
        tz = (local.tzname() or "").strip()
        if tz:
            return local.strftime("%Y-%m-%d %H:%M") + " " + tz
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def quick_hub_last_patch_caption(root_s: str) -> str:
    p = (root_s or "").strip()
    if not p:
        return "Last patch with this hub: set a Discord install folder to see history."
    root = Path(p)
    if not root.is_dir():
        return "Last patch with this hub: that folder was not found."
    meta = quick_hub_meta_path(root)
    if not meta.is_file():
        return "Last patch with this hub: never"
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return "Last patch with this hub: (could not read saved data)"
    iso = (data.get("last_patch_utc") or data.get("last_patch_iso") or "").strip()
    if not iso:
        return "Last patch with this hub: never"
    shown = _format_last_patch_utc_for_ui(iso)
    return "Last patch with this hub: %s" % shown if shown else "Last patch with this hub: never"

# endregion Backup And Metadata

# region Filesystem Helpers


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    safe_mkdir(dst.parent)
    shutil.copytree(src, dst)


def _auth_token() -> str:
    return (os.environ.get("DISCORD_STEREO_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()

# endregion Filesystem Helpers

# region Process Management

# Mirrors Discord_voice_node_patcher.ps1: scope Update.exe under the selected install.


def _windows_kill_discord_update_processes_under_root(discord_root: Path) -> None:
    root = str(discord_root).replace("'", "''")
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$root='" + root + "';"
        "$procs=Get-CimInstance Win32_Process -Filter \"Name='Update.exe'\";"
        "foreach($p in $procs){"
        "  $ep=$p.ExecutablePath;"
        "  if($ep -and $ep -like ($root + '*')){"
        "    try{ Stop-Process -Id $p.ProcessId -Force }catch{}"
        "  }"
        "}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def stop_discord_processes(log: "Logger", *, target: Optional[Target] = None) -> None:
    pf = detect_platform_key()
    names = [
        "Discord",
        "DiscordCanary",
        "DiscordPTB",
        "DiscordDevelopment",
        "Lightcord",
        "Vencord",
        "Equicord",
        "BetterVencord",
        "Update",
    ]
    try:
        if pf == "windows":
            for n in names:
                if n.lower() == "update":
                    continue
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", f"{n}.exe"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except Exception:
                    pass
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "Discord*.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass
            try:
                if target and target.discord_root and target.discord_root.is_dir():
                    _windows_kill_discord_update_processes_under_root(target.discord_root)
            except Exception:
                pass
            time.sleep(0.6)
            log.ok("Closed Discord processes (best-effort).")
            return
        for n in names:
            try:
                subprocess.run(
                    ["pkill", "-f", n],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass
        time.sleep(0.6)
        log.ok("Closed Discord processes (best-effort).")
    except Exception as e:
        log.warn(f"Could not stop Discord processes: {human_exc(e)}")


def relaunch_discord_for_target(target: Target, log: "Logger") -> None:
    pf = detect_platform_key()
    root = target.discord_root

    if pf == "windows":
        upd = root / "Update.exe"
        exe = (target.exe_name or _windows_client_exe_for_root(root)).strip() or "Discord.exe"
        tmp = os.environ.get("TEMP") or os.environ.get("TMP") or "."
        out_log = Path(tmp) / "DiscordStereoHubSimple_discord_out.txt"
        err_log = Path(tmp) / "DiscordStereoHubSimple_discord_err.txt"
        cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        def _popen_like_patcher(argv: list, cwd: str) -> None:
            out_f = open(out_log, "w", encoding="utf-8", errors="replace")
            try:
                err_f = open(err_log, "w", encoding="utf-8", errors="replace")
                try:
                    subprocess.Popen(
                        argv,
                        cwd=cwd,
                        stdout=out_f,
                        stderr=err_f,
                        close_fds=False,
                        creationflags=cflags,
                    )
                finally:
                    err_f.close()
            finally:
                out_f.close()

        if upd.is_file():
            try:
                _popen_like_patcher([str(upd), "--processStart", exe], str(root))
                log.ok(f"Relaunched Discord via Update.exe ({exe})")
                return
            except Exception as e:
                log.warn(f"Relaunch via Update.exe failed: {human_exc(e)}")

        try:
            app = target.app_dir or find_discord_app_dir(root)
            if app:
                exe_path = app / exe
                if not exe_path.is_file() and exe != "Discord.exe":
                    if (app / "Discord.exe").is_file():
                        exe_path = app / "Discord.exe"
                if exe_path.is_file():
                    _popen_like_patcher([str(exe_path)], str(app))
                    log.ok(f"Relaunched Discord directly ({exe_path.name})")
                    return
        except Exception as e:
            log.warn(f"Could not locate app-* exe for relaunch: {human_exc(e)}")
        log.warn("Could not relaunch Discord automatically. Please start it manually.")
        return

    if pf == "macos":
        try:
            subprocess.Popen(["open", "-a", "Discord"])
            log.ok("Relaunched Discord (open -a Discord)")
            return
        except Exception:
            pass
        try:
            subprocess.Popen(["open", "/Applications/Discord.app"])
            log.ok("Relaunched Discord (/Applications/Discord.app)")
            return
        except Exception as e:
            log.warn(f"Could not relaunch Discord on macOS: {human_exc(e)}")
        return

    if pf == "linux":
        for cmd in (["discord"], ["Discord"], ["flatpak", "run", "com.discordapp.Discord"]):
            try:
                subprocess.Popen(cmd)
                log.ok(f"Relaunched Discord ({' '.join(cmd)})")
                return
            except Exception:
                continue
        log.warn("Could not relaunch Discord automatically on Linux. Please start it manually.")
        return

    log.warn("Auto-relaunch is not supported on this OS.")

# endregion Process Management

# region Staging And Downloads


def clear_dir_contents(p: Path) -> None:
    if not p.exists():
        safe_mkdir(p)
        return
    if not p.is_dir():
        raise RuntimeError(f"Expected a folder, got: {p}")
    for child in p.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=False)
            else:
                child.unlink(missing_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to remove {child}: {e}")


def copy_dir_contents(src_dir: Path, dst_dir: Path) -> None:
    safe_mkdir(dst_dir)
    for src in src_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        safe_mkdir(dst.parent)
        shutil.copy2(src, dst)


def download_bytes(url: str, timeout_s: int = 120, *, accept: Optional[str] = None) -> bytes:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", f"{APP_NAME.replace(' ', '')}/{APP_VERSION}")
    req.add_header("Cache-Control", "no-cache")
    req.add_header("Pragma", "no-cache")
    if accept:
        req.add_header("Accept", accept)
    tok = _auth_token()
    if tok:
        if tok.startswith("github_pat_"):
            req.add_header("Authorization", f"Bearer {tok}")
        else:
            req.add_header("Authorization", f"token {tok}")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def validate_download_payload(name: str, data: bytes) -> None:
    if not data:
        raise RuntimeError(f"{name}: empty download")
    head = data[:256].lstrip()
    if head.startswith(b"<!DOCTYPE html") or head.startswith(b"<html") or b"<title>" in head[:200].lower():
        raise RuntimeError(f"{name}: download looks like HTML (rate limit / error page)")
    low = (name or "").lower()
    binary_exts = (".node", ".dll", ".exe", ".tflite", ".so", ".dylib")
    if low.endswith(binary_exts) and len(data) < 1024:
        raise RuntimeError(f"{name}: binary download too small ({len(data)} bytes)")


def extract_zip_bytes_to_dir(zip_bytes: bytes, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    safe_mkdir(dest)
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        zf.extractall(dest)


def find_voice_dir_in_payload_dir(payload_root: Path) -> Optional[Path]:
    if _looks_like_discord_voice_dir(payload_root):
        return payload_root
    if _looks_like_discord_voice_dir(payload_root / "discord_voice"):
        return payload_root / "discord_voice"
    try:
        for p in payload_root.rglob("discord_voice.node"):
            if p.is_file():
                return p.parent
    except Exception:
        return None
    return None

# endregion Staging And Downloads

# region GitHub Patched Nodes


def patched_zip_url_for_platform() -> str:
    pf = detect_platform_key()
    if pf == "windows":
        return PATCHED_WINDOWS_GITHUB_CONTENTS_API
    if pf == "macos":
        return PATCHED_MACOS_ZIP_URL
    if pf == "linux":
        return PATCHED_LINUX_GITHUB_CONTENTS_API
    return PATCHED_WINDOWS_GITHUB_CONTENTS_API


def _download_github_contents_listing(api_url: str, timeout_s: int = 60) -> list:
    raw = download_bytes(api_url, timeout_s=timeout_s, accept="application/vnd.github.v3+json")
    try:
        j = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        raise RuntimeError(f"GitHub listing JSON parse failed: {e}")
    if not isinstance(j, list):
        raise RuntimeError("GitHub contents API returned unexpected JSON (expected list).")
    return j


def download_github_folder_to_dir(api_url: str, dest: Path, log: "Logger") -> None:
    listing = _download_github_contents_listing(api_url)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    safe_mkdir(dest)
    n_ok = 0
    n_fail = 0
    for ent in listing:
        try:
            if not isinstance(ent, dict):
                continue
            if ent.get("type") != "file":
                continue
            name = str(ent.get("name") or "").strip()
            dl = str(ent.get("download_url") or "").strip()
            if not name or not dl:
                continue
            log.info(f"Downloading: {name}")
            data = download_bytes(dl, timeout_s=120)
            validate_download_payload(name, data)
            (dest / name).write_bytes(data)
            n_ok += 1
        except Exception as e:
            n_fail += 1
            log.warn(f"Failed: {ent.get('name','?')} ({human_exc(e)})")
    if n_ok == 0:
        raise RuntimeError("No files were downloaded from the GitHub folder (empty listing or blocked/rate-limited).")
    if n_fail:
        log.warn(f"Downloaded {n_ok} file(s), {n_fail} failed.")
    else:
        log.ok(f"Downloaded {n_ok} file(s).")

# endregion GitHub Patched Nodes

# region Patch And Revert


def ensure_permanent_unpatched_backup(target: Target, log: "Logger") -> Path:
    bd = permanent_backup_dir(target)
    if bd.is_dir() and _looks_like_discord_voice_dir(bd):
        log.info(f"Permanent UNPATCHED backup already exists: {bd}")
        return bd
    log.info("Creating permanent UNPATCHED backup (first time)...")
    copy_tree(target.voice_dir, bd)
    log.ok(f"Saved permanent UNPATCHED backup: {bd}")
    return bd


def _local_patched_bundle_dir_for_platform() -> Optional[Path]:
    pf = detect_platform_key()
    ws = Path(__file__).resolve().parents[1]
    if pf == "windows":
        return ws / "Updates" / "Nodes" / "Patched Nodes (for Installer)" / "Windows"
    if pf == "linux":
        return ws / "Updates" / "Nodes" / "Patched Nodes (for Installer)" / "Linux"
    if pf == "macos":
        return ws / "Updates" / "Nodes" / "Patched Nodes (for Installer)" / "macOS"
    return None


def patch(target: Target, log: "Logger") -> None:
    ensure_permanent_unpatched_backup(target, log)
    stop_discord_processes(log, target=target)
    pf = detect_platform_key()
    staging = hub_data_dir() / "staging" / "patched_payload"
    payload_voice: Optional[Path] = None

    if pf == "windows" or pf == "linux":
        if os.environ.get(OFFLINE_SKIP_REMOTE_ENV, "").strip() == "1":
            local = _local_patched_bundle_dir_for_platform()
            if not local or not local.is_dir():
                raise RuntimeError(f"{OFFLINE_SKIP_REMOTE_ENV}=1 but local patched bundle folder was not found.")
            log.info(f"Offline mode: using local patched bundle: {local}")
            copy_dir_contents(local, staging)
        else:
            api = patched_zip_url_for_platform()
            label = "Windows" if pf == "windows" else "Linux"
            log.info(f"Fetching the latest patched module ({label})...")
            download_github_folder_to_dir(api, staging, log)
        payload_voice = find_voice_dir_in_payload_dir(staging)
    else:
        url = patched_zip_url_for_platform()
        if "example.invalid" in url:
            raise RuntimeError(
                "Patched-binary download URL is a placeholder for this OS.\n"
                "Configure PATCHED_* constants in discord_stereo_hub.py."
            )
        log.info(f"Downloading patched voice module: {url}")
        z = download_bytes(url)
        validate_download_payload("patched payload", z)
        log.ok(f"Downloaded {len(z)} bytes")
        extract_zip_bytes_to_dir(z, staging)
        payload_voice = find_voice_dir_in_payload_dir(staging)

    if not payload_voice or not _looks_like_discord_voice_dir(payload_voice):
        raise RuntimeError("Downloaded payload does not contain a valid discord_voice module (discord_voice.node missing).")

    log.info(f"Installing patched module to: {target.voice_dir}")
    clear_dir_contents(target.voice_dir)
    copy_dir_contents(payload_voice, target.voice_dir)
    log.ok("Patch applied.")
    try:
        record_quick_hub_last_patch(target.discord_root)
    except Exception:
        pass
    relaunch_discord_for_target(target, log)


def revert(target: Target, log: "Logger") -> None:
    bd = permanent_backup_dir(target)
    if not _looks_like_discord_voice_dir(bd):
        raise RuntimeError(f"No permanent UNPATCHED backup found at: {bd}\nRun Patch once first to create the baseline.")

    stop_discord_processes(log, target=target)
    log.info(f"Restoring UNPATCHED backup to: {target.voice_dir}")
    clear_dir_contents(target.voice_dir)
    copy_dir_contents(bd, target.voice_dir)
    log.ok("Revert complete.")
    relaunch_discord_for_target(target, log)

# endregion Patch And Revert

# region Logging


class Logger:

    def __init__(self, text: "tk.Text"):
        self.text = text
        self._main_thread_id = threading.get_ident()
        safe_mkdir(log_path().parent)
        ok_c = getattr(devhub, "ONLINE_GREEN", "#23a559")
        warn_c = getattr(devhub, "YELLOW", "#fdd835")
        fail_c = getattr(devhub, "RED", "#f44336")
        info_c = getattr(devhub, "ACCENT_GLOW", "#949cf7")
        try:
            self.text.tag_configure("lg_ok", foreground=ok_c)
            self.text.tag_configure("lg_warn", foreground=warn_c)
            self.text.tag_configure("lg_fail", foreground=fail_c)
            self.text.tag_configure("lg_info", foreground=info_c)
        except Exception:
            pass

    def _insert(self, line: str, tag: str) -> None:
        try:
            self.text.insert("end", line + "\n", (tag,))
            self.text.see("end")
        except Exception:
            pass

    def _write(self, line: str) -> None:
        tag = "lg_info"
        if "FAIL:" in line:
            tag = "lg_fail"
        elif "WARN:" in line:
            tag = "lg_warn"
        elif "OK:" in line:
            tag = "lg_ok"
        if threading.get_ident() == self._main_thread_id:
            self._insert(line, tag)
        else:
            try:
                self.text.after(0, self._insert, line, tag)
            except Exception:
                pass
        try:
            with log_path().open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def info(self, msg: str) -> None:
        self._write(f"[{_now()}] {msg}")

    def ok(self, msg: str) -> None:
        self._write(f"[{_now()}] OK: {msg}")

    def warn(self, msg: str) -> None:
        self._write(f"[{_now()}] WARN: {msg}")

    def fail(self, msg: str) -> None:
        self._write(f"[{_now()}] FAIL: {msg}")

# endregion Logging

# region GUI


class App:
    def __init__(self) -> None:
        if tk is None:
            raise RuntimeError(
                "tkinter is not available.\n\n"
                "Windows/macOS: it should be included with Python.\n"
                "Linux (Debian/Ubuntu): install it with: sudo apt-get install python3-tk"
            )
        self.root = tk.Tk()
        try:
            if devhub is not None and hasattr(devhub, "sync_tk_scaling_from_display"):
                devhub.sync_tk_scaling_from_display(self.root)
        except Exception:
            pass
        self.root.title(APP_NAME)
        self._destroying = False
        self._anim_busy = False
        self._anim_job: Optional[str] = None
        self._tagline_job: Optional[str] = None
        self._status_pulse_ok = True

        self.platform_key = detect_platform_key()

        self._bg = getattr(devhub, "BG_DEEP", "#0e0e12")
        self._bg_mid = getattr(devhub, "BG_DEEP_MID", "#12121a")
        self._card = getattr(devhub, "CARD_BG", "#1a1a22")
        self._card_border = getattr(devhub, "CARD_BORDER", "#2e3040")
        self._fg = getattr(devhub, "FG", "#e0e0e0")
        self._fg_dim = getattr(devhub, "NOTE_FG", "#b5bac1")
        self._accent = getattr(devhub, "ACCENT_PRIMARY", "#5865f2")
        self._accent_soft = getattr(devhub, "ACCENT_SOFT", "#4752c4")
        self._accent_glow = getattr(devhub, "ACCENT_GLOW", "#949cf7")
        self._accent_lo = self._accent
        self._accent_hi = self._accent_glow
        self._btn_gray = getattr(devhub, "DISCORD_SURFACE", "#2b2d31")
        self._btn_gray_hover = getattr(devhub, "DISCORD_SURFACE_HOVER", "#35373c")
        self._green = getattr(devhub, "GREEN", "#4caf50")
        self._green_hover = getattr(devhub, "GREEN_HOVER", "#66bb6a")
        self._orange = getattr(devhub, "ORANGE", "#ff9800")
        self._orange_hover = getattr(devhub, "ORANGE_HOVER", "#ffb74d")
        self._status_dim = self._fg_dim
        self._status_bright = getattr(devhub, "ONLINE_GREEN", "#23a559")

        self._font_hero = getattr(devhub, "FONT_TITLE", ("Segoe UI", 30, "bold"))
        self._font_ui = getattr(devhub, "FONT_UI", ("Segoe UI", 11))
        self._font_small = getattr(devhub, "FONT_SMALL", ("Segoe UI", 10))
        self._font_tag = getattr(devhub, "FONT_SECTION", ("Segoe UI", 11, "bold"))

        self.root.configure(bg=self._bg)
        try:
            sw = int(self.root.winfo_screenwidth())
            sh = int(self.root.winfo_screenheight())
        except Exception:
            sw, sh = 1280, 800
        w = max(620, min(int(sw * 0.44), 900))
        h = max(560, min(int(sh * 0.58), 680))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        try:
            self.root.minsize(520, 500)
            self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        except Exception:
            self.root.geometry("820x600")

        top_chrome = tk.Frame(self.root, bg=self._bg, highlightthickness=0)
        top_chrome.pack(fill="x")
        stripe_row = tk.Frame(top_chrome, bg=self._bg, highlightthickness=0)
        stripe_row.pack(fill="x")
        for col, h in ((self._accent, 2), (self._accent_soft, 2), (self._accent_glow, 2)):
            tk.Frame(stripe_row, bg=col, height=h, highlightthickness=0).pack(fill="x")

        self._accent_stripe = tk.Frame(top_chrome, bg=self._accent, height=7, highlightthickness=0)
        self._accent_stripe.pack(fill="x")

        outer = tk.Frame(self.root, bg=self._bg, highlightthickness=0)
        outer.pack(fill="both", expand=True, padx=18, pady=(16, 18))

        hero = tk.Frame(outer, bg=self._bg, highlightthickness=0)
        hero.pack(fill="x")
        self._sparkle_lbl = tk.Label(
            hero,
            text="✦",
            font=("Segoe UI", 22),
            bg=self._bg,
            fg=self._accent_glow,
            width=2,
            anchor="center",
        )
        self._sparkle_lbl.pack(side="left", padx=(0, 6))
        title_stack = tk.Frame(hero, bg=self._bg, highlightthickness=0)
        title_stack.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_stack,
            text=APP_NAME,
            font=self._font_hero,
            bg=self._bg,
            fg=self._fg,
            anchor="w",
        ).pack(anchor="w")
        badge_holder = tk.Frame(hero, bg=self._bg, highlightthickness=0)
        badge_holder.pack(side="right", padx=(12, 0))
        self._version_badge = tk.Label(
            badge_holder,
            text=" -- ",
            font=self._font_tag,
            bg=self._accent_soft,
            fg="#ffffff",
            padx=10,
            pady=4,
        )
        self._version_badge.pack(side="right")
        tk.Label(
            badge_holder,
            text="Client detected:",
            font=("Segoe UI", 9),
            bg=self._bg,
            fg=self._fg_dim,
            anchor="e",
        ).pack(side="right", padx=(0, 10))

        self._tagline_messages = (
            "Patch stereo voice in one click; revert in one click.",
            "We save a backup before you patch so you can undo safely.",
            "No terminal needed. Just use the big green button.",
        )
        self._tagline_idx = 0
        self._tagline_lbl = tk.Label(
            outer,
            text=self._tagline_messages[0],
            font=self._font_ui,
            bg=self._bg,
            fg=self._accent_glow,
            anchor="w",
            wraplength=780,
            justify="left",
        )
        self._tagline_lbl.pack(fill="x", pady=(10, 2))

        tk.Label(
            outer,
            text="This PC: %s (%s)" % (_platform_label(self.platform_key), _readable_os()),
            font=self._font_small,
            bg=self._bg,
            fg=self._fg_dim,
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        self._hub_script_status_lbl = tk.Label(
            outer,
            text="Stereo Hub · v%s · preparing update check…" % APP_VERSION,
            font=self._font_small,
            bg=self._bg,
            fg=self._accent_glow,
            anchor="w",
            wraplength=820,
            justify="left",
        )
        self._hub_script_status_lbl.pack(fill="x", pady=(0, 14))

        rim = tk.Frame(outer, bg=self._card_border, highlightthickness=0)
        rim.pack(fill="both", expand=True)
        card = tk.Frame(rim, bg=self._card, highlightthickness=0)
        card.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(
            card,
            text="Where is Discord installed on this PC?",
            font=self._font_tag,
            bg=self._card,
            fg=self._fg,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 4))

        row = tk.Frame(card, bg=self._card, highlightthickness=0)
        row.pack(fill="x", padx=16, pady=(4, 8))

        self.path_var = tk.StringVar(value="")
        try:
            self.path_var.trace_add("write", self._on_path_var_changed)
        except Exception:
            pass
        tk.Label(row, text="Discord install folder", font=self._font_ui, bg=self._card, fg=self._fg_dim).pack(
            side="left"
        )
        ent = tk.Entry(
            row,
            textvariable=self.path_var,
            bg=self._bg_mid,
            fg=self._fg,
            insertbackground=self._fg,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self._card_border,
            highlightcolor=self._accent,
        )
        ent.pack(side="left", fill="x", expand=True, padx=(10, 10), ipady=7)

        def themed_btn(parent, text, bg, hover, cmd):
            b = tk.Button(
                parent,
                text=text,
                command=cmd,
                font=self._font_ui,
                bg=bg,
                fg="#ffffff",
                activeforeground="#ffffff",
                activebackground=hover,
                relief="flat",
                bd=0,
                padx=16,
                pady=9,
                cursor="hand2",
            )
            b._base_bg = bg  # type: ignore[attr-defined]
            b._hover_bg = hover  # type: ignore[attr-defined]

            def _on(_e=None):
                try:
                    if str(b.cget("state")) == "normal":
                        b.configure(bg=hover)
                except Exception:
                    pass

            def _off(_e=None):
                try:
                    if str(b.cget("state")) == "normal":
                        b.configure(bg=b._base_bg)  # type: ignore[attr-defined]
                except Exception:
                    pass

            b.bind("<Enter>", _on)
            b.bind("<Leave>", _off)
            return b

        themed_btn(row, "Auto-detect", self._btn_gray, self._btn_gray_hover, self.on_autodetect).pack(side="left", padx=(0, 8))
        themed_btn(row, "Browse...", self._btn_gray, self._btn_gray_hover, self.on_browse).pack(side="left")

        self._last_patch_lbl = tk.Label(
            card,
            text=quick_hub_last_patch_caption(""),
            font=self._font_small,
            bg=self._card,
            fg=self._fg_dim,
            anchor="w",
            wraplength=720,
            justify="left",
        )
        self._last_patch_lbl.pack(fill="x", padx=16, pady=(0, 10))

        btns = tk.Frame(card, bg=self._card, highlightthickness=0)
        btns.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(btns, text="Actions", font=self._font_tag, bg=self._card, fg=self._fg_dim).pack(anchor="w")
        btn_row = tk.Frame(btns, bg=self._card, highlightthickness=0)
        btn_row.pack(fill="x", pady=(8, 0))

        self.btn_patch = themed_btn(btn_row, "Patch Discord voice", self._green, self._green_hover, self.on_patch)
        self.btn_patch.pack(side="left")
        self.btn_revert = themed_btn(btn_row, "Revert to backup", self._orange, self._orange_hover, self.on_revert)
        self.btn_revert.pack(side="left", padx=(14, 0))

        self.status = tk.Label(
            card,
            text="Ready when you are",
            anchor="w",
            font=self._font_small,
            bg=self._card,
            fg=self._fg_dim,
        )
        self.status.pack(fill="x", padx=16, pady=(4, 10))

        log_actions = tk.Frame(card, bg=self._card, highlightthickness=0)
        log_actions.pack(fill="x", padx=16, pady=(0, 6))
        themed_btn(log_actions, "Copy log", self._btn_gray, self._btn_gray_hover, self.on_copy_log).pack(side="left")

        log_rim = tk.Frame(card, bg=self._card_border, highlightthickness=0)
        log_rim.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        log_inner = tk.Frame(log_rim, bg=self._bg_mid, highlightthickness=0)
        log_inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.log_text = tk.Text(
            log_inner,
            height=14,
            bg=self._bg_mid,
            fg=self._fg,
            insertbackground=self._fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            font=getattr(devhub, "FONT_LOG", ("Consolas", 10)),
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.bind("<Control-a>", self._log_select_all)
        self.log_text.bind("<Control-A>", self._log_select_all)
        self.log_text.bind("<Control-c>", lambda _e: None)
        self.log_text.bind("<Control-C>", lambda _e: None)
        self.logger = Logger(self.log_text)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._fade_in()
        self._start_motion()
        self.on_autodetect()
        self._refresh_install_derived_ui()
        self.root.after(350, self._run_hub_github_self_update_thread)

    def _hub_update_defer_to_ui(self, fn) -> None:
        try:
            if self._destroying:
                fn()
                return
            self.root.after(0, fn)
        except Exception:
            try:
                fn()
            except Exception:
                pass

    def _set_hub_script_status(self, text: str) -> None:
        if self._destroying:
            return
        try:
            self._hub_script_status_lbl.configure(text=text)
            self.root.update_idletasks()
        except Exception:
            pass

    def _run_hub_github_self_update_thread(self) -> None:
        t = threading.Thread(target=self._hub_github_self_update_worker, daemon=True)
        t.start()

    def _hub_github_self_update_worker(self) -> None:
        lg = self.logger

        def defer(fn):
            self._hub_update_defer_to_ui(fn)

        skip, hub_path = _hub_self_update_skip_reason_or_ready_path()
        if skip:
            lg.warn(f"Hub self-update: skipped — {skip}.")
            short = skip if len(skip) <= 76 else skip[:73] + "…"

            defer(lambda s=short: self._set_hub_script_status(f"Stereo Hub · v{APP_VERSION} · update check skipped ({s})"))
            return

        if hub_path is None:
            lg.fail("Hub self-update: internal error — no hub script path despite checks passing.")
            return

        defer(lambda: self.set_busy(True))
        defer(lambda: self.set_status("Hub script: checking for updates…"))
        defer(lambda: self._set_hub_script_status(f"Stereo Hub · v{APP_VERSION} · checking GitHub for a newer hub…"))
        lg.info(f"Hub self-update: checking GitHub (this copy v{APP_VERSION}).")

        will_restart = False
        remote_ver = ""
        try:
            lg.info("Hub self-update: (1/4) Downloading canonical hub script from GitHub raw…")
            defer(
                lambda: self._set_hub_script_status(f"Stereo Hub · v{APP_VERSION} · (1/4) Downloading hub from GitHub…")
            )

            raw = download_bytes(HUB_SELF_UPDATE_RAW_URL, timeout_s=45)
            validate_download_payload("discord_stereo_hub.py", raw)
            if _raw_download_looks_like_error_page(raw):
                raise RuntimeError("download looks like HTML / rate-limit / error page")
            remote_src = raw.decode("utf-8", errors="replace")
            lg.ok(f"Hub self-update: (1/4) Download finished ({len(raw):,} bytes).")

            lg.info("Hub self-update: (2/4) Reading remote APP_VERSION.")
            defer(
                lambda: self._set_hub_script_status(
                    f"Stereo Hub · v{APP_VERSION} · (2/4) Parsing remote hub version…"
                )
            )
            remote_ver = _parse_app_version_from_hub_source(remote_src) or ""
            if not remote_ver:
                raise RuntimeError("could not parse APP_VERSION from GitHub hub script.")

            lg.info(f'Hub self-update: GitHub main reports Stereo Hub APP_VERSION="{remote_ver}".')

            cmp = _compare_semver_like(APP_VERSION, remote_ver)
            if cmp > 0:
                lg.info(
                    f"Hub self-update: this copy is newer than GitHub "
                    f"(local v{APP_VERSION}, GitHub v{remote_ver}); keeping local script."
                )
                defer(
                    lambda rv=remote_ver: self._set_hub_script_status(
                        f"Stereo Hub · v{APP_VERSION} · ahead of GitHub (remote v{rv}) — no update."
                    )
                )
                return
            if cmp == 0:
                lg.ok(
                    f"Hub self-update: (3/4) Versions match — your hub script is up to date (v{APP_VERSION})."
                )
                defer(
                    lambda: self._set_hub_script_status(
                        f"Stereo Hub · v{APP_VERSION} · up to date (GitHub also v{APP_VERSION})."
                    )
                )
                return

            lg.warn(
                f"Hub self-update: (3/4) Update available — GitHub v{remote_ver} is newer than local v{APP_VERSION}."
            )
            defer(
                lambda rv=remote_ver: self._set_hub_script_status(
                    f"Stereo Hub · v{APP_VERSION} → v{rv} · (4/4) Installing update…"
                )
            )

            if not _looks_like_stereo_hub_py(remote_src):
                raise RuntimeError("downloaded hub failed integrity checks")

            lg.info("Hub self-update: (4/4) Replacing discord_stereo_hub.py on disk, then restarting…")
            _atomic_replace_hub_py(hub_path, remote_src)

            lg.ok(
                f"Hub self-update: installed v{remote_ver}. Restarting this app so changes take effect…"
            )
            will_restart = True
            defer(
                lambda rv=remote_ver: self._set_hub_script_status(f"Stereo Hub · restarting · loading v{rv}…")
            )
            defer(lambda: self.set_status("Restarting Stereo Hub — loading new hub…"))

            defer(lambda p=hub_path: self._invoke_hub_restart_safe(p))

        except Exception as e:
            lg.fail(f"Hub self-update: {human_exc(e)}")
            fail_ver = remote_ver or "?"
            defer(
                lambda fv=fail_ver: self._set_hub_script_status(
                    f"Stereo Hub · v{APP_VERSION} · update check/install failed · still on v{APP_VERSION}"
                    + (f" · remote was v{fv}" if fv != "?" else "")
                )
            )

        finally:
            if not will_restart:
                defer(lambda: self.set_busy(False))
                defer(lambda: self.set_status("Ready."))

    def _invoke_hub_restart_safe(self, hub_path: Path) -> None:
        if self._destroying:
            return
        self._destroying = True
        try:
            try:
                self.root.withdraw()
                self.root.update_idletasks()
            except Exception:
                pass
            for jid in (self._anim_job, self._tagline_job):
                if jid:
                    try:
                        self.root.after_cancel(jid)
                    except Exception:
                        pass
            try:
                self.root.quit()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass
        except Exception:
            pass
        _restart_hub_program(hub_path)

    def _on_path_var_changed(self, *_args: object) -> None:
        self._refresh_install_derived_ui()

    def _refresh_install_derived_ui(self) -> None:
        root_s = self.path_var.get()
        disp = quick_hub_badge_text(root_s)
        try:
            self._version_badge.configure(text=" %s " % disp)
        except Exception:
            pass
        try:
            self._last_patch_lbl.configure(text=quick_hub_last_patch_caption(root_s))
        except Exception:
            pass

    def _on_close(self) -> None:
        self._destroying = True
        for jid in (self._anim_job, self._tagline_job):
            if jid:
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
        self._anim_job = None
        self._tagline_job = None
        try:
            self.root.destroy()
        except Exception:
            pass

    def _fade_in(self) -> None:
        try:
            self.root.attributes("-alpha", 0.0)
        except Exception:
            return

        def step(a: float) -> None:
            if self._destroying:
                return
            if a >= 1.0:
                try:
                    self.root.attributes("-alpha", 1.0)
                except Exception:
                    pass
                return
            try:
                self.root.attributes("-alpha", a)
            except Exception:
                return
            self.root.after(18, lambda: step(min(1.0, a + 0.07)))

        self.root.after(40, lambda: step(0.12))

    def _start_motion(self) -> None:
        self._sparkle_idx = 0
        self._sparkles = ("✦", "✧", "⋆", "✦")

        def tick() -> None:
            if self._destroying:
                return
            ph = time.monotonic() * 1.2
            t = (math.sin(ph) + 1.0) * 0.5
            try:
                self._accent_stripe.configure(bg=_lerp_rgb(self._accent_lo, self._accent_hi, 0.18 + 0.72 * t))
            except Exception:
                pass
            if not self._anim_busy and self._status_pulse_ok:
                try:
                    st = (math.sin(ph * 0.65) + 1.0) * 0.5
                    self.status.configure(fg=_lerp_rgb(self._status_dim, self._status_bright, 0.25 + 0.65 * st))
                except Exception:
                    pass
            try:
                self._sparkle_idx = (self._sparkle_idx + 1) % len(self._sparkles)
                self._sparkle_lbl.configure(text=self._sparkles[self._sparkle_idx])
            except Exception:
                pass
            self._anim_job = self.root.after(85, tick)

        def rotate_tagline() -> None:
            if self._destroying:
                return
            self._tagline_idx = (self._tagline_idx + 1) % len(self._tagline_messages)
            try:
                self._tagline_lbl.configure(text=self._tagline_messages[self._tagline_idx])
            except Exception:
                pass
            self._tagline_job = self.root.after(4500, rotate_tagline)

        tick()
        self._tagline_job = self.root.after(4200, rotate_tagline)

    def _log_select_all(self, _event=None):
        try:
            self.log_text.tag_add("sel", "1.0", "end-1c")
            self.log_text.mark_set("insert", "1.0")
            self.log_text.see("insert")
        except Exception:
            pass
        return "break"

    def on_copy_log(self) -> None:
        try:
            txt = self.log_text.get("1.0", "end-1c")
        except Exception:
            txt = ""
        if not txt.strip():
            if devhub is not None and hasattr(devhub, "hub_show_info"):
                try:
                    devhub.hub_show_info(self.root, "Copy log", "Log is empty.")
                    return
                except Exception:
                    pass
            try:
                messagebox.showinfo(APP_NAME, "Log is empty.")
            except Exception:
                pass
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.root.update_idletasks()
        except Exception as e:
            if devhub is not None and hasattr(devhub, "hub_show_error"):
                try:
                    devhub.hub_show_error(self.root, "Copy log failed", str(e))
                    return
                except Exception:
                    pass
            try:
                messagebox.showerror(APP_NAME, f"Copy failed:\n\n{e}")
            except Exception:
                pass
            return
        if devhub is not None and hasattr(devhub, "hub_show_info"):
            try:
                devhub.hub_show_info(self.root, "Copied", "Log copied to clipboard.")
                return
            except Exception:
                pass
        try:
            messagebox.showinfo(APP_NAME, "Log copied to clipboard.")
        except Exception:
            pass

    def set_busy(self, busy: bool) -> None:
        self._anim_busy = busy
        st = "disabled" if busy else "normal"
        for b in (self.btn_patch, self.btn_revert):
            try:
                b.configure(state=st)
                if not busy:
                    b.configure(bg=b._base_bg)  # type: ignore[attr-defined]
            except Exception:
                pass
        if busy:
            try:
                self.status.configure(fg=self._fg_dim)
            except Exception:
                pass
        self.root.update_idletasks()

    def set_status(self, msg: str) -> None:
        try:
            self.status.configure(text=msg)
            if msg.startswith("Ready"):
                self._status_pulse_ok = True
            else:
                self._status_pulse_ok = False
                self.status.configure(fg=self._fg_dim)
        except Exception:
            pass

    def on_autodetect(self) -> None:
        tgt, err = resolve_target()
        if not tgt:
            self.path_var.set("")
            self.logger.warn(err)
            self.set_status("Auto-detect failed. Try Browse.")
            return
        self.path_var.set(str(tgt.discord_root))
        self.logger.ok(f"Auto-detected voice module: {tgt.voice_dir}")
        self.set_status("Ready")

    def on_browse(self) -> None:
        start = str(Path.home())
        try:
            chosen = filedialog.askdirectory(title="Select your Discord install folder", initialdir=start)
        except Exception:
            chosen = ""
        if not chosen:
            return
        self.path_var.set(chosen)
        self.logger.info(f"Selected Discord root: {chosen}")

    def _get_target(self) -> Target:
        p = self.path_var.get().strip()
        if not p:
            tgt, err = resolve_target()
            if not tgt:
                raise RuntimeError(err)
            return tgt
        root = Path(p)
        tgt, err = resolve_target(preferred_root=root)
        if not tgt:
            raise RuntimeError(err)
        return tgt

    def on_patch(self) -> None:
        self._run_action("Patch", patch)

    def on_revert(self) -> None:
        self._run_action("Revert", revert)

    def _run_action(self, name: str, fn) -> None:
        try:
            tgt = self._get_target()
        except Exception as e:
            self.logger.fail(human_exc(e))
            self.set_status("Could not resolve Discord install.")
            return

        self.set_busy(True)
        self.set_status("Running %s..." % name)
        self.logger.info(f"=== {name} ===")
        self.logger.info(f"Discord root: {tgt.discord_root}")
        self.logger.info(f"Voice dir:    {tgt.voice_dir}")

        result_q: "queue.Queue[Optional[tuple]]" = queue.Queue()

        def _worker() -> None:
            try:
                fn(tgt, self.logger)
                result_q.put(None)
            except Exception as e:
                result_q.put((e, traceback.format_exc().strip()))

        def _poll() -> None:
            try:
                result = result_q.get_nowait()
            except queue.Empty:
                self.root.after(50, _poll)
                return
            if result is None:
                self.set_status("Ready. %s is complete." % name)
                if name == "Patch":
                    self._refresh_install_derived_ui()
            else:
                exc, tb = result
                self.logger.fail(human_exc(exc))
                self.logger.fail(tb)
                if devhub is not None and hasattr(devhub, "hub_show_error"):
                    try:
                        devhub.hub_show_error(self.root, f"{name} failed", str(exc))
                    except Exception:
                        try:
                            messagebox.showerror(APP_NAME, f"{name} failed:\n\n{exc}")
                        except Exception:
                            pass
                else:
                    try:
                        messagebox.showerror(APP_NAME, f"{name} failed:\n\n{exc}")
                    except Exception:
                        pass
                self.set_status("%s failed." % name)
            self.set_busy(False)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        self.root.after(50, _poll)

    def run(self) -> None:
        self.root.mainloop()

# endregion GUI

# region Main Entry


def main() -> int:
    if os.environ.get("DISCORD_STEREO_SELF_UPDATE_FLOW_TEST", "").strip() == "1":
        sys.stdout.write(APP_VERSION + "\n")
        try:
            sys.stdout.flush()
        except Exception:
            pass
        return 0
    try:
        safe_mkdir(hub_data_dir())
    except Exception:
        pass
    try:
        App().run()
        return 0
    except Exception as e:
        sys.stderr.write(f"{APP_NAME} failed to start: {human_exc(e)}\n")
        return 1


# endregion Main Entry

if __name__ == "__main__":
    raise SystemExit(main())
