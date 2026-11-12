# DR-0001: Trang duyệt & sửa video trên web (Review Studio)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã triển khai | 2026-11-12 | Claude (BA/dev-planner) | chungkhoantony1983 (yêu cầu làm 2026-11-12) |

Capability: `video-render` · Nhánh: `feat/video-review-studio` · Domain workflow: `spec`

Vai trò: **BA** = dev-planner · **Dev** = dev-implementer · **Reviewer** = dev-reviewer · **Tester** = dev-tester · **MKTG** = persona `ux`, đánh giá dưới góc nhìn người vận hành không rành kỹ thuật.

---

## Bối cảnh

**Vấn đề (gốc rễ)**:
Sau khi `demo.py` dựng video, việc duyệt và sửa đều làm trên terminal:

- `approval_step()` in kịch bản ra terminal, mở video, rồi hỏi `y/n`. Muốn sửa caption hay chữ trên màn hình thì phải mở `script.json` sửa tay, sau đó chạy `--rerender`.
- Kiểu tiểu phẩm (`needs_images`): người vận hành phải tự đổi tên ảnh thành `canh_N.png`, bỏ đúng thư mục, rồi gõ lệnh.
- Không sửa được lời đọc. Muốn đổi một câu thì phải tạo lại cả video, tức là gọi lại Groq và tạo lại toàn bộ giọng đọc.

Người vận hành không rành kỹ thuật nên dễ sai ở các bước này. Thêm nữa, duyệt xong là thư mục bị đẩy lên Drive và **xoá khỏi máy**, nên mọi chỉnh sửa phải xong *trước* khi duyệt.

**Lý do làm bây giờ**: người dùng yêu cầu ngày 2026-11-12 (Trang 2 trong đánh giá "dashboard + trang demo").

**Ràng buộc**:
- Chi phí $0 (P02). Gemini TTS free tier giới hạn 10 lượt/ngày, mỗi câu đọc tốn 1 lượt.
- Không được trộn 2 bộ giọng (Gemini và edge-tts) trong cùng một video. Quy tắc này đã có sẵn trong `generate_voiceovers`.
- `app.html` là trang TikTok đang xét duyệt app: **không được đổi** hành vi hay ngôn ngữ của trang này cho đến khi app được duyệt (memory: repo-public-for-tiktok-review).
- Không có test suite (`agent/CLAUDE.md`).

---

## Quyết định

> **Làm trang `Studio` riêng, viết bằng tiếng Việt, do chính service local `creator_main` phục vụ tại `http://127.0.0.1:8000/studio`. Mọi xử lý video vẫn nằm trong `demo.py` (thêm 2 lệnh `--render-only` và `--approve`). Service chỉ chạy `demo.py` ở tiến trình nền và báo tiến độ. Mặc định, bước duyệt chuyển từ terminal sang web.**

Điểm khác so với đề xuất trước đó ("mở rộng `app.html`"): `app.html` được giữ nguyên vì TikTok đang xét duyệt app. Trang Studio nằm cùng service với `app.html`, nên vẫn chỉ cần chạy một service.

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Trang `studio.html` riêng do `creator_main` phục vụ (cùng origin), backend gọi `demo.py` qua subprocess | ⭐ | Không đụng `app.html` đang xét duyệt. Cùng origin nên không cần CORS hay Private Network Access. Subprocess cách ly lỗi ffmpeg/TTS, logic dựng video vẫn chỉ ở một nơi (`demo.py`) |
| B | Thêm tab sửa video vào `app.html` (GitHub Pages) | - | Thay đổi trang TikTok reviewer đang xem. Trang tiếng Anh và public, trong khi phần sửa dành cho người vận hành Việt. Mỗi request lại phải qua CORS/PNA |
| C | Mở rộng Streamlit `dashboard/` | - | Phụ thuộc backend Postgres/Redis đang hoãn, chỉ có khung. Sẽ là framework UI thứ 2 cần bảo trì |
| D | Backend `import demo` rồi gọi hàm trực tiếp | - | Lỗi hoặc treo khi render làm sập service. `demo.py` dùng biến toàn cục (`KEEP_LOCAL`) và `print`. `uvicorn --app-dir backend` không có repo root trong `sys.path` |

---

## Thay đổi cấu trúc

### Dữ liệu

