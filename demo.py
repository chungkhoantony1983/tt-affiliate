"""
TT Content Publisher — CLI Demo
Pipeline: Product (CLI / CSV) → Script segments (Groq) → Multi-voice TTS (edge-tts)
          → AI story images (optional) → Video (FFmpeg) → Manual upload kit

Styles:
  story  — short skit with Vietnamese characters (AI images + character voices) → product → CTA
  simple — product images only, narrator voice

Usage:
  python demo.py --csv products.csv
  python demo.py --product "Máy hút bụi mini" --price 189000 --images a.jpg,b.jpg \
                 --points "Hút mạnh|Sạc USB|Nhỏ gọn" --style simple
"""

import argparse
import asyncio
import base64
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path

W, H = 1080, 1920
FPS = 25
GAP = 0.25          # silence between spoken segments (s)
END_HOLD = 0.8      # extra hold on the last scene (s)

# speaker → (edge-tts voice, rate, pitch). edge-tts has only 2 Vietnamese voices,
# so older characters are made by lowering pitch + slowing down.
VOICES = {
    "narrator": ("vi-VN-HoaiMyNeural", "+10%", "+0Hz"),
    "con_gai":  ("vi-VN-HoaiMyNeural", "+8%",  "+12Hz"),
    "con_trai": ("vi-VN-NamMinhNeural", "+8%", "+0Hz"),
    "me":       ("vi-VN-HoaiMyNeural", "-8%",  "-25Hz"),
    "ba":       ("vi-VN-HoaiMyNeural", "-12%", "-35Hz"),
    "bo":       ("vi-VN-NamMinhNeural", "-8%", "-15Hz"),
    "ong":      ("vi-VN-NamMinhNeural", "-12%", "-25Hz"),
}

# ---------------------------------------------------------------------------
# 0. Config
# ---------------------------------------------------------------------------

def load_env(path: str = ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines); existing env vars win."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _slug(text: str, max_len: int = 40) -> str:
    text = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    text = text.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:max_len] or "product"


# ---------------------------------------------------------------------------
# 1. Script Generation (Groq API)
# ---------------------------------------------------------------------------

def _extract_json(content: str) -> dict:
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1:
        content = content[start:end + 1]
    return json.loads(content)


STORY_STRUCTURE = """Cấu trúc "segments" (tổng 20-30 giây):
1. 2-3 segment kind="story": tiểu phẩm đời thường giữa các nhân vật người Việt.
   speaker PHẢI khớp vai người đang nói: con_gai, con_trai, me (mẹ), bo (bố), ba (bà), ong (ông).
   - Segment đầu tiên là HOOK: tình huống/nỗi đau cụ thể, gây tò mò trong 2 giây đầu.
   - Mỗi segment story có "image_prompt" bằng TIẾNG ANH: ảnh chân thực, người Việt Nam, nhà Việt, hành động + cảm xúc rõ.
     Mô tả ngoại hình mỗi nhân vật GIỐNG HỆT nhau ở mọi cảnh (tuổi, tóc, quần áo). Không có chữ trong ảnh. KHÔNG vẽ sản phẩm.
2. 2 segment kind="product", speaker="narrator": lợi ích sản phẩm (lấy từ Điểm nổi bật). "text" ≤ 4 từ.
3. (Tuỳ chọn) 1 segment kind="story" cảnh kết: nhân vật vui vẻ sau khi có sản phẩm (có image_prompt, không vẽ sản phẩm).
4. 1 segment kind="cta", speaker="narrator": kêu gọi bấm GIỎ HÀNG VÀNG ở góc dưới video. Không nhắc "link bio"."""

SIMPLE_STRUCTURE = """Cấu trúc "segments" (tổng 20-30 giây), tất cả speaker="narrator":
1. 1 segment kind="product" là HOOK: tình huống/nỗi đau cụ thể, gây tò mò trong 2 giây đầu.
2. 2-3 segment kind="product": lợi ích sản phẩm (lấy từ Điểm nổi bật). "text" ≤ 4 từ.
3. 1 segment kind="cta": kêu gọi bấm GIỎ HÀNG VÀNG ở góc dưới video. Không nhắc "link bio"."""


