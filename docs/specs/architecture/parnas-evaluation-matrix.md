# L3 — Parnas Evaluation Matrix (CRC × Cap S/N判定)

> **Mục đích**: Đánh giá xem mỗi CRC (biến động) cần thay đổi cấu trúc (S) hay chỉ cần config nội bộ (N) cho từng Cap.
> S合計 tối thiểu = boundary design tối ưu.
>
> **Legend**: **S** = Structural change (sửa code/interface), **N** = Config/internal (absorb bằng config/data)

---

## Matrix

| CRC \ Cap | shopee-sync | script-gen | video-render | tiktok-publish | analytics | n8n-orchestration | S count |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CRC-001** Thêm sản phẩm | N | N | N | N | N | N | **0** |
| **CRC-002** Xoá/ẩn sản phẩm | N | N | N | N | N | N | **0** |
| **CRC-003** Thay đổi thuộc tính SP | N | N | N | N | N | N | **0** |
| **CRC-004** Thay đổi hoa hồng | N | N | N | N | N | N | **0** |
| **CRC-005** Thêm nền tảng mới | **S** | N | N | **S** | **S** | **S** | **4** |
| **CRC-006** Xoá nền tảng | N | N | N | N | N | N | **0** |
| **CRC-007** Content strategy pivot | N | N | N | N | N | N | **0** |
| **CRC-008** API breaking changes | **S** | N | N | **S** | N | N | **2** |
| **CRC-009** Account change | N | N | N | N | N | N | **0** |
| **CRC-010** LLM provider change | N | **S** | N | N | N | N | **1** |
| **S total per Cap** | **2** | **1** | **0** | **2** | **1** | **1** | |

---

## Analysis

### S/N Reasoning

| CRC | Cap | S/N | Lý do |
|-----|-----|-----|-------|
| CRC-001~004 | All | N | Product CRUD, commission, priority thay đổi → chỉ data changes, pipeline xử lý tự động qua existing flow. Không cần sửa interface. |
| CRC-005 | shopee-sync | **S** | Cần thêm adapter class mới (SyncAdapter interface + PlatformX implementation). Structural change. |
| CRC-005 | tiktok-publish | **S** | Cần thêm PublishAdapter implementation mới. Structural. |
| CRC-005 | analytics | **S** | Cần thêm MetricFetcher implementation cho platform mới. |
| CRC-005 | n8n-orchestration | **S** | Cần thêm/sửa workflows cho platform mới (trigger, schedule mới). |
| CRC-005 | script-gen | N | Script generation logic không thay đổi — chỉ input source khác (product data format đã normalize ở sync layer). |
| CRC-005 | video-render | N | Video render không quan tâm product source. Input vẫn là Script + images. |
| CRC-006 | All | N | Disable = config change (`platform.enabled = false`). Adapter code giữ nguyên, chỉ skip. |
| CRC-007 | script-gen | N | Prompt templates externalized (YAML config). Swap template = config change. |
| CRC-007 | video-render | N | Visual style templates externalized. Config change. |
| CRC-008 | shopee-sync | **S** | API version upgrade có thể thay đổi request/response schema → sửa adapter code. |
| CRC-008 | tiktok-publish | **S** | Same — API contract change → sửa adapter code. |
| CRC-010 | script-gen | **S** | Thêm LLM adapter mới (interface mới nếu provider có behavior khác biệt lớn, VD: local Ollama). |

### Boundary Validation

| Observation | Assessment |
|---|---|
| **S total = 7** (across 10 CRCs × 6 Caps = 60 cells) | **Tốt** — 88% changes absorbed by config (N) |
| **video-render S = 0** | Perfect isolation — chỉ nhận input đã normalize, không phụ thuộc external platform |
| **CRC-001~004 (daily ops) all N** | Tốt — biến động thường xuyên nhất không cần sửa code |
| **CRC-005 S = 4** (highest) | Expected — thêm platform là biến đổi lớn nhất, nhưng adapter pattern giới hạn scope |
| **shopee-sync & tiktok-publish S = 2** | Boundary services (facing external APIs) chịu structural change nhiều nhất — đúng theo design intent |

### Kết luận

**Current Cap boundary đã tối ưu** vì:
1. S合計 = 7/60 (11.7%) — rất thấp
2. High-frequency changes (CRC-001~004) = 0 structural impact
3. Structural changes tập trung ở boundary adapters (designed for extension)
4. `video-render` hoàn toàn isolated (S=0) — đúng single responsibility

**Không cần re-split hoặc merge caps.**

---

## Adapter Interface Summary (Anti-S Design)

Để đảm bảo CRC-005/008/010 chỉ cần thêm adapter (không sửa core):

| Interface | Location | Implementations |
|-----------|----------|-----------------|
| `PlatformSyncAdapter` | shopee-sync | ShopeeAffiliate, [TikTokShop], [Lazada] |
| `PlatformPublishAdapter` | tiktok-publish | TikTokV2, [TikTokShop], [YouTube Shorts] |
| `LLMAdapter` | script-gen | Groq, Gemini, Claude, [Ollama] |
| `MetricFetchAdapter` | analytics | TikTokAnalytics, [ShopeeAnalytics] |

> `[brackets]` = planned/future adapters (CRC-005)
