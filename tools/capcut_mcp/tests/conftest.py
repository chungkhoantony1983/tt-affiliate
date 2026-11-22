import struct
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capcut_mcp.media import MediaInfo  # noqa: E402


def make_png(path: Path, w: int, h: int) -> Path:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.write_bytes(png)
    return path


@pytest.fixture
def assets(tmp_path):
    """Fake media files. Videos/audio are empty placeholders; tests pass MediaInfo explicitly
    so they don't need ffmpeg."""
    d = tmp_path / "assets"
    d.mkdir()
    img = make_png(d / "hoi_an.png", 64, 96)
    clip = d / "ha_giang.mp4"
    clip.write_bytes(b"\x00")
    voice = d / "voice.mp3"
    voice.write_bytes(b"\x00")
    music = d / "music.mp3"
    music.write_bytes(b"\x00")
    return {
        "img": str(img), "clip": str(clip), "voice": str(voice), "music": str(music),
        "clip_info": MediaInfo(kind="video", duration=12.0, width=1920, height=1080, has_audio=True),
        "voice_info": MediaInfo(kind="audio", duration=9.5),
        "music_info": MediaInfo(kind="audio", duration=120.0),
    }
