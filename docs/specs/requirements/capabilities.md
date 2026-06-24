# L2 Capabilities — TikTok Affiliate Automation

> **SSoT**: Full L2 capability specifications. 責務/境界/データ/出すもの/ルール/設定/品質/CRC Trace.
> Architecture detail (components, interfaces) → [L3](../architecture/capabilities/)

---

## Capability一覧

| # | Capability | 略称 | 責務 |
|:-:|-----------|:----:|------|
| 1 | Shopee Product Sync | shopee-sync | Đồng bộ sản phẩm từ Shopee Affiliate, phân loại, đánh priority |
| 2 | AI Script Generation | script-gen | Tạo kịch bản video từ product data bằng AI |
| 3 | Video Rendering | video-render | Render short video 9:16 từ images + TTS voiceover |
| 4 | TikTok Publishing | tiktok-publish | Upload + publish video lên TikTok via API v2 |
| 5 | Performance Analytics | analytics | Thu thập metrics, tạo report, gửi alert |
| 6 | N8N Orchestration | n8n-orchestration | Quản lý, schedule, error-recover các workflow |

---

## 5-Axis Overview

| Capability | Input | Output | Trigger | SLA | Cost |
|-----------|-------|--------|---------|-----|------|
| shopee-sync | Shopee API response | Product records in DB | Weekly schedule (N8N) | < 5 min/sync | $0 |
| script-gen | Product data JSON | Script JSON (hook, body, cta) | On-demand from pipeline | < 30s/script | $0 (Groq free) |
| video-render | Script + product images | .mp4 file (1080×1920) | Celery task queue | < 5 min/video | $0 (local) |
| tiktok-publish | Video file + metadata | Published video ID | Scheduled posting slots | < 2 min/upload | $0 |
| analytics | TikTok API metrics | Report JSON + Telegram msg | Daily cron (N8N) | < 1 min | $0 |
| n8n-orchestration | Trigger events | Workflow execution logs | Schedule + webhook + error | Always-on | $0 |

---

## CAP-01: shopee-sync

### 責務 (Responsibility)
Đồng bộ sản phẩm từ Shopee Affiliate API, duy trì product catalog cập nhật, phân loại và đánh giá priority score.

### 境界 (Boundary)
- **Owns**: Product entity lifecycle (create, update, deactivate)
- **Does NOT own**: Script/video generation decisions (thuộc pipeline)
- **Interface IN**: Shopee API (PlatformSyncAdapter)
- **Interface OUT**: Product records available for script-gen

### データ (Data)

**Aggregate: Product**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| shopee_item_id | VARCHAR(50) | UNIQUE, NOT NULL |
| name | VARCHAR(500) | NOT NULL |
| price | INTEGER (VND) | NOT NULL |
| commission_rate | DECIMAL(5,2) | NOT NULL, ≥ 0 |
| category | VARCHAR(100) | NOT NULL |
| image_urls | JSONB | array of URLs |
| affiliate_link | VARCHAR(1000) | NOT NULL |
| status | ENUM | active / inactive / out_of_stock |
| priority_score | DECIMAL(5,4) | 0.0000 – 1.0000 |
| last_synced_at | TIMESTAMP | NOT NULL |

**Lifecycle**: `active` → `out_of_stock` (reversible) → `inactive` (soft delete)

### 出すもの (Output)
- Product records in DB (queryable by other caps)
- Telegram notification: sync summary (new/updated/deactivated count)

### ルール (Rules)
1. Sync lặp lại không tạo duplicate (upsert by shopee_item_id)
2. Product hết hàng 14 ngày liên tục → status = `inactive`
3. Priority score = weighted(commission_rate × 0.4, sales_rank × 0.3, discount × 0.2, newness × 0.1)
4. Affiliate link re-generate nếu > 7 ngày

### 設定 (Configuration)
- `SYNC_SCHEDULE`: cron expression (default: weekly Monday 08:00)
- `PRIORITY_WEIGHTS`: JSON object for scoring formula
- `DEACTIVATE_DAYS`: days before deactivation (default: 14)

### 品質 (Quality)
- Sync < 5 min for up to 500 products
- Zero data loss: upsert, never delete
- Recovery: retry 3x with exponential backoff on API failure