def generate_script(product: dict, style: str) -> dict:
    """Generate a segmented TikTok Shop affiliate script using Groq API."""
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    points = "; ".join(product["selling_points"]) or "(không có — tự suy luận hợp lý, KHÔNG bịa số liệu)"
    price = f"{product['price']:,}đ" if product["price"] else "(chưa có — KHÔNG nhắc đến giá)"
    structure = STORY_STRUCTURE if style == "story" else SIMPLE_STRUCTURE

    prompt = f"""Bạn là creator TikTok Việt Nam chuyên làm video tiếp thị liên kết TikTok Shop.
Viết kịch bản video ngắn cho sản phẩm:

Sản phẩm: {product['name']}
Giá: {price}
Danh mục: {product['category']}
Điểm nổi bật: {points}
Ghi chú: {product.get('notes') or '-'}

{structure}

Quy tắc:
- "line" là lời thoại được đọc thành giọng nói: ≤ 15 từ, tiếng Việt đời thường, tự nhiên, KHÔNG emoji, không ký hiệu.
- "text" là chữ hiện trên màn hình: rất ngắn hoặc để "" (đã có giọng đọc, không lặp lại lời thoại).
- "hook": chữ lớn hiện ở cảnh đầu, ≤ 8 từ.
- CHỈ dùng thông số/con số có trong "Điểm nổi bật" và "Ghi chú". Không tự thêm thông số.
- Không cam kết sai sự thật, không dùng "rẻ nhất", "tốt nhất thế giới", không bịa số liệu/đánh giá.
- Ghi chú có ràng buộc (vd: không phải thiết bị y tế) thì PHẢI tuân thủ tuyệt đối.
- Ghi chú nêu khách hàng mục tiêu thì hook nói trực tiếp với người đó, bằng tình huống cụ thể họ gặp hằng ngày.
- Viết đúng chính tả tiếng Việt có dấu.
- Không nói "mình đã dùng/đã thử" trừ khi Ghi chú nói rõ người đăng đã dùng.
- hashtags viết KHÔNG dấu, viết liền, chữ thường, liên quan trực tiếp đến sản phẩm/nhu cầu người mua.

Chỉ trả về JSON:
{{
  "hook_style": "question | shock | relatable | bold_claim | story",
  "hook": "...",
  "segments": [
    {{"kind": "story | product | cta", "speaker": "...", "line": "...", "text": "...", "image_prompt": "... (chỉ cho story)"}}
  ],
  "caption": "caption đăng TikTok, 1-2 câu, có thể có emoji",
  "hashtags": ["#...", "#...", "#...", "#..."]
}}"""

    # qwen3.8-27b writes more natural Vietnamese than gpt-oss-120b (which misspells, e.g. "khuế đại")
    model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
    print(f"📝 Generating {style} script with Groq ({model})...")
    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=4000,
            )
            script = _extract_json(response.choices[0].message.content or "")
            segments = [s for s in script.get("segments", []) if (s.get("line") or "").strip()]
            if len(segments) < 3:
                raise ValueError(f"too few segments ({len(segments)})")
            break
        except Exception as e:
            last_error = e
            print(f"   Retry {attempt + 1}/2 after error: {e}")
    else:
        raise RuntimeError(f"Script generation failed: {last_error}")

    for seg in segments:
        if seg.get("speaker") not in VOICES:
            seg["speaker"] = "narrator"
        if seg.get("kind") not in ("story", "product", "cta"):
            seg["kind"] = "product"
        if seg["kind"] == "story" and (style != "story" or not seg.get("image_prompt")):
            seg["kind"] = "product"
    script["segments"] = segments
    script["style"] = style

    # TikTok VN hashtags: no diacritics, no spaces, lowercase, unique
    tags = ["#" + _slug(t, 30).replace("-", "") for t in script.get("hashtags", [])] + ["#tiktokshop"]
    script["hashtags"] = list(dict.fromkeys(t for t in tags if len(t) > 1))[:6]

    print(f"✅ Script: {len(segments)} segments — hook: {script.get('hook')}")
    return script


# ---------------------------------------------------------------------------
# 2. TTS — one audio file per segment, voice by speaker (edge-tts)
# ---------------------------------------------------------------------------

