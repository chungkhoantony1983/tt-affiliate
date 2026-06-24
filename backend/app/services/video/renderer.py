"""
Video Renderer - tạo video TikTok từ ảnh sản phẩm + voiceover
sử dụng MoviePy + FFmpeg
"""
import os
import json
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, TextClip, ColorClip
)
from moviepy.audio.AudioClip import CompositeAudioClip

# TikTok format: 1080x1920 (9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30


def download_image(url: str, save_path: str) -> str:
    """Download ảnh từ URL về local."""
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)
    return save_path


def prepare_product_image(image_path: str, output_path: str) -> str:
    """
    Resize và crop ảnh về 1080x1080 (square), sau đó đặt trên background 1080x1920.
    """
    img = Image.open(image_path).convert("RGB")

    # Square crop từ center
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    img = img.resize((1080, 1080), Image.LANCZOS)

    # Tạo background 1080x1920 màu trắng
    bg = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color=(255, 255, 255))
    # Đặt ảnh sản phẩm ở giữa (padding top 200px)
    bg.paste(img, (0, 200))

    bg.save(output_path, "JPEG", quality=95)
    return output_path


def add_text_overlay(image_path: str, texts: list[dict], output_path: str) -> str:
    """
    Thêm text overlay lên ảnh.
    texts: [{"text": "...", "x": 0, "y": 0, "font_size": 60, "color": (255,255,255)}]
    """
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for item in texts:
        try:
            # Sử dụng font mặc định nếu không có custom font
            font = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                item.get("font_size", 50)
            )
        except Exception:
            font = ImageFont.load_default()

        draw.text(
            (item.get("x", 50), item.get("y", 50)),
            item["text"],
            fill=item.get("color", (255, 255, 255)),
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

    img.save(output_path, "JPEG", quality=95)
    return output_path


def render_product_video(
    product: dict,
    script: dict,
    image_paths: list[str],
    audio_path: str,
    output_path: str,
    bg_music_path: str = None
) -> str:
    """
    Render video sản phẩm hoàn chỉnh.
    
    Args:
        product: thông tin sản phẩm
        script: kịch bản từ AI (hook, benefits, cta...)
        image_paths: danh sách đường dẫn ảnh sản phẩm local
        audio_path: đường dẫn file voiceover
        output_path: đường dẫn xuất video
        bg_music_path: nhạc nền (optional)
    
    Returns: path đến video đã render
    """
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    clips = []
    n_images = max(len(image_paths), 1)
    img_duration = total_duration / n_images

    for i, img_path in enumerate(image_paths):
        # Chuẩn bị ảnh
        prepared_path = img_path.replace(".jpg", "_prepared.jpg")
        prepare_product_image(img_path, prepared_path)

        clip = ImageClip(prepared_path, duration=img_duration)

        # Thêm tên sản phẩm trên ảnh đầu
        if i == 0:
            price_text = f"💰 {product.get('price', 0):,.0f}đ"
            if product.get("discount_percent", 0) > 0:
                price_text += f" (-{product['discount_percent']:.0f}%)"

            name_clip = TextClip(
                product["name"][:50],
                fontsize=45,
                color="white",
                font="Arial-Bold",
                stroke_color="black",
                stroke_width=2,
                size=(1000, None),
                method="caption"
            ).set_position(("center", 1300)).set_duration(img_duration)

            price_clip = TextClip(
                price_text,
                fontsize=55,
                color="#FF4444",
                font="Arial-Bold",
                stroke_color="white",
                stroke_width=2
            ).set_position(("center", 1420)).set_duration(img_duration)

            clip = CompositeVideoClip([clip, name_clip, price_clip])

        # Hook text trên ảnh đầu
        if i == 0 and script.get("hook"):
            hook_clip = TextClip(
                script["hook"],
                fontsize=60,
                color="yellow",
                font="Arial-Bold",
                stroke_color="black",
                stroke_width=3,
                size=(1000, None),
                method="caption"
            ).set_position(("center", 100)).set_duration(min(3.0, img_duration))

            clip = CompositeVideoClip([clip, hook_clip])

        clips.append(clip.set_fps(FPS))

    # Ghép clips
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_duration(total_duration)

    # Thêm voiceover
    if bg_music_path and os.path.exists(bg_music_path):
        bg_audio = AudioFileClip(bg_music_path).volumex(0.15)
        bg_audio = bg_audio.subclip(0, total_duration)
        final_audio = CompositeAudioClip([audio, bg_audio])
        final_video = final_video.set_audio(final_audio)
    else:
        final_video = final_video.set_audio(audio)

    # Export
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="/tmp/temp_audio.m4a",
        remove_temp=True,
        verbose=False,
        logger=None
    )

    return output_path
