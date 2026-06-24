# Capability: n8n-orchestration

> **Mục đích**: Quản lý và vận hành các N8N automation workflows.
> N8N chạy self-hosted trên desktop nhà, kết nối tất cả capabilities.

---

## Overview

| | |
|--|--|
| **Infrastructure** | N8N self-hosted, Docker, trên desktop nhà |
| **URL** | `http://localhost:5678` |
| **Cost** | $0 (self-hosted, điện nhà) |
| **Requirements** | Desktop phải bật 24/7 |

---

## Workflows Hiện Có

### WF-01: Daily Product Video

```yaml
name: daily-product-video
trigger: Cron — 9:00 AM (Asia/Ho_Chi_Minh)
steps:
  1. GET /api/products/pending-video?limit=2
  2. IF no products → Telegram "Không có sản phẩm mới"
  3. FOR each product:
     a. POST /api/videos/create {product_id, content_type: "product_showcase"}
     b. WAIT 5 phút
     c. GET /api/videos/{job_id}/status (poll mỗi 2 phút, max 5 lần)
     d. IF status == "rendered" → POST /api/videos/{job_id}/upload
     e. Telegram notify kết quả
```

### WF-02: Lifestyle Content (2x/tuần)

```yaml
name: lifestyle-content
trigger: Cron — Thứ 3 và Thứ 6, 2:00 PM
steps:
  1. GET /api/topics/suggest (AI gợi ý topic dựa trên trending)
  2. POST /api/videos/create {topic, content_type: "lifestyle"}
  3. [same render + upload flow as WF-01]
```

### WF-03: Daily Analytics Sync

```yaml
name: daily-analytics
trigger: Cron — 10:00 PM daily
steps:
  1. POST /api/analytics/sync-tiktok
  2. GET /api/analytics/daily-summary
  3. Telegram gửi daily digest
```

### WF-04: Weekly Product Sync

```yaml
name: weekly-shopee-sync
trigger: Cron — Thứ 2, 8:00 AM
steps:
  1. POST /api/shopee/sync
  2. GET /api/products/new-count
  3. Telegram gửi sync report
```

### WF-05: Weekly Report

```yaml
name: weekly-report
trigger: Cron — Chủ nhật, 9:00 PM
steps:
  1. GET /api/analytics/weekly-summary
  2. Telegram gửi weekly report (views, best video, revenue)
```

---

## N8N Setup Guide

### 1. Cài đặt Docker

```bash
cd docker/
cp ../.env.example ../.env
# Điền API keys vào .env
docker-compose up -d n8n postgres redis
```

### 2. Truy cập N8N

```
URL: http://localhost:5678
User: admin (N8N_USER từ .env)
Pass: [N8N_PASSWORD từ .env]
```

### 3. Import Workflows

```bash
# Workflows JSON ở: n8n/workflows/*.json
# Import qua N8N UI: Settings → Import workflow
```

### 4. Config Credentials trong N8N

| Service | Type | Cần điền |
|---------|------|----------|
| Backend API | HTTP Header Auth | API base URL |
| Telegram | Telegram API | Bot token + chat ID |

---

## API Endpoints (Backend → N8N gọi)

```
GET  /api/products/pending-video     ← sản phẩm chưa có video
POST /api/videos/create              ← tạo video job
GET  /api/videos/{id}/status         ← check job status
POST /api/videos/{id}/upload         ← upload lên TikTok
POST /api/shopee/sync                ← trigger sync
POST /api/analytics/sync-tiktok      ← sync TikTok stats
GET  /api/analytics/daily-summary    ← daily stats
GET  /api/analytics/weekly-summary   ← weekly report
```

---

## Monitoring & Alerting

### Khi nào N8N alert qua Telegram:

- ✅ Video đã publish thành công
- ❌ Video render fail (kèm error message)
- ❌ Upload fail (kèm lý do)
- ⚠️ Daily video không được tạo (không có sản phẩm pending)
- ✅ Weekly sync hoàn thành (+N sản phẩm)
- 📊 Daily/weekly performance digest

### N8N Error Handling

```
Mỗi workflow node có:
- On Error: Continue (không dừng toàn workflow)
- Retry: 2 lần với delay 30s
- Final fail → Telegram error notification
```

---

## Desktop Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| RAM | 8GB+ | Docker + N8N + Celery + Postgres |
| CPU | 4+ cores | Video rendering (FFmpeg) |
| Storage | 50GB+ free | Videos, Docker images |
| Network | Ổn định, upload > 5Mbps | TikTok video upload |
| UPS | Khuyến nghị | Tránh mất điện dừng job |

---

## Cost Notes

- N8N self-hosted: **$0** (mã nguồn mở)
- Docker Desktop (Mac/Windows): **$0** (personal use)
- Điện: ~50-100W × 24h × 30 ngày ≈ 36-72 kWh ≈ **50,000-100,000₫/tháng**

---

## Files

```
n8n/workflows/
├── daily_product_video.json
├── lifestyle_content.json
├── daily_analytics.json
├── weekly_shopee_sync.json
└── weekly_report.json

docker/
└── docker-compose.yml
```
