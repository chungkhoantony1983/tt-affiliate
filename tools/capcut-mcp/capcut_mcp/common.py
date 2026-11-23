"""Shared helpers: config, paths, media download, spec normalisation."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import platform
import shutil
import urllib.request
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.environ.get("CAPCUT_MCP_HOME", Path.home() / ".capcut-mcp"))
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = CONFIG_DIR / "cache"
OUTPUT_DIR = Path(os.environ.get("CAPCUT_MCP_OUTPUT", Path.home() / "Movies" / "CapCut-MCP"))

ASPECTS = {
    "9:16": (1080, 1920),  # TikTok, Reels, Shorts
    "1:1": (1080, 1080),   # Facebook / Instagram feed
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),  # YouTube
}

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


# --------------------------------------------------------------------------- config

def load_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def candidate_draft_folders() -> list[Path]:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return [
            home / "Movies/CapCut/User Data/Projects/com.lveditor.draft",
            home / "Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft",
            home / "Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
        ]
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        return [
            local / "CapCut/User Data/Projects/com.lveditor.draft",
            local / "CapCut Drafts",
            local / "JianyingPro/User Data/Projects/com.lveditor.draft",
        ]
    return [home / "CapCut/drafts"]


def get_drafts_folder() -> Path | None:
    cfg = load_config()
    if cfg.get("drafts_folder") and Path(cfg["drafts_folder"]).is_dir():
        return Path(cfg["drafts_folder"])
    env = os.environ.get("CAPCUT_DRAFTS_FOLDER")
    if env and Path(env).is_dir():
        return Path(env)
    for p in candidate_draft_folders():
        if p.is_dir():
            return p
    return None


def _has_drawtext(exe: str) -> bool:
    import subprocess
    try:
        out = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    return " drawtext " in out


def find_ffmpeg() -> str | None:
    # Homebrew ffmpeg 8+ ships without libfreetype (no drawtext); prefer a build that has it.
    cands = [os.environ.get("CAPCUT_FFMPEG"), shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
    try:
        import imageio_ffmpeg  # type: ignore
        cands.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    cands = [c for c in dict.fromkeys(cands) if c and Path(c).exists()]
    for c in cands:
        if _has_drawtext(c):
            return c
    return cands[0] if cands else None


def find_font(bold: bool = True) -> str | None:
    """A TTF with Vietnamese glyphs, for the ffmpeg renderer."""
    cfg = load_config()
    if cfg.get("font_file") and Path(cfg["font_file"]).exists():
        return cfg["font_file"]
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


# --------------------------------------------------------------------------- media

def fetch_media(src: str) -> Path:
    """Return a local path for a file path or an http(s) URL (downloaded to cache)."""
    if src.startswith(("http://", "https://")):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha1(src.encode()).hexdigest()[:16]
        existing = list(CACHE_DIR.glob(key + ".*"))
        if existing:
            return existing[0]
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
        ext = Path(src.split("?")[0]).suffix.lower()
        if ext not in IMAGE_EXT | VIDEO_EXT | {".mp3", ".wav", ".m4a", ".aac"}:
            ext = mimetypes.guess_extension(ctype) or ".jpg"
            if ext == ".jpe":
                ext = ".jpg"
        out = CACHE_DIR / f"{key}{ext}"
        out.write_bytes(data)
        return _normalise_image(out)
    p = Path(os.path.expanduser(src)).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {src}")
    return _normalise_image(p)


def _normalise_image(p: Path) -> Path:
    """CapCut does not reliably accept webp/gif stills: convert them to PNG when Pillow exists."""
    if p.suffix.lower() not in {".webp"}:
        return p
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return p
    out = CACHE_DIR / (hashlib.sha1(str(p).encode()).hexdigest()[:16] + ".png")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        Image.open(p).convert("RGBA").save(out)
    return out


def is_video(p: Path) -> bool:
    return p.suffix.lower() in VIDEO_EXT


def hex_to_rgb01(color: str) -> tuple[float, float, float]:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def safe_name(name: str) -> str:
    bad = '<>:"/\\|?*'
    out = "".join("_" if ch in bad else ch for ch in name).strip()
    return out[:80] or "video"


# --------------------------------------------------------------------------- spec

POSITIONS = {"top": 0.62, "upper": 0.35, "center": 0.0, "lower": -0.4, "bottom": -0.68}


def normalise_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Fill defaults and validate a video spec. See README for the format."""
    if not spec.get("scenes"):
        raise ValueError("spec cần ít nhất 1 scene")
    s = dict(spec)
    s.setdefault("name", "video")
    s.setdefault("aspect", "9:16")
    if s["aspect"] not in ASPECTS:
        raise ValueError(f"aspect phải là một trong {list(ASPECTS)}")
    s.setdefault("fps", 30)
    theme = {"primary": "#FF2D55", "accent": "#FFD60A", "text": "#FFFFFF", "dark": "#111111"}
    theme.update(s.get("theme") or {})
    s["theme"] = theme
    scenes = []
    for i, sc in enumerate(s["scenes"]):
        sc = dict(sc)
        sc.setdefault("duration", 3.0)
        sc["duration"] = float(sc["duration"])
        if sc["duration"] <= 0.2:
            raise ValueError(f"scene {i}: duration quá ngắn")
        sc.setdefault("motion", "zoom_in")
        sc.setdefault("transition", None)
        sc.setdefault("background", theme["dark"])
        texts = []
        for t in sc.get("texts") or []:
            if isinstance(t, str):
                t = {"text": t}
            t = dict(t)
            t.setdefault("position", "bottom")
            t.setdefault("size", 9.0)
            t.setdefault("color", theme["text"])
            t.setdefault("bold", True)
            t.setdefault("start", 0.0)
            t.setdefault("end", sc["duration"])
            texts.append(t)
        sc["texts"] = texts
        scenes.append(sc)
    s["scenes"] = scenes
    return s


def solid_color_png(color: str, width: int, height: int) -> Path:
    """Write (or reuse) a plain-colour PNG, used for scenes without media."""
    import struct
    import zlib

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / f"solid_{color.lstrip('#')}_{width}x{height}.png"
    if out.exists():
        return out
    r, g, b = (int(v * 255) for v in hex_to_rgb01(color))
    row = b"\x00" + bytes([r, g, b]) * width
    raw = zlib.compress(row * height, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    out.write_bytes(png)
    return out
