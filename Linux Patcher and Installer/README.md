# 🐧 Linux Patcher & Installer

**True stereo and high-bitrate voice for Discord on Linux**

[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux)
[![Focus](https://img.shields.io/badge/Focus-True%20Stereo%20Voice-5865F2?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux)

Part of the [Discord Stereo project](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux) — **48 kHz**, **up to 400 kbps**, and **true stereo** on Linux.

---

## 🚀 Quick start: use the launcher

**Recommended:** run the launcher once. It fetches the latest installer and patcher files, then opens the GUI.

```bash
chmod +x discord-stereo-launcher.sh
./discord-stereo-launcher.sh
```

The launcher:

- Creates a **Linux Stereo Installer** folder next to itself (if needed)
- Downloads or updates three files from the repo: Python GUI, installer script, and patcher script
- Runs the Python GUI from that folder

**Options:**

| Option | Effect |
|--------|--------|
| `--no-update` / `-n` | Skip download; run existing files only |
| `--force` / `-f` | Force redownload and overwrite all three files |
| `--help` / `-h` | Show launcher usage |

Without internet, the launcher skips updates and runs whatever is already in **Linux Stereo Installer** (if present).

---

## 📦 What’s in this repo

| File / folder | Purpose |
|---------------|--------|
| **`discord-stereo-launcher.sh`** | Single entry point: updates files, then runs the GUI |
| **`Linux Stereo Installer/`** | Created by the launcher; contains the three files below |
| **`Discord_Stereo_Installer_For_Linux.py`** | Tkinter GUI: install pre-patched module or patch locally, restore backups |
| **`Stereo-Installer-Linux.sh`** | Backend: download pre-patched `discord_voice.node`, backups, verify |
| **`discord_voice_patcher_linux.sh`** | Backend: compile and patch `discord_voice.node` in place |

The Python script uses the two `.sh` scripts from the same directory (no embedding). The launcher keeps all three in sync from the [Updates](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Linux%20Patcher%20and%20Installer/Updates) URLs.

---

## 🎯 What this does

| Before | After |
|--------|--------|
| 24 kHz | **48 kHz** |
| ~64 kbps | **up to 400 kbps** |
| Mono downmix | **True stereo** |
| Built-in filtering | **Filterless passthrough** |

---

## 🖥️ Supported install types

| Install type | Typical path |
|--------------|--------------|
| **Deb / native** | `~/.config/discord/`, `~/.config/discordcanary/`, `~/.config/discordptb/` |
| **Flatpak** | `~/.var/app/com.discordapp.Discord/...` |
| **Snap** | Often read-only; deb or Flatpak recommended for patching |

The scripts auto-detect Stable, Canary, and PTB in these locations.

---

## ⚙️ Requirements

- **Bash** (launcher and scripts)
- **Python 3** with **tkinter** (e.g. `python3-tk` on Debian/Ubuntu)
- **curl** (used by the launcher and installer for downloads)

**Install mode (pre-patched download):** **jq** (installer uses GitHub API).

**Patch mode (compile and patch in place):** **C++ compiler** (`g++` or `clang++`).

```bash
# Ubuntu/Debian
sudo apt install g++ python3-tk curl jq

# Fedora/RHEL
sudo dnf install gcc-c++ python3-tkinter curl jq

# Arch
sudo pacman -S gcc tk curl jq
```

---

## 🚀 Usage

### Run via launcher (recommended)

```bash
./discord-stereo-launcher.sh
```

In the GUI you can:

- **Install pre-patched files** — download pre-patched `discord_voice.node` and install (needs network, curl, jq).
- **Patch in place** — build the patcher and patch your local `.node` (needs g++/clang; close Discord first).
- **Restore** — revert to a backup.
- **Check** — refresh the client list (e.g. after opening Discord or joining voice).

### Run GUI only (no launcher)

If you already have **Linux Stereo Installer** with the three files:

```bash
cd "Linux Stereo Installer"
python3 Discord_Stereo_Installer_For_Linux.py
```

### Launcher and script options

**Launcher** (`discord-stereo-launcher.sh`): `--no-update`, `--force`, `--help`.

**Python GUI**: `--debug`, `--patcher` / `--mode=patch`, `--mode=install` (if supported).

**Backend scripts** (for advanced use, run from **Linux Stereo Installer**):

```bash
./Stereo-Installer-Linux.sh --help
./discord_voice_patcher_linux.sh --help
```

---

## ❓ FAQ

<details>
<summary><b>Discord updated and patching stopped working</b></summary>

Offsets are tied to a specific `discord_voice.node` build. After a Discord update, you need updated offsets. Check the repo for new patcher/installer versions and run the launcher (without `--no-update`) to pull the latest files.
</details>

<details>
<summary><b>"No C++ compiler found" (patch mode)</b></summary>

Patch mode compiles a small C++ helper at runtime. Install g++/clang++ (see Requirements), or use **Install pre-patched files** in the GUI if your Discord build is supported.
</details>

<details>
<summary><b>"Cannot open file" / Permission denied</b></summary>

The patcher needs write access to `discord_voice.node`. For installs under `~/.config/` this is usually fine. If not: `chmod +w /path/to/discord_voice.node`. Use sudo only if you understand the implications.
</details>

<details>
<summary><b>"Binary validation failed — unexpected bytes at patch sites"</b></summary>

The binary does not match the offsets in the current patcher (different Discord build). Run the launcher without `--no-update` to get the latest patcher, or use installer mode if a pre-patched module exists for your version.
</details>

<details>
<summary><b>No Discord installations found</b></summary>

Run Discord at least once so the voice module exists. Join a voice channel briefly if the module path is missing. Use **Check** in the GUI to rescan.
</details>

<details>
<summary><b>Flatpak / Snap permission issues</b></summary>

**Flatpak:** Paths under `~/.var/app/` are usually writable. **Snap:** Often read-only — prefer deb or Flatpak for patching.
</details>

<details>
<summary><b>How do I restore / unpatch?</b></summary>

Use **Restore** in the GUI, or run the installer/patcher with `--restore`. Letting Discord update also replaces the voice module with a fresh copy.
</details>

<details>
<summary><b>Launcher fails to download or says file not found</b></summary>

You need network access and `curl`. If downloads fail, the launcher will warn and still try to run existing files in **Linux Stereo Installer**. Use `--force` to retry overwriting, or run with `--no-update` to skip updates. Ensure the repo URLs are reachable (no firewall blocking raw GitHub).
</details>

---

## 🔗 Links

- [Main repo](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux) — Windows/macOS/Linux, offsets, releases
- [Voice Playground](https://discord-voice.xyz/)

---

**Disclaimer:** Provided as-is for research and experimentation. Use at your own risk. Not affiliated with Discord Inc.
