<div align="center">

# Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://codeberg.org/DiscordStereoPatcher-macOS)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

**On GitHub?** Open the README on the **`main`** branch so you see the latest: [`README.md` (main)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/README.md)

</div>

---

## 👋 New here?

**Goal:** better Discord voice (stereo, bitrate, filters) — in a few clicks.

| Step | What to do |
|:---:|:---|
| **1** | **Pick your OS** in the table below — always start with the easy path. |
| **2** | **Run** the installer or patcher for your OS (the scripts **close Discord and restart it** when needed — you don’t have to quit manually). |
| **3** | Join a voice channel and confirm everything sounds right. |

> 💡 **Easy path** = pre-downloaded patches. **No C++ compiler.**  
> 🧩 **Advanced path** = you compile + patch yourself — only if you need fresh offsets or full control → [Advanced: runtime patcher](#advanced-runtime-patcher).

---

## ✨ Pick your platform

|  | **You want…** | **Jump to** |
|:---:|:---|:---|
| 🪟 | **Windows — simplest** | [**Voice Fixer (easy)**](#windows-easy) |
| 🐧 | **Linux** — pre-patched installer *or* runtime patcher | [**Stereo Installer**](#linux-easy) · [**Runtime patcher**](#advanced-runtime-patcher) |
| 🍎 | **macOS** | [**macOS on Codeberg**](#macos-patcher--live) |

---

## 📦 Where to download

|  |  |
|:---|:---|
| 📀 **Release bundles** (Windows + Linux installers packaged together) | [**GitHub Releases**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases) · e.g. [v0.5](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v0.5) |
| 🍎 **macOS** | [**Codeberg — macOS patcher**](https://codeberg.org/DiscordStereoPatcher-macOS) |
| ⚡ **Latest scripts always** (what the BAT / launchers fetch) | **[`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates)** on `main` |

> **`Updates/`** is the live source — auto-updaters and “run from GitHub” flows pull from here.

---

<a id="windows-easy"></a>

## 🪟 Windows — Voice Fixer (easy)

**In one sentence:** drops **pre-patched** `discord_voice.node` files into your Discord folder(s), with backups. **No compiler.**

### ⚡ TL;DR — do this

1. Download **`Stereo Installer.bat`** → [open the `Updates/Windows` folder](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) → use the file, or grab it directly: [**Stereo Installer.bat (raw)**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Windows/Stereo%20Installer.bat).
2. **Right‑click → Run as administrator.**
3. In **DiscordVoiceFixer**, pick your client(s) → install. The script **closes Discord for you** and restarts it when needed.

<details>
<summary><b>📝 More detail (optional)</b></summary>

1. Save `Stereo Installer.bat` anywhere you like (Desktop is fine).
2. Run as **Administrator** so `%LOCALAPPDATA%\Discord\...` can be updated without permission errors.
3. The BAT downloads and runs [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1) from `main` — power users can invoke that script directly if they prefer.

</details>

---

<a id="linux-easy"></a>

## 🐧 Linux — Stereo Installer (pre-patched)

**In one sentence:** downloads **pre-built patched** `discord_voice.node` bundles from the repo and installs them for common Discord paths (deb / Flatpak / Snap where supported). **No compiler.**

> ⚠️ **Pre-patched Linux bundles often lag Discord stable.** Community drops have not always been refreshed every release (for example, working pre-built modules were last aligned with older app versions such as **0.0.128**, while Discord may ship **0.0.132** or newer). If the installer’s modules **don’t match** your installed Discord build, use the **[Linux runtime patcher](#advanced-runtime-patcher)** with [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) instead — it targets the **offsets + fingerprint** baked into the script for a specific `discord_voice.node` (update offsets when Discord updates).

### ⚡ TL;DR — do this

1. Download **`Stereo-Installer-Linux.sh`** from [`Updates/Linux/Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates) — direct: [**raw file**](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/raw/main/Updates/Linux/Updates/Stereo-Installer-Linux.sh).
2. In a terminal (in the folder where you saved the script):

   ```bash
   chmod +x Stereo-Installer-Linux.sh
   ./Stereo-Installer-Linux.sh
   ```

3. Follow the GUI — or use `./Stereo-Installer-Linux.sh --no-gui` for a text menu. The installer **handles Discord** (close/restart) for you unless you pass flags like `--no-restart`.

<details>
<summary><b>📝 Extras (help, launcher)</b></summary>

|  |  |
|:---|:---|
| 📖 **All options** | `./Stereo-Installer-Linux.sh --help` (restore, silent, diagnostics, …) |
| 🚀 **One-shot launcher** | [`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh) downloads the latest helper + GUI into a **`Linux Stereo Installer/`** folder next to the script |
| 🔧 **Current Discord, no matching bundle?** | Use [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) (see [Advanced: runtime patcher](#advanced-runtime-patcher)) and refresh offsets if needed ([Offset Finder](#offset-finder)). |

</details>

---

<a id="advanced-runtime-patcher"></a>

## 🧩 Advanced: runtime patcher

You **compile** a small tool and **patch** your local `discord_voice.node` at runtime. **On Linux this is often the reliable path** when you are on the latest Discord build and the **pre-patched Stereo Installer** bundles are behind. Update **offsets** when Discord ships a new voice module ([Offset Finder](#offset-finder)).

| OS | Start here | You also need |
|:---|:---|:---|
| 🪟 **Windows** | [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) → [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) | **C++** (VS Build Tools or MinGW-w64) |
| 🐧 **Linux** | [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) | **`g++`** |

<details>
<summary><b>🐧 Linux runtime patcher notes</b></summary>

Can download an **unpatched** stock node from this repo, then patch — or use **`--patch-local`** for a file you already have. Run the script with **`--help`** for all flags.

</details>

---

## 🍎 macOS Patcher — Live

The macOS patcher is officially active. Huge thanks to **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills/Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)** for six months of work to make it happen.

- Bash patcher with auto-detection  
- Code signing handling  
- Apple Silicon (Rosetta) support  

👉 **[Get the macOS Patcher on Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)**

---

<details>
<summary><b>🎯 Mission, features & repository layout</b></summary>

## 🎯 Mission

Enable **filterless true stereo** at **high bitrates** in Discord and beyond — focusing on signal integrity, channel behavior, and real-time media experimentation across all three platforms.

## 🔊 What we do

| Area | Focus |
|------|--------|
| **True stereo preservation** | Bypass mono downmix, force 2-channel output |
| **Bitrate unlocking** | Remove encoder caps, push toward Opus high-bitrate |
| **Sample rate restoration** | Bypass 24 kHz limits → native 48 kHz |
| **Filter bypassing** | Disable HP filters, DC rejection, gain processing |
| **Signal integrity** | Clean passthrough without Discord's audio "enhancements" |

## 📂 Repository layout

Everything shippable and research-related lives in two top-level folders.

### [`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates)

| Path | Contents |
|------|----------|
| [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) | **`Stereo Installer.bat`** → Voice Fixer (pre-patched nodes) · **`Stereo-Node-Patcher-Windows.BAT`** → runtime patcher PS1 |
| [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux) | **`discord-stereo-launcher.sh`** · **`Updates/Linux/Updates/`** — **`Stereo-Installer-Linux.sh`**, **`discord_voice_patcher_linux.sh`** |
| [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) | **`discord_voice_node_offset_finder_v5.py`**, **`offset_finder_gui.py`** |
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | Unpatched / patched module metadata the installers expect |

### [`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump)

Archived `discord_voice` module trees keyed by **platform + build** — for offset research and regression checks. Maintainer material; **not** required to use Releases or the easy installers.

</details>

---

## ❓ FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Expected. Discord ships a new `discord_voice.node` with most updates, which shifts the internal offsets the patcher targets. Wait for updated offsets in this repo, or run the **Offset Finder** against your node and paste the new block into the patcher, then re-run.

Check [`Updates/Windows/Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) (and Linux/macOS counterparts) after a Discord release.
</details>

<details>
<summary><b>"No C++ compiler found"</b></summary>

The **runtime patcher** compiles a small C++ binary at runtime. The **easy installers** do not need a compiler.

**Windows:** Install [Visual Studio](https://visualstudio.microsoft.com/) (Community, select "Desktop development with C++") or [MinGW-w64](https://www.mingw-w64.org/).

**Linux:**
```
Ubuntu/Debian:  sudo apt install g++
Fedora/RHEL:    sudo dnf install gcc-c++
Arch:           sudo pacman -S gcc
```

**macOS:**
```
xcode-select --install
```
</details>

<details>
<summary><b>"Cannot open file" / Permission denied</b></summary>

**Windows:** Right-click the patcher → **Run as Administrator**. The script auto-elevates but do it manually if it fails.

**Linux:** Most `~/.config/discord/` installs are user-writable. If not:
```
sudo chmod +w /path/to/discord_voice.node
```

**macOS:**
```
codesign --remove-signature /path/to/discord_voice.node
```
</details>

<details>
<summary><b>"Binary validation failed — unexpected bytes at patch sites"</b></summary>

The patcher checks known byte sequences before writing. A mismatch means your `discord_voice.node` is from a different build than the offsets expect — this is a safety feature that prevents corrupting the wrong binary.

**Fix:** Use offsets that match your current Discord build. Check `Updates/` for the latest scripts or run the Offset Finder if you're ahead of published offsets.
</details>

<details>
<summary><b>"This file appears to already be patched"</b></summary>

The patcher detected its own patch bytes at the target locations. This is a warning only — it will re-patch anyway to ensure all patches are applied consistently.
</details>

<details>
<summary><b>No Discord installations found</b></summary>

The patcher scans standard install paths. Custom installs won't be auto-detected.

**Windows:** Checks `%LOCALAPPDATA%\Discord`.

**Linux:** Checks `~/.config/discord`, `/opt/discord`, Flatpak (`~/.var/app/com.discordapp.Discord`), and Snap (`/snap/discord`).

**macOS:** Checks `~/Library/Application Support/discord` and `/Applications/Discord.app`.

If your install is elsewhere, manually point the compiled patcher at the `.node` file.
</details>

<details>
<summary><b>Audio sounds distorted / clipping</b></summary>

You're using too high a gain multiplier. Anything above **3x** can clip on loud sources.

**Recommended:** Start at **1x** (unity gain). Only go higher if your mic is very quiet. Re-run the patcher with a lower gain value to fix.
</details>

<details>
<summary><b>Does this work with BetterDiscord / Vencord / Equicord?</b></summary>

**Yes.** The Windows patcher auto-detects BetterDiscord, Vencord, Equicord, BetterVencord, and Lightcord. It patches the underlying `discord_voice.node`, which is shared regardless of client mod. On Linux/macOS, as long as the mod uses the standard Electron module structure, the patcher will find the voice node.
</details>

<details>
<summary><b>Will this get my account banned?</b></summary>

This modifies client-side audio encoding locally. It does not interact with Discord's servers in any unauthorized way — it changes how your client encodes audio before sending it through the normal Opus pipeline. There have been **no known bans** from using this patcher.

That said, modifying Discord's files is technically against their ToS. Use at your own discretion.
</details>

<details>
<summary><b>How do I restore / unpatch?</b></summary>

**Windows:** Run the patcher and click **Restore**, or run with the `-Restore` flag.

**Linux/macOS:**
```
./discord_voice_patcher_linux.sh --restore
./discord_voice_patcher_macos.sh --restore
```

You can also just let Discord update — any update replaces `discord_voice.node` with a fresh copy.
</details>

<details>
<summary><b>macOS: "Discord is damaged and can't be opened"</b></summary>

macOS quarantine flagging after patching. Fix:
```
xattr -cr /Applications/Discord.app
```
</details>

<details>
<summary><b>macOS: mmap fails / code signing errors</b></summary>

Patching invalidates the binary's code signature. The macOS patcher re-signs automatically with an ad-hoc signature, but if that fails:
```
codesign --remove-signature /path/to/discord_voice.node
# Then re-run the patcher
```
</details>

<details>
<summary><b>Linux: Flatpak / Snap permission issues</b></summary>

**Flatpak:**
```
find ~/.var/app/com.discordapp.Discord -name "discord_voice.node"
# Patch with explicit path if needed
```

**Snap:** `/snap/discord/current/` is read-only. Copy the node out, patch it, copy it back — or use the deb install instead.
</details>

<details>
<summary><b>Does the other person need the patch too?</b></summary>

**No.** The patch changes how *your* client encodes and sends audio. The receiver just sees a higher-quality Opus stream. No changes needed on their end.
</details>

<details>
<summary><b>I'm not being heard / others can't hear me</b></summary>

If you're using a **VPN, your audio may not transmit correctly.** Low-quality or misconfigured VPNs can interfere with Discord's voice UDP packets — causing others to hear nothing, hear choppy audio, or miss you entirely. Try disconnecting your VPN and testing again. If that fixes it, the VPN is the culprit (try a different server, protocol, or provider).
</details>

<details>
<summary><b>What's the difference between the Installer and the Patcher?</b></summary>

**Installer** ([`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo%20Installer.bat) → [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1)) — downloads and drops **pre-patched** `discord_voice.node` files directly into your Discord install. GUI-driven with backup/restore, update detection, and EQ APO fix. No compiler needed. Best for most users.

**Patcher** ([`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) → [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1)) — **compiles and applies patches at runtime** directly to the binary at specific offsets. Requires a C++ compiler. Use this when you have updated offsets ahead of a published pre-patched node, or want full control over patch behavior.
</details>

---

<details>
<summary><b>🧬 Technical deep dive (architecture, patch tables, offset finder)</b></summary>

## 🧬 Technical deep dive

### Architecture

The patcher modifies Discord's `discord_voice.node` — a native Node.js addon (shared library) containing the Opus encoder pipeline, audio preprocessing, and WebRTC integration. It ships as a PE DLL (Windows), ELF shared object (Linux), or Mach-O dylib (macOS).

```
Patcher (Bash/PowerShell)
┌──────────────────────────┐
│ Read offsets from config  │
│ Generate C++ source       │
│ Compile amplifier +       │
│   patcher binary          │
│ Execute against binary    │
│ Write patched bytes       │
└──────────────────────────┘
```

### The 17 patch targets

| # | Target | What it does | Patch |
|---|--------|--------------|--------|
| 1 | `CreateAudioFrameStereo` | Forces stereo channel count in frame metadata | `mov r13,rax; nop` (Win) / `mov r12,rax; nop` (Linux/macOS) |
| 2 | `AudioEncoderOpusConfigSetChannels` | Overwrite channel immediate to `2` | `0x02` |
| 3 | `MonoDownmixer` | Bypasses stereo→mono mix entirely | NOP block + `JMP rel32` (layout-aware on Linux Clang vs MSVC) |
| 4 | `EmulateStereoSuccess1` | Forces stereo capability check to return `2` | `0x02` |
| 5 | `EmulateStereoSuccess2` | Patches conditional branch to unconditional jump | `JMP (0xEB)` |
| 6 | `EmulateBitrateModified` | Overwrites bitrate result with 400000 | `0x80 0x1A 0x06` |
| 7 | `SetsBitrateBitrateValue` | Writes 400kbps as 32-bit LE | `0x80 0x1A 0x06 0x00 0x00` |
| 8 | `SetsBitrateBitwiseOr` | NOPs the bitwise OR that caps bitrate | 3× `NOP` |
| 9 | `Emulate48Khz` | NOPs `cmovb` that clamps sample rate to 24kHz | 3× `NOP` |
| 10 | `HighPassFilter` | Replaces HP filter entry with `ret` | `RET` / 11-byte stub |
| 11 | `HighpassCutoffFilter` | Overwrites HP filter body with compiled `hp_cutoff()` | Compiled function body |
| 12 | `DcReject` | Overwrites DC rejection body with compiled `dc_reject()` | Compiled function body |
| 13 | `DownmixFunc` | Immediate `RET` to skip downmix processing | `0xC3` |
| 14 | `AudioEncoderOpusConfigIsOk` | Forces config validation to return `1` | `mov rax,1; ret` (Win) / `ret` (Linux/macOS) |
| 15 | `ThrowError` | Suppresses encoder errors | `0xC3` |
| 16 | `EncoderConfigInit1` | First Opus config constructor — init to 400kbps | `0x80 0x1A 0x06 0x00` |
| 17 | `EncoderConfigInit2` | Second Opus config constructor — same | `0x80 0x1A 0x06 0x00` |

### Platform differences

| Aspect | Windows (PE) | Linux (ELF) | macOS (Mach-O) |
|--------|--------------|-------------|----------------|
| **Compiler** | MSVC | Clang | Clang |
| **Calling convention** | rcx, rdx, r8, r9 | rdi, rsi, rdx, rcx | rdi, rsi, rdx, rcx |
| **Image base** | `0x180000000` | 0 (PIE) | 0 (PIE) |
| **CreateAudioFrameStereo** | `mov r13,rax` | `mov r12,rax` | `mov r12,rax` |
| **EmulateStereoSuccess2** | `JNE (0x75)` | `JE (0x74)` | `JE (0x74)` |
| **ConfigIsOk patch** | 8-byte `mov rax,1; ret` | 1-byte `ret` | 1-byte `ret` |
| **HighPassFilter patch** | 11-byte stub | 1-byte `ret` | 1-byte `ret` |

### Amplifier injection

`hp_cutoff` and `dc_reject` are compiled separately, then their machine code is copied byte-for-byte into the binary at the corresponding offsets — replacing Discord's filter implementations with custom versions that write specific values to the Opus encoder state and apply a gain multiplier: `out[i] = in[i] * (channels + Multiplier)`.

At **1x** gain, `Multiplier = -1`, which with `channels = 2` gives exactly unity gain — no amplification.

### Offset Finder

When Discord rebases `discord_voice.node`, RVAs move. Run [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) (or [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py)) against your current node, then paste the generated `# region Offsets` block into `Discord_voice_node_patcher.ps1` (and sync Linux/macOS configs as needed).

</details>

---

<details>
<summary><b>📋 Full changelog</b></summary>

## 📋 Changelog

### Repo layout (Mar 2026)
- Flattened shipping assets under `Updates/` (Windows, Linux, Offset Finder, Nodes)
- Added `Voice Node Dump/` for archived module trees and build-to-build research
- README paths updated; macOS remains on [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)

### v6.0 — Cross-platform release (Feb 2026)
- macOS Patcher — native bash, code signing, Apple Silicon (Rosetta)
- Linux beta patcher — native bash, auto-detects deb/Flatpak/Snap
- Platform-specific patch bytes (r12 vs r13, je vs jne, Clang vs MSVC prologue)
- POSIX file I/O (mmap/msync) for Linux/macOS

### v5.0 — Multi-client & GUI patcher (Feb 2026)
- Multi-client detection (Stable, Canary, PTB, BD, Vencord, Equicord, etc.)
- GUI patcher with gain slider, backup/restore, auto-relaunch
- Auto-updater with version comparison and downgrade prevention
- User config persistence

### v4.0 — Encoder config init (Feb 2026)
- Patched both Opus encoder config constructors (`EncoderConfigInit1`, `EncoderConfigInit2`)
- Prevents bitrate reset between encoder creation and first `SetBitrate`
- `DuplicateEmulateBitrateModified` path patching

### v3.0 — Full stereo pipeline (Jan 2026)
- Complete stereo enforcement: `CreateAudioFrameStereo`, `SetChannels`, `MonoDownmixer`
- Bitrate unlock across encoder paths
- 48kHz sample rate restoration
- High-pass filter bypass with function body injection
- `ConfigIsOk` override and `ThrowError` suppression
- Configurable audio gain (1–10x)

### v2.0 — Initial patcher (Jan 2026)
- Basic binary patching for stereo and bitrate
- Single-client support, manual offset entry

### v1.0 — Proof of concept (Dec 2025)
- Manual hex editing guide, initial Windows PE research

</details>

---

## 🤝 Partners

[Shaun (sh6un)](https://github.com/sh6un) · [UnpackedX](https://codeberg.org/UnpackedX) · [Voice Playground](https://discord-voice.xyz/) · [Oracle](https://github.com/oracle-dsc) · [Loof-sys](https://github.com/LOOF-sys) · [Hallow](https://github.com/ProdHallow) · [Ascend](https://github.com/bloodybapestas) · BluesCat · [Sentry](https://github.com/sentry1000) · [Sikimzo](https://github.com/sikimzo) · [CRÜE](https://codeberg.org/DiscordStereoPatcher-macOS) · [HorrorPills / Geeko](https://github.com/HorrorPills)

---

## 💬 Get involved

Found new offsets? Have test results? Want to help reverse engineer macOS/Linux builds? **Contributors, testers, and audio nerds welcome.**

**[Report an Issue](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/issues)** · **[Join the Discord](https://discord.gg/gDY6F8RAfM)**

---

> ⚠️ **Disclaimer:** Tools provided as-is for research and experimentation. Use at your own risk. Not affiliated with Discord Inc.
