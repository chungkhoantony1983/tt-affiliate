"""Export a finished product-video folder to a CapCut draft project (DR-0013, capability capcut-edit).

Reads only files that already exist in the folder (script.json, product.json, audio_N.mp3, images):
no Groq, no Gemini, no new voice (C-0013-1). Writes nothing in the folder except capcut.json (C-0013-2).

The drafting itself lives in tools/capcut-mcp (package `capcut_mcp`), which is also the MCP server
Claude Desktop uses, so both paths share one implementation.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

# Keep in step with demo.py render_video so CapCut timing matches video.mp4.
GAP = 0.25
END_HOLD = 0.8
MAX_PRODUCT_IMAGES = 10  # same as demo.py
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

YELLOW = "#FFE14D"
RED = "#E11E3C"
CTA_YELLOW = "#FFC300"


class ExportError(Exception):
    """exit_code 4 = folder not ready (missing file), 9 = CapCut / capcut-mcp problem."""

    def __init__(self, message: str, exit_code: int = 4):
        super().__init__(message)
        self.exit_code = exit_code


def _price_text(price) -> str | None:
    try:
        p = int(price or 0)
    except (TypeError, ValueError):
        return None
    return f"{p:,}đ".replace(",", ".") if p else None


def _image_for(src: str, out_dir: Path, idx: int) -> str | None:
    """Resolve a product.json image entry to something capcut_mcp can load (local path or URL)."""
    src = (src or "").strip()
    if not src:
        return None
    if src.startswith(("http://", "https://")):
        cached = out_dir / f"img_{idx}.jpg"  # downloaded by render_video
        return str(cached) if cached.is_file() else src
    p = Path(src)
    if not p.is_absolute():
        p = out_dir / src
    return str(p) if p.is_file() else None


def _story_image(out_dir: Path, i: int) -> str | None:
    for ext in IMAGE_EXTS:
        p = out_dir / f"canh_{i + 1}{ext}"
        if p.is_file():
            return str(p)
    return None


def build_spec(out_dir: Path) -> dict:
    """Turn a video folder into a capcut_mcp spec. Raises ExportError when the folder is not ready."""
    out_dir = Path(out_dir)
    if not (out_dir / "product.json").is_file():
        raise ExportError("Chỉ hỗ trợ video sản phẩm (thư mục không có product.json)")
    if not (out_dir / "script.json").is_file():
        raise ExportError("Thư mục chưa có script.json")
    product = json.loads((out_dir / "product.json").read_text(encoding="utf-8"))
    script = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    segments = script.get("segments") or []
    if not segments:
        raise ExportError("script.json không có cảnh nào")

    missing = [i + 1 for i in range(len(segments)) if not (out_dir / f"audio_{i}.mp3").is_file()]
    if missing:
        raise ExportError(f"Thiếu giọng đọc ở cảnh {missing}. Dựng lại video trên Studio trước khi xuất.")
    no_duration = [i + 1 for i, s in enumerate(segments) if not s.get("duration")]
    if no_duration:
        raise ExportError(f"Cảnh {no_duration} chưa có thời lượng giọng đọc (script.json).")

    images = [im for im in (_image_for(s, out_dir, i) for i, s in enumerate((product.get("images") or [])[:MAX_PRODUCT_IMAGES])) if im]
    first = images[0] if images else None
    price = _price_text(product.get("price"))
    hook = script.get("hook")

    scenes, product_idx = [], 0
    for i, seg in enumerate(segments):
        kind = seg.get("kind", "product")
        dur = float(seg["duration"]) + GAP + (END_HOLD if i == len(segments) - 1 else 0)
        texts: list[dict] = []
        if kind == "cta":
            role, media = "cta", first
            texts.append({"text": "Video có gắn link tiếp thị liên kết", "position": "top", "size": 5,
                          "bold": False, "color": "#FFFFFF"})
            if price:
                texts.append({"text": price, "position": "center", "size": 11, "color": "#FFFFFF", "bg": RED})
            texts.append({"text": "BẤM GIỎ HÀNG VÀNG BÊN DƯỚI", "position": "lower", "size": 9,
                          "color": "#000000", "bg": CTA_YELLOW, "start": 0.3})
        elif kind == "story":
            role = "hook" if i == 0 else "story"
            media = _story_image(out_dir, i) or first
            if i == 0 and hook:
                texts.append({"text": hook, "position": "top", "size": 11, "color": YELLOW, "border": "#000000"})
            texts.append({"text": seg.get("line", ""), "position": "bottom", "size": 7, "color": "#FFFFFF",
                          "border": "#000000"})
        else:
            media = images[product_idx % len(images)] if images else None
            if i == 0 and hook:
                role = "hook"
                texts.append({"text": hook, "position": "top", "size": 11, "color": YELLOW, "border": "#000000"})
            else:
                role = "point"
                if seg.get("text"):
                    texts.append({"text": seg["text"], "position": "top", "size": 9, "color": "#000000",
                                  "bg": YELLOW})
                if price and product_idx == 0:
                    role = "price"
                    texts.append({"text": price, "position": "bottom", "size": 10, "color": "#FFFFFF",
                                  "bg": RED, "start": 0.2})
            product_idx += 1
        scenes.append({"media": media, "duration": round(dur, 3), "role": role, "texts": texts,
                       "audio": str(out_dir / f"audio_{i}.mp3"), "background": "#111111"})

    if not any(sc["media"] for sc in scenes):
        raise ExportError("Video này chưa có ảnh nào (không có ảnh sản phẩm, cũng không có ảnh nhân vật canh_N). "
                          "Thêm ảnh sản phẩm trên Studio rồi Dựng lại, sau đó xuất CapCut. "
                          "Nếu xuất bây giờ, CapCut chỉ có nền đen.")

    stamp = out_dir.name[:13]  # YYYYmmdd_HHMM… keeps re-exports of one folder on one draft
    return {
        "name": f"TT - {product.get('name', 'video')} {stamp}".strip(),
        "aspect": "9:16",
        "fps": 25,
        "category": product.get("category", ""),
        "product_name": product.get("name", ""),
        "look": os.environ.get("CAPCUT_LOOK", "auto"),
        "scenes": scenes,
    }


def export_folder(out_dir: Path, drafts_folder: str | None = None) -> dict:
    """Build the CapCut draft for one video folder and record it in capcut.json."""
    out_dir = Path(out_dir)
    spec = build_spec(out_dir)
    try:
        from capcut_mcp.capcut_builder import build_capcut_draft
    except ImportError as e:
        raise ExportError("Chưa cài capcut-mcp: .venv/bin/pip install -e tools/capcut-mcp", 9) from e
    try:
        result = build_capcut_draft(spec, drafts_folder=drafts_folder or os.environ.get("CAPCUT_DRAFTS_FOLDER") or None)
    except FileNotFoundError as e:
        raise ExportError(str(e), 9) from e
    except Exception as e:  # pycapcut / CapCut format problems must not break the video folder
        raise ExportError(f"Tạo dự án CapCut lỗi: {type(e).__name__}: {e}", 9) from e
    record = {"draft_name": result.get("draft_name"), "draft_path": result.get("draft_path"),
              "duration_s": result.get("duration_s"), "exported_at": datetime.now().isoformat(timespec="seconds")}
    (out_dir / "capcut.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def auto_export_enabled() -> bool:
    return os.environ.get("CAPCUT_AUTO_EXPORT", "1").strip().lower() not in ("0", "false", "no", "")
