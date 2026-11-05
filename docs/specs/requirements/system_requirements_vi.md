# Yêu cầu Hệ thống — Nền tảng Tự động hóa & Phân tích Dữ liệu Affiliate

> **SSoT**: Các yêu cầu & Capability L1/L2 cho Nền tảng tự động hóa TikTok và Phân tích Affiliate tích hợp. Dựa trên Thiết kế Hướng Năng lực (Capability Driven Design - CDD).

## 1. Tầm nhìn Sản phẩm & Mục tiêu Kinh doanh

**Tầm nhìn Sản phẩm:**
Xây dựng một nền tảng tự động hóa affiliate tích hợp AI có khả năng dự đoán nhu cầu tiêu dùng sắp tới dựa trên mùa, ngày lễ, sự kiện, thời tiết và xu hướng tìm kiếm, từ đó tự động đề xuất sản phẩm, tạo nội dung video, đăng tải lên TikTok và liên tục tối ưu hóa doanh thu thông qua machine learning.

**Mục tiêu Kinh doanh:**
Tạo ra một hệ thống affiliate tự học, end-to-end với khả năng:
1. **Dự đoán Nhu cầu:** Phát hiện các cơ hội mua sắm trong tương lai trước từ 7–30 ngày.
2. **Tìm kiếm Sản phẩm:** Đề xuất và đồng bộ các sản phẩm affiliate từ đa sàn TMĐT (Shopee, Lazada, Amazon...) có tỷ lệ chuyển đổi cao.
3. **Tự động hóa Nội dung:** Tự động tạo kịch bản, render video 9:16 và sản xuất nội dung cho đa nền tảng.
4. **Đăng tải Tự động:** Tự động tải lên và đăng video đa nền tảng mạng xã hội (TikTok, FB Reels, YT Shorts) thông qua API.
5. **Tối ưu hóa Liên tục:** Theo dõi hiệu suất (lượt xem, lượt click, chuyển đổi) và cải thiện các đề xuất.
6. **Khả năng Mở rộng:** Dễ dàng mở rộng từ một ngách (niche) duy nhất sang nhiều ngách khác nhau.

**Ý tưởng Cốt lõi:**
Hệ thống chuyển dịch từ cách tiếp cận "ưu tiên sản phẩm" (product-first) sang "ưu tiên ý định" (intent-first), tuân theo luồng sau:
`Sự kiện → Nhu cầu → Từ khóa → Đồng bộ Đa sàn → Kịch bản AI → Render Video → Đăng tải Đa nền tảng → Traffic → Chuyển đổi → Học hỏi`

**KPI Chính:**
- Doanh thu hoa hồng Affiliate.
- Lượt xem Video & Tỷ lệ nhấp (CTR).
- Tỷ lệ chuyển đổi (CVR) & Doanh thu trên 1000 lượt xem (RPM).
- Tỷ lệ thành công của việc đăng bài tự động hoàn toàn.

---

## 2. Tổng quan Mô-đun & Kiến trúc Hệ thống

Dựa trên cách tiếp cận CDD, hệ thống tích hợp "Phân tích Nhu cầu" với "Luồng Tự động hóa" trên nhiều nền tảng. Các capability thống nhất bao gồm:

| # | Tầng Capability | Capability | Viết tắt | Trách nhiệm |
|:-:|-----------------|------------|:----:|-------------|
| 1 | **Intelligence** | Event Intelligence Engine | `event-intel` | Nhận diện tín hiệu nhu cầu tương lai từ sự kiện, thời tiết. |
| 2 | **Intelligence** | Demand Prediction Engine | `demand-predict` | Chuyển đổi tín hiệu sự kiện thành nhu cầu mua sắm. |
| 3 | **Intelligence** | Keyword Intelligence Engine | `keyword-intel` | Tạo chủ đề tìm kiếm có ý định mua hàng cao. |
| 4 | **Sourcing** | E-commerce Sync | `ecommerce-sync` | Tìm kiếm, chấm điểm và đồng bộ sản phẩm từ đa sàn TMĐT (Shopee, Lazada...). |
| 5 | **Sourcing** | Affiliate Link Engine | `link-engine` | Tạo, quản lý và theo dõi affiliate links (UTM, tracking). |
| 6 | **Production** | Content Factory & Script Gen | `content-factory` | Lên kế hoạch nội dung và tạo kịch bản video bằng AI (LLM). |
| 7 | **Production** | Video Rendering Engine | `video-render` | Render video ngắn (9:16) từ hình ảnh, script, và TTS. |
| 8 | **Distribution** | Social Media Publishing | `social-publish` | Upload và publish video lên đa nền tảng (TikTok, FB Reels, Shorts) qua API. |
| 9 | **Optimization**| Analytics & Learning Engine | `analytics-learn` | Thu thập metrics (Social, Ecommerce), phân tích và tối ưu hóa. |
| 10| **Core** | Workflow Orchestration | `n8n-orchestrator`| Quản lý, lập lịch và xử lý lỗi các luồng tự động hóa. |
| 11| **Sourcing** | Collaboration Inbox | `collab-inbox` | Hằng ngày quét lời mời hợp tác (TikTok Shop Target Collaboration) từ nhãn hàng/cửa hàng, lấy thông tin sản phẩm, ghi Google Sheet, đẩy vào hàng đợi tạo video. |

