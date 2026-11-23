# DR-0013: Xuất video sang CapCut (Studio + MCP) kèm giọng đọc edge-tts

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã duyệt (2026-11-23, kèm trả lời Q-1…Q-4 ở § 11; Q-1, Q-3, Q-4 đổi so với đề xuất) | 2026-11-23 | Claude (BA) | chungkhoantony1983 (2026-11-23) |

Capability: `capcut-edit` (mới), `video-render`, `script-gen` · Nhánh: `feat/issue-36-capcut-export` · GitHub issue: #36 · Cấp: **M** (Dev + Reviewer + Tester + Tech Lead vì chạm API Studio và subprocess; MKTG xem chữ trên nút Studio)

> Số DR: quét mọi ref local/remote ngày 2026-11-23, số lớn nhất là DR-0012.

---

## 1. Bối cảnh

**Yêu cầu người dùng (2026-11-23)**:

1. Tích hợp `capcut-mcp` vào Tt Affiliate, "làm cả hai": nút xuất CapCut trên Studio **và** Claude điều khiển qua MCP.
2. Video CapCut làm bằng `capcut-mcp` hiện có ảnh, chữ nhưng **không có tiếng**. Người dùng hỏi có cần đưa vào Tt Affiliate và dùng edge-tts không.
3. Mục tiêu chung: bớt phụ thuộc Gemini (TTS 10 lượt/ngày, 4 lượt/video sản phẩm, nguồn: `agent/CLAUDE.md`).

**Hiện trạng**:

| Chỗ | Hiện trạng | Hệ quả |
|-----|-----------|--------|
| `demo.py run_one` | Groq viết kịch bản → `generate_voiceovers` (Gemini mặc định, hết quota → edge-tts) → `render_video` FFmpeg + Pillow | Chỉ ra `video.mp4` đã "đóng"; muốn chỉnh chữ/nhịp phải sửa trên Studio rồi dựng lại |
| Thư mục video | `script.json` (segments: `kind`, `line`, `text`, `duration`), `product.json`, `audio_N.mp3`, `anh_sp_N.*`, `canh_N.png` | Đủ dữ liệu để dựng lại thành dự án CapCut mà **không gọi lại AI** |
| `capcut-mcp` (ngoài repo, trên Mac ở `~/Documents/project/capcut-mcp`) | Tạo draft CapCut bằng `pycapcut==0.0.4` + MP4 dự phòng bằng FFmpeg; spec chỉ có 1 file `voiceover` cho cả video; đã có bản sửa định dạng draft cho CapCut 9.8 (chỉ nằm trên máy người dùng) | Không có giọng theo từng cảnh, không tự đọc giọng; code không có git nên khó đồng bộ giữa các bản |
| Studio (`api/studio.py`) | Chạy `demo.py` bằng subprocess, một job một lúc, API ghi cần `X-Studio: 1` (C-0001-2, C-0001-3) | Nút mới phải theo đúng khuôn này |

**Chi phí**: edge-tts $0, không giới hạn công bố (nguồn: `FEASIBILITY.md`). pycapcut, FFmpeg $0. Groq như hiện tại. Gemini: 0 lượt khi chọn edge-tts.

---

## 2. Quyết định

> **Thêm capability mới `capcut-edit`. Thêm `capcut_export.py` biến một thư mục video có sẵn thành dự án nháp CapCut (ảnh, chữ, giá, CTA, giọng đọc từng cảnh, đúng thời lượng từng câu), gọi bằng `demo.py --capcut DIR`, nút "Xuất sang CapCut" trên Studio, và **tự chạy sau khi có giọng đọc** khi tạo video (Q-3). Hiệu ứng hình (chuyển cảnh, chuyển động ảnh, animation chữ, filter, hiệu ứng cảnh) **chọn theo bối cảnh**: theo danh mục sản phẩm và loại cảnh (hook / điểm nổi bật / giá / CTA), không chỉ ảnh tĩnh (Q-1). Thêm lựa chọn giọng `edge` khi tạo video để không tốn Gemini. `capcut-mcp` được đưa vào repo (`tools/capcut-mcp/`), có giọng đọc theo cảnh (edge-tts) và thêm công cụ MCP gọi lại các phần trên.**

