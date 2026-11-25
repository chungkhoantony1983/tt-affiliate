"""Probe local media files: kind (video/photo/audio), duration, width/height.

Order of strategies:
1. ffprobe on PATH (most accurate).
2. ffmpeg from imageio-ffmpeg (already in requirements-demo.txt) or PATH,
   parsing the `ffmpeg -i` banner.
3. Pure-Python header parsing for PNG / JPEG / GIF / WEBP images.

If nothing works, callers must pass duration/width/height explicitly.
"""

from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".heic"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


@dataclass
class MediaInfo:
    kind: str  # "video" | "photo" | "audio"
    duration: float | None = None  # seconds; None for photos
    width: int | None = None
    height: int | None = None
    has_audio: bool | None = None


def kind_from_ext(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXT:
        return "photo"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in VIDEO_EXT:
        return "video"
    raise ValueError(f"Unsupported media extension: {ext or '(none)'} ({path})")


def _image_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as f:
        head = f.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        if head[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", head[6:10])
            return w, h
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            chunk = head[12:16]
            f.seek(0)
            data = f.read(64)
            if chunk == b"VP8X":
                w = int.from_bytes(data[24:27], "little") + 1
                h = int.from_bytes(data[27:30], "little") + 1
                return w, h
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                b = data[21:25]
                w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                return w, h
            return None
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return None
                code = marker[1]
                if code in (0xD8, 0x01) or 0xD0 <= code <= 0xD7:
                    continue
                seg_len_raw = f.read(2)
                if len(seg_len_raw) < 2:
                    return None
                seg_len = struct.unpack(">H", seg_len_raw)[0]
                if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    data = f.read(5)
                    h, w = struct.unpack(">HH", data[1:5])
                    return w, h
                f.seek(seg_len - 2, 1)
    return None


def _ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _probe_ffprobe(path: Path) -> MediaInfo | None:
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
        data = json.loads(out)
    except Exception:
        return None
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = data.get("format", {}).get("duration")
    info = MediaInfo(kind=kind_from_ext(path))
    info.duration = float(dur) if dur not in (None, "N/A") else None
    if v:
        info.width, info.height = int(v.get("width", 0)) or None, int(v.get("height", 0)) or None
    info.has_audio = a is not None
    return info


_DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VID_RE = re.compile(r"Stream #.*Video:.*?(\d{2,5})x(\d{2,5})")


def _probe_ffmpeg_banner(path: Path) -> MediaInfo | None:
    exe = _ffmpeg_exe()
    if not exe:
        return None
    try:
        err = subprocess.run([exe, "-hide_banner", "-i", str(path)],
                             capture_output=True, text=True, timeout=30).stderr
    except Exception:
        return None
    info = MediaInfo(kind=kind_from_ext(path))
    m = _DUR_RE.search(err)
    if m:
        h, mi, s = m.groups()
        info.duration = int(h) * 3600 + int(mi) * 60 + float(s)
    m = _VID_RE.search(err)
    if m:
        info.width, info.height = int(m.group(1)), int(m.group(2))
    info.has_audio = "Audio:" in err
    if info.duration is None and info.width is None:
        return None
    return info


def probe(path: str | Path) -> MediaInfo:
    """Return what we can learn about a media file. Raises FileNotFoundError."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Media file not found: {p}")
    kind = kind_from_ext(p)
    if kind == "photo":
        size = _image_size(p)
        if size:
            return MediaInfo(kind="photo", width=size[0], height=size[1])
    info = _probe_ffprobe(p) or _probe_ffmpeg_banner(p)
    if info:
        if kind == "photo":
            info.duration = None
        return info
    return MediaInfo(kind=kind)
