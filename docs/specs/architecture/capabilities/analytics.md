# Capability: analytics

> **Mục đích**: Thu thập và phân tích performance data từ TikTok, báo cáo
> định kỳ để tối ưu hóa content strategy.

---

## Overview

| | |
|--|--|
| **Input** | TikTok video IDs, Shopee affiliate click data |
| **Output** | Performance report (Telegram), Dashboard stats, DB metrics |
| **Schedule** | Daily 10:00 PM + weekly Sunday báo cáo |
| **Cost** | $0 (TikTok Analytics API miễn phí) |

---

## Workflow — Daily Sync

```
[N8N Trigger: 10:00 PM daily]
        ↓
1. Fetch video stats từ TikTok API:
   - views, likes, comments, shares
   - Cho tất cả video đã publish trong 30 ngày gần nhất
        ↓
2. Update DB: video_jobs.views, likes, comments, shares
        ↓
3. Tính engagement rate:
   ER = (likes + comments + shares) / views × 100
        ↓
4. Identify top performers:
   - Video có views > average × 1.5
   - Video có ER > 5%
        ↓
5. Gửi daily digest (Telegram):
   "📊 Hôm nay: X views tổng | Best: [tên video] (Yk views)"
```

## Workflow — Weekly Report

```
[N8N Trigger: Sunday 9:00 PM]
        ↓
1. Aggregate 7-day data:
   - Total views, total likes, total shares
   - New followers (nếu API cho phép)
   - Affiliate clicks (từ bio link tracker)
        ↓
2. Top 3 videos tuần này
3. Category performance (sản phẩm loại nào hiệu quả)
4. Gợi ý content tuần tới (dựa trên data)
        ↓
5. Gửi weekly report (Telegram + lưu vào DB)
```

---

## Metrics Tracked

| Metric | Source | Tần suất cập nhật |
|--------|--------|------------------|
| Views | TikTok API | Daily |
| Likes | TikTok API | Daily |
| Comments | TikTok API | Daily |
| Shares | TikTok API | Daily |
| Engagement Rate | Calculated | Daily |
| Affiliate Clicks | Bio link tracker | Realtime |
| Estimated Revenue | Shopee dashboard | Manual weekly |

---

## Telegram Notifications

```
Daily digest format:
📊 [Ngày] TikTok Daily
├─ Views hôm nay: {today_views:,}
├─ Likes: {today_likes} | Shares: {today_shares}
├─ Best video: "{hook}" — {views:,} views
└─ Affiliate clicks: {clicks}

Weekly report format:
📈 Weekly Report [{week}]
├─ Total views: {total_views:,} ({week_growth:+.0f}%)
├─ New followers: +{new_followers}
├─ Best video: "{hook}" — {views:,} views
├─ Best category: {category}
└─ Est. affiliate revenue: ~{revenue:,}₫
```

---

## A/B Testing Framework

Khi có đủ data (> 20 videos), enable A/B testing:

```
Hook styles:
  A: Câu hỏi ("Bạn có biết...")
  B: Fact gây shock ("X% người Việt không biết...")
  C: Promise ("Chỉ 30k mà đẹp như hàng triệu")

Track: views và ER theo hook style
Kết luận sau: 30 videos/style
```

---

## Cost Notes

- TikTok Analytics API: **miễn phí**
- Telegram Bot API: **miễn phí**
- Storage cho metrics: ~100 bytes/video/ngày → 100 videos × 30 ngày = ~300KB

---

## Dependencies

- `tiktok-publish` → video IDs
- Telegram Bot (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- PostgreSQL → đọc và ghi video_jobs table

---

## Files

```
backend/app/services/analytics/
├── tiktok_analytics.py   ← fetch video stats
├── report_generator.py   ← tạo báo cáo
└── telegram_notifier.py  ← gửi Telegram
```
