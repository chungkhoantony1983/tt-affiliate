# Capability: ecommerce-sync

> **Trạng thái (2026-11-05)**: Adapter Shopee **tạm dừng**, ưu tiên TikTok Shop. Code được giữ lại nhưng tắt bằng `SHOPEE_ENABLED=false`.

> **Mục đích**: Sync danh sách sản phẩm từ các nền tảng Affiliate (Shopee, Lazada, Amazon...) vào database local thông qua `EcommerceAdapter`.
> Generate và cache affiliate tracking links.

---

## Overview

| | |
|--|--|
| **Input** | Platform credentials, affiliate unique IDs |
| **Output** | Danh sách products trong PostgreSQL DB |
| **Schedule** | Hàng tuần (Monday 8:00 AM) + on-demand |
| **Cost** | $0 (API miễn phí cho affiliates) |

---

## Workflow

```
[Trigger: N8N schedule hoặc manual]
        ↓
1. Iterate over enabled Platforms (Shopee, Lazada):
   a. Load `EcommerceAdapter` tương ứng.
   b. Fetch product list từ Affiliate API.
   c. Lấy tất cả sản phẩm, handle pagination.
        ↓
2. Cho mỗi sản phẩm:
   a. Upsert vào bảng products theo `(source_platform, source_item_id)`
   b. Cập nhật: name, price, images, stock, rating, sales_count
   c. Generate/refresh affiliate link qua Adapter nếu > 7 ngày
        ↓
3. Đánh dấu sản phẩm đã hết hàng → is_active = False
        ↓
4. Identify "hot products":
   - Giảm giá > 20% → flag as priority
   - Sales count top 20% → flag as priority
        ↓
5. Gửi notification (Telegram):
   "Sync hoàn thành: +N sản phẩm mới, M sản phẩm cập nhật từ [Platform]"
        ↓
[Output: DB updated → script-gen có thể dùng product data]
```

---

## Affiliate Link Generation

`EcommerceAdapter` abstract class yêu cầu method `generate_affiliate_link`.

```python
class EcommerceAdapter(ABC):
    @abstractmethod
    def fetch_products(self) -> List[ProductData]:
        pass

    @abstractmethod
    def generate_affiliate_link(self, item_id: str, unique_id: str) -> str:
        pass
```

Mỗi platform sẽ tự implement logic tạo tracking link của riêng mình. Ví dụ Shopee có param `affiliateId`, Lazada có param `sub_aff_id`.

---

## Database Schema (Product)

```sql
products:
  id                  SERIAL PRIMARY KEY
  source_platform     VARCHAR(50)  ← 'shopee', 'lazada', 'amazon'
  source_item_id      VARCHAR(100)
  name                VARCHAR(500)
  description         TEXT
  price               FLOAT
  original_price      FLOAT
  discount_percent    FLOAT
  category            VARCHAR(200)
  image_urls          TEXT (JSON array)
  affiliate_link      TEXT
  source_url          TEXT
  stock               INT
  sales_count         INT
  rating              FLOAT
  is_active           BOOLEAN
  is_priority         BOOLEAN    ← hot products
  last_synced         TIMESTAMP
  video_count         INT        ← số video đã tạo
  UNIQUE(source_platform, source_item_id)
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
| API rate limit | Quá nhiều request | Retry sau 60s (per Adapter) |
| Image URL 404 | Nền tảng xóa ảnh | Skip, dùng ảnh khác |
| Product deactivated | Shop ngừng bán | Set `is_active = False` |
| Affiliate link invalid | Link hết hạn | Re-generate thông qua Adapter |

---

## API Setup (Credentials)

Hệ thống quản lý biến môi trường động cho nhiều nền tảng:
- **Shopee**: `SHOPEE_APP_ID`, `SHOPEE_SECRET_KEY`, `SHOPEE_AFFILIATE_ID`
- **Lazada**: `LAZADA_APP_KEY`, `LAZADA_APP_SECRET`, `LAZADA_AFFILIATE_ID`
(Được config qua n8n và truyền vào backend adapter).

---

## Files

```
backend/app/services/ecommerce/
├── sync_orchestrator.py  ← Orchestrate multi-platform sync
├── product_ranker.py     ← Prioritization logic
└── adapters/
    ├── base.py           ← EcommerceAdapter ABC
    ├── shopee.py         ← Shopee implementation
    └── lazada.py         ← Lazada implementation
```