---

## 3. Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|:---:|------|
| A | Chỉ nút Studio | | Không điều khiển bằng lời trong Claude được |
| B | Chỉ MCP, Claude tự viết kịch bản | | Bỏ qua cổng duyệt Studio, không dùng lại video đã làm |
| C | Cả hai, MCP gọi lại chung `capcut_export` | ⭐ | Người dùng chọn (2026-11-23). Một chỗ code, hai cách dùng |
| D | Dùng giọng đọc có sẵn trong CapCut (Text to speech) | | pycapcut không tạo được giọng CapCut; người dùng phải bấm tay từng câu |

---

## 4. Thay đổi cấu trúc

### 4.1 Dữ liệu / file

| Thứ | Trước | Sau | Lý do |
|-----|-------|-----|------|
| `capcut-mcp` | Thư mục rời trên Mac | `tools/capcut-mcp/` trong repo (lấy bản đang có trên Mac, gồm bản sửa CapCut 9.8). Cài vào `.venv` bằng `pip install -e tools/capcut-mcp` | Có git, một bản duy nhất; MCP trên Mac trỏ vào đây (xem Q-1) |
| Spec của capcut-mcp | `voiceover` 1 file cho cả video | Thêm `scenes[].audio` (file) và `scenes[].narration` (câu đọc). Có `audio` thì cảnh dài bằng audio + `GAP`; có `narration` mà không có `audio` thì đọc bằng edge-tts | Khớp nhịp từng câu như `render_video` |
| Thư mục video | — | Thêm `capcut.json`: `{draft_name, draft_path, exported_at}` | Studio biết video đã xuất, hiện tên dự án |
| `.env.example` | — | `CAPCUT_DRAFTS_FOLDER=` (trống = tự dò), `CAPCUT_AUTO_EXPORT=1` | Mac có nhiều đường dẫn draft; tắt tự xuất khi cần |
| Bảng hiệu ứng theo bối cảnh | — | `tools/capcut-mcp/capcut_mcp/looks.py`: nhóm danh mục (đồ ăn, làm đẹp, thời trang, trà, điện tử, gia dụng, mặc định) × loại cảnh → chuyển cảnh, chuyển động ảnh, animation vào của ảnh, animation chữ, filter, hiệu ứng cảnh. Chỉ dùng tên có trong pycapcut; MCP nhận thêm `look` / hiệu ứng từng cảnh để Claude tự chọn | Q-1 |
| `choose_persona` | điện tử, máy móc, ô tô, thể thao → nam; còn lại → nữ | Thêm **trà** vào nhóm nam; nấu ăn, làm đẹp, thời trang → nữ (đã đúng mặc định). edge-tts: nữ = `vi-VN-HoaiMyNeural`, nam = `vi-VN-NamMinhNeural` | Q-4 |

### 4.2 Luồng

```
Studio "Xuất sang CapCut" ─┐
demo.py --capcut DIR ──────┼─▶ capcut_export.export_folder(DIR)
MCP affiliate_export ──────┘      đọc script.json + product.json + audio_N + ảnh
                                  → spec (hook trên cùng, chữ cảnh, giá, CTA "BẤM GIỎ HÀNG VÀNG BÊN DƯỚI",
                                    dòng "Video có gắn link tiếp thị liên kết")
                                  → capcut_mcp.build_capcut_draft → capcut.json

Tạo video mới (Studio / --create-json / CLI) + chọn giọng "Miễn phí (edge-tts)"
  → generate_voiceovers(provider="edge")  → như cũ → có thể bấm Xuất sang CapCut

Claude Desktop (MCP):
  affiliate_fetch_product(link TikTok)   → product_sources.fetch_tiktok_product (ảnh, giá, mô tả)
  Claude viết hook + câu đọc từng cảnh   → create_product_video(..., narration từng cảnh, voice="edge")
  hoặc affiliate_list_videos / affiliate_export_to_capcut(thư mục) cho video đã duyệt trên Studio
```

---

## 5. Kế hoạch công việc

