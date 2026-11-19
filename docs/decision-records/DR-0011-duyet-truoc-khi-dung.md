# DR-0011: Duyệt trước khi dựng (cổng duyệt kịch bản, hình, ảnh nhân vật cho mọi loại video)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã duyệt (2026-11-19, kèm câu trả lời Q1–Q5 ở § 12; Q4 đổi so với đề xuất) | 2026-11-18 | Claude (BA) | chungkhoantony1983 (2026-11-19) |

Capability: `video-render`, `script-gen`, `travel-content` · Nhánh: `feat/review-gates` · GitHub issue: #? (chưa tạo, lỗi TLS) · Domain workflow: `feature`

Vai trò: **BA** = `ba` · **Dev** = `dev` · **Reviewer** = `reviewer` · **Tester** = `tester` · **MKTG** = `marketing` (giao diện, chữ cho người vận hành không rành kỹ thuật) · **Tech Lead** (chạm `demo.py`, mã thoát, tiến trình nền).

> **Đánh dấu**: chỗ ghi "cần kiểm khi làm" là chưa kiểm trên code của nhánh khác chưa merge. BA đã đọc `main` (`demo.py`, `exercise.py`, `product_sources.py`, `api/studio.py`, `studio.html`) và đọc các DR/nhánh mở ở chế độ chỉ đọc.
>
> **Số ràng buộc**: ba DR khác nhau đều có `C-0002-x` (DR-0002 travel, DR-0002 gemini-quota, DR-0002 clip-trim). Trong DR này luôn ghi kèm tên: "C-0002-4 (travel)".

---

## 1. Bối cảnh

**Vấn đề gốc**: luồng hiện tại là *viết kịch bản → đọc giọng → dựng → người vận hành duyệt → sửa → đọc lại giọng + dựng lại*. Sửa SAU khi dựng là bước đắt nhất (đọc lại giọng, dựng lại 1–2 phút; video Gemini mất 1 lượt cho mỗi câu sửa, hạn mức 10 lượt/ngày). Lỗi nội dung (hook yếu, câu bịa, số sai, hình lạc đề, prompt ảnh nhân vật sai) lẽ ra phải bắt được **trước** khi tốn giọng đọc và dựng.

**Yêu cầu người dùng (2026-11-18)**, cho cả video sản phẩm, bài tập, du lịch:

1. Duyệt hook + kịch bản (lời đọc, phụ đề, dữ kiện) trên Studio, bấm Duyệt rồi mới đọc giọng và dựng.
2. Duyệt clip/ảnh đã chọn cho từng cảnh (đổi hoặc báo thiếu) trước khi dựng.
3. Duyệt prompt ảnh nhân vật (style `story`) trước khi tạo hoặc tải ảnh.

**Đã đọc trong code (`main`)**:

