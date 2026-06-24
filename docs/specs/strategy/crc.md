# CRC — Change Request Catalog

> **SSoT**: L1→L2 bridge. Mỗi entry = 1 business change scenario cần thiết kế đáp ứng.
> Status: `open` → `designed` → `implemented` → `verified`

---

## CRC一覧 (Active)

| ID | 変更シナリオ | Source | Priority | Status |
|----|------------|--------|----------|--------|
| CRC-001 | Thêm sản phẩm affiliate mới | Business | P0 | open |
| CRC-002 | Xoá/dừng sản phẩm khỏi pipeline | Business | P0 | open |
| CRC-003 | Thay đổi commission rate từ Shopee | External | P1 | open |
| CRC-004 | Thêm platform mới (Lazada/Sendo) | Strategy | P2 | open |
| CRC-005 | Dừng platform hiện tại | Strategy | P2 | open |
| CRC-006 | Chuyển đổi niche/content style | Business | P1 | open |
| CRC-007 | API breaking change (TikTok/Shopee) | External | P0 | open |
| CRC-008 | Thay đổi TikTok account | Ops | P1 | open |
| CRC-009 | Thay đổi LLM provider | Ops | P2 | open |
| CRC-010 | Tăng throughput (>20 videos/day) | Scaling | P3 | open |

---

## Impact Matrix

| CRC | shopee-sync | script-gen | video-render | tiktok-publish | analytics | n8n-orch |
|-----|:-----------:|:----------:|:------------:|:--------------:|:---------:|:--------:|
| CRC-001 | ●● | ● | ● | ● | ○ | ● |
| CRC-002 | ●● | ○ | ○ | ○ | ○ | ● |
| CRC-003 | ●● | ● | ○ | ○ | ●● | ○ |
| CRC-004 | ●● | ● | ○ | ○ | ● | ●● |
| CRC-005 | ●● | ○ | ○ | ○ | ● | ●● |
| CRC-006 | ● | ●● | ●● | ● | ● | ○ |
| CRC-007 | ●● | ○ | ○ | ●● | ● | ● |
| CRC-008 | ○ | ○ | ○ | ●● | ●● | ● |
| CRC-009 | ○ | ●● | ○ | ○ | ○ | ● |
| CRC-010 | ● | ● | ●● | ●● | ● | ●● |

> Legend: ●● = Major change (interface/data model), ● = Minor change (config/logic), ○ = No impact

---

## CRC Details

### CRC-001: Thêm sản phẩm affiliate mới

- **Trigger**: Shopee store có sản phẩm mới, hoặc thêm sản phẩm thủ công
- **Impact**: Product record inserted → tự động vào pipeline generation
- **Design response**: shopee-sync upsert, priority scoring tự đánh, pipeline tự pick
- **Acceptance**: Sản phẩm mới xuất hiện trong DB, được generate script trong vòng 24h

### CRC-002: Xoá/dừng sản phẩm khỏi pipeline

- **Trigger**: Sản phẩm hết hàng, shop dừng bán, commission quá thấp
- **Impact**: Product status → `inactive`, không generate thêm video
- **Design response**: Soft delete (status field), cascade stop pending jobs
- **Acceptance**: Không video mới cho sản phẩm inactive, video cũ vẫn live

### CRC-003: Thay đổi commission rate từ Shopee

- **Trigger**: Shopee/shop thay đổi commission%, detected khi sync
- **Impact**: Priority score cần recalculate, có thể ảnh hưởng ranking
- **Design response**: shopee-sync detect change → update rate → re-rank priority
- **Acceptance**: Priority score reflect commission mới trong 1 sync cycle

### CRC-004: Thêm platform mới (Lazada/Sendo)

- **Trigger**: Quyết định mở rộng sang marketplace khác
- **Impact**: Cần thêm PlatformSyncAdapter, schema product cần support multi-source
- **Design response**: Adapter pattern (PlatformSyncAdapter IF), product.source field
- **Acceptance**: Platform mới sync được mà không sửa pipeline core

### CRC-005: Dừng platform hiện tại

- **Trigger**: Commission giảm, platform không còn hiệu quả
- **Impact**: Disable adapter, deactivate all products từ platform đó
- **Design response**: Adapter enable/disable flag, bulk deactivate by source
- **Acceptance**: Pipeline chạy bình thường với platform còn lại

### CRC-006: Chuyển đổi niche/content style

- **Trigger**: Pivot sang niche mới (tech → beauty), hoặc thay đổi video style
- **Impact**: Prompt templates thay đổi, video render settings có thể khác
- **Design response**: Template versioning, content_type as parameter, render config per niche
- **Acceptance**: Video mới reflect style mới, cũ vẫn intact

### CRC-007: API breaking change (TikTok/Shopee)

- **Trigger**: Platform ra API version mới, deprecate endpoint
- **Impact**: Adapter implementation cần update, có thể downtime
- **Design response**: Adapter interface stable, chỉ thay implementation. DLQ catch failures
- **Acceptance**: Pipeline recover trong < 24h sau khi fix adapter

### CRC-008: Thay đổi TikTok account

- **Trigger**: Account bị ban, muốn chạy multi-account
- **Impact**: OAuth tokens thay đổi, analytics history tách account
- **Design response**: tiktok_auth table per account, publish_jobs link to account_id
- **Acceptance**: Switch account không mất data cũ

### CRC-009: Thay đổi LLM provider

- **Trigger**: Provider tăng giá, chất lượng giảm, provider mới tốt hơn
- **Impact**: LLMAdapter implementation swap
- **Design response**: LLMAdapter interface + provider config in .env
- **Acceptance**: Swap provider chỉ cần đổi config, không sửa business logic

### CRC-010: Tăng throughput (>20 videos/day)

- **Trigger**: Revenue tốt, muốn scale
- **Impact**: Celery concurrency, DB connections, storage, posting schedule
- **Design response**: Worker scaling (concurrency param), connection pooling, storage cleanup
- **Acceptance**: Pipeline handle target throughput without degradation

---

## Governance Rules

1. **P0 CRCs** phải có design response trước khi code
2. Mỗi CRC khi implement xong → verify với acceptance criteria → status = `verified`
3. CRC mới từ external (API change) được tạo khi phát hiện, priority auto = P0
4. Review CRC list mỗi tháng, archive CRCs đã verified > 30 ngày