### CRC Trace
- CRC-001: Thêm sản phẩm → Product created automatically
- CRC-002: Dừng sản phẩm → status = inactive
- CRC-003: Commission change → detected on sync, re-score
- CRC-004: Thêm platform → PlatformSyncAdapter interface

---

## CAP-02: script-gen

### 責務
Tạo kịch bản video ngắn (hook + body + CTA) từ product data sử dụng LLM, đảm bảo đa dạng và phù hợp content type.

### 境界
- **Owns**: Script entity, Prompt template entity
- **Does NOT own**: Product data (read-only from shopee-sync)
- **Interface IN**: Product data from DB, PromptTemplate
- **Interface OUT**: Script records for video-render

### データ

**Aggregate: Script**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| product_id | UUID | FK → products |
| content_type | ENUM | product_review / lifestyle_tip / comparison / trending |
| hook | VARCHAR(200) | NOT NULL |
| body | TEXT | NOT NULL |
| cta | VARCHAR(200) | NOT NULL |
| estimated_duration_sec | INTEGER | NOT NULL |
| llm_provider | VARCHAR(20) | groq / gemini / claude |
| status | ENUM | draft / approved / rejected / used |

**Lifecycle**: `draft` → `approved` (auto or manual) → `used` (linked to video_job)

**Aggregate: PromptTemplate**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| name | VARCHAR(100) | UNIQUE |
| content_type | VARCHAR(50) | NOT NULL |
| system_prompt | TEXT | NOT NULL |
| user_prompt_template | TEXT | NOT NULL (Jinja2) |
| version | INTEGER | auto-increment |

### 出すもの
- Script JSON cho video-render pipeline
- Fallback: nếu primary LLM fail → switch to secondary

### ルール
1. Mỗi product tối đa 3 scripts active (để A/B test style)
2. Script hook ≤ 3 giây khi đọc (ước tính ~50 ký tự)
3. Script tổng ≤ 60 giây (TikTok short-form optimal)
4. Không dùng từ ngữ vi phạm policy TikTok (gambling, medical claims)
5. LLM provider fallback: groq → gemini → claude (cost escalation)

### 設定
- `LLM_PRIMARY`: default provider (groq)
- `LLM_FALLBACK_CHAIN`: ordered list of fallbacks
- `MAX_SCRIPTS_PER_PRODUCT`: 3
- `MAX_DURATION_SEC`: 60
- `CONTENT_TYPE_ROTATION`: strategy for varying content types

### 品質
- Generation < 30s per script
- Diversity: no 2 scripts cho cùng product có hook giống nhau > 80%
- Cost tracking: log cost per generation

### CRC Trace
- CRC-006: Content pivot → change PromptTemplate, new content_type
- CRC-009: LLM provider change → swap LLMAdapter, update config

---

## CAP-03: video-render

### 責務
Render video ngắn 9:16 (1080×1920) từ script + product images + TTS voiceover. Output file .mp4 sẵn sàng publish.

### 境界
- **Owns**: VideoJob entity, rendering pipeline (FFmpeg + TTS)
- **Does NOT own**: Script content (read-only), product images (downloaded)
- **Interface IN**: Script record, product image URLs
- **Interface OUT**: .mp4 file path for tiktok-publish

### データ

**Aggregate: VideoJob**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| script_id | UUID | FK → scripts |
| product_id | UUID | FK → products |
| status | ENUM | queued / rendering / done / failed |
| output_path | VARCHAR(500) | path to .mp4 |
| duration_sec | DECIMAL(5,1) | actual video length |
| tts_provider | VARCHAR(20) | edge-tts / openai |
| render_time_sec | DECIMAL(6,1) | processing time |
| retry_count | INTEGER | max 3 |

**Lifecycle**: `queued` → `rendering` → `done` | `failed` (retry ≤ 3 → DLQ)

### 出すもの
- .mp4 file in `storage/videos/{date}/{job_id}.mp4`
- Thumbnail extracted from first frame

### ルール
1. Resolution: 1080×1920 (9:16), H.264, AAC audio
2. TTS voice: vi-VN-HoaiMyNeural (edge-tts default)
3. Background music volume ≤ 20% of voiceover
4. Max retry 3 lần, sau đó → Dead Letter Queue
5. Temp files cleanup sau khi render xong
6. Output file ≤ 50MB (TikTok limit)

