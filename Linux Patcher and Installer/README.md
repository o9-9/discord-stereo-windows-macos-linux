# 🐧 Linux Patcher & Installer

**True stereo and high-bitrate voice for Discord on Linux**

![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)
![Focus](https://img.shields.io/badge/Focus-True%20Stereo%20Voice-5865F2?style=flat-square)

Part of the [Discord Audio Collective](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux) — unlocking **48 kHz**, **384 kbps**, and **true stereo** on Linux.

---

## 📦 What’s in this repo

This folder is published with **one file**:

| File | Purpose |
|------|---------|
| **`Discord_Stereo_Installer_For_Linux.py`** | Standalone GUI + embedded installer & patcher |

The `.py` file **embeds** the full `Stereo-Installer-Linux.sh` and `discord_voice_patcher_linux.sh` payloads. On first run it extracts them to:

`~/.cache/DiscordVoiceFixerStandalone/`

You do **not** need separate `.sh` files in the repo — everything is inside the single script.

---

## 🎯 What This Does

| Before | After |
|:------:|:-----:|
| 24 kHz | **48 kHz** |
| ~64 kbps | **384 kbps** |
| Mono downmix | **True Stereo** |
| Aggressive filtering | **Filterless passthrough** |

---

## 🖥️ Supported Install Types

| Install type | Path (typical) |
|--------------|----------------|
| **Deb / native** | `~/.config/discord/`, `~/.config/discordcanary/`, `~/.config/discordptb/` |
| **Flatpak** | `~/.var/app/com.discordapp.Discord/config/discord/` |
| **Snap** | May be read-only; deb or Flatpak recommended for patching |

The embedded scripts auto-detect Discord Stable, Canary, and PTB in these locations.

---

## ⚙️ Requirements

- **Python 3** with **tkinter** (usually `python3-tk` on Debian/Ubuntu)
- **Bash** (scripts re-exec as bash if needed)

**Install mode (pre-patched download)** — no compiler:

- **curl**, **jq** (installer uses the GitHub API)

**Patch mode (compile & patch in place)**:

- **C++ compiler:** `g++` or `clang++`

  ```bash
  # Ubuntu/Debian
  sudo apt install g++ python3-tk

  # Fedora/RHEL
  sudo dnf install gcc-c++ python3-tkinter

  # Arch
  sudo pacman -S gcc tk
  ```

---

## 🚀 Usage

### Run the GUI (recommended)

```bash
chmod +x Discord_Stereo_Installer_For_Linux.py   # optional
python3 Discord_Stereo_Installer_For_Linux.py
```

In the app:

- **Install pre-patched files** — downloads pre-patched `discord_voice.node` from backup and installs (needs network + curl/jq).
- **Patch unpatched files** — compiles the patcher and patches your local `.node` (needs g++/clang; close Discord first).

Use **Check** to refresh the client list after opening Discord (and joining a voice channel once if needed). **Restore** reverts from backup.

### CLI / headless

After the first run, the extracted scripts live under `~/.cache/DiscordVoiceFixerStandalone/`. Advanced users can run them directly, e.g.:

```bash
bash ~/.cache/DiscordVoiceFixerStandalone/Stereo-Installer-Linux.sh --help
bash ~/.cache/DiscordVoiceFixerStandalone/discord_voice_patcher_linux.sh --help
```

Re-running the **`.py`** is enough for most people — it always uses the embedded copies and refreshes the cache if the payload changes.

### Optional arguments

| Argument | Effect |
|----------|--------|
| `--debug` | Debug / sanity check (useful on Windows without bash) |
| `--patcher` / `--mode=patch` | Start in patch mode instead of install mode |
| `--mode=install` | Start in install mode |

---

## ❓ FAQ

<details>
<summary><b>Discord updated and patching stopped working</b></summary>

Offsets are tied to a specific `discord_voice.node` build. When Discord updates, you need new offsets. Run the [offset finder](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux) on the new binary, update the patcher script, then rebuild the standalone (or replace the embedded payload if you maintain a fork).
</details>

<details>
<summary><b>"No C++ compiler found" (patch mode)</b></summary>

Patch mode compiles a small C++ binary at runtime. Install a compiler (see Requirements), or use **Install pre-patched files** if your build is supported by the backup.
</details>

<details>
<summary><b>"Cannot open file" / Permission denied</b></summary>

The patcher needs write access to `discord_voice.node`. For user installs under `~/.config/` this is usually fine. If not:

```bash
chmod +w /path/to/discord_voice.node
```

Use sudo only if you understand the implications.
</details>

<details>
<summary><b>"Binary validation failed — unexpected bytes at patch sites"</b></summary>

The binary doesn’t match the offsets in the embedded patcher (different Discord build). Update offsets via the [offset finder](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux), or use installer mode if a pre-patched module exists for your version.
</details>

<details>
<summary><b>No Discord installations found</b></summary>

Run Discord at least once so the voice module is downloaded. Join a voice channel briefly if the module folder is missing. Then use **Check** in the GUI to rescan.
</details>

<details>
<summary><b>Flatpak / Snap permission issues</b></summary>

**Flatpak:** Paths under `~/.var/app/` are usually writable.

**Snap:** Often read-only — prefer deb or Flatpak for patching.
</details>

<details>
<summary><b>How do I restore / unpatch?</b></summary>

Use **Restore** in the GUI, or run the extracted installer/patcher with `--restore` (see CLI section above). Letting Discord update also replaces the voice module with a fresh copy.
</details>

<details>
<summary><b>Why only one file in the repo?</b></summary>

A single **`.py`** is easier to download and run, avoids “which script do I use?”, and keeps installer + patcher versions in lockstep. The same logic still runs underneath — it’s just embedded and launched through Python/tkinter.
</details>

---

## 🔗 Links

- **[Main repo](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux)** — Offset finder, Windows/macOS/Linux assets
- **[Voice Playground](https://discord-voice.xyz/)**

---

> ⚠️ **Disclaimer:** Provided as-is for research and experimentation. Use at your own risk. Not affiliated with Discord Inc.
