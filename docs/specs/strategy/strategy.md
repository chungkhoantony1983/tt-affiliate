# L1 Strategy — Omni-Channel Affiliate Intelligence Platform

> **SSoT**: Tài liệu chiến lược dự án. Định nghĩa scope, actors, constraints, goals.

---

## §0 前提 (Prerequisites)

| 項目 | 内容 |
|------|------|
| **プロジェクト名** | Omni-Channel Affiliate Intelligence |
| **目的** | E-commerce sản phẩm → Đa nền tảng mạng xã hội video tự động, kiếm affiliate commission |
| **運用者** | Solo operator (1 人) |
| **月額予算** | $20–25/月 (Plan B Hybrid) |
| **MVP scope** | 10 video/ngày tự động, 4 niche groups |
| **Timeline** | 1 tháng (4 tuần) |
| **Mục tiêu dài hạn** | Side income tự động, con trai hỗ trợ vận hành |
| **Budget chịu lỗ** | 1-2M₫/tháng × 6 tháng (chi phí học tập) |

---

## §0-A 商品選定基準 (Product Selection Criteria)

### Bộ lọc chọn sản phẩm

| Tiêu chí | Điều kiện |
|----------|----------|
| Giá bán | 100K – 500K VND |
| Hoa hồng | ≥ 10% |
| Số đơn đã bán | ≥ 1,000 đơn |
| Video mẫu trên các platform | ≥ 20 video |
| Giải quyết vấn đề rõ ràng | Có |
| Xem phát hiểu ngay (3 giây) | Có |

### Công thức chọn sản phẩm

> "Người xem có hiểu lợi ích trong 3 giây không?" → Có = chọn, Không = bỏ.

### Niche Groups (Tập trung thị trường Việt Nam)

| Nhóm | Ví dụ | Mùa / Sự kiện tiêu biểu |
|------|-------|--------------|
| Đồ gia dụng & Bếp | Máy hút bụi mini, dao đa năng, máy lọc nước mini | Dọn nhà đón Tết, Mùa mưa, Ở trọ |
| Công nghệ & Phụ kiện | Tai nghe, Sạc nhanh, Cáp, Giá đỡ điện thoại/laptop, Camera mini | Tựu trường, Du lịch/Dã ngoại, Lễ 2/9 |
| Chăm sóc cá nhân & Sức khỏe | Máy cạo lông, Máy vệ sinh tai, Máy matxa cổ gáy | Trung thu (quà tặng), Du lịch hè |
| Phụ kiện xe máy | Áo mưa tiện lợi, chống bám nước, bọc giày | Mùa mưa bão (T6-T9) |

### Không chọn

- ❌ Quần áo, Mỹ phẩm, Thực phẩm chức năng, Nước hoa, Đồ cần giải thích dài

---

## §1 関連組織・アクター・システム

### §1-A 運用者

- **Solo Operator** — quản lý toàn bộ: chọn sản phẩm, review video trước publish, monitor analytics
- **Con trai** — hỗ trợ vận hành lâu dài (cần docs rõ ràng)

### §1-B 外部プラットフォーム

| System | 役割 |
|--------|------|
| **Social Platforms** (system) | Video hosting + distribution + audience (TikTok, FB, YT) |
| **E-commerce Affiliate** (system) | Sản phẩm + affiliate link + commission tracking (Shopee, Lazada, Amazon) |
| **Telegram** (system) | Notification channel |

### §1-C 内部システム

| System | 役割 |
|--------|------|
| **N8N** (system) | Workflow orchestration (self-hosted Docker) |
| **FastAPI Backend** (system) | API server + business logic |
| **Celery + Redis** (system) | Async task queue (video rendering) |
| **PostgreSQL** (system) | Product DB + video job tracking |
| **FFmpeg** (system) | Video rendering engine |
| **edge-tts** (system) | Vietnamese TTS (Microsoft free) |
| **Streamlit Dashboard** (system) | Operations UI |

### §1-D AI サービス

| System | 役割 | Cost |
|--------|------|------|
| **Groq API** (system) | Primary LLM — Llama 3.1 70B, 14,400 req/day | $0 |
| **Gemini 1.5 Flash** (system) | Fallback LLM | $0 |
| **Claude Pro** (system) | Manual quality review (web UI only) | $20/mo |
| **Google Antigravity** (system) | Development IDE + Gemini access | $0 |

