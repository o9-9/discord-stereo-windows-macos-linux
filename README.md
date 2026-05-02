<div align="center">

# Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#windows-voice-fixer)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#macos)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#linux-launcher)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

</div>

<a id="stereo-hub"></a>

## 📢 Stereo Hub v1.0

**Stereo Hub** is **[released as v1.0](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v1.0)**. Download **`Stereo_Hub.py`** from that release and run it with **Python 3** — that is the supported path for everyone now. **Codeberg** (macOS) is still down — [**macOS**](#macos).

---

## 📷 Before & after

| Before | After |
|:------:|:-----:|
| [![Before](https://i.ibb.co/j9x89156/before.png)](https://ibb.co/XfdWfv42) | [![After](https://i.ibb.co/WvqZ9n22/after.png)](https://ibb.co/jkBmKhrr) |
| *Original Discord Audio* | *99.9% Filterless Audio* |

---

<details>
<summary><b>Advanced / legacy patch methods</b></summary>

<a id="advanced-legacy-patch-methods"></a>

> Older flow: **v0.5** [`Updates.zip`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v0.5) and the full [`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates) tree on `main` still exist if you need scripts or bundles outside Stereo Hub.

## 👋 Are You New Here?

**pick a platform, run the tool, then test in a voice channel** 
(scripts may restart Discord when they patch `discord_voice.node`).

| Step | Your guide |
|:---:|:---|
| **1** | Choose your **OS** (table below). |
| **2** | **Run** the linked tool. |
| **3** | Join a channel and check audio. |

---

## 🧭 Pick your platform

|  | **You want…** | **Jump to** |
|:---:|:---|:---|
| 🪟 | **Windows — easiest** | [**Stereo Installer**](#windows-voice-fixer) |
| 🐧 | **Linux — launcher** | [**Stereo launcher**](#linux-launcher) |
| 🍎 | **macOS** | [**macOS**](#macos) |
| 🔧 | **Windows — advanced** | [**Advanced patching**](#advanced-windows-patching) |
| 🧰 | **New Discord build / bad offsets** | [**Offset Finder**](#offset-finder) |

---

## 📥 Downloads & sources

|  |  |
|:---|:---|
| 📦 **GitHub Releases** | [**Releases**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) (Stereo Hub **v1.0** + older bundles) |
| 🍎 **macOS** | [**macOS**](#macos) |
| 🔗 **Latest scripts** | **[`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates)** on `main` |

</details>

---

<a id="windows-voice-fixer"></a>

## 🪟 Windows — Stereo Installer

Drops pre-patched `discord_voice.node` (with backup). **No compiler.**

### Quick steps

1. Grab [`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Windows/Stereo%20Installer.bat) from [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows).
2. **Right-click → Run as administrator.**
3. In **DiscordVoiceFixer**, pick clients; Discord is restarted for you.

<details>
<summary>📝 Optional detail</summary>

The `.bat` fetches [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1) from `main`. Admin avoids permission issues under `%LOCALAPPDATA%\Discord\`.

</details>

---

<a id="linux-launcher"></a>

## 🐧 Linux — Stereo launcher

[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh) fetches the patcher, installer, and `Discord_Stereo_Installer_For_Linux.py` into **`Linux Stereo Installer/`** and opens a **GUI** (installer vs patcher). **Installer** = **placeholder**; for now the patcher path is **filterless** only, **not** true **stereo** — **use patcher mode.**

### Quick steps

1. Install dependencies (Debian/Ubuntu examples):
   - `sudo apt install g++ python3 python3-tk` (C++ for patcher, tk for GUI)
2. Download **[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/discord-stereo-launcher.sh)** from [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux).
3. `chmod +x` and `./discord-stereo-launcher.sh` → **patcher mode** (test installer if you need).

### Patcher only (no GUI)

<a id="linux-voice-patcher"></a>

**CLI:** [`Updates/Linux/Updates/discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) — `g++`, `chmod +x`, `./discord_voice_patcher_linux.sh --help`

---

<a id="advanced-windows-patching"></a>

## 🔧 Advanced Windows patching

For when **[Voice Fixer](#windows-voice-fixer)** is not enough: custom offsets, odd installs, or you want to change patch behavior. Downloads the script, **compiles a small C++ tool**, patches `discord_voice.node` in place. **Requires a C++ compiler** (VS with “Desktop development with C++”, or MinGW-w64).

Run [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) (pulls [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) from `main`). Bad match? [**Offset Finder**](#offset-finder) → **copy** block → **paste** into offsets in `Discord_voice_node_patcher.ps1` → re-run.

---

<a id="offset-finder"></a>

## 🧰 Offset Finder

Point the **Offset Finder** at **your** `discord_voice.node` → **copy the block** it prints → **paste the offsets** into the **offsets** section in your patcher script: **`Discord_voice_node_patcher.ps1`** (Windows) or **`discord_voice_patcher_linux.sh`** (Linux), then re-run the patcher.  
Scripts: [CLI `discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) · [GUI `offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py) in [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) · **macOS (Swift):** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) if up, else [**macOS**](#macos).

---

<a id="macos"></a>

## 🍎 macOS

**Codeberg** is **still down**; the **macOS** build is **moving** here. When it’s up: **Swift GUI** (patch, backup, Apple Silicon, signing) — [repo](https://codeberg.org/DiscordStereoPatcher-macOS) · thanks **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills / Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)**.

---

<details>
<summary><b>📖 Mission &amp; repository layout</b></summary>

## 🎯 Mission

Enable **filterless true stereo** at **high bitrates** in Discord — with emphasis on signal integrity and real-time audio across **Windows, macOS, and Linux**.

## 🔊 What this project changes

| Area | Focus |
|------|--------|
| True stereo | Avoid mono downmix; keep two channels |
| Bitrate | Work around / raise encoder Opus limits where patched |
| Sample rate | Restore 48 kHz where limited |
| Filters | Bypass HP/DC paths where patched |
| Integrity | Less client-side “enhancement” on the signal |

## 📂 Repository layout

| Path | Contents |
|------|----------|
| [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) | Voice Fixer, Advanced Windows patching (`.BAT` + PS1) |
| [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux) | **[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh)** (main entry — GUI mode picker); `Updates/Linux/Updates/` — patcher + installer scripts |
| [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) | Offset finder CLI and GUI |
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | `Unpatched` / `Patched` reference voice bundles (see subfolders) |
| — | **macOS (Swift):** not in `Updates/` here — [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) · [**macOS**](#macos) |

[`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump) (repo root) — research / archives

</details>

---

## ❓ FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

New `discord_voice.node` → new RVAs. Wait for a repo update, or [**Offset Finder**](#offset-finder) → **copy** block → **paste** offsets into the **offsets** section of the **Windows** / **Linux** patcher script, then re-run.

</details>

<details>
<summary><b>No C++ compiler found</b></summary>

**Voice Fixer** — no compiler. **[Advanced Windows](#advanced-windows-patching)** and **Linux** `discord_voice_patcher_linux.sh` (also via [stereo launcher](#linux-launcher)) build C++ at run time. **Windows:** [Visual Studio](https://visualstudio.microsoft.com/) (Desktop dev + C++) or [MinGW-w64](https://www.mingw-w64.org/). **Linux:** `sudo apt install g++` (Debian/Ubuntu) / `sudo dnf install gcc-c++` (Fedora) / `sudo pacman -S gcc` (Arch). **macOS:** [**macOS**](#macos); Swift app was on [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) (down), moving here.

</details>

<details>
<summary><b>Cannot open file / permission denied</b></summary>

**Windows:** Run the patcher as **Administrator**.

**Linux:** Most installs under `~/.config/discord/` are user-writable. If not: `sudo chmod +w /path/to/discord_voice.node`

**macOS:** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) docs if up, else [**macOS**](#macos).

</details>

<details>
<summary><b>Binary validation failed — unexpected bytes</b></summary>

`discord_voice.node` does not match the script. [**Offset Finder**](#offset-finder) → **copy** block **→ paste** into the patcher’s **offsets** section, or use an updated script from the repo.

</details>

<details>
<summary><b>File already patched</b></summary>

Patcher re-applies to keep its sites consistent; safe to run again.

</details>

<details>
<summary><b>No Discord installation found</b></summary>

**Windows** `%LOCALAPPDATA%\Discord` · **Linux** `~/.config/discord`, `/opt`, Flatpak, Snap (patcher also scans more). **macOS:** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app or [**macOS**](#macos).

</details>

<details>
<summary><b>Distorted or clipping audio</b></summary>

Gain may be too high. Stay at **1×** unless the source is very quiet; values above **3×** often clip.

</details>

<details>
<summary><b>BetterDiscord / Vencord / Equicord</b></summary>

**Yes** (Windows auto-detect). Targets `discord_voice.node`; Linux: usual Electron tree if the mod does not move modules. **macOS:** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) / [**macOS**](#macos).

</details>

<details>
<summary><b>Account bans</b></summary>

This changes local encoding only. There are **no known bans** tied to this project. Editing client files may violate Discord’s terms — use at your own risk.

</details>

<details>
<summary><b>Restore / unpatch</b></summary>

**Windows:** Restore in the patcher UI, or use `-Restore` where supported.

**Linux:** `./discord_voice_patcher_linux.sh --restore`

**macOS:** restore/backup in [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app if you have it. No macOS patcher in this repo — [**macOS**](#macos).

A Discord app update also replaces `discord_voice.node` with a fresh copy.

</details>

<details>
<summary><b>Linux: Flatpak / Snap</b></summary>

**Flatpak:** e.g. `find ~/.var/app/... -name "discord_voice.node"`. Patcher also checks **Equicord** / other ids under `~/.var/app/`. **Snap:** may be read-only — copy `discord_voice.node` out, patch, copy back, or use deb/rpm/Flatpak.

</details>

<details>
<summary><b>Does the other person need the patch?</b></summary>

**No.** Only your client encoding changes; receivers get a normal Opus stream.

</details>

<details>
<summary><b>Others cannot hear me</b></summary>

Some **VPNs** break voice UDP. Disconnect the VPN and test again; try another server or protocol if needed.

</details>

<details>
<summary><b>Voice Fixer vs Advanced Windows patching</b></summary>

**Voice Fixer** ([`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo%20Installer.bat) → [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1)) installs **pre-patched** `discord_voice.node` files. **No compiler.**

**Advanced Windows patching** ([`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) → [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1)) builds the patcher on your machine and edits the binary. **Needs a C++ compiler.** Use when Voice Fixer isn’t enough — new Discord build, custom offsets, or you want full control.

**Linux:** [stereo launcher](#linux-launcher) → **patcher** (installer = placeholder; patch = **filterless** only, not true **stereo**). Or [CLI `discord_voice_patcher_linux.sh`](#linux-voice-patcher).

</details>

---

<details>
<summary><b>🔬 Technical deep dive</b></summary>

### Architecture

Patches `discord_voice.node` (PE / ELF / Mach-O).

`offsets → C++ build → write binary`

### Patch targets (summary)

| # | Target | Role |
|---|--------|------|
| 1–3 | Stereo / channels / mono path | Force stereo, skip mono downmix |
| 4–9 | Bitrate / 48 kHz | Raise limits, restore sample rate where patched |
| 10–13 | Filters / downmix | Replace or skip DSP as implemented |
| 14–17 | Config / errors | Validation and error paths |

MSVC / Clang and register choices differ per build.

**Workflow:** [**Offset Finder**](#offset-finder) (copy **offset block** into patcher) → C++ build → write `discord_voice.node`. **macOS (Swift):** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) if up, else [**macOS**](#macos).

</details>

---

<details>
<summary><b>📋 Changelog</b></summary>

### `main` (now)
**Stereo Hub v1.0** on [Releases](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v1.0) (`Stereo_Hub.py`). Legacy **v0.5** bundle still on [v0.5](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v0.5). **Codeberg** (macOS) down → [**macOS**](#macos)

### Repo layout (Mar 2026)
- Shipping assets under `Updates/`; `Voice Node Dump/` for archives

### v6.0 (Feb 2026)
- macOS **Swift** GUI on Codeberg; Linux bash patcher; platform-specific bytes; mmap I/O on Unix

### v5.0 (Feb 2026)
- Multi-client GUI, backups, auto-update hooks

### v4.0–v1.0
- Encoder init patches, stereo pipeline, early patcher and PoC

</details>

---

## 🤝 Partners

[Shaun (sh6un)](https://github.com/sh6un) · [UnpackedX](https://codeberg.org/UnpackedX) · [Voice Playground](https://discord-voice.xyz/) · [Oracle](https://github.com/oracle-dsc) · [Loof-sys](https://github.com/LOOF-sys) · [Hallow](https://github.com/ProdHallow) · [Ascend](https://github.com/bloodybapestas) · BluesCat · [Sentry](https://github.com/sentry1000) · [Sikimzo](https://github.com/sikimzo) · [CRÜE](https://codeberg.org/DiscordStereoPatcher-macOS) · [HorrorPills / Geeko](https://github.com/HorrorPills)

---

## 💬 Get involved

**[Report an issue](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/issues)** · **[Join the Discord](https://discord.gg/gDY6F8RAfM)**

---

> ⚠️ **Disclaimer:** Provided as-is for research and experimentation. Not affiliated with Discord Inc. Use at your own risk.
