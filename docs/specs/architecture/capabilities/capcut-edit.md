# Capability: capcut-edit

> **Mục đích**: Chuyển video sản phẩm thành **dự án nháp CapCut** để người vận hành chỉnh tay (hiệu ứng, chữ, nhịp),
> và cho Claude Desktop tạo video quảng cáo bằng lời qua MCP. Dùng giọng đọc có sẵn (Gemini hoặc edge-tts),
> không gọi thêm AI. Quyết định và lý do: `docs/decision-records/DR-0013-xuat-capcut-va-mcp.md`.

---

## Overview

| | |
|--|--|
| **Input** | Thư mục `storage/videos/<...>/` của video **sản phẩm** (có `product.json`, `script.json`, `audio_N.mp3`, ảnh); hoặc spec JSON / thông tin sản phẩm qua MCP |
| **Output** | Dự án CapCut trong thư mục draft của CapCut (Mac: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`); `capcut.json` trong thư mục video |
| **Giọng** | Giữ nguyên giọng của video (C-0013-1). Qua MCP: edge-tts, nữ cho nấu ăn / làm đẹp / thời trang, nam cho trà / điện tử |
| **Cost** | $0 (không Groq, không Gemini khi xuất) |

## Thành phần

| Phần | Vị trí | Việc |
|------|--------|------|
| Xuất | `capcut_export.py` | `build_spec(dir)` đọc file trong thư mục video, `export_folder(dir)` gọi `capcut_mcp` rồi ghi `capcut.json`. Thoát mã 4 (thư mục chưa sẵn sàng) / 9 (CapCut hoặc capcut-mcp lỗi) |
| CLI | `demo.py --capcut DIR` | Xuất một thư mục; `--voice edge|gemini` chọn giọng khi tạo mới |
| Tự xuất | `demo.py auto_export_capcut` | Sau khi dựng xong (giọng đã chốt), nếu `CAPCUT_AUTO_EXPORT` ≠ 0 và đã cài capcut-mcp. Lỗi chỉ cảnh báo, không làm hỏng video |
| Studio | `POST /api/studio/videos/{folder}/capcut` | Nút "Xuất sang CapCut" (cần `X-Studio: 1`, một job một lúc) |
| MCP | `tools/capcut-mcp/` | Tạo draft + MP4; `looks.py` chọn hiệu ứng theo danh mục và loại cảnh; `voice.py` edge-tts theo cảnh; công cụ `affiliate_*` |

## Hiệu ứng theo bối cảnh (`looks.py`)

Danh mục sản phẩm → bộ look (`food`, `beauty`, `fashion`, `tea`, `tech`, `home`). Mỗi look có mặc định và chỉnh theo loại cảnh
(`hook`, `point`, `price`, `story`, `cta`): chuyển động ảnh, chuyển cảnh, animation vào của ảnh, filter, hiệu ứng cảnh,
animation chữ. Giá trị đã đặt trong spec luôn thắng look. Tên hiệu ứng lấy từ pycapcut; tên lạ trong look bị bỏ qua, tên lạ do người đặt báo lỗi.

## Khung dự án CapCut 9.8 (`skeleton_v9`)

CapCut 9.x trên Mac chỉ liệt kê dự án có `draft_info.json` và thư mục `Timelines/`. capcut-mcp ghép nội dung vào một dự án trống do CapCut 9.8
lưu. Khung này **không nằm trong git** (repo công khai). Tìm theo thứ tự: `CAPCUT_SKELETON_DIR`, `~/.capcut-mcp/skeleton_v9`, thư mục gói.
`CAPCUT_LEGACY_LAYOUT=1` bỏ bước này (CapCut cũ, kiểm thử).

## MCP + Tt Affiliate

Đặt `TT_AFFILIATE_DIR` trong cấu hình MCP. Công cụ: `affiliate_list_videos`, `affiliate_export_to_capcut(folder)`, `affiliate_fetch_product(url)`.
Chỉ đụng thư mục con trực tiếp của `storage/videos` (C-0013-3).

## Ràng buộc

C-0013-1, C-0013-2, C-0013-3 (xem DR-0013).
