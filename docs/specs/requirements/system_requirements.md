# System Requirements — Affiliate Intelligence & Automation Platform

> **SSoT**: L1/L2 Requirements & Capabilities for the integrated Affiliate Intelligence and TikTok Automation Platform. Based on Capability Driven Design (CDD).

## 1. Product Vision & Business Goal

**Product Vision:**
Build an AI-powered affiliate automation platform that predicts upcoming consumer demand based on seasons, holidays, events, weather, and search trends, then automatically recommends products from multiple e-commerce platforms, generates video content, publishes to various social channels (TikTok, Reels, Shorts), and continuously optimizes revenue through machine learning.

**Business Goal:**
Create a self-learning, end-to-end affiliate system capable of:
1. **Demand Prediction:** Detecting future buying opportunities 7–30 days in advance.
2. **Product Sourcing:** Recommending and syncing high-conversion affiliate products from multiple e-commerce platforms (Shopee, Lazada, Amazon, etc.).
3. **Content Automation:** Automatically generating scripts, rendering 9:16 videos, and producing multi-platform content.
4. **Autonomous Publishing:** Uploading and publishing videos to social media automatically via API.
5. **Continuous Optimization:** Tracking performance (views, clicks, conversions) and improving recommendations.
6. **Scalability:** Scaling from a single niche to multiple niches effortlessly.

**Core Concept:**
The system shifts from "product-first" to "intent-first", following this flow:
`Event → Demand → Keyword → Marketplace Sync → AI Script → Video Render → Social Publish → Traffic → Conversion → Learning`

**Primary KPI:**
- Affiliate commission revenue.
- Video Views & Click-through rate (CTR).
- Conversion rate (CVR) & Revenue per 1000 views.
- Fully automated publishing success rate.

---

## 2. System Architecture & Modules Overview

Based on the CDD approach, the system integrates the "Demand Intelligence" with the "Automation Pipeline" across multiple platforms. The unified capabilities are:

| # | Capability Layer | Capability | 略称 (Abbr) | 責務 (Responsibility) |
|:-:|------------------|------------|:----:|------|
| 1 | **Intelligence** | Event Intelligence Engine | `event-intel` | Nhận diện tín hiệu nhu cầu tương lai từ sự kiện, thời tiết. |
| 2 | **Intelligence** | Demand Prediction Engine | `demand-predict` | Chuyển đổi tín hiệu sự kiện thành nhu cầu mua sắm. |
| 3 | **Intelligence** | Keyword Intelligence Engine | `keyword-intel` | Tạo chủ đề tìm kiếm có ý định mua hàng cao. |
| 4 | **Sourcing** | E-commerce Sync | `ecommerce-sync` | Tìm kiếm, chấm điểm và đồng bộ sản phẩm từ nhiều sàn TMĐT (Shopee, Lazada...). |
| 5 | **Sourcing** | Affiliate Link Engine | `link-engine` | Tạo, quản lý và theo dõi affiliate links (UTM, tracking). |
| 6 | **Production** | Content Factory & Script Gen | `content-factory` | Lên kế hoạch nội dung và tạo kịch bản video bằng AI (LLM). |
| 7 | **Production** | Video Rendering Engine | `video-render` | Render video ngắn (9:16) từ hình ảnh, script, và TTS. |
| 8 | **Distribution** | Social Media Publishing | `social-publish` | Upload và publish video lên đa nền tảng (TikTok, Shorts, Reels) qua API. |
| 9 | **Optimization**| Analytics & Learning Engine | `analytics-learn` | Thu thập metrics (Social, Ecommerce), phân tích và tối ưu hóa. |
| 10| **Core** | Workflow Orchestration | `n8n-orchestrator`| Quản lý, lập lịch và xử lý lỗi các luồng tự động hóa. |
| 11| **Sourcing** | Collaboration Inbox | `collab-inbox` | Daily scan of brand/shop collaboration invitations (TikTok Shop Target Collaboration), extract product info, write to Google Sheet, enqueue video creation. |

---

## 3. Capability Details (L2 Specifications)

### 3.1. Intelligence & Demand Layer

**CAP-01: Event Intelligence (`event-intel`)**
* **責務:** Identify future demand signals from calendars and trends.
* **出すもの:** Future Event Signals (e.g., Summer, Back to School, Mega Sale).
* **ルール:** Phát hiện trước 7-30 ngày.

**CAP-02: Demand & Keyword Prediction (`demand-keyword`)**
* **責務:** Convert events into customer needs and high-intent search topics.
* **出すもの:** Demand Opportunities & Search Intent keywords.

### 3.2. Sourcing Layer

