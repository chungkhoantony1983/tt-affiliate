# Capability: shopee-sync

> **Mục đích**: Sync danh sách sản phẩm từ Shopee Affiliate store vào database local.
> Generate và cache affiliate tracking links.

---

## Overview

| | |
|--|--|
| **Input** | Shopee store ID, affiliate unique ID |
| **Output** | Danh sách products trong PostgreSQL DB |
| **Schedule** | Hàng tuần (Monday 8:00 AM) + on-demand |
| **Cost** | $0 (Shopee API miễn phí cho affiliates) |

---

## Workflow

```
[Trigger: N8N schedule hoặc manual]
        ↓
1. Fetch product list từ Shopee Affiliate API:
   GET /api/v2/product/get_item_base_info
   - Lấy tất cả sản phẩm trong store
   - Page size: 100 / request
        ↓
2. Cho mỗi sản phẩm:
   a. Upsert vào bảng products
   b. Cập nhật: name, price, images, stock, rating, sales_count
   c. Generate/refresh affiliate link nếu > 7 ngày
        ↓
3. Đánh dấu sản phẩm đã hết hàng → is_active = False
        ↓
4. Identify "hot products":
   - Giảm giá > 20% → flag as priority
   - Sales count top 20% → flag as priority
        ↓
5. Gửi notification (Telegram):
   "Sync hoàn thành: +N sản phẩm mới, M sản phẩm cập nhật"
        ↓
[Output: DB updated → script-gen có thể dùng product data]
```

---

## Affiliate Link Generation

```python
# Shopee affiliate link format
BASE_URL = "https://shope.ee/affiliate"

def generate_affiliate_link(item_id: str, unique_id: str) -> str:
    """
    Tạo tracking link cho affiliate commission.
    unique_id: Shopee affiliate unique ID của bạn
    """
    params = {
        "itemId": item_id,
        "affiliateId": unique_id,
        "source": "tiktok"
    }
    return f"{BASE_URL}?{urlencode(params)}"
```

**Lưu ý**: Affiliate link của Shopee không có TTL cố định, nhưng nên re-generate
định kỳ 7 ngày hoặc khi giá thay đổi.

---

## Database Schema (Product)

```sql
products:
  id                  SERIAL PRIMARY KEY
  shopee_item_id      VARCHAR(100) UNIQUE
  name                VARCHAR(500)
  description         TEXT
  price               FLOAT
  original_price      FLOAT
  discount_percent    FLOAT
  category            VARCHAR(200)
  image_urls          TEXT (JSON array)
  affiliate_link      TEXT
  shopee_url          TEXT
  stock               INT
  sales_count         INT
  rating              FLOAT
  is_active           BOOLEAN
  is_priority         BOOLEAN    ← hot products
  last_synced         TIMESTAMP
  video_count         INT        ← số video đã tạo
```

---

## Product Prioritization

Sản phẩm được ưu tiên tạo video theo:
1. `is_priority = True` (hot, high discount)
2. `video_count = 0` (chưa có video nào)
3. `sales_count DESC` (bán chạy nhất)
4. `discount_percent DESC` (giảm nhiều nhất)

---

## Error Handling

| Lỗi | Nguyên nhân | Xử lý |
|-----|-------------|-------|
| API rate limit | Quá nhiều request | Retry sau 60s |
| Image URL 404 | Shopee xóa ảnh | Skip, dùng ảnh khác |
| Product deactivated | Shop ngừng bán | Set `is_active = False` |
| Affiliate link invalid | Link hết hạn | Re-generate |

---

## Shopee API Setup

1. Đăng ký tại **Shopee Affiliate Program** (shopee.vn/affiliate)
2. Lấy `affiliate_unique_id` từ dashboard
3. Đăng ký **Shopee Open Platform** để dùng Product API
4. Credentials cần thiết:
   - `SHOPEE_APP_ID`
   - `SHOPEE_SECRET_KEY`
   - `SHOPEE_AFFILIATE_UNIQUE_ID`

---

## Cost Notes

- Shopee API: **miễn phí** cho affiliates
- Database storage: ~1KB/product → 1000 sản phẩm = ~1MB

---

## Files

```
backend/app/services/shopee/
├── shopee_service.py     ← API calls
├── affiliate_links.py    ← link generation
└── product_ranker.py     ← prioritization logic
```