| Đối tượng | Trước | Sau | Lý do |
|-----------|-------|-----|-------|
| `script.json` → `tts_provider` | Không có | `"gemini"` hoặc `"edge"`, ghi khi tạo giọng | Đọc lại câu đã sửa bằng **đúng** bộ giọng của video |
| `script.json` → `segments[i].audio_line` | Không có | Câu thoại đã dùng để tạo `audio_i.mp3` | Phát hiện câu nào đã sửa và cần đọc lại. Thư mục cũ chưa có trường này thì coi như `audio_line = line` |
| `product.json` → `images[k]` | URL hoặc đường dẫn gốc | Có thể là `anh_sp_{k+1}.<ext>` trong thư mục video | Thay ảnh sản phẩm từ trang web |
| Ảnh cảnh nhân vật | `canh_N.png` chép tay vào thư mục | Tải lên từ web, lưu thành `canh_N.<ext>` (xoá các đuôi khác) | Bỏ bước đổi tên và gõ lệnh |
| `status` trên Sheet/CSV | trống, `done`, `skip`, `needs_images` | Thêm `review` (đã dựng, chờ duyệt trên web) | `pending()` đã bỏ qua mọi status khác rỗng, nên không phải sửa logic lọc |
| `.env` → `APPROVAL_MODE` | Không có | `web` (mặc định) hoặc `terminal` | Giữ được cách duyệt cũ khi cần |

### Luồng hệ thống

```
Trước:  … → render_video → approval_step (terminal y/n) → post.txt → Drive (xoá local) → status=done
Sau:    … → render_video → [APPROVAL_MODE=web] dừng, status=review, giữ thư mục
                 │
                 ▼  Người vận hành mở http://127.0.0.1:8000/studio
        Xem video → sửa caption / hashtag / hook / chữ cảnh / giá / lời đọc / ảnh
                 → "Dựng lại video"  = demo.py --render-only DIR   (chỉ đọc lại câu đã sửa)
                 → "Duyệt & lưu"     = demo.py --approve DIR       (post.txt → Drive → status=done)
```

`--skip-approval` giữ nguyên nghĩa cũ (đăng luôn, không dừng). `APPROVAL_MODE=terminal` giữ nguyên `approval_step()`.

### Luồng dữ liệu

- Trang → `PUT /api/studio/videos/{folder}` → ghi `script.json` / `product.json`. **Không** render ở bước này.
- Trang → `POST …/render` → service chạy `python demo.py --render-only <dir>` trong tiến trình nền, ghi log vào `<dir>/studio.log`. Trang đọc tiến độ qua `GET /api/studio/job`.
- `--render-only`: đọc lại câu có `line != audio_line` bằng `tts_provider` → `render_video` → `write_image_prompts`. Không duyệt, không Drive.
- Nếu đọc lại bằng Gemini bị lỗi (thường do hết quota): **không đổi file audio nào**, báo lỗi rõ ràng. Trang đưa lựa chọn "Đọc lại toàn bộ bằng giọng miễn phí (edge)" (`--revoice-all edge`), để không bao giờ trộn 2 bộ giọng.

### Thao tác người dùng (trang Studio)