| # | Việc | Vai trò | Output | Vị trí |
|---|------|---------|--------|--------|
| 1 | Đưa capcut-mcp vào repo (lấy bản trên Mac, có bản sửa CapCut 9.8), thêm `scenes[].audio`, `narration`, edge-tts, `looks.py` hiệu ứng theo bối cảnh, `scene_effect` từng cảnh | Dev | Nhóm 1 | `tools/capcut-mcp/` |
| 1b | Spec capability `docs/specs/architecture/capabilities/capcut-edit.md` | BA | Tài liệu | docs |
| 2 | `capcut_export.py` + `demo.py --capcut DIR` | Dev | Nhóm 2 | root |
| 3 | Chọn giọng khi tạo: `--voice edge|gemini` (CLI, mặc định giữ như hiện tại = Gemini), trường `voice` trong create-json, ô chọn trên màn hình Tạo video; thêm "trà" vào nhóm giọng nam; tự xuất CapCut sau khi dựng nếu `CAPCUT_AUTO_EXPORT=1` và cài capcut-mcp (lỗi xuất không làm hỏng video, chỉ ghi cảnh báo) | Dev | Nhóm 2 | `demo.py`, `studio.html`, `api/studio.py` |
| 4 | `POST /videos/{folder}/capcut` (subprocess, một job một lúc, `X-Studio: 1`) + nút trên trang video + hiện `capcut.json` | Dev | Nhóm 3 | `api/studio.py`, `studio.html` |
| 5 | Công cụ MCP `affiliate_list_videos`, `affiliate_export_to_capcut`, `affiliate_fetch_product` (đọc `TT_AFFILIATE_DIR`) | Dev | Nhóm 1 | `tools/capcut-mcp/` |
| 6 | Soát diff, bảo mật (đường dẫn thư mục không thoát khỏi `storage/videos`) | Reviewer + Tech Lead | Báo cáo | — |
| 7 | Test theo § 9 trên bản sao, edge-tts | Tester | Báo cáo | thư mục tạm |
| 8 | Chữ trên nút, thông báo lỗi | MKTG | Góp ý | — |
| 9 | Cập nhật `video-render.md`, hướng dẫn vận hành, `TODO.md`, `agent/CLAUDE.md` | BA | Tài liệu | docs |

Nhóm 1 và 2 không sửa chung file, làm song song được; nhóm 3 sau nhóm 2.

---

## 6. Rủi ro và giả định

| Mã | Nội dung | Xử lý |
|----|----------|-------|
| R-1 | CapCut đổi định dạng draft (đã gặp ở 9.8) | Vẫn có `video.mp4` FFmpeg như cũ; lỗi CapCut không làm hỏng thư mục video |
| R-2 | Không kiểm được CapCut thật trên cloud | Tester kiểm JSON draft; người dùng mở thử trên Mac (E2E-3) |
| R-3 | CapCut đang mở không thấy dự án mới | Thông báo "Thoát hẳn CapCut rồi mở lại" |
| R-4 | edge-tts cần mạng, có lúc lỗi | Lỗi thì dừng, không tạo draft thiếu tiếng (exit 3, như đọc lại giọng) |
| A-1 | Người dùng có quyền dùng ảnh sản phẩm từ trang TikTok Shop cho affiliate | Như pipeline hiện tại |

---

## 7. Ràng buộc mới

- **C-0013-1**: Xuất CapCut **không gọi AI** (không Groq, không Gemini). Chỉ đọc file trong thư mục video. Thiếu audio cảnh nào thì báo lỗi, không tự đọc bù bằng giọng khác (giữ C-0001-1: không trộn 2 bộ giọng).
- **C-0013-2**: Xuất CapCut không sửa `script.json`, `product.json`, `video.mp4`; chỉ ghi `capcut.json` và thư mục draft của CapCut.
- **C-0013-3**: Công cụ MCP chỉ đọc/ghi trong `TT_AFFILIATE_DIR/storage/videos/<tên thư mục>`; tên thư mục có `/` hoặc `..` bị từ chối.

---

## 8. File thay đổi

| File | Loại |
|------|------|
| `tools/capcut-mcp/**` | Mới (chuyển từ máy người dùng) |
| `capcut_export.py` | Mới |
| `demo.py` (`--capcut`, `--voice`) | Sửa |
| `backend/app/api/studio.py`, `backend/app/web/studio.html` | Sửa |
| `requirements-demo.txt` (`-e tools/capcut-mcp`), `.env.example` | Sửa |
| `render_video`, Gemini TTS, Drive, Sheet | Không đổi |

