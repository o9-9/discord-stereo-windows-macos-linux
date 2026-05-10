#!/usr/bin/env python3

import sys
import os
import io
import atexit
import struct
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import networkx as nx
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    VIZ_AVAILABLE = True
except ImportError:
    VIZ_AVAILABLE = False

VERSION = "5.1.9"

TARGET_BITRATE_BPS = 384000
_BITRATE_LE = TARGET_BITRATE_BPS.to_bytes(4, "little")
BITRATE_PATCH_3 = " ".join(f"{b:02X}" for b in _BITRATE_LE[:3])
BITRATE_PATCH_4 = " ".join(f"{b:02X}" for b in _BITRATE_LE)
BITRATE_PATCH_5 = BITRATE_PATCH_4 + " 00"

DERIVATIONS = {
    "CodecProbe_ForceSuccessBranch": [
        ("CodecProbe_ChannelCountPatch", 0xC),
        ("CodecProbe_ChannelCountPatch", 0x1),
    ],
    "SampleRate_Select48kNop": [
        ("CodecProbe_ChannelCountPatch", 0x168),
    ],
    "OpusBitrate_Imul384k": [
        ("CodecProbe_ChannelCountPatch", 0x45F),
    ],
    "WebRtcHighpass_Trampoline": [
        ("CodecProbe_ChannelCountPatch", 0xC275),
    ],
    "AudioEncoder_BitrateOrMaskNop": [
        ("AudioEncoder_BitrateMovImm", 0x8),
    ],
    "OpusEncoderConfig_IsOkRetTrue": [
        ("OpusEncoderConfig_SetStereoChannels", 0x29C),
        ("OpusEncoderConfig_SetStereoChannels", 0x19B),
        ("OpusEncoderConfig_SetStereoChannels", 0x30B),
    ],
    "WebRtcDcReject_Injected": [
        ("WebRtcHighpassCutoff_Injected", 0x1E0),
        ("WebRtcHighpassCutoff_Injected", 0x1B0),
    ],
    "OpusEncoderConfig_CtorBitrate_A": [
        ("OpusEncoderConfig_SetStereoChannels", 0xA),
    ],
    "OpusEncoderConfig_CtorUseInbandFecOn": [
        ("OpusEncoderConfig_CtorBitrate_A", 0x27),
    ],
}

_PHASE2_SKIP_CLANG = frozenset({
    "OpusBitrate_Imul384k",
})

SLIDING_WINDOW_DEFAULT = 128
SLIDING_WINDOW_OVERRIDES = {
    "CodecProbe_ForceSuccessBranch": 48,
    "OpusEncoderConfig_CtorBitrate_A": 48,
    "OpusBitrate_Imul384k": 0x1000,
}

class Signature:

    def __init__(self, name, pattern_hex, target_offset, description,
                 expected_original=None, patch_bytes=None, patch_len=None,
                 disambiguator=None, alt_patterns=None):
        self.name = name
        self.pattern_hex = pattern_hex
        self.pattern = self._parse(pattern_hex)
        self.target_offset = target_offset
        self.description = description
        self.expected_original = expected_original
        self.patch_bytes = patch_bytes
        self.patch_len = patch_len
        self.disambiguator = disambiguator
        self.alt_patterns = []
        if alt_patterns:
            for alt_hex, alt_off in alt_patterns:
                self.alt_patterns.append((self._parse(alt_hex), alt_off))

    @staticmethod
    def _parse(hex_str):
        return [None if b == '??' else int(b, 16) for b in hex_str.split()]

    def __repr__(self):
        return f"Signature({self.name})"


def _mono_downmixer_disambiguator(data, match_offset):
    if match_offset + 8 + 13 <= len(data):
        if data[match_offset + 8:match_offset + 8 + 13] == b'\x90' * 13:
            return False
    jg_pos = match_offset + 19
    if jg_pos + 6 > len(data):
        return False
    if b'\x44\x0f\xb6' in data[jg_pos + 6 : jg_pos + 18]:
        return True
    if b'\x44\x0f\xb6' in data[jg_pos + 6 : jg_pos + 70]:
        return True
    return False


def _ess1_no_duplicate_cmp_in_next_24(data, match_offset):
    if match_offset + 18 + 24 > len(data):
        return True
    chunk = data[match_offset + 18 : match_offset + 18 + 24]
    pos = 0
    while pos <= len(chunk) - 8:
        if chunk[pos:pos+3] == b'\x80\xBC\x24' and chunk[pos+7] == 0x01:
            return False
        pos += 1
    return True


def has_nearby_stereo_setter(data, file_offset, window=120):
    if not isinstance(data, (bytes, bytearray)) or file_offset < 0:
        return False
    start = max(0, file_offset - window)
    end = min(len(data) - 8, file_offset + window)
    for pos in range(start, end):
        if data[pos:pos + 3] != b'\xC6\x84\x24':
            continue
        disp = struct.unpack_from('<I', data, pos + 3)[0]
        imm = data[pos + 7]
        if imm in (0, 1, 2) and 0x140 <= disp <= 0x1C0:
            return True
    return False


SIGNATURES = [
    Signature(
        name="CodecProbe_ChannelCountPatch",
        pattern_hex="E8 ?? ?? ?? ?? BD ?? 00 00 00 80 BC 24 80 01 00 00 01",
        target_offset=6,
        description="Stereo channel count: call <rel>; mov ebp, CHANNELS; cmp byte [rsp+0x180], 1",
        expected_original="01",
        patch_bytes="02",
        alt_patterns=[
            ("E8 ?? ?? ?? ?? BD ?? 00 00 00 80 BC 24 ?? ?? 00 00 01", 6),
            ("BD ?? 00 00 00 80 BC 24 ?? ?? 00 00 01", 1),
        ],
    ),

    Signature(
        name="OpusEncoderConfig_SetStereoChannels",
        pattern_hex="48 B9 14 00 00 00 80 BB 00 00 48 89 08 48 C7 40 08 ?? 00 00 00",
        target_offset=17,
        description="Opus config: mov rcx, {48000<<32|20}; mov [rax],rcx; mov qword [rax+8], CHANNELS",
        expected_original="01",
        patch_bytes="02",
        alt_patterns=[
            ("48 B9 14 00 00 00 80 BB 00 00 48 89 08 48 C7 40 ?? ?? 00 00 00", 17),
            ("48 B9 14 00 00 00 80 BB 00 00 48 89 ?? 48 C7 ?? ?? ?? 00 00 00", 17),
        ],
    ),

    Signature(
        name="DownmixMono_BypassBranch",
        pattern_hex="48 89 F9 E8 ?? ?? ?? ?? 84 C0 74 0D 83 BE ?? ?? 00 00 09 0F 8F",
        target_offset=8,
        description="Mono downmix gate: mov rcx,rdi; call; test al,al; jz +0xD; cmp [rsi+??], 9; jg",
        expected_original="84 C0 74 0D",
        patch_bytes="90 90 90 90 90 90 90 90 90 90 90 90 E9",
        patch_len=13,
        disambiguator=_mono_downmixer_disambiguator,
        alt_patterns=[
            ("48 89 ?? E8 ?? ?? ?? ?? 84 C0 ?? ?? 83 ?? ?? ?? 00 00 09 0F 8F", 8),
            ("4C 89 ?? E8 ?? ?? ?? ?? 84 C0 74 ?? 83 7B ?? 09 0F 8F", 8),
            ("4C 89 ?? E8 ?? ?? ?? ?? 84 C0 74 ?? 83 7B ?? 09 7F", 8),
        ],
    ),

    Signature(
        name="AudioEncoder_BitrateMovImm",
        pattern_hex="89 F8 48 B9 ?? ?? ?? ?? 01 00 00 00 48 09 C1 48 89 4E 1C",
        target_offset=4,
        description="Bitrate setter: mov eax,edi; mov rcx,imm64; or rcx,rax; mov [rsi+0x1C],rcx",
        expected_original=None,
        alt_patterns=[
            ("89 F8 48 B9 ?? ?? ?? ?? 01 00 00 00 48 09 C1 48 89 ?? ??", 4),
            ("89 ?? 48 B9 ?? ?? ?? ?? 01 00 00 00 48 09 C1 48 89 ?? ??", 4),
        ],
    ),

    Signature(
        name="AudioEncoderCodec_ThrowNoOp",
        pattern_hex="56 56 57 53 48 81 EC C8 00 00 00 0F 29 B4 24 B0 00 00 00 4C 89 CE 4C 89 C7 89 D3",
        target_offset=-1,
        description="Error handler: push rsi;rdi;rbx; sub rsp,0xC8; movaps [rsp+0xB0],xmm6; ...",
        expected_original="41",
        patch_bytes="C3",
        alt_patterns=[
            ("56 56 57 53 48 81 EC ?? ?? 00 00 0F 29 B4 24 ?? ?? 00 00 4C 89 CE 4C 89 C7 89 D3", -1),
        ],
    ),

    Signature(
        name="ChannelDownmix_RetStub",
        pattern_hex="57 41 56 41 55 41 54 56 57 55 53 48 83 EC 10 48 89 0C 24 45 85 C0",
        target_offset=-1,
        description="Downmix function: push r15..r12,rsi,rdi,rbp,rbx; sub rsp,0x10; ...",
        expected_original="41",
        patch_bytes="C3",
        alt_patterns=[
            ("57 41 56 41 55 41 54 56 57 55 53 48 83 EC ?? 48 89 0C 24 45 85 C0", -1),
            ("57 41 56 41 55 41 54 56 57 55 53 48 83 EC ?? 48 89 0C 24", -1),
        ],
    ),

    Signature(
        name="AudioFrame_StereoChannelAssign",
        pattern_hex="B8 80 BB 00 00 BD 00 7D 00 00 0F 43 E8",
        target_offset=31,
        description="Audio frame: mov eax,48000; mov ebp,32000; cmovae ebp,eax; ... second cmov",
        expected_original="4C 0F 43 E8",
        patch_bytes="49 89 C5 90",
        alt_patterns=[
            ("B8 80 BB 00 00 BD 00 7D 00 00 0F ?? E8", 31),
        ],
    ),

    Signature(
        name="WebRtcHighpassCutoff_Injected",
        pattern_hex="56 48 83 EC 30 44 0F 29 44 24 20 0F 29 7C 24 10 0F 29 34 24",
        target_offset=0,
        description="HP cutoff filter: push rsi; sub rsp,0x30; SSE saves (xmm8,xmm7,xmm6)",
        expected_original="56 48 83 EC 30",
        patch_bytes=None,
        patch_len=0x100,
        alt_patterns=[
            ("56 48 83 EC ?? 44 0F 29 44 24 ?? 0F 29 7C 24 ?? 0F 29 34 24", 0),
        ],
    ),
    Signature(
        name="OpusEncoderConfig_CtorBitrate_B",
        pattern_hex="48 B9 ?? ?? ?? ?? ?? ?? ?? ?? 48 89 48 10 66 C7 40 18 00 00 C6 40 1A 00",
        target_offset=6,
        description="Encoder config constructor 2: mov rcx,packed_qword; mov [rax+0x10],rcx; ...",
        expected_original="00 7D 00 00",
        patch_bytes=BITRATE_PATCH_4,
        patch_len=4,
        alt_patterns=[
            ("48 B9 ?? ?? ?? ?? ?? ?? ?? ?? 48 89 48 ?? 66 C7 40 ?? 00 00 C6 40 ?? 00", 6),
        ],
    ),
]

CLANG_ALT_PATTERNS = [
    ("CodecProbe_ChannelCountPatch",
     "E8 ?? ?? ?? ?? BF ?? 00 00 00 80 ?? 24 ?? ?? 00 00 01", 6),
    ("CodecProbe_ChannelCountPatch",
     "?? ?? 00 00 00 80 ?? 24 ?? ?? 00 00 01", 1),
    ("OpusEncoderConfig_SetStereoChannels",
     "48 B8 14 00 00 00 80 BB 00 00 48 89 ?? 48 C7 ?? ?? ?? 00 00 00", 17),
    ("OpusEncoderConfig_SetStereoChannels",
     "48 ?? 14 00 00 00 80 BB 00 00 48 89 ?? ?? 48 C7 ?? ?? ?? 00 00 00", 18),
    ("DownmixMono_BypassBranch",
     "48 89 FF E8 ?? ?? ?? ?? 84 C0 74 ?? 83 ?? ?? ?? 00 00 09 0F 8F", 8),
    ("DownmixMono_BypassBranch",
     "F3 0F 1E FA ?? 89 ?? E8 ?? ?? ?? ?? 84 C0 74 ?? 83 ?? ?? ?? 00 00 09 0F 8F", 12),
    ("DownmixMono_BypassBranch",
     "4C 89 ?? E8 ?? ?? ?? ?? 84 C0 74 ?? 83 7B ?? 09 0F 8F", 8),
    ("DownmixMono_BypassBranch",
     "4C 89 ?? E8 ?? ?? ?? ?? 84 C0 74 ?? 83 7B ?? 09 7F", 8),
    ("AudioEncoder_BitrateMovImm",
     "89 F8 48 ?? ?? ?? ?? ?? 01 00 00 00 48 09 ?? 48 89 ?? ??", 4),
    ("AudioEncoder_BitrateMovImm",
     "89 ?? 48 B8 ?? ?? ?? ?? 01 00 00 00 48 09 ?? 48 89 ?? ??", 4),
    ("AudioEncoderCodec_ThrowNoOp",
     "55 48 89 E5 41 57 41 56 41 55 41 54 53 48 ?? EC ?? ?? 00 00", -1),
    ("AudioEncoderCodec_ThrowNoOp",
     "F3 0F 1E FA 55 48 89 E5 41 57 41 56 41 55 41 54 53", 3),
    ("ChannelDownmix_RetStub",
     "55 48 89 E5 41 57 41 56 41 55 41 54 53 48 83 EC ?? 45 85 C0", -1),
    ("ChannelDownmix_RetStub",
     "F3 0F 1E FA 55 48 89 E5 41 57 41 56 41 55 41 54 53 48 83 EC ??", 3),
    ("ChannelDownmix_RetStub",
     "41 57 41 56 41 55 41 54 55 53 48 83 EC ?? 49 89 ?? 45 85 ??", -1),
    ("AudioFrame_StereoChannelAssign",
     "B8 80 BB 00 00 ?? ?? 00 7D 00 00 0F ?? ??", 31),
    ("WebRtcHighpassCutoff_Injected",
     "55 48 89 E5 ?? ?? EC ?? 0F 29 ?? ?? ?? 0F 29 ?? ?? ?? 0F 29", 0),
    ("WebRtcHighpassCutoff_Injected",
     "F3 0F 1E FA 56 48 83 EC ?? ?? 0F 29 ?? ?? ?? 0F 29 ?? ?? ?? 0F 29", 4),
    ("OpusEncoderConfig_CtorBitrate_B",
     "48 ?? ?? ?? ?? ?? ?? ?? ?? ?? 48 89 ?? ?? 66 C7 ?? ?? 00 00 C6 ?? ?? 00", 6),
    ("AudioEncoder_BitrateMovImm",
     "89 ?? 48 B9 00 00 00 00 01 00 00 00 48 09 C1", 4),
    ("AudioFrame_StereoChannelAssign",
     "B8 80 BB 00 00 41 BD 00 7D 00 00 44 0F 43 E8", 31),
    ("AudioFrame_StereoChannelAssign",
     "B8 80 BB 00 00 41 ?? 00 7D 00 00 ?? 0F 43 ??", 31),
]

# region PE Parser

def parse_pe(data):
    if len(data) < 0x40 or data[:2] != b'MZ':
        return None

    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    if pe_offset + 4 > len(data) or data[pe_offset:pe_offset+4] != b'PE\x00\x00':
        return None

    coff = pe_offset + 4
    num_sections = struct.unpack_from('<H', data, coff + 2)[0]
    timestamp = struct.unpack_from('<I', data, coff + 4)[0]
    opt_header_size = struct.unpack_from('<H', data, coff + 16)[0]

    opt = coff + 20
    magic = struct.unpack_from('<H', data, opt)[0]

    if magic == 0x20B:
        image_base = struct.unpack_from('<Q', data, opt + 24)[0]
    else:
        image_base = struct.unpack_from('<I', data, opt + 28)[0]

    sections = []
    sec_offset = opt + opt_header_size
    for i in range(num_sections):
        s = sec_offset + i * 40
        name = data[s:s+8].rstrip(b'\x00').decode('ascii', errors='replace')
        vsize = struct.unpack_from('<I', data, s + 8)[0]
        vaddr = struct.unpack_from('<I', data, s + 12)[0]
        raw_size = struct.unpack_from('<I', data, s + 16)[0]
        raw_offset = struct.unpack_from('<I', data, s + 20)[0]
        sections.append({
            'name': name, 'vsize': vsize, 'vaddr': vaddr,
            'raw_size': raw_size, 'raw_offset': raw_offset
        })

    file_offset_adjustment = None
    text_section = None
    for sec in sections:
        if sec['name'] == '.text':
            text_section = sec
            file_offset_adjustment = sec['vaddr'] - sec['raw_offset']
            break

    if file_offset_adjustment is None:
        for sec in sections:
            if sec['vaddr'] > 0 and sec['raw_offset'] > 0:
                file_offset_adjustment = sec['vaddr'] - sec['raw_offset']
                text_section = sec
                break

    if file_offset_adjustment is None:
        file_offset_adjustment = 0xC00
        text_section = sections[0] if sections else None

    build_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return {
        'image_base': image_base,
        'timestamp': timestamp,
        'build_time': build_time,
        'sections': sections,
        'pe_offset': pe_offset,
        'text_section': text_section,
        'file_offset_adjustment': file_offset_adjustment,
    }

# endregion PE Parser


# region ELF Parser
ELF_SYMBOL_MAP = {

    "AudioEncoderCodec_ThrowNoOp": {
        "patterns": ["Environment5ThrowIJPKcEE", "Environment5Throw", "throw_error"],
        "at_start": True,
        "prefer_smallest": True,
    },
    "ChannelDownmix_RetStub": {
        "patterns": ["downmix_and_resample"],
        "at_start": True,
    },
    "WebRtcHighpassCutoff_Injected": {
        "patterns": ["hp_cutoff"],
        "at_start": True,
    },
    "WebRtcDcReject_Injected": {
        "patterns": ["dc_reject"],
        "at_start": True,
    },
    "WebRtcHighpass_Trampoline": {
        "patterns": ["InitializeHighPassFilter"],
        "at_start": True,
    },


    "CodecProbe_ChannelCountPatch": {
        "patterns": ["LocalUser16CommitAudioCodecEv",
                     "LocalUser13ApplySettings"],
        "at_start": False,
        "linux_scan": "stereo_cmp_byte",
        "prefer_largest": True,
    },
    "AudioFrame_StereoChannelAssign": {
        "patterns": ["CreateAudioFrameToProcess", "CreateAudioFrame"],
        "at_start": False,
        "linux_scan": "channel_cmov",
    },
    "OpusEncoderConfig_SetStereoChannels": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev",
                     "OpusConfigC1", "OpusConfigC2"],
        "at_start": False,
        "linux_scan": "opus_config_channels",
    },
    "OpusEncoderConfig_SetMultiChannelStereo": {
        "patterns": [
            "AudioEncoderMultiChannelOpusConfigC1Ev",
            "AudioEncoderMultiChannelOpusConfigC2Ev",
            "AudioEncoderMultiChannelOpusConfig",
            "MultiChannelOpusConfig",
        ],
        "at_start": False,
        "linux_scan": "multichannel_opus_config_channels",
    },
    "AudioEncoder_BitrateMovImm": {
        "patterns": ["WebrtcAdmHelper22EnsureRecordingStarted",
                     "WebrtcAdmHelper20EnsurePlayoutStarted"],
        "exclude_patterns": ["__function", "__policy"],
        "at_start": False,
        "linux_scan": "bitrate_movabs_or",
    },
    "OpusEncoderConfig_CtorBitrate_B": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev"],
        "at_start": False,
        "linux_scan": "opus_config_bitrate",
    },
    "DownmixMono_BypassBranch": {
        "patterns": ["CapturedAudioProcessor7Process"],
        "at_start": False,
        "linux_scan": "mono_downmix_test",
    },
    "CodecProbe_ForceSuccessBranch": {
        "patterns": ["LocalUser16CommitAudioCodecEv",
                     "LocalUser13ApplySettings"],
        "at_start": False,
        "linux_scan": "stereo_success2_byte",
        "prefer_largest": True,
    },
    "SampleRate_Select48kNop": {
        "patterns": ["LocalUser16CommitAudioCodecEv",
                     "LocalUser13ApplySettings"],
        "at_start": False,
        "linux_scan": "emulate_48khz_cmov",
        "prefer_largest": True,
    },
}


_ARM64_MOVZ_W_MASK = 0xFFFFFFE0
_ARM64_MOVZ_W1     = 0x52800020
_ARM64_MOVZ_W2     = 0x52800040
_ARM64_MOVZ_W48000 = 0x52977000
_ARM64_MOVZ_W32000 = 0x528FA000
_ARM64_MOVZ_W960   = 0x52807800
_ARM64_RET         = 0xD65F03C0


ARM64_SYMBOL_MAP = {
    "AudioEncoderCodec_ThrowNoOp": {
        "patterns": ["Environment5ThrowIJPKcEE", "Environment5Throw", "throw_error"],
        "at_start": True,
        "prefer_smallest": True,
    },
    "ChannelDownmix_RetStub": {
        "patterns": ["downmix_and_resample"],
        "at_start": True,
    },
    "WebRtcHighpassCutoff_Injected": {
        "patterns": ["hp_cutoff"],
        "at_start": True,
    },
    "WebRtcDcReject_Injected": {
        "patterns": ["dc_reject"],
        "at_start": True,
    },
    "WebRtcHighpass_Trampoline": {
        "patterns": ["InitializeHighPassFilter"],
        "at_start": True,
    },

    "AudioFrame_StereoChannelAssign": {
        "patterns": ["CreateAudioFrameToProcess", "CreateAudioFrame"],
        "at_start": False,
        "arm64_scan": "arm64_channel_movz",
    },
    "OpusEncoderConfig_SetStereoChannels": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev",
                     "OpusConfigC1", "OpusConfigC2"],
        "at_start": False,
        "arm64_scan": "arm64_opus_config_channels",
    },
    "CodecProbe_ChannelCountPatch": {
        "patterns": ["LocalUser16CommitAudioCodecEv"],
        "at_start": False,
        "arm64_scan": "arm64_stereo_cmp",
        "prefer_largest": True,
    },
    "DownmixMono_BypassBranch": {
        "patterns": ["CapturedAudioProcessor7Process"],
        "at_start": False,
        "arm64_scan": "arm64_mono_downmix",
    },
    "OpusEncoderConfig_CtorBitrate_B": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev"],
        "at_start": False,
        "arm64_scan": "arm64_bitrate_const",
    },
    "AudioEncoder_BitrateMovImm": {
        "patterns": ["AudioRtpReceiver17SetupMediaChannel",
                     "SetupMediaChannel"],
        "at_start": False,
        "arm64_scan": "arm64_bitrate_or",
    },
    "OpusEncoderConfig_IsOkRetTrue": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev",
                     "AudioEncoderOpus"],
        "at_start": False,
        "arm64_scan": "arm64_opus_config_isok",
    },
    "OpusEncoderConfig_CtorBitrate_A": {
        "patterns": ["AudioEncoderOpusConfigC1Ev", "AudioEncoderOpusConfigC2Ev"],
        "at_start": False,
        "arm64_scan": "arm64_opus_config_init1",
    },
    "CodecProbe_ForceSuccessBranch": {
        "patterns": ["LocalUser16CommitAudioCodecEv"],
        "at_start": False,
        "arm64_scan": "arm64_stereo_success2",
        "prefer_largest": True,
    },
    "SampleRate_Select48kNop": {
        "patterns": ["LocalUser16CommitAudioCodecEv"],
        "at_start": False,
        "arm64_scan": "arm64_emulate_48khz",
        "prefer_largest": True,
    },
    "OpusBitrate_Imul384k": {
        "patterns": ["LocalUser16CommitAudioCodecEv"],
        "at_start": False,
        "arm64_scan": "arm64_bitrate_modified",
        "prefer_largest": True,
    },
    "AudioEncoder_BitrateOrMaskNop": {
        "patterns": ["AudioRtpReceiver17SetupMediaChannel",
                     "SetupMediaChannel"],
        "at_start": False,
        "arm64_scan": "arm64_bitrate_or_insn",
    },
}