| Thao tác | Gọi | Tốn gì |
|----------|-----|--------|
| Chọn video trong danh sách (nhãn: Chờ duyệt / Cần ảnh / Chỉ xem) | `GET /videos` | — |
| Sửa caption, hashtag → Lưu | `PUT` | $0, không dựng lại |
| Sửa hook, chữ trên cảnh sản phẩm, giá → Lưu → Dựng lại | `PUT` + `render` | $0, khoảng 1–2 phút |
| Sửa lời đọc → Lưu → Dựng lại | `PUT` + `render` | Mỗi câu sửa = 1 lượt Gemini (hạn mức 10/ngày). Trang hiện số lượt sẽ dùng trước khi bấm |
| Tải ảnh nhân vật / ảnh sản phẩm | `POST …/image` | $0 |
| Duyệt & lưu (hộp xác nhận: "thư mục sẽ chuyển lên Drive và xoá khỏi máy") | `POST …/approve` | $0 |

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 1 | Ghi `tts_provider`, `audio_line`; thêm `revoice_changed()`; `--render-only`, `--approve`, `--revoice-all`; `APPROVAL_MODE` | Dev | DR này | Code | `demo.py` |
| 2 | API Studio: list, chi tiết, lưu, tải ảnh, render/approve chạy nền, xem job | Dev | #1 | Code | `backend/app/api/studio.py` |
| 3 | Phục vụ trang `/studio` + ảnh cảnh; gắn router | Dev | #2 | Code | `backend/app/creator_main.py` |
| 4 | Trang Studio (tiếng Việt, dùng được trên điện thoại, sáng/tối) | Dev + MKTG | #2 | HTML | `backend/app/web/studio.html` |
| 5 | File bấm đúp để mở Studio (chạy service + mở trình duyệt) | Dev + MKTG | #3 | Script | `scripts/mo-studio.command` |
| 6 | Review code: đường dẫn, upload, khoá job, hồi quy CLI | Reviewer | #1–5 | Ghi chú review | DR §Kết quả |
| 7 | Test theo bảng quyết định trên **bản sao** thư mục video (edge-tts, không tốn quota Gemini; tắt Drive và Sheet) | Tester | #1–5 | Kết quả V-x | DR §Kết quả |
| 8 | Đánh giá dễ dùng: chụp màn hình trang, đi qua các tình huống của người vận hành | MKTG | #4, #5 | Danh sách sửa | DR §Kết quả |
| 9 | Cập nhật tài liệu | BA | #1–8 | Docs | xem §SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Hết quota Gemini khi đọc lại vài câu | Không dựng lại được | Không đổi audio cũ. Báo lỗi tiếng Việt kèm lựa chọn đọc lại toàn bộ bằng edge |
| R-2 | Rủi ro | Thư mục cũ không có `tts_provider` | Có thể đọc lại sai bộ giọng | Dùng `tts_provider()` hiện tại và ghi chú rõ trên trang. Thư mục mới luôn có trường này |
| R-3 | Rủi ro | Trang web khác gửi request ngầm tới `localhost:8000` (CSRF) | Sửa hoặc xoá được video | Các API ghi bắt buộc header `X-Studio: 1`. Header này không nằm trong CORS `allow_headers`, nên trình duyệt chặn request từ origin khác |
| R-4 | Rủi ro | Tên thư mục hoặc file độc hại (`../`) | Ghi ra ngoài `storage/videos` | Chỉ nhận thư mục có trong danh sách. Ảnh lưu bằng tên do server tự đặt, kiểm tra bằng Pillow, tối đa 15 MB |
| R-5 | Rủi ro | Bấm dựng lại nhiều lần cùng lúc | 2 ffmpeg ghi cùng file | Mỗi lúc chỉ chạy 1 job, job thứ hai bị từ chối (409) |
| A-1 | Giả định | Video dạng bài tập (`ex_intro`, `clips`, không có `product.json`) do script ngoài repo tạo | Không dựng lại được bằng `demo.py` | Hiện ở chế độ "Chỉ xem" (xem video, copy caption) |
| A-2 | Giả định | Service chạy từ repo root bằng `.venv` | Subprocess không tìm thấy `demo.py` | Tính repo root từ `__file__` và dùng `sys.executable` |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0001-1 | Một video chỉ dùng một bộ giọng. Khi đọc lại một phần thì phải dùng `tts_provider` của video; lỗi thì không thay audio nào | Trộn giọng nghe rõ là ghép | `demo.py` (revoice) | — |
| C-0001-2 | Mọi xử lý video nằm trong `demo.py`. `api/studio.py` chỉ đọc/ghi JSON, ảnh và chạy subprocess | Một nguồn logic duy nhất, CLI và web cho cùng kết quả | `backend/app/api/studio.py` | Khi chuyển sang backend đầy đủ (sau M1–M3) |
| C-0001-3 | API ghi của Studio bắt buộc header `X-Studio` và không mở qua CORS | Chống CSRF tới service local | `studio.py`, `creator_main.py` | — |
| C-0001-4 | Không đổi `app.html` trong DR này | App TikTok đang xét duyệt | `app.html` | Khi app đã được duyệt |