---

## 9. Tiêu chí hoàn thành (DoD)

| Mã | Điều kiện | Mong đợi | Cách kiểm |
|----|-----------|----------|-----------|
| D-1 | `--capcut` trên bản sao một video simple có 4 cảnh | Thư mục draft có `draft_content.json`, 4 đoạn video, 4 đoạn audio, thời lượng mỗi cảnh = audio + 0.25s (±0.05s) | đọc JSON |
| D-2 | Video không có giá (`price=0`) | Không có chữ giá | đọc JSON |
| D-3 | Thiếu `audio_2.mp3` | Exit khác 0, thông báo cảnh 3 thiếu giọng, không tạo draft | mã thoát |
| D-4 | Thư mục không có `product.json` (travel) | Từ chối, "Chỉ hỗ trợ video sản phẩm" | mã thoát |
| D-5 | Tạo video với `voice=edge` | `script.json → tts_provider = "edge"`, sổ đếm Gemini không đổi | so file sổ đếm |
| D-6 | `POST /videos/{folder}/capcut` thiếu `X-Studio` | 403 | TestClient |
| D-7 | MCP `affiliate_export_to_capcut("../x")` | Từ chối | gọi hàm |
| D-8 | MCP `create_product_video` với `narration` từng cảnh, `voice="edge"` | Draft và MP4 đều có tiếng | ffprobe có luồng audio |
| D-9 | Hồi quy: `--render-only`, `--approve` | Như trước | chạy trên bản sao |
| D-10 | Tạo video với `CAPCUT_AUTO_EXPORT=1` | Có `capcut.json` sau khi dựng; nếu xuất lỗi thì video vẫn `review`, log có cảnh báo | mã thoát + file |
| D-11 | Cùng một video, danh mục "Đồ ăn" và "Điện tử" | Bộ hiệu ứng khác nhau (chuyển cảnh, filter, animation chữ), mọi tên hiệu ứng có trong pycapcut | đọc JSON |
| D-12 | `choose_persona` sản phẩm "Trà ô long" | `nam_bac` | gọi hàm |
| E2E-3 | Người dùng mở draft trên CapCut Mac | Thấy ảnh, chữ, nghe giọng | người dùng xác nhận |

---

## 10. Những gì KHÔNG làm

Tự bấm Export trong CapCut; dùng giọng TTS của CapCut; video du lịch / bài tập sang CapCut; đăng TikTok; Shopee.

---

## 11. Câu hỏi mở cho người dùng

| Mã | Câu hỏi | Đề xuất của BA | Trả lời |
|----|---------|----------------|---------|
| Q-1 | Đưa `capcut-mcp` vào repo `tools/capcut-mcp/` (Claude Desktop trỏ vào đó), bỏ bản rời ở `~/Documents/project/capcut-mcp`? | Có: một bản duy nhất, có lịch sử sửa | Có, là một capability trong repo. Hiệu ứng hình chọn theo bối cảnh video cho đẹp, bắt mắt, không chỉ ảnh đơn thuần |
| Q-2 | Khi tạo video mới, giọng mặc định là gì? | Giữ Gemini mặc định, thêm ô chọn "Miễn phí (edge-tts)" | Mặc định Gemini như hiện tại |
| Q-3 | Sau khi tạo video, có tự xuất sang CapCut luôn không? | Không, bấm nút khi cần (xuất mất vài giây, nhưng chỉ cần cho video muốn chỉnh tay) | Có, tự xuất sau khi đã có giọng đọc |
| Q-4 | Giọng edge-tts cho MCP: nữ miền Nam (`HoaiMy`) hay nam miền Bắc (`NamMinh`)? | Theo `choose_persona` như pipeline | Nữ: nấu ăn, làm đẹp, thời trang. Nam: trà, điện tử… |

---

## 12. Kết quả

(Điền sau khi Dev, Reviewer, Tester, MKTG xong.)

## 13. Liên quan

Issue #36 · DR-0001 (Studio), DR-0007 (tạo video mới), DR-0012 (sổ đếm Gemini) · `pycapcut` 0.0.4
