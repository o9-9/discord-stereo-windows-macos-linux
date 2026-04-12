<div align="center">

# Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://codeberg.org/DiscordStereoPatcher-macOS)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

</div>

---

## 👋 Are You New Here?

**Well our goal is to give yoy better Discord voice quality with stereo, bitrate, and filterless audio - just follow the steps listed below**

| Step | Your guide |
|:---:|:---|
| **1** | **Choose your OS** in the next table — start with the path we link to. |
| **2** | **Run** the tool for that platform. Scripts **close and restart Discord** for you when they need to touch `discord_voice.node`. |
| **3** | **Hop in a voice channel** and make sure everything sounds right. |

> 🪟 **Windows:** [Voice Fixer](#windows-voice-fixer) is the easy road — pre-patched files, **no compiler.**  
> 🐧 **Linux:** start with **[`discord-stereo-launcher.sh`](#linux-launcher)** — it downloads the **installer + patcher + GUI** and you **pick a mode**. The GUI **warns that installer mode is still a placeholder**; use **patcher mode** for a working path (needs **`g++`**).  
> 🔧 **Windows (advanced):** need new offsets or full control? See **[Advanced Windows patching](#advanced-windows-patching)** — requires a **C++ compiler** (skip if Voice Fixer is enough).

---

## 🧭 Pick your platform

|  | **You want…** | **Jump to** |
|:---:|:---|:---|
| 🪟 | **Windows — easiest** | [**Voice Fixer**](#windows-voice-fixer) |
| 🐧 | **Linux — launcher** | [**Stereo launcher**](#linux-launcher) |
| 🍎 | **macOS** | [**Codeberg patcher**](#macos) |
| 🔧 | **Windows — advanced** | [**Advanced patching**](#advanced-windows-patching) |

---

## 📥 Downloads & sources

|  |  |
|:---|:---|
| 📦 **GitHub Releases** | [**Releases**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) (bundled installers) |
| 🍎 **macOS patcher** | [**Codeberg**](https://codeberg.org/DiscordStereoPatcher-macOS) |
| 🔗 **Latest scripts** | **[`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates)** on `main` (what launchers fetch) |

> **`Updates/`** is always current — handy if you run scripts straight from the repo.

---

<a id="windows-voice-fixer"></a>

## 🪟 Windows — Voice Fixer

**What it does:** drops **pre-patched** `discord_voice.node` files into your install(s), with backups. **No compiler.**

### Quick steps

1. Grab [`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Windows/Stereo%20Installer.bat) from [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows).
2. **Right-click → Run as administrator.**
3. In **DiscordVoiceFixer**, pick your client(s) and install. Discord is **closed and restarted** for you.

<details>
<summary>📝 Optional detail</summary>

The `.bat` pulls [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1) from `main`. Running as Administrator avoids permission issues under `%LOCALAPPDATA%\Discord\`.

</details>

---

<a id="linux-launcher"></a>

## 🐧 Linux — Stereo launcher

**Start here on Linux.** [`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh) downloads **`discord_voice_patcher_linux.sh`**, **`Stereo-Installer-Linux.sh`**, and **`Discord_Stereo_Installer_For_Linux.py`** into **`Linux Stereo Installer/`** next to the launcher, then opens a **GUI** where you **choose installer vs patcher mode**. The UI **warns that installer mode is still a placeholder** (pre-built bundles) — **use patcher mode** for a working path today.

### Quick steps

1. Install dependencies (Debian/Ubuntu examples):
   - **`sudo apt install g++ python3 python3-tk`** — `g++` for patcher mode, **Python 3 + tkinter** for the GUI.
2. Download **[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/discord-stereo-launcher.sh)** from [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux).
3. `chmod +x discord-stereo-launcher.sh` and run **`./discord-stereo-launcher.sh`**. When the GUI opens, choose **patcher mode** unless you are testing installer flow.

When Discord updates the voice module, run the [Offset Finder](#offset-finder) and **update offsets** in `discord_voice_patcher_linux.sh` (the launcher downloads the latest copy from `main` unless you use `--no-update`).

<details>
<summary>📝 Run the patcher script directly (no GUI)</summary>

<a id="linux-voice-patcher"></a>

Use [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) from [`Updates/Linux/Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates) if you prefer the terminal only: install **`g++`**, `chmod +x`, run **`./discord_voice_patcher_linux.sh --help`**.

</details>

---

<a id="advanced-windows-patching"></a>

## 🔧 Advanced Windows patching

**Who this is for:** you already tried **[Voice Fixer](#windows-voice-fixer)** or Discord updated and you need **custom offsets**, an **unusual install**, or you want to **edit patch behavior** yourself.

**What it does:** downloads the patcher script, **builds a small C++ tool on your PC**, then patches `discord_voice.node` in place. **You need a C++ compiler** (Visual Studio with “Desktop development with C++”, or MinGW-w64).

**How to run:**

1. Download [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) from [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) (it fetches [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) from `main`).
2. Double-click the `.BAT` or run it from a terminal and follow the prompts.

If offsets in the script don’t match your Discord build, use the [Offset Finder](#offset-finder) and update the script before patching.

---

<a id="macos"></a>

## 🍎 macOS

The macOS build lives on **Codeberg**: a **native Swift GUI** for patching and backups (Apple Silicon–friendly), plus signing and related tooling. Huge thanks to **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills / Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)**.

👉 **[Discord Stereo Patcher — macOS on Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)** (repos and docs there describe the Swift app and any optional scripts.)

---

<details>
<summary><b>📖 Mission &amp; repository layout</b></summary>

## 🎯 Mission

Enable **filterless true stereo** at **high bitrates** in Discord — with emphasis on signal integrity and real-time audio across **Windows, macOS, and Linux**.

## 🔊 What this project changes

| Area | Focus |
|------|--------|
| True stereo | Avoid mono downmix; keep two channels |
| Bitrate | Reduce encoder caps; higher Opus bitrate |
| Sample rate | Restore 48 kHz where limited |
| Filters | Bypass HP/DC paths where patched |
| Integrity | Less client-side “enhancement” on the signal |

## 📂 Repository layout

| Path | Contents |
|------|----------|
| [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) | Voice Fixer, Advanced Windows patching (`.BAT` + PS1) |
| [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux) | **[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh)** (main entry — GUI mode picker); `Updates/Linux/Updates/` — patcher + installer scripts |
| [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) | Offset finder CLI and GUI |
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | Reference nodes for patchers |

[`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump) — archived modules for research (optional for end users).

</details>

---

## ❓ FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Discord often ships a new `discord_voice.node`, which moves RVAs. Wait for updated offsets in this repo, or run the **Offset Finder** on your file, paste the new block into the patcher, and run again.

</details>

<details>
<summary><b>No C++ compiler found</b></summary>

**Voice Fixer (Windows)** does not need a compiler.

**Advanced Windows patching** and **Linux patcher mode** (`discord_voice_patcher_linux.sh`, including via the [stereo launcher](#linux-launcher)) generate and compile C++ when you run them. Install a toolchain:

**Windows:** [Visual Studio](https://visualstudio.microsoft.com/) (Desktop development with C++) or [MinGW-w64](https://www.mingw-w64.org/).

**Linux:** e.g. `sudo apt install g++` (Debian/Ubuntu), `sudo dnf install gcc-c++` (Fedora), `sudo pacman -S gcc` (Arch).

**macOS** uses the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) Swift app — see their docs for toolchain or build steps.

</details>

<details>
<summary><b>Cannot open file / permission denied</b></summary>

**Windows:** Run the patcher as **Administrator**.

**Linux:** Most installs under `~/.config/discord/` are user-writable. If not: `sudo chmod +w /path/to/discord_voice.node`

**macOS:** see the [Codeberg macOS project](https://codeberg.org/DiscordStereoPatcher-macOS) for permission and signing behavior.

</details>

<details>
<summary><b>Binary validation failed — unexpected bytes</b></summary>

The patcher checks bytes before writing. A mismatch means your `discord_voice.node` does not match the offsets in the script. Update offsets for your build or use the Offset Finder.

</details>

<details>
<summary><b>File already patched</b></summary>

The patcher saw its own bytes at a site. It may re-apply patches so everything stays consistent.

</details>

<details>
<summary><b>No Discord installation found</b></summary>

Standard paths are scanned. **Windows:** `%LOCALAPPDATA%\Discord`. **Linux:** `~/.config/discord`, `/opt/discord`, Flatpak, Snap. Custom installs may need a manual path to the `.node` file. **macOS:** handled in the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app — check their docs if Discord is not found.

</details>

<details>
<summary><b>Distorted or clipping audio</b></summary>

Gain may be too high. Stay at **1×** unless the source is very quiet; values above **3×** often clip.

</details>

<details>
<summary><b>BetterDiscord / Vencord / Equicord</b></summary>

**Yes** on Windows (auto-detected clients). The patch targets `discord_voice.node`. On Linux, standard Electron layouts work if the mod keeps the usual module paths. **macOS:** see [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS).

</details>

<details>
<summary><b>Account bans</b></summary>

This changes local encoding only. There are **no known bans** tied to this project. Editing client files may violate Discord’s terms — use at your own risk.

</details>

<details>
<summary><b>Restore / unpatch</b></summary>

**Windows:** Restore in the patcher UI, or use `-Restore` where supported.

**Linux:** `./discord_voice_patcher_linux.sh --restore`

**macOS:** use restore or backup options in the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app (this repo does not ship macOS scripts).

A Discord app update also replaces `discord_voice.node` with a fresh copy.

</details>

<details>
<summary><b>Linux: Flatpak / Snap</b></summary>

**Flatpak:** locate the node, e.g. `find ~/.var/app/com.discordapp.Discord -name "discord_voice.node"`

**Snap:** `/snap/discord/current/` is often read-only; you may need to copy the file out, patch, and copy back, or use another package format.

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

**Linux:** use the **[stereo launcher](#linux-launcher)** first — it downloads the installer + patcher and lets you pick a mode; **installer mode is still a placeholder.** Patcher mode runs `discord_voice_patcher_linux.sh`. You can also run [`discord_voice_patcher_linux.sh`](#linux-voice-patcher) alone (see collapsible under [Linux — Stereo launcher](#linux-launcher)).

</details>

---

<details>
<summary><b>🔬 Technical deep dive</b></summary>

### Architecture

The project patches `discord_voice.node` (Opus pipeline, preprocessing, WebRTC). Format depends on OS: PE (Windows), ELF (Linux), Mach-O (macOS).

```
Read offsets → generate C++ → compile → patch binary on disk
```

### Patch targets (summary)

| # | Target | Role |
|---|--------|------|
| 1–3 | Stereo / channels / mono path | Force stereo, skip mono downmix |
| 4–9 | Bitrate / 48 kHz | Raise limits, restore sample rate where patched |
| 10–13 | Filters / downmix | Replace or skip DSP as implemented |
| 14–17 | Config / errors | Validation and error paths |

Full byte-level detail varies by platform (MSVC vs Clang, register choices, etc.).

<a id="offset-finder"></a>

### Offset Finder

After Discord rebases the module, run [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) or [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py), then paste the generated offset block into the Windows / Linux patcher scripts. For **macOS**, follow the **Swift** patcher workflow on [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS).

</details>

---

<details>
<summary><b>📋 Changelog</b></summary>

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