def _clean_tts_text(text: str) -> str:
    """Remove stage-direction labels like [Hook 0-3s] that break edge-tts."""
    text = re.sub(r"\[[^\]]*\]", "", text)   # strip [...]
    text = re.sub(r"\s{2,}", " ", text)        # collapse whitespace
    return text.strip()


async def _tts(text: str, speaker: str, output_path: str) -> None:
    import edge_tts

    voice, rate, pitch = VOICES.get(speaker, VOICES["narrator"])
    if speaker == "narrator":
        voice = os.environ.get("TTS_VOICE", voice)
    for attempt in range(3):
        try:
            await edge_tts.Communicate(_clean_tts_text(text), voice, rate=rate, pitch=pitch).save(output_path)
            return
        except Exception as e:
            if attempt == 2:
                raise
            print(f"   Retry {attempt + 1}/2 after error: {e}")
            await asyncio.sleep(2)


def generate_voiceovers(segments: list, out_dir: Path) -> None:
    """Write audio_{i}.mp3 per segment; stores path + duration on each segment."""
    from mutagen.mp3 import MP3

    print(f"🎙️  Generating voiceover ({len(segments)} segments)...")
    for i, seg in enumerate(segments):
        path = out_dir / f"audio_{i}.mp3"
        asyncio.run(_tts(seg["line"], seg["speaker"], str(path)))
        seg["audio_path"] = str(path)
        seg["duration"] = float(MP3(str(path)).info.length)
    total = sum(s["duration"] for s in segments) + GAP * len(segments)
    print(f"✅ Voiceover: {total:.1f}s")


# ---------------------------------------------------------------------------
# 3. AI story images (provider: gemini | pollinations | none)
# ---------------------------------------------------------------------------

IMAGE_STYLE = ("Photorealistic vertical 9:16 photo, cinematic soft natural light, authentic Vietnamese home, "
               "real people, candid moment, shallow depth of field. No text, no captions, no watermark.")


def _http_bytes(req: urllib.request.Request, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _image_pollinations(prompt: str, seed: int) -> bytes:
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
           + f"?width={W}&height={H}&nologo=true&seed={seed}&model=flux")
    headers = {"User-Agent": "Mozilla/5.0"}
    if os.environ.get("POLLINATIONS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['POLLINATIONS_TOKEN']}"
    return _http_bytes(urllib.request.Request(url, headers=headers))


def _image_gemini(prompt: str, seed: int) -> bytes:
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
    )
    data = json.loads(_http_bytes(req))
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("Gemini returned no image")


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _scene_image_file(out_dir: Path, i: int):
    """Manually supplied image for segment i: canh_{i+1}.(png|jpg|jpeg|webp)."""
    for ext in IMAGE_EXTS:
        p = out_dir / f"canh_{i + 1}{ext}"
        if p.exists():
            return p
    return None


