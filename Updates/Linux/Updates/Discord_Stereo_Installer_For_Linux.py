#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Linux Stereo installer GUI: runs Stereo-Installer-Linux.sh / discord_voice_patcher_linux.sh beside this file."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

# region Paths

def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def script_dir():
    """Directory containing this script and the .sh installer/patcher."""
    return _script_dir()

def installer_script():
    """Path to Stereo-Installer-Linux.sh (same directory as this .py)."""
    return os.path.join(_script_dir(), "Stereo-Installer-Linux.sh")

def patcher_script():
    """Path to discord_voice_patcher_linux.sh (same directory as this .py)."""
    return os.path.join(_script_dir(), "discord_voice_patcher_linux.sh")

# endregion Paths


# region Platform / debug

IS_WINDOWS = sys.platform.startswith("win")
DEBUG_MODE = (
    os.environ.get("DISCORD_VOICE_FIXER_DEBUG", "").lower() in ("1", "true", "yes")
    or "--debug" in sys.argv
)

# endregion Platform / debug


def _which(cmd: str):
    return shutil.which(cmd)


def _dpi_init_before_tk():
    """Windows: per-monitor DPI aware so tk scales at 125%/150%/200%. Call before first Tk()."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _dpi_apply_after_tk(root):
    """Set tk scaling from display DPI so fonts/layout scale up/down with resolution."""
    try:
        if IS_WINDOWS:
            dpi = 96
            try:
                import ctypes
                hwnd = root.winfo_id()
                dpi = int(ctypes.windll.user32.GetDpiForWindow(hwnd))
            except Exception:
                pass
            dpi = max(72, min(384, dpi))
            root.tk.call("tk", "scaling", dpi / 72.0)
        else:
            ppi = root.winfo_fpixels("1i")
            if ppi and ppi > 0:
                root.tk.call("tk", "scaling", min(5.0, max(0.8, ppi / 72.0)))
    except Exception:
        pass


def _base_geometry():
    """Initial window size; tall enough so button row + log are never clipped."""
    return 640, 900


def _base_minsize():
    """Minimum size so all sections remain visible after DPI scaling."""
    return 600, 800


def _is_installer_script(script_path: str) -> bool:
    """True if script is Stereo-Installer-Linux.sh (which accepts --no-gui). Patcher does not."""
    return script_path is not None and "Stereo-Installer-Linux.sh" in os.path.basename(script_path)


def _wsl_bash_cmd(script_path: str, args: list[str]) -> list[str] | None:
    """If WSL is available, return argv to run script inside WSL (Windows path -> /mnt/c/...)."""
    wsl = _which("wsl.exe") or _which("wsl")
    if not wsl:
        return None
    try:
        sp = os.path.normpath(os.path.abspath(script_path))
        if len(sp) >= 2 and sp[1] == ":":
            drive = sp[0].lower()
            rest = sp[2:].replace("\\", "/")
            wsl_path = "/mnt/%s%s" % (drive, rest)
        else:
            wsl_path = sp.replace("\\", "/")
        # Only installer supports --no-gui; patcher does not
        if _is_installer_script(script_path):
            return [wsl, "bash", wsl_path, "--no-gui"] + list(args)
        return [wsl, "bash", wsl_path] + list(args)
    except Exception:
        return None


def _bash_argv(script_path: str, args: list[str]) -> tuple[list[str] | None, str]:
    """
    Return (argv, reason). argv is None if cannot run.
    On Windows without bash: try WSL; else None with reason for debug log.
    Only the installer script gets --no-gui; the patcher does not support it.
    """
    bash = _which("bash")
    if bash:
        if _is_installer_script(script_path):
            return [bash, script_path, "--no-gui"] + args, "native bash"
        return [bash, script_path] + args, "native bash"
    if IS_WINDOWS:
        wsl_cmd = _wsl_bash_cmd(script_path, args)
        if wsl_cmd:
            return wsl_cmd, "wsl"
        return None, "no bash and no wsl (use WSL or Linux to run scripts)"
    return None, "bash not in PATH"


THEME = {
    "bg": "#202225",
    "control_bg": "#2f3136",
    "primary": "#5865f2",
    "secondary": "#464950",
    "warning": "#faa81a",
    "success": "#579e57",
    "text": "#ffffff",
    "text_secondary": "#969696",
    "text_dim": "#b4b4b4",
}

FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "normal": ("Segoe UI", 9),
    "button": ("Segoe UI", 11, "bold"),
    "small": ("Segoe UI", 8),
    "console": ("Consolas", 9),
}


def _substitute_fonts():
    try:
        import tkinter.font as tkfont
        # Probe Tk must use same DPI as main window on Windows
        _dpi_init_before_tk()
        root = tk.Tk()
        root.withdraw()
        if "Segoe UI" not in tkfont.families():
            sub = "DejaVu Sans"
            for k in list(FONTS.keys()):
                v = FONTS[k]
                if isinstance(v, tuple) and v[0] == "Segoe UI":
                    FONTS[k] = (sub, v[1], *v[2:]) if len(v) > 2 else (sub, v[1])
        root.destroy()
    except Exception:
        pass


class ThemedButton(tk.Frame):
    def __init__(self, parent, text, command, bg=None, width=None):
        super().__init__(parent, bg=THEME["bg"])
        self._cmd = command
        self._bg = bg or THEME["primary"]
        self._active = self._darken(self._bg)
        self.btn = tk.Label(
            self,
            text=text,
            bg=self._bg,
            fg=THEME["text"],
            font=FONTS.get("button"),
            padx=12,
            pady=6,
            cursor="hand2",
        )
        # width in chars forces wide buttons; omit unless needed to avoid clipping whole row
        if width is not None:
            self.btn.config(width=int(width))
        self.btn.pack()
        self.btn.bind("<Button-1>", lambda e: self._cmd())
        self.btn.bind("<Enter>", lambda e: self.btn.config(bg=self._active))
        self.btn.bind("<Leave>", lambda e: self.btn.config(bg=self._bg))

    @staticmethod
    def _darken(hex_color):
        if hex_color.startswith("#") and len(hex_color) == 7:
            r = max(0, int(hex_color[1:3], 16) - 25)
            g = max(0, int(hex_color[3:5], 16) - 25)
            b = max(0, int(hex_color[5:7], 16) - 25)
            return "#%02x%02x%02x" % (r, g, b)
        return hex_color


# Single placeholder when no clients detected (keep short to avoid OptionMenu horizontal scroll)
CLIENT_PLACEHOLDER = "(No clients yet - run Check)"


class DiscordVoiceFixerGUI:
    MODE_INSTALL = "install"
    MODE_PATCH = "patch"

    def __init__(self, initial_mode=None):
        self.mode = initial_mode or self.MODE_INSTALL
        self._client_list = []
        self._wrap_labels = []

        _dpi_init_before_tk()
        self.root = tk.Tk()
        _dpi_apply_after_tk(self.root)
        title = "Discord Stereo Installer For Linux"
        if DEBUG_MODE:
            title += " [DEBUG]"
        self.root.title(title)
        self.root.configure(bg=THEME["bg"])
        w, h = _base_geometry()
        self.root.geometry("%dx%d" % (w, h))
        mw, mh = _base_minsize()
        self.root.minsize(mw, mh)
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._warn_if_scripts_missing()
        if self.mode == self.MODE_INSTALL and not (IS_WINDOWS and not _which("bash") and not _which("wsl.exe") and not _which("wsl")):
            self._refresh_clients()
        elif IS_WINDOWS and DEBUG_MODE:
            self._sanity_check_log()

    def _on_root_configure(self, event):
        """Keep label wraplength in sync with window width (DPI / resize)."""
        if event.widget is not self.root:
            return
        try:
            width = self.root.winfo_width()
            if width < 100:
                return
            wrap = max(260, width - 72)
            for lbl, pad in self._wrap_labels:
                try:
                    if lbl.winfo_exists():
                        lbl.config(wraplength=max(260, width - pad))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        if mode == self.MODE_INSTALL:
            self.client_frame.pack(fill=tk.X, padx=20, pady=4, after=self._mode_frame)
            if not (IS_WINDOWS and not _which("bash") and not _which("wsl.exe") and not _which("wsl")):
                self._refresh_clients()
        else:
            self.client_frame.pack_forget()
        self._rebuild_action_buttons()
        self._update_mode_desc()

    def _update_mode_desc(self):
        if self.mode == self.MODE_INSTALL:
            self.mode_desc.config(
                text=(
                    "Downloads pre-patched discord_voice.node from backup and installs into your Discord app.\n"
                    "Use when you want stereo without compiling. Requires network + curl/jq on Linux."
                )
            )
        else:
            self.mode_desc.config(
                text=(
                    "Patches your existing discord_voice.node in place (48 kHz / 384 kbps / stereo).\n"
                    "Requires a C++ compiler (g++ or clang). Close Discord before patching."
                )
            )

    def _build_ui(self):
        tk.Label(
            self.root,
            text="Discord Stereo Installer For Linux",
            bg=THEME["bg"],
            fg=THEME["text"],
            font=FONTS["title"],
        ).pack(pady=(14, 2))

        subtitle = "Oracle | Shaun | Hallow | Ascend | Sentry | Sikimzo | Cypher"
        if DEBUG_MODE:
            subtitle += " | DEBUG"
        tk.Label(
            self.root,
            text=subtitle,
            bg=THEME["bg"],
            fg=THEME["text_secondary"],
            font=FONTS["small"],
        ).pack()
        tk.Label(
            self.root,
            text="48 kHz | 384 kbps | Stereo",
            bg=THEME["bg"],
            fg=THEME["text_dim"],
            font=FONTS["small"],
        ).pack(pady=(0, 10))

        mode_frame = tk.LabelFrame(
            self.root,
            text=" What do you want to do? ",
            bg=THEME["bg"],
            fg=THEME["text"],
            font=FONTS["normal"],
            bd=1,
            relief=tk.GROOVE,
        )
        mode_frame.pack(fill=tk.X, padx=20, pady=4)
        self._mode_frame = mode_frame

        self.mode_var = tk.StringVar(value=self.mode)
        inner = tk.Frame(mode_frame, bg=THEME["bg"])
        inner.pack(fill=tk.X, padx=12, pady=10)

        # Short one-line hints under each radio to avoid truncation; full detail in mode_desc inside frame
        def add_mode_row(value, title, hint):
            f = tk.Frame(inner, bg=THEME["bg"])
            f.pack(fill=tk.X, pady=4)
            tk.Radiobutton(
                f,
                text=title,
                variable=self.mode_var,
                value=value,
                command=lambda v=value: self._set_mode(v),
                bg=THEME["bg"],
                fg=THEME["text"],
                selectcolor=THEME["control_bg"],
                activebackground=THEME["bg"],
                activeforeground=THEME["text"],
                font=FONTS["normal"],
            ).pack(anchor=tk.W)
            hint_lbl = tk.Label(
                f,
                text=hint,
                bg=THEME["bg"],
                fg=THEME["text_dim"],
                font=FONTS["small"],
                wraplength=520,
                justify=tk.LEFT,
                anchor=tk.W,
            )
            hint_lbl.pack(anchor=tk.W, padx=(24, 0), fill=tk.X)
            self._wrap_labels.append((hint_lbl, 72))

        add_mode_row(
            self.MODE_INSTALL,
            "Install pre-patched files",
            "Uses curl/jq. Downloads pre-patched discord_voice.node and installs it. Needs network.",
        )
        add_mode_row(
            self.MODE_PATCH,
            "Patch unpatched files",
            "Uses g++ or clang. Compiles patcher and patches your .node in place. Close Discord first.",
        )

        # Summary inside mode frame so it is not orphaned below
        desc_wrap = tk.Frame(mode_frame, bg=THEME["bg"])
        desc_wrap.pack(fill=tk.X, padx=12, pady=(0, 10))
        tk.Label(
            desc_wrap,
            text="Mode summary:",
            bg=THEME["bg"],
            fg=THEME["text_secondary"],
            font=FONTS["small"],
        ).pack(anchor=tk.W)
        self.mode_desc = tk.Label(
            desc_wrap,
            text="",
            bg=THEME["bg"],
            fg=THEME["text_dim"],
            font=FONTS["small"],
            justify=tk.LEFT,
            wraplength=520,
            anchor=tk.W,
        )
        self.mode_desc.pack(anchor=tk.W, fill=tk.X)
        self._wrap_labels.append((self.mode_desc, 48))
        self._update_mode_desc()

        self.client_frame = tk.LabelFrame(
            self.root,
            text=" Discord client (install mode) ",
            bg=THEME["bg"],
            fg=THEME["text"],
            font=FONTS["normal"],
            bd=1,
            relief=tk.GROOVE,
        )
        self.client_var = tk.StringVar(value=CLIENT_PLACEHOLDER)
        self.client_combo = tk.OptionMenu(self.client_frame, self.client_var, self.client_var.get())
        self.client_combo.config(
            bg=THEME["control_bg"],
            fg=THEME["text"],
            activebackground=THEME["secondary"],
            activeforeground=THEME["text"],
            highlightthickness=0,
        )
        self.client_combo["menu"].config(bg=THEME["control_bg"], fg=THEME["text"])
        self.client_combo.pack(fill=tk.X, padx=12, pady=10)

        if self.mode == self.MODE_INSTALL:
            self.client_frame.pack(fill=tk.X, padx=20, pady=4)
        else:
            self.client_frame.pack_forget()

        # Pack button bar at BOTTOM first so it always gets height; log fills space above.
        self.button_container = tk.Frame(self.root, bg=THEME["bg"])
        self.button_container.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(8, 12))
        self._rebuild_action_buttons()

        log_frame = tk.LabelFrame(
            self.root,
            text=" Log ",
            bg=THEME["bg"],
            fg=THEME["text"],
            font=FONTS["normal"],
            bd=1,
            relief=tk.GROOVE,
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=4)
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            log_frame,
            textvariable=self.status_var,
            bg=THEME["control_bg"],
            fg=THEME["text_dim"],
            font=FONTS["small"],
            anchor=tk.W,
        )
        status_bar.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.log = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            bg=THEME["control_bg"],
            fg=THEME["text"],
            font=FONTS["console"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        for tag, fg in [
            ("info", THEME["text_dim"]),
            ("ok", THEME["success"]),
            ("warn", THEME["warning"]),
            ("err", "#ed4245"),
        ]:
            self.log.tag_config(tag, foreground=fg)

        if IS_WINDOWS and not _which("bash"):
            self.log_line(
                "Windows: bash not in PATH. Install WSL and use: wsl bash <script>.sh --no-gui ...",
                "warn",
            )
            self.log_line("Or set DISCORD_VOICE_FIXER_DEBUG=1 (or --debug) to run sanity check only.", "info")
        else:
            self.log_line("Select a mode, then use the actions. Linux: bash required. Windows: WSL recommended.", "info")

        self._fit_window_to_content()

    def _fit_window_to_content(self):
        """Resize window to at least what the layout requests so nothing is clipped."""
        try:
            self.root.update_idletasks()
            reqw = self.root.winfo_reqwidth()
            reqh = self.root.winfo_reqheight()
            # Extra margin for title bar / borders / DPI rounding
            margin_w, margin_h = 48, 64
            w = max(_base_geometry()[0], reqw + margin_w)
            h = max(_base_geometry()[1], reqh + margin_h)
            # Cap to avoid huge window on misreported reqsize
            w = min(w, 1200)
            h = min(h, 1000)
            self.root.geometry("%dx%d" % (w, h))
            self.root.update_idletasks()
        except Exception:
            pass

    def _rebuild_action_buttons(self):
        if not getattr(self, "button_container", None):
            return
        try:
            if not self.button_container.winfo_exists():
                return
        except Exception:
            return
        for w in list(self.button_container.winfo_children()):
            w.destroy()

        # Two rows so buttons are never cut off on narrow windows
        row1 = tk.Frame(self.button_container, bg=THEME["bg"])
        row1.pack(fill=tk.X, pady=(0, 6))
        row2 = tk.Frame(self.button_container, bg=THEME["bg"])
        row2.pack(fill=tk.X)

        if self.mode == self.MODE_INSTALL:
            ThemedButton(row1, "Start Fix", self._fix_selected).pack(side=tk.LEFT, padx=3)
            ThemedButton(row1, "Fix All", self._fix_all, bg=THEME["success"]).pack(side=tk.LEFT, padx=3)
            ThemedButton(row1, "Verify", self._verify, bg=THEME["secondary"]).pack(side=tk.LEFT, padx=3)
            ThemedButton(row1, "Check", self._check, bg=THEME["warning"]).pack(side=tk.LEFT, padx=3)
            ThemedButton(row2, "Restore", self._restore, bg=THEME["secondary"]).pack(side=tk.LEFT, padx=3)
        else:
            ThemedButton(row1, "Patch all (silent)", self._patcher_silent).pack(side=tk.LEFT, padx=3)
            ThemedButton(row1, "List backups", self._patcher_list_backups, bg=THEME["secondary"]).pack(
                side=tk.LEFT, padx=3
            )
            ThemedButton(row2, "Restore", self._patcher_restore, bg=THEME["secondary"]).pack(side=tk.LEFT, padx=3)

        if DEBUG_MODE or (IS_WINDOWS and not _which("bash")):
            ThemedButton(row2, "Sanity check", self._sanity_check_log, bg=THEME["warning"]).pack(
                side=tk.LEFT, padx=3
            )

        ThemedButton(row2, "Quit", self._on_close, bg=THEME["secondary"]).pack(side=tk.RIGHT, padx=3)

    def log_line(self, line, tag="info"):
        try:
            # ASCII-safe for Windows console encoding edge cases
            if isinstance(line, str):
                line = line.encode("ascii", errors="replace").decode("ascii")
            self.log.insert(tk.END, line + "\n", tag)
            self.log.see(tk.END)
            self.root.update_idletasks()
        except Exception:
            pass

    def _sanity_check_log(self):
        """Windows debug: validate scripts and environment without running bash."""
        self.log_line("=== SANITY CHECK (debug) ===", "ok")
        self.log_line("platform: %s" % sys.platform, "info")
        self.log_line("script_dir: %s" % script_dir(), "info")
        for label, path in [
            ("installer", installer_script()),
            ("patcher", patcher_script()),
        ]:
            exists = os.path.isfile(path)
            self.log_line("%s: %s %s" % (label, "OK" if exists else "MISSING", path), "ok" if exists else "err")
            if exists:
                try:
                    sz = os.path.getsize(path)
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        first = f.readline().strip()
                    self.log_line("  size=%s first_line=%s" % (sz, first[:80]), "info")
                except Exception as ex:
                    self.log_line("  read error: %s" % ex, "err")
        self.log_line("bash: %s" % (_which("bash") or "(none)"), "info")
        self.log_line("wsl: %s" % (_which("wsl.exe") or _which("wsl") or "(none)"), "info")
        argv, reason = _bash_argv(installer_script(), ["--list-clients"])
        self.log_line("run installer via: %s" % reason, "ok" if argv else "warn")
        self.log_line("=== END SANITY CHECK ===", "ok")

    def _run_bash(self, args, cwd=None, offer_restart=False):
        if cwd is None:
            cwd = script_dir()
        script = installer_script() if self.mode == self.MODE_INSTALL else patcher_script()
        if not os.path.isfile(script):
            messagebox.showerror("Error", "Script not found:\n%s" % script)
            return

        argv, reason = _bash_argv(script, args)
        if DEBUG_MODE and argv:
            self.log_line("[DEBUG] would run: %s" % reason, "warn")
            self.log_line("[DEBUG] argv: %s" % argv, "info")
            if not messagebox.askyesno("Debug", "DEBUG_MODE set. Run for real anyway?"):
                self.log_line("[DEBUG] skipped run", "warn")
                return

        if argv is None:
            self.log_line("Cannot run: %s" % reason, "err")
            self._sanity_check_log()
            messagebox.showwarning(
                "Cannot run",
                "Bash not available. On Windows use WSL or set DISCORD_VOICE_FIXER_DEBUG=1 for sanity check only.",
            )
            return

        self.log_line("$ " + " ".join(argv), "info")
        self.status_var.set("Running...")

        def worker():
            p = None
            rc = -1
            try:
                kwargs = {
                    "cwd": cwd,
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                    "env": dict(os.environ),
                }
                if not IS_WINDOWS:
                    kwargs["text"] = True
                    kwargs["bufsize"] = 1
                else:
                    kwargs["text"] = True
                    kwargs["encoding"] = "utf-8"
                    kwargs["errors"] = "replace"
                p = subprocess.Popen(argv, **kwargs)
                stdout = p.stdout
                if stdout is not None:
                    for line in iter(stdout.readline, ""):
                        if not line:
                            break
                        line = line.rstrip()
                        tag = "info"
                        if "[OK]" in line or "OK]" in line:
                            tag = "ok"
                        elif "[X]" in line or "ERROR" in line or "failed" in line.lower():
                            tag = "err"
                        elif "[!]" in line or "WARN" in line:
                            tag = "warn"
                        self.root.after(0, lambda l=line, t=tag: self.log_line(l, t))
                rc = p.wait() if p is not None else -1
                self.root.after(
                    0,
                    lambda r=rc: self.log_line("-- exit %s --" % r, "ok" if r == 0 else "err"),
                )
            except Exception as e:
                if p is not None:
                    try:
                        p.wait(timeout=1)
                    except Exception:
                        p.kill()
                self.root.after(0, lambda: self.log_line(str(e), "err"))
                rc = -1
            # Schedule UI updates on main thread
            def on_done():
                if rc == 0:
                    self.status_var.set("Done")
                    if offer_restart:
                        self._ask_restart_discord()
                else:
                    self.status_var.set("Failed")
                    messagebox.showwarning(
                        "Operation failed",
                        "The operation failed (exit code %s).\nSee the log for details." % rc,
                    )
                self.root.after(2000, lambda: self.status_var.set("Ready"))

            self.root.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _ask_restart_discord(self):
        """Offer to start Discord after a successful fix/restore (installer has --start-discord)."""
        if not messagebox.askyesno("Restart Discord", "Operation completed successfully.\nRestart Discord now?"):
            return
        inst = installer_script()
        if not os.path.isfile(inst):
            return
        argv, _ = _bash_argv(inst, ["--start-discord"])
        if argv is None:
            messagebox.showinfo("Start Discord", "Could not run installer to start Discord.\nStart it manually.")
            return
        try:
            subprocess.Popen(argv, cwd=script_dir(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log_line("Started Discord (installer --start-discord)", "ok")
        except Exception as e:
            self.log_line("Failed to start Discord: %s" % e, "err")
            messagebox.showinfo("Start Discord", "Could not start Discord.\nStart it manually.")

    def _warn_if_scripts_missing(self):
        """Log and alert if installer or patcher script is missing (e.g. not run via launcher)."""
        inst = installer_script()
        pat = patcher_script()
        if not os.path.isfile(inst) or not os.path.isfile(pat):
            self.log_line("Scripts not found in same folder as this .py.", "warn")
            self.log_line("  Installer: %s" % inst, "info")
            self.log_line("  Patcher:   %s" % pat, "info")
            self.log_line("Run discord-stereo-launcher.sh to download and run from the correct folder.", "info")
            messagebox.showwarning(
                "Scripts missing",
                "Stereo-Installer-Linux.sh or discord_voice_patcher_linux.sh not found in:\n%s\n\n"
                "Run discord-stereo-launcher.sh (it will download and run from the correct folder)."
                % script_dir(),
            )

    def _refresh_clients(self):
        script = installer_script()
        if not os.path.isfile(script):
            self.log_line("Install mode: Stereo-Installer-Linux.sh not found. Run the launcher or place it next to this .py.", "warn")
            return
        argv, reason = _bash_argv(script, ["--list-clients"])
        if argv is None:
            self.log_line("Skip client list: %s" % reason, "warn")
            self._client_list = []
            menu = self.client_combo["menu"]
            menu.delete(0, "end")
            menu.add_command(
                label=CLIENT_PLACEHOLDER, command=lambda: self.client_var.set(CLIENT_PLACEHOLDER)
            )
            self.client_var.set(CLIENT_PLACEHOLDER)
            return
        try:
            out = subprocess.run(
                argv,
                cwd=script_dir(),
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            clients = []
            for line in out.stdout.splitlines():
                line = line.strip()
                m = re.match(r"^(\d+)\s+(.+)$", line)
                if m:
                    clients.append((int(m.group(1)), m.group(2)))
            menu = self.client_combo["menu"]
            menu.delete(0, "end")
            if not clients:
                self._client_list = []
                menu.add_command(
                    label=CLIENT_PLACEHOLDER, command=lambda: self.client_var.set(CLIENT_PLACEHOLDER)
                )
                self.client_var.set(CLIENT_PLACEHOLDER)
                self.log_line("No clients found. Open Discord and join a voice channel once.", "warn")
                return
            self._client_list = clients
            for _i, name in clients:
                menu.add_command(label=name, command=lambda n=name: self.client_var.set(n))
            self.client_var.set(clients[0][1])
        except Exception as e:
            self.log_line("Client scan failed: %s" % e, "err")
            self._client_list = []
            try:
                menu = self.client_combo["menu"]
                menu.delete(0, "end")
                menu.add_command(
                    label=CLIENT_PLACEHOLDER, command=lambda: self.client_var.set(CLIENT_PLACEHOLDER)
                )
                self.client_var.set(CLIENT_PLACEHOLDER)
            except Exception:
                pass

    def _fix_selected(self):
        if self.mode != self.MODE_INSTALL:
            return
        if self.client_var.get() == CLIENT_PLACEHOLDER:
            messagebox.showwarning("No client", "Run Check after opening Discord, or pick a client from the list.")
            return
        if not self._client_list:
            messagebox.showwarning("No client", "No Discord client found.")
            return
        name = self.client_var.get()
        if not name:
            return
        if not messagebox.askyesno("Confirm", "Fix %s?\nDiscord will be closed." % name):
            return
        self._run_bash(["--fix=" + name], offer_restart=True)

    def _fix_all(self):
        if not messagebox.askyesno("Fix all", "Fix ALL clients?\nDiscord will be closed."):
            return
        self._run_bash(["--silent"], offer_restart=True)

    def _verify(self):
        self._run_bash(["--check"])

    def _restore(self):
        if not messagebox.askyesno("Restore", "Restore original voice modules from backup?"):
            return
        self._run_bash(["--restore"], offer_restart=True)

    def _check(self):
        self._run_bash(["--check"])

    def _patcher_silent(self):
        if not messagebox.askyesno("Patch all", "Patch ALL clients silently?\nClose Discord first."):
            return
        self._run_bash(["--silent"], offer_restart=True)

    def _patcher_restore(self):
        if not messagebox.askyesno("Restore", "Run patcher restore?"):
            return
        self._run_bash(["--restore"], offer_restart=True)

    def _patcher_list_backups(self):
        self._run_bash(["--list-backups"])

    def run(self):
        self.root.mainloop()


def main():
    _dpi_init_before_tk()
    _substitute_fonts()
    initial = None
    for a in sys.argv[1:]:
        if a in ("--patcher", "-p", "patcher", "--mode=patch"):
            initial = DiscordVoiceFixerGUI.MODE_PATCH
        elif a == "--mode=install":
            initial = DiscordVoiceFixerGUI.MODE_INSTALL
    DiscordVoiceFixerGUI(initial_mode=initial).run()


if __name__ == "__main__":
    main()