# Capability: tiktok-publish

> **Mục đích**: Upload video đã render lên TikTok và publish với caption/hashtags.
> Sử dụng TikTok Content Posting API v2.

---

## Overview

| | |
|--|--|
| **Input** | `video_path` (MP4), `caption`, `hashtags[]`, `scheduled_time` (optional) |
| **Output** | `publish_id`, `tiktok_video_id`, `share_url` |
| **Rate limit** | 20 posts/day (TikTok API limit) |
| **Cost** | $0 (TikTok API miễn phí cho creators) |

---

## Workflow

```
[Input: rendered video + caption]
        ↓
1. Validate video file:
   - Format: MP4
   - Size: < 500MB
   - Duration: 15-60s
   - Resolution: 1080x1920
        ↓
2. Check/refresh access token:
   - Token TTL = 24h
   - Auto-refresh nếu gần hết hạn
        ↓
3. Initialize upload session:
   POST /v2/post/publish/inbox/video/init/
   → nhận publish_id + upload_url
        ↓
4. Upload video chunk:
   PUT {upload_url}
   Content-Type: video/mp4
        ↓
5. Check publish status (polling):
   GET /v2/post/publish/status/fetch/
   → chờ đến khi status = PUBLISHED_BUT_BANNED hoặc SUCCESS
        ↓
6. Update database: tiktok_video_id, share_url, publish_time
        ↓
[Output: published video → analytics tracking]
```

---

## API Endpoints

```
Base: https://open.tiktokapis.com/v2

POST /post/publish/inbox/video/init/    ← init upload
PUT  {upload_url}                       ← upload file
POST /post/publish/status/fetch/        ← check status
GET  /video/query/                      ← get video stats
POST /oauth/token/refresh/              ← refresh token
```

---

## Access Token Management

```python
# Token lifecycle
ACCESS_TOKEN_TTL = 86400        # 24 hours
REFRESH_TOKEN_TTL = 86400 * 30  # 30 days

# Auto-refresh logic
if time_until_expiry < 3600:    # < 1 hour remaining
    refresh_access_token()
```

**Lưu ý bảo mật**:
- `access_token` và `refresh_token` lưu trong database (encrypted)
- Không lưu trong code hoặc `.env`
- Rotate refresh_token khi dùng

---

## Caption Format

```
{caption_text}

{hashtags formatted as #tag1 #tag2 ...}
Link sản phẩm: 🔗 Link trong bio

⚠️ Max 2200 ký tự tổng
⚠️ Max 30 hashtags
```

---

## Error Handling

| Lỗi | HTTP Code | Xử lý |
|-----|-----------|-------|
| Token expired | 401 | Auto-refresh token, retry |
| Upload timeout | 408/504 | Retry với exponential backoff (3 lần) |
| Content policy violation | 400 | Log, flag video để review manual |
| Daily limit exceeded | 429 | Queue sang ngày hôm sau |
| File too large | 400 | Transcode lại với bitrate thấp hơn |

---

## Prerequisites

1. **TikTok Developer Account**: [developers.tiktok.com](https://developers.tiktok.com)
2. **App được approve** với scopes:
   - `video.upload` — upload video
   - `video.list` — đọc video list
3. **Content Posting API** được enable cho app
4. **OAuth flow** hoàn thành để lấy access_token

---

## Cost Notes

- TikTok API: **miễn phí** cho content creators
- Không có charge per upload hay per API call
- Giới hạn: 20 posts/day (đủ cho strategy 1-2 video/ngày)

---

## Dependencies

- `video-render` → cung cấp video file đã render
- TikTok app credentials (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`)
- Access token (lưu trong DB, không trong env)

---

## Files

```
backend/app/services/tiktok/
├── tiktok_service.py    ← upload, publish, status
├── token_manager.py     ← auth, refresh
└── content_policy.py    ← validate trước khi upload
```