supersedes: —

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `docs/specs/architecture/capabilities/video-render.md` | Thêm mục "Duyệt & sửa trên web": luồng, API, quy tắc giọng đọc | [x] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Duyệt bằng Studio thay cho `y/n`; tải ảnh nhân vật trên web | [x] |
| `agent/CLAUDE.md` | Luồng `demo.py` (bước duyệt), lệnh chạy Studio | [x] |
| `TODO.md` | Ghi việc đã xong + quyết định | [x] |
| `.env.example` | `APPROVAL_MODE` | [x] |

## File code thay đổi

- [x] `demo.py`: `tts_provider`/`audio_line`, `revoice_changed`, `--render-only`, `--approve`, `--revoice-all`, `APPROVAL_MODE`
- [x] `backend/app/api/studio.py` (mới)
- [x] `backend/app/creator_main.py`: router + `/studio`
- [x] `backend/app/web/studio.html` (mới)
- [x] `scripts/mo-studio.command` (mới)
- [x] `backend/app/core/config.py`: thêm `DRIVE_FOLDER_ID`, `TTS_PROVIDER` (chỉ để trang biết có Drive và đoán giọng cho thư mục cũ)
- [x] `.gitignore`: `storage/studio-logs/`
- Không đổi: `app.html`, `api/creator.py`, `dashboard/` (Streamlit để nguyên, sẽ xoá ở việc riêng)

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: code

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1 | Tạo video mới, `APPROVAL_MODE` không đặt | Không hỏi `y/n`. Kết quả `status=review`, thư mục giữ lại, chưa lên Drive | Đọc code + chạy `finish` trên bản sao |
| D-2 | Sửa caption/hashtag rồi Lưu | `script.json` đổi, `video.mp4` không đổi (mtime giữ nguyên) | TestClient |
| D-3 | Sửa hook/chữ cảnh/giá rồi Dựng lại | Video mới, không file audio nào bị tạo lại | Chạy thật (edge) |
| D-4 | Sửa 1 lời đọc, video `tts_provider=edge` | Chỉ `audio_i` của câu đó đổi, `audio_line` cập nhật | Chạy thật |
| D-5 | Sửa lời đọc, video Gemini, Gemini lỗi | Không audio nào đổi, job báo lỗi tiếng Việt kèm gợi ý dùng edge | Giả lập lỗi (key sai) |
| D-6 | `--revoice-all edge` | Đọc lại tất cả câu bằng edge, `tts_provider=edge` | Chạy thật |
| D-7 | Tải ảnh cảnh story / ảnh sản phẩm | Lưu `canh_N.<ext>` / `anh_sp_k.<ext>`. File không phải ảnh bị từ chối (400) | TestClient |
| D-8 | Thư mục `needs_images` được tải đủ ảnh rồi dựng lại | `prompts.txt` bị xoá, nhãn chuyển sang "Chờ duyệt" | Chạy thật |
| D-9 | Duyệt (không có Drive/Sheet) | `post.txt` được ghi, job báo xong | Chạy thật |
| D-10 | Request ghi không có `X-Studio` / tên thư mục lạ / có 1 job đang chạy | 403 / 404 / 409 | TestClient |
| D-11 | Thư mục bài tập không có `product.json` | Hiện "Chỉ xem", các API ghi trả 409 | TestClient |
| D-12 | Hồi quy: `--rerender`, `--skip-approval`, `APPROVAL_MODE=terminal`, `app.html` + `/api/creator` | Hành vi như cũ | Đọc diff + gọi `/api/creator/videos` |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | `video-render.md` | Thêm | Có mục Studio, khớp API thật | Xem diff |
| DD-2 | Hướng dẫn vận hành | Sửa | Không còn bước gõ `y/n`; có cách mở Studio bằng bấm đúp | Xem diff |
| DD-3 | `agent/CLAUDE.md`, `TODO.md`, `.env.example` | Đồng bộ | Khớp với code | Đối chiếu chéo |

