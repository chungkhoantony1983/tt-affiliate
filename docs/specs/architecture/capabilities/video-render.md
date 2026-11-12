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
| No images | E-commerce không có ảnh | Tạo solid color slide với text |
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
- `ecommerce-sync` → image URLs
- FFmpeg (`apt install ffmpeg`)
- Python packages: `moviepy`, `Pillow`, `edge-tts`
- Storage path: `STORAGE_PATH` env var

---

## Duyệt & sửa trên web (Studio) — DR-0001

> Áp dụng cho MVP `demo.py`. Quyết định và lý do: `docs/decision-records/DR-0001-video-review-studio.md`.

### Luồng

```
demo.py … → render_video → [APPROVAL_MODE=web, mặc định] dừng, status=review, giữ thư mục
                 │
                 ▼  http://127.0.0.1:8000/studio  (service creator_main, bấm đúp scripts/mo-studio.command)
        Xem video → sửa caption / hashtag / hook / chữ cảnh / giá / lời đọc / ảnh
                 → "Dựng lại video" = demo.py --render-only DIR   (chỉ đọc lại câu đã sửa)
                 → "Duyệt & lưu"    = demo.py --approve DIR       (post.txt → Drive → status=done)
```

- `APPROVAL_MODE=terminal`: giữ cách cũ (`approval_step`, hỏi `y/n`). `--skip-approval`: duyệt luôn, không dừng.
- `--render-only` xoá `post.txt` cũ nếu có: video mới phải duyệt lại.
- `--approve` từ chối (exit 4) nếu `script.json` còn `needs_render` hoặc còn cảnh story thiếu ảnh.

### Dữ liệu trong thư mục video

| Trường / file | Ý nghĩa |
|---------------|---------|
| `script.json` → `tts_provider` | `gemini` hoặc `edge`: bộ giọng của video. Thư mục cũ không có thì đoán theo cài đặt hiện tại |
| `script.json` → `segments[i].audio_line` | Câu đã dùng để tạo `audio_i.mp3`. `line != audio_line` → câu cần đọc lại |
| `script.json` → `needs_render` | Studio đặt khi sửa hook/giá/lời đọc/chữ cảnh/ảnh. `render_and_check` xoá sau khi dựng |
| `product.json` → `images[k]` | URL, hoặc `anh_sp_{k+1}.<ext>` (ảnh tải lên, nằm trong thư mục video) |
| `canh_N.<ext>` | Ảnh cảnh story N (tải lên từ Studio hoặc chép tay) |
| `storage/studio-logs/<thư mục>.log` | Log của job Studio gần nhất. Nằm ngoài thư mục video để không bị tải lên Drive |

Cột `status` trên Sheet thêm giá trị `review` (đã dựng, chờ duyệt trên web).

### Quy tắc giọng đọc (C-0001-1)

- Một video chỉ dùng một bộ giọng. `revoice_changed()` đọc lại các câu đã sửa bằng `tts_provider` của video.
- Tạo hết file mới (`_new_audio_i.mp3`) rồi mới thay. Lỗi ở bất kỳ câu nào → xoá file tạm, **không đổi audio nào**, exit 3.
- Studio khi đó đưa lựa chọn `--revoice-all edge`: đọc lại toàn bộ bằng edge-tts, `tts_provider=edge`.
- Mỗi câu sửa trên video Gemini = 1 lượt (free tier 10 lượt/ngày). Trang hiện số lượt trước khi dựng.

### API (`backend/app/api/studio.py`, prefix `/api/studio`)

| Method | Path | Việc |
|--------|------|------|
| GET | `/videos` | Danh sách thư mục có `video.mp4`, nhãn `review` / `needs_images` / `approved` / `view_only` |
| GET | `/videos/{folder}` | Chi tiết: caption, hook, giá, từng cảnh, ảnh, bộ giọng, `needs_render` |
| GET | `/videos/{folder}/video`, `/files/{name}` | Phát video; ảnh `canh_N`, `anh_sp_N`, `img_N` |
| PUT | `/videos/{folder}` | Lưu sửa vào JSON, không dựng |
| POST | `/videos/{folder}/image?target=scene\|product&index=` | Body là bytes ảnh. PNG/JPG/WEBP, ≤ 15 MB, kiểm bằng Pillow |
| POST | `/videos/{folder}/render` | Body `{"revoice_all": "edge"}` tuỳ chọn. Chạy `demo.py --render-only` nền |
| POST | `/videos/{folder}/approve` | Chạy `demo.py --approve` nền |
| GET | `/job` | `idle` / `running` / `done` / `error` (`error_kind`: `revoice`, `not_ready`, `failed`) + log |

- Mỗi lúc chỉ một job. Job thứ hai, hoặc sửa/tải ảnh khi job đang chạy → 409.
- API ghi bắt buộc header `X-Studio: 1` và Host là `127.0.0.1`/`localhost` (C-0001-3). Header này không nằm trong CORS `allow_headers`.
- Thư mục không có `product.json` hoặc `segments` (video bài tập làm ngoài repo) → `view_only`, API ghi trả 409.
- `api/studio.py` không xử lý video (C-0001-2): chỉ đọc/ghi JSON, ảnh và chạy `demo.py` bằng `sys.executable`, cwd = repo root.

---

## Files

```
backend/app/services/video/
├── renderer.py          ← main render logic
├── image_processor.py   ← crop, resize, overlay
└── tts_service.py       ← edge-tts + OpenAI TTS wrapper
```
