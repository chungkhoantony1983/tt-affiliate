# TikTok & Shopee Affiliate Automation Platform — Kế Hoạch Xây Dựng

> **Mục tiêu:** Tự động tạo video TikTok chất lượng cao để quảng cáo sản phẩm Shopee Affiliate và nội dung lifestyle hỗ trợ tăng trưởng kênh.

---

## Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                     CONTROL DASHBOARD                        │
│              (Web UI - quản lý & theo dõi)                   │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                       N8N WORKFLOWS                          │
│  (Orchestration: trigger, schedule, connect các service)     │
└──┬──────────────┬──────────────┬──────────────┬─────────────┘
   │              │              │              │
┌──▼──┐      ┌───▼───┐     ┌────▼────┐    ┌────▼────┐
│ AI  │      │ Video │     │ TikTok  │    │ Shopee  │
│Engine│     │Renderer│    │  API    │    │  API    │
│(LLM)│      │(FFmpeg)│    │(Upload) │    │(Products│
└─────┘      └───────┘     └─────────┘    └─────────┘
```

---

## Phase 1 — Nền Tảng (Tuần 1-2)

### 1.1 Setup Môi Trường
- [ ] Cài đặt N8N (self-hosted via Docker)
- [ ] Setup Python backend (FastAPI)
- [ ] Setup database (PostgreSQL)
- [ ] Cấu hình Redis (task queue)
- [ ] Tạo `.env` quản lý API keys

### 1.2 Kết Nối Shopee Affiliate
- [ ] Đăng ký Shopee Affiliate API / Shopee Open Platform
- [ ] Fetch danh sách sản phẩm từ store
- [ ] Lưu sản phẩm vào DB (tên, giá, ảnh, link affiliate, category)
- [ ] Tự động generate affiliate link tracking

### 1.3 Kết Nối TikTok
- [ ] Đăng ký TikTok for Developers → Content Posting API
- [ ] OAuth2 authentication flow
- [ ] Test upload video thủ công

---

## Phase 2 — AI Content Engine (Tuần 2-4)

### 2.1 Script Generator (AI)

**Input:** Thông tin sản phẩm (tên, giá, mô tả, category)  
**Output:** Kịch bản video TikTok 15-60 giây

```
Prompt Template:
- Hook (0-3s): câu mở đầu gây chú ý
- Problem/Need (3-10s): đặt vấn đề người xem gặp phải  
- Solution (10-30s): sản phẩm giải quyết như thế nào
- Social Proof (30-45s): lợi ích, đánh giá
- CTA (45-60s): link bio / comment để nhận link
```

**AI Models sử dụng:**
| Công việc | Tool đề xuất |
|-----------|-------------|
| Viết script | GPT-4o / Claude 3.5 Sonnet |
| Text-to-Speech (giọng đọc) | ElevenLabs / OpenAI TTS |
| Tạo hình ảnh sản phẩm | Stable Diffusion / Ideogram |
| Tạo video AI | Kling AI / Runway ML / Pika |
| Background music | Suno AI / Pixabay API |
| Caption/Subtitle | Whisper API |

### 2.2 Video Types (2 loại chính)

#### Loại 1: Product Showcase Video
```
Template: [Hook text] → [Product images slideshow] → 
          [Benefits bullets] → [Price reveal] → [CTA]
Duration: 15-30 giây
```

#### Loại 2: Lifestyle Content Video (tăng organic reach)
```
Template: [Life tip/hack] → [Problem] → [Solution] →
          [Product recommendation tự nhiên] → [CTA nhẹ]
Duration: 30-60 giây
Categories: mẹo cuộc sống, nấu ăn, làm đẹp, tổ chức nhà cửa
```

### 2.3 Video Renderer (FFmpeg Pipeline)
- Ghép ảnh sản phẩm thành slideshow
- Overlay text/caption
- Thêm voiceover
- Thêm background music (volume thấp)
- Thêm intro/outro branding
- Export: MP4 1080x1920 (9:16 portrait)

---

## Phase 3 — N8N Automation Workflows (Tuần 3-5)

### Workflow 1: Daily Product Video
```
Schedule (9:00 AM daily)
    → Lấy sản phẩm chưa được làm video từ DB
    → Gọi AI Script Generator API  
    → Gọi Video Renderer API
    → Review queue (optional manual approval)
    → Upload lên TikTok
    → Lưu kết quả + tracking link vào DB
    → Gửi notification (Telegram/Email)
```

### Workflow 2: Trending Content
```
Schedule (2x/tuần)
    → Fetch TikTok trending hashtags (scraper)
    → Chọn topic phù hợp với niche
    → Tạo lifestyle video AI
    → Upload với trending hashtags
    → Monitor performance
```

### Workflow 3: Performance Monitor
```
Schedule (hàng ngày 10:00 PM)
    → Fetch video stats từ TikTok API (views, likes, shares)
    → Phân tích video nào hiệu quả
    → Cập nhật DB
    → Báo cáo weekly qua Telegram
```

### Workflow 4: Shopee Product Sync
```
Schedule (hàng tuần thứ 2)
    → Sync sản phẩm mới từ Shopee store
    → Kiểm tra sản phẩm hết hàng → disable
    → Cập nhật giá (nếu thay đổi)
    → Flag sản phẩm hot (nhiều đơn hàng)
```

---

## Phase 4 — Dashboard & Analytics (Tuần 5-6)

### Web Dashboard (Next.js hoặc Streamlit đơn giản)
- [ ] Danh sách sản phẩm + trạng thái video
- [ ] Queue video đang chờ render / upload
- [ ] Stats: views, engagement, click affiliate
- [ ] Lịch đăng video (calendar view)
- [ ] Manual trigger tạo video
- [ ] Preview video trước khi đăng

### Analytics Tracking
- TikTok video performance (views, likes, shares, comments)
- Click-through rate từ bio link
- Shopee conversion (qua affiliate tracking)
- Revenue tracking (hoa hồng)

---

## Phase 5 — Tối Ưu & Scale (Tuần 7+)

- [ ] A/B testing hook khác nhau cho cùng sản phẩm
- [ ] Auto-detect sản phẩm trending trên Shopee → ưu tiên tạo video
- [ ] Comment automation (trả lời comment hỏi link)
- [ ] Cross-post lên Instagram Reels / YouTube Shorts
- [ ] Batch generation: 7 video/tuần cùng lúc
- [ ] Template library (lưu template video hiệu quả)

---

## Tech Stack Chi Tiết

| Layer | Technology | Lý do |
|-------|-----------|-------|
| **Automation** | N8N (self-hosted) | Visual workflow, nhiều connector |
| **Backend API** | Python FastAPI | Async, dễ tích hợp AI libs |
| **Task Queue** | Celery + Redis | Xử lý render video nền |
| **Database** | PostgreSQL | Structured data, relations |
| **Video Processing** | FFmpeg + MoviePy | Mạnh, free, linh hoạt |
| **AI Script** | OpenAI GPT-4o API | Chất lượng cao, API đơn giản |
| **AI Voice** | OpenAI TTS / ElevenLabs | Giọng tiếng Việt tự nhiên |
| **AI Video** | Kling AI API | Video AI chất lượng tốt |
| **Storage** | MinIO / AWS S3 | Lưu video render |
| **Dashboard** | Streamlit (MVP) | Nhanh, đơn giản |
| **Container** | Docker + Docker Compose | Dễ deploy |
| **Notifications** | Telegram Bot API | Nhận thông báo realtime |

---

## Chi Phí Ước Tính (Hàng Tháng)

| Service | Chi phí |
|---------|---------|
| OpenAI API (GPT-4o + TTS) | ~$20-50 |
| ElevenLabs (nếu dùng) | ~$5-22 |
| Kling AI / Runway (video AI) | ~$20-50 |
| VPS (N8N + Backend) | ~$10-20 |
| AWS S3 / Storage | ~$5 |
| **Tổng** | **~$60-150/tháng** |

> Với 1100 followers ban đầu, target: 10K followers trong 3 tháng → affiliate income bù đắp chi phí

---

## Thứ Tự Ưu Tiên Xây Dựng (MVP First)

```
Sprint 1 (MVP - 1 tuần):
✅ Script AI generate từ thông tin sản phẩm
✅ FFmpeg render slideshow + voiceover đơn giản  
✅ Upload thủ công lên TikTok (test)

Sprint 2 (Automation - 1 tuần):
✅ N8N workflow tự động hóa pipeline
✅ TikTok API auto-upload
✅ Shopee product sync

Sprint 3 (Quality - 1 tuần):
✅ Video quality cải thiện (transitions, effects)
✅ Dashboard theo dõi
✅ Analytics cơ bản

Sprint 4 (Scale):
✅ A/B testing
✅ Lifestyle content pipeline
✅ Multi-platform (Reels, Shorts)
```

---

## Bước Tiếp Theo Ngay Bây Giờ

1. **Xác nhận tools AI** muốn sử dụng (GPT-4o? ElevenLabs?)
2. **Kiểm tra TikTok API access** — cần apply Content Posting API
3. **Shopee Affiliate API** — đã có access chưa?
4. **Server/VPS** đã có hay cần setup?
5. Bắt đầu code **MVP Phase 1** với cấu trúc project

---

*Được tạo: 2026-06-24 | Version 1.0*