| Chỗ | Hiện trạng | Hệ quả |
|-----|-----------|--------|
| `demo.py` `run_one` | `generate_script` → `generate_voiceovers` → `generate_story_images` → `save_script` + `product.json` → `finish` (dựng ngay). Không có chỗ dừng trước giọng | Giọng đọc luôn tốn trước khi người thấy kịch bản (chỉ thấy sau khi dựng) |
| `demo.py` `finish` / `render_and_check` | Sau dựng: thiếu ảnh nhân vật → `needs_images` (video nháp dùng ảnh sản phẩm); đủ → `review` (APPROVAL_MODE=web) | `prompts.txt` chỉ có SAU khi dựng |
| `demo.py` `SHEET_STATUS` | `ready_for_manual_upload→done`, `needs_images`, `review`. `ProductSheet.pending()` bỏ qua mọi status khác rỗng | Status mới tự được bỏ qua khi chạy lại, không phải sửa bộ lọc |
| `exercise.py` `run_next` | Lời đọc lấy thẳng từ giáo trình (không Groq). Thiếu clip → `needs_clips`, dừng **trước giọng** (đã có sẵn một cổng clip) | Cổng clip của bài tập chỉ là "có/không có file", chưa cho xem/đổi |
| `api/studio.py` | `_folders()` chỉ liệt kê thư mục **có `video.mp4`**; `_editable` cần `product.json`; `_label` = `needs_images` (có `prompts.txt`) / `approved` (có `post.txt`) / `review`; `ERROR_KINDS = {3, 4}`; render/approve chạy `demo.py` bằng subprocess (C-0001-2) | Thư mục chưa dựng không hiện trên Studio |
| `travel.py` (nhánh `travel-p1`, PR #17) | `_run_row_body`: research → facts → `write_and_check` (Groq + `check_script`) → `build_media` → `voice_segments` (edge-tts) → `render` → status `review`. Mã thoát 5 `fact_check`, 6 `facts_stale`, 7 `drive_failed` | Hai điểm dừng tự nhiên: sau `write_and_check` (kịch bản) và sau `build_media` (hình) |
| DR-0010 (nhánh `travel-story`) | Thư viện cảnh quay, kiểm khớp hình, mã **8** `needs_broll` + `--resume DIR`; Studio giai đoạn A không có UI cho mã 8 và không có "thay clip" (giai đoạn B) | Cổng hình chính là chỗ DR-0010 giai đoạn B cần |

**Chi phí hiện tại** (nguồn: `agent/CLAUDE.md`, DR-0007, DR-0010): Groq $0 (free). Gemini TTS free 10 lượt/ngày, 4 lượt/video sản phẩm; hết thì edge-tts $0. Dựng FFmpeg $0. Tìm clip Pixabay/Pexels/Wikimedia: $0 (hạn mức gọi API chưa rõ, cần kiểm khi làm).

**Ràng buộc ngoài**: không đổi `app.html` (C-0001-4); Shopee tạm dừng; kênh chưa có quyền affiliate (xem `TODO.md`) nên video du lịch và bài tập (không bán hàng) vẫn đăng được.

---

## 2. Quyết định

> **Thêm tối đa 3 cổng duyệt trước khi tốn giọng đọc và dựng. Mỗi cổng là một "trạng thái thư mục" ghi trong `script.json → stage` (và `status` trên Sheet/CSV): `script_review` (kịch bản + prompt ảnh), `images_review` (ảnh nhân vật, chỉ style story), `media_review` (clip/ảnh từng cảnh). Thư mục ở cổng nào cũng hiện trên Studio dù chưa có `video.mp4`. Người vận hành sửa trên Studio rồi bấm "Duyệt ... và tiếp tục", Studio chạy `demo.py --continue DIR` (một lệnh chung cho mọi loại video). Cổng nào cũng tắt/bật được; mặc định theo loại video. Cổng chỉ tốn Groq và tìm media ($0 trong phạm vi quota free); đọc giọng và dựng chỉ xảy ra sau cổng cuối.**

### 2.1 Các cổng theo loại video

| Loại | Cổng 1 `script_review` | Cổng 2 | Sau cổng cuối |
|------|-----------------------|--------|---------------|
| **Du lịch** (`travel.py`) | Sau `write_and_check`: hook, `line`, `subs.vi`, `caption`, hashtag; dữ kiện (claim, quote, nguồn) chỉ đọc | `media_review`: sau `build_media` (thư viện cảnh quay DR-0010 / stock): xem clip từng cảnh, nhãn nguồn, đổi clip, báo thiếu | `voice_segments` (edge-tts) → `render` → `review` |
| **Sản phẩm, style story** | Sau `generate_script`: hook, lời đọc, chữ trên cảnh sản phẩm, giá, caption, **prompt ảnh nhân vật từng cảnh** | `images_review`: hiện prompt (nút Sao chép), tải ảnh nhân vật từng cảnh, hoặc "Dùng ảnh sản phẩm cho cảnh này" | `choose_persona` + `generate_voiceovers` → `render` → `review` |
| **Sản phẩm, style simple** | Như trên (không có prompt ảnh) | `media_review` tuỳ chọn: xem ảnh sản phẩm gắn cho từng cảnh (đã chọn ở màn hình Tạo video của DR-0007) | Như trên |
| **Bài tập** (`exercise.py`) | Lời đọc lấy từ giáo trình đã duyệt, không có Groq → xem được nhưng mặc định tắt | `media_review`: xem clip từng cảnh (clip của bạn / Pixabay), báo thiếu; thay thế chuyển sang mục cắt clip của DR-0002 clip-trim | Giọng → dựng → `review` |

Thứ tự khi có nhiều cổng: `script_review` → `images_review` / `media_review` → (giọng + dựng).

### 2.2 Quan hệ với trạng thái hiện có

| Trạng thái | Ý nghĩa mới | Thay đổi |
|-----------|-------------|----------|
| `script_review`, `images_review`, `media_review` | **Mới.** Chưa có giọng đọc, chưa có `video.mp4` | Thêm vào `SHEET_STATUS` / tên nhãn Studio |
| `needs_images` (đã có) | Đã dựng nháp, còn cảnh thiếu ảnh nhân vật | **Giữ nguyên nghĩa**, thư mục cũ vẫn dùng như cũ. Luồng mới (cổng bật) không tạo bản nháp: dừng ở `images_review` |
| `review` (đã có) | Đã dựng, chờ duyệt cuối | Không đổi. Đây là điểm đến sau cổng cuối |
| `needs_clips` (exercise), `needs_broll` (DR-0010) | Thiếu clip trước giọng | Hợp nhất dần vào `media_review` (thiếu hiện là cảnh "Thiếu" trong cổng hình); mã thoát/Sheet cũ giữ cho tới khi DR-0010 merge |

### 2.3 Lệnh duyệt

| Việc | Lệnh | Ghi chú |
|------|------|---------|
| Duyệt cổng hiện tại, chạy tiếp đến cổng kế hoặc đến dựng | `demo.py --continue DIR` | Đọc `stage` trong `script.json`; kiểm lại (§ 5); sang cổng kế hoặc đọc giọng + dựng, rồi đặt status `review` |
| Chọn lại clip cho một số cảnh ($0, không giọng) | `demo.py --rematch DIR --scenes 2,3` | Loại clip hiện tại của các cảnh này khỏi lựa chọn, tìm clip khác; ở lại `media_review`. Cần kiểm khi làm: gộp với `--resume` của DR-0010 |
| Duyệt cuối (như cũ) | `demo.py --approve DIR` | Không đổi |

`--resume DIR` của DR-0010: giữ nguyên; khi hai DR cùng merge thì `--resume` là bí danh của `--continue` trên thư mục `media_review` (Dev quyết định bí danh hay gộp). Người vận hành chỉ thấy nút trên Studio, không gõ lệnh.

### 2.4 Tắt/bật cổng (chạy tin cậy)

- Biến môi trường `.env`: `REVIEW_GATES` = danh sách cổng bật, ví dụ `script,images,media`; `none` = tắt hết. Ghi đè từng loại: `REVIEW_GATES_PRODUCT`, `REVIEW_GATES_EXERCISE`, `REVIEW_GATES_TRAVEL`. Cờ CLI `--gates script,media` hoặc `--no-gates` ghi đè `.env` cho lần chạy đó.
- **Mặc định (đề xuất, hỏi người dùng ở Q1)**: du lịch `script,media`; sản phẩm story `script,images`; sản phẩm simple `script`; bài tập `media`.
- `APPROVAL_MODE=terminal`: không dừng ở cổng nào (duyệt kiểu y/n như cũ; gate cần Studio).
- **`--skip-approval` (đã chốt 2026-11-19, Q4)**: bỏ **duyệt cuối** (đăng luôn như hiện nay) và bỏ cổng **hình/ảnh** (`images_review`, `media_review`; ảnh thiếu thì dùng ảnh sản phẩm / báo lỗi như hiện nay), nhưng **vẫn giữ cổng kịch bản** `script_review`. Chạy không người (cron, `--sheet` hàng loạt) vì vậy dừng ở `script_review`, Sheet ghi `script_review`, không đọc giọng, không dựng, không đăng. Muốn chạy hoàn toàn không dừng phải ghi rõ `--no-gates` (hoặc `REVIEW_GATES=none`) cùng với `--skip-approval`; mỗi lần dùng `--no-gates` log in một dòng cảnh báo "bỏ qua cổng kịch bản".
- Chạy hàng loạt (`--sheet`): mỗi hàng dừng ở cổng đầu, nên người vận hành tạo nhiều kịch bản rồi duyệt một lượt.

---

## 3. Chi phí (P02)

| Giai đoạn | Việc | Chi phí | Lượt Gemini TTS |
|-----------|------|---------|-----------------|
| Trước cổng 1 | Đọc trang sản phẩm / nguồn travel, Groq viết kịch bản | Groq free, $0 | 0 |
| Cổng 1, 2 (đang chờ) | Người sửa trên Studio; `--rematch` tìm clip khác | $0 (hạn mức gọi API tìm clip chưa rõ, cần kiểm khi làm) | 0 |
| Sau cổng cuối | Đọc giọng | Gemini: 4 lượt/video sản phẩm, free 10/ngày; hết lượt → edge-tts $0. Travel: edge-tts $0 (DR-0008 quyết định 3). Bài tập: theo `exercise.py` hiện tại | Như hiện tại |
| Sau cổng cuối | Dựng FFmpeg | $0 | 0 |

**Lợi ích tiền/quota**: sửa lời trước khi đọc giọng nghĩa là mỗi câu chỉ đọc **một lần** (hiện sửa sau dựng tốn thêm 1 lượt Gemini mỗi câu sửa, DR-0001). Không có chi phí trả phí mới. Chi phí thật là **thời gian người vận hành**: thêm 1–3 lần bấm duyệt mỗi video (chưa đo; MKTG đánh giá ở bước review).

Khi gemini-quota (DR-0002 gemini-quota) merge: màn hình cổng 1 hiện "Duyệt xong sẽ dùng khoảng 4 lượt giọng Gemini, hôm nay còn N" qua `GET /api/studio/voice-quota` (cần kiểm khi làm).

---

## 4. Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Cổng theo trạng thái thư mục (`script.json → stage`) + `demo.py --continue` chung cho mọi loại, Studio liệt kê thư mục chưa có video | ⭐ | Một cơ chế cho 3 loại video; mọi xử lý trong `demo.py`/`travel.py` (C-0001-2); thư mục cũ không có `stage` chạy như cũ; Sheet tự bỏ qua status mới |
| B | Mỗi loại video tự làm cổng riêng (travel một kiểu, product một kiểu) | - | Ba bộ trạng thái, ba lệnh, ba màn hình; người vận hành phải nhớ khác nhau |
| C | Chỉ thêm `--dry-script` in kịch bản ra terminal, duyệt bằng mắt rồi chạy lại | - | Sai yêu cầu (duyệt trên Studio); chạy lại gọi Groq lần 2 và kịch bản có thể khác bản đã duyệt |
| D | Giữ luồng cũ, chỉ đọc giọng lười (đọc khi bấm Duyệt cuối) | - | Vẫn dựng video trước khi duyệt; người không xem được kịch bản dưới dạng chữ sớm; không giải quyết hình lạc đề |

---

## 5. Thay đổi cấu trúc

### 5.1 Dữ liệu

| Đối tượng | Trước | Sau | Lý do |
|-----------|-------|-----|-------|
| `script.json → stage` | Không có | `"script_review"` \| `"images_review"` \| `"media_review"`; xoá khi dựng xong | Một nơi chứa trạng thái cổng cho mọi loại |
| `script.json → gates_pending` | Không có | Danh sách cổng còn lại phải qua, ví dụ `["images"]` | `--continue` biết cổng kế tiếp mà không đọc lại `.env` (cấu hình đổi giữa chừng không làm lệch) |
| `script.json → segments[i].image_prompt` | Có, chỉ đọc lại từ `prompts.txt` khi hiện trên Studio | Là nguồn duy nhất; `prompts.txt` luôn sinh ra từ `script.json`, không bị đọc ngược | Prompt sửa ở cổng 1 phải thành prompt thật |
| `script.json → segments[i].media_flag` | Không có | `"missing"` khi người báo thiếu / sai hình; `--continue` từ chối nếu còn cảnh gắn cờ | Báo thiếu hình trước khi dựng |
| `script.json → image_fallback` (theo cảnh) | Không có | `"product"` khi người chọn dùng ảnh sản phẩm thay ảnh nhân vật | Thay cho "video nháp" của `needs_images` |
| Sheet/CSV `status` | trống, `done`, `skip`, `needs_images`, `review` (+ `needs_broll`, `needs_sources` ở nhánh travel) | Thêm `script_review`, `images_review`, `media_review` | Hàng đang chờ duyệt không bị làm lại |
| `travel.py _set_sheet_status(only_from=("", "review"))` | Chỉ ghi đè hàng trống / `review` | Thêm 3 status cổng vào `only_from` | Chuyển `script_review → media_review → review` được; status gõ tay vẫn không bị ghi đè |
| Mã thoát | 3 revoice, 4 not_ready, 5 fact_check, 6 facts_stale, 7 drive_failed (travel-p1); 8 needs_broll (DR-0010 dự kiến); 5, 6 cũng dùng cho cờ `--clip-*` (clip-trim, tách khỏi luồng này) | **9** = `gate_not_ready` (dùng `--continue` trên thư mục không ở cổng nào, hoặc còn cảnh `media_flag`/thiếu ảnh chưa xử lý). **10–11 để dành** cho DR này. Thiếu hình dùng mã 8 (nếu DR-0010 chưa merge thì DR này định nghĩa 8 cùng nghĩa); kiểm kịch bản travel dùng mã 5 | Không đụng 3–7; Studio thêm vào `ERROR_KINDS` |

### 5.2 Luồng hệ thống (từng loại, cổng bật hết)

```
Sản phẩm story:
  autofill → generate_script (Groq) → ghi script.json + product.json, stage=script_review  ⏸ Cổng 1
  --continue → kiểm lại → ghi prompts.txt từ script.json, stage=images_review             ⏸ Cổng 2 (tải ảnh)
  --continue → [IMAGE_PROVIDER=gemini: tạo ảnh] → choose_persona + generate_voiceovers → render → status=review → duyệt cuối như cũ

Du lịch:
  research → facts → write_and_check (Groq) → script.json, stage=script_review             ⏸ Cổng 1
  --continue → check_script (C-0008-1, C-0002-1/4 travel) → build_media → stage=media_review ⏸ Cổng 2
  --continue → voice_segments (edge-tts) → render → status=review

Bài tập:
  next_item → build_script → chọn clip → (thiếu: needs_clips như cũ) → stage=media_review   ⏸ Cổng 2
  --continue → generate_voiceovers → render → review
```

Khi một cổng tắt thì bước đó chạy thẳng như hiện nay. Khi mọi cổng tắt: hành vi y như `main`.

### 5.3 Studio: danh sách thư mục và API

- `_folders()` liệt kê thêm thư mục có `script.json → stage` thuộc 3 cổng (kể cả chưa có `video.mp4`; travel: có `topic.json`). `_label` kiểm `stage` **trước** `prompts.txt` (tránh nhầm với `needs_images`).
- `GET /videos/{folder}` trả thêm `stage`, `gates_pending`, `video_url = null`; với cổng hình trả `media[]` theo cảnh `{url, kind: clip|image, source: "library"|"stock"|"product"|"character", license, page, flag}`.
- `PUT /videos/{folder}` ở cổng: ghi `script.json` (hook, line, subs, text, caption, hashtag, giá, `image_prompt`, `media_flag`, `image_fallback`). Không đặt `needs_render`. Không thêm/xoá cảnh (giữ rule "Số cảnh không khớp").
- Thêm `POST /videos/{folder}/continue` (chạy `demo.py --continue DIR` như job nền, action `continue`), `POST /videos/{folder}/rematch` (`--rematch`). `POST .../render` và `.../approve` trả 409 với thư mục còn ở cổng ("Hãy duyệt kịch bản trước"). Mọi API ghi bắt buộc `X-Studio: 1` (C-0001-3).
- Một job một lúc, log trong `storage/studio-logs/` như cũ. Dòng log `Studio folder: <tên>` phải in cả khi dừng ở cổng, để màn hình Tạo video (DR-0007) mở đúng thư mục.

### 5.4 Giao diện Studio (mô tả bằng lời, tiếng Việt, không lộ tên trạng thái kỹ thuật)

- **Danh sách**: nhãn mới "Chờ duyệt kịch bản", "Chờ ảnh nhân vật", "Chờ duyệt hình", bên cạnh "Chờ duyệt" (đã dựng), "Cần ảnh", "Chỉ xem". Đếm số video chờ ở từng nhãn.
- **Dải bước ở đầu màn hình**: "Bước 1 Kịch bản → Bước 2 Hình → Bước 3 Xem video đã dựng → Duyệt". Bước hiện tại tô đậm; chú thích: "Chưa tốn giọng đọc. Máy chỉ đọc giọng và dựng sau khi bạn bấm Duyệt." Nút **Duyệt kịch bản và tiếp tục**, **Lưu** (chưa dựng).
- **Cổng kịch bản**: không có khung video; các ô hook, lời đọc từng cảnh, chữ trên cảnh, giá (sản phẩm), caption, hashtag. Trong cảnh story có ô "Prompt ảnh nhân vật" và nút Sao chép. Du lịch: dưới mỗi cảnh một hộp "Dữ kiện" chỉ đọc (câu trích, nguồn, ngày kiểm). Lỗi kiểm (số lạ, thiếu nguồn) hiện câu tiếng Việt đỏ ngay dưới cảnh và khoá nút Duyệt.
- **Cổng ảnh nhân vật** (story): mỗi cảnh một thẻ: prompt, nút Sao chép, nút Tải ảnh lên (dùng `POST .../image` sẵn có), nút "Dùng ảnh sản phẩm cho cảnh này". Nút Duyệt chỉ sáng khi cảnh nào cũng có ảnh hoặc đã chọn dùng ảnh sản phẩm.
- **Cổng hình** (clip/ảnh): lưới từng cảnh, clip tự lặp, tắt tiếng, kèm câu lời của cảnh đó. Nhãn nguồn: "Cảnh quay của bạn", "Ảnh sản phẩm", "Stock, chưa ai xem" (chữ theo DR-0010 § 6.6), "Thiếu". Nút **Chọn clip khác** (`--rematch`, $0) và **Báo thiếu**. Cảnh thiếu: hướng dẫn thêm cảnh quay như DR-0010 § 6.7, không dùng chữ "exit", "needs_broll", "BROLL_DIR". Điện thoại 390px không cuộn ngang.
- Không đụng `app.html` (C-0001-4).

### 5.5 Kiểm lại khi bấm Duyệt (`--continue`)

| Cổng | Kiểm lại | Nếu sai |
|------|----------|---------|
| `script_review` du lịch | `check_script(strict=False)`: số trong line/subs/hook/caption có trong quote (C-0008-1), mỗi cảnh `answer` có fact hợp lệ (C-0002-1 travel), câu "check the official site" khi có fact `tier1_categories` (C-0002-4 travel), giới hạn từ (DR-0010) | Mã 5, `stage` giữ nguyên, không gọi giọng/dựng |
| `script_review` du lịch | Fact `volatile` quá 30 ngày | Chỉ cảnh báo ở cổng; vẫn chặn ở `--approve` (mã 6, C-0008-2) |
| `script_review` sản phẩm | Lời đọc không rỗng, độ dài tối đa như `PUT` hiện tại; giá `0` hoặc `>= 1000` (C-0007-2); nếu giá đổi mà lời còn nhắc giá cũ → **cảnh báo** (không chặn) | Rỗng/dài/giá lỗi → báo 400 ngay khi Lưu; cảnh báo hiện ở Studio |
| `images_review` | Mọi cảnh story có `canh_N.<ext>` hoặc `image_fallback=product` | Mã 9 |
| `media_review` | Không còn cảnh `media_flag` hoặc thiếu file; thư viện: `library_problem` (C-0010-8, nếu DR-0010 merge) | Mã 8 (thiếu) / mã 9 |

---

## 6. Phạm vi từng giai đoạn

| GĐ | Loại video | Nội dung | Điều kiện bắt đầu |
|----|-----------|----------|--------------------|
| **0** | Chung | `stage`, `--continue`, mã 9, liệt kê thư mục chưa có video, khung cổng trên Studio, biến `REVIEW_GATES*`, `SHEET_STATUS` | PR #17 (`travel-p1`) đã merge; xem § 9 |
| **1** | **Du lịch** (đề xuất làm trước: video mới, là điểm đau của người dùng, code `travel.py` chưa có người dùng cũ) | Cổng kịch bản + cổng hình (xem, báo thiếu, `--rematch`) | GĐ 0; DR-0010 merge (cổng hình dùng thư viện) |
| **2** | Sản phẩm | Cổng kịch bản; cổng ảnh nhân vật (story); cổng hình (simple) | GĐ 0; DR-0007 và gemini-quota merge |
| **3** | Bài tập | Cổng hình (clip), tuỳ chọn cổng kịch bản; thư mục bài tập hiện "Chỉ xem" trên Studio nên cần mở chế độ sửa cổng | GĐ 0; clip-trim merge (mục cắt clip) |

---

## 7. Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Gỡ khi |
|----|-----------|-------|---------|--------|
| C-0011-1 | Khi một video đang ở cổng thì `demo.py`/`travel.py` **không** gọi TTS (Gemini hay edge) và **không** chạy FFmpeg dựng cho video đó. Giọng và dựng chỉ chạy sau cổng cuối đã bật | Mục tiêu của DR: không tốn giọng/dựng trước khi duyệt | `demo.py`, `travel.py`, `exercise.py` | — |
| C-0011-2 | `--continue` kiểm lại toàn bộ luật nội dung của loại video (travel: C-0008-1, C-0002-1 và C-0002-4 của DR-0002 travel; sản phẩm: C-0007-2) trước khi sang bước sau. Sai thì dừng, `stage` giữ nguyên | Người sửa tay ở cổng không được vượt luật dữ kiện | `demo.py`, `travel.py` | — |
| C-0011-3 | Logic cổng nằm trong `demo.py`/`travel.py`/`exercise.py`. `api/studio.py` chỉ đọc/ghi JSON, ảnh và chạy subprocess; API ghi cần `X-Studio: 1`, không mở CORS | Mở rộng C-0001-2, C-0001-3 | `backend/app/api/studio.py` | Khi chuyển backend đầy đủ |
| C-0011-4 | Thư mục không có `script.json → stage` chạy y như trước. Nghĩa của `needs_images`, `review`, `needs_clips`, `needs_broll` không đổi. 3 tên `script_review`, `images_review`, `media_review` dành riêng cho DR này | Không phá thư mục và hàng Sheet đang có | Mọi nơi đọc `status`/`stage` | — |
| C-0011-5 | Cổng kịch bản chỉ bỏ bằng cấu hình rõ ràng (`REVIEW_GATES*`, `--gates`, `--no-gates`, `APPROVAL_MODE=terminal`); `--skip-approval` chỉ bỏ duyệt cuối và cổng hình/ảnh, không bỏ cổng kịch bản. Mặc định theo loại video ghi trong DR này và `.env.example` | Không tắt âm thầm: cổng kịch bản không bao giờ bị bỏ chỉ vì `--skip-approval`; chạy không người không thể lọt kịch bản chưa ai xem | `demo.py` | — |
| C-0011-6 | Thư mục ở cổng không bao giờ bị tải lên Drive hoặc xoá. Chỉ `--approve` (duyệt cuối) mới làm việc đó | Mất kịch bản chưa dựng là mất việc | `demo.py`, `drive_upload.py` | — |
| C-0011-7 | `script.json → image_prompt` là nguồn duy nhất của prompt ảnh nhân vật; `prompts.txt` luôn sinh từ nó, không parse ngược | Prompt sửa ở cổng phải là prompt đưa cho người tạo ảnh | `demo.py`, `studio.py` | — |
| C-0011-8 | Mã thoát: 9 = `gate_not_ready`; 10–11 để dành; không dùng lại 3–8 cho nghĩa khác | Studio đọc mã thoát (`ERROR_KINDS`) | `demo.py`, `studio.py`, `travel.py` | — |

**Chạm nhưng không đổi**: C-0001-1 (một bộ giọng; giọng chỉ đọc một lần sau cổng), C-0001-4, C-0007-2, C-0008-1, C-0008-2, C-0002-1/3/4/5 (DR-0002 travel), C-0002-1 (gemini-quota: một model/video; giọng đọc qua `quota_reserve` ở bước sau cổng), C-0010-8, C-0010-10 (mã 8 trước Groq vẫn giữ). `supersedes: —`

---

## 8. Bảng quyết định

### 8.1 Code

| # | Điều kiện đầu vào | Kết quả mong đợi | Cách kiểm |
|---|-------------------|------------------|-----------|
| D-1 | Product story, `REVIEW_GATES=script,images`, `run_one` | Dừng, `script.json.stage=script_review`, có `product.json`, **0 lời gọi TTS**, không có `audio_*.mp3`/`video.mp4`; Sheet `script_review`; log in `Studio folder:` | TTS giả đếm lời gọi, Groq giả |
| D-2 | D-1 rồi `--continue` | `prompts.txt` sinh từ `script.json`, `stage=images_review`, vẫn 0 TTS | Như trên |
| D-3 | D-2 rồi `--continue` khi còn cảnh story chưa có ảnh và không `image_fallback` | Mã 9, `stage` giữ, 0 TTS | Chạy trên bản sao |
| D-4 | Đủ ảnh, `--continue` | Giọng (edge, bản sao), dựng, `status=review`, `stage` bị xoá | edge-tts |
| D-5 | Sửa `image_prompt` ở cổng 1 rồi tới cổng 2 | `prompts.txt` có đúng chữ đã sửa | So file |
| D-6 | Product simple, `REVIEW_GATES=script` | Một cổng, `--continue` đi thẳng giọng + dựng → `review` | Chạy bản sao |
| D-7 | Travel, sửa `hook`/`line` chèn số không có trong quote, `--continue` | Mã 5, câu `[FACT_CHECK]` nêu cảnh + số, không đổi `stage`, 0 TTS | Sửa `script.json` bản sao |
| D-8 | Travel, `--continue` ở `script_review`, mọi thứ đúng | `build_media`, `stage=media_review`, 0 TTS, `video.mp4` chưa có | Searcher giả |
| D-9 | Travel, cảnh gắn `media_flag=missing`, `--continue` | Mã 8 (hoặc 9 nếu DR-0010 chưa merge), liệt kê cảnh | Bản sao |
| D-10 | `--rematch DIR --scenes 2` | Cảnh 2 đổi sang clip khác (khác clip cũ), cảnh khác giữ nguyên, ở lại `media_review`, $0 | Thư viện giả 2 clip |
| D-11 | Exercise thiếu clip | Hành vi `needs_clips` cũ (dừng trước giọng); đủ clip + cổng media bật → `media_review` thay vì dựng | `exercise.py` bản sao |
| D-12 | `--no-gates` (hoặc `REVIEW_GATES=none`), hoặc `APPROVAL_MODE=terminal` | Không cổng nào; hành vi y như `main`; `--no-gates` in dòng cảnh báo | So đầu ra với `main` |
| D-12a | `--skip-approval` một mình, cổng kịch bản bật (mặc định) | Dừng ở `script_review`: 0 TTS, 0 dựng, 0 đăng; Sheet `script_review`; exit 0 | TTS giả đếm lời gọi |
| D-12b | `--skip-approval` sau khi kịch bản đã duyệt (`--continue`) | Bỏ cổng hình/ảnh và duyệt cuối: đọc giọng, dựng, `publish` như `main` | Bản sao |
| D-12c | `--skip-approval --no-gates` | Chạy thẳng như `main` | So đầu ra với `main` |
| D-13 | `--continue` trên thư mục không có `stage` | Mã 9, thông báo tiếng Việt, không đổi file | Bản sao thư mục cũ |
| D-14 | Hồi quy: thư mục cũ có `video.mp4`, không `stage` | `GET /videos`, `PUT`, `render`, `approve` hoạt động như trước (DR-0001); nhãn `needs_images`/`review`/`approved` đúng | Bản sao thư mục cũ |
| D-15 | Studio: `GET /videos` | Thư mục ở cổng (không `video.mp4`) hiện với nhãn cổng; `video_url=null`; `.../video` trả 404 | API test |
| D-16 | Studio: `POST .../render` hoặc `.../approve` trên thư mục ở cổng | 409, thông báo tiếng Việt | API test |
| D-17 | Studio: API ghi thiếu `X-Studio: 1` | 403 (C-0001-3) | API test |
| D-18 | Hai job cùng lúc | Job thứ hai bị 409 như cũ | API test |
| D-19 | Hàng Sheet `script_review` khi chạy `--sheet` lại | Không bị làm lại (`pending()` bỏ qua) | Sheet/CSV giả |
| D-20 | Hàng Sheet có status gõ tay `skip`, travel `--continue` | Không bị ghi đè (`only_from`) | Sheet giả |
| D-21 | Gemini hết lượt ở bước giọng sau cổng cuối | Như hiện tại: mã 3, không đổi audio, `stage` giữ để `--continue` lại / chọn edge | Gemini giả lỗi |
| D-22 | Giá đổi ở cổng 1 từ 189000 sang 210000, lời còn "189 nghìn" | Chỉ cảnh báo, không chặn | Bản sao |

### 8.2 Tài liệu

| # | Tài liệu | Mong đợi |
|---|----------|----------|
| DD-1 | Hướng dẫn vận hành | Có mục "Duyệt trước khi dựng": 3 nhãn mới, bấm gì, thấy gì; không có chữ `stage`, `exit`, `--continue` trong phần người dùng |
| DD-2 | `.env.example` | `REVIEW_GATES`, `REVIEW_GATES_PRODUCT/EXERCISE/TRAVEL` kèm mặc định |
| DD-3 | `agent/CLAUDE.md` | Luồng `demo.py` có 3 cổng, lệnh `--continue`, `--rematch`, mã 9 |
| DD-4 | Spec L3 `video-render.md`, `script-gen.md`, `travel-content.md` | Luồng có cổng, trạng thái, API |

---

## 9. Rủi ro và thứ tự merge

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Xung đột | 4 nhánh mở cùng sửa `demo.py` (`main()`, `run_one`, `SHEET_STATUS`, dispatch `--render-only`/`--approve`), `studio.py` (`_folders`, `_label`, `ERROR_KINDS`, `video_detail`) và `studio.html` (nhãn, hàm `render`): `travel-p1`/`travel-story` (DR-0008, DR-0010), `gemini-quota` (DR-0002), `studio-create-video` (DR-0007) | Merge conflict lớn; DR này đổi chính các hàm đó | **Dev không bắt đầu GĐ 0 trước khi PR #17 merge.** Thứ tự đề xuất: #17 → gemini-quota → studio-create-video → travel-story (10a) → review-gates. Người điều phối chạy lại `branch_observer report --fetch` trước khi làm |
| R-2 | Phụ thuộc | Cổng hình du lịch cần thư viện cảnh quay (DR-0010); `--rematch` và mã 8 trùng `--resume` | GĐ 1 phần hình chưa làm được nếu 10a chưa merge | GĐ 1 làm cổng kịch bản trước, cổng hình sau 10a; bí danh `--resume` |
| R-3 | Phụ thuộc | DR-0007 hiện cảnh báo "Tạo video mới sẽ dùng ~4 lượt Gemini" ở màn Tạo video; sau DR này lượt chỉ dùng ở bước sau cổng | Chữ sai | Đổi chữ khi làm GĐ 2 (MKTG duyệt) |
| R-4 | Rủi ro | Người vận hành bỏ quên video ở cổng, thư mục chất đống | Rối danh sách | Đếm theo nhãn; Q5 (nút Bỏ video) |
| R-5 | Rủi ro | Thêm thao tác bấm làm chậm người vận hành | Giảm tốc độ đăng | Mặc định theo loại (Q1); `--no-gates` cho kịch bản đã tin. `--skip-approval` một mình không còn chạy thẳng: chạy hàng loạt không người sẽ dừng ở `script_review`, tài liệu vận hành phải nói rõ (người đang dùng cron/script cũ cần thêm `--no-gates`) |
| R-6 | Rủi ro | Studio hiện thư mục chưa dựng làm lộ `_editable` sai (cần `product.json`; travel dùng `topic.json`; exercise không có) | Lỗi 500 / "Chỉ xem" nhầm | Logic nhận dạng loại thư mục tập trung một hàm; test D-14, D-15 |
| R-7 | Giả định | `ProductSheet.pending()` bỏ qua mọi status khác rỗng (đã đọc ở `main`); `TravelSheet.pending()` (nhánh travel) cần kiểm khi làm | Hàng bị làm lại | Test D-19 |
| R-8 | Giả định | Hạn mức tìm clip free (Pixabay/Pexels/Wikimedia) chưa rõ | `--rematch` có thể bị chặn | Dùng cache `_cached_search` đã có; báo lỗi tiếng Việt |

---

## 10. Kế hoạch theo vai trò

| # | Việc | Vai trò | Output |
|---|------|---------|--------|
| 1 | Trả lời Q1–Q5 | Người dùng | Xong 2026-11-19, ghi ở DR § 12 |
| 2 | Cập nhật DR sau câu trả lời, tạo issue (khi hết lỗi TLS) | BA | DR |
| 3 | GĐ 0 chung (`stage`, `--continue`, mã 9, `REVIEW_GATES*`, liệt kê Studio) | Dev (Tech Lead soát: mã thoát, subprocess, đọc/ghi `script.json`) | Code |
| 4 | GĐ 1 du lịch → GĐ 2 sản phẩm → GĐ 3 bài tập | Dev | Code |
| 5 | Soát diff: C-0011-x, hồi quy `main`, C-0001-2/3 | Reviewer + Tech Lead | Ghi chú |
| 6 | Test D-x trên bản sao (edge-tts, Groq/Sheet/Drive giả) | Tester | Kết quả nguyên văn |
| 7 | Review chữ/giao diện cổng, điện thoại 390px, nhãn | MKTG | Danh sách sửa |
| 8 | Cập nhật tài liệu § 11 | BA | Docs |

---

## 11. Tài liệu SSoT bị ảnh hưởng và file code dự kiến đổi

| Tài liệu | Cập nhật | Xong |
|----------|----------|:----:|
| `docs/specs/architecture/capabilities/video-render.md` § Studio | Cổng, trạng thái, API mới | [ ] |
| `docs/specs/architecture/capabilities/script-gen.md` | Dừng sau `generate_script` | [ ] |
| `docs/specs/architecture/capabilities/travel-content.md` | Cổng kịch bản + hình | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Duyệt trước khi dựng: bấm gì, thấy gì, khi nào tắt | [ ] |
| `.claude/CLAUDE.md` | Luồng `demo.py`, lệnh, mã thoát 9, biến môi trường | [ ] |
| `.env.example` | `REVIEW_GATES*` | [ ] |
| `TODO.md` | Một dòng con trỏ (đã thêm) + ghi tiến độ khi xong | [ ] |

**Code dự kiến đổi (cho Dev, BA không sửa)**: `demo.py` (`run_one`, `main`, `SHEET_STATUS`, `--continue`/`--rematch`/`--gates`/`--no-gates`, `finish`, mã 9) · `travel.py` (`_run_row_body` tách điểm dừng, `_set_sheet_status` `only_from`, `main_existing`) · `exercise.py` (`run_next` điểm dừng cổng hình) · `product_sources.py` (kiểm `TravelSheet.pending()`) · `backend/app/api/studio.py` (`_folders`, `_label`, `ERROR_KINDS`, `video_detail`, `save_video`, `continue`/`rematch`) · `backend/app/api/studio_travel.py` · `backend/app/web/studio.html` · `.env.example`.

---

## 12. Quyết định của người dùng (2026-11-19)

| # | Câu hỏi | Người dùng chốt | Hệ quả trong DR |
|---|---------|-----------------|-----------------|
| Q1 | Mặc định cổng theo loại | Như đề xuất: du lịch = kịch bản + hình; sản phẩm story = kịch bản + ảnh nhân vật; sản phẩm simple = kịch bản; bài tập = hình | § 2.4 |
| Q2 | Story chưa có ảnh nhân vật | Dừng hẳn ở cổng ảnh, không có video nháp; giữ nút "Dùng ảnh sản phẩm cho cảnh này" | § 2.1, 2.2, D-3 |
| Q3 | Thứ tự | Duyệt DR; làm du lịch → sản phẩm → bài tập; hạ tầng (GĐ 0) chỉ sau khi PR #17 merge | § 6, § 9 R-1 |
| Q4 | `--skip-approval` | **Đổi so với đề xuất**: không bỏ mọi cổng. Bỏ duyệt cuối + cổng hình/ảnh, **vẫn giữ cổng kịch bản**; chạy không người dừng ở `script_review` (Sheet ghi trạng thái). Bỏ hết phải thêm `--no-gates` | § 2.4, C-0011-5, D-12…D-12c, R-5 |
| Q5 | Nút "Bỏ video này" | Để sau | § 14; tạm đặt `skip` tay trên Sheet |

---|---------|----------------|
| Q1 | Mặc định bật cổng nào cho từng loại? | Du lịch: kịch bản + hình. Sản phẩm story: kịch bản + ảnh nhân vật. Sản phẩm simple: kịch bản. Bài tập: chỉ hình (lời từ giáo trình đã duyệt). Tắt được bằng `.env`/cờ |
| Q2 | Video sản phẩm story: khi chưa có ảnh nhân vật thì dừng hẳn ở cổng ảnh (không còn "video nháp dùng ảnh sản phẩm" như `needs_images`), kèm nút "Dùng ảnh sản phẩm cho cảnh này"? | Đồng ý. Tránh dựng nháp tốn giọng; người vẫn bỏ qua được từng cảnh |
| Q3 | Thứ tự làm: du lịch trước, rồi sản phẩm, rồi bài tập? Du lịch phải chờ PR #17 và DR-0010 merge | Du lịch trước (video mới, điểm đau lớn nhất); GĐ 0 chỉ bắt đầu sau PR #17 |
| Q4 | `--skip-approval` (chạy không người) có nên bỏ qua mọi cổng? | Có. Nghĩa của cờ là "không dừng"; muốn dừng ở cổng thì không dùng cờ này |
| Q5 | Cần nút "Bỏ video này" ở cổng (xoá thư mục + đặt Sheet `skip`)? Đây là thao tác xoá | Làm sau (không trong DR này) và hỏi xác nhận hai lần; trước mắt đặt `skip` tay trên Sheet. Nếu bạn muốn có ngay, nói để BA thêm vào GĐ 0 |

---

## 13. Tiêu chí hoàn thành (DoD) và E2E

### Tiêu chí

- [ ] Mọi dòng D-1…D-22 và DD-1…DD-4 đạt; kết quả Tester chép nguyên văn.
- [ ] Với `--no-gates`, đầu ra `demo.py` giống `main` (D-12).
- [ ] Không vi phạm C-0001-1…4, C-0007-2, C-0008-1/2, C-0002 (travel) 1/3/4/5, C-0011-1…8.
- [ ] `app.html` và `api/creator.py` không đổi (`git diff` rỗng).
- [ ] Tài liệu SSoT § 11 đã cập nhật và đối chiếu code (tên lệnh, cờ, nhãn Studio).

### E2E

| # | Kịch bản | Mong đợi |
|---|----------|----------|
| V-1 | Du lịch, một câu hỏi phở (DR-0010 V-1), cổng bật: chạy → mở Studio → sửa một câu, thêm số sai → Duyệt | Bị chặn (mã 5, câu tiếng Việt); sửa lại → qua; thấy cổng hình, đổi một clip bằng "Chọn clip khác"; Duyệt → giọng + dựng → "Chờ duyệt" → Duyệt cuối. Số lượt Gemini = 0 |
| V-2 | Sản phẩm story, Gemini thật chỉ cho Tester đọc bản ghi (không dùng quota thật; Gemini giả) | Dừng ở kịch bản, sửa prompt ảnh, tải ảnh, Duyệt → 4 lời gọi TTS đúng một lần, không lời gọi nào ở cổng |
| V-3 | Bài tập có đủ clip, cổng hình bật | Dừng ở "Chờ duyệt hình"; báo thiếu một cảnh → chặn; xử lý xong → dựng |
| V-4 | Thư mục cũ (đã dựng, không `stage`) mở trên Studio, sửa, dựng lại, duyệt | Như DR-0001 |
| V-5 | `--sheet` với 3 hàng trống | 3 thư mục `script_review`, 3 hàng Sheet cùng status; chạy lại không làm lại |

---

## 14. Ngoài phạm vi

- Tạo video bằng AI (Veo) hay ảnh bằng API trả phí; đổi `IMAGE_PROVIDER` mặc định.
- Đổi `app.html`, scope TikTok, Shopee.
- Thêm kiểm dữ kiện mới cho video sản phẩm (chỉ cảnh báo giá; không đối chiếu thông số sản phẩm).
- Sửa dữ kiện (facts) trên Studio: chỉ đọc; muốn đổi thì thêm nguồn / `facts_manual` rồi tạo lại.
- Thêm/xoá cảnh, cắt clip trong cổng hình (thuộc DR-0002 clip-trim), UI thay clip bằng cách tải clip lên Studio (DR-0010 giai đoạn B).
- Nút "Bỏ video này" (Q5), duyệt nhiều video một lượt.
- Đăng TikTok tự động.

---

## 15. Kết quả

(Điền sau khi Dev, Reviewer, Tester xong.)