def write_image_prompts(segments: list, out_dir: Path) -> list:
    """Write prompts.txt for story scenes still missing an image; return missing scene numbers."""
    missing = [(i, s) for i, s in enumerate(segments)
               if s["kind"] == "story" and not s.get("image_path") and not _scene_image_file(out_dir, i)]
    path = out_dir / "prompts.txt"
    if not missing:
        path.unlink(missing_ok=True)
        return []
    lines = [
        "TẠO ẢNH NHÂN VẬT BẰNG GEMINI APP (gemini.google.com — gói AI Plus)",
        "",
        "1. Mở 1 cuộc trò chuyện MỚI, dán lần lượt từng prompt bên dưới (cùng 1 chat để nhân vật giống nhau).",
        "   Từ prompt thứ 2 trở đi, thêm câu: \"Giữ nguyên các nhân vật giống hệt ảnh trước.\"",
        "2. Tải ảnh về, đổi tên đúng như dòng 'Lưu thành', bỏ vào thư mục:",
        f"   {out_dir.resolve()}",
        "3. Chạy: .venv/bin/python demo.py --rerender " + str(out_dir),
        "",
    ]
    for i, seg in missing:
        lines += [
            "=" * 70,
            f"CẢNH {i + 1} — Lưu thành: canh_{i + 1}.png   (lời thoại: \"{seg['line']}\")",
            "-" * 70,
            f"Create a vertical 9:16 image. {seg['image_prompt']} {IMAGE_STYLE}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return [i + 1 for i, _ in missing]


def generate_story_images(segments: list, out_dir: Path, seed: int) -> None:
    """API image generation (IMAGE_PROVIDER=gemini|pollinations). Default 'manual':
    images are made by hand in the Gemini app (see write_image_prompts)."""
    provider = os.environ.get("IMAGE_PROVIDER", "manual").lower()
    story = [(i, s) for i, s in enumerate(segments) if s["kind"] == "story"]
    if not story or provider in ("manual", "none"):
        return
    print(f"🖼️  Generating {len(story)} story image(s) ({provider})...")
    fn = _image_gemini if provider == "gemini" else _image_pollinations
    for i, seg in story:
        try:
            data = fn(f"{seg['image_prompt']} {IMAGE_STYLE}", seed)
            path = out_dir / f"ai_{i}.jpg"
            path.write_bytes(data)
            seg["image_path"] = str(path)
        except Exception as e:
            print(f"   ⚠️  Image for segment {i + 1} failed ({e}) — using product image")


# ---------------------------------------------------------------------------
# 4. Video Render — one scene per segment, timed to its audio (Pillow + FFmpeg)
# ---------------------------------------------------------------------------

FONT_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Unicode.ttf"]
FONT_REGULAR = ["/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _font(size: int, bold: bool = True):
    from PIL import ImageFont
    for path in (FONT_BOLD if bold else FONT_REGULAR):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_px(draw, text: str, font, max_w: int) -> list:
    """Wrap text by pixel width (keeps Vietnamese words intact)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _text_block(draw, text: str, y: int, font, color="white", max_w: int = W - 140,
                stroke: int = 6, gap: int = 14) -> int:
    """Draw centered, outlined, wrapped text; return next y."""
    for line in _wrap_px(draw, text, font, max_w):
        bb = draw.textbbox((0, 0), line, font=font, stroke_width=stroke)
        draw.text(((W - (bb[2] - bb[0])) / 2, y), line, font=font, fill=color,
                  stroke_width=stroke, stroke_fill="black")
        y += (bb[3] - bb[1]) + gap
    return y


def _pill(draw, text: str, y: int, font, fill, color="white", pad=(50, 22)) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + pad[0] * 2, th + pad[1] * 2
    x = (W - pw) // 2
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=ph // 2, fill=fill)
    draw.text((x + pad[0] - bb[0], y + pad[1] - bb[1]), text, font=font, fill=color)
    return y + ph


def _cover(img):
    """Scale + center-crop image to fill the 9:16 frame."""
    scale = max(W / img.width, H / img.height)
    im = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, top = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((left, top, left + W, top + H))


def _background(img_src):
    """Blurred, darkened cover of the product image; gradient if no image."""
    from PIL import Image, ImageFilter, ImageEnhance
    if img_src is None:
        bg = Image.new("RGB", (W, H))
        for y in range(H):
            t = y / (H - 1)
            bg.paste((int(20 + 40 * t), int(10 + 10 * t), int(50 + 60 * t)), (0, y, W, y + 1))
        return bg
    bg = _cover(img_src).filter(ImageFilter.GaussianBlur(40))
    return ImageEnhance.Brightness(bg).enhance(0.45)


def _paste_fit(canvas, img, box, radius: int = 28):
    """Paste image scaled to fit inside box (x0, y0, x1, y1), centered, rounded."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    scale = min(bw / img.width, bh / img.height)
    im = img.resize((int(img.width * scale), int(img.height * scale)))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width, im.height], radius=radius, fill=255)
    canvas.paste(im, (x0 + (bw - im.width) // 2, y0 + (bh - im.height) // 2), mask)


def _scene_story(ai_img, product_img, line: str, hook: str = None):
    """Full-bleed AI story image + small dialogue subtitle (hook text on first scene)."""
    from PIL import ImageDraw
    if ai_img is not None:
        canvas = _cover(ai_img)
    else:
        # No AI image → product hero instead of an empty blurred frame
        canvas = _background(product_img)
        if product_img is not None:
            _paste_fit(canvas, product_img, (0, 380, W, 1300), radius=0)
    draw = ImageDraw.Draw(canvas)
    if hook:
        _text_block(draw, hook, 230, _font(84), color="#FFE14D", stroke=7)
    # Subtitle sits above TikTok's bottom UI (caption + product anchor cover ~350px)
    _text_block(draw, line, 1330, _font(50), stroke=5, gap=10)
    return canvas


def _scene_product(img, text: str, hook: str = None, price_text: str = None):
    """Product image full-width as the hero; one short label on top."""
    from PIL import ImageDraw
    canvas = _background(img)
    if img is not None:
        _paste_fit(canvas, img, (0, 330, W, 1430), radius=0)
    draw = ImageDraw.Draw(canvas)
    if hook:
        _text_block(draw, hook, 120, _font(78), color="#FFE14D", stroke=7)
    elif text:
        _pill(draw, text, 170, _font(62), fill="#FFE14D", color="black")
    if price_text:
        _pill(draw, price_text, 1460, _font(70), fill=(225, 30, 60))
    return canvas


def _scene_cta(img, price_text: str):
    from PIL import ImageDraw
    canvas = _background(img)
    if img is not None:
        _paste_fit(canvas, img, (60, 190, W - 60, 1130))
    draw = ImageDraw.Draw(canvas)
    _text_block(draw, "Video có gắn link tiếp thị liên kết", 110, _font(30, bold=False), stroke=3)
    y = 1170
    if price_text:
        y = _pill(draw, price_text, y, _font(72), fill=(225, 30, 60)) + 30
    y = _pill(draw, "BẤM GIỎ HÀNG VÀNG BÊN DƯỚI", y, _font(56), fill="#FFC300", color="black")
    # Arrow pointing down to TikTok's product anchor area
    cx, ay = W // 2, y + 30
    draw.polygon([(cx - 60, ay), (cx + 60, ay), (cx, ay + 80)], fill="#FFC300")
    return canvas


def _load_image(src: str, out_dir: Path, idx: int):
    """Load local path or URL into a PIL image (RGB). Returns None on failure."""
    from PIL import Image
    try:
        if src.startswith("http://") or src.startswith("https://"):
            dest = out_dir / f"img_{idx}.jpg"
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            dest.write_bytes(_http_bytes(req, timeout=30))
            src = str(dest)
        return Image.open(src).convert("RGB")
    except Exception as e:
        print(f"   ⚠️  Cannot load image {src}: {e}")
        return None


def render_video(script: dict, product: dict, output_path: str) -> str:
    """One scene per segment; each scene lasts exactly as long as its spoken line."""
    out_dir = Path(output_path).parent
    images = [im for im in (_load_image(s, out_dir, i) for i, s in enumerate(product["images"][:3])) if im]
    segments = script["segments"]
    print(f"🎬 Rendering video (1080x1920, {len(segments)} scenes, {len(images)} product image(s))...")

    price_text = f"{product['price']:,}đ".replace(",", ".") if product["price"] else None
    first_img = images[0] if images else None
    hook = script.get("hook")
    scenes, product_idx = [], 0
    for i, seg in enumerate(segments):
        seg_hook = hook if i == 0 else None
        if seg["kind"] == "story":
            src = _scene_image_file(out_dir, i) or seg.get("image_path")
            ai = _load_image(str(src), out_dir, 100 + i) if src else None
            img = _scene_story(ai, first_img, seg["line"], hook=seg_hook)
        elif seg["kind"] == "cta":
            img = _scene_cta(first_img, price_text)
        else:
            pimg = images[product_idx % len(images)] if images else None
            img = _scene_product(pimg, seg.get("text", ""), hook=seg_hook,
                                 price_text=price_text if product_idx == 0 and not seg_hook else None)
            product_idx += 1
        dur = seg["duration"] + GAP + (END_HOLD if i == len(segments) - 1 else 0)
        scenes.append((img, dur))

    inputs, filters, frame_files = [], [], []
    for i, (img, dur) in enumerate(scenes):
        fp = out_dir / f"_scene_{i}.png"
        img.save(fp)
        frame_files.append(fp)
        frames = int(dur * FPS)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(fp)]
        # Slow push-in / pull-out alternating, keeps the frame alive
        zoom = f"1+0.06*on/{frames}" if i % 2 == 0 else f"1.06-0.06*on/{frames}"
        filters.append(
            f"[{i}:v]scale={W * 2}:{H * 2},zoompan=z='{zoom}':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1[v{i}]"
        )
        print(f"   Scene {i + 1} [{segments[i]['kind']}/{segments[i]['speaker']}]: {dur:.1f}s")
    n = len(scenes)
    for i, seg in enumerate(segments):
        inputs += ["-i", str(out_dir / Path(seg["audio_path"]).name)]
        pad = GAP + (END_HOLD if i == n - 1 else 0)
        filters.append(f"[{n + i}:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur={pad}[a{i}]")
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
    filters.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")

    cmd = [
        _ffmpeg_bin(), "-y", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for fp in frame_files:
        fp.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"❌ FFmpeg stderr:\n{result.stderr[-3000:]}")
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")

    total = sum(d for _, d in scenes)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"✅ Video: {output_path}  ({size_mb:.1f} MB, {total:.1f}s, {n} scenes)")
    return output_path