**CAP-03: E-commerce Sync (`ecommerce-sync`)**
* **責務:** Đồng bộ sản phẩm từ đa sàn TMĐT (Shopee, Lazada, Amazon...) qua `EcommerceAdapter`, đánh giá priority score dựa trên demand và metrics.
* **出すもの:** Ranked Product records in DB.
* **ルール:** 
  - Upsert để tránh duplicate.
  - Priority Score = Search Demand + Commission Rate + Conversion Potential.
  - Sản phẩm hết hàng > 14 ngày -> `inactive`.

**CAP-04: Affiliate Link Engine (`link-engine`)**
* **責務:** Attach and manage affiliate links with tracking capabilities.
* **出すもの:** Trackable Affiliate Links.

**CAP-10: Collaboration Inbox (`collab-inbox`)** *(added 2026-10-15)*
* **責務:** Daily (08:00 cron) check the TikTok account for new collaboration invitations from brands/shops (Target Collaboration, Inbox invites, free-sample offers).
* **Sources (priority order):** (1) TikTok Shop Partner API — Affiliate Creator `target_collaborations/search` if access granted; (2) Playwright browser automation on the creator Affiliate Center web with a saved login session; (3) Semi-manual: operator pastes invite link/screenshot into Google Sheet or Telegram bot.
* **出すもの:** One Google Sheet row per invitation (shop, product, price, commission %, expiry, free sample, product URL, images, status) + `Product` record with `source_platform = tiktok_shop`.
* **ルール:**
  - Dedupe by `(collab_id, product_id)`.
  - Auto-filter: commission ≥ 10%, price 100K–500K, in-niche; otherwise `needs_review`.
  - **Accepting the invite** and **attaching the product anchor when posting** are done by a human (Content Posting API cannot attach TikTok Shop products).
  - Passing products → auto script + render → `pending_approval` (SP-7).

### 3.3. Production Layer

**CAP-05: Content Factory & Script Gen (`content-factory`)**
* **責務:** Tạo kịch bản video (hook + body + CTA) từ product data sử dụng AI (Groq/Gemini/Claude).
* **出すもの:** Script JSON sẵn sàng cho video rendering.
* **ルール:** Tối đa 60s, hook dưới 3s. Fallback LLM theo thứ bậc tối ưu chi phí.

**CAP-06: Video Rendering (`video-render`)**
* **責務:** Render video ngắn (1080x1920) tự động dựa trên script, voiceover TTS, và hình ảnh sản phẩm.
* **出すもの:** File `.mp4`.

### 3.4. Distribution Layer

**CAP-07: Social Media Publishing (`social-publish`)**
* **責務:** Upload video lên đa nền tảng mạng xã hội kèm caption, hashtag, và link sản phẩm qua `SocialPublishAdapter` (TikTok API, YouTube API, Graph API).
* **出すもの:** Published Video ID & Status per platform.
* **ルール:** Lên lịch đăng bài rải rác theo múi giờ vàng (Golden hours).

### 3.5. Analytics & Core Layer

**CAP-08: Analytics & Learning Engine (`analytics-learn`)**
* **責務:** Theo dõi view, click, conversion từ các nền tảng social và hoa hồng từ các sàn TMĐT.
* **出すもの:** Báo cáo hiệu suất, cảnh báo qua Telegram, và feedback loop để AI tinh chỉnh Product Score / Content Format.

**CAP-09: Workflow Orchestration (`n8n-orchestrator`)**
* **責務:** Schedule pipeline (Sync -> AI -> Render -> Publish -> Analytics).
* **出すもの:** Workflow execution logs, retry mechanisms.

---

## 4. User Dashboard & Interface

**Daily Opportunity & Operation Feed:**
* **Upcoming Events:** Back To School (21 days left).
* **Predicted Demand & Keywords:** "Study Setup", "Bàn học thông minh".
* **System Actions:**
  * Sourced 15 new high-commission products.
  * Generated 5 scripts & rendered 3 videos.
  * Scheduled 3 TikTok posts for today.
* **Performance:** 
  * Expected Opportunity Score: 85/100
  * Yesterday's Revenue: +500,000 VND.

---

## 5. Technical Architecture

* **Backend & API:** Node.js, PostgreSQL, Redis
* **Automation Workflow:** n8n (Orchestrator)
* **AI Agents:** Gemini API, Groq, Claude
* **Video Generation:** Local Python/FFmpeg + TTS services
* **Deployment:** Docker, Self-hosted Windows Server

---

## 6. Long-Term Vision

Evolve the system from a single-channel (TikTok) Shopee affiliate bot into a **Multi-channel Demand Intelligence System**. Ultimately capable of predicting market demand, producing omni-channel content (Shorts, Reels, TikTok, Blogs), and maximizing affiliate revenue seamlessly across diverse platforms.
