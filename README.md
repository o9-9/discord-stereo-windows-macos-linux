<div align="center">

# 🎙️ Discord Audio Collective

**Filterless true stereo · High-bitrate Opus · Windows · macOS · Linux**

[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows)
[![macOS](https://img.shields.io/badge/macOS-Active-00C853?style=flat-square)](https://codeberg.org/DiscordStereoPatcher-macOS)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square)](https://discord-voice.xyz/)

</div>

---

## 🍎 macOS Patcher — Live

The macOS patcher is officially active. Huge thanks to **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills/Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)** for six months of work to make it happen.

- Bash patcher with auto-detection
- Code signing handling
- Apple Silicon (Rosetta) support

👉 **[Get the macOS Patcher on Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)**

---

## 🚀 Releases

Bundled **Windows + Linux** patchers and installers ship on **[GitHub Releases (v0.5)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v0.5)**.

**macOS** tooling lives on **[Codeberg — Discord Stereo Patcher (macOS)](https://codeberg.org/DiscordStereoPatcher-macOS)**.

The **`Updates/`** tree is the canonical source for raw scripts — used by auto-updaters, launchers, and advanced users running directly from `main`.

---

## 🎯 Mission

Enable **filterless true stereo** at **high bitrates** in Discord and beyond — focusing on signal integrity, channel behavior, and real-time media experimentation across all three platforms.

---

## 🔬 What We Do

| Area | Focus |
|---|---|
| **True Stereo Preservation** | Bypass mono downmix, force 2-channel output |
| **Bitrate Unlocking** | Remove encoder caps, push toward Opus high-bitrate |
| **Sample Rate Restoration** | Bypass 24kHz limits → native 48kHz |
| **Filter Bypassing** | Disable HP filters, DC rejection, gain processing |
| **Signal Integrity** | Clean passthrough without Discord's audio "enhancements" |

---

## 📂 Repository Layout

Everything shippable and research-related lives in two top-level folders.

### [`Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates)

| Path | Contents |
|---|---|
| [`Updates/Windows/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Windows) | [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) — core PowerShell patcher with gain, backups, and multi-client detection · [`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) — launcher BAT for the patcher · [`Stereo%20Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo%20Installer.bat) — simplified installer flow · [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1) — repair/restore helper |
| [`Updates/Linux/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux) | [`discord-stereo-launcher.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/discord-stereo-launcher.sh) — top-level Linux launcher · [`Updates/Linux/Updates/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates) contains [`discord_voice_patcher_linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/discord_voice_patcher_linux.sh) — core patcher · [`Stereo-Installer-Linux.sh`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Linux/Updates/Stereo-Installer-Linux.sh) — installer helper |
| [`Updates/Offset Finder/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Offset%20Finder) | [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) — CLI tool to discover/validate RVAs after a Discord update · [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py) — GUI wrapper for the same |
| [`Updates/Nodes/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes) | **Unpatched Nodes** — stock module metadata the patcher expects · **Patched Nodes** — pre-patched bundles for the Windows installer flow |

### [`Voice Node Dump/`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Voice%20Node%20Dump)

Archived `discord_voice` module trees keyed by **platform + build** — used for offset research, regression checks, and comparing unpatched vs patched layouts. Maintainer/contributor material; not required to run the patcher from Releases.

---

## ❓ FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Expected. Discord ships a new `discord_voice.node` with most updates, which shifts the internal offsets the patcher targets. Wait for updated offsets in this repo, or run the **Offset Finder** against your node and paste the new block into the patcher, then re-run.

Check [`Updates/Windows/Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1) (and Linux/macOS counterparts) after a Discord release.
</details>

<details>
<summary><b>"No C++ compiler found"</b></summary>

The patcher compiles a small C++ binary at runtime. You need a compiler:

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

- **[`Stereo Installer.bat`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo%20Installer.bat) / [`DiscordVoiceFixer.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1)** — simplified installer-oriented flow.
- **[`Stereo-Node-Patcher-Windows.BAT`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Stereo-Node-Patcher-Windows.BAT) + [`Discord_voice_node_patcher.ps1`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/Discord_voice_node_patcher.ps1)** — full patcher with gain control, backups, multi-client detection, and auto-update from this repo.

Use the **Installer** for simplicity; the **Patcher** for full control.
</details>

---

## 🧬 Technical Deep Dive

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

### The 18 Patch Targets

| # | Target | What It Does | Patch |
|---|---|---|---|
| 1 | `CreateAudioFrameStereo` | Forces stereo channel count in frame metadata | `mov r13,rax; nop` (Win) / `mov r12,rax; nop` (Linux/macOS) |
| 2 | `AudioEncoderOpusConfigSetChannels` | Overwrite channel immediate to `2` | `0x02` |
| 3 | `MonoDownmixer` | Bypasses stereo→mono mix entirely | 12× `NOP` + `JMP` |
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
| 16 | `DuplicateEmulateBitrateModified` | Parallel bitrate path — same 400kbps patch as #6 | `0x80 0x1A 0x06` |
| 17 | `EncoderConfigInit1` | First Opus config constructor — init to 400kbps | `0x80 0x1A 0x06 0x00` |
| 18 | `EncoderConfigInit2` | Second Opus config constructor — same | `0x80 0x1A 0x06 0x00` |

### Platform Differences

| Aspect | Windows (PE) | Linux (ELF) | macOS (Mach-O) |
|---|---|---|---|
| **Compiler** | MSVC | Clang | Clang |
| **Calling convention** | rcx, rdx, r8, r9 | rdi, rsi, rdx, rcx | rdi, rsi, rdx, rcx |
| **Image base** | `0x180000000` | 0 (PIE) | 0 (PIE) |
| **CreateAudioFrameStereo** | `mov r13,rax` | `mov r12,rax` | `mov r12,rax` |
| **EmulateStereoSuccess2** | `JNE (0x75)` | `JE (0x74)` | `JE (0x74)` |
| **ConfigIsOk patch** | 8-byte `mov rax,1; ret` | 1-byte `ret` | 1-byte `ret` |
| **HighPassFilter patch** | 11-byte stub | 1-byte `ret` | 1-byte `ret` |

### Amplifier Injection

`hp_cutoff` and `dc_reject` are compiled separately, then their machine code is copied byte-for-byte into the binary at the corresponding offsets — replacing Discord's filter implementations with custom versions that write specific values to the Opus encoder state and apply a gain multiplier: `out[i] = in[i] * (channels + Multiplier)`.

At **1x** gain, `Multiplier = -1`, which with `channels = 2` gives exactly unity gain — no amplification.

### Offset Finder

When Discord rebases `discord_voice.node`, RVAs move. Run [`discord_voice_node_offset_finder_v5.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/discord_voice_node_offset_finder_v5.py) (or [`offset_finder_gui.py`](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Offset%20Finder/offset_finder_gui.py)) against your current node, then paste the generated `# region Offsets` block into `Discord_voice_node_patcher.ps1` (and sync Linux/macOS configs as needed).

---

## 📋 Changelog

### Repo Layout (Mar 2026)
- Flattened shipping assets under `Updates/` (Windows, Linux, Offset Finder, Nodes)
- Added `Voice Node Dump/` for archived module trees and build-to-build research
- README paths updated; macOS remains on [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS)

### v6.0 — Cross-Platform Release (Feb 2026)
- 🍎 macOS Patcher — native bash, code signing, Apple Silicon (Rosetta)
- 🐧 Linux Beta Patcher — native bash, auto-detects deb/Flatpak/Snap
- Platform-specific patch bytes (r12 vs r13, je vs jne, Clang vs MSVC prologue)
- POSIX file I/O (mmap/msync) for Linux/macOS

### v5.0 — Multi-Client & GUI Patcher (Feb 2026)
- Multi-client detection (Stable, Canary, PTB, BD, Vencord, Equicord, etc.)
- GUI patcher with gain slider, backup/restore, auto-relaunch
- Auto-updater with version comparison and downgrade prevention
- User config persistence

### v4.0 — Encoder Config Init (Feb 2026)
- Patched both Opus encoder config constructors (`EncoderConfigInit1`, `EncoderConfigInit2`)
- Prevents bitrate reset between encoder creation and first `SetBitrate`
- `DuplicateEmulateBitrateModified` path patching

### v3.0 — Full Stereo Pipeline (Jan 2026)
- Complete stereo enforcement: `CreateAudioFrameStereo`, `SetChannels`, `MonoDownmixer`
- Bitrate unlock across encoder paths
- 48kHz sample rate restoration
- High-pass filter bypass with function body injection
- `ConfigIsOk` override and `ThrowError` suppression
- Configurable audio gain (1–10x)

### v2.0 — Initial Patcher (Jan 2026)
- Basic binary patching for stereo and bitrate
- Single-client support, manual offset entry

### v1.0 — Proof of Concept (Dec 2025)
- Manual hex editing guide, initial Windows PE research

---

## 🤝 Partners

[Shaun (sh6un)](https://github.com/sh6un) · [UnpackedX](https://codeberg.org/UnpackedX) · [Voice Playground](https://discord-voice.xyz/) · [Oracle](https://github.com/oracle-dsc) · [Loof-sys](https://github.com/LOOF-sys) · [Hallow](https://github.com/ProdHallow) · [Ascend](https://github.com/bloodybapestas) · BluesCat · [Sentry](https://github.com/sentry1000) · [Sikimzo](https://github.com/sikimzo) · [CRÜE](https://codeberg.org/DiscordStereoPatcher-macOS) · [HorrorPills / Geeko](https://github.com/HorrorPills)

---

## 💬 Get Involved

Found new offsets? Have test results? Want to help reverse engineer macOS/Linux builds? **Contributors, testers, and audio nerds welcome.**

**[Report an Issue](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/issues)** · **[Join the Discord](https://discord.gg/gDY6F8RAfM)**

---

> ⚠️ **Disclaimer:** Tools provided as-is for research and experimentation. Use at your own risk. Not affiliated with Discord Inc.