def parse_elf(data):
    if len(data) < 64:
        return None

    if data[:4] != b'\x7fELF':
        return None

    ei_class = data[4]
    ei_data = data[5]
    if ei_class != 2 or ei_data != 1:
        if ei_class == 2 and ei_data == 2:
            return None
        if ei_class == 1:
            return None

    e_type = struct.unpack_from('<H', data, 16)[0]
    e_machine = struct.unpack_from('<H', data, 18)[0]
    e_entry = struct.unpack_from('<Q', data, 24)[0]
    e_shoff = struct.unpack_from('<Q', data, 40)[0]
    e_shentsize = struct.unpack_from('<H', data, 58)[0]
    e_shnum = struct.unpack_from('<H', data, 60)[0]
    e_shstrndx = struct.unpack_from('<H', data, 62)[0]

    if e_shoff == 0 or e_shnum == 0:
        return None

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if off + e_shentsize > len(data):
            break
        sh_name_idx = struct.unpack_from('<I', data, off)[0]
        sh_type = struct.unpack_from('<I', data, off + 4)[0]
        sh_flags = struct.unpack_from('<Q', data, off + 8)[0]
        sh_addr = struct.unpack_from('<Q', data, off + 16)[0]
        sh_offset = struct.unpack_from('<Q', data, off + 24)[0]
        sh_size = struct.unpack_from('<Q', data, off + 32)[0]
        sh_link = struct.unpack_from('<I', data, off + 40)[0]
        sh_entsize = struct.unpack_from('<Q', data, off + 56)[0]
        sections.append({
            'name_idx': sh_name_idx, 'type': sh_type, 'flags': sh_flags,
            'vaddr': sh_addr, 'raw_offset': sh_offset, 'raw_size': sh_size,
            'link': sh_link, 'entsize': sh_entsize, 'index': i,
            'name': '',
        })

    if e_shstrndx < len(sections):
        strtab = sections[e_shstrndx]
        strtab_off = strtab['raw_offset']
        strtab_end = strtab_off + strtab['raw_size']
        for sec in sections:
            idx = sec['name_idx']
            name_off = strtab_off + idx
            if name_off < strtab_end:
                end = data.find(b'\x00', name_off, strtab_end)
                if end < 0:
                    end = strtab_end
                sec['name'] = data[name_off:end].decode('ascii', errors='replace')

    text_section = None
    file_offset_adjustment = 0
    for sec in sections:
        if sec['name'] == '.text':
            text_section = sec
            file_offset_adjustment = sec['vaddr'] - sec['raw_offset']
            break

    if text_section is None:
        SHF_EXECINSTR = 0x4
        for sec in sections:
            if sec['flags'] & SHF_EXECINSTR and sec['vaddr'] > 0 and sec['raw_offset'] > 0:
                text_section = sec
                file_offset_adjustment = sec['vaddr'] - sec['raw_offset']
                break

    symbols = []
    SHT_SYMTAB = 2
    SHT_DYNSYM = 11
    for sec in sections:
        if sec['type'] not in (SHT_SYMTAB, SHT_DYNSYM):
            continue
        if sec['entsize'] == 0:
            continue
        if sec['link'] >= len(sections):
            continue
        sym_strtab = sections[sec['link']]
        sym_strtab_off = sym_strtab['raw_offset']
        sym_strtab_end = sym_strtab_off + sym_strtab['raw_size']

        num_syms = sec['raw_size'] // sec['entsize']
        for j in range(num_syms):
            sym_off = sec['raw_offset'] + j * sec['entsize']
            if sym_off + 24 > len(data):
                break
            st_name = struct.unpack_from('<I', data, sym_off)[0]
            st_info = data[sym_off + 4]
            st_shndx = struct.unpack_from('<H', data, sym_off + 6)[0]
            st_value = struct.unpack_from('<Q', data, sym_off + 8)[0]
            st_size = struct.unpack_from('<Q', data, sym_off + 16)[0]

            name_off = sym_strtab_off + st_name
            sym_name = ''
            if name_off < sym_strtab_end:
                end = data.find(b'\x00', name_off, min(name_off + 512, sym_strtab_end))
                if end < 0:
                    end = min(name_off + 512, sym_strtab_end)
                sym_name = data[name_off:end].decode('ascii', errors='replace')

            if sym_name and st_value > 0:
                STT_FUNC = 2
                sym_type = st_info & 0xF
                symbols.append({
                    'name': sym_name,
                    'value': st_value,
                    'size': st_size,
                    'type': sym_type,
                    'is_func': sym_type == STT_FUNC,
                    'section': st_shndx,
                })

    func_symbols = {}
    for sym in symbols:
        if sym['is_func'] and sym['value'] > 0:
            func_symbols[sym['name']] = sym

    arch = 'x86_64' if e_machine == 0x3E else f'machine_{e_machine}'

    return {
        'format': 'elf',
        'image_base': 0,
        'file_offset_adjustment': file_offset_adjustment,
        'text_section': text_section,
        'sections': [{'name': s['name'], 'vaddr': s['vaddr'],
                       'raw_size': s['raw_size'], 'raw_offset': s['raw_offset']}
                      for s in sections if s['name']],
        'symbols': symbols,
        'func_symbols': func_symbols,
        'has_symbols': len(func_symbols) > 50,
        'arch': arch,
        'entry': e_entry,
    }

# endregion ELF Parser


# region Mach-O Parser

def parse_macho(data):
    if len(data) < 32:
        return None

    magic = struct.unpack_from('<I', data, 0)[0]

    FAT_MAGIC = 0xBEBAFECA
    FAT_MAGIC_64 = 0xBFBAFECA
    if magic in (FAT_MAGIC, FAT_MAGIC_64):
        return _parse_fat_macho(data)

    MH_MAGIC_64 = 0xFEEDFACF
    MH_MAGIC_64_BE = 0xCFFAEDFE

    if magic == MH_MAGIC_64:
        return _parse_macho_slice(data, 0)
    elif magic == MH_MAGIC_64_BE:
        return None
    elif struct.unpack_from('>I', data, 0)[0] in (0xCAFEBABE, 0xCAFEBABF):
        return _parse_fat_macho(data)

    return None


def _parse_fat_macho(data):
    nfat_arch = struct.unpack_from('>I', data, 4)[0]
    if nfat_arch > 20:
        return None

    CPU_TYPE_X86_64 = 0x01000007
    CPU_TYPE_ARM64 = 0x0100000C

    x86_result = None
    arm64_offset = None
    arm64_size = None

    for i in range(nfat_arch):
        off = 8 + i * 20
        if off + 20 > len(data):
            break
        cputype = struct.unpack_from('>I', data, off)[0]
        cpusubtype = struct.unpack_from('>I', data, off + 4)[0]
        offset = struct.unpack_from('>I', data, off + 8)[0]
        size = struct.unpack_from('>I', data, off + 12)[0]

        if cputype == CPU_TYPE_X86_64 and offset + size <= len(data):
            result = _parse_macho_slice(data, offset)
            if result:
                result['fat_offset'] = offset
                result['fat_size'] = size
                x86_result = result

        elif cputype == CPU_TYPE_ARM64 and offset + size <= len(data):
            arm64_offset = offset
            arm64_size = size

    if x86_result is not None:
        if arm64_offset is not None:
            arm64_info = _parse_macho_slice(data, arm64_offset)
            if arm64_info:
                arm64_info['fat_offset'] = arm64_offset
                arm64_info['fat_size'] = arm64_size
                x86_result['arm64_info'] = arm64_info
        return x86_result

    if arm64_offset is not None:
        arm64_info = _parse_macho_slice(data, arm64_offset)
        if arm64_info:
            arm64_info['fat_offset'] = arm64_offset
            arm64_info['fat_size'] = arm64_size
            return arm64_info

    return None


def _parse_macho_slice(data, base_offset):
    magic = struct.unpack_from('<I', data, base_offset)[0]
    if magic != 0xFEEDFACF:
        return None

    cputype = struct.unpack_from('<I', data, base_offset + 4)[0]
    ncmds = struct.unpack_from('<I', data, base_offset + 16)[0]
    sizeofcmds = struct.unpack_from('<I', data, base_offset + 20)[0]

    CPU_TYPE_X86_64 = 0x01000007
    CPU_TYPE_ARM64 = 0x0100000C
    if cputype == CPU_TYPE_X86_64:
        arch = 'x86_64'
    elif cputype == CPU_TYPE_ARM64:
        arch = 'arm64'
    else:
        arch = f'cpu_{cputype:#x}'

    LC_SEGMENT_64 = 0x19
    LC_SYMTAB = 0x02

    sections = []
    text_section = None
    file_offset_adjustment = 0
    cmd_offset = base_offset + 32

    symtab_off = 0
    symtab_nsyms = 0
    strtab_off = 0
    strtab_size = 0

    for _ in range(ncmds):
        if cmd_offset + 8 > len(data):
            break
        cmd = struct.unpack_from('<I', data, cmd_offset)[0]
        cmdsize = struct.unpack_from('<I', data, cmd_offset + 4)[0]
        if cmdsize < 8:
            break

        if cmd == LC_SEGMENT_64 and cmd_offset + 72 <= len(data):
            segname = data[cmd_offset + 8:cmd_offset + 24].rstrip(b'\x00').decode('ascii', errors='replace')
            vm_addr = struct.unpack_from('<Q', data, cmd_offset + 24)[0]
            vm_size = struct.unpack_from('<Q', data, cmd_offset + 32)[0]
            file_off = struct.unpack_from('<Q', data, cmd_offset + 40)[0]
            file_size = struct.unpack_from('<Q', data, cmd_offset + 48)[0]
            nsects = struct.unpack_from('<I', data, cmd_offset + 64)[0]

            sec_base = cmd_offset + 72
            for s in range(nsects):
                sec_off = sec_base + s * 80
                if sec_off + 80 > len(data):
                    break
                sectname = data[sec_off:sec_off + 16].rstrip(b'\x00').decode('ascii', errors='replace')
                seg_of_sect = data[sec_off + 16:sec_off + 32].rstrip(b'\x00').decode('ascii', errors='replace')
                s_addr = struct.unpack_from('<Q', data, sec_off + 32)[0]
                s_size = struct.unpack_from('<Q', data, sec_off + 40)[0]
                s_offset = struct.unpack_from('<I', data, sec_off + 48)[0]

                sections.append({
                    'name': f"{seg_of_sect},{sectname}",
                    'vaddr': s_addr,
                    'raw_size': s_size,
                    'raw_offset': s_offset + base_offset,
                })

                if seg_of_sect == '__TEXT' and sectname == '__text':
                    text_section = sections[-1]
                    file_offset_adjustment = s_addr - (s_offset + base_offset)

        elif cmd == LC_SYMTAB and cmd_offset + 24 <= len(data):
            symtab_off = struct.unpack_from('<I', data, cmd_offset + 8)[0] + base_offset
            symtab_nsyms = struct.unpack_from('<I', data, cmd_offset + 12)[0]
            strtab_off = struct.unpack_from('<I', data, cmd_offset + 16)[0] + base_offset
            strtab_size = struct.unpack_from('<I', data, cmd_offset + 20)[0]

        cmd_offset += cmdsize

    func_symbols = {}
    symbols = []
    NLIST_64_SIZE = 16
    if symtab_nsyms > 0 and symtab_off + symtab_nsyms * NLIST_64_SIZE <= len(data):
        strtab_end = strtab_off + strtab_size
        for i in range(min(symtab_nsyms, 200000)):
            noff = symtab_off + i * NLIST_64_SIZE
            if noff + NLIST_64_SIZE > len(data):
                break
            n_strx = struct.unpack_from('<I', data, noff)[0]
            n_type = data[noff + 4]
            n_sect = data[noff + 5]
            n_value = struct.unpack_from('<Q', data, noff + 8)[0]

            name_off = strtab_off + n_strx
            sym_name = ''
            if name_off < strtab_end:
                end = data.find(b'\x00', name_off, min(name_off + 512, strtab_end))
                if end < 0:
                    end = min(name_off + 512, strtab_end)
                sym_name = data[name_off:end].decode('ascii', errors='replace')

            if sym_name and n_value > 0:
                is_defined = (n_type & 0x0e) == 0x0e
                sym = {'name': sym_name, 'value': n_value, 'is_func': is_defined and n_sect > 0, 'size': 0}
                symbols.append(sym)
                if sym['is_func']:
                    func_symbols[sym_name] = sym

    has_symbols = len(func_symbols) > 50

    if has_symbols:
        sorted_funcs = sorted(func_symbols.values(), key=lambda s: s['value'])
        for i, sym in enumerate(sorted_funcs):
            if i + 1 < len(sorted_funcs):
                gap = sorted_funcs[i + 1]['value'] - sym['value']
                sym['size'] = gap if 0 < gap < 0x100000 else 0
            else:
                sym['size'] = 0

    return {
        'format': 'macho',
        'image_base': 0,
        'file_offset_adjustment': file_offset_adjustment,
        'text_section': text_section,
        'sections': sections,
        'symbols': symbols,
        'func_symbols': func_symbols,
        'has_symbols': has_symbols,
        'arch': arch,
    }

# endregion Mach-O Parser


# region macOS Stereo Patch Finder

def _parse_fat_macho_slices(data):
    if len(data) < 32:
        return []
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic not in (0xBEBAFECA, 0xBFBAFECA):
        return []
    nfat = struct.unpack_from(">I", data, 4)[0]
    if nfat > 20:
        return []
    CPU_X86_64, CPU_ARM64 = 0x01000007, 0x0100000C
    slices = []
    for i in range(nfat):
        off = 8 + i * 20
        if off + 20 > len(data):
            break
        cputype = struct.unpack_from(">I", data, off)[0]
        slice_off = struct.unpack_from(">I", data, off + 8)[0]
        slice_size = struct.unpack_from(">I", data, off + 12)[0]
        if cputype == CPU_X86_64 and slice_off + slice_size <= len(data):
            slices.append({"arch": "x86_64", "fat_offset": slice_off, "fat_size": slice_size,
                          "data": data[slice_off : slice_off + slice_size]})
        elif cputype == CPU_ARM64 and slice_off + slice_size <= len(data):
            slices.append({"arch": "arm64", "fat_offset": slice_off, "fat_size": slice_size,
                          "data": data[slice_off : slice_off + slice_size]})
    return slices


def _parse_hex_bytes(s):
    return bytes([int(b, 16) for b in s.split() if b])


_X86_STEREO = [
    {"n": "MultiChannelOpusConfig_channels", "p": "C7 07 14 00 00 00 48 C7 47 08 01 00 00 00", "t": 10, "o": "01", "x": "02"},
    {"n": "MultiChannelOpusConfig_bitrate", "p": "48 B8 00 00 00 00 00 7D 00 00 48 89 47 10 66 C7 47 18", "t": 7, "o": "7D 00", "x": BITRATE_PATCH_3},
    {"n": "OpusConfig_channels", "p": "48 B8 14 00 00 00 80 BB 00 00 48 89 07 48 C7 47 08 01 00 00 00", "t": 17, "o": "01", "x": "02"},
    {"n": "OpusConfig_bitrate", "p": "48 B8 00 00 00 00 00 7D 00 00 48 89 47 10 C6 47 18 01", "t": 7, "o": "7D 00", "x": BITRATE_PATCH_3},
    {"n": "StereoDownmixChannels", "p": "66 0F 1F 44 00 00 55 48 89 E5 41 57 41 56 41 54 53 48 89 F3 48 8B 46 28 48 83 F8 02", "t": 6, "o": "55", "x": "C3"},
    {"n": "StereoDownMixFrame", "p": "84 C0 74 18 49 8B 76 18", "t": 2, "o": "74 18", "x": "90 90"},
    {"n": "StereoApplyAudioNetworkAdaptor", "p": "80 7D D8 01 0F 84 9F 00 00 00", "t": 4, "o": "0F 84 9F 00 00 00", "x": "90 90 90 90 90 90"},
    {"n": "SdpToConfig_channels", "p": "41 BF 01 00 00 00 80 7D C8 01 75", "t": 2, "o": "01", "x": "02"},
    {"n": "SdpToConfig_jne", "p": "41 BF ?? ?? ?? ?? 80 7D C8 01 75", "t": 10, "o": "75", "x": "EB"},
]

_ARM64_STEREO = [
    {"n": "MultiChannelOpusConfig_channels", "p": "28 00 80 52", "t": 0, "o": "28", "x": "48", "occ": 1},
    {"n": "OpusConfig_channels", "p": "28 00 80 52", "t": 0, "o": "28", "x": "48", "occ": 2},
    {"n": "StereoConstBitrate", "p": "00 00 00 00 00 7D 00 00 09", "t": 5, "o": "7D 00", "x": BITRATE_PATCH_3, "occ": 1},
    {"n": "StereoDownmixChannels", "p": "F6 57 BD A9", "t": 0, "o": "F6 57 BD A9", "x": "C0 03 5F D6", "occ": 1},
    {"n": "StereoDownMixFrame", "p": "20 01 00 34", "t": 0, "o": "20 01 00 34", "x": "1F 20 03 D5", "occ": 1},
    {"n": "StereoApplyAudioNetworkAdaptor", "p": "41 01 00 54", "t": 0, "o": "41 01 00 54", "x": "0A 00 00 14", "occ": 1},
    {"n": "SdpToConfig_cinc1", "p": "15 15 88 9A", "t": 0, "o": "15 15 88 9A", "x": "55 00 80 52", "occ": 1},
    {"n": "SdpToConfig_mov1", "p": "35 00 80 52", "t": 0, "o": "35", "x": "55", "occ": 1},
    {"n": "SdpToConfig_cinc2", "p": "15 15 88 9A", "t": 0, "o": "15 15 88 9A", "x": "55 00 80 52", "occ": 2},
    {"n": "SdpToConfig_mov2", "p": "35 00 80 52", "t": 0, "o": "35", "x": "55", "occ": 2},
]

MIN_ARM64_VA = 0x4000


def _find_stereo_x86(slice_info, out):
    d, fo = slice_info["data"], slice_info["fat_offset"]
    seen = {}
    for s in _X86_STEREO:
        pat = Signature._parse(s["p"])
        ms = scan_pattern(d, pat)
        if len(ms) < 1:
            continue
        m = ms[0]
        po = m + s["t"]
        orig = _parse_hex_bytes(s["o"])
        if d[po : po + len(orig)] != orig:
            continue
        ok, conf, val_msgs = _run_patch_site_validation(d, po, s, 0)
        if not ok:
            for vmsg in val_msgs:
                print(f"[warn] {vmsg}")
            print(f"[warn] {s['n']}: validation failed (confidence {conf}), skipping stereo patch")
            continue
        key = (s["n"], 0)
        if key in seen:
            continue
        seen[key] = True
        out.append({"arch": "x86_64", "va": po, "fat_offset": fo + po, "orig": s["o"], "patch": s["x"], "name": s["n"]})


def _find_stereo_arm64(slice_info, out):
    d, fo = slice_info["data"], slice_info["fat_offset"]
    seen = {}
    for s in _ARM64_STEREO:
        pat = Signature._parse(s["p"])
        ms = [x for x in scan_pattern(d, pat) if x >= MIN_ARM64_VA]
        occ = s.get("occ", 1)
        if len(ms) < occ:
            continue
        m = ms[occ - 1]
        po = m + s["t"]
        orig = _parse_hex_bytes(s["o"])
        if d[po : po + len(orig)] != orig:
            continue
        ok, conf, val_msgs = _run_patch_site_validation(d, po, s, 0)
        if not ok:
            for vmsg in val_msgs:
                print(f"[warn] {vmsg}")
            print(f"[warn] {s['n']}: validation failed (confidence {conf}), skipping stereo patch")
            continue
        key = (s["n"], occ)
        if key in seen:
            continue
        seen[key] = True
        out.append({"arch": "arm64", "va": po, "fat_offset": fo + po, "orig": s["o"], "patch": s["x"], "name": s["n"]})


def find_macos_stereo_patches(data):
    slices = _parse_fat_macho_slices(data)
    if not slices:
        return []
    out = []
    for sl in slices:
        if sl["arch"] == "x86_64":
            _find_stereo_x86(sl, out)
        else:
            _find_stereo_arm64(sl, out)
    return out

# endregion macOS Stereo Patch Finder


# region Format Detection

def detect_binary_format(data):
    pe = parse_pe(data)
    if pe:
        pe['format'] = 'pe'
        pe['arch'] = 'x86_64'
        pe['has_symbols'] = False
        pe['func_symbols'] = {}
        pe['symbols'] = []
        return pe
    macho = parse_macho(data)
    if macho:
        return macho
    elf = parse_elf(data)
    if elf:
        return elf
    return {
        'format': 'raw',
        'image_base': 0,
        'file_offset_adjustment': 0,
        'text_section': None,
        'sections': [],
        'arch': 'unknown',
        'has_symbols': False,
        'func_symbols': {},
        'symbols': [],
        'note': 'Could not detect binary format. Using raw scan with adjustment=0.',
    }


