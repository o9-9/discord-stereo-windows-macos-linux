<div align="center">

# Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#windows-voice-fixer)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#macos)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux#linux-launcher)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

</div>

> **v1.0 is releasing soon.** We are polishing installers, launchers, and docs for a stable 1.0 line across Windows, macOS, and Linux. Until then, grab the current bundled tree as **`Updates.zip`** on [**Releases**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) (**v0.5**), which matches [`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates) on `main`.

---

## 👋 Are You New Here?

**Well our goal is to give you better Discord voice quality with stereo, bitrate, and filterless audio - just follow the steps listed below**

| Step | Your guide |
|:---:|:---|
| **1** | **Choose your OS** in the next table — start with the path we link to. |
| **2** | **Run** the tool for that platform. Scripts **close and restart Discord** for you when they need to touch `discord_voice.node`. |
| **3** | **Hop in a voice channel** and make sure everything sounds right. |

---

## 🧭 Pick your platform

|  | **You want…** | **Jump to** |
|:---:|:---|:---|
| 🪟 | **Windows — easiest** | [**Voice Fixer**](#windows-voice-fixer) |
| 🐧 | **Linux — launcher** | [**Stereo launcher**](#linux-launcher) |
| 🍎 | **macOS** | [**macOS**](#macos) |
| 🔧 | **Windows — advanced** | [**Advanced patching**](#advanced-windows-patching) |
| 🧰 | **New Discord build / bad offsets** | [**Offset Finder**](#offset-finder) |

---

## 📥 Downloads & sources

|  |  |
|:---|:---|
| 📦 **GitHub Releases** | [**Releases**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) (bundled installers) |
| 🍎 **macOS** | [**macOS**](#macos) |
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

**Start here on Linux.** [`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh) downloads **`discord_voice_patcher_linux.sh`**, **`Stereo-Installer-Linux.sh`**, and **`Discord_Stereo_Installer_For_Linux.py`** into **`Linux Stereo Installer/`** next to the launcher, then opens a **GUI** where you **choose installer vs patcher mode**. The **Installer** is a **placeholder** for now: the **current** patch is **filterless** only, **not** true **stereo** — **use patcher mode** for a working path today.

### Quick steps

1. Install dependencies (Debian/Ubuntu examples):
   - **`sudo apt install g++ python3 python3-tk`** — `g++` for patcher mode, **Python 3 + tkinter** for the GUI.
2. Download **[`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/discord-stereo-launcher.sh)** from [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux).
3. `chmod +x discord-stereo-launcher.sh` and run **`./discord-stereo-launcher.sh`**. When the GUI opens, choose **patcher mode** unless you are testing installer flow.

When Discord updates the voice module, use the [**Offset Finder**](#offset-finder) and **update offsets** in `discord_voice_patcher_linux.sh` (the launcher downloads the latest copy from `main` unless you use `--no-update`).

### Patcher only (no GUI)

<a id="linux-voice-patcher"></a>

**Terminal:** use [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) from [`Updates/Linux/Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates): install **`g++`**, `chmod +x`, then **`./discord_voice_patcher_linux.sh --help`**.

---

<a id="advanced-windows-patching"></a>

## 🔧 Advanced Windows patching