### 設定
- `TTS_PROVIDER`: edge-tts (default)
- `TTS_VOICE`: vi-VN-HoaiMyNeural
- `MUSIC_VOLUME_RATIO`: 0.2
- `MAX_RETRIES`: 3
- `VIDEO_RETENTION_DAYS`: 30

### 品質
- Render < 5 min per video
- Audio sync: voiceover aligned with visual transitions
- Celery concurrency: 2 parallel renders (limited by CPU)

### CRC Trace
- CRC-006: Style change → render config per content_type
- CRC-010: Scale → increase Celery concurrency

---

## CAP-04: tiktok-publish

### 責務
Upload video lên TikTok, quản lý OAuth tokens, schedule posting times, handle publish errors.

### 境界
- **Owns**: PublishJob entity, TikTok auth tokens
- **Does NOT own**: Video file (from video-render), posting content (from script)
- **Interface IN**: VideoJob (done) + Script metadata
- **Interface OUT**: Published video ID, share URL

### データ

**Aggregate: PublishJob**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| video_job_id | UUID | FK → video_jobs |
| tiktok_post_id | VARCHAR(100) | nullable until published |
| title | VARCHAR(150) | NOT NULL |
| hashtags | JSONB | array of strings |
| scheduled_at | TIMESTAMP | optional |
| published_at | TIMESTAMP | set on success |
| status | ENUM | pending / uploading / published / failed / rejected |

**Lifecycle**: `pending` → `uploading` → `published` | `failed` (retry) | `rejected` (TikTok policy)

**Aggregate: TikTokAuth**

| Field | Type | Constraint |
|-------|------|-----------|
| account_id | VARCHAR(100) | PK |
| access_token | TEXT | encrypted |
| refresh_token | TEXT | encrypted |
| expires_at | TIMESTAMP | NOT NULL |

### 出すもの
- Published video on TikTok
- Telegram notification: publish success/failure

### ルール
1. Posting schedule: optimal times (11:00, 15:00, 19:00, 21:00 ICT)
2. Max 3 videos/day per account (avoid spam detection)
3. Token auto-refresh 1h before expiry
4. If rejected by TikTok → flag, don't retry same content
5. Hashtag limit: ≤ 5 per video

### 設定
- `POSTING_SLOTS`: list of optimal times
- `MAX_POSTS_PER_DAY`: 3
- `TOKEN_REFRESH_BUFFER_HOURS`: 1

### 品質
- Upload < 2 min per video
- Token refresh: zero-downtime (pre-emptive)
- Error recovery: retry 2x, then DLQ

### CRC Trace
- CRC-007: API change → update PlatformPublishAdapter implementation
- CRC-008: Account change → new tiktok_auth record, config switch

---

## CAP-05: analytics

### 責務
Thu thập performance metrics từ TikTok, aggregate, tạo reports, gửi alerts. Feed data cho priority scoring.

### 境界
- **Owns**: VideoMetric entity, DailyReport entity
- **Does NOT own**: Video content, publish decisions
- **Interface IN**: TikTok Creator API (metrics), publish_jobs (video mapping)
- **Interface OUT**: Reports (Telegram), dashboard data, priority feedback to shopee-sync

### データ

**Aggregate: VideoMetric**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| publish_job_id | UUID | FK → publish_jobs |
| product_id | UUID | FK → products |
| date | DATE | NOT NULL |
| views | INTEGER | ≥ 0 |
| likes | INTEGER | ≥ 0 |
| clicks | INTEGER | ≥ 0 |
| conversions | INTEGER | ≥ 0 |
| revenue_vnd | INTEGER | ≥ 0 |
| UNIQUE | | (publish_job_id, date) |

**Lifecycle**: Created daily, immutable after creation (append-only)

**Aggregate: DailyReport**

| Field | Type | Constraint |
|-------|------|-----------|
| date | DATE | PK, UNIQUE |
| total_videos_published | INTEGER | |
| total_views | INTEGER | |
| total_revenue_vnd | INTEGER | |
| pipeline_health | ENUM | healthy / degraded / down |

### 出すもの
- Daily Telegram report (views, revenue, top video, health)
- Weekly summary for manual review
- Priority feedback: high-performing product categories → boost priority_score

### ルール
1. Metrics fetched daily at 06:00 (previous day data settled)
2. Revenue attribution: conversions × product commission
3. Top video = highest views in last 7 days
4. Pipeline health: healthy (all jobs OK) / degraded (DLQ > 0) / down (backend unreachable)