def _linux_scan_within_function(data, func_start, func_size, scan_type, adj):
    import struct as _st

    end = min(func_start + func_size, len(data))
    func = data[func_start:end]
    flen = len(func)

    if scan_type == "multichannel_opus_config_channels":
        pat = b"\xC7\x07\x14\x00\x00\x00\x48\xC7\x47\x08"
        for i in range(flen - (len(pat) + 4)):
            if func[i : i + len(pat)] != pat:
                continue
            ch_off = i + len(pat)
            if ch_off < flen and func[ch_off] in (0x01, 0x02):
                return func_start + ch_off + adj
        return None

    if scan_type == "opus_config_channels":
        for i in range(flen - 24):
            if (func[i:i+2] == b'\x48\xb8'
                    and func[i+2] == 0x14 and func[i+6:i+10] == b'\x80\xbb\x00\x00'):
                ch_off = i + 0x15
                if ch_off < flen and func[ch_off] in (0x01, 0x02):
                    return func_start + ch_off + adj
        return None

    if scan_type == "opus_config_bitrate":
        for i in range(flen - 10):
            if (func[i:i+2] == b'\x48\xb8'
                    and func[i+2:i+7] == b'\x00\x00\x00\x00\x00'
                    and func[i+7:i+10] == b'\x7d\x00\x00'):
                target_off = i + 5
                if func[target_off:target_off+4] == b'\x00\x7d\x00\x00':
                    return func_start + target_off + adj
        return None

    if scan_type == "stereo_cmp_byte":
        def _is_stereo_cmp(buf, pos, buflen):
            if pos + 8 > buflen:
                return False, 0, 0
            if buf[pos] != 0x80:
                return False, 0, 0
            modrm = buf[pos + 1]
            if not (0xB8 <= modrm <= 0xBF):
                return False, 0, 0
            if (modrm & 7) == 4:
                return False, 0, 0
            val = buf[pos + 6]
            if val not in (0x00, 0x01):
                return False, 0, 0
            jcc_byte = buf[pos + 7]
            if jcc_byte not in (0x74, 0x75, 0x0F):
                return False, 0, 0
            if jcc_byte == 0x0F and pos + 9 <= buflen:
                if buf[pos + 8] not in (0x84, 0x85):
                    return False, 0, 0
            member_off = _st.unpack_from('<I', buf, pos + 2)[0]
            if not (0x100 < member_off < 0x1000):
                return False, 0, 0
            return True, modrm, member_off

        for i in range(flen - 8):
            ok, modrm, member_off = _is_stereo_cmp(func, i, flen)
            if not ok:
                continue
            off_bytes = func[i+2:i+6]
            setter_modrm = 0x80 | (modrm & 7)
            setter = bytes([0xC6, setter_modrm]) + off_bytes + b'\x01'
            search_start = i + 8
            search_end = min(i + 56, flen)
            if setter in func[search_start:search_end]:
                return func_start + i + 6 + adj
        for i in range(flen - 8):
            ok, modrm, member_off = _is_stereo_cmp(func, i, flen)
            if ok:
                return func_start + i + 6 + adj
        return None

    if scan_type == "stereo_success2_byte":
        found_first = False
        for i in range(flen - 8):
            if func[i] != 0x80:
                continue
            modrm = func[i + 1]
            if not (0xB8 <= modrm <= 0xBF) or (modrm & 7) == 4:
                continue
            val = func[i + 6]
            jcc_byte = func[i + 7]
            if val not in (0x00, 0x01):
                continue
            if jcc_byte not in (0x74, 0x75, 0x0F):
                continue
            if jcc_byte == 0x0F and i + 9 <= flen:
                if func[i + 8] not in (0x84, 0x85):
                    continue
            member_off = _st.unpack_from('<I', func, i + 2)[0]
            if not (0x100 < member_off < 0x1000):
                continue
            if not found_first:
                found_first = True
                continue
            return func_start + i + 7 + adj
        return None

    if scan_type == "emulate_48khz_cmov":
        for i in range(flen - 16):
            if func[i] == 0x83 and 0xB8 <= func[i+1] <= 0xBF:
                if (func[i+1] & 7) == 4:
                    continue
                disp = _st.unpack_from('<I', func, i+2)[0]
                if 0x40 < disp < 0x1000 and func[i+6] == 0x02:
                    for j in range(7, 20):
                        if i + j + 4 > flen:
                            break
                        b0 = func[i + j]
                        b1 = func[i + j + 1]
                        if b0 == 0x0F and 0x40 <= b1 <= 0x4F:
                            return func_start + i + j + adj
                        if b0 == 0x48 and b1 == 0x0F and i + j + 2 < flen:
                            if 0x40 <= func[i + j + 2] <= 0x4F:
                                return func_start + i + j + adj
            if func[i] == 0x41 and func[i+1] == 0x83 and i+8 <= flen:
                if 0xB8 <= func[i+2] <= 0xBF and (func[i+2] & 7) != 4:
                    disp = _st.unpack_from('<I', func, i+3)[0]
                    if 0x40 < disp < 0x1000 and func[i+7] == 0x02:
                        for j in range(8, 24):
                            if i + j + 4 > flen:
                                break
                            b0 = func[i + j]
                            b1 = func[i + j + 1]
                            if b0 == 0x0F and 0x40 <= b1 <= 0x4F:
                                return func_start + i + j + adj
                            if b0 == 0x48 and b1 == 0x0F and i + j + 2 < flen:
                                if 0x40 <= func[i + j + 2] <= 0x4F:
                                    return func_start + i + j + adj
        for i in range(flen - 12):
            if func[i:i+3] == b'\x48\x8d\x05' or func[i:i+3] == b'\x48\x8d\x15':
                for j in range(7, 24):
                    if i + j + 4 > flen:
                        break
                    if func[i+j] == 0x48 and func[i+j+1] == 0x0F:
                        if 0x40 <= func[i+j+2] <= 0x4F:
                            return func_start + i + j + adj
        return None

    if scan_type == "channel_cmov":
        for i in range(flen - 40):
            if func[i:i+5] == b'\xb8\x80\xbb\x00\x00':
                for j in range(5, 40):
                    if i+j+4 <= flen and func[i+j:i+j+3] == b'\x4c\x0f\x43':
                        return func_start + i + j + adj
        return None

    if scan_type == "bitrate_movabs_or":
        for i in range(flen - 16):
            if (func[i:i+2] == b'\x48\xb9'
                    and func[i+6:i+10] == b'\x01\x00\x00\x00'
                    and func[i+10:i+13] == b'\x48\x09\xc1'):
                return func_start + i + 2 + adj
        return None

    if scan_type == "mono_downmix_test":
        def _mono_match_at(i):
            if func[i:i+2] != b'\x84\xc0' or func[i+2] != 0x74:
                return None
            cmp_start = i + 4
            if cmp_start >= flen - 4 or func[cmp_start] != 0x83:
                return None
            modrm = func[cmp_start + 1]
            if ((modrm >> 3) & 7) != 7:
                return None
            mod = modrm >> 6
            if mod == 1 and cmp_start + 4 <= flen:
                imm_off = cmp_start + 3
            elif mod == 2 and cmp_start + 7 <= flen:
                imm_off = cmp_start + 6
            else:
                return None
            if func[imm_off] != 0x09:
                return None
            jg_off = imm_off + 1
            if jg_off >= flen:
                return None
            j0 = func[jg_off]
            if j0 == 0x0F and jg_off + 1 < flen and func[jg_off + 1] in (0x8F, 0x8D):
                return ("near", func_start + i + adj)
            if j0 in (0x7F, 0x7D):
                return ("short", func_start + i + adj)
            return None

        short_best = None
        for i in range(flen - 8):
            m = _mono_match_at(i)
            if not m:
                continue
            kind, off = m
            if kind == "near":
                return off
            short_best = off
        return short_best

    return None


def _arm64_scan_within_function(data, func_start, func_size, scan_type, adj):
    end = min(func_start + func_size, len(data))
    func = data[func_start:end]
    flen = len(func)
    if flen < 8:
        return None

    def _read32(buf, off):
        return struct.unpack_from('<I', buf, off)[0]

    def _is_movz_w(raw, imm16):
        return (raw & _ARM64_MOVZ_W_MASK) == (0x52800000 | (imm16 << 5))

    if scan_type == "arm64_channel_movz":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 48000):
                for j in range(4, min(256, i + 4), 4):
                    r2 = _read32(func, i - j)
                    if _is_movz_w(r2, 1):
                        return func_start + (i - j) + adj
                for j in range(4, min(256, flen - i), 4):
                    r2 = _read32(func, i + j)
                    if _is_movz_w(r2, 1):
                        return func_start + (i + j) + adj
        return None

    if scan_type == "arm64_opus_config_channels":
        candidates = []
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 48000) or _is_movz_w(raw, 960):
                for j in range(-128, 128, 4):
                    off2 = i + j
                    if 0 <= off2 < flen - 4:
                        r2 = _read32(func, off2)
                        if _is_movz_w(r2, 1):
                            if off2 + 4 < flen - 4:
                                next_raw = _read32(func, off2 + 4)
                                is_store = (next_raw & 0x3B000000) == 0x39000000 and not ((next_raw >> 22) & 1)
                                is_stp = (next_raw & 0x7FC00000) == 0x29000000
                                if is_store or is_stp:
                                    candidates.append(off2)
        if candidates:
            return func_start + candidates[0] + adj
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 1):
                return func_start + i + adj
        return None

    if scan_type == "arm64_stereo_cmp":
        for i in range(0, flen - 12, 4):
            raw = _read32(func, i)
            if (raw & 0xFFC00000) != 0x39400000:
                continue
            imm12 = (raw >> 10) & 0xFFF
            rt = raw & 0x1F
            if not (0x100 <= imm12 <= 0x1000):
                continue
            next_raw = _read32(func, i + 4)
            next_rt = next_raw & 0x1F
            if (next_raw & 0x7F000000) == 0x34000000 and next_rt == rt:
                return func_start + i + adj
            if (next_raw & 0x7E000000) == 0x36000000 and next_rt == rt:
                return func_start + i + adj
            if (next_raw & 0xFF000000) == 0x71000000:
                subs_rn = (next_raw >> 5) & 0x1F
                subs_rd = next_raw & 0x1F
                if subs_rn == rt and subs_rd == 0x1F and i + 8 < flen:
                    third = _read32(func, i + 8)
                    if (third & 0xFF000010) == 0x54000000:
                        return func_start + i + adj
        return None

    if scan_type == "arm64_stereo_success2":
        found_first = False
        for i in range(0, flen - 12, 4):
            raw = _read32(func, i)
            if (raw & 0xFFC00000) != 0x39400000:
                continue
            imm12 = (raw >> 10) & 0xFFF
            rt = raw & 0x1F
            if not (0x100 <= imm12 <= 0x1000):
                continue
            next_raw = _read32(func, i + 4)
            next_rt = next_raw & 0x1F
            branch_off = None
            if (next_raw & 0x7F000000) == 0x34000000 and next_rt == rt:
                branch_off = i + 4
            elif (next_raw & 0x7E000000) == 0x36000000 and next_rt == rt:
                branch_off = i + 4
            elif (next_raw & 0xFF000000) == 0x71000000:
                subs_rn = (next_raw >> 5) & 0x1F
                if subs_rn == rt and (next_raw & 0x1F) == 0x1F and i + 8 < flen:
                    third = _read32(func, i + 8)
                    if (third & 0xFF000010) == 0x54000000:
                        branch_off = i + 8
            if branch_off is not None:
                if not found_first:
                    found_first = True
                    continue
                return func_start + branch_off + adj
        return None

    if scan_type == "arm64_emulate_48khz":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if (raw & 0xFFE00C00) in (0x1A800000, 0x1A800400):
                return func_start + i + adj
        return None

    if scan_type == "arm64_bitrate_modified":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 32000):
                return func_start + i + adj
        literal_32000 = struct.pack('<I', 32000)
        search_end = min(func_start + flen + 2048, len(data) - 4)
        for i in range(func_start, search_end - 3):
            if data[i:i + 4] == literal_32000:
                return i + adj
        return None

    if scan_type == "arm64_bitrate_const":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 32000):
                return func_start + i + adj
        channels_off = None
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 1):
                channels_off = i
                break
        if channels_off is not None:
            for i in range(channels_off + 8, flen - 4, 4):
                raw = _read32(func, i)
                if (raw & 0xFF800000) == 0x52800000:
                    imm16 = (raw >> 5) & 0xFFFF
                    if imm16 > 100:
                        return func_start + i + adj
        return None

    if scan_type == "arm64_bitrate_or":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if (raw & 0xFFFFFC00) == 0xB2600000:
                return func_start + i + adj
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if (raw & 0xFFE0FFE0) == 0xF2A00020:
                return func_start + i + adj
        return None

    if scan_type == "arm64_bitrate_or_insn":
        for i in range(0, flen - 8, 4):
            raw = _read32(func, i)
            if (raw & 0xFFFFFC00) == 0xB2600000:
                return func_start + (i + 4) + adj
        return None

    if scan_type == "arm64_opus_config_isok":
        for i in range(0, flen - 8, 4):
            raw = _read32(func, i)
            if (raw & 0xFFC003E0) == 0xB9400000:
                next_raw = _read32(func, i + 4)
                if (next_raw & 0xFF000000) == 0x71000000:
                    return func_start + i + adj
                if (next_raw & 0xFFE0FFE0) == 0x2A0003E0:
                    return func_start + i + adj
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if (raw & 0xFF800000) == 0x12800000:
                return func_start + i + adj
        return None

    if scan_type == "arm64_opus_config_init1":
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if _is_movz_w(raw, 48000):
                return func_start + i + adj
        for i in range(0, flen - 4, 4):
            raw = _read32(func, i)
            if (raw & 0x9F000000) == 0x90000000:
                return func_start + i + adj
        return None

    if scan_type == "arm64_mono_downmix":
        for i in range(0, flen - 12, 4):
            raw = _read32(func, i)
            is_cbz = (raw & 0x7F000000) == 0x34000000
            is_tbz = (raw & 0x7E000000) == 0x36000000
            if not (is_cbz or is_tbz):
                continue
            for j in range(4, min(24, flen - i), 4):
                r2 = _read32(func, i + j)
                if (r2 & 0xFFFFFC1F) == 0x7100241F:
                    return func_start + i + adj
        return None

    return None


def _resolve_elf_symbols(bin_info, data):
    if not bin_info.get('has_symbols') or not bin_info.get('func_symbols'):
        return {}, []

    func_syms = bin_info['func_symbols']
    adj = bin_info['file_offset_adjustment']
    resolved = {}
    details = []

    for offset_name, mapping in ELF_SYMBOL_MAP.items():
        candidates = []
        for pattern in mapping['patterns']:
            for sym_name, sym in func_syms.items():
                if pattern.lower() in sym_name.lower():
                    candidates.append(sym)

        if not candidates:
            continue

        if mapping.get('exclude_patterns'):
            candidates = [c for c in candidates
                          if not any(ep in c['name'] for ep in mapping['exclude_patterns'])]
            if not candidates:
                continue

        if mapping.get('prefer_smallest'):
            candidates.sort(key=lambda c: c.get('size', 0x10000))
        elif mapping.get('prefer_largest'):
            candidates.sort(key=lambda c: c.get('size', 0), reverse=True)

        best = candidates[0]
        for c in candidates:
            if any(p.lower() == c['name'].lower().rstrip('_') for p in mapping['patterns']):
                best = c
                break

        sym_addr = best['value']

        if mapping['at_start']:
            file_off = sym_addr - adj
            if 0 <= file_off < len(data):
                resolved[offset_name] = sym_addr
                details.append((offset_name, sym_addr, best['name'], 'symbol-direct'))
        else:
            linux_scan = mapping.get('linux_scan')
            scan_found = False
            for candidate in candidates:
                func_size = candidate.get('size', 0)
                if func_size == 0 or func_size > 0x10000:
                    func_size = 0x2000

                func_file_start = candidate['value'] - adj
                if func_file_start < 0:
                    func_file_start = 0

                if linux_scan:
                    result = _linux_scan_within_function(
                        data, func_file_start, func_size, linux_scan, adj)
                    if result is not None:
                        resolved[offset_name] = result
                        details.append((offset_name, result, candidate['name'], 'symbol+scan'))
                        scan_found = True
                        break

            if not scan_found:
                func_size = best.get('size', 0)
                if func_size == 0 or func_size > 0x10000:
                    func_size = 0x2000
                func_file_start = sym_addr - adj
                if func_file_start < 0:
                    func_file_start = 0

                if linux_scan:
                    func_file_end = min(func_file_start + func_size, len(data))
                    resolved[f"_symhint_{offset_name}"] = (
                        func_file_start, func_file_end, best['name'])
                    details.append((offset_name, sym_addr, best['name'],
                                    'symbol-range-hint'))
                else:
                    func_file_end = min(func_file_start + func_size, len(data))
                    resolved[f"_symhint_{offset_name}"] = (
                        func_file_start, func_file_end, best['name'])
                    details.append((offset_name, sym_addr, best['name'],
                                    'symbol-range-hint'))

    return resolved, details

# endregion Format Detection


# region Signature Scanner

def scan_pattern(data, pattern, limit=0, start=0, end=None):
    matches = []
    pat_len = len(pattern)
    if end is None:
        end = len(data)

    first_fixed = None
    for i, b in enumerate(pattern):
        if b is not None:
            first_fixed = (i, b)
            break

    if first_fixed is None:
        return matches

    skip_to, first_byte = first_fixed
    needle = bytes([first_byte])
    pos = start

    while pos <= end - pat_len:
        idx = data.find(needle, pos + skip_to, end)
        if idx < 0:
            break

        candidate = idx - skip_to
        if candidate < start:
            pos = idx + 1
            continue

        if candidate + pat_len > end:
            break

        match = True
        for j, p in enumerate(pattern):
            if p is not None and data[candidate + j] != p:
                match = False
                break

        if match:
            matches.append(candidate)
            if 0 < limit <= len(matches):
                return matches

        pos = candidate + 1

    return matches


def find_offset(data, sig, text_start=0, text_end=None):

    tiers = [(sig.pattern, sig.target_offset, "primary")]
    for i, (p, o) in enumerate(sig.alt_patterns):
        tiers.append((p, o, f"relaxed-{i+1}"))

    for pattern, target_off, tier in tiers:
        matches = scan_pattern(data, pattern, start=text_start, end=text_end)

        if len(matches) == 0:
            continue

        if len(matches) == 1:
            file_offset = matches[0] + target_off
            if 0 <= file_offset < len(data):
                if sig.name == "CodecProbe_ChannelCountPatch" and not has_nearby_stereo_setter(data, matches[0], 120):
                    print(f"  [FILTER] CodecProbe_ChannelCountPatch @ 0x{matches[0]:X} has no nearby stereo setter (accepting anyway)")
                return file_offset, None, tier

        resolved = list(matches)
        if sig.disambiguator and len(resolved) > 1:
            valid = [m for m in resolved if sig.disambiguator(data, m)]
            if len(valid) >= 1:
                resolved = valid

        if sig.name == "CodecProbe_ChannelCountPatch" and len(resolved) >= 1:
            resolved = [m for m in resolved if _ess1_no_duplicate_cmp_in_next_24(data, m)]
            if not resolved:
                continue
        if sig.name == "CodecProbe_ChannelCountPatch" and len(resolved) >= 1:
            with_setter = [m for m in resolved if has_nearby_stereo_setter(data, m, 120)]
            if len(resolved) > 1 and len(with_setter) >= 1:
                for m in resolved:
                    if m not in with_setter:
                        print(f"  [FILTER] Rejected CodecProbe_ChannelCountPatch @ 0x{m:X} — no nearby stereo setter")
                resolved = with_setter
            elif len(resolved) == 1 and not with_setter:
                print(f"  [FILTER] CodecProbe_ChannelCountPatch @ 0x{resolved[0]:X} has no nearby stereo setter (accepting anyway)")

        if len(resolved) > 1 and sig.expected_original:
            expected = bytes.fromhex(sig.expected_original.replace(' ', ''))
            valid = []
            for m in resolved:
                tf = m + target_off
                if 0 <= tf and tf + len(expected) <= len(data):
                    if data[tf:tf+len(expected)] == expected:
                        valid.append(m)
            if len(valid) >= 1:
                resolved = valid

        if len(resolved) > 1 and sig.patch_bytes and not sig.patch_bytes.startswith('<'):
            patched = bytes.fromhex(sig.patch_bytes.replace(' ', ''))
            valid = []
            for m in resolved:
                tf = m + target_off
                if 0 <= tf and tf + len(patched) <= len(data):
                    if data[tf:tf+len(patched)] == patched:
                        valid.append(m)
            if len(valid) >= 1:
                resolved = valid

        if len(resolved) == 1:
            file_offset = resolved[0] + target_off
            if 0 <= file_offset < len(data):
                return file_offset, None, tier
        elif len(resolved) > 1:
            if tier != "primary":
                file_offset = resolved[0] + target_off
                if 0 <= file_offset < len(data):
                    return file_offset, None, f"{tier}(ambig:{len(resolved)})"

    return None, f"no matches across {len(tiers)} tier(s)", "none"


# endregion Signature Scanner


# region Patch Safety and Heuristics

CONFIDENCE_THRESHOLD = 75
CONFIDENCE_SIGNATURE_MATCH = 50
CONFIDENCE_CONTEXT_VALID = 25
CONFIDENCE_ORIGINAL_BYTES = 25
CONFIDENCE_FINGERPRINT_MATCH = 20
CONFIDENCE_HEURISTIC_PATTERN = 15

_OPCODE_PREFIXES = (0x66, 0xF2, 0xF3, 0x2E, 0x3E, 0x26, 0x64, 0x65, 0x36)
_COMMON_OPCODES = (0x48, 0x49, 0x4C, 0x4D, 0x55, 0x53, 0x56, 0x57, 0x41, 0xC3,
                   0x89, 0x8B, 0xB8, 0xB9, 0xC7, 0xE8, 0xE9, 0x74, 0x75, 0x0F)


def validate_context(binary_data, offset, expected_prefix=None, expected_suffix=None):
    if not isinstance(binary_data, (bytes, bytearray)):
        return False
    n = len(binary_data)
    if offset < 0 or offset >= n:
        return False
    before = min(32, offset)
    after = min(32, n - offset)
    if before < 16 or after < 16:
        return False
    pre = binary_data[offset - before:offset]
    suf = binary_data[offset:offset + after]
    if pre == b'\x00' * len(pre) or pre == b'\xff' * len(pre):
        return False
    if suf == b'\x00' * len(suf) or suf == b'\xff' * len(suf):
        return False
    is_arm64 = False
    if offset % 4 == 0 and len(pre) >= 16:
        arm64_like = 0
        for i in range(0, min(16, len(pre)) - 3, 4):
            top_byte = pre[i + 3]
            if top_byte in (0xD6, 0xF9, 0xA9, 0x52, 0x72, 0xB9, 0x91, 0xD2,
                            0x94, 0x97, 0x54, 0x36, 0x37, 0x34, 0x35, 0x14,
                            0x17, 0xAA, 0x2A, 0x6B, 0xEB, 0x71, 0xF1):
                arm64_like += 1
        if arm64_like >= 2:
            is_arm64 = True
    if is_arm64:
        arm_valid = 0
        for i in range(0, min(16, len(pre)) - 3, 4):
            word = struct.unpack_from('<I', pre, i)[0]
            top4 = (word >> 28) & 0xF
            if top4 in (0x0, 0x1, 0x2, 0x3, 0x5, 0x6, 0x7, 0x9, 0xA, 0xB, 0xD, 0xF):
                arm_valid += 1
        return arm_valid >= 2
    opcode_like = sum(1 for b in pre[-16:] if b in _COMMON_OPCODES or b in _OPCODE_PREFIXES)
    if opcode_like < 2:
        return False
    if expected_prefix is not None:
        exp = expected_prefix if isinstance(expected_prefix, bytes) else bytes.fromhex(expected_prefix.replace(' ', ''))
        if len(exp) > 0 and len(suf) >= len(exp) and suf[:len(exp)] != exp:
            return False
    if expected_suffix is not None:
        exp = expected_suffix if isinstance(expected_suffix, bytes) else bytes.fromhex(expected_suffix.replace(' ', ''))
        if len(exp) > 0 and len(pre) >= len(exp) and pre[-len(exp):] != exp:
            return False
    return True


def compute_function_fingerprint(binary_data, offset, window=96):
    n = len(binary_data)
    if offset < 0 or offset >= n:
        return ""
    half = window // 2
    start = max(0, offset - half)
    end = min(n, offset + half)
    if end - start < 16:
        return ""
    region = bytearray(binary_data[start:end])
    rlen = len(region)
    i = 0
    while i < rlen - 2:
        b0 = region[i]
        b1 = region[i + 1] if i + 1 < rlen else 0
        if 0xB8 <= b0 <= 0xBF and i + 5 <= rlen:
            for j in range(1, 5):
                region[i + j] = 0
            i += 5
            continue
        if b0 == 0x48 and 0xB8 <= b1 <= 0xBF and i + 10 <= rlen:
            for j in range(2, 10):
                region[i + j] = 0
            i += 10
            continue
        if b0 in (0xE8, 0xE9) and i + 5 <= rlen:
            for j in range(1, 5):
                region[i + j] = 0
            i += 5
            continue
        if b0 == 0xEB or (0x70 <= b0 <= 0x7F):
            if i + 2 <= rlen:
                region[i + 1] = 0
            i += 2
            continue
        if b0 == 0x48 and b1 == 0xC7 and i + 7 <= rlen:
            for j in range(3, 7):
                if i + j < rlen:
                    region[i + j] = 0
            i += 7
            continue
        if b0 in (0x48, 0x4C) and b1 == 0x8D and i + 6 <= rlen:
            for j in range(3, min(7, rlen - i)):
                region[i + j] = 0
            i += 7
            continue
        if b0 == 0x0F and 0x80 <= b1 <= 0x8F and i + 6 <= rlen:
            for j in range(2, 6):
                region[i + j] = 0
            i += 6
            continue
        i += 1
    return hashlib.sha1(bytes(region)).hexdigest()


