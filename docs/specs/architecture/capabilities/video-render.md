# Capability: video-render

> **Mục đích**: Render video TikTok hoàn chỉnh (MP4, 1080x1920, 9:16)
> từ ảnh sản phẩm + voiceover audio + text overlays.

---

## Overview

| | |
|--|--|
| **Input** | `script JSON`, `image_paths[]`, `audio_path` (voiceover), `product data` |
| **Output** | `output.mp4` (1080x1920, H.264, AAC, 15-60s) |
| **SLA** | 1-3 phút/video (CPU render), < 30s (GPU) |
| **Cost** | $0 (FFmpeg local, chạy trên desktop nhà) |

---

## Workflow

```
[Inputs: script, images, audio]
        ↓
1. Download product images → local cache (storage/images/)
        ↓
2. Prepare images:
   - Crop to square (center crop)
   - Resize to 1080x1080
   - Place on 1080x1920 white/gradient background
        ↓
3. Generate voiceover audio:
   - edge-tts (free, Vietnamese) → default
   - OpenAI TTS API → fallback nếu cần quality cao
        ↓
4. Calculate slide durations:
   - Total duration = audio duration
   - Each image = total_duration / num_images
        ↓
5. Render với FFmpeg/MoviePy:
   - Slideshow từ images
   - Text overlays: hook (0-3s), tên SP, giá, CTA cuối
   - Voiceover track
   - Background music (volume 15%, optional)
   - Transitions: fade giữa slides
        ↓
6. Export: MP4, H.264, AAC, 1080x1920, FPS=30
        ↓
[Output: storage/videos/{job_id}/output.mp4]
```

---

## Video Specifications

```
Format:     MP4
Codec:      H.264 (libx264)
Audio:      AAC, 44.1kHz, stereo
Resolution: 1080 × 1920 (9:16 portrait)
FPS:        30
Duration:   15-60 giây
Max size:   500MB (TikTok limit)
Bitrate:    ~4-8 Mbps video, 128kbps audio
```

---

## Text Overlay Rules

| Element | Vị trí | Timing | Style |
|---------|--------|--------|-------|
| Hook text | Top center, y=100 | 0-3s | Font 60px, màu vàng, stroke đen |
| Tên sản phẩm | Bottom, y=1300 | Toàn video | Font 45px, trắng, stroke đen |
| Giá / discount | Bottom, y=1420 | Toàn video | Font 55px, đỏ (#FF4444) |
| CTA text | Bottom center | Cuối 10s | Font 50px, trắng nền mờ |

---

## TTS Configuration

```python
# edge-tts (free, default)
EDGE_TTS_VOICE = "vi-VN-HoaiMyNeural"  # Giọng nữ Việt tự nhiên
EDGE_TTS_SPEED = "+10%"                # Hơi nhanh cho TikTok

# OpenAI TTS (fallback)
OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "nova"
OPENAI_TTS_SPEED = 1.1
```

---

## File Structure

```
storage/
└── {job_id}/
    ├── product_0.jpg      ← raw download
    ├── product_1.jpg
    ├── product_0_prepared.jpg  ← resized + bg
    ├── voiceover.mp3      ← TTS output
    ├── bg_music.mp3       ← optional background
    └── output.mp4         ← final video
```

---

## Error Handling

| Lỗi | Nguyên nhân | Xử lý |
|-----|-------------|-------|
| Image download fail | URL expired / network | Skip image, dùng ảnh còn lại |
| No images | Shopee không có ảnh | Tạo solid color slide với text |
| Audio too short | TTS < 5s | Re-generate với voiceover_text dài hơn |
| FFmpeg error | Missing codec | Check `ffmpeg -codecs` và install |
| Output > 500MB | Video quá dài/quality cao | Giảm bitrate hoặc cắt bớt duration |

---

## Cost Notes

- **edge-tts**: Hoàn toàn miễn phí (Microsoft Edge TTS)
- **FFmpeg**: Miễn phí, chạy local trên desktop
- **OpenAI TTS**: $15/1M chars ≈ $0.002/video (500 chars/video)
- **Celery worker**: Chạy trên cùng desktop, không tốn thêm

---

## Dependencies

- `script-gen` → script JSON
- `shopee-sync` → image URLs
- FFmpeg (`apt install ffmpeg`)
- Python packages: `moviepy`, `Pillow`, `edge-tts`
- Storage path: `STORAGE_PATH` env var

---

## Files

```
backend/app/services/video/
├── renderer.py          ← main render logic
├── image_processor.py   ← crop, resize, overlay
└── tts_service.py       ← edge-tts + OpenAI TTS wrapper
```