**Who this is for:** you already tried **[Voice Fixer](#windows-voice-fixer)** or Discord updated and you need **custom offsets**, an **unusual install**, or you want to **edit patch behavior** yourself.

**What it does:** downloads the patcher script, **builds a small C++ tool on your PC**, then patches `discord_voice.node` in place. **You need a C++ compiler** (Visual Studio with “Desktop development with C++”, or MinGW-w64).

**How to run:**

1. Download [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) from [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) (it fetches [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) from `main`).
2. Double-click the `.BAT` or run it from a terminal and follow the prompts.

If offsets in the script don’t match your Discord build, use the [**Offset Finder**](#offset-finder) and update the script before patching.

---

<a id="offset-finder"></a>

## 🧰 Offset Finder

When `discord_voice.node` changes, RVAs move — you need **new offsets** in the Windows / Linux patcher scripts. Run the finder on **your** module file, paste the script block it prints, then re-run the patcher.

- [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) (CLI)
- [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py) (GUI) — in [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder)

**macOS:** the Swift patcher on **Codeberg** is the usual path when the **Codeberg** service is up; with **Codeberg** down, follow migration notes under [**macOS**](#macos).

---

<a id="macos"></a>

## 🍎 macOS

**Codeberg** is **down**, so the **macOS** build is **moving** to **this GitHub repository**. It remains a **native Swift GUI** for patching and backups (Apple Silicon–friendly), plus signing and related tooling. Huge thanks to **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills / Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)**.

👉 **[Discord Stereo Patcher — macOS (Codeberg)](https://codeberg.org/DiscordStereoPatcher-macOS)** — full repo and docs when the **Codeberg** host is back.

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
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | Reference nodes for patchers |

[`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump) — archived modules for research (optional for end users).

</details>

---

## ❓ FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Discord often ships a new `discord_voice.node`, which moves RVAs. Wait for updated offsets in this repo, or run the [**Offset Finder**](#offset-finder) on your file, paste the new block into the patcher, and run again.

</details>

<details>
<summary><b>No C++ compiler found</b></summary>

**Voice Fixer (Windows)** does not need a compiler.

**Advanced Windows patching** and **Linux patcher mode** (`discord_voice_patcher_linux.sh`, including via the [stereo launcher](#linux-launcher)) generate and compile C++ when you run them. Install a toolchain:

**Windows:** [Visual Studio](https://visualstudio.microsoft.com/) (Desktop development with C++) or [MinGW-w64](https://www.mingw-w64.org/).

**Linux:** e.g. `sudo apt install g++` (Debian/Ubuntu), `sudo dnf install gcc-c++` (Fedora), `sudo pacman -S gcc` (Arch).

**macOS (Swift app):** see [**macOS**](#macos). Tooling was on [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) while the host is up; **Codeberg** has been down — the build is **moving to this repository** (no macOS tree here yet; follow that section and any pinned issue).

</details>

<details>
<summary><b>Cannot open file / permission denied</b></summary>

**Windows:** Run the patcher as **Administrator**.

**Linux:** Most installs under `~/.config/discord/` are user-writable. If not: `sudo chmod +w /path/to/discord_voice.node`

**macOS:** signing and file access match the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app notes when the host is online; for current guidance while **Codeberg** is down, see [**macOS**](#macos).

</details>

<details>
<summary><b>Binary validation failed — unexpected bytes</b></summary>

The patcher checks bytes before writing. A mismatch means your `discord_voice.node` does not match the offsets in the script. Update offsets for your build (see the [**Offset Finder**](#offset-finder) section).

</details>

<details>
<summary><b>File already patched</b></summary>

The patcher saw its own bytes at a site. It may re-apply patches so everything stays consistent.

</details>

<details>
<summary><b>No Discord installation found</b></summary>

Standard paths are scanned. **Windows:** `%LOCALAPPDATA%\Discord`. **Linux:** `~/.config/discord`, `/opt/discord`, Flatpak, Snap. Custom installs may need a manual path to the `.node` file. **macOS:** the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app walks installs when the host is up; if the site is down or the app is not installed, see [**macOS**](#macos).

</details>

<details>
<summary><b>Distorted or clipping audio</b></summary>

Gain may be too high. Stay at **1×** unless the source is very quiet; values above **3×** often clip.

</details>

<details>
<summary><b>BetterDiscord / Vencord / Equicord</b></summary>

**Yes** on Windows (auto-detected clients). The patch targets `discord_voice.node`. On Linux, standard Electron layouts work if the mod keeps the usual module paths. **macOS:** [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) when online; else [**macOS**](#macos) above.

</details>

<details>
<summary><b>Account bans</b></summary>

This changes local encoding only. There are **no known bans** tied to this project. Editing client files may violate Discord’s terms — use at your own risk.

</details>

<details>
<summary><b>Restore / unpatch</b></summary>

**Windows:** Restore in the patcher UI, or use `-Restore` where supported.

**Linux:** `./discord_voice_patcher_linux.sh --restore`

**macOS:** restore/backup in the [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) app if you have a build; **this repo** does not ship a macOS patcher on disk — see [**macOS**](#macos) and **Codeberg** status.

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

**Linux:** use the **[stereo launcher](#linux-launcher)** first — it downloads the installer + patcher and lets you pick a mode; **the Installer** is a **placeholder**; the **current** patcher path is **filterless** only, **not** true **stereo**. Patcher mode runs `discord_voice_patcher_linux.sh`. You can also use **[`discord_voice_patcher_linux.sh` only](#linux-voice-patcher)** (terminal) under the same [Linux — Stereo launcher](#linux-launcher) section.

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

### Patching workflow

Read offsets (see the [**Offset Finder**](#offset-finder) section above) → generate C++ → compile → write patches into `discord_voice.node` on disk. **macOS** Swift workflow is on **Codeberg** when that host is up.

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
