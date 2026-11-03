import asyncio
import json
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

# 1. Script Generation (Groq)
def generate_script_groq(product_name: str, price: int, category: str) -> dict:
    from groq import Groq
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

    prompt = f"""Bạn là chuyên gia tạo kịch bản video TikTok affiliate cho sản phẩm Việt Nam.
Tạo kịch bản video ngắn (15-30 giây) cho sản phẩm sau:

Sản phẩm: {product_name}
Giá: {price:,}đ
Danh mục: {category}

Yêu cầu:
- Hook (3 giây đầu): câu gây tò mò, người xem hiểu lợi ích ngay
- Body (10-20 giây): mô tả lợi ích chính, cách dùng
- CTA (3 giây cuối): kêu gọi mua hàng qua link affiliate
- Tone: tự nhiên, hào hứng, dễ hiểu
- Ngôn ngữ: Tiếng Việt

Trả về JSON format:
{{
  "hook": "...",
  "body": "...",
  "cta": "...",
  "full_script": "câu chuyện liền mạch từ hook đến CTA, KHÔNG có nhãn [Hook]/[Body]/[CTA], chỉ lời thoại thuần tuý để đọc thành tiếng",
  "hashtags": ["#tag1", "#tag2", ...],
  "estimated_duration_sec": 20
}}

CHỈ trả về JSON, không có text khác."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000,
    )

    content = response.choices[0].message.content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    script = json.loads(content)
    return script

# 2. TTS (edge-tts)
def _clean_tts_text(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

async def generate_voiceover_edge(text: str, output_path: str) -> str:
    import edge_tts
    voice = "vi-VN-HoaiMyNeural"
    clean  = _clean_tts_text(text)

    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(clean, voice, rate="+5%")
            await communicate.save(output_path)
            break
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                raise
    return output_path

# 3. Video Render (Pillow + FFmpeg concat)
def _gradient(W: int, H: int, top: tuple, bot: tuple):
    from PIL import Image
    img = Image.new("RGB", (W, H))
    for y in range(H):
        t = y / (H - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        img.paste((r, g, b), (0, y, W, y + 1))
    return img

def _ctext(draw, text: str, y: int, font, W: int, color) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=color)
    return y + (bb[3] - bb[1]) + 14

def _wtext(draw, text: str, y: int, font, W: int, color, chars=26) -> int:
    for line in textwrap.wrap(text, width=chars):
        y = _ctext(draw, line, y, font, W, color) + 4
    return y

def _scene_hook(W: int, H: int, hook: str, get_font) -> "Image.Image":
    from PIL import ImageDraw
    img  = _gradient(W, H, (14, 8, 48), (50, 12, 90))
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 160, W - 60, 170], fill="#7c3aed")
    _ctext(draw, "TT CONTENT PUBLISHER", 185, get_font(28), W, "#a78bfa")
    font  = get_font(72)
    lines = textwrap.wrap(hook, width=20)
    lh    = 96
    total = len(lines) * lh
    y     = (H - total) // 2 - 80
    for line in lines:
        y = _ctext(draw, line, y, font, W, "white") + 4
    _ctext(draw, "Xem ngay >>", H - 280, get_font(38), W, "#c4b5fd")
    draw.rectangle([60, H - 230, W - 60, H - 220], fill="#7c3aed")
    return img

def _scene_product(W: int, H: int, name: str, price_text: str, body: str, get_font) -> "Image.Image":
    from PIL import ImageDraw
    img  = _gradient(W, H, (8, 18, 50), (18, 40, 80))
    draw = ImageDraw.Draw(img)
    y = 140
    y = _wtext(draw, name, y, get_font(64), W, "white", chars=22) + 24
    draw.rectangle([100, y, W - 100, y + 4], fill="#3b82f6")
    y += 36
    pf    = get_font(84)
    pbb   = draw.textbbox((0, 0), price_text, font=pf)
    pw, ph = pbb[2] - pbb[0] + 80, pbb[3] - pbb[1] + 28
    px    = (W - pw) // 2
    draw.rounded_rectangle([px, y, px + pw, y + ph], radius=22, fill=(210, 40, 40))
    draw.text(((W - (pbb[2] - pbb[0])) / 2, y + 14), price_text, font=pf, fill="white")
    y += ph + 52
    y = _wtext(draw, body, y, get_font(46), W, "#ccd8f5", chars=24)
    _ctext(draw, "Chi tiet san pham >>", H - 260, get_font(36), W, "#60a5fa")
    draw.rectangle([100, H - 210, W - 100, H - 202], fill="#3b82f6")
    return img

def _scene_cta(W: int, H: int, cta: str, tags: str, price_text: str, get_font) -> "Image.Image":
    from PIL import ImageDraw
    img  = _gradient(W, H, (45, 8, 65), (90, 18, 110))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 130], fill=(200, 35, 35))
    _ctext(draw, "FLASH SALE - HOM NAY", 32, get_font(52), W, "white")
    y = 180
    y = _ctext(draw, price_text, y, get_font(96), W, "#ffd700") + 16
    draw.rectangle([100, y, W - 100, y + 4], fill="#a78bfa")
    y += 40
    y = _wtext(draw, cta, y, get_font(58), W, "white", chars=20) + 20
    pill_text = "Link mua o BIO  >"
    pf     = get_font(44)
    pbb    = draw.textbbox((0, 0), pill_text, font=pf)
    pw, ph = pbb[2] - pbb[0] + 60, pbb[3] - pbb[1] + 24
    px     = (W - pw) // 2
    draw.rounded_rectangle([px, y, px + pw, y + ph], radius=ph // 2, fill="#7c3aed")
    draw.text(((W - (pbb[2] - pbb[0])) / 2, y + 12), pill_text, font=pf, fill="white")
    y += ph + 40
    _wtext(draw, tags, y, get_font(34), W, "#c4b5fd", chars=32)
    return img

def render_video_demo(voiceover_path: str, script: dict, product_name: str, price: int, output_path: str) -> str:
    from PIL import ImageFont
    ffmpeg_bin  = shutil.which("ffmpeg")  or "/opt/homebrew/bin/ffmpeg"
    ffprobe_bin = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

    probe = subprocess.run(
        [ffprobe_bin, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", voiceover_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())

    font_candidates = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font_path = next((f for f in font_candidates if Path(f).exists()), None)

    def get_font(size: int):
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    W, H       = 1080, 1920
    price_text = f"{price:,}d".replace(",", ".")
    hook_text  = script.get("hook", product_name)
    body_text  = script.get("body", "San pham chat luong cao")
    cta_text   = script.get("cta",  "Mua ngay qua link!")
    tags_text  = " ".join(script.get("hashtags", [])[:4])

    s1 = max(6.0,  duration * 0.18)
    s3 = max(7.0,  duration * 0.25)
    s2 = max(5.0,  duration - s1 - s3)

    scenes = [
        (_scene_hook(W, H, hook_text, get_font), round(s1, 2)),
        (_scene_product(W, H, product_name, price_text, body_text, get_font), round(s2, 2)),
        (_scene_cta(W, H, cta_text, tags_text, price_text, get_font), round(s3, 2)),
    ]

    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_files = []
    for i, (img, dur) in enumerate(scenes):
        fp = str(out_dir / f"_scene_{i}.png")
        img.save(fp)
        frame_files.append((fp, dur))

    inputs = []
    for fp, dur in frame_files:
        inputs += ["-loop", "1", "-t", str(dur), "-r", "25", "-i", fp]
    inputs += ["-i", voiceover_path]

    n = len(frame_files)
    filter_str  = "".join(f"[{i}:v]" for i in range(n))
    filter_str += f"concat=n={n}:v=1:a=0,scale={W}:{H}[vout]"

    ffmpeg_cmd = [
        ffmpeg_bin, "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[vout]",
        "-map", f"{n}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    for fp, _ in frame_files:
        Path(fp).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}\n{result.stderr}")
    return output_path