# ---------------------------------------------------------------------------
# 5. Approval Step
# ---------------------------------------------------------------------------

def approval_step(script: dict, video_path: str) -> bool:
    """Manual approval before publishing."""
    print("\n" + "=" * 60)
    print("📋 REVIEW BEFORE PUBLISHING")
    print("=" * 60)
    print(f"\n🎯 Hook: {script.get('hook', 'N/A')}\n")
    for seg in script["segments"]:
        print(f"   [{seg['kind']:<7} {seg['speaker']:<8}] {seg['line']}")
    print(f"\n📝 Caption: {script.get('caption', '')} {' '.join(script.get('hashtags', []))}")
    print(f"\n🎬 Video: {video_path}")
    print("=" * 60)
    if sys.platform == "darwin":
        subprocess.run(["open", video_path])
    response = input("\n✅ Approve? (y/n): ").strip().lower()
    return response == "y"


# ---------------------------------------------------------------------------
# 6. Publish — manual upload kit (TikTok API pending; product anchor is app-only)
# ---------------------------------------------------------------------------

def publish_to_tiktok(video_path: str, script: dict, product: dict) -> dict:
    """Write post.txt (caption + checklist) next to the video for manual upload."""
    caption = f"{script.get('caption', '').strip()} {' '.join(script.get('hashtags', []))}".strip()
    product_line = product["name"] + (f" — {product['price']:,}đ" if product["price"] else "")
    post_path = Path(video_path).parent / "post.txt"
    post_path.write_text(
        "=== CAPTION (copy) ===\n"
        f"{caption}\n\n"
        "=== SẢN PHẨM ===\n"
        f"{product_line}\n"
        f"{product.get('product_url') or '(chưa có link sản phẩm)'}\n\n"
        "=== CHECKLIST ĐĂNG ===\n"
        "[ ] Chuyển video.mp4 sang điện thoại (AirDrop)\n"
        "[ ] TikTok → + → Tải lên → chọn video\n"
        "[ ] Dán caption ở trên\n"
        "[ ] Thêm liên kết → Sản phẩm → chọn đúng sản phẩm trong showcase\n"
        "[ ] Cài đặt khác → BẬT nhãn 'Nội dung do AI tạo' (giọng đọc + hình người do AI tạo)\n"
        "[ ] Đăng → ghi lại vào bảng §4 trong TODO.md\n",
        encoding="utf-8",
    )
    print(f"\n📦 Upload kit ready: {post_path}")
    return {"status": "ready_for_manual_upload", "post_path": str(post_path),
            "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _split(value: str, sep: str) -> list:
    return [v.strip() for v in (value or "").split(sep) if v.strip()]


def load_products_csv(path: str) -> list:
    """CSV columns: name, price, category, images (|-separated), selling_points (|-separated),
    product_url, commission_pct, sold_count, notes, style, status.
    Rows with status 'done' or 'skip' are ignored."""
    products = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not (row.get("name") or "").strip():
                continue
            if (row.get("status") or "").strip().lower() in ("done", "skip"):
                continue
            products.append({
                "name": row["name"].strip(),
                "price": int(re.sub(r"[^\d]", "", row.get("price") or "0") or 0),
                "category": (row.get("category") or "").strip() or "Khác",
                "images": _split(row.get("images"), "|"),
                "selling_points": _split(row.get("selling_points"), "|"),
                "product_url": (row.get("product_url") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
                "style": (row.get("style") or "").strip().lower() or None,
            })
    return products


def run_one(product: dict, base_dir: Path, style: str, skip_approval: bool) -> dict:
    style = product.get("style") or style
    out_dir = base_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{_slug(product['name'])}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"🎯 {product['name']} — {product['price'] or '?'}đ ({product['category']}, style={style})")
    print("=" * 60)

    script = generate_script(product, style)
    generate_voiceovers(script["segments"], out_dir)
    generate_story_images(script["segments"], out_dir, seed=zlib.crc32(product["name"].encode()) % 100000)
    (out_dir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "product.json").write_text(json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8")
    return finish(out_dir, script, product, skip_approval)


def finish(out_dir: Path, script: dict, product: dict, skip_approval: bool) -> dict:
    """Render → (draft if story images missing) → approval → upload kit."""
    video_path = str(out_dir / "video.mp4")
    render_video(script, product, video_path)

    missing = write_image_prompts(script["segments"], out_dir)
    if missing:
        print(f"\n🖼️  Cần ảnh nhân vật cho cảnh {missing} → làm theo {out_dir / 'prompts.txt'}")
        print("   (video.mp4 hiện là bản nháp, dùng ảnh sản phẩm thay cho cảnh nhân vật)")
        return {"status": "needs_images", "dir": str(out_dir)}

    if not skip_approval and not approval_step(script, video_path):
        print("❌ Rejected — kept files for reference.")
        return {"status": "rejected", "dir": str(out_dir)}

    result = publish_to_tiktok(video_path, script, product)
    result["dir"] = str(out_dir)
    return result


def rerender(out_dir: Path, skip_approval: bool) -> dict:
    """Re-render an existing output folder (reuses script + audio, picks up canh_N images)."""
    script = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    product = json.loads((out_dir / "product.json").read_text(encoding="utf-8"))
    print("\n" + "=" * 60)
    print(f"🔁 Re-render: {product['name']}  ({out_dir})")
    print("=" * 60)
    return finish(out_dir, script, product, skip_approval)


def main():
    parser = argparse.ArgumentParser(description="TT Content Publisher — TikTok Shop affiliate video")
    parser.add_argument("--csv", help="Products CSV (batch mode)")
    parser.add_argument("--rerender", nargs="+", metavar="DIR",
                        help="Re-render output folder(s) after adding canh_N.png images")
    parser.add_argument("--product", help="Product name")
    parser.add_argument("--price", type=int, help="Price in VND")
    parser.add_argument("--category", default="Nhà cửa", help="Product category")
    parser.add_argument("--images", default="", help="Comma-separated image paths or URLs (max 3 used)")
    parser.add_argument("--points", default="", help="Selling points, |-separated")
    parser.add_argument("--url", default="", help="TikTok Shop product URL (for post.txt)")
    parser.add_argument("--notes", default="", help="Constraints / target customer for the script")
    parser.add_argument("--style", default="story", choices=["story", "simple"],
                        help="story = skit with AI characters; simple = product images only")
    parser.add_argument("--output-dir", default="storage/videos", help="Output directory")
    parser.add_argument("--skip-approval", action="store_true", help="Skip manual approval step")
    args = parser.parse_args()

    load_env()
    if args.rerender:
        for d in args.rerender:
            r = rerender(Path(d), args.skip_approval)
            print(f"\n{r['status']:<24} {r.get('dir', '')}")
        return
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set. Add it to .env (see .env.example)")
        sys.exit(1)

    if args.csv:
        products = load_products_csv(args.csv)
    elif args.product:
        products = [{
            "name": args.product, "price": args.price or 0, "category": args.category,
            "images": _split(args.images, ","), "selling_points": _split(args.points, "|"),
            "product_url": args.url, "notes": args.notes, "style": None,
        }]
    else:
        parser.error("Use --csv FILE or --product NAME [--price VND]")

    base_dir = Path(args.output_dir)
    results = []
    for product in products:
        try:
            results.append((product["name"], run_one(product, base_dir, args.style, args.skip_approval)))
        except Exception as e:
            print(f"❌ {product['name']}: {e}")
            results.append((product["name"], {"status": "error", "error": str(e)}))

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for name, r in results:
        print(f"{r['status']:<24} {name}  {r.get('dir', r.get('error', ''))}")


if __name__ == "__main__":
    main()