### Kiểm tra E2E

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| V-1 | Mở Studio | Chạy service, mở `/studio` | Danh sách video hiện có nhãn | ✅ Bấm đúp `mo-studio.command` → service lên, `/studio` 200, danh sách 3 video có nhãn Chờ duyệt / Đã duyệt / Chỉ xem | 2026-11-12 |
| V-2 | Sửa → dựng lại → xem | Dùng bản sao thư mục, sửa 1 câu | Video mới phát được, câu mới được đọc | ✅ Chỉ `audio_2.mp3` tạo lại (edge), video dựng lại. Khung hình kiểm bằng ảnh: hook mới, chữ cảnh mới, ảnh tải lên. ⚠️ Chưa nghe bằng tai | 2026-11-12 |
| V-3 | Duyệt | Bấm Duyệt trên bản sao | `post.txt` có caption mới | ✅ (qua API `approve`, không Drive/Sheet) | 2026-11-12 |
| V-4 | MKTG | Chụp màn hình desktop + mobile | Không có chữ kỹ thuật (JSON, segment, mtime). Nút chính rõ ràng | ✅ Sau 4 chỉnh sửa (xem Review M-1…M-4). Chỉ còn log kỹ thuật nằm trong mục gập "Xem chi tiết kỹ thuật" | 2026-11-12 |

### Cổng chất lượng

- [x] Đã kiểm hết bảng quyết định
- [x] Không có hồi quy
- [x] Không vi phạm ràng buộc hiện có
- [x] Xong mọi việc trong kế hoạch
- [x] Đã cập nhật tài liệu SSoT

---

## Kết quả

### Triển khai

| # | Việc | Kết quả | Ghi chú |
|---|------|---------|---------|
| 1 | `demo.py` | ✅ | `generate_voiceovers` trả về bộ giọng và ghi `audio_line`; `revoice_changed()` (tạo hết file `_new_audio_i.mp3` rồi mới thay); `render_only()`, `approve()`, `publish()`, `render_and_check()`; `--render-only`, `--approve`, `--revoice-all`; `APPROVAL_MODE`; `set_sheet_status()` thay `mark_sheet_done()` (thêm `review`); `_load_image` nhận ảnh nằm trong thư mục video. Exit code: 3 = đọc lại lỗi, 4 = chưa đủ điều kiện duyệt |
| 2 | `api/studio.py` | ✅ | 9 endpoint, xem `video-render.md` § Studio |
| 3 | `creator_main.py` | ✅ | Gắn router, `GET /studio`, `GET /` → `/studio`. CORS giữ nguyên |
| 4 | `studio.html` | ✅ | Một file, không thư viện ngoài, sáng/tối, mobile. Mở thẳng một video bằng `/studio#<thư mục>` |
| 5 | `mo-studio.command` | ✅ | Service đang chạy thì chỉ mở trình duyệt |
| 9 | Tài liệu | ✅ | Xem §Tài liệu SSoT |

**Khác với thiết kế ban đầu:**

| Điểm | Thiết kế | Thực tế | Lý do |
|------|----------|---------|-------|
| Log job | `<dir>/studio.log` | `storage/studio-logs/<thư mục>.log` | Log trong thư mục video sẽ bị tải lên Drive, và mất khi duyệt xong thư mục bị xoá |
| Phát hiện "cần dựng lại" | Không nêu | `script.json → needs_render` do Studio đặt, `render_and_check` xoá | Chặn duyệt video cũ hơn chỗ đã sửa (cả trên web và `--approve`) |
| `--render-only` | Không nêu | Xoá `post.txt` cũ | Video đã duyệt mà dựng lại thì phải duyệt lại, nhãn không còn "Đã duyệt" |
| Upload ảnh | Không nêu cách gửi | Body là bytes, `target`/`index` trên query | `python-multipart` chưa cài trong `.venv`, tránh thêm phụ thuộc |
| Chống CSRF | Header `X-Studio` | Thêm kiểm Host là `127.0.0.1`/`localhost` | Chặn DNS rebinding (trang lạ trỏ tên miền về 127.0.0.1 thì cùng origin, gửi được header) |
| Nhãn danh sách | Chờ duyệt / Cần ảnh / Chỉ xem | Thêm **Đã duyệt** (có `post.txt`) | Thư mục giữ lại sau khi duyệt (`--keep-local` hoặc không có Drive) |

### Review