---

## §2 ユーザーニーズ (UN)

| ID | UN | Actor | 備考 |
|----|-----|-------|------|
| UN-1 | E-commerce sản phẩm được sync tự động hàng tuần | Operator | Passive — chỉ cần approve |
| UN-2 | Hệ thống tự lọc ra top sản phẩm (highest commission, best seller) | System | Tự động chấm điểm (priority score) |
| UN-3 | Video script được tạo tự động cho sản phẩm chọn lọc | System | LLM agent (Groq/Gemini) |
| UN-4 | Video được publish tự động lên Social Platforms | System | Auto, nhưng operator review video trước publish |
| UN-5 | Nhận báo cáo performance hàng ngày | Operator | Telegram notification |
| UN-6 | Dashboard hiển thị tổng quan pipeline | Operator | Web UI on-demand |

---

## §3 成功条件 (SC)

| ID | Condition | Metric |
|----|-----------|--------|
| SC-1 | Pipeline chạy tự động 24/7 | Uptime > 95% |
| SC-2 | Tạo ≥ 10 video/ngày | Daily video count |
| SC-3 | Chi phí ≤ $25/tháng | Monthly cost tracking |
| SC-4 | Ít nhất 1 video viral/tuần (>10K views) | Weekly analytics |
| SC-5 | Affiliate commission > $0 trong tháng đầu | E-commerce dashboards |
| SC-6 | Full flow hoạt động end-to-end | Pipeline test |
| SC-7 | Dashboard thống kê hoạt động | Streamlit UI |
| SC-8 | Lợi nhuận vượt chi phí (break-even) | Monthly P&L |

---

## §4 制約 (SP — System Properties / Constraints)

| ID | Constraint | Rationale |
|----|-----------|-----------|
| SP-1 | Self-hosted on home desktop (Mac) | Zero hosting cost |
| SP-2 | Docker Compose orchestration | Reproducible, portable |
| SP-3 | No paid API for automation (chỉ free tier) | Budget constraint |
| SP-4 | Vietnamese content only | Target market = VN |
| SP-5 | Video format 1080×1920, H.264, 15–60s | Social Platforms optimal |
| SP-6 | N8N là orchestrator duy nhất | Single control plane |
| SP-7 | Operator review video trước publish | Quality gate |
| SP-8 | Code đơn giản, docs rõ cho handover | Con trai hỗ trợ |
| SP-9 | Delivery trong 1 tháng (4 tuần) | Timeline constraint |

---

## §5 用語集 (UL — Ubiquitous Language)

| Term | Definition |
|------|-----------|
| **Script** | JSON chứa hook + voiceover_text + hashtags + caption cho 1 video |
| **Render job** | Task trong Celery queue: input = script + images → output = .mp4 |
| **Affiliate link** | URL E-commerce có tracking code, earn commission khi user mua |
| **Niche** | Category sản phẩm tập trung (vd: skincare, home decor) |
| **Hook** | 2-3 giây đầu video, quyết định viewer retention |
| **Pipeline** | Full flow: sync → script → render → publish → track |
| **Posting slot** | Thời điểm tối ưu để đăng video (peak hours VN) |

---

## §6 Reference Index

| Ref | Location | Content |
|-----|----------|---------|
| R-1 | [FEASIBILITY.md](../../../FEASIBILITY.md) | Cost analysis, Plans A/B/C, SWOT |
| R-2 | [Social APIs (TikTok, FB, YT)](https://developers.tiktok.com/) | Official API docs |
| R-3 | [E-commerce APIs (Shopee, Lazada)](https://affiliate.shopee.vn/) | Affiliate program docs |
| R-4 | [Groq Console](https://console.groq.com/) | API key + rate limits |
| R-5 | [edge-tts](https://github.com/rany2/edge-tts) | TTS library docs |

---

## §7 SLO (Service Level Objectives)

| Service | Metric | Target |
|---------|--------|--------|
| Video render | Throughput | ≥ 10 videos/day |
| Video render | Latency | < 5 min/video |
| Social publish | Success rate | > 95% |
| E-commerce sync | Freshness | ≤ 7 days stale |
| Pipeline | Availability | > 95% uptime |
| Script generation | Latency | < 30s/script |