def _detect_function_boundary(binary_data, offset, direction=-1, max_scan=512):
    n = len(binary_data)
    if offset < 0 or offset >= n:
        return None, 0


    if direction < 0:
        start = max(0, offset - max_scan)
        for i in range(offset - 1, start, -1):
            b = binary_data[i]
            if b == 0xCC and i + 4 <= n:
                run = 0
                for j in range(i, min(i + 8, n)):
                    if binary_data[j] == 0xCC:
                        run += 1
                    else:
                        break
                if run >= 3:
                    boundary = i + run
                    if boundary <= offset:
                        return boundary, 8
            if b == 0xC3 and i + 2 <= n:
                nxt = binary_data[i + 1]
                if nxt in (0x90, 0x66, 0x0F, 0xCC):
                    boundary = i + 1
                    while boundary < n and binary_data[boundary] in (0x90, 0xCC):
                        boundary += 1
                    if boundary <= offset:
                        return boundary, 6
        return None, 0
    else:
        end = min(n, offset + max_scan)
        for i in range(offset, end):
            b = binary_data[i]
            if b == 0xC3 and i > offset + 4:
                if i + 1 < n and binary_data[i + 1] in (0xCC, 0x90, 0x66, 0x0F):
                    return i, 7
                if i + 1 < n and binary_data[i + 1] in (0x55, 0x56, 0x57, 0x41, 0x53):
                    return i, 5
            if b == 0xCC and i + 3 < n:
                if binary_data[i + 1] == 0xCC and binary_data[i + 2] == 0xCC:
                    return i, 7
        return None, 0


def _estimate_instruction_flow(binary_data, offset, count=8):
    n = len(binary_data)
    pos = offset
    valid = 0
    checked = 0

    rex_range = range(0x40, 0x50)
    mandatory_prefixes = (0x66, 0xF2, 0xF3)
    _LEN_HINTS = {
        0x50: (1, 1), 0x51: (1, 1), 0x52: (1, 1), 0x53: (1, 1),
        0x54: (1, 1), 0x55: (1, 1), 0x56: (1, 1), 0x57: (1, 1),
        0x58: (1, 1), 0x59: (1, 1), 0x5A: (1, 1), 0x5B: (1, 1),
        0x5C: (1, 1), 0x5D: (1, 1), 0x5E: (1, 1), 0x5F: (1, 1),
        0x90: (1, 1), 0xC3: (1, 1), 0xCC: (1, 1), 0xCB: (1, 1),
        0xC9: (1, 1),
        0xE8: (5, 5), 0xE9: (5, 5),
        0xEB: (2, 2),
        0x74: (2, 2), 0x75: (2, 2), 0x70: (2, 2), 0x71: (2, 2),
        0x72: (2, 2), 0x73: (2, 2), 0x76: (2, 2), 0x77: (2, 2),
        0x78: (2, 2), 0x79: (2, 2), 0x7A: (2, 2), 0x7B: (2, 2),
        0x7C: (2, 2), 0x7D: (2, 2), 0x7E: (2, 2), 0x7F: (2, 2),
        0xB8: (5, 5), 0xB9: (5, 5), 0xBA: (5, 5), 0xBB: (5, 5),
        0xBC: (5, 5), 0xBD: (5, 5), 0xBE: (5, 5), 0xBF: (5, 5),
    }

    while checked < count and pos < n - 1:
        b0 = binary_data[pos]
        step = 0

        adj_pos = pos
        if b0 in rex_range:
            adj_pos += 1
            if adj_pos >= n:
                break
            b0_inner = binary_data[adj_pos]
        else:
            b0_inner = b0

        if b0_inner in _LEN_HINTS:
            mn, mx = _LEN_HINTS[b0_inner]
            step = mn + (adj_pos - pos)
            valid += 1
        elif b0 in mandatory_prefixes or b0 in rex_range:
            step = 3
            valid += 1
        elif b0 in (0x0F,):
            step = 3
            valid += 1
        elif b0 in _COMMON_OPCODES or b0 in _OPCODE_PREFIXES:
            step = 2
            valid += 1
        else:
            step = 2

        checked += 1
        pos += max(step, 1)

    return valid, checked