---

## 3. Chi tiết Capability (Đặc tả L2)

### 3.1. Intelligence & Demand Layer (Tầng Phân tích & Nhu cầu)

**CAP-01: Event Intelligence (`event-intel`)**
* **Trách nhiệm:** Xác định các tín hiệu nhu cầu tương lai từ lịch và xu hướng.
* **Đầu ra:** Các Tín hiệu Sự kiện tương lai (VD: Mùa hè, Tựu trường, Siêu Sale).
* **Quy tắc:** Phát hiện trước 7-30 ngày.

**CAP-02: Demand & Keyword Prediction (`demand-keyword`)**
* **Trách nhiệm:** Chuyển đổi sự kiện thành nhu cầu khách hàng và các chủ đề tìm kiếm có ý định mua hàng cao.
* **Đầu ra:** Các Cơ hội Nhu cầu & Từ khóa Ý định Tìm kiếm.

### 3.2. Sourcing Layer (Tầng Nguồn Hàng)

**CAP-03: E-commerce Sync (`ecommerce-sync`)**
* **Trách nhiệm:** Đồng bộ sản phẩm từ các API Affiliate (Shopee, Lazada, Amazon...) qua `EcommerceAdapter`, đánh giá điểm ưu tiên (priority score) dựa trên nhu cầu và chỉ số.
* **Đầu ra:** Danh sách các bản ghi Sản phẩm đã được xếp hạng trong CSDL.
* **Quy tắc:** 
  - Upsert để tránh trùng lặp.
  - Điểm Ưu tiên = Nhu cầu Tìm kiếm + Tỷ lệ Hoa hồng + Tiềm năng Chuyển đổi.
  - Sản phẩm hết hàng > 14 ngày -> trạng thái `inactive`.

**CAP-04: Affiliate Link Engine (`link-engine`)**
* **Trách nhiệm:** Gắn và quản lý các link affiliate có khả năng theo dõi (tracking).
* **Đầu ra:** Các Link Affiliate có thể theo dõi.

**CAP-10: Collaboration Inbox (`collab-inbox`)** *(bổ sung 2026-10-15)*
* **Trách nhiệm:** Mỗi ngày (cron 08:00) kiểm tra tài khoản TikTok để phát hiện lời mời hợp tác mới từ nhãn hàng/cửa hàng (Target Collaboration, lời mời trong Inbox, đề nghị gửi mẫu).
* **Nguồn dữ liệu (theo thứ tự ưu tiên):**
  1. TikTok Shop Partner API — Affiliate Creator (`/affiliate_creator/.../target_collaborations/search`) nếu được cấp quyền.
  2. Tự động hóa trình duyệt (Playwright, session đăng nhập lưu sẵn) trên trang Affiliate Center web cho nhà sáng tạo.
  3. Bán tự động: operator dán link/ảnh lời mời vào Google Sheet hoặc Telegram bot.
* **Đầu ra:** Mỗi lời mời → 1 dòng Google Sheet (cửa hàng, sản phẩm, giá, % hoa hồng, hạn lời mời, mẫu miễn phí, link sản phẩm, ảnh, trạng thái) + bản ghi `Product` trong DB với `source_platform = tiktok_shop`.
* **Quy tắc:**
  - Chống trùng theo `(collab_id, product_id)`.
  - Lọc tự động: hoa hồng ≥ 10%, giá 100K–500K, đúng niche; còn lại để `cần duyệt`.
  - Việc **chấp nhận lời mời** và **gắn giỏ hàng (product anchor) khi đăng** do người duyệt thực hiện (API Content Posting không hỗ trợ gắn sản phẩm TikTok Shop).
  - Sản phẩm đạt lọc → tự động sinh script + render video → trạng thái `chờ duyệt` (SP-7).