### 設定
- `METRICS_FETCH_TIME`: 06:00 daily
- `REPORT_SEND_TIME`: 07:00 daily
- `RETENTION_DAYS_RAW`: 90
- `TOP_VIDEO_WINDOW_DAYS`: 7

### 品質
- Report delivered by 07:00 daily
- Metrics accuracy: match TikTok dashboard ±5%
- No duplicate metrics per video per day

### CRC Trace
- CRC-003: Commission change → revenue calculation updated
- CRC-008: Account change → metrics per account_id

---

## CAP-06: n8n-orchestration

### 責務
Central orchestrator: schedule workflows, trigger cap sequences, handle errors, manage DLQ, health monitoring.

### 境界
- **Owns**: Workflow execution, scheduling, DLQ, error recovery
- **Does NOT own**: Business logic of individual caps
- **Interface IN**: Cron triggers, webhook events, error signals
- **Interface OUT**: Cap triggers (HTTP calls to backend API)

### データ

**Aggregate: WorkflowRun**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| workflow_name | VARCHAR(100) | NOT NULL |
| trigger_type | ENUM | cron / event / manual |
| status | ENUM | running / success / partial_fail / failed |
| caps_executed | JSONB | array of cap names |

**Aggregate: DeadLetterQueue**

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | PK |
| source_cap | VARCHAR(50) | NOT NULL |
| job_id | UUID | NOT NULL |
| error_message | TEXT | NOT NULL |
| attempts | INTEGER | NOT NULL |
| resolved_at | TIMESTAMP | nullable |

### Workflows

| ID | Name | Schedule | Caps triggered |
|----|------|----------|---------------|
| W1 | daily-pipeline | Cron 09:00 | script-gen → video-render → tiktok-publish |
| W2 | weekly-sync | Cron Mon 08:00 | shopee-sync |
| W3 | daily-analytics | Cron 06:00 | analytics |
| W4 | post-scheduler | Cron at posting slots | tiktok-publish |
| W5 | error-recovery | Every 30 min | DLQ check + retry |

### ルール
1. Pipeline sequential: sync → script → render → publish (dependency chain)
2. If any cap fails → log to DLQ, continue next items
3. DLQ auto-retry: 3 attempts, exponential backoff (5m, 30m, 2h)
4. After 3 failed retries → Telegram alert, manual intervention required
5. Health check: ping all services every 30 min

### 設定
- `PIPELINE_SCHEDULE`: 09:00 daily
- `DLQ_MAX_RETRIES`: 3
- `DLQ_BACKOFF_MINUTES`: [5, 30, 120]
- `HEALTH_CHECK_INTERVAL_MIN`: 30

### 品質
- Workflow execution visible in N8N UI
- All runs logged to workflow_runs table
- Alert latency < 5 min for critical failures

### CRC Trace
- CRC-004/005: Platform add/remove → workflow config change
- CRC-007: API change → error spike triggers DLQ
- CRC-010: Scale → adjust scheduling, add parallel paths

---

## Dependency Map

```
┌─────────────────────────────────────────────────────┐
│                 n8n-orchestration                     │
│            (triggers & schedules all)                 │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
       ▼          │          │          │
┌────────────┐    │          │          │
│ shopee-sync│    │          │          │
└─────┬──────┘    │          │          │
      │ product   │          │          │
      │ data      │          │          │
      ▼           │          │          │
┌────────────┐    │          │          │
│ script-gen │◄───┘          │          │
└─────┬──────┘               │          │
      │ script                │          │
      │ JSON                  │          │
      ▼                       │          │
┌──────────────┐              │          │
│ video-render │◄─────────────┘          │
└─────┬────────┘                         │
      │ .mp4 file                        │
      ▼                                  │
┌───────────────┐                        │
│ tiktok-publish│                        │
└─────┬─────────┘                        │
      │ video_id                         │
      ▼                                  │
┌────────────┐                           │
│ analytics  │◄──────────────────────────┘
└────────────┘
```

---

## BPM参照

- [Daily Pipeline](bpm/daily-pipeline.d2) — 日次動画生成パイプライン
- [Weekly Sync](bpm/weekly-sync.d2) — 週次商品同期フロー
