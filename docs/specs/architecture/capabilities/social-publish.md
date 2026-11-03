# Capability: social-publish

> **Mục đích**: Upload video đã render lên các nền tảng mạng xã hội (TikTok, YT Shorts, FB Reels) và publish với caption/hashtags thông qua `SocialPublishAdapter`.

---

## Overview

| | |
|--|--|
| **Input** | `video_path` (MP4), `caption`, `hashtags[]`, `scheduled_time`, `target_platforms[]` |
| **Output** | `publish_id`, `platform_video_id`, `share_url` per platform |
| **Rate limit** | Tuân thủ rate limit của từng nền tảng (VD: 20 posts/day cho TikTok API) |
| **Cost** | $0 (Platform APIs thường miễn phí cho creators) |

---

## Workflow

```
[Input: rendered video + caption + platforms]
        ↓
1. Validate video file:
   - Format: MP4
   - Resolution: 1080x1920
   - Optimize cho multi-platform nếu cần (VD: độ dài, bitrate)
        ↓
2. Lặp qua các nền tảng đích (target_platforms):
   a. Load `SocialPublishAdapter` tương ứng (TikTok, YouTube, FB)
   b. Check/refresh access token của nền tảng
   c. Khởi tạo upload session / metadata
   d. Upload video chunk/file
   e. Polling publish status
        ↓
3. Update database: platform_video_id, share_url, publish_time
        ↓
[Output: published video → analytics tracking]
```

---

## Publishing Adapter

Hệ thống cung cấp một interface chung để public video lên đa nền tảng.

```python
class SocialPublishAdapter(ABC):
    @abstractmethod
    def validate_video(self, video_path: str) -> bool:
        pass

    @abstractmethod
    def refresh_token(self) -> None:
        pass

    @abstractmethod
    def publish_video(self, video_path: str, caption: str, hashtags: List[str]) -> PublishResult:
        pass
```

---

## Access Token Management

Mỗi adapter tự quản lý access token lifecycle của mình (vd. `ACCESS_TOKEN_TTL = 86400` cho TikTok).

**Lưu ý bảo mật**:
- `access_token` và `refresh_token` lưu trong database (encrypted) theo từng platform_account
- Không lưu trong code hoặc `.env`
- Rotate refresh_token tự động khi dùng

---

## Error Handling

| Lỗi | Xử lý |
|-----|-------|
| Token expired | Auto-refresh token, retry |
| Upload timeout | Retry với exponential backoff (3 lần) |
| Content policy violation | Log error, flag video để review manual |
| Daily limit exceeded | Queue sang ngày hôm sau |
| File size/format rejected | Transcode lại với profile phù hợp của nền tảng |

---

## Prerequisites

1. **Developer Accounts**: TikTok Developers, Google Cloud Console (cho YouTube Data API), Meta Developers (cho Graph API).
2. **App Approvals**: Yêu cầu xin quyền upload video/shorts/reels.
3. **OAuth Flow**: Thực hiện xác thực người dùng để lưu tokens vào database.

---

## Files

```
backend/app/services/social/
├── publish_orchestrator.py ← Orchestrate multi-platform publish
├── schedule_manager.py     ← Lên lịch giờ vàng
├── auth_manager.py         ← Quản lý Tokens
└── adapters/
    ├── base.py             ← SocialPublishAdapter ABC
    ├── tiktok_v2.py        ← TikTok impl
    ├── youtube_shorts.py   ← YouTube Shorts impl
    └── fb_reels.py         ← Facebook Reels impl
```
