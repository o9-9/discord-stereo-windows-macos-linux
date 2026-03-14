# Discord Stereo Patcher & Installer

**True stereo and high-bitrate voice on Discord — Windows, macOS, and Linux.**

[![Focus](https://img.shields.io/badge/Focus-True%20Stereo%20Voice-5865F2?style=flat-square)](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux)
[![Voice Playground](https://img.shields.io/badge/Voice%20Playground-Labs-white?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIi8+PGxpbmUgeDE9IjIiIHkxPSIxMiIgeDI9IjIyIiB5Mj0iMTIiLz48cGF0aCBkPSJNMTIgMmExNS4zIDE1LjMgMCAwIDEgNCAxMCAxNS4zIDE1LjMgMCAwIDEtNCAxMCAxNS4zIDE1LjMgMCAwIDEtNC0xMCAxNS4zIDE1LjMgMCAwIDEgNC0xMHoiLz48L3N2Zz4=)](https://discord-voice.xyz/)
[![Windows](https://img.shields.io/badge/Windows-Active-00C853?style=flat-square)](./Windows%20Patcher%20and%20Installer/)
[![macOS](https://img.shields.io/badge/MacOS-Active-00C853?style=flat-square)](https://codeberg.org/DiscordStereoPatcher-macOS)
[![Linux](https://img.shields.io/badge/Linux-Active-00C853?style=flat-square)](./Linux%20Patcher%20and%20Installer/)

---

## Quick links

| Platform | Get it |
|----------|--------|
| **Windows** | [Windows Patcher and Installer](./Windows%20Patcher%20and%20Installer/) — GUI patcher, multi-client detection |
| **macOS** | [macOS Patcher](https://codeberg.org/DiscordStereoPatcher-macOS) — Bash patcher, code signing, Apple Silicon |
| **Linux** | [Linux Patcher and Installer](./Linux%20Patcher%20and%20Installer/) — Bash patcher, deb / Flatpak / Snap |

**Release:** [v0.5 on GitHub Releases](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/releases/tag/v0.5) (Windows + Linux patcher and installer)

---

## What this does

We patch Discord’s `discord_voice.node` so voice uses **filterless true stereo** at **high bitrates** instead of Discord’s default limits.

| Before | After |
|--------|--------|
| 24 kHz | **48 kHz** |
| ~64 kbps | **up to 400 kbps** |
| Mono downmix | **True stereo** |
| Built-in filtering | **Filterless passthrough** |

**How:** True stereo preservation, bitrate unlock, 48 kHz restoration, and bypass of high-pass / DC rejection / gain processing so your client sends a clean, high-quality Opus stream. Receivers hear the improvement with no changes on their side.

---

## Important: VPN and voice

**If you can’t be heard or voice is unstable, try disabling your VPN.**  
VPNs, strict firewalls, and some antivirus tools interfere with Discord’s voice packets. Stereo needs more bandwidth and is hit harder. This is a network issue, not a patcher bug. If you need a VPN, use split-tunnelling so Discord traffic bypasses it.

---

## macOS patcher

The **macOS patcher** is maintained by **[Crüe](https://codeberg.org/DiscordStereoPatcher-macOS)** and **[HorrorPills/Geeko](https://codeberg.org/DiscordStereoPatcher-macOS)** — thanks to them for the work that made it possible.

- Bash patcher with auto-detection  
- Code signing handling  
- Apple Silicon (Rosetta) support  

**[Get the macOS Patcher](https://codeberg.org/DiscordStereoPatcher-macOS)**

---

## Mission and scope

**Goal:** Filterless true stereo at high bitrates in Discord and similar clients.

We focus on signal integrity, channel behaviour, and real-time voice: bypassing mono downmix, removing encoder caps, restoring 48 kHz, and disabling Discord’s extra processing so the stream stays clean.

---

## FAQ

<details>
<summary><b>Discord updated and the patcher stopped working</b></summary>

Normal. Discord often ships a new `discord_voice.node`; the layout the patcher targets changes. Wait for updated offsets in this repo, update your patcher script, and run it again.
</details>

<details>
<summary><b>"No C++ compiler found"</b></summary>

The patcher builds a small C++ helper at runtime. Install a compiler:

- **Windows:** [Visual Studio](https://visualstudio.microsoft.com/) (Desktop development with C++) or [MinGW-w64](https://www.mingw-w64.org/)
- **Linux:** `sudo apt install g++` (Debian/Ubuntu), `sudo dnf install gcc-c++` (Fedora), `sudo pacman -S gcc` (Arch)
- **macOS:** `xcode-select --install` (Xcode Command Line Tools, includes `clang++`)
</details>

<details>
<summary><b>"Cannot open file" / Permission denied</b></summary>

The patcher must be able to write to `discord_voice.node`.

- **Windows:** Run as Administrator (right-click → Run as administrator).
- **Linux:** `chmod +w /path/to/discord_voice.node` or run the patcher with `sudo` if needed.
- **macOS:** `chmod +w` first; if it still fails, try `codesign --remove-signature /path/to/discord_voice.node` then run the patcher again.
</details>

<details>
<summary><b>"Binary validation failed — unexpected bytes at patch sites"</b></summary>

The patcher checks known byte sequences before patching. A mismatch means this `discord_voice.node` is from a different build than the offsets in the script. Use offsets that match your Discord build (see the repo for the latest).
</details>

<details>
<summary><b>"This file appears to already be patched"</b></summary>

The patcher found its own patch bytes. It’s a warning only; it will re-apply patches so all 18 are consistent (useful after a partial patch).
</details>

<details>
<summary><b>No Discord installations found</b></summary>

The patcher only looks in standard install paths. Custom installs won’t be auto-detected. You can still point the patcher at the `.node` file manually. Typical paths: Windows `%LOCALAPPDATA%\Discord`; Linux `~/.config/discord`, `/opt/discord`, Flatpak/Snap paths; macOS `~/Library/Application Support/discord`, `/Applications/Discord.app`.
</details>

<details>
<summary><b>Audio distorted or clipping</b></summary>

Gain is too high. The patcher’s gain multiplies raw samples; above about **3x** you can clip. Use **1x** or **2x** unless your mic is very quiet. If it’s already distorted, re-run with a lower gain.
</details>

<details>
<summary><b>Does this work with BetterDiscord / Vencord / Equicord?</b></summary>

Yes. The Windows patcher detects BetterDiscord, Vencord, Equicord, BetterVencord, and Lightcord. It patches the same `discord_voice.node` they use. On Linux/macOS, any client that uses the usual Electron layout is supported.
</details>

<details>
<summary><b>Will this get my account banned?</b></summary>

This only changes how your client encodes audio before sending it over the normal Opus pipeline. We don’t know of any bans from using it. Modifying Discord’s files is still against their ToS; use at your own risk.
</details>

<details>
<summary><b>How do I restore / unpatch?</b></summary>

- **Windows:** Use **Restore** in the patcher or run with `-Restore`; it will list backups.
- **Linux/macOS:** `./discord_voice_patcher_linux.sh --restore` or `./discord_voice_patcher_macos.sh --restore`.

Letting Discord update also replaces `discord_voice.node` with a fresh, unpatched copy.
</details>

<details>
<summary><b>macOS: "Discord is damaged and can't be opened"</b></summary>

Quarantine flag after patching. Run: `xattr -cr /Applications/Discord.app`
</details>

<details>
<summary><b>macOS: mmap or code signing errors</b></summary>

Patching breaks the code signature. The macOS patcher re-signs ad-hoc; if it fails, run `codesign --remove-signature /path/to/discord_voice.node` then run the patcher again.
</details>

<details>
<summary><b>Linux: Flatpak / Snap permission issues</b></summary>

Sandboxing can block writes to the voice module. **Flatpak:** locate the node with `find ~/.var/app/com.discordapp.Discord -name "discord_voice.node"` and patch with an explicit path if needed. **Snap:** installs under `/snap/discord/current/` are often read-only; patch a copied file and replace it, or use the deb package.
</details>

<details>
<summary><b>Does the other person need the patch too?</b></summary>

No. The patch only changes how your client encodes and sends audio. They receive a normal (higher-quality) Opus stream and hear the improvement without any change on their side.
</details>

<details>
<summary><b>Installer vs Patcher?</b></summary>

**Installer** (e.g. `Stereo-Installer-Windows.bat`): one-click, no compiler; downloads pre-patched modules. **Patcher** (e.g. `Stereo-Node-Patcher-Windows.BAT`): compiles and patches locally, supports custom gain and newest Discord builds. Use the installer for simplicity, the patcher for control.
</details>

---

## Changelog

<details>
<summary><b>Show changelog</b></summary>

### v6.0 — Cross-Platform (Feb 2026)
- macOS patcher (bash, code signing, Apple Silicon)
- Linux beta patcher (bash, deb/Flatpak/Snap)
- Platform-specific patch bytes; POSIX file I/O on Linux/macOS

### v5.0 — Multi-Client & GUI (Feb 2026)
- Multi-client detection; GUI with gain slider, backup/restore, auto-relaunch
- Auto-updater; persisted user settings

### v4.0 — Encoder config init (Feb 2026)
- Patched encoder config constructors; duplicate bitrate path

### v3.0 — Full stereo pipeline (Jan 2026)
- Stereo enforcement, 400 kbps, 48 kHz, filter bypass, gain injection

### v2.0 — Initial patcher (Jan 2026)
- Basic binary patching; single-client; manual offsets

### v1.0 — Proof of concept (Dec 2025)
- Manual hex guide; Windows PE research

</details>

---

## Technical deep dive

<details>
<summary><b>Architecture and patch targets</b></summary>

The patcher modifies Discord’s `discord_voice.node` — a native Node.js addon (PE on Windows, ELF on Linux, Mach-O on macOS) containing the Opus encoder pipeline and WebRTC integration. It reads offsets, generates C++ source, compiles the amplifier and patcher binary, and writes patched bytes.

**18 patch targets:** CreateAudioFrameStereo (stereo channel in frame metadata), AudioEncoderOpusConfigSetChannels (force 2), MonoDownmixer (NOP+jump bypass), EmulateStereoSuccess1/2 (stereo check override), EmulateBitrateModified + SetsBitrateBitrateValue + SetsBitrateBitwiseOr (400 kbps), Emulate48Khz (48 kHz passthrough), HighPassFilter/HighpassCutoffFilter/DcReject (filter bypass or replacement), DownmixFunc (ret skip), AudioEncoderOpusConfigIsOk (return 1), ThrowError (ret), DuplicateEmulateBitrateModified, EncoderConfigInit1/2 (init bitrate 400 kbps). Platform differences: Windows uses MSVC and different registers (e.g. r13 vs r12, JNE vs JE); Linux/macOS use Clang and PIE; ConfigIsOk and HighPassFilter use different patch sizes (8-byte stub on Windows, 1-byte ret on Linux/macOS).

**Amplifier injection:** `hp_cutoff` and `dc_reject` are compiled to machine code and copied into the binary at the target offsets; they disable internal filtering and apply gain. Validation and backup/restore prevent corrupting the wrong binary when Discord updates.
</details>

---

## Repositories

| Repo | Description |
|------|-------------|
| [Windows Patcher and Installer](./Windows%20Patcher%20and%20Installer/) | Windows voice patcher and installer |
| [macOS Patcher](https://codeberg.org/DiscordStereoPatcher-macOS) | macOS voice patcher |
| [Linux Patcher and Installer](./Linux%20Patcher%20and%20Installer/) | Linux voice patcher and installer |

---

## Thanks

- **Shaun (sh6un)**, **UnpackedX** ([Voice Playgrounds](https://discord-voice.xyz/)), **Oracle (oracle-dsc)**, **Loof-sys**
- **Hallow**, **Ascend**, BluesCat, **Sentry**, **Sikimzo**
- **CRÜE** and **HorrorPills/Geeko** and [Codeberg](https://codeberg.org/DiscordStereoPatcher-macOS) for the macOS patcher

Contributors, testers, and anyone with new offsets or test results are welcome.

---

**Disclaimer:** Provided as-is for research and experimentation. Not affiliated with Discord Inc. Use at your own risk.

**[Report issue](https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/issues)** · **[Development Discord](https://discord.gg/gDY6F8RAfM)**
