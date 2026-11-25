"""Free voiceover with edge-tts (DR-0013): one mp3 per scene narration line."""

from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from pathlib import Path

from .common import CACHE_DIR

VOICES = {"female": ("vi-VN-HoaiMyNeural", "+10%"), "male": ("vi-VN-NamMinhNeural", "+8%")}

# Same split as tt-affiliate choose_persona (DR-0013 Q-4): cooking, beauty, fashion -> female;
# tea, electronics, machines, cars, sport -> male; everything else -> female.
FEMALE = ["nau an", "do an", "an vat", "banh", "thuc pham", "bep", "lam dep", "my pham", "duong da",
          "trang diem", "thoi trang", "quan ao", "giay dep", "tui xach", "trang suc", "me va be", "suc khoe"]
MALE = ["tra", "am tra", "dien tu", "cong nghe", "dien thoai", "may tinh", "laptop", "tai nghe", "loa",
        "camera", "thiet bi", "o to", "xe may", "the thao", "gym", "dung cu"]


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def pick_voice(category: str = "", product_name: str = "") -> str:
    for field in (category, product_name):
        text = _plain(field)
        for gender, words in (("female", FEMALE), ("male", MALE)):
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words):
                return gender
    return "female"


def synthesize(text: str, gender: str = "female") -> Path:
    """Return a cached mp3 of `text`. Raises RuntimeError if edge-tts is missing or fails."""
    try:
        import edge_tts  # type: ignore
    except ImportError as e:
        raise RuntimeError("Chưa cài edge-tts: pip install edge-tts") from e
    voice, rate = VOICES.get(gender, VOICES["female"])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / ("tts_" + hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16] + ".mp3")
    if out.exists() and out.stat().st_size > 0:
        return out
    tmp = out.with_suffix(".part.mp3")

    async def run() -> None:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(tmp))

    try:
        asyncio.run(run())
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"edge-tts lỗi (cần mạng): {e}") from e
    tmp.replace(out)
    return out


def audio_seconds(path: Path) -> float:
    try:
        from mutagen.mp3 import MP3  # type: ignore
        return float(MP3(str(path)).info.length)
    except Exception:
        pass
    import subprocess
    from .common import find_ffmpeg
    ff = find_ffmpeg() or "ffmpeg"
    p = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    if not m:
        raise RuntimeError(f"Không đọc được thời lượng audio {path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)
