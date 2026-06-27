# Session Summary — TikTok Affiliate Automation
> Cập nhật: 2026-06-26 | Chuyển sang context mới từ file này

---

## Trạng thái dự án

| Hạng mục | Trạng thái |
|----------|-----------|
| GitHub repo | ✅ `https://github.com/chungkhoantony1983/tt-affiliate` |
| GitHub Pages | ✅ Live — `terms.html`, `privacy.html` hoạt động |
| Design docs L1–L4 | ✅ Hoàn chỉnh trong `docs/specs/` |
| CLI demo tool | ✅ `demo.py` hoạt động end-to-end |
| Video mẫu sinh ra | ✅ `storage/demo/video_20260625_002104.mp4` (494KB, 3 scene) |
| TikTok app submission | ❌ Chưa — cần demo video + submit |
| Phase 1 backend code | ❌ Chưa bắt đầu |
| demo.py push lên GitHub | ❌ Chưa commit |

---

## Git / GitHub

```
Repo:     https://github.com/chungkhoantony1983/tt-affiliate
Remote:   git@github-chungkhoantony:chungkhoantony1983/tt-affiliate.git
SSH key:  /Users/trieuanhtuan/.ssh/chungkhoankeygen
Alias:    github-chungkhoantony (trong ~/.ssh/config)
Branch:   main
```

**Uncommitted files cần push:**
```bash
git add demo.py
git commit -m "feat: CLI demo tool — 3-scene video pipeline"
git push
```

---

## demo.py — CLI Tool

**Vị trí:** `/Users/trieuanhtuan/Documents/claude/tiktok_affiliate/demo.py`

**Chạy:**
```bash
export GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
python3 demo.py --product "Máy hút bụi mini" --price 250000 --category "Nhà cửa" --skip-approval
```

**Pipeline 5 bước:**
1. **Groq API** → tạo JSON script (hook/body/cta/full_script/hashtags)
2. **edge-tts** → voiceover MP3 (giọng `vi-VN-HoaiMyNeural`)
3. **Pillow + FFmpeg** → MP4 3 scene (hook → product → CTA)
4. **Approval step** → review trước khi publish (bỏ qua bằng `--skip-approval`)
5. **Mock publish** → log thông tin (TikTok API chưa được duyệt)

**Output:** `storage/demo/script_*.json`, `storage/demo/voiceover_*.mp3`, `storage/demo/video_*.mp4`

**Fixes đã làm:**
- Model: `llama-3.1-70b-versatile` → `openai/gpt-oss-120b` (deprecated)
- Video: bỏ FFmpeg `drawtext` (không có libfreetype) → dùng **Pillow** vẽ frame
- TTS: strip `[Hook 0-3s]` labels bằng `_clean_tts_text()` regex, retry 3 lần
- Font: `Arial Unicode.ttf` tại `/Library/Fonts/Arial Unicode.ttf` (hỗ trợ tiếng Việt)
- Video: 3 scene (gradient bg khác màu) thay vì 1 frame tĩnh

---

## Video 3 Scene

| Scene | Duration | Nội dung | Background |
|-------|----------|---------|------------|
| 1. Hook | 18% tổng | Hook question lớn, centered | Tím đậm `(14,8,48)→(50,12,90)` |
| 2. Product | 57% tổng | Tên sp + price badge đỏ + body | Xanh đậm `(8,18,50)→(18,40,80)` |
| 3. CTA | 25% tổng | Flash Sale banner + giá vàng + CTA pill + hashtags | Tím `(45,8,65)→(90,18,110)` |

FFmpeg concat: `-loop 1 -t {dur} -r 25 -i scene_N.png` + `concat=n=3:v=1:a=0`

---

## Dependencies cài đặt

```
groq==1.5.0          # Groq SDK
edge-tts==7.2.8      # Microsoft TTS
Pillow               # Image/text rendering
ffmpeg 8.1.2         # /opt/homebrew/bin/ffmpeg (brew install ffmpeg)
```

**Lưu ý:** FFmpeg Homebrew build 8.1.2 **KHÔNG có libfreetype** → `drawtext` filter không hoạt động → phải dùng Pillow.

---

## Groq API

- **API Key:** `YOUR_GROQ_API_KEY_HERE`
- **Model hiện tại:** `openai/gpt-oss-120b` (thay thế llama-3.1-70b deprecated Jan 2025)
- **Ghi chú:** `llama-3.3-70b-versatile` vẫn dùng được nhưng deprecated Aug 16, 2026

---

## TikTok Developer App

- **Portal:** https://developers.tiktok.com
- **App đã tạo**, cần:
  1. Quay màn hình demo chạy `demo.py` (~1-2 phút)
  2. Upload video lên App Review
  3. Điền description, use case
  4. Submit for review
- **Scopes cần:** `video.publish`, `video.upload`, `user.info.basic`
- **Privacy Policy:** `https://chungkhoantony1983.github.io/tt-affiliate/privacy.html`
- **Terms:** `https://chungkhoantony1983.github.io/tt-affiliate/terms.html`

---

## GitHub Pages

- **URL:** `https://chungkhoantony1983.github.io/tt-affiliate/`
- `terms.html` → ✅ `https://chungkhoantony1983.github.io/tt-affiliate/terms.html`
- `privacy.html` → ✅ `https://chungkhoantony1983.github.io/tt-affiliate/privacy.html`
- `.nojekyll` đã thêm

---

## Cấu trúc dự án quan trọng

```
demo.py                        ← CLI demo tool (chưa commit)
storage/demo/                  ← Output files (gitignored)
docs/specs/strategy/strategy.md   ← L1: chiến lược, budget, timeline
docs/specs/requirements/capabilities.md  ← L2: 6 capabilities
docs/specs/architecture/capabilities/    ← L3: chi tiết từng cap
docs/specs/implementation/              ← L4: DB schema, security
backend/app/core/config.py     ← FastAPI config (chưa implement)
.env.example                   ← Template cho env vars
```

---

## Việc cần làm tiếp theo (ưu tiên)

1. **[Ngay]** Commit + push `demo.py`:
   ```bash
   git add demo.py && git commit -m "feat: CLI demo tool — 3-scene video pipeline" && git push
   ```

2. **[Ngay]** Quay màn hình chạy demo → upload lên TikTok app review

3. **[Tuần 1]** Bắt đầu Phase 1 backend:
   - FastAPI app structure (đã có skeleton tại `backend/`)
   - Script generation API (`/api/v1/scripts/generate`)
   - TTS API (`/api/v1/tts/generate`)
   - Video render API (`/api/v1/videos/render`)

---

## Business Decisions đã chốt

- **Niche:** Nhà cửa, Công nghệ, Đồ bếp, Phụ kiện ô tô
- **Giá mục tiêu:** 100K–500K VND
- **Commission:** ≥10%
- **Budget:** 1–2M VND/tháng × 6 tháng
- **Operator:** Con trai (chạy pipeline)
- **SP-7:** Review trước khi publish (approval step trong demo.py)
- **Timeline:** 1 tháng (Week 1: Core pipeline, Week 2: Auto-publish, Week 3: Orchestration, Week 4: Dashboard)