| # | Góp ý | Xử lý |
|---|-------|-------|
| R-a | Thư mục đã duyệt mà dựng lại vẫn mang nhãn "Đã duyệt" | `--render-only` xoá `post.txt` |
| R-b | Sửa JSON hoặc tải ảnh khi job đang chạy sẽ bị `--render-only` ghi đè lúc kết thúc | PUT / upload trả 409 khi có job |
| R-c | Đường dẫn: tên thư mục chỉ nhận nếu có trong danh sách; file ảnh phục vụ qua regex `canh_N` / `anh_sp_N` / `img_N`; ảnh lưu bằng tên server đặt | Đạt, có test |
| R-d | Ghi `script.json` / `product.json` qua file tạm rồi `replace` | Tránh file hỏng khi lỗi giữa chừng |
| R-e | Hồi quy CLI: `run_sheet` dùng bảng `SHEET_STATUS`; `--rerender` giờ cập nhật Sheet cả `needs_images`/`review` (trước chỉ `done`) | Chủ ý: Sheet khớp trạng thái thư mục |
| M-1 | (MKTG) Thanh nút dưới vẫn hiện khi chưa chọn video (`display:flex` đè `hidden`) | Sửa CSS |
| M-2 | (MKTG) Video bài tập hiện tên thư mục `20261101_090000_bai-tap` | Dùng dòng đầu caption, hoặc tên thư mục bỏ ngày giờ |
| M-3 | (MKTG) Thông báo duyệt nhắc tên file `post.txt` | Đổi thành "chữ đăng kèm đã lưu cạnh video" |
| M-4 | (MKTG) Khung video đen trước khi bấm phát | Hiện khung hình đầu (`#t=0.1`) |

### Test

Chạy trên **bản sao** 3 thư mục (`bot-me-den` simple, `omniear` story, 1 thư mục bài tập giả) trong worktree, không `.env` (edge-tts, không Drive, không Sheet). TestClient + `demo.py` chạy thật: **48/48 đạt**.

| # | Kết quả |
|---|---------|
| D-1 | ✅ `finish()` không đặt `APPROVAL_MODE` → `review`, thư mục còn, không có `post.txt` |
| D-2 | ✅ Caption/hashtag lưu, hashtag chuẩn hoá và bỏ trùng, `video.mp4` mtime giữ nguyên, không `needs_render` |
| D-3 | ✅ Hook + chữ cảnh + giá + ảnh SP → dựng lại, mtime mọi `audio_*.mp3` giữ nguyên |
| D-4 | ✅ Chỉ `audio_2.mp3` đổi, `audio_line` cập nhật, thư mục cũ được ghi `audio_line` cũ trước khi sửa và `tts_provider=edge` sau khi dựng |
| D-5 | ✅ `tts_provider=gemini` + key sai → exit 3, `error_kind=revoice`, audio và video không đổi, không còn file tạm |
| D-6 | ✅ `--revoice-all edge`: cả 4 audio tạo lại, `tts_provider=edge`, `audio_line == line` |
| D-7 | ✅ Ảnh SP → `anh_sp_1.png` + `product.json`; ảnh cảnh → `canh_5.png`; file không phải ảnh → 400; cảnh không phải story / vị trí sai → 400 |
| D-8 | ✅ Xoá `canh_5.png` → dựng → `needs_images` + gợi ý tạo ảnh cảnh 5; tải ảnh → dựng → `prompts.txt` mất, nhãn Chờ duyệt |
| D-9 | ✅ `post.txt` có caption mới, job `done`, thư mục giữ lại |
| D-10 | ✅ Không header → 403; Host lạ → 403; thư mục lạ / `../` → 404; job thứ hai → 409; PUT khi job chạy → 409; preflight CORS không cho `x-studio` |
| D-11 | ✅ Thư mục bài tập: "Chỉ xem", PUT/render → 409 |
| D-12 | ✅ `--rerender --skip-approval` → `ready_for_manual_upload`; `APPROVAL_MODE=terminal` → hỏi y/n (n → `rejected`, y → `ready_for_manual_upload`); `--approve` khi `needs_render` → exit 4; `/api/creator/videos` vẫn trả danh sách; `app.html` không đổi |

Chưa kiểm: Drive và Sheet thật (cố ý tắt khi test); giọng Gemini thật khi đọc lại (chỉ test nhánh lỗi, để không tốn quota); nghe bằng tai câu đọc lại.

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| Đánh giá trước đó | Trao đổi 2026-11-12: "Trang 2: Xem video, sửa, tạo lại" |
| Code hiện có | `demo.py` (`finish`, `rerender`, `approval_step`), `backend/app/api/creator.py` |
| Công cụ | `workflow_step.py` không chạy được (thiếu module `automation_engine`), các phase được điều phối thủ công |