def run_heuristic_analysis(binary_data, offset, patch_len=4):
    if offset < 32 or offset + 32 > len(binary_data):
        return False, 0
    score = 0
    pre = binary_data[offset - 24:offset]
    suf = binary_data[offset:offset + 24]

    bound_start, bound_conf = _detect_function_boundary(binary_data, offset, direction=-1, max_scan=1024)
    if bound_start is not None:
        dist = offset - bound_start
        if dist < 4096:
            score += 3
    bound_end, end_conf = _detect_function_boundary(binary_data, offset, direction=+1, max_scan=1024)
    if bound_end is not None:
        dist = bound_end - offset
        if dist < 4096:
            score += 2

    valid_insns, checked = _estimate_instruction_flow(binary_data, max(0, offset - 16), count=6)
    if checked > 0 and valid_insns >= (checked * 2 // 3):
        score += 3
    valid_after, checked_after = _estimate_instruction_flow(binary_data, offset, count=6)
    if checked_after > 0 and valid_after >= (checked_after * 2 // 3):
        score += 2

    if pre[-1] in (0x55, 0x53, 0x56, 0x57):
        score += 2
    if len(pre) >= 3 and pre[-3] == 0x48 and pre[-2] == 0x83 and pre[-1] == 0xEC:
        score += 2
    for i in range(len(pre) - 4):
        if pre[i:i+4] == b'\x55\x48\x89\xe5':
            score += 2
            break

    for i in range(len(pre) - 2):
        if pre[i] in (0x48, 0x49, 0x4C) and pre[i + 1] in (0x89, 0x8B, 0xC7, 0x09, 0x01):
            score += 2
            break

    for i in range(min(16, len(suf) - 1)):
        if suf[i] == 0xC3:
            score += 2
            break
        if suf[i] in (0x74, 0x75, 0x0F) and i + 1 < len(suf):
            score += 1
            break

    region = binary_data[max(0, offset - 32):min(len(binary_data), offset + 32)]
    opcode_hits = sum(1 for b in region if b in _COMMON_OPCODES or b in _OPCODE_PREFIXES)
    density = opcode_hits / max(len(region), 1)
    if density > 0.15:
        score += 2

    return score >= 5, min(15, score)


def calculate_confidence(signature_match, context_valid, original_bytes_match,
                         fingerprint_match, heuristic_score):
    total = 0
    if signature_match:
        total += CONFIDENCE_SIGNATURE_MATCH
    if context_valid:
        total += CONFIDENCE_CONTEXT_VALID
    if original_bytes_match:
        total += CONFIDENCE_ORIGINAL_BYTES
    if fingerprint_match:
        total += CONFIDENCE_FINGERPRINT_MATCH
    total += min(CONFIDENCE_HEURISTIC_PATTERN, heuristic_score)
    return total


def validate_patch_site(binary_data, offset, expected_original_bytes, patch_bytes,
                        patch_name="", known_fingerprints=None, expected_prefix=None,
                        expected_suffix=None):
    messages = []
    if offset < 0 or offset >= len(binary_data):
        return False, 0, ["offset out of bounds"]
    if isinstance(expected_original_bytes, str):
        exp_orig = bytes.fromhex(expected_original_bytes.replace(' ', '')) if expected_original_bytes.strip() else b''
    else:
        exp_orig = expected_original_bytes or b''
    if isinstance(patch_bytes, str):
        patch_b = bytes.fromhex(patch_bytes.replace(' ', '')) if patch_bytes.strip() else b''
    else:
        patch_b = patch_bytes or b''
    read_len = max(len(exp_orig), len(patch_b), 1)
    if offset + read_len > len(binary_data):
        return False, 0, ["patch region exceeds binary size"]
    current = binary_data[offset:offset + read_len]
    orig_match = True
    if len(exp_orig) > 0:
        if current[:len(exp_orig)] != exp_orig:
            orig_match = False
            messages.append("unexpected bytes at patch location")
    ctx_ok = validate_context(binary_data, offset, expected_prefix, expected_suffix)
    if not ctx_ok:
        messages.append("context validation failed")
    fp = compute_function_fingerprint(binary_data, offset)
    fp_match = False
    if known_fingerprints and fp and fp in known_fingerprints:
        fp_match = True
    elif known_fingerprints and fp:
        messages.append("fingerprint mismatch")
    heur_ok, heur_score = run_heuristic_analysis(binary_data, offset, len(patch_b))
    if orig_match and len(exp_orig) > 0:
        heur_ok, heur_score = True, CONFIDENCE_HEURISTIC_PATTERN
    elif not heur_ok:
        messages.append("heuristic analysis uncertain")
    conf = calculate_confidence(True, ctx_ok, orig_match, fp_match, heur_score)
    ok = conf >= CONFIDENCE_THRESHOLD
    return ok, conf, messages


def _run_patch_site_validation(data, file_offset, sig_or_dict, adj=0):
    if hasattr(sig_or_dict, 'expected_original') and hasattr(sig_or_dict, 'patch_bytes'):
        exp = sig_or_dict.expected_original or ''
        patch = sig_or_dict.patch_bytes or ''
        name = getattr(sig_or_dict, 'name', '')
    else:
        exp = sig_or_dict.get('o', '') or ''
        patch = sig_or_dict.get('x', '') or ''
        name = sig_or_dict.get('n', '') or ''
    if patch.startswith('<'):
        return True, 100, []
    if not exp and not patch:
        return True, 100, []
    try:
        exp_b = bytes.fromhex(exp.replace(' ', '')) if exp.strip() else b''
    except ValueError:
        exp_b = b''
    try:
        patch_b = bytes.fromhex(patch.replace(' ', '')) if patch.strip() else b''
    except ValueError:
        patch_b = b''
    if not exp_b and not patch_b:
        return True, 100, []
    if file_offset < 0 or file_offset >= len(data):
        return False, 0, ["offset out of bounds"]
    read_len = max(len(exp_b), len(patch_b))
    if file_offset + read_len > len(data):
        return False, 0, ["patch region exceeds binary size"]
    ok, conf, msgs = validate_patch_site(data, file_offset, exp_b or patch_b, patch_b or exp_b,
                                          patch_name=name)
    return ok, conf, msgs


# endregion Patch Safety and Heuristics


# region Offset Discovery Engine

def _topo_sort_derivations(derivations):
    all_derived = set(derivations.keys())
    order = []
    visited = set()

    def visit(name):
        if name in visited:
            return
        visited.add(name)
        if name in derivations:
            for anchor, _delta in derivations[name]:
                if anchor in all_derived:
                    visit(anchor)
        order.append(name)

    for name in derivations:
        visit(name)
    return order



ALL_OFFSET_NAMES = [
    "AudioFrame_StereoChannelAssign",
    "OpusEncoderConfig_SetStereoChannels",
    "DownmixMono_BypassBranch",
    "CodecProbe_ChannelCountPatch",
    "CodecProbe_ForceSuccessBranch",
    "OpusBitrate_Imul384k",
    "AudioEncoder_BitrateMovImm",
    "AudioEncoder_BitrateOrMaskNop",
    "SampleRate_Select48kNop",
    "WebRtcHighpass_Trampoline",
    "WebRtcHighpassCutoff_Injected",
    "WebRtcDcReject_Injected",
    "ChannelDownmix_RetStub",
    "OpusEncoderConfig_IsOkRetTrue",
    "AudioEncoderCodec_ThrowNoOp",
    "OpusEncoderConfig_CtorBitrate_A",
    "OpusEncoderConfig_CtorBitrate_B",
    "OpusEncoderConfig_CtorUseInbandFecOn",
]

LINUX_ONLY_OFFSET_NAMES = ("OpusEncoderConfig_SetMultiChannelStereo",)


def _all_offset_names():
    return list(ALL_OFFSET_NAMES) + list(LINUX_ONLY_OFFSET_NAMES)


def _missing_discovered(results, fmt):
    m = [n for n in _all_offset_names() if n not in results]
    if fmt == "pe":
        m = [n for n in m if n not in LINUX_ONLY_OFFSET_NAMES]
    return m


_WINDOWS_PATCHER_OFFSET_ORDER = (
    "AudioFrame_StereoChannelAssign",
    "OpusEncoderConfig_SetStereoChannels",
    "DownmixMono_BypassBranch",
    "CodecProbe_ChannelCountPatch",
    "CodecProbe_ForceSuccessBranch",
    "OpusBitrate_Imul384k",
    "AudioEncoder_BitrateMovImm",
    "AudioEncoder_BitrateOrMaskNop",
    "SampleRate_Select48kNop",
    "WebRtcHighpass_Trampoline",
    "WebRtcHighpassCutoff_Injected",
    "WebRtcDcReject_Injected",
    "ChannelDownmix_RetStub",
    "OpusEncoderConfig_IsOkRetTrue",
    "AudioEncoderCodec_ThrowNoOp",
    "OpusEncoderConfig_CtorBitrate_A",
    "OpusEncoderConfig_CtorBitrate_B",
    "OpusEncoderConfig_CtorUseInbandFecOn",
    "NetEq_DelayMsPerLossPercent",
    "Pacer_ForceBlockAudioFalse",
    "Discord_SetAutomaticGainControlConfig",
    "Discord_SetAutomaticGainControl_bool",
    "Discord_SetNoiseSuppression_bool",
    "Discord_SetEchoCancellation_bool",
    "Discord_SetEchoCancellationPreEcho_bool",
    "Discord_EnableBuiltInAcousticEchoCancel_bool",
    "Discord_SetNoiseCancellation_bool",
    "Discord_SetNoiseCancellationDuringProcessing_bool",
)
if len(_WINDOWS_PATCHER_OFFSET_ORDER) != 28:
    raise RuntimeError("_WINDOWS_PATCHER_OFFSET_ORDER must be 28 entries (patcher sync)")

WINDOWS_PATCHER_OFFSET_NAMES = list(_WINDOWS_PATCHER_OFFSET_ORDER[:18])
WINDOWS_EXTENDED_OFFSET_NAMES = list(_WINDOWS_PATCHER_OFFSET_ORDER[18:])

WINDOWS_DISCORD_EXPORT_NAMES = {
    "Discord_SetAutomaticGainControlConfig": "?SetAutomaticGainControlConfig@Discord@@QEAAXUGainControllerConfig@media@discord@@@Z",
    "Discord_SetAutomaticGainControl_bool": "?SetAutomaticGainControl@Discord@@QEAAX_N@Z",
    "Discord_SetNoiseSuppression_bool": "?SetNoiseSuppression@Discord@@QEAAX_N@Z",
    "Discord_SetEchoCancellation_bool": "?SetEchoCancellation@Discord@@QEAAX_N@Z",
    "Discord_SetEchoCancellationPreEcho_bool": "?SetEchoCancellationPreEcho@Discord@@QEAAX_N@Z",
    "Discord_EnableBuiltInAcousticEchoCancel_bool": "?EnableBuiltInAEC@Discord@@QEAAX_N@Z",
    "Discord_SetNoiseCancellation_bool": "?SetNoiseCancellation@Discord@@QEAAX_N@Z",
    "Discord_SetNoiseCancellationDuringProcessing_bool": "?SetNoiseCancellationDuringProcessing@Discord@@QEAAX_N@Z",
}
if set(WINDOWS_DISCORD_EXPORT_NAMES) != set(_WINDOWS_PATCHER_OFFSET_ORDER[20:]):
    raise RuntimeError("WINDOWS_DISCORD_EXPORT_NAMES keys must match Discord API LOCK entries in _WINDOWS_PATCHER_OFFSET_ORDER[20:]")

PATCHER_OFFSET_NAMES = list(_WINDOWS_PATCHER_OFFSET_ORDER)

if len(ALL_OFFSET_NAMES) != len(set(ALL_OFFSET_NAMES)):
    raise RuntimeError("ALL_OFFSET_NAMES has duplicate entries (breaks patcher hit counting)")
if len(PATCHER_OFFSET_NAMES) != len(set(PATCHER_OFFSET_NAMES)):
    raise RuntimeError("PATCHER_OFFSET_NAMES has duplicate entries")


def count_patcher_offsets_found(results, patcher_names=None):
    names = list(dict.fromkeys(patcher_names or PATCHER_OFFSET_NAMES))
    hits = sum(1 for k in names if k in results)
    return hits, len(names)


ALLOWED_OFFSET_NAMES = (
    frozenset(ALL_OFFSET_NAMES)
    | frozenset(WINDOWS_EXTENDED_OFFSET_NAMES)
    | frozenset(LINUX_ONLY_OFFSET_NAMES)
)
for _map_name, _map in (("ELF_SYMBOL_MAP", ELF_SYMBOL_MAP), ("ARM64_SYMBOL_MAP", ARM64_SYMBOL_MAP)):
    _extra = set(_map.keys()) - ALLOWED_OFFSET_NAMES
    if _extra:
        raise RuntimeError("%s has keys not in ALLOWED_OFFSET_NAMES: %s" % (_map_name, sorted(_extra)))


def _log_context_fingerprints(data, results, adj):
    critical = [
        "CodecProbe_ChannelCountPatch", "OpusEncoderConfig_SetStereoChannels", "DownmixMono_BypassBranch",
        "AudioEncoder_BitrateMovImm", "AudioFrame_StereoChannelAssign",
    ]
    for name in critical:
        if name not in results:
            continue
        rva = results[name]
        file_off = rva - adj
        if file_off < 32 or file_off + 32 > len(data):
            continue
        region = data[file_off - 32:file_off + 32]
        fp = hashlib.sha1(region).hexdigest()[:16]
        print(f"  [CONTEXT FINGERPRINT] {name} @ 0x{rva:X}  sha1:{fp}...")


def _prune_results_to_allowed(results, tiers_used=None, label=""):
    if not results:
        return
    removed = [k for k in list(results.keys()) if k not in ALLOWED_OFFSET_NAMES]
    for k in removed:
        results.pop(k, None)
        if tiers_used is not None:
            tiers_used.pop(k, None)
    if removed and label:
        print(f"  [INFO] Pruned non-patcher offset(s) from {label}: {', '.join(removed)}")


def _sliding_window_recover(data, anchor_config, delta, name, adj, bin_fmt='pe'):
    exp_map = _build_expected_map(bin_fmt)

    if name not in exp_map:
        return None, 0

    exp_hex, exp_len = exp_map[name]
    if not exp_hex:
        return None, 0

    expected = bytes.fromhex(exp_hex.replace(' ', ''))
    if len(expected) < 2:
        window = min(SLIDING_WINDOW_OVERRIDES.get(name, 16), 16)
    else:
        window = SLIDING_WINDOW_OVERRIDES.get(name, SLIDING_WINDOW_DEFAULT)

    exact_file = anchor_config + delta - adj

    if 0 <= exact_file and exact_file + len(expected) <= len(data):
        if data[exact_file:exact_file + len(expected)] == expected:
            return anchor_config + delta, 0

    if len(expected) == 1:
        candidates = []
        for dist in range(1, window + 1):
            for direction in (+1, -1):
                candidate = exact_file + (dist * direction)
                if 0 <= candidate and candidate + 1 <= len(data):
                    if data[candidate:candidate + 1] == expected:
                        candidates.append((candidate, dist * direction))
        if len(candidates) == 0:
            return None, 0
        if len(candidates) != 1:
            print(f"  [SLIDING AMBIGUOUS] {name}: {len(candidates)} matches for expected byte in ±{window}, skipping")
            return None, 0
        candidate, slide_dist = candidates[0]
        return candidate + adj, slide_dist

    for dist in range(1, window + 1):
        for direction in (+1, -1):
            candidate = exact_file + (dist * direction)
            if 0 <= candidate and candidate + len(expected) <= len(data):
                if data[candidate:candidate + len(expected)] == expected:
                    config_off = candidate + adj
                    return config_off, dist * direction

    return None, 0


def _find_emulate_bitrate_in_anchor_window(data, anchor_file, adj, window=0x2000):
    literal_32000 = b'\x00\x7d\x00\x00'
    start = max(0, anchor_file - window)
    end = min(len(data) - 4, anchor_file + window)
    candidates = []
    pos = data.find(literal_32000, start, end + 1)
    while pos >= 0:
        if pos >= 2 and data[pos - 2] == 0x69:
            candidates.append((pos, True))
        elif pos >= 1 and 0xB8 <= data[pos - 1] <= 0xBF:
            candidates.append((pos, False))
        pos = data.find(literal_32000, pos + 1, end + 1)
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: (abs(x[0] - anchor_file), not x[1]))
    file_off = candidates[0][0]
    reason = "imul 32000" if candidates[0][1] else "mov 32000"
    return file_off + adj, f"anchor-window({reason} @file:0x{file_off:X})"


def _run_heuristic_scan(data, missing_names, adj, text_start, text_end):
    hints = []
    if "OpusBitrate_Imul384k" in missing_names:
        imul_pat = Signature._parse("69 ?? 00 7D 00 00")
        matches = scan_pattern(data, imul_pat, start=text_start, end=text_end)
        for m in matches:
            candidate_file = m + 2
            reason = f"imul *,32000 @file:0x{m:X}"
            hints.append(("OpusBitrate_Imul384k", candidate_file, reason))
    if "SampleRate_Select48kNop" in missing_names:
        for i in range(text_start, min(text_end, len(data) - 24)):
            if data[i] == 0x83 and 0xB8 <= data[i+1] <= 0xBF and (data[i+1] & 7) != 4:
                if i + 7 <= len(data) and data[i+6] == 0x02:
                    for j in range(7, 20):
                        if i + j + 2 <= len(data) and data[i+j] == 0x0F and 0x40 <= data[i+j+1] <= 0x4F:
                            hints.append(("SampleRate_Select48kNop", i + j, f"cmp ...,2 + cmov @file:0x{i:X} [HEURISTIC USED]"))
                            break
            if data[i:i+2] == b'\x41\x83' and i + 8 <= len(data):
                if 0xB8 <= data[i+2] <= 0xBF and (data[i+2] & 7) != 4 and data[i+7] == 0x02:
                    for j in range(8, 24):
                        if i + j + 2 <= len(data) and data[i+j] == 0x0F and 0x40 <= data[i+j+1] <= 0x4F:
                            hints.append(("SampleRate_Select48kNop", i + j, f"41 83 cmp ...,2 + cmov @file:0x{i:X} [HEURISTIC USED]"))
                            break
    if "AudioFrame_StereoChannelAssign" in missing_names:
        pair_pat = Signature._parse("B8 80 BB 00 00 BD 00 7D 00 00")
        matches = scan_pattern(data, pair_pat, start=text_start, end=text_end, limit=5)
        for m in matches:
            for off in range(20, 60):
                pos = m + off
                if pos + 4 <= len(data) and data[pos:pos+4] == b'\x4C\x0F\x43\xE8':
                    hints.append(("AudioFrame_StereoChannelAssign", pos, f"48k/32k pair + cmovae @file:0x{m:X}"))
                    break
    if "OpusEncoderConfig_SetStereoChannels" in missing_names:
        bb80_pat = Signature._parse("48 B9 14 00 00 00 80 BB 00 00")
        matches = scan_pattern(data, bb80_pat, start=text_start, end=text_end, limit=5)
        for m in matches:
            for scan in range(12, 40):
                pos = m + scan
                if pos + 5 <= len(data) and data[pos] == 0x48 and data[pos+1] == 0xC7:
                    target = pos + 4
                    if target < len(data):
                        hints.append(("OpusEncoderConfig_SetStereoChannels", target,
                                     f"Opus config struct @file:0x{m:X}"))
                    break

    if missing_names:
        opus_positions = []
        search_start = text_start
        while True:
            pos = data.find(b'Opus', search_start, text_end)
            if pos < 0:
                break
            opus_positions.append(pos)
            search_start = pos + 1
            if len(opus_positions) >= 20:
                break

        if opus_positions:
            for name in missing_names:
                if "Encoder" not in name and "Config" not in name:
                    continue
                for opus_pos in opus_positions[:10]:
                    window_start = max(text_start, opus_pos - 0x400)
                    window_end = min(text_end, opus_pos + 0x400)
                    const_pat = Signature._parse("80 BB 00 00")
                    sub_matches = scan_pattern(data, const_pat, start=window_start, end=window_end)
                    for sm in sub_matches[:3]:
                        hints.append((name, sm, f"near Opus string @file:0x{opus_pos:X}"))

    return hints[:15]


def _cross_validate(results, adj, data, tiers_used=None, bin_fmt='pe'):
    warnings = []
    tiers = tiers_used or {}

    if bin_fmt == 'pe':
        for derived_name, paths in DERIVATIONS.items():
            if derived_name not in results:
                continue
            derived_tier = tiers.get(derived_name, '')
            if derived_tier.startswith('symbol'):
                continue
            matched_any = False
            checked_any = False
            mismatch_msg = None
            for anchor_name, expected_delta in paths:
                if anchor_name not in results:
                    continue
                checked_any = True
                actual_delta = results[derived_name] - results[anchor_name]
                if actual_delta == expected_delta:
                    matched_any = True
                    break
                mismatch_msg = (
                    f"Delta mismatch: {derived_name} - {anchor_name} = "
                    f"0x{actual_delta:X} (expected deltas: "
                    f"{', '.join(f'0x{d:X}' for _, d in paths)})"
                )
            if checked_any and not matched_any and mismatch_msg:
                warnings.append(mismatch_msg)

    if "OpusEncoderConfig_CtorBitrate_A" in results and "OpusEncoderConfig_CtorBitrate_B" in results:
        for name in ["OpusEncoderConfig_CtorBitrate_A", "OpusEncoderConfig_CtorBitrate_B"]:
            f = results[name] - adj
            if 0 <= f and f + 4 <= len(data):
                val = data[f:f+4]
                if val != b'\x00\x7D\x00\x00' and val != b'\x00\xDC\x05\x00':
                    warnings.append(f"{name}: unexpected config bytes {val.hex(' ')} "
                                    f"(expected 00 7D 00 00 or 00 DC 05 00)")

    return warnings


BITRATE_OFFSET_NAMES = [
    "OpusBitrate_Imul384k", "AudioEncoder_BitrateMovImm",
    "OpusEncoderConfig_CtorBitrate_A", "OpusEncoderConfig_CtorBitrate_B",
]

def run_bitrate_audit_pe(data, results, adj, text_start, text_end):
    literal_32000 = struct.pack("<I", 32000)
    literal_512000 = struct.pack("<I", 512000)
    bitrate_rvas = set()
    for name in BITRATE_OFFSET_NAMES:
        if name in results and results[name]:
            bitrate_rvas.add(results[name])
    covered_32k = []
    uncovered_32k = []
    covered_512k = []
    uncovered_512k = []
    for start in range(text_start, min(text_end, len(data) - 4)):
        chunk = data[start : start + 4]
        if chunk == literal_32000:
            rva = start + adj
            if any(abs(rva - br) <= 10 for br in bitrate_rvas):
                covered_32k.append((start, rva))
            else:
                uncovered_32k.append((start, rva))
        elif chunk == literal_512000:
            rva = start + adj
            if any(abs(rva - br) <= 10 for br in bitrate_rvas):
                covered_512k.append((start, rva))
            else:
                uncovered_512k.append((start, rva))
    print("\n" + "=" * 65)
    print("  BITRATE AUDIT (PE .text)")
    print("=" * 65)
    print(f"  Known bitrate patch sites: {len(bitrate_rvas)}")
    print(f"  32000 (0x7D00):   {len(covered_32k)} covered, {len(uncovered_32k)} uncovered")
    if uncovered_32k:
        for f, rva in uncovered_32k[:10]:
            print(f"    uncovered  file 0x{f:X}  RVA 0x{rva:X}")
        if len(uncovered_32k) > 10:
            print(f"    ... and {len(uncovered_32k) - 10} more")
    print(f"  512000 (0x7D000): {len(covered_512k)} covered, {len(uncovered_512k)} uncovered")
    if uncovered_512k:
        for f, rva in uncovered_512k[:10]:
            print(f"    uncovered  file 0x{f:X}  RVA 0x{rva:X}")
        if len(uncovered_512k) > 10:
            print(f"    ... and {len(uncovered_512k) - 10} more")
        rva0 = uncovered_512k[0][1]
        print(f"  [INFO] 512000 literals in .text not near known bitrate sites (example RVA 0x{rva0:X}).")
        print("         Treat as noise unless IDA + Linux xref confirm another encoder init path.")
    if not uncovered_32k and not uncovered_512k and bitrate_rvas:
        print("  All 32000/512000 constants in .text are at or near known patch sites.")
    print()
    return uncovered_512k[0][1] if uncovered_512k else None


def _resolve_arm64_symbols(bin_info, data):
    if not bin_info.get('has_symbols') or not bin_info.get('func_symbols'):
        return {}, []

    func_syms = bin_info['func_symbols']
    adj = bin_info['file_offset_adjustment']
    resolved = {}
    details = []

    for offset_name, mapping in ARM64_SYMBOL_MAP.items():
        candidates = []
        for pattern in mapping['patterns']:
            for sym_name, sym in func_syms.items():
                if pattern.lower() in sym_name.lower():
                    candidates.append(sym)

        if not candidates:
            continue

        if mapping.get('prefer_smallest'):
            candidates.sort(key=lambda c: c.get('size', 0x10000))
        elif mapping.get('prefer_largest'):
            candidates.sort(key=lambda c: c.get('size', 0), reverse=True)

        best = candidates[0]
        for c in candidates:
            if any(p.lower() == c['name'].lower().lstrip('_').rstrip('_') for p in mapping['patterns']):
                best = c
                break

        sym_addr = best['value']

        if mapping['at_start']:
            file_off = sym_addr - adj
            if 0 <= file_off < len(data):
                resolved[offset_name] = sym_addr
                details.append((offset_name, sym_addr, best['name'], 'arm64-symbol'))
        else:
            func_size = best.get('size', 0)
            if func_size == 0 or func_size > 0x10000:
                func_size = 0x4000

            func_file_start = sym_addr - adj
            if func_file_start < 0:
                func_file_start = 0

            arm64_scan = mapping.get('arm64_scan')
            if arm64_scan:
                result = _arm64_scan_within_function(
                    data, func_file_start, func_size, arm64_scan, adj)
                if result is not None:
                    resolved[offset_name] = result
                    details.append((offset_name, result, best['name'], 'arm64-symbol+scan'))
                else:
                    func_file_end = min(func_file_start + func_size, len(data))
                    resolved[f"_symhint_{offset_name}"] = (
                        func_file_start, func_file_end, best['name'])
                    details.append((offset_name, sym_addr, best['name'],
                                    'arm64-hint'))
            else:
                details.append((offset_name, sym_addr, best['name'], 'arm64-hint'))

    return resolved, details


def discover_offsets_arm64(data, arm64_info):
    results = {}
    errors = []
    tiers_used = {}

    adj = arm64_info.get('file_offset_adjustment', 0)
    fat_offset = arm64_info.get('fat_offset', 0)

    if not arm64_info.get('has_symbols'):
        print("\n  [ARM64] No symbols in arm64 slice - cannot resolve offsets")
        for name in _all_offset_names():
            errors.append((name, "no arm64 symbols"))
        return results, errors, adj, tiers_used

    print("\n" + "=" * 65)
    print("  ARM64 PHASE 0: Symbol Table Resolution")
    print("=" * 65)

    n_func = len(arm64_info.get('func_symbols', {}))
    print(f"  arm64 symbols: {n_func} functions")

    try:
        sym_resolved, sym_details = _resolve_arm64_symbols(arm64_info, data)
    except Exception as e:
        sym_resolved = {}
        sym_details = []
        print(f"  [WARN] ARM64 symbol resolution failed: {e}")

    for offset_name, config_off, sym_name, method in sym_details:
        safe_sym = sym_name.encode('ascii', errors='replace').decode('ascii')[:50]

        if method == 'arm64-symbol':
            file_off = config_off - adj
            results[offset_name] = config_off
            tiers_used[offset_name] = f"arm64-sym({safe_sym})"
            print(f"  [SYM ] {offset_name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [{safe_sym}]")

        elif method == 'arm64-symbol+scan':
            file_off = config_off - adj
            results[offset_name] = config_off
            tiers_used[offset_name] = f"arm64-scan({safe_sym})"
            print(f"  [SCAN] {offset_name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [via {safe_sym}]")

        elif method == 'arm64-hint':
            print(f"  [HINT] {offset_name:45s} function '{safe_sym}' - scan did not match")

    if "OpusBitrate_Imul384k" not in results:
        slice_start = fat_offset
        slice_end = fat_offset + arm64_info.get('fat_size', 0)
        if slice_end > len(data):
            slice_end = len(data)
        literal_32000 = struct.pack('<I', 32000)
        orig_low3 = b'\x00\x7d\x00'
        candidates = []
        for i in range(slice_start, slice_end - 4):
            if data[i:i + 4] == literal_32000 and data[i:i + 3] == orig_low3:
                candidates.append(i)
        if candidates:
            results["OpusBitrate_Imul384k"] = candidates[0] + adj
            tiers_used["OpusBitrate_Imul384k"] = "arm64-literal-32000(1st)"
            print(f"  [SCAN] {'OpusBitrate_Imul384k':45s} = 0x{candidates[0] + adj:X}  (file 0x{candidates[0]:X})  [literal 32000]")

    validation_failures = _validate_discovered_offsets(results, data, adj)
    for name, reason in validation_failures:
        results.pop(name, None)
        tiers_used.pop(name, None)
        errors.append((name, reason))
        print(f"  [INVALID] {name}: {reason}")

    missing = [n for n in _all_offset_names() if n not in results and n not in LINUX_ONLY_OFFSET_NAMES]
    if missing:
        print(f"\n  ARM64 missing offsets ({len(missing)}): {', '.join(missing)}")
        for name in missing:
            errors.append((name, "no arm64 match"))

    _prune_results_to_allowed(results, tiers_used, label="arm64")

    return results, errors, adj, tiers_used


def _pe_file_off_to_rva(file_off, sections):
    for sec in sections or []:
        ro = sec.get("raw_offset", 0)
        rs = sec.get("raw_size", 0)
        va = sec.get("vaddr", 0)
        if ro > 0 and ro <= file_off < ro + rs:
            return file_off - ro + va
    return None


def _pe_rva_to_file_off(rva, sections):
    for sec in sections or []:
        va = sec.get("vaddr", 0)
        vs = sec.get("vsize", 0) or sec.get("raw_size", 0)
        ro = sec.get("raw_offset", 0)
        if va and ro and va <= rva < va + vs:
            return rva - va + ro
    return None


def _pe_read_cstr(data, off, max_len=512):
    end = data.find(b"\x00", off, min(len(data), off + max_len))
    if end < 0:
        return None
    try:
        return data[off:end].decode("ascii")
    except UnicodeDecodeError:
        return None


def _pe_parse_exports(data, bin_info):
    if bin_info.get("format") != "pe":
        return {}
    cached = bin_info.get("exports_by_name")
    if cached is not None:
        return cached
    sections = bin_info.get("sections") or []
    pe_off = bin_info.get("pe_offset")
    if not pe_off or pe_off + 4 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    coff = pe_off + 4
    if coff + 20 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    opt_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    if opt + 2 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        dd_off = opt + 112
    elif magic == 0x10B:
        dd_off = opt + 96
    else:
        bin_info["exports_by_name"] = {}
        return {}
    if dd_off + 8 > opt + opt_size or dd_off + 8 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    exp_rva = struct.unpack_from("<I", data, dd_off)[0]
    exp_size = struct.unpack_from("<I", data, dd_off + 4)[0]
    if exp_rva == 0 or exp_size < 40:
        bin_info["exports_by_name"] = {}
        return {}
    exp_file = _pe_rva_to_file_off(exp_rva, sections)
    if exp_file is None or exp_file + 40 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    num_funcs = struct.unpack_from("<I", data, exp_file + 20)[0]
    num_names = struct.unpack_from("<I", data, exp_file + 24)[0]
    funcs_rva = struct.unpack_from("<I", data, exp_file + 28)[0]
    names_rva = struct.unpack_from("<I", data, exp_file + 32)[0]
    ords_rva = struct.unpack_from("<I", data, exp_file + 36)[0]
    funcs_file = _pe_rva_to_file_off(funcs_rva, sections)
    names_file = _pe_rva_to_file_off(names_rva, sections)
    ords_file = _pe_rva_to_file_off(ords_rva, sections)
    if None in (funcs_file, names_file, ords_file):
        bin_info["exports_by_name"] = {}
        return {}
    if funcs_file + num_funcs * 4 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    if names_file + num_names * 4 > len(data) or ords_file + num_names * 2 > len(data):
        bin_info["exports_by_name"] = {}
        return {}
    out = {}
    for i in range(num_names):
        name_rva = struct.unpack_from("<I", data, names_file + i * 4)[0]
        name_file = _pe_rva_to_file_off(name_rva, sections)
        if name_file is None:
            continue
        nm = _pe_read_cstr(data, name_file)
        if not nm:
            continue
        ord_idx = struct.unpack_from("<H", data, ords_file + i * 2)[0]
        if ord_idx >= num_funcs:
            continue
        fn_rva = struct.unpack_from("<I", data, funcs_file + ord_idx * 4)[0]
        if fn_rva == 0:
            continue
        if exp_rva <= fn_rva < exp_rva + exp_size:
            continue
        out[nm] = fn_rva
    bin_info["exports_by_name"] = out
    return out


def _discover_windows_extended_offsets_pe(data, bin_info, results, tiers_used, text_start, text_end):
    if bin_info.get("format") != "pe" or "CodecProbe_ChannelCountPatch" not in results:
        return

    adj = bin_info.get("file_offset_adjustment", 0xC00)
    image_base = bin_info.get("image_base", 0x180000000)
    sections = bin_info.get("sections") or []

    print("\n" + "=" * 65)
    print("  PHASE 2c: Windows Extended (NetEq / Pacer / Discord API)")
    print("=" * 65)

    pat_ne = bytes.fromhex("48 B8 14 00 00 00 C8 00 00 00")
    ne_hits = []
    idx = text_start
    while idx < text_end:
        j = data.find(pat_ne, idx, text_end)
        if j < 0:
            break
        ne_hits.append(j + adj)
        idx = j + 1
    if len(ne_hits) == 1:
        rva = ne_hits[0]
        results["NetEq_DelayMsPerLossPercent"] = rva
        tiers_used["NetEq_DelayMsPerLossPercent"] = "extended(neteq-movabs)"
        print(f"  [ OK ] NetEq_DelayMsPerLossPercent{' ':16s} = 0x{rva:X}  [movabs 14..C8]")
    elif not ne_hits:
        print("  [FAIL] NetEq_DelayMsPerLossPercent: movabs pattern not found")
    else:
        print(f"  [FAIL] NetEq_DelayMsPerLossPercent: ambiguous ({len(ne_hits)} movabs hits)")

    pacer_key = b"WebRTC-Pacer-BlockAudio\x00"
    pk = data.find(pacer_key)
    if pk < 0:
        print("  [FAIL] Pacer_ForceBlockAudioFalse: string WebRTC-Pacer-BlockAudio not found")
    else:
        str_rva = _pe_file_off_to_rva(pk, sections)
        if str_rva is None:
            print("  [FAIL] Pacer_ForceBlockAudioFalse: could not map string file offset to RVA")
        else:
            str_va = image_base + str_rva
            lea_rva = None
            i = text_start
            ts = bin_info.get("text_section") or {}
            tva = ts.get("vaddr", 0x1000)
            traw = ts.get("raw_offset", text_start)
            while i < text_end - 7:
                if data[i : i + 3] == b"\x48\x8d\x05":
                    disp = struct.unpack_from("<i", data, i + 3)[0]
                    insn_rva = tva + (i - traw)
                    tgt_va = image_base + insn_rva + 7 + disp
                    if tgt_va == str_va:
                        lea_rva = insn_rva
                        break
                i += 1
            if lea_rva is None:
                print("  [FAIL] Pacer_ForceBlockAudioFalse: no LEA to BlockAudio string in .text")
            else:
                lea_file = lea_rva - adj
                found_p = None
                for k in range(lea_file, min(lea_file + 0x120, text_end - 3)):
                    if data[k : k + 3] == b"\x0f\x94\xc3":
                        found_p = k + adj
                        break
                if found_p:
                    results["Pacer_ForceBlockAudioFalse"] = found_p
                    tiers_used["Pacer_ForceBlockAudioFalse"] = "extended(pacer-blockaudio)"
                    print(f"  [ OK ] Pacer_ForceBlockAudioFalse{' ':21s} = 0x{found_p:X}  [setz bl after LEA]")
                else:
                    print("  [FAIL] Pacer_ForceBlockAudioFalse: setz bl not found after LEA")

    exports = _pe_parse_exports(data, bin_info)
    if not exports:
        print(f"  [FAIL] Discord API lock sites: PE export directory unreadable")
    else:
        resolved = 0
        missing = []
        for name, mangled in WINDOWS_DISCORD_EXPORT_NAMES.items():
            rva = exports.get(mangled)
            if rva is None:
                missing.append(name)
                continue
            results[name] = rva
            tiers_used[name] = "extended(discord-api+pe-export)"
            resolved += 1
        if missing:
            print(f"  [WARN] Discord API lock sites: {resolved}/{len(WINDOWS_DISCORD_EXPORT_NAMES)} resolved; missing: {', '.join(missing)}")
        else:
            print(f"  [ OK ] Discord API lock sites{' ':26s} ({resolved} RVAs, PE export table)")


def discover_offsets(data, bin_info, verbose=True):
    _saved_stdout = None
    if not verbose:
        _saved_stdout = sys.stdout
        sys.stdout = io.StringIO()
    try:
        return _discover_offsets_impl(data, bin_info)
    finally:
        if _saved_stdout is not None:
            sys.stdout = _saved_stdout


def _discover_offsets_impl(data, bin_info):
    results = {}
    errors = []
    tiers_used = {}

    fmt = bin_info.get('format', 'raw') if bin_info else 'raw'
    adj = bin_info.get('file_offset_adjustment', 0) if bin_info else 0xC00
    if adj is None:
        adj = 0xC00 if fmt == 'pe' else 0

    text_start = 0
    text_end = len(data)
    if bin_info and bin_info.get('text_section'):
        ts = bin_info['text_section']
        text_start = ts['raw_offset']
        text_end = text_start + ts['raw_size']
        if fmt == 'pe' and text_start + 16 <= len(data):
            prologue = data[text_start:text_start + 16]
            if not any(p in prologue for p in (b'\x55', b'\x48\x89\xE5', b'\x48\x83\xEC', b'\xE8', b'\x48\x8B')):
                print(f"  [WARN] PE .text at file 0x{text_start:X} does not contain common prologue bytes (55/48 89 E5/48 83 EC/E8)")

    sym_hints = {}
    if bin_info and bin_info.get('has_symbols') and fmt in ('elf', 'macho'):
        print("\n" + "=" * 65)
        print("  PHASE 0: Symbol Table Resolution")
        print("=" * 65)

        try:
            sym_resolved, sym_details = _resolve_elf_symbols(bin_info, data)
        except Exception as e:
            sym_resolved = {}
            sym_details = []
            print(f"  [WARN] Symbol resolution failed: {e}")

        for offset_name, config_off, sym_name, method in sym_details:
            if method == 'symbol-direct':
                file_off = config_off - adj
                accept = True
                _exp_sym = _build_expected_map(fmt)
                if offset_name in _exp_sym:
                    exp_hex, exp_len = _exp_sym[offset_name]
                    if exp_hex:
                        expected = bytes.fromhex(exp_hex.replace(' ', ''))
                        if 0 <= file_off and file_off + len(expected) <= len(data):
                            actual = data[file_off:file_off + len(expected)]
                            if actual != expected:
                                print(f"  [SKIP] {offset_name:45s} symbol '{sym_name}' @0x{config_off:X} - bytes do not match")
                                accept = False

                if accept:
                    results[offset_name] = config_off
                    tiers_used[offset_name] = f"symbol({sym_name})"
                    print(f"  [SYM ] {offset_name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [{sym_name}]")

            elif method == 'symbol+scan':
                results[offset_name] = config_off
                tiers_used[offset_name] = f"symbol+scan({sym_name})"
                file_off = config_off - adj
                print(f"  [SCAN] {offset_name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [via {sym_name}]")

            elif method == 'symbol-range-hint':
                hint_key = f"_symhint_{offset_name}"
                if hint_key in sym_resolved:
                    sym_hints[offset_name] = sym_resolved[hint_key]
                    print(f"  [HINT] {offset_name:45s} function '{sym_name}' - will do targeted scan")

        if not sym_details:
            print("  No symbol matches found - falling through to signature scanning")

    print("\n" + "=" * 65)
    print("  PHASE 1: Signature Scanning (primary + relaxed)")
    print("=" * 65)

    for sig in SIGNATURES:
        if sig.name in results:
            print(f"  [SKIP] {sig.name:45s} already resolved via symbol table")
            continue

        scan_start = text_start
        scan_end = text_end
        if sig.name in sym_hints:
            hint_start, hint_end, hint_sym = sym_hints[sig.name]
            scan_start = max(text_start, hint_start - 0x200)
            scan_end = min(text_end, hint_end + 0x200)

        file_off, err, tier = find_offset(data, sig, scan_start, scan_end)

        if err and sig.name in sym_hints:
            file_off, err, tier = find_offset(data, sig, text_start, text_end)

        if err:
            print(f"  [FAIL] {sig.name}: {err}")
            errors.append((sig.name, err))
        else:
            print(f"  [info] signature match at offset 0x{file_off:X}")
            ok, conf, val_msgs = _run_patch_site_validation(data, file_off, sig, adj)
            if not ok:
                for m in val_msgs:
                    print(f"  [warn] {m}")
                print(f"  [warn] {sig.name}: validation failed (confidence {conf} < {CONFIDENCE_THRESHOLD}), skipping")
                errors.append((sig.name, f"confidence {conf} < {CONFIDENCE_THRESHOLD}"))
                continue
            config_off = file_off + adj
            tag = "OK" if tier == "primary" else "ALT"
            print(f"  [{tag:4s}] {sig.name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [{tier}] (conf={conf})")

            if sig.expected_original:
                expected = bytes.fromhex(sig.expected_original.replace(' ', ''))
                actual = data[file_off:file_off+len(expected)]
                if actual != expected:
                    print(f"         WARNING: Expected {expected.hex(' ')} but found {actual.hex(' ')}")

            results[sig.name] = config_off
            tiers_used[sig.name] = tier

    still_missing = [sig.name for sig in SIGNATURES if sig.name not in results]
    if still_missing:
        print("\n" + "=" * 65)
        print("  PHASE 1c: Clang/Platform-Specific Alternates")
        print("=" * 65)

        for sig_name, pat_hex, target_off in CLANG_ALT_PATTERNS:
            if sig_name not in still_missing:
                continue
            if sig_name in results:
                continue

            pattern = Signature._parse(pat_hex)
            matches = scan_pattern(data, pattern, start=text_start, end=text_end)

            if len(matches) == 0:
                continue

            resolved = matches
            orig_sig = None
            for s in SIGNATURES:
                if s.name == sig_name:
                    orig_sig = s
                    break

            if orig_sig and orig_sig.disambiguator and len(resolved) > 1:
                valid = [m for m in resolved if orig_sig.disambiguator(data, m)]
                if valid:
                    resolved = valid

            if orig_sig and orig_sig.expected_original and len(resolved) > 1:
                expected = bytes.fromhex(orig_sig.expected_original.replace(' ', ''))
                valid = []
                for m in resolved:
                    tf = m + target_off
                    if 0 <= tf and tf + len(expected) <= len(data):
                        if data[tf:tf+len(expected)] == expected:
                            valid.append(m)
                if valid:
                    resolved = valid

            if len(resolved) >= 1:
                file_off = resolved[0] + target_off
                if 0 <= file_off < len(data):
                    ok, conf, _ = _run_patch_site_validation(data, file_off, orig_sig or {}, adj)
                    if not ok:
                        print(f"  [warn] {sig_name}: validation failed (confidence {conf}), skipping")
                    else:
                        config_off = file_off + adj
                        ambig = f"(ambig:{len(resolved)})" if len(resolved) > 1 else ""
                        tier = f"clang-alt{ambig}"
                        print(f"  [CLNG] {sig_name:45s} = 0x{config_off:X}  (file 0x{file_off:X})  [{tier}] (conf={conf})")
                        results[sig_name] = config_off
                        tiers_used[sig_name] = tier
                        still_missing = [n for n in still_missing if n != sig_name]

        if still_missing:
            print(f"  Still missing after Clang alts: {', '.join(still_missing)}")

    patched_fallbacks = []

    if "DownmixMono_BypassBranch" not in results:
        fb_pat = Signature._parse("48 89 F9 E8 ?? ?? ?? ?? 90 90 90 90 90 90 90 90 90 90 90 90 E9")
        matches = scan_pattern(data, fb_pat, start=text_start, end=text_end)
        if len(matches) > 1:
            matches = [m for m in matches if _mono_downmixer_disambiguator(data, m)]
        if len(matches) == 1:
            config_off = matches[0] + 8 + adj
            results["DownmixMono_BypassBranch"] = config_off
            tiers_used["DownmixMono_BypassBranch"] = "patched-fallback"
            patched_fallbacks.append("DownmixMono_BypassBranch")
            print(f"  [FALL] DownmixMono_BypassBranch{' ':30s} = 0x{config_off:X}  [patched NOP sled]")

    if "AudioEncoder_BitrateMovImm" not in results:
        for fb_hex in [
            "89 F8 48 B9 ?? ?? ?? ?? ?? ?? ?? ?? 90 90 90 48 89 4E 1C",
            "89 ?? 48 B9 ?? ?? ?? ?? ?? ?? ?? ?? 90 90 90 48 89 ?? ??",
        ]:
            fb_pat = Signature._parse(fb_hex)
            matches = scan_pattern(data, fb_pat, start=text_start, end=text_end)
            if len(matches) == 1:
                config_off = matches[0] + 4 + adj
                results["AudioEncoder_BitrateMovImm"] = config_off
                tiers_used["AudioEncoder_BitrateMovImm"] = "patched-fallback"
                patched_fallbacks.append("AudioEncoder_BitrateMovImm")
                print(f"  [FALL] AudioEncoder_BitrateMovImm{' ':20s} = 0x{config_off:X}  [patched or->NOP]")
                break

    if "WebRtcHighpassCutoff_Injected" not in results:
        hp_key = "WebRtcHighpass_Trampoline"
        if hp_key not in results and "CodecProbe_ChannelCountPatch" in results:
            results[hp_key] = results["CodecProbe_ChannelCountPatch"] + 0xC275
        if hp_key in results:
            hp_file = results[hp_key] - adj
            if (0 <= hp_file and hp_file + 11 <= len(data) and
                data[hp_file] == 0x48 and data[hp_file+1] == 0xB8 and data[hp_file+10] == 0xC3):
                hpc_va = struct.unpack_from('<Q', data, hp_file + 2)[0]
                if fmt == 'pe' and bin_info:
                    hpc_config = hpc_va - bin_info['image_base']
                    if 0 < hpc_config < len(data):
                        results["WebRtcHighpassCutoff_Injected"] = hpc_config
                        tiers_used["WebRtcHighpassCutoff_Injected"] = "patched-stub-extract"
                        patched_fallbacks.append("WebRtcHighpassCutoff_Injected")
                        print(f"  [FALL] WebRtcHighpassCutoff_Injected{' ':23s} = 0x{hpc_config:X}  [from HP stub VA=0x{hpc_va:X}]")
                elif fmt in ('elf', 'macho'):
                    if 0 < hpc_va < len(data) + adj:
                        results["WebRtcHighpassCutoff_Injected"] = hpc_va
                        tiers_used["WebRtcHighpassCutoff_Injected"] = "patched-stub-extract"
                        patched_fallbacks.append("WebRtcHighpassCutoff_Injected")
                        print(f"  [FALL] WebRtcHighpassCutoff_Injected{' ':23s} = 0x{hpc_va:X}  [from HP stub VA]")

    if patched_fallbacks:
        print(f"\n  NOTE: Binary appears already patched. Fallback used for: {', '.join(patched_fallbacks)}")

    print("\n" + "=" * 65)
    print("  PHASE 2: Relative Offset Derivation (chain-aware)")
    print("=" * 65)

    for derived_name in _topo_sort_derivations(DERIVATIONS):
        if derived_name in results:
            continue
        if fmt in ('elf', 'macho') and derived_name in _PHASE2_SKIP_CLANG:
            continue

        paths = DERIVATIONS[derived_name]
        found = False
        for anchor_name, delta in paths:
            if anchor_name not in results:
                continue

            config_off = results[anchor_name] + delta
            file_off = config_off - adj

            if file_off < 0 or file_off >= len(data):
                continue

            verified_exact = True
            _exp_drv = _build_expected_map(fmt)
            if derived_name in _exp_drv:
                exp_hex, _ = _exp_drv[derived_name]
                if exp_hex:
                    expected = bytes.fromhex(exp_hex.replace(' ', ''))
                    actual = data[file_off:file_off+len(expected)]
                    if actual != expected:
                        verified_exact = False

            if verified_exact:
                print(f"  [ OK ] {derived_name:45s} = 0x{config_off:X}  (from {anchor_name} + 0x{delta:X})")
                results[derived_name] = config_off
                tiers_used[derived_name] = f"derived({anchor_name}+0x{delta:X})"
                found = True
                break

        if not found:
            for anchor_name, delta in paths:
                if anchor_name not in results:
                    continue
                slid_off, slide_dist = _sliding_window_recover(
                    data, results[anchor_name], delta, derived_name, adj,
                    bin_fmt=fmt
                )
                if slid_off is not None and slide_dist != 0:
                    sign = "+" if slide_dist > 0 else ""
                    print(f"  [SLID] {derived_name:45s} = 0x{slid_off:X}  "
                          f"(from {anchor_name} + 0x{delta:X} {sign}{slide_dist})")
                    results[derived_name] = slid_off
                    tiers_used[derived_name] = f"sliding({anchor_name}+0x{delta:X}{sign}{slide_dist})"
                    found = True
                    break

        if not found:
            _exp_drv = _build_expected_map(fmt)
            for anchor_name, delta in paths:
                if anchor_name not in results:
                    continue
                config_off = results[anchor_name] + delta
                file_off = config_off - adj
                if 0 <= file_off < len(data):
                    has_expected = False
                    if derived_name in _exp_drv:
                        exp_hex, _ = _exp_drv[derived_name]
                        if exp_hex:
                            has_expected = True
                    if has_expected:
                        continue
                    print(f"  [ OK ] {derived_name:45s} = 0x{config_off:X}  (from {anchor_name} + 0x{delta:X})  [unverified]")
                    results[derived_name] = config_off
                    tiers_used[derived_name] = f"derived-unverified({anchor_name}+0x{delta:X})"
                    found = True
                    break

        if not found:
            tried = ", ".join(a for a, _ in paths)
            print(f"  [FAIL] {derived_name}: no anchor available (tried: {tried})")
            errors.append((derived_name, f"no anchor available (tried: {tried})"))

    missing = _missing_discovered(results, fmt)
    if missing:
        print("\n" + "=" * 65)
        print("  PHASE 2b: Heuristic Recovery")
        print("=" * 65)

        if "OpusBitrate_Imul384k" in missing and "CodecProbe_ChannelCountPatch" in results:
            anchor_file = results["CodecProbe_ChannelCountPatch"] - adj
            config_off, reason = _find_emulate_bitrate_in_anchor_window(data, anchor_file, adj, window=0x2000)
            if config_off is None and "SampleRate_Select48kNop" in results and "CodecProbe_ForceSuccessBranch" in results:
                lo = min(anchor_file, results["SampleRate_Select48kNop"] - adj, results["CodecProbe_ForceSuccessBranch"] - adj)
                hi = max(anchor_file, results["SampleRate_Select48kNop"] - adj, results["CodecProbe_ForceSuccessBranch"] - adj)
                mid = (lo + hi) // 2
                config_off, reason = _find_emulate_bitrate_in_anchor_window(
                    data, mid, adj, window=(hi - lo) // 2 + 0x2000
                )
            if config_off is None and text_start < text_end:
                full_window = max(anchor_file - text_start, text_end - anchor_file)
                if full_window > 0x2000:
                    config_off, reason = _find_emulate_bitrate_in_anchor_window(data, anchor_file, adj, window=full_window)
                    if config_off is not None:
                        reason = f"full-text-scan({reason})"
            if config_off is not None:
                ebm_file = config_off - adj
                dist = abs(ebm_file - anchor_file)
                if dist > 0x20000:
                    print(f"  [REJECT] OpusBitrate_Imul384k @ 0x{config_off:X} — too far from anchor (0x{dist:X} > 0x20000), skipping")
                    config_off = None
                else:
                    tag = "FULL-TEXT" if "full-text-scan" in reason else "ANCHOR"
                    print(f"  [{tag}] OpusBitrate_Imul384k    = 0x{config_off:X}  "
                          f"[{reason}]  (distance from ApplySettings anchor: 0x{dist:X})")
                    results["OpusBitrate_Imul384k"] = config_off
                    tiers_used["OpusBitrate_Imul384k"] = reason
                    missing = _missing_discovered(results, fmt)

        hints = _run_heuristic_scan(data, missing, adj, text_start, text_end)
        ebm_far_candidates = []
        if hints:
            EMULATE_BITRATE_MAX_DISTANCE = 0x2000
            for name, file_off, reason in hints:
                if name in results:
                    continue
                if name == "OpusBitrate_Imul384k" and "CodecProbe_ChannelCountPatch" in results:
                    anchor_file = results["CodecProbe_ChannelCountPatch"] - adj
                    if abs(file_off - anchor_file) > EMULATE_BITRATE_MAX_DISTANCE:
                        ebm_far_candidates.append((file_off, reason))
                        print(f"  [HEUR] Rejected {name} @ 0x{file_off + adj:X} — too far from CodecProbe_ChannelCountPatch (delta 0x{abs(file_off - anchor_file):X} > 0x{EMULATE_BITRATE_MAX_DISTANCE:X})")
                        continue
                config_off = file_off + adj
                _exp_map = _build_expected_map(fmt)
                if name in _exp_map:
                    exp_hex, exp_len = _exp_map[name]
                    if exp_hex:
                        expected = bytes.fromhex(exp_hex.replace(' ', ''))
                        actual = data[file_off:file_off+len(expected)]
                        if actual != expected:
                            continue
                print(f"  [HEUR] {name:45s} = 0x{config_off:X}  [{reason}]")
                results[name] = config_off
                tiers_used[name] = f"heuristic({reason})"

        if "OpusBitrate_Imul384k" not in results and ebm_far_candidates and fmt == "macho" and "CodecProbe_ChannelCountPatch" in results:
            anchor_file = results["CodecProbe_ChannelCountPatch"] - adj
            expected_32000 = bytes.fromhex("007D00")
            valid = []
            for file_off, reason in ebm_far_candidates:
                if file_off + 3 <= len(data) and data[file_off:file_off + 3] == expected_32000:
                    valid.append((file_off, abs(file_off - anchor_file)))
            if valid:
                valid.sort(key=lambda x: x[1])
                file_off = valid[0][0]
                config_off = file_off + adj
                results["OpusBitrate_Imul384k"] = config_off
                tiers_used["OpusBitrate_Imul384k"] = "fallback-far(imul 32000,closest-to-anchor)"
                print(f"  [FALLBACK-FAR] OpusBitrate_Imul384k = 0x{config_off:X}  (no in-window candidate; using closest imul 32000 — VERIFY bitrate after patch)")
                missing = _missing_discovered(results, fmt)

        if not hints:
            still = _missing_discovered(results, fmt)
            if still:
                print(f"  No heuristic candidates for: {', '.join(still)}")

    if fmt == "pe" and bin_info:
        _discover_windows_extended_offsets_pe(data, bin_info, results, tiers_used, text_start, text_end)

    validation_failures = _validate_discovered_offsets(results, data, adj)
    for name, reason in validation_failures:
        results.pop(name, None)
        tiers_used.pop(name, None)
        errors.append((name, reason))
        print(f"  [INVALID] {name}: {reason}")

    errors = [(n, e) for n, e in errors if n not in results]
    _err_seen = {}
    for n, e in errors:
        if n not in _err_seen:
            _err_seen[n] = e
    errors = list(_err_seen.items())

    _prune_results_to_allowed(results, tiers_used, label=fmt)

    _log_context_fingerprints(data, results, adj)

    return results, errors, adj, tiers_used


# endregion Offset Discovery Engine


# region Validation

EXPECTED_ORIGINALS = {
    "CodecProbe_ChannelCountPatch":    ("01", 1),
    "CodecProbe_ForceSuccessBranch":    ("75", 1),
    "SampleRate_Select48kNop":             ("0F 42 C1", 3),
    "OpusBitrate_Imul384k":   (None, 3),
    "AudioEncoder_BitrateMovImm":  (None, 5),
    "AudioEncoder_BitrateOrMaskNop":     ("48 09 C1", 3),
    "WebRtcHighpass_Trampoline":           (None, 11),
    "AudioFrame_StereoChannelAssign":   (None, 4),
    "OpusEncoderConfig_SetStereoChannels": ("01", 1),
    "OpusEncoderConfig_IsOkRetTrue": ("8B 11 31 C0", 4),
    "DownmixMono_BypassBranch":            ("84 C0", 2),
    "AudioEncoderCodec_ThrowNoOp":               ("41", 1),
    "ChannelDownmix_RetStub":              ("41", 1),
    "WebRtcHighpassCutoff_Injected":     (None, 0x100),
    "WebRtcDcReject_Injected":                 (None, 0x1B6),
    "OpusEncoderConfig_CtorBitrate_A":       ("00 7D 00 00", 4),
    "OpusEncoderConfig_CtorBitrate_B":       ("00 7D 00 00", 4),
    "OpusEncoderConfig_CtorUseInbandFecOn":   ("00", 1),
    "NetEq_DelayMsPerLossPercent": ("48 B8 14 00 00 00 C8 00 00 00", 10),
    "Pacer_ForceBlockAudioFalse": ("0F 94 C3", 3),
}

EXPECTED_ORIGINALS_CLANG = {
    "ChannelDownmix_RetStub":              ("55", 1),
    "OpusEncoderConfig_IsOkRetTrue": ("55 48 89 E5", 4),
    "SampleRate_Select48kNop":             (None, 4),
    "OpusBitrate_Imul384k":   ("00 7D 00", 3),
    "WebRtcHighpassCutoff_Injected":     (None, 0x100),
    "WebRtcDcReject_Injected":                 (None, 0x1B6),
}

EXPECTED_ORIGINALS_LINUX_ONLY = {
    "CodecProbe_ChannelCountPatch":    ("00", 1),
    "CodecProbe_ForceSuccessBranch":    ("74", 1),
    "AudioFrame_StereoChannelAssign":   ("4C 0F 43", 4),
    "SampleRate_Select48kNop":             ("48 0F 43 D0", 4),
    "OpusEncoderConfig_SetMultiChannelStereo": ("01", 1),
}

EXPECTED_ORIGINALS_MACHO_ONLY = {
    "AudioEncoderCodec_ThrowNoOp":               ("55", 1),
    "AudioFrame_StereoChannelAssign":   ("4C 0F 43 E0", 4),
    "CodecProbe_ForceSuccessBranch":    (None, 1),
    "SampleRate_Select48kNop":             (None, 4),
}

EXPECTED_ORIGINALS_ARM64 = {
    "AudioEncoderCodec_ThrowNoOp":               (None, 4),
    "ChannelDownmix_RetStub":              (None, 4),
    "WebRtcHighpassCutoff_Injected":     (None, 4),
    "WebRtcDcReject_Injected":                 (None, 4),
    "WebRtcHighpass_Trampoline":           (None, 4),
    "OpusEncoderConfig_SetStereoChannels": (None, 4),
    "AudioFrame_StereoChannelAssign":   (None, 4),
    "CodecProbe_ChannelCountPatch":    (None, 4),
    "DownmixMono_BypassBranch":            (None, 4),
    "OpusEncoderConfig_CtorBitrate_B":       (None, 4),
}


def _build_expected_map(fmt, arch=None):
    if arch == 'arm64':
        return dict(EXPECTED_ORIGINALS_ARM64)
    m = dict(EXPECTED_ORIGINALS)
    if fmt in ('elf', 'macho'):
        m.update(EXPECTED_ORIGINALS_CLANG)
    if fmt == 'elf':
        m.update(EXPECTED_ORIGINALS_LINUX_ONLY)
    if fmt == 'macho':
        m.update(EXPECTED_ORIGINALS_MACHO_ONLY)
    return m

PATCH_INFO = {
    "CodecProbe_ChannelCountPatch":    ("02", "Channel count 1->2"),
    "CodecProbe_ForceSuccessBranch":    ("EB", "PE: EB on short jcc. ELF: 6x NOP on jz/jnz rel32 (see discord_voice_patcher_linux.sh)"),
    "SampleRate_Select48kNop":             ("90 90 90", "cmovb->NOPs (force 48kHz)"),
    "OpusBitrate_Imul384k":   (BITRATE_PATCH_3, "imul 32000->384000 bps"),
    "AudioEncoder_BitrateMovImm":  (BITRATE_PATCH_5, "384000 in imm64"),
    "AudioEncoder_BitrateOrMaskNop":     ("90 90 90", "or rcx,rax->NOPs"),
    "WebRtcHighpass_Trampoline":           ("<dynamic: mov rax, IMAGE_BASE+HPC; ret>", "Redirect to HPC"),
    "AudioFrame_StereoChannelAssign":   ("49 89 C4 90", "Clang ELF: cmovnb r12,rax -> mov r12,rax; nop (PE/MSVC uses 49 89 C5 90 / r13)"),
    "OpusEncoderConfig_SetStereoChannels": ("02", "Channel count 1->2"),
    "OpusEncoderConfig_SetMultiChannelStereo": ("02", "MultiChannel Opus config channels 1->2 (Linux)"),
    "OpusEncoderConfig_IsOkRetTrue": ("48 C7 C0 01 00 00 00 C3", "return 1"),
    "DownmixMono_BypassBranch":            ("90 90 90 90 90 90 90 90 90 90 90 90 E9", "NOP sled + jmp"),
    "AudioEncoderCodec_ThrowNoOp":               ("C3", "ret (disable throws)"),
    "ChannelDownmix_RetStub":              ("C3", "ret (disable downmix)"),
    "WebRtcHighpassCutoff_Injected":     ("<injected: hp_cutoff>", "Custom HP cutoff + gain"),
    "WebRtcDcReject_Injected":                 ("<injected: dc_reject>", "Custom DC reject + gain"),
    "OpusEncoderConfig_CtorBitrate_A":       (BITRATE_PATCH_4, "Config qword: 32000->384000"),
    "OpusEncoderConfig_CtorBitrate_B":       (BITRATE_PATCH_4, "Config qword: 32000->384000"),
    "OpusEncoderConfig_CtorUseInbandFecOn":   ("01", "AudioEncoderOpusConfig ctor: use_inband_fec imm 0->1"),
    "NetEq_DelayMsPerLossPercent": ("48 B8 00 00 00 00 00 00 00 00", "imm64 -> 0"),
    "Pacer_ForceBlockAudioFalse": ("30 DB 90", "setz bl -> xor bl,bl; nop"),
}


def validate_offsets(data, results, adj, bin_fmt='pe'):
    print("\n" + "=" * 65)
    print("  PHASE 3: Byte Verification")
    print("=" * 65)

    verified = 0
    warnings = 0

    expected_map = _build_expected_map(bin_fmt)

    for name, config_off in sorted(results.items(), key=lambda x: x[1]):
        file_off = config_off - adj

        if file_off < 0 or file_off >= len(data):
            print(f"  [FAIL] {name:45s} offset 0x{config_off:X} out of bounds")
            warnings += 1
            continue

        if name in expected_map:
            expected_hex, length = expected_map[name]
            actual = data[file_off:file_off+length]

            if name == "CodecProbe_ForceSuccessBranch" and bin_fmt == "elf":
                peek = data[file_off : min(file_off + 6, len(data))]
                if len(peek) >= 1 and peek[0] in (0x74, 0x75):
                    print(f"  [PASS] {name:45s} original bytes: {peek[:1].hex(' ')} (short jcc)")
                    verified += 1
                    continue
                if len(peek) >= 2 and peek[0] == 0x0F and peek[1] in (0x84, 0x85):
                    print(f"  [PASS] {name:45s} jcc near rel32: {peek.hex(' ')}")
                    verified += 1
                    continue
                if len(peek) >= 6 and peek[:6] == b"\x90" * 6:
                    print(f"  [WARN] {name:45s} ALREADY PATCHED (6x NOP)")
                    warnings += 1
                    continue

            if expected_hex:
                expected = bytes.fromhex(expected_hex.replace(' ', ''))
                if actual[:len(expected)] == expected:
                    print(f"  [PASS] {name:45s} original bytes: {actual[:len(expected)].hex(' ')}")
                    verified += 1
                else:
                    patch_hex = PATCH_INFO.get(name, (None,))[0]
                    if name == "SampleRate_Select48kNop" and bin_fmt == "elf":
                        patch_hex = "90 90 90 90"
                    if patch_hex and not patch_hex.startswith('<'):
                        try:
                            patched = bytes.fromhex(patch_hex.replace(' ', ''))
                            if actual[:len(patched)] == patched:
                                print(f"  [WARN] {name:45s} ALREADY PATCHED: {actual[:len(patched)].hex(' ')}")
                                warnings += 1
                                continue
                        except ValueError:
                            pass
                    print(f"  [WARN] {name:45s} unexpected: {actual[:len(expected)].hex(' ')} (expected {expected_hex})")
                    warnings += 1
            else:
                print(f"  [INFO] {name:45s} bytes: {actual[:min(8,length)].hex(' ')} (no fixed expected)")
                verified += 1

    return verified, warnings


def check_injection_sites(data, results, adj):
    print("\n" + "=" * 65)
    print("  PHASE 4: Injection Site Capacity")
    print("=" * 65)

    for name, inject_size, desc in [("WebRtcHighpassCutoff_Injected", 0x100, "hp_cutoff"), ("WebRtcDcReject_Injected", 0x1B6, "dc_reject")]:
        if name not in results:
            print(f"  [SKIP] {name}: not found")
            continue

        file_off = results[name] - adj
        func_end = None

        for i in range(file_off, min(file_off + 0x400, len(data) - 3)):
            if data[i:i+4] == b'\xcc\xcc\xcc\xcc':
                func_end = i
                break
            if data[i] == 0xC3 and i > file_off + 8:
                nop_run = 0
                for j in range(i+1, min(i+17, len(data))):
                    if data[j] in (0x90, 0x66, 0x0F, 0x1F, 0x2E, 0x84, 0x00, 0x40):
                        nop_run += 1
                    else:
                        break
                if nop_run >= 4:
                    func_end = i + 1
                    break

        if func_end is None:
            print(f"  [INFO] {name}: no padding found; using symbol size for capacity")
            continue

        available = func_end - file_off
        margin = available - inject_size
        status = "OK" if margin >= 0 else "OVER"
        print(f"  [{status:4s}] {name:30s}  available={available} (0x{available:X})  "
              f"needed={inject_size} (0x{inject_size:X})  margin={margin:+d} bytes")

# endregion Validation


def _md5_file_hex(file_path, lower=False):
    with open(file_path, "rb") as f:
        h = hashlib.md5(f.read()).hexdigest()
    return h.lower() if lower else h


# region Output Formatters

def format_powershell_config(results, bin_info=None, file_path=None, file_size=None):
    lines = []
    fmt = (bin_info or {}).get('format', 'raw')
    adj = (bin_info or {}).get('file_offset_adjustment', 0)

    if bin_info and file_path and file_size:
        md5 = _md5_file_hex(file_path)
        build_str = ''
        if fmt == 'pe' and 'build_time' in bin_info:
            build_str = bin_info['build_time'].strftime('%b %d %Y')
        else:
            build_str = f'{fmt.upper()} binary'
        lines.append(f"    # Auto-generated by discord_voice_node_offset_finder_v5.py v{VERSION}")
        lines.append(f"    # Build: {build_str} | Size: {file_size} | MD5: {md5}")
        if fmt != 'pe':
            lines.append(f"    # Format: {fmt.upper()} | Arch: {bin_info.get('arch', '?')}")
            lines.append(f"    # Note: on macOS and Linux use the 'file_offset' values below for direct binary patching")

    lines.append("    Offsets = @{")
    ordered = _all_offset_names()
    max_len = max(len(n) for n in ordered)

    for name in ordered:
        pad = " " * (max_len - len(name))
        if name in results:
            lines.append(f"        {name}{pad} = 0x{results[name]:X}")
        else:
            lines.append(f"        {name}{pad} = 0x0")

    lines.append("    }")
    return "\n".join(lines)


def _validate_discovered_offsets(results, data, adj, margin=512):
    invalid = []
    n = len(data)
    for name, rva in list(results.items()):
        if rva == 0:
            invalid.append((name, "offset is zero (invalid)"))
            continue
        file_off = rva - adj
        if file_off < 0:
            invalid.append((name, "file offset is negative"))
            continue
        if file_off >= n - margin:
            invalid.append((name, f"0x{rva:X} (file 0x{file_off:X}) out of file bounds"))
            continue
    invalid_names = {x for x, _ in invalid}
    rva_to_names = {}
    for name, rva in results.items():
        if name in invalid_names:
            continue
        rva_to_names.setdefault(rva, []).append(name)
    for rva, names in rva_to_names.items():
        if len(names) > 1:
            for name in names[1:]:
                invalid.append((name, f"duplicate RVA 0x{rva:X} (same as {names[0]})"))
    return invalid


def _validate_pe_offsets_for_patcher(results, bin_info, file_size):
    if not bin_info or file_size is None:
        return False, "missing bin_info or file_size"
    adj = bin_info.get("file_offset_adjustment", 0xC00)
    required = set(PATCHER_OFFSET_NAMES)
    if required - set(results):
        return False, "missing required offsets"
    seen_rva = set()
    for name in PATCHER_OFFSET_NAMES:
        rva = results[name]
        if rva == 0:
            return False, f"{name} is zero"
        if rva in seen_rva:
            return False, f"duplicate RVA 0x{rva:X}"
        seen_rva.add(rva)
        file_off = rva - adj
        if file_off < 0 or file_off >= file_size - 512:
            return False, f"{name} (0x{rva:X}) out of file bounds"
    return True, None


WINDOWS_PATCHER_OFFSET_ORDER = list(WINDOWS_PATCHER_OFFSET_NAMES)


def _read_discord_app_build_sidecar(parent_dir):
    if not parent_dir:
        return None
    pdir = Path(parent_dir)
    for fname in ("discord_app_build.txt", "discord_app_build", "APP_BUILD.txt"):
        p = pdir / fname
        if not p.is_file():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    return s
        except OSError:
            continue
    return None


def _app_dir_semver_from_name(dir_name):
    m = re.match(r"(?i)^app-([\d.]+)$", dir_name)
    if not m:
        return None, ()
    s = m.group(1).strip()
    parts = []
    for p in s.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            return None, ()
    return s, tuple(parts)


def _discord_app_version_matching_install(file_path, data):
    path = Path(file_path) if file_path else None
    try:
        if data is None and path and path.is_file():
            data = path.read_bytes()
        if not data:
            return None
        sz = len(data)
        digest = hashlib.md5(data).hexdigest()
    except OSError:
        return None

    roots = []
    if sys.platform == "win32":
        la = os.environ.get("LOCALAPPDATA", "")
        if la:
            roots.extend(
                Path(la) / c
                for c in (
                    "Discord",
                    "DiscordCanary",
                    "DiscordPTB",
                    "DiscordDevelopment",
                )
            )
    elif sys.platform == "darwin":
        sup = Path.home() / "Library" / "Application Support"
        for c in ("discord", "discordcanary", "discordptb", "discorddevelopment"):
            roots.append(sup / c)

    best = None
    for root in roots:
        if not root.is_dir():
            continue
        for app_dir in root.glob("app-*"):
            if not app_dir.is_dir():
                continue
            ver_str, ver_tuple = _app_dir_semver_from_name(app_dir.name)
            if not ver_str:
                continue
            hit = False
            for node in app_dir.glob("modules/discord_voice*/discord_voice/discord_voice.node"):
                try:
                    if node.stat().st_size != sz:
                        continue
                    if hashlib.md5(node.read_bytes()).hexdigest() != digest:
                        continue
                except OSError:
                    continue
                hit = True
                break
            if not hit:
                continue
            label = root.name
            if best is None or ver_tuple > best[0]:
                best = (ver_tuple, ver_str, label)

    if best:
        return best[1], f"matching-install:{best[2]}"
    return None


def _read_manifest_discord_app_version(parent_dir):
    if not parent_dir:
        return None
    mf = Path(parent_dir) / "manifest.json"
    if not mf.is_file():
        return None
    try:
        obj = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    for key in ("discordAppVersion", "discord_app_version", "appVersion"):
        v = obj.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() != "null":
            return s
    return None


def _pe_rsrc_blob(data, bin_info):
    if not data or not bin_info or bin_info.get("format") != "pe":
        return None
    for sec in bin_info.get("sections") or []:
        if sec.get("name") == ".rsrc":
            ro = sec.get("raw_offset") or 0
            rs = sec.get("raw_size") or 0
            if ro > 0 and rs > 0 and ro + rs <= len(data):
                return data[ro : ro + rs]
    return None


def _utf16_stringfileinfo_value(blob, key_ascii):
    if not blob or not key_ascii:
        return None
    key = (key_ascii + "\0").encode("utf-16le")
    idx = 0
    while idx < len(blob):
        j = blob.find(key, idx)
        if j < 0:
            return None
        pos = j + len(key)
        while pos < len(blob) and blob[pos] == 0:
            pos += 1
        chars = bytearray()
        while pos + 1 < len(blob):
            if blob[pos] == 0 and blob[pos + 1] == 0:
                break
            chars.append(blob[pos])
            chars.append(blob[pos + 1])
            pos += 2
        try:
            s = chars.decode("utf-16le").strip()
        except (UnicodeDecodeError, UnicodeError):
            idx = j + 1
            continue
        if s and re.fullmatch(r"[\d.]+", s):
            return s
        idx = j + 1
    return None


def resolve_discord_app_version(file_path, data=None, bin_info=None, cli_version=None):
    path = Path(file_path) if file_path else None
    parent = path.parent if path else None

    if cli_version:
        v = str(cli_version).strip()
        if v:
            return v, "cli"

    env_v = (os.environ.get("DISCORD_APP_VERSION") or os.environ.get("DISCORD_APP_BUILD") or "").strip()
    if env_v:
        return env_v, "environment"

    side = _read_discord_app_build_sidecar(parent)
    if side:
        return side, "discord_app_build.txt"

    man = _read_manifest_discord_app_version(parent)
    if man:
        return man, "manifest.json"

    if path:
        for part in path.resolve().parts:
            m = re.match(r"(?i)^app-([\d.]+)$", part)
            if m:
                return m.group(1).strip(), "path"
        s = os.path.normpath(str(path))
        m = re.search(r"(?i)app-\s*([\d.]+)", s)
        if m:
            return m.group(1).strip(), "path"

    install_ver = _discord_app_version_matching_install(path, data)
    if install_ver:
        return install_ver[0], install_ver[1]

    if data is not None and bin_info and bin_info.get("format") == "pe":
        blob = _pe_rsrc_blob(data, bin_info)
        if blob:
            fv = _utf16_stringfileinfo_value(blob, "FileVersion")
            if fv:
                return fv, "pe:FileVersion"
            pv = _utf16_stringfileinfo_value(blob, "ProductVersion")
            if pv:
                return pv, "pe:ProductVersion"

    return "unspecified", "none"


def format_windows_patcher_block(results, bin_info, file_path, file_size, discord_app_version=None):
    if not bin_info or not file_path or file_size is None:
        return None
    if bin_info.get('format') != 'pe':
        return None
    ok, _err = _validate_pe_offsets_for_patcher(results, bin_info, file_size)
    if not ok:
        return None
    with open(file_path, 'rb') as f:
        raw = f.read()
    md5 = hashlib.md5(raw).hexdigest().lower()
    if discord_app_version is None:
        app_ver, _src = resolve_discord_app_version(
            Path(file_path), data=raw, bin_info=bin_info, cli_version=None)
    else:
        app_ver = str(discord_app_version).strip() or "unspecified"
    lines = [
        "# region Offsets (PASTE HERE)",
        "",
        "$Script:OffsetsMeta = @{",
        '    FinderVersion = "discord_voice_node_offset_finder.py v%s"' % VERSION,
        '    DiscordAppVersion = "%s"' % app_ver,
        "    Size          = %s" % file_size,
        '    MD5           = "%s"' % md5,
        "}",
        "",
        "$Script:Offsets = @{",
    ]
    ordered = list(PATCHER_OFFSET_NAMES)
    max_len = max((len(n) for n in ordered), default=0)
    for name in ordered:
        if name not in results:
            continue
        pad = " " * (max_len - len(name))
        lines.append("    %s%s = 0x%X" % (name, pad, results[name]))
    lines.append("}")
    lines.append("")
    lines.append("# endregion Offsets")
    return "\n".join(lines) + "\n"


PATCHER_DEBUG_GROUPS = {
    "STEREO": [
        ("CodecProbe_ChannelCountPatch", "LocalUser::CommitAudioCodec / ApplySettings (channel 1->2)"),
        ("CodecProbe_ForceSuccessBranch", "LocalUser::CommitAudioCodec / ApplySettings (force success jmp)"),
        ("AudioFrame_StereoChannelAssign", "EngineAudioTransport::CreateAudioFrameToProcess"),
        ("OpusEncoderConfig_SetStereoChannels", "webrtc::AudioEncoderOpusConfig ctor (ch 1->2)"),
        ("DownmixMono_BypassBranch", "CapturedAudioProcessor::Process (bypass mono path)"),
    ],
    "BITRATE": [
        ("OpusBitrate_Imul384k", "OpusBitrate_Imul384k (384kbps)"),
        ("AudioEncoder_BitrateMovImm", "AudioEncoder_BitrateMovImm (384kbps)"),
        ("AudioEncoder_BitrateOrMaskNop", "AudioEncoder_BitrateOrMaskNop (NOP)"),
    ],
    "SAMPLERATE": [
        ("SampleRate_Select48kNop", "SampleRate_Select48kNop (NOP cmovb)"),
    ],
    "FILTER": [
        ("WebRtcHighpass_Trampoline", "WebRtcHighpass_Trampoline (RET stub)"),
        ("WebRtcHighpassCutoff_Injected", "WebRtcHighpassCutoff_Injected (inject hp_cutoff)"),
        ("WebRtcDcReject_Injected", "WebRtcDcReject_Injected (inject dc_reject)"),
        ("ChannelDownmix_RetStub", "downmix_and_resample early RET"),
        ("OpusEncoderConfig_IsOkRetTrue", "webrtc::AudioEncoderOpusConfig::IsOK (RET true)"),
        ("AudioEncoderCodec_ThrowNoOp", "AudioEncoderCodec_ThrowNoOp (RET)"),
    ],
    "ENCODER": [
        ("OpusEncoderConfig_CtorBitrate_A", "OpusEncoderConfig ctor literal (32000->384000)"),
        ("OpusEncoderConfig_CtorBitrate_B", "OpusEncoderConfig ctor literal (32000->384000)"),
    ],
    "FEC": [
        ("OpusEncoderConfig_CtorUseInbandFecOn", "AudioEncoderOpusConfig ctor: default use_inband_fec -> 1 (Opus FEC)"),
    ],
    "NETEQ": [
        ("NetEq_DelayMsPerLossPercent", "NetEq ms_per_loss_percent -> 0 (FEC friendly; no Opus loss-hint hacks)"),
    ],
    "PACING": [
        ("Pacer_ForceBlockAudioFalse", "Pacer BlockAudio -> false"),
    ],
    "DISCORD_API_LOCK": [
        ("Discord_SetAutomaticGainControlConfig", "Discord::SetAutomaticGainControlConfig (AGC off)"),
        ("Discord_SetAutomaticGainControl_bool", "Discord::SetAutomaticGainControl(bool) (AGC off)"),
        ("Discord_SetNoiseSuppression_bool", "Discord::SetNoiseSuppression(bool) (NS off)"),
        ("Discord_SetEchoCancellation_bool", "Discord::SetEchoCancellation(bool) (echo cancel off)"),
        ("Discord_SetEchoCancellationPreEcho_bool", "Discord::SetEchoCancellationPreEcho (echo cancel off)"),
        ("Discord_EnableBuiltInAcousticEchoCancel_bool", "Discord::EnableBuiltInAEC (acoustic echo off; not Opus FEC)"),
        ("Discord_SetNoiseCancellation_bool", "Discord::SetNoiseCancellation (Krisp NC off)"),
        ("Discord_SetNoiseCancellationDuringProcessing_bool", "Discord::SetNoiseCancellationDuringProcessing (Krisp NC off)"),
    ],
}


def format_windows_debug_mode(results=None):
    lines = []
    for group_name, patches in PATCHER_DEBUG_GROUPS.items():
        lines.append(f"  [{group_name}]")
        for key, _ in patches:
            lines.append(f"    {key}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_linux_patcher_block(results, bin_info, file_path, file_size):
    if not bin_info or not file_path or file_size is None:
        return None
    fmt = bin_info.get('format', 'raw')
    if fmt != 'elf':
        return None
    adj = bin_info.get('file_offset_adjustment', 0)
    md5 = _md5_file_hex(file_path, lower=True)
    lines = [
        "# discord_voice_patcher_linux.sh — EXPECTED_* + OFFSET_* from finder",
        f'EXPECTED_MD5="{md5}"',
        f"EXPECTED_SIZE={file_size}",
        "",
    ]
    ordered = WINDOWS_PATCHER_OFFSET_ORDER
    for name in ordered:
        if name in results:
            file_off = results[name] - adj
            lines.append(f"OFFSET_{name}=0x{file_off:X}")
        else:
            lines.append(f"OFFSET_{name}=0x0")
    extra_val = 0
    if "OpusEncoderConfig_SetMultiChannelStereo" in results:
        extra_val = results["OpusEncoderConfig_SetMultiChannelStereo"] - adj
    extra = f"OFFSET_OpusEncoderConfig_SetMultiChannelStereo=0x{extra_val:X}"
    inserted = False
    for i, line in enumerate(lines):
        if line.startswith("OFFSET_OpusEncoderConfig_SetStereoChannels="):
            lines.insert(i + 1, extra)
            inserted = True
            break
    if not inserted:
        lines.append(extra)
    lines.append("FILE_OFFSET_ADJUSTMENT=0")
    lines.append("")
    lines.append("# Required offset names (18 Windows + Linux MultiChannel); validate before build.")
    lines.append("REQUIRED_OFFSET_NAMES=(")
    lines.append("    AudioFrame_StereoChannelAssign OpusEncoderConfig_SetStereoChannels OpusEncoderConfig_SetMultiChannelStereo DownmixMono_BypassBranch")
    lines.append("    CodecProbe_ChannelCountPatch CodecProbe_ForceSuccessBranch OpusBitrate_Imul384k")
    lines.append("    AudioEncoder_BitrateMovImm AudioEncoder_BitrateOrMaskNop SampleRate_Select48kNop")
    lines.append("    WebRtcHighpass_Trampoline WebRtcHighpassCutoff_Injected WebRtcDcReject_Injected ChannelDownmix_RetStub")
    lines.append("    OpusEncoderConfig_IsOkRetTrue AudioEncoderCodec_ThrowNoOp")
    lines.append("    OpusEncoderConfig_CtorBitrate_A OpusEncoderConfig_CtorBitrate_B OpusEncoderConfig_CtorUseInbandFecOn")
    lines.append(")")
    return "\n".join(lines) + "\n"


def format_macos_patcher_block(results, bin_info, file_path, file_size,
                               arm64_results=None, arm64_info=None, arm64_adj=None):
    if not bin_info or not file_path or file_size is None:
        return None
    fmt = bin_info.get('format', 'raw')
    if fmt != 'macho':
        return None
    adj = bin_info.get('file_offset_adjustment', 0)
    md5 = _md5_file_hex(file_path, lower=True)
    ordered = _all_offset_names()
    n_expected = len(ordered)

    x86_found = sum(1 for n in ordered if n in results)

    lines = [
        "# macOS/Clang offsets - Auto-generated by discord_voice_node_offset_finder_v5.py v" + VERSION,
        f"# Build: MACHO binary | Size: {file_size} | MD5: {md5}",
        "# Using file_offset values for direct binary patching (fat file offset when universal)",
    ]

    lines.append(f"# x86_64 slice offsets ({x86_found}/{n_expected})")
    lines.append("declare -A OFFSETS=(")
    for name in ordered:
        if name in results:
            abs_file_off = results[name] - adj
            lines.append(f"    [{name}]=0x{abs_file_off:X}")
        else:
            lines.append(f"    [{name}]=0x0")
    lines.append(")")

    if arm64_results and arm64_info:
        a64_adj = arm64_adj if arm64_adj is not None else arm64_info.get('file_offset_adjustment', 0)
        a64_found = sum(1 for n in ordered if n in arm64_results)

        lines.append("")
        lines.append(f"# arm64 slice offsets ({a64_found}/{n_expected})")
        lines.append("declare -A ARM64_OFFSETS=(")
        for name in ordered:
            if name in arm64_results:
                abs_file_off = arm64_results[name] - a64_adj
                lines.append(f"    [{name}]=0x{abs_file_off:X}")
            else:
                lines.append(f"    [{name}]=0x0")
        lines.append(")")

    lines.append("FILE_OFFSET_ADJUSTMENT=0")
    return "\n".join(lines)


def format_json(results, bin_info, file_path, file_size, adj, tiers_used,
                arm64_results=None, arm64_info=None, arm64_adj=None, arm64_tiers=None,
                discord_app_version=None, discord_app_version_source=None):
    fmt = bin_info.get('format', 'raw') if bin_info else 'pe'
    offsets_only = {name: off for name, off in results.items() if name in ALLOWED_OFFSET_NAMES}
    out = {
        "tool": "discord_voice_node_offset_finder",
        "version": VERSION,
        "file": str(file_path),
        "file_size": file_size,
        "md5": _md5_file_hex(file_path),
        "format": fmt,
        "arch": bin_info.get('arch', 'unknown') if bin_info else 'unknown',
        "file_offset_adjustment": hex(adj),
        "offsets": {name: hex(off) for name, off in sorted(offsets_only.items())},
        "resolution_tiers": {k: v for k, v in (tiers_used or {}).items() if k in ALLOWED_OFFSET_NAMES},
        "total_found": len(offsets_only),
        "total_expected": len(ALL_OFFSET_NAMES),
        "linux_only_offset_names": list(LINUX_ONLY_OFFSET_NAMES),
        "discord_app_version": discord_app_version or "unspecified",
        "discord_app_version_source": (discord_app_version_source or "none"),
    }

    if fmt == 'pe' and bin_info:
        out["pe_timestamp"] = bin_info.get('timestamp')
        out["pe_build_time"] = bin_info['build_time'].isoformat() if 'build_time' in bin_info else None
        out["image_base"] = hex(bin_info.get('image_base', 0))
    elif fmt in ('elf', 'macho') and bin_info:
        out["image_base"] = hex(bin_info.get('image_base', 0))
        out["has_symbols"] = bin_info.get('has_symbols', False)
        out["file_offsets"] = {name: hex(off - adj) for name, off in sorted(offsets_only.items())}

    expected_map = _build_expected_map(fmt)
    patches = []
    for name in _all_offset_names():
        if name not in offsets_only:
            continue
        file_off = offsets_only[name] - adj
        expected_hex, length = expected_map.get(name, (None, 0))
        patches.append({
            "name": name,
            "file_offset": file_off,
            "file_offset_hex": hex(file_off),
            "expected_original": expected_hex.replace(' ', '') if expected_hex else None,
            "length": length,
        })
    out["patches"] = patches

    if fmt in ('elf', 'macho'):
        inject = []
        for name, size in [("WebRtcHighpassCutoff_Injected", 0x100), ("WebRtcDcReject_Injected", 0x1B6)]:
            if name in offsets_only:
                file_off = offsets_only[name] - adj
                inject.append({
                    "name": name,
                    "file_offset": file_off,
                    "file_offset_hex": hex(file_off),
                    "inject_size": size,
                })
        out["injection_sites"] = inject

    if bin_info and fmt == 'macho' and 'stereo_patches' in bin_info:
        out["stereo_patches"] = bin_info["stereo_patches"]

    if arm64_results and arm64_info:
        a64_adj = arm64_adj if arm64_adj is not None else arm64_info.get('file_offset_adjustment', 0)
        a64_offsets = {}
        a64_file_offsets = {}
        a64_tiers_out = {}
        for name in sorted(arm64_results.keys()):
            if name in ALLOWED_OFFSET_NAMES:
                abs_file_off = arm64_results[name] - a64_adj
                a64_offsets[name] = hex(arm64_results[name])
                a64_file_offsets[name] = hex(abs_file_off)
                if arm64_tiers and name in arm64_tiers:
                    a64_tiers_out[name] = arm64_tiers[name]
        out["arm64_offsets"] = a64_offsets
        out["arm64_file_offsets"] = a64_file_offsets
        out["arm64_resolution_tiers"] = a64_tiers_out
        out["arm64_found"] = len(a64_offsets)
        out["arm64_expected"] = len(ALL_OFFSET_NAMES)

    return json.dumps(out, indent=2, ensure_ascii=True)

# endregion Output Formatters


# region Visualization

def generate_viz_graph(results, out_dir):
    if not VIZ_AVAILABLE:
        return None
    try:
        G = nx.DiGraph()
        sig_names = {s.name for s in SIGNATURES}
        for name in results:
            color = '#5865F2' if name in sig_names else '#ED4245'
            G.add_node(name, color=color)
        for derived, paths in DERIVATIONS.items():
            if derived not in results:
                continue
            for anchor, delta in paths:
                if anchor in results:
                    G.add_edge(anchor, derived, label=f"+0x{delta:X}")
                    break
        if len(G.nodes) == 0:
            return None

        plt.figure(figsize=(14, 9))
        pos = nx.spring_layout(G, k=2.5, iterations=60, seed=42)
        colors = [G.nodes[n].get('color', '#99AAB5') for n in G.nodes()]
        nx.draw(G, pos, with_labels=True, node_color=colors, node_size=2800,
                font_size=7, font_weight='bold', arrows=True, edge_color='#72767D',
                arrowsize=15, font_color='white', edgecolors='#2C2F33', linewidths=1.5)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7, font_color='#B9BBBE')
        plt.title("Offset Derivation Graph", fontsize=14, fontweight='bold', color='#FFFFFF')
        plt.gca().set_facecolor('#36393F')
        plt.gcf().set_facecolor('#2C2F33')
        plt.axis('off')

        viz_path = out_dir / 'offsets_graph.png'
        plt.savefig(viz_path, dpi=150, bbox_inches='tight', facecolor='#2C2F33')
        plt.close()
        return viz_path
    except Exception:
        try:
            plt.close()
        except Exception:
            pass
        return None

# endregion Visualization


# region Auto-Detection

def find_discord_node():
    clients = ['discord', 'discordcanary', 'discordptb', 'discorddevelopment']
    clients_cap = ['Discord', 'DiscordCanary', 'DiscordPTB', 'DiscordDevelopment']

    def _search_modules_dirs(base):
        if not base.exists():
            return None
        for app_dir in sorted(base.glob('app-*'), reverse=True):
            modules = app_dir / 'modules'
            if not modules.exists():
                continue
            for vd in modules.glob('discord_voice*'):
                for candidate in [vd / 'discord_voice' / 'discord_voice.node', vd / 'discord_voice.node']:
                    if candidate.exists():
                        return candidate
        modules = base / 'modules'
        if modules.exists():
            for vd in modules.glob('discord_voice*'):
                for candidate in [vd / 'discord_voice' / 'discord_voice.node', vd / 'discord_voice.node']:
                    if candidate.exists():
                        return candidate
        return None

    def _search_recursive(base, max_depth=5):
        if not base.exists():
            return None
        for candidate in base.rglob('discord_voice.node'):
            try:
                rel = candidate.relative_to(base)
                if len(rel.parts) <= max_depth:
                    return candidate
            except ValueError:
                pass
        return None

    if sys.platform == 'win32':
        localappdata = os.environ.get('LOCALAPPDATA', '')
        if localappdata:
            for client in clients_cap:
                found = _search_modules_dirs(Path(localappdata) / client)
                if found:
                    return found

    elif sys.platform == 'darwin':
        home = Path.home()

        for app_name in ['Discord', 'Discord Canary', 'Discord PTB', 'Discord Development']:
            app_path = Path(f'/Applications/{app_name}.app/Contents/Resources')
            if app_path.exists():
                found = _search_modules_dirs(app_path)
                if found:
                    return found
                found = _search_recursive(app_path.parent / 'Frameworks', max_depth=6)
                if found:
                    return found

        app_support = home / 'Library' / 'Application Support'
        for client in clients:
            found = _search_modules_dirs(app_support / client)
            if found:
                return found

        for cask_dir in [Path('/usr/local/Caskroom'), Path('/opt/homebrew/Caskroom')]:
            if cask_dir.exists():
                for d in cask_dir.glob('discord*'):
                    found = _search_recursive(d, max_depth=8)
                    if found:
                        return found

        print("  Typical macOS locations:")
        print("    /Applications/Discord.app/Contents/Resources/app-*/modules/discord_voice*/")
        print("    ~/Library/Application Support/discord/*/modules/discord_voice*/")

    else:
        home = Path.home()

        config_dir = home / '.config'
        for client in clients:
            found = _search_modules_dirs(config_dir / client)
            if found:
                return found

        flatpak_base = home / '.var' / 'app'
        for flatpak_id in ['com.discordapp.Discord', 'com.discordapp.DiscordCanary']:
            flatpak = flatpak_base / flatpak_id
            if flatpak.exists():
                for sub in ['config/discord', 'config/discordcanary', '.config/discord', '.config/discordcanary']:
                    found = _search_modules_dirs(flatpak / sub)
                    if found:
                        return found
                found = _search_recursive(flatpak, max_depth=8)
                if found:
                    return found

        for snap_base in [Path('/snap'), home / 'snap']:
            for client in ['discord', 'discord-canary']:
                snap_dir = snap_base / client
                if snap_dir.exists():
                    found = _search_recursive(snap_dir, max_depth=8)
                    if found:
                        return found

        for sys_base in ['/opt', '/usr/share', '/usr/lib']:
            for pattern in ['discord*', 'Discord*']:
                for d in Path(sys_base).glob(pattern):
                    if d.is_dir():
                        found = _search_recursive(d, max_depth=6)
                        if found:
                            return found

        for d in home.glob('.discord*'):
            found = _search_recursive(d, max_depth=6)
            if found:
                return found

        for d in Path('/tmp').glob('.mount_Discord*'):
            found = _search_recursive(d, max_depth=6)
            if found:
                return found

        print("  Typical Linux locations:")
        print("    ~/.config/discord/*/modules/discord_voice*/")
        print("    ~/.var/app/com.discordapp.Discord/config/discord/*/modules/discord_voice*/  (Flatpak)")
        print("    /snap/discord/current/usr/share/discord/modules/discord_voice*/  (Snap)")
        print("    /opt/discord/modules/discord_voice*/  (deb/rpm)")

    return None

# endregion Auto-Detection


# region Main

def _cleanup_created_files(path_list):
    for p in path_list:
        try:
            Path(p).unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass


def main():
    created_files = []
    atexit.register(_cleanup_created_files, created_files)

    json_only = '--json' in sys.argv
    quiet = ('--quiet' in sys.argv or '-q' in sys.argv) or json_only
    export_path = None
    cli_discord_ver = None
    file_arg = None
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == '--export' and i + 1 < len(sys.argv):
            export_path = sys.argv[i + 1]
            i += 2
            continue
        if a == '--discord-version' and i + 1 < len(sys.argv):
            cli_discord_ver = sys.argv[i + 1].strip()
            i += 2
            continue
        if a in ('--json', '--quiet', '-q'):
            i += 1
            continue
        if a.startswith('-'):
            i += 1
            continue
        if file_arg is None:
            file_arg = a
        i += 1

    if not quiet:
        print("=" * 65)
        print(f"  Discord Voice Node Offset Finder v{VERSION}")
        print("  Cross-platform tiered scanning with chain-aware derivation")
        print("=" * 65)

    if file_arg:
        file_path = Path(file_arg)
    else:
        print("\nNo file specified, searching for Discord install...")
        file_path = find_discord_node()
        if file_path:
            print(f"  Found: {file_path}")
        else:
            print("  Not found. Usage: python discord_voice_node_offset_finder_v5.py [--discord-version 1.0.xxxx] <path>")
            sys.exit(1)

    if not file_path.exists():
        print(f"\nERROR: File not found: {file_path}")
        sys.exit(1)

    data = file_path.read_bytes()
    file_size = len(data)
    if not quiet:
        print(f"\n  File: {file_path}")
        print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
        print(f"  MD5:  {hashlib.md5(data).hexdigest()}")

    bin_info = detect_binary_format(data)
    fmt = bin_info.get('format', 'raw')
    adj = bin_info.get('file_offset_adjustment', 0)
    arch = bin_info.get('arch', 'unknown')
    dapp_ver, dapp_src = resolve_discord_app_version(
        file_path, data=data, bin_info=bin_info, cli_version=cli_discord_ver)

    if not quiet:
        print(f"\n  Binary Format:       {fmt.upper()}")
        print(f"  Architecture:        {arch}")
        if bin_info.get('note'):
            print(f"  NOTE: {bin_info['note']}")

    if fmt == 'pe' and not quiet:
        print(f"  PE Image Base:       0x{bin_info['image_base']:X}")
        if 'build_time' in bin_info:
            print(f"  PE Timestamp:        {bin_info['build_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        ts = bin_info.get('text_section')
        if ts:
            print(f"  Offset Adjustment:   0x{adj:X}  (.text VA 0x{ts['vaddr']:X} - raw 0x{ts['raw_offset']:X})")
        else:
            print(f"  Offset Adjustment:   0x{adj:X}  (fallback)")
        for s in bin_info.get('sections', []):
            print(f"    {s['name']:8s}  VA=0x{s['vaddr']:08X}  Size=0x{s['raw_size']:08X}  Raw=0x{s['raw_offset']:08X}")

    elif fmt == 'elf' and not quiet:
        ts = bin_info.get('text_section')
        if ts:
            print(f"  Offset Adjustment:   0x{adj:X}  (.text VA 0x{ts['vaddr']:X} - raw 0x{ts['raw_offset']:X})")
        else:
            print(f"  Offset Adjustment:   0x{adj:X}")
        n_func = len(bin_info.get('func_symbols', {}))
        has_sym = bin_info.get('has_symbols', False)
        print(f"  Symbol Table:        {'YES' if has_sym else 'NO'} ({n_func} function symbols)")
        if has_sym:
            print(f"  NOTE: Linux nodes usually ship with symbols; resolution uses the symbol table.")

    elif fmt == 'macho' and not quiet:
        ts = bin_info.get('text_section')
        if ts:
            print(f"  Offset Adjustment:   0x{adj:X}  (__TEXT,__text VA 0x{ts['vaddr']:X} - raw 0x{ts['raw_offset']:X})")
        else:
            print(f"  Offset Adjustment:   0x{adj:X}")
        if bin_info.get('fat_offset'):
            print(f"  Fat Binary:          x86_64 slice at offset 0x{bin_info['fat_offset']:X} ({bin_info.get('fat_size', 0):,} bytes)")
        if bin_info.get('arm64_info'):
            a64 = bin_info['arm64_info']
            print(f"                       arm64  slice at offset 0x{a64.get('fat_offset', 0):X} ({a64.get('fat_size', 0):,} bytes)")
            n_a64_sym = len(a64.get('func_symbols', {}))
            if n_a64_sym > 50:
                print(f"  arm64 Symbols:       YES ({n_a64_sym} function symbols)")
        has_sym = bin_info.get('has_symbols', False)
        if has_sym:
            n_func = len(bin_info.get('func_symbols', {}))
            print(f"  x86_64 Symbol Table: YES ({n_func} function symbols)")

    elif fmt == 'raw' and not quiet:
        print(f"  WARNING: Could not parse binary format - using raw scan (adj=0)")

    if not quiet:
        print(f"  Discord app build:   {dapp_ver}  (source: {dapp_src})")

    pe_info = bin_info if fmt == 'pe' else None

    stereo_patches = []
    if fmt == 'macho':
        stereo_patches = find_macos_stereo_patches(data)
        if stereo_patches:
            bin_info["stereo_patches"] = stereo_patches

    verbose = not quiet
    emitted_json_text = None
    if quiet:
        _stdout_main = sys.stdout
        sys.stdout = io.StringIO()
    exit_code = 0
    results, errors, adj, tiers_used = None, [], 0, {}
    arm64_results = {}
    arm64_adj = 0
    arm64_tiers = {}
    arm64_info = bin_info.get("arm64_info") if bin_info else None
    try:
        results, errors, adj, tiers_used = discover_offsets(data, bin_info, verbose=verbose)
        verified, warnings = validate_offsets(data, results, adj, bin_fmt=fmt)
        check_injection_sites(data, results, adj)

        if fmt == 'pe':
            ts = bin_info.get('text_section')
            if ts:
                t_start = ts['raw_offset']
                t_end = ts['raw_offset'] + ts['raw_size']
            else:
                t_start = 0
                t_end = len(data)
            run_bitrate_audit_pe(data, results, adj, t_start, t_end)

        xval_warnings = _cross_validate(results, adj, data, tiers_used=tiers_used, bin_fmt=fmt)
        if xval_warnings:
            print("\n" + "=" * 65)
            print("  PHASE 5: Cross-Validation")
            print("=" * 65)
            for w in xval_warnings:
                print(f"  [XVAL] {w}")

        if arm64_info and arm64_info.get("arch") == "arm64":
            print("\n" + "=" * 65)
            print("  ARM64 OFFSET DISCOVERY (Apple Silicon)")
            print("=" * 65)
            n_arm64_sym = len(arm64_info.get('func_symbols', {}))
            print(f"  arm64 slice: fat_offset=0x{arm64_info.get('fat_offset', 0):X}  "
                  f"size={arm64_info.get('fat_size', 0):,} bytes")
            print(f"  arm64 symbols: {n_arm64_sym} functions  "
                  f"adjustment=0x{arm64_info.get('file_offset_adjustment', 0):X}")

            arm64_results, _arm64_errors, arm64_adj, arm64_tiers = \
                discover_offsets_arm64(data, arm64_info)

        if len(results) >= 10:
            viz_path = generate_viz_graph(results, file_path.parent)
            if viz_path:
                created_files.append(viz_path)
                print(f"\n  Dependency graph saved: {viz_path}")

        print("\n" + "=" * 65)
        print("  RESULTS SUMMARY")
        print("=" * 65)
        print(f"  Format:           {fmt.upper()} ({arch})")
        if fmt == 'pe':
            patcher_count, n_pk = count_patcher_offsets_found(results)
            print(f"  Windows patcher:   {patcher_count} / {n_pk}  (required for Discord_voice_node_patcher.ps1)")
            core_hits = sum(1 for n in ALL_OFFSET_NAMES if n in results)
            print(f"  Core offsets:      {core_hits} / {len(ALL_OFFSET_NAMES)}  (stereo/codec)")
            print(f"  x86_64 keys in map: {len(results)}")
        else:
            core_hits = sum(1 for n in ALL_OFFSET_NAMES if n in results)
            print(f"  Core offsets:       {core_hits} / {len(ALL_OFFSET_NAMES)}")
            print(f"  x86_64 found:      {len(results)} (including platform extras in map)")
        print(f"  Bytes verified:   {verified}")
        print(f"  Warnings:         {warnings}")
        print(f"  Cross-validation: {len(xval_warnings)} issue(s)" if xval_warnings else "  Cross-validation: clean")
        print(f"  Errors:           {len(errors)}")

        if arm64_info:
            ac = sum(1 for n in ALL_OFFSET_NAMES if n in arm64_results)
            print(f"  arm64 core:       {ac} / {len(ALL_OFFSET_NAMES)}  (map size {len(arm64_results)})")

        tier_counts = {}
        for name, tier in tiers_used.items():
            bucket = tier.split('(')[0].split('-')[0]
            tier_counts[bucket] = tier_counts.get(bucket, 0) + 1
        if tier_counts:
            print(f"  Resolution:       {', '.join(f'{k}: {v}' for k, v in sorted(tier_counts.items()))}")

        if errors:
            print(f"\n  Failed offsets:")
            for name, err in errors:
                print(f"    {name}: {err}")

        if results and fmt == 'elf':
            print("\n" + "=" * 65)
            print("  OFFSET TABLE (config VA / file offset)")
            print("=" * 65)
            print(f"  {'Name':<45s} {'config_va':>12s} {'file_offset':>12s}  tier")
            print(f"  {'-'*45} {'-'*12} {'-'*12}  {'-'*20}")
            for name in _all_offset_names():
                if name in results:
                    config_off = results[name]
                    file_off = config_off - adj
                    tier = tiers_used.get(name, '?')
                    print(f"  {name:<45s} 0x{config_off:>08X}  0x{file_off:>08X}  [{tier}]")
                else:
                    print(f"  {name:<45s} {'NOT FOUND':>12s}")
            print(f"\n  # Note: on Linux use the 'file_offset' values for direct binary patching")

        if results:
            if fmt == 'pe':
                win_block = format_windows_patcher_block(results, bin_info, file_path, file_size, discord_app_version=dapp_ver)
                if not win_block and bin_info and file_size is not None:
                    ok, err = _validate_pe_offsets_for_patcher(results, bin_info, file_size)
                    if not ok:
                        print(f"\n  [WARN] Windows patcher block skipped: {err}")
                if win_block:
                    print("\n" + "=" * 65)
                    print("  COPY BELOW -> Discord_voice_node_patcher.ps1")
                    print("  Replace the entire # region Offsets (PASTE HERE) ... # endregion Offsets section")
                    print("=" * 65)
                    print("")
                    print("--- BEGIN COPY (Windows) ---")
                    print(win_block, end="")
                    print("--- END COPY ---")
                    print("")
                    print("  DEBUG MODE (matches patcher GUI groups)")
                    print("  " + "-" * 60)
                    print(format_windows_debug_mode(results))
                    print("")

            if fmt == 'elf':
                ps_config = format_powershell_config(results, bin_info, file_path, file_size)
                print("\n" + "=" * 65)
                print("  PATCHER OFFSET TABLE (copy-paste into patcher)")
                print("=" * 65)
                print(ps_config)

            if fmt == 'elf':
                linux_block = format_linux_patcher_block(results, bin_info, file_path, file_size)
                if linux_block:
                    print("\n" + "=" * 65)
                    print("  COPY BELOW -> discord_voice_patcher_linux.sh")
                    print("  Replace EXPECTED_MD5, EXPECTED_SIZE, and OFFSET_* section")
                    print("=" * 65)
                    print("")
                    print("--- BEGIN COPY (Linux) ---")
                    print(linux_block)
                    print("--- END COPY ---")
                    print("")
            elif fmt == 'macho':
                macos_block = format_macos_patcher_block(
                    results, bin_info, file_path, file_size,
                    arm64_results=arm64_results if arm64_results else None,
                    arm64_info=arm64_info,
                    arm64_adj=arm64_adj if arm64_results else None)
                if macos_block:
                    print("")
                    print("--- BEGIN COPY (macOS) ---")
                    print(macos_block)
                    print("--- END COPY ---")
                    print("")

            if fmt == 'elf':
                offset_names = _all_offset_names()
                max_name_len = max(len(n) for n in offset_names)
                print(f"\n    # File offsets for direct binary patching (hex editor):")
                print("    FileOffsets = @{")
                for name in offset_names:
                    pad = " " * (max_name_len - len(name))
                    if name in results:
                        file_off = results[name] - adj
                        print(f"        {name}{pad} = 0x{file_off:X}")
                    else:
                        print(f"        {name}{pad} = 0x0")
                print("    }")

            stub_line = ""
            if fmt == 'pe' and bin_info and "WebRtcHighpassCutoff_Injected" in results:
                hpc_va = bin_info['image_base'] + results["WebRtcHighpassCutoff_Injected"]
                va_bytes = struct.pack('<Q', hpc_va)
                stub = b'\x48\xB8' + va_bytes + b'\xC3'
                stub_line = f"\n  WebRtcHighpass_Trampoline stub: {stub.hex(' ')}\n    mov rax, 0x{hpc_va:X}; ret"
                print(stub_line)

            script_dir = Path(__file__).resolve().parent
            if fmt == 'pe':
                wb = format_windows_patcher_block(results, bin_info, file_path, file_size, discord_app_version=dapp_ver)
                file_content = [wb] if wb else []
            elif fmt == 'macho':
                mb = format_macos_patcher_block(
                    results, bin_info, file_path, file_size,
                    arm64_results=arm64_results if arm64_results else None,
                    arm64_info=arm64_info,
                    arm64_adj=arm64_adj if arm64_results else None)
                file_content = [mb] if mb else []
            else:
                ps_config = format_powershell_config(results, bin_info, file_path, file_size)
                file_content = [ps_config]
                file_content.append("\n# File offsets for direct binary patching:")
                for name in _all_offset_names():
                    if name in results:
                        file_content.append(f"# {name} = file:0x{results[name] - adj:X}  config:0x{results[name]:X}")

            for try_dir in [script_dir, file_path.parent, Path.cwd()]:
                try:
                    out_path = try_dir / "offsets.txt"
                    out_path.write_text("\n".join(file_content), encoding="ascii")
                    created_files.append(out_path)
                    print(f"\n  Offset file saved: {out_path}")
                    break
                except Exception:
                    continue

            try:
                json_text = format_json(
                    results, bin_info, file_path, file_size, adj, tiers_used,
                    arm64_results=arm64_results if arm64_results else None,
                    arm64_info=arm64_info,
                    arm64_adj=arm64_adj if arm64_results else None,
                    arm64_tiers=arm64_tiers if arm64_results else None,
                    discord_app_version=dapp_ver,
                    discord_app_version_source=dapp_src)
                emitted_json_text = json_text
                if json_only:
                    pass
                elif export_path:
                    Path(export_path).write_text(json_text, encoding="ascii")
                    if not quiet:
                        print(f"  JSON exported: {export_path}")
                else:
                    json_path = file_path.with_suffix('.offsets.json')
                    json_path.write_text(json_text, encoding="ascii")
                    created_files.append(json_path)
                    print(f"  JSON saved: {json_path}")
            except Exception:
                pass

        patcher_hits, n_pk = count_patcher_offsets_found(results or {})
        patcher_ok = (patcher_hits == n_pk) if results else False

        core_hits = sum(1 for n in ALL_OFFSET_NAMES if n in results) if results else 0
        arm64_core = sum(1 for n in ALL_OFFSET_NAMES if n in arm64_results) if arm64_results else -1

        if fmt == 'pe':
            if patcher_ok:
                print(f"\n  *** ALL {n_pk} WINDOWS PATCHER OFFSETS FOUND ***")
                exit_code = 0
            else:
                if patcher_hits > 0:
                    print(f"\n  *** PARTIAL: {patcher_hits}/{n_pk} Windows patcher offsets ***")
                    exit_code = 1
                else:
                    print(f"\n  *** INSUFFICIENT: Windows patcher needs all {n_pk} ***")
                    exit_code = 2
        else:
            n_required = len(ALL_OFFSET_NAMES)
            arm64_ok = (arm64_core < 0) or (arm64_core == n_required)
            if core_hits == n_required and arm64_ok:
                msg = f"*** ALL {n_required} CORE OFFSETS FOUND ***"
                if arm64_core >= 0:
                    msg += f"  |  arm64 core: {arm64_core}/{n_required}"
                print(f"\n  {msg}")
                exit_code = 0
            elif core_hits >= n_required - 2:
                print(f"\n  *** PARTIAL SUCCESS: {core_hits}/{n_required} core x86_64 offsets ***", end="")
                if arm64_core >= 0 and arm64_core < n_required:
                    print(f"  (arm64 core: {arm64_core}/{n_required})")
                else:
                    print()
                exit_code = 1
            else:
                print(f"\n  *** INSUFFICIENT RESULTS: {core_hits}/{n_required} core x86_64 offsets ***")
                exit_code = 2
    finally:
        if quiet:
            sys.stdout = _stdout_main
            if json_only and emitted_json_text is not None:
                print(emitted_json_text)
            elif fmt == 'pe' and results:
                patcher_count, n_q = count_patcher_offsets_found(results)
                xval = _cross_validate(results, adj, data, tiers_used=tiers_used)
                print("  {} / {}  (required for Discord_voice_node_patcher.ps1)".format(patcher_count, n_q))
                print("  x86_64 discovered: {} offsets".format(len(results)))
                if patcher_count == n_q:
                    print("  [OK] ALL {} WINDOWS PATCHER OFFSETS FOUND".format(n_q))
                else:
                    print("  *** PARTIAL: {}/{} ***".format(patcher_count, n_q))
                print("  Cross-validation: clean" if not xval else "  Cross-validation: {} issue(s)".format(len(xval)))
                win_block = format_windows_patcher_block(results, bin_info, file_path, file_size, discord_app_version=dapp_ver)
                if win_block:
                    print("")
                    print("--- BEGIN COPY (Windows) ---")
                    print(win_block, end="")
                    print("--- END COPY ---")
            elif fmt == 'elf' and results:
                linux_block = format_linux_patcher_block(results, bin_info, file_path, file_size)
                if linux_block:
                    print("")
                    print("--- BEGIN COPY (Linux) ---")
                    print(linux_block)
                    print("--- END COPY ---")
            elif fmt == 'macho' and results:
                macos_block = format_macos_patcher_block(
                    results, bin_info, file_path, file_size,
                    arm64_results=arm64_results if arm64_results else None,
                    arm64_info=arm64_info,
                    arm64_adj=arm64_adj if arm64_results else None)
                if macos_block:
                    print("")
                    print("--- BEGIN COPY (macOS) ---")
                    print(macos_block)
                    print("--- END COPY ---")
    return exit_code


if __name__ == '__main__':
    code = main()
    if sys.stdin.isatty() and sys.platform == 'win32':
        input("\n  Press Enter to close...")
    sys.exit(code)

# endregion Main
