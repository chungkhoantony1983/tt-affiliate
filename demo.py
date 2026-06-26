"""
TT Content Publisher — CLI Demo
Quick demo: Product → Script (Groq) → TTS (edge-tts) → Video (FFmpeg) → Ready to publish
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Script Generation (Groq API)
# ---------------------------------------------------------------------------

def generate_script(product_name: str, price: int, category: str) -> dict:
    """Generate a TikTok video script using Groq API."""
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

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

    print("📝 Generating script with Groq (GPT-OSS 120B)...")
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000,
    )

    content = response.choices[0].message.content.strip()
    # Extract JSON from response
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    script = json.loads(content)
    print(f"✅ Script generated ({script.get('estimated_duration_sec', '?')}s)")
    return script


# ---------------------------------------------------------------------------
# 2. TTS — Text to Speech (edge-tts)
# ---------------------------------------------------------------------------

def _clean_tts_text(text: str) -> str:
    """Remove stage-direction labels like [Hook 0-3s] that break edge-tts."""
    text = re.sub(r"\[[^\]]*\]", "", text)   # strip [...]
    text = re.sub(r"\s{2,}", " ", text)        # collapse whitespace
    return text.strip()


async def generate_voiceover(text: str, output_path: str) -> str:
    """Generate Vietnamese voiceover using edge-tts."""
    import edge_tts

    voice = "vi-VN-HoaiMyNeural"
    clean  = _clean_tts_text(text)
    print(f"🎙️  Generating voiceover ({voice})...")
    print(f"   Text ({len(clean)} chars): {clean[:80]}...")

    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(clean, voice, rate="+5%")
            await communicate.save(output_path)
            break
        except Exception as e:
            if attempt < 2:
                print(f"   Retry {attempt + 1}/2 after error: {e}")
                await asyncio.sleep(2)
            else:
                raise

    print(f"✅ Voiceover saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 3. Video Render — 3-scene animation (Pillow + FFmpeg concat)
# ---------------------------------------------------------------------------

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
    """Draw horizontally centered text; return next y."""
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=color)
    return y + (bb[3] - bb[1]) + 14


def _wtext(draw, text: str, y: int, font, W: int, color, chars=26) -> int:
    for line in textwrap.wrap(text, width=chars):
        y = _ctext(draw, line, y, font, W, color) + 4
    return y


def _scene_hook(W: int, H: int, hook: str, get_font) -> "Image.Image":
    """Scene 1 — full-screen hook question."""
    from PIL import ImageDraw
    img  = _gradient(W, H, (14, 8, 48), (50, 12, 90))
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([60, 160, W - 60, 170], fill="#7c3aed")
    _ctext(draw, "TT CONTENT PUBLISHER", 185, get_font(28), W, "#a78bfa")

    # Hook — vertically centered
    font  = get_font(72)
    lines = textwrap.wrap(hook, width=20)
    lh    = 96
    total = len(lines) * lh
    y     = (H - total) // 2 - 80
    for line in lines:
        y = _ctext(draw, line, y, font, W, "white") + 4

    # Scroll hint
    _ctext(draw, "Xem ngay >>", H - 280, get_font(38), W, "#c4b5fd")
    draw.rectangle([60, H - 230, W - 60, H - 220], fill="#7c3aed")
    return img


def _scene_product(W: int, H: int, name: str, price_text: str, body: str,
                   get_font) -> "Image.Image":
    """Scene 2 — product name, price badge, body description."""
    from PIL import ImageDraw
    img  = _gradient(W, H, (8, 18, 50), (18, 40, 80))
    draw = ImageDraw.Draw(img)

    # Product name
    y = 140
    y = _wtext(draw, name, y, get_font(64), W, "white", chars=22) + 24

    # Horizontal rule
    draw.rectangle([100, y, W - 100, y + 4], fill="#3b82f6")
    y += 36

    # Price badge
    pf    = get_font(84)
    pbb   = draw.textbbox((0, 0), price_text, font=pf)
    pw, ph = pbb[2] - pbb[0] + 80, pbb[3] - pbb[1] + 28
    px    = (W - pw) // 2
    draw.rounded_rectangle([px, y, px + pw, y + ph], radius=22, fill=(210, 40, 40))
    draw.text(((W - (pbb[2] - pbb[0])) / 2, y + 14), price_text, font=pf, fill="white")
    y += ph + 52

    # Body text
    y = _wtext(draw, body, y, get_font(46), W, "#ccd8f5", chars=24)

    # Bottom hint
    _ctext(draw, "Chi tiet san pham >>", H - 260, get_font(36), W, "#60a5fa")
    draw.rectangle([100, H - 210, W - 100, H - 202], fill="#3b82f6")
    return img


def _scene_cta(W: int, H: int, cta: str, tags: str, price_text: str,
               get_font) -> "Image.Image":
    """Scene 3 — call to action + buy now."""
    from PIL import ImageDraw
    img  = _gradient(W, H, (45, 8, 65), (90, 18, 110))
    draw = ImageDraw.Draw(img)

    # Top flash-sale banner
    draw.rectangle([0, 0, W, 130], fill=(200, 35, 35))
    _ctext(draw, "FLASH SALE - HOM NAY", 32, get_font(52), W, "white")

    # Price (big)
    y = 180
    y = _ctext(draw, price_text, y, get_font(96), W, "#ffd700") + 16

    # Divider
    draw.rectangle([100, y, W - 100, y + 4], fill="#a78bfa")
    y += 40

    # CTA text
    y = _wtext(draw, cta, y, get_font(58), W, "white", chars=20) + 20

    # "Link mua o BIO" pill
    pill_text = "Link mua o BIO  >"
    pf     = get_font(44)
    pbb    = draw.textbbox((0, 0), pill_text, font=pf)
    pw, ph = pbb[2] - pbb[0] + 60, pbb[3] - pbb[1] + 24
    px     = (W - pw) // 2
    draw.rounded_rectangle([px, y, px + pw, y + ph], radius=ph // 2, fill="#7c3aed")
    draw.text(((W - (pbb[2] - pbb[0])) / 2, y + 12), pill_text, font=pf, fill="white")
    y += ph + 40

    # Hashtags
    _wtext(draw, tags, y, get_font(34), W, "#c4b5fd", chars=32)
    return img


def render_video(
    voiceover_path: str,
    script: dict,
    product_name: str,
    price: int,
    output_path: str,
) -> str:
    """3-scene video: hook → product → CTA.  Pillow draws frames, FFmpeg concat + audio."""
    from PIL import ImageFont

    print("🎬 Rendering video — 3 scenes (1080x1920)...")

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
    price_text = f"{price:,}d".replace(",", ".")      # ASCII only for safety
    hook_text  = script.get("hook", product_name)
    body_text  = script.get("body", "San pham chat luong cao")
    cta_text   = script.get("cta",  "Mua ngay qua link!")
    tags_text  = " ".join(script.get("hashtags", [])[:4])

    # Scene durations
    s1 = max(6.0,  duration * 0.18)
    s3 = max(7.0,  duration * 0.25)
    s2 = max(5.0,  duration - s1 - s3)

    scenes = [
        (_scene_hook(W, H, hook_text, get_font),               round(s1, 2)),
        (_scene_product(W, H, product_name, price_text,
                        body_text, get_font),                   round(s2, 2)),
        (_scene_cta(W, H, cta_text, tags_text,
                    price_text, get_font),                      round(s3, 2)),
    ]

    out_dir     = Path(output_path).parent
    frame_files = []
    for i, (img, dur) in enumerate(scenes):
        fp = str(out_dir / f"_scene_{i}.png")
        img.save(fp)
        frame_files.append((fp, dur))
        print(f"   Scene {i+1}: {dur:.1f}s  →  {fp}")

    # Build FFmpeg args: one -loop 1 -t D -r 25 -i FILE per scene, then audio
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
        print(f"❌ FFmpeg stderr:\n{result.stderr[-3000:]}")
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"✅ Video: {output_path}  ({size_mb:.1f} MB, {duration:.1f}s, 3 scenes)")
    return output_path


# ---------------------------------------------------------------------------
# 4. Approval Step
# ---------------------------------------------------------------------------

def approval_step(script: dict, video_path: str) -> bool:
    """Manual approval before publishing."""
    print("\n" + "=" * 60)
    print("📋 REVIEW BEFORE PUBLISHING")
    print("=" * 60)
    print(f"\n🎯 Hook: {script.get('hook', 'N/A')}")
    print(f"\n📖 Body: {script.get('body', 'N/A')}")
    print(f"\n🛒 CTA: {script.get('cta', 'N/A')}")
    print(f"\n#️⃣  Tags: {', '.join(script.get('hashtags', []))}")
    print(f"\n🎬 Video: {video_path}")
    print(f"\n⏱️  Duration: ~{script.get('estimated_duration_sec', '?')}s")
    print("=" * 60)

    response = input("\n✅ Approve and publish? (y/n): ").strip().lower()
    return response == "y"


# ---------------------------------------------------------------------------
# 5. Publish (mock — TikTok API not yet approved)
# ---------------------------------------------------------------------------

def publish_to_tiktok(video_path: str, script: dict) -> dict:
    """Mock publish — will use TikTok Content Posting API when approved."""
    print("\n🚀 Publishing to TikTok...")
    print("   ⚠️  TikTok API pending approval — simulating publish")
    print(f"   📤 Video: {video_path}")
    print(f"   📝 Title: {script.get('hook', 'Product Review')}")
    print(f"   #️⃣  Hashtags: {', '.join(script.get('hashtags', []))}")

    result = {
        "status": "simulated",
        "timestamp": datetime.now().isoformat(),
        "video_path": video_path,
        "message": "TikTok API approval pending. Video ready for manual upload.",
    }
    print(f"\n✅ Publish simulated at {result['timestamp']}")
    print("   → Upload this video manually to TikTok for now")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="TT Content Publisher — Generate affiliate video for TikTok"
    )
    parser.add_argument("--product", required=True, help="Product name")
    parser.add_argument("--price", type=int, required=True, help="Price in VND")
    parser.add_argument("--category", default="Nhà cửa",
                        choices=["Nhà cửa", "Công nghệ", "Đồ bếp", "Phụ kiện ô tô"],
                        help="Product category")
    parser.add_argument("--output-dir", default="storage/demo",
                        help="Output directory")
    parser.add_argument("--skip-approval", action="store_true",
                        help="Skip manual approval step")

    args = parser.parse_args()

    # Check requirements
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set. Run: export GROQ_API_KEY=your_key")
        sys.exit(1)

    # Setup output dir
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 60)
    print("🎯 TT CONTENT PUBLISHER — Video Generation Pipeline")
    print("=" * 60)
    print(f"Product: {args.product}")
    print(f"Price:   {args.price:,}đ")
    print(f"Category: {args.category}")
    print("=" * 60)

    # Step 1: Generate script
    script = generate_script(args.product, args.price, args.category)

    # Save script
    script_path = out_dir / f"script_{timestamp}.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"💾 Script saved: {script_path}")

    # Step 2: Generate voiceover
    audio_path = str(out_dir / f"voiceover_{timestamp}.mp3")
    asyncio.run(generate_voiceover(script["full_script"], audio_path))

    # Step 3: Render video
    video_path = str(out_dir / f"video_{timestamp}.mp4")
    render_video(audio_path, script, args.product, args.price, video_path)

    # Step 4: Approval
    if not args.skip_approval:
        approved = approval_step(script, video_path)
        if not approved:
            print("\n❌ Video rejected. Pipeline stopped.")
            sys.exit(0)
    else:
        print("\n⏩ Approval skipped (--skip-approval)")

    # Step 5: Publish (mock)
    result = publish_to_tiktok(video_path, script)

    # Summary
    print("\n" + "=" * 60)
    print("📊 PIPELINE SUMMARY")
    print("=" * 60)
    print(f"✅ Script:    {script_path}")
    print(f"✅ Voiceover: {audio_path}")
    print(f"✅ Video:     {video_path}")
    print(f"✅ Status:    {result['status']}")
    print("=" * 60)
    print("\nDone! 🎉")


if __name__ == "__main__":
    main()