### 3.3. Production Layer (Tầng Sản xuất)

**CAP-05: Content Factory & Script Gen (`content-factory`)**
* **Trách nhiệm:** Tạo kịch bản video (hook + body + CTA) từ dữ liệu sản phẩm sử dụng AI (Groq/Gemini/Claude).
* **Đầu ra:** File Script dạng JSON sẵn sàng cho việc render video.
* **Quy tắc:** Tối đa 60s, hook dưới 3s. Fallback LLM theo thứ bậc tối ưu chi phí.

**CAP-06: Video Rendering (`video-render`)**
* **Trách nhiệm:** Render video ngắn (1080x1920) tự động dựa trên script, voiceover TTS, và hình ảnh sản phẩm.
* **Đầu ra:** File `.mp4`.

### 3.4. Distribution Layer (Tầng Phân phối)

**CAP-07: Social Media Publishing (`social-publish`)**
* **Trách nhiệm:** Upload video lên đa nền tảng mạng xã hội (TikTok, FB Reels, YT Shorts) kèm caption, hashtag, và link sản phẩm qua `SocialPublishAdapter`.
* **Đầu ra:** ID Video đã đăng & Trạng thái tương ứng mỗi nền tảng.
* **Quy tắc:** Lên lịch đăng bài rải rác theo múi giờ vàng (Golden hours).

### 3.5. Analytics & Core Layer (Tầng Phân tích & Lõi)

**CAP-08: Analytics & Learning Engine (`analytics-learn`)**
* **Trách nhiệm:** Theo dõi lượt xem, click, chuyển đổi từ các nền tảng social và hoa hồng từ các sàn TMĐT.
* **Đầu ra:** Báo cáo hiệu suất, cảnh báo qua Telegram, và vòng lặp phản hồi (feedback loop) để AI tinh chỉnh Điểm Sản phẩm / Định dạng Nội dung.

**CAP-09: Workflow Orchestration (`n8n-orchestrator`)**
* **Trách nhiệm:** Lập lịch cho toàn bộ luồng (Đồng bộ -> AI -> Render -> Publish -> Analytics).
* **Đầu ra:** Nhật ký thực thi workflow, cơ chế thử lại (retry) khi có lỗi.

---

## 4. Giao diện & Bảng Điều khiển Người dùng (User Dashboard)

**Bảng tin Cơ hội & Hoạt động Hàng ngày:**
* **Sự kiện Sắp tới:** Tựu trường (còn 21 ngày).
* **Nhu cầu & Từ khóa Dự đoán:** "Góc học tập", "Bàn học thông minh".
* **Hành động của Hệ thống:**
  * Đã tìm kiếm 15 sản phẩm mới có hoa hồng cao.
  * Đã tạo 5 kịch bản & render 3 video.
  * Đã lên lịch 3 bài đăng TikTok cho hôm nay.
* **Hiệu suất:** 
  * Điểm Cơ hội Dự kiến: 85/100
  * Doanh thu Hôm qua: +500,000 VND.

---

## 5. Kiến trúc Kỹ thuật

* **Backend & API:** Node.js, PostgreSQL, Redis
* **Điều phối Workflow (Automation):** n8n
* **AI Agents:** Gemini API, Groq, Claude
* **Tạo Video:** Python/FFmpeg cục bộ + dịch vụ TTS
* **Triển khai (Deployment):** Docker, Self-hosted Windows Server

---

## 6. Tầm nhìn Dài hạn

Phát triển hệ thống từ một bot làm affiliate Shopee đơn kênh (TikTok) thành một **Hệ thống Phân tích Nhu cầu Đa kênh (Multi-channel Demand Intelligence System)**. Đích đến cuối cùng là khả năng dự đoán nhu cầu thị trường, sản xuất nội dung đa kênh (Shorts, Reels, TikTok, Blogs) và tối đa hóa doanh thu affiliate một cách mượt mà trên nhiều nền tảng khác nhau.
