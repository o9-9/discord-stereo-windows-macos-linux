<div align="center">

# Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://codeberg.org/DiscordStereoPatcher-macOS)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

</div>

---

## Start here

| Step | Action |
|:---:|:---|
| **1** | Pick your OS in the table below. |
| **2** | Run the tool for your platform (see [Windows](#windows-voice-fixer) or [Linux](#linux-voice-patcher)). Scripts close and restart Discord when needed. |
| **3** | Join a voice channel and verify audio. |

**Windows:** [Voice Fixer](#windows-voice-fixer) — pre-patched modules, no compiler.

**Linux:** [`discord_voice_patcher_linux.sh`](#linux-voice-patcher) — needs `g++`. The Linux Stereo Installer (pre-built bundles) is a placeholder and not supported yet.

---

## Choose your platform

|  | Link |
|:---:|:---|
| Windows | [Voice Fixer](#windows-voice-fixer) |
| Linux | [Voice patcher](#linux-voice-patcher) |
| macOS | [Codeberg](#macos) |

---

## Downloads

|  |  |
|:---|:---|
| Releases | [GitHub Releases](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) |
| macOS patcher | [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) |
| Latest scripts | [`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates) on `main` |

---

<a id="windows-voice-fixer"></a>

## Windows — Voice Fixer

Installs pre-patched `discord_voice.node` files with backups. No compiler.

1. Download [`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Windows/Stereo%20Installer.bat) from [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows).
2. Right-click → **Run as administrator**.
3. In DiscordVoiceFixer, select clients and install. Discord is closed and restarted for you.

<details>
<summary>More detail</summary>

The batch file downloads [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1) from `main`. Run as Administrator so `%LOCALAPPDATA%\Discord\` can be updated.

</details>

---

<a id="linux-voice-patcher"></a>

## Linux — Voice patcher

Compiles a small patcher and patches `discord_voice.node` at fixed offsets. Requires **`g++`**.

1. Install a toolchain (e.g. `sudo apt install g++` on Debian/Ubuntu).
2. Download [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) from [`Updates/Linux/Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates).
3. `chmod +x discord_voice_patcher_linux.sh` and run it. Use `./discord_voice_patcher_linux.sh --help` for options (`--patch-local`, etc.).

When Discord updates the voice module, refresh offsets with the [Offset Finder](#offset-finder) and update the script.

`Stereo-Installer-Linux.sh` and related files remain in the repo for later; they are not the supported path today.

---

<a id="windows-runtime-patcher"></a>

## Windows — Runtime patcher

Use when you need new offsets or full control. Compiles C++ at runtime — requires a **C++** toolchain (Visual Studio with C++, or MinGW-w64).

- [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) → [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1)

---

<a id="macos"></a>

## macOS

Thanks to **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills / Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)** for the macOS patcher (bash, signing, Apple Silicon).

**[macOS patcher on Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)**

---

<details>
<summary><b>Mission and repository layout</b></summary>

## Mission

Enable **filterless true stereo** at **high bitrates** in Discord — with emphasis on signal integrity and real-time audio behavior across Windows, macOS, and Linux.

## What we do

| Area | Focus |
|------|--------|
| True stereo | Avoid mono downmix; keep two channels |
| Bitrate | Reduce encoder caps; higher Opus bitrate |
| Sample rate | Restore 48 kHz where limited |
| Filters | Bypass HP/DC paths where patched |
| Integrity | Less client-side “enhancement” on the signal |

## Repository layout

| Path | Contents |
|------|----------|
| [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) | Voice Fixer, Windows runtime patcher |
| [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux) | `discord_voice_patcher_linux.sh`; installer scripts reserved |
| [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) | Offset finder CLI and GUI |
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | Reference nodes for patchers |

[`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump) — archived modules for research (optional for end users).

</details>

---

## FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Discord often ships a new `discord_voice.node`, which moves RVAs. Wait for updated offsets in this repo, or run the **Offset Finder** on your file, paste the new block into the patcher, and run again.

</details>

<details>
<summary><b>No C++ compiler found</b></summary>

**Voice Fixer (Windows)** does not need a compiler.

**Runtime patchers** generate and compile C++ during a run. Install a toolchain:

**Windows:** [Visual Studio](https://visualstudio.microsoft.com/) (Desktop development with C++) or [MinGW-w64](https://www.mingw-w64.org/).

**Linux:** e.g. `sudo apt install g++` (Debian/Ubuntu), `sudo dnf install gcc-c++` (Fedora), `sudo pacman -S gcc` (Arch).

**macOS:** `xcode-select --install`

</details>

<details>
<summary><b>Cannot open file / permission denied</b></summary>

**Windows:** Run the patcher as **Administrator**.

**Linux:** Most installs under `~/.config/discord/` are user-writable. If not: `sudo chmod +w /path/to/discord_voice.node`

**macOS:** `codesign --remove-signature /path/to/discord_voice.node` if required, then retry.

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

Standard paths are scanned. **Windows:** `%LOCALAPPDATA%\Discord`. **Linux:** `~/.config/discord`, `/opt/discord`, Flatpak, Snap. **macOS:** `~/Library/Application Support/discord`, `/Applications/Discord.app`. Custom installs may need a manual path to the `.node` file.

</details>

<details>
<summary><b>Distorted or clipping audio</b></summary>

Gain may be too high. Stay at **1×** unless the source is very quiet; values above **3×** often clip.

</details>

<details>
<summary><b>BetterDiscord / Vencord / Equicord</b></summary>

**Yes** on Windows (auto-detected clients). The patch targets `discord_voice.node`. On Linux or macOS, standard Electron layouts are supported if the mod keeps the usual module paths.

</details>

<details>
<summary><b>Account bans</b></summary>

This changes local encoding only. There are **no known bans** tied to this project. Editing client files may violate Discord’s terms — use at your own risk.

</details>

<details>
<summary><b>Restore / unpatch</b></summary>

**Windows:** Restore in the patcher UI, or use `-Restore` where supported.

**Linux:** `./discord_voice_patcher_linux.sh --restore`

**macOS:** `./discord_voice_patcher_macos.sh --restore`

A Discord app update also replaces `discord_voice.node` with a fresh copy.

</details>

<details>
<summary><b>macOS: “Discord is damaged”</b></summary>

Quarantine after patching. Try: `xattr -cr /Applications/Discord.app`

</details>

<details>
<summary><b>macOS: signing / mmap errors</b></summary>

Patching can break the signature. The macOS patcher re-signs when possible. If needed: `codesign --remove-signature /path/to/discord_voice.node`, then run the patcher again.

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
<summary><b>Installer vs runtime patcher (Windows)</b></summary>

**Voice Fixer** ([`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo%20Installer.bat) → [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1)) installs **pre-patched** nodes. No compiler.

**Runtime patcher** ([`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) → [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1)) builds and applies patches at runtime. Needs a C++ compiler. Use for new offsets or full control.

**Linux:** use [`discord_voice_patcher_linux.sh`](#linux-voice-patcher); the Linux Stereo Installer is not supported yet.

</details>

---

<details>
<summary><b>Technical deep dive</b></summary>

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

After Discord rebases the module, run [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) or [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py), then paste the generated offset block into the Windows script and align Linux/macOS configs.

</details>

---

<details>
<summary><b>Changelog</b></summary>

### Repo layout (Mar 2026)
- Shipping assets under `Updates/`; `Voice Node Dump/` for archives

### v6.0 (Feb 2026)
- macOS patcher; Linux bash patcher; platform-specific bytes; mmap I/O on Unix

### v5.0 (Feb 2026)
- Multi-client GUI, backups, auto-update hooks

### v4.0–v1.0
- Encoder init patches, stereo pipeline, early patcher and PoC

</details>

---

## Partners

[Shaun (sh6un)](https://github.com/sh6un) · [UnpackedX](https://codeberg.org/UnpackedX) · [Voice Playground](https://discord-voice.xyz/) · [Oracle](https://github.com/oracle-dsc) · [Loof-sys](https://github.com/LOOF-sys) · [Hallow](https://github.com/ProdHallow) · [Ascend](https://github.com/bloodybapestas) · BluesCat · [Sentry](https://github.com/sentry1000) · [Sikimzo](https://github.com/sikimzo) · [CRÜE](https://codeberg.org/DiscordStereoPatcher-macOS) · [HorrorPills / Geeko](https://github.com/HorrorPills)

---

## Get involved

**[Issues](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/issues)** · **[Discord](https://discord.gg/gDY6F8RAfM)**

---

> **Disclaimer:** Provided as-is for research. Not affiliated with Discord Inc. Use at your own risk.
