# DR-0008: Travel P1 — kiểm số chặt hơn, mã thoát riêng cho fact quá hạn, các chốt P1

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã duyệt | 2026-11-16 | Claude (BA) | chungkhoantony1983 (đồng ý toàn bộ 8 đề xuất, 2026-11-16) |

Capability: `travel-content` · Nhánh: `feat/travel-p1` · supersedes: **DR-0002** (chỉ C-0002-1, C-0002-2, dòng D-11; phần còn lại của DR-0002 giữ nguyên)

> **Vì sao số 0008**: số 0002 đến 0007 đã bị các nhánh khác dùng. DR này là bản bổ sung cho DR-0002, không thay toàn bộ.

## Vấn đề

Khi viết chi tiết thực thi P1 (review Tech Lead 2026-11-16), hai chỗ của DR-0002 không dùng được:

1. **C-0002-2** nói `--approve` thoát mã 4 khi fact quá hạn. Studio đang hiểu mã 4 là "cần dựng lại / thiếu ảnh": người vận hành bấm Dựng lại mãi không hết lỗi.
2. **C-0002-1** chỉ kiểm số trong `line` / `text`. Số vẫn lọt qua `subs` (phụ đề VI), `hook`, `caption`, là chỗ người xem đọc và có thể sai visa / phí.

## Quyết định

| # | Quyết định | Thay cho |
|---|-----------|----------|
| 1 | Fact `volatile` quá 30 ngày: `--approve` **chặn bằng mã thoát 6** (`facts_stale`). `--render-only` chỉ **cảnh báo** trong log, vẫn dựng. Thêm `demo.py --travel --refresh-facts DIR` (tải lại trang, kiểm lại quote, cập nhật `checked_on`) | C-0002-2, D-11 |
| 2 | Kiểm số cả trên `subs.*`, `hook`, `caption` (ngoài `line`, `text`), so theo **giá trị chuẩn hoá** (`150,000` = `150.000`; `US$25` = `$25` = `25 USD`). Số viết bằng chữ ("twenty-five") coi là lỗi | C-0002-1 |
| 3 | P1 chỉ dùng **edge-tts**. Gemini cho travel làm sau khi nhánh gemini-quota merge, và phải đi qua `quota_reserve` | (làm rõ DR-0002 § Giọng) |
| 4 | Không upload `clip_*` / `img_*` lên Drive (đã có link trang gốc trong `credits.txt`) | (làm rõ DR-0002 § Luồng) |

Quyết định vận hành kèm theo (người dùng chốt 2026-11-16, không đổi ràng buộc): hàng hộ chiếu chỉ dùng trang visa-requirements; hàng tàu Bắc-Nam chỉ dùng FAQ (đã cập nhật `seed-questions.csv`, hết `skip`); cách đọc tên Việt do người dùng nghe video phở (V-2) rồi sửa `vn.json`; video visa người Mỹ (V-1) do người vận hành chép `facts_manual` tay từ travel.state.gov; Studio làm cuối nhánh, logic ở `studio_travel.py`.

## Chi phí (P02)

Mọi việc ở DR này $0: kiểm số và kiểm hạn là code thuần; `--refresh-facts` chỉ tải trang (không gọi Groq, trừ khi phải viết lại cảnh; khi đó 1 lượt Groq free). Không tốn lượt Gemini TTS (P1 dùng edge-tts).

## Ràng buộc mới (thay ràng buộc cũ)

| Mã | Nội dung | Thay |
|----|----------|------|
| C-0008-1 | Mọi con số (tiền, ngày, %, số lượng) trong `line`, `text`, `subs.*`, `hook`, `caption` phải có (cùng giá trị sau chuẩn hoá) trong `quote` của fact được trích. Số trong `subs` của cảnh phải nằm trong quote fact của cảnh đó. Kiểm trước TTS và trước mỗi lần dựng lại. Sai → mã thoát 5 (`fact_check`), không đổi audio, không dựng | C-0002-1 |
| C-0008-2 | Fact `volatile` có `checked_on` > 30 ngày: `--approve` thoát mã **6** (`facts_stale`) với thông báo tiếng Việt chỉ lệnh `--refresh-facts`; `--render-only` dựng được và chỉ cảnh báo. Màn hình cuối và caption vẫn ghi nguồn + tháng năm. Mã 4 giữ nguyên nghĩa cũ | C-0002-2 |

**Hệ quả bổ sung khi code (ghi 2026-11-16, không đổi quyết định):**
- Mã thoát **7** (`drive_failed`, dòng `[DRIVE_FAILED]`) dành cho tải lên Drive lỗi khi `--approve` (luồng travel): không `done`, thư mục còn.
- `--refresh-facts --confirm <ids>` để lại dấu vết kiểm tay: `confirmed_by_hand` (giờ ISO) trong `facts.json` và một dòng trong `refresh.log` (không tải lên Drive; bản `facts.json` trên Drive giữ `confirmed_by_hand`).

## Bảng quyết định (kiểm được)

| # | Điều kiện đầu vào | Kết quả mong đợi | Cách kiểm |
|---|-------------------|------------------|-----------|
| D-11 | `--approve`, fact volatile `checked_on` 31 ngày trước | exit 6, thông báo tiếng Việt nêu `--refresh-facts`; không upload, status không đổi | Sửa ngày trên bản sao |
| D-11a | `--render-only` cùng thư mục | Dựng xong (exit 0), log có cảnh báo fact quá hạn | Như trên |
| D-11b | `--refresh-facts`, quote còn / mất trên trang | Còn: `checked_on` = hôm nay, duyệt được. Mất: bỏ fact; thiếu fact cho cảnh `answer` → `needs_sources` | Trang giả lập |
| D-12 | `subs.vi` của cảnh có số `30` mà quote fact cảnh đó chỉ có `25` | exit 5, log nêu cảnh + số; audio không đổi | Sửa tay `script.json` bản sao |
| D-12a | `caption` / `hook` chứa số không có trong quote nào | exit 5 như trên | Như trên |
| D-12b | `line` ghi `$25`, quote ghi `25 USD`; `150,000` vs `150.000` | Qua kiểm | Chạy kiểm trên bản sao |
| D-12c | `line` ghi "twenty-five" | Lỗi, Groq viết lại 1 lần; vẫn sai → `needs_sources` | Groq giả lập bằng file JSON |
| D-13 | Hồi quy: video sản phẩm / bài tập chạy `--approve`, `--render-only` | Không đổi hành vi, mã 4 vẫn nghĩa cũ | Chạy bản sao |

## E2E

| # | Kịch bản | Mong đợi |
|---|----------|----------|
| E-1 | Video visa, fact checked 31 ngày trước: Studio bấm Duyệt | Studio báo câu tiếng Việt riêng ("dữ kiện quá hạn, chạy làm mới"), không phải "cần dựng lại" |
| E-2 | Sau `--refresh-facts` thành công, duyệt lại | Duyệt được, post.txt ghi tháng năm mới |

## Liên kết spec

`docs/specs/architecture/capabilities/travel-content.md` § Chi tiết thực thi P1: **T-4** (kiểm số), **T-5** (mã 5, sửa lời trên Studio), **T-6** (mã 6, `--refresh-facts`), T-8 (Drive, quyết định 4).

## Tài liệu SSoT bị ảnh hưởng

`travel-content.md` (đã cập nhật tham chiếu), `docs/operations/huong-dan-van-hanh-hang-ngay.md` (sau khi Dev xong: lỗi mã 5, 6, lệnh làm mới), `TODO.md` M2d (đã cập nhật), `.claude/CLAUDE.md` (cờ `--refresh-facts`, sau khi Dev xong).

## Kế hoạch theo vai trò

| Vai trò | Việc |
|---------|------|
| BA | DR này, spec, TODO (xong); hướng dẫn vận hành sau khi Dev xong |
| Dev | `travel.py`: kiểm số chuẩn hoá (T-4), mã 5 và 6, `--refresh-facts` (T-6); `demo.py` cờ; `studio_travel.py` + `ERROR_KINDS[5]`, `[6]` (T-5), làm cuối nhánh |
| Reviewer | Soát diff so với C-0008-1/2; mã 4 không đổi nghĩa |
| Tester | D-11 đến D-13, E-1, E-2 trên bản sao, edge-tts, không Gemini/Drive/Sheet thật |
| Tech Lead | Đã review 2026-11-16; soát lại phần `--refresh-facts` (tải trang qua T-1) |
| MKTG | Review Studio: câu báo mã 5, 6 người vận hành có hiểu không |

## Kết quả

> **Phạm vi**: mục này cũng ghi kết quả P1 của DR-0002 (DR-0002 đã khoá, không sửa). Nhánh `feat/travel-p1`, 2026-11-16/17. Quy trình: Dev A (`travel.py`, CLI, Drive) + Dev B (Studio) → kiểm vòng 1 (Reviewer, Tester, Techlead, Marketing) → sửa → kiểm vòng 2 → sửa → kiểm xác nhận cuối (Reviewer, Tester). Chi phí kiểm: $0, không dùng lượt Gemini; Groq, nguồn, Drive, Sheet giả lập, edge-tts thật.

### Việc đã làm

Code P1 xong (research → kiểm nguồn → script EN/VI → clip → edge-tts → dựng; Studio nhận thư mục travel; `--refresh-facts [--confirm]`; mã thoát 5/6/7). Chưa chạy với dữ liệu thật (xem "Người dùng phải tự kiểm").

### Reviewer

- Vòng 1: 2 Chặn (#1 `--refresh-facts` không làm mới được dữ kiện nhập tay / nguồn `auto_fetch:false`; #2 ngưỡng quote 30 so với 10 ký tự cho dữ kiện nhập tay), 6 Nên sửa (#3 kiểm số theo đơn vị; #4 số viết bằng chữ ở hook/caption/subs; #5 Studio `_days_old` None; #6 Drive lỗi vẫn ghi done; #7 download_media theo redirect; #8 hook so với segments[0].line) + gợi ý. Đã sửa hết.
- Vòng 2: xác nhận 2 Chặn vòng 1 đã sửa; 1 Chặn mới (A: câu hỏi có số viết bằng chữ như "Is two days enough in Hanoi?" luôn ra needs_sources), Nên sửa B (million vs number_words), C (skip_approval + approve lỗi → status review), D (Drive duyệt lại tải trùng file), E (Studio confirm_ids cho nguồn auto_fetch:false), gợi ý F–J. Đã sửa hết.
- Cuối: **Chặn 0, Nên sửa 0.** A–J đều đúng. Gợi ý còn lại (không chặn, ghi vào `TODO.md`): (1) Studio có thể báo "N dữ kiện bị ẩn" khi snapshot thiếu danh sách nguồn dù chúng vẫn hiện (không link); (2) hook dài cắt bằng "…" có thể kết thúc giữa cụm ("…from the…"); (3) tiền tố `refresh.` bỏ qua upload Drive hiện chỉ khớp `refresh.log`.

### Tech Lead

- Vòng 1 (review DR): 4 Chặn, 10 Nên sửa, 7 Gợi ý, đã đưa vào spec T-1…T-20 (fetch_source an toàn, mã thoát 5/6, dựng riêng không đảo ngược clip, TTS riêng, 2 chỗ móc `demo.py`, Studio ở file riêng…). Bug có sẵn trên `main`: `--keep-local` bị bỏ qua với `--exercise` → issue #15.
- Vòng 2 (review diff): 0 Chặn. Nên sửa: N1 dấu vết `--confirm` (đã làm: `confirmed_by_hand` + `refresh.log`); N7 file chưa theo dõi bởi git (`travel.py`, `studio_travel.py`, `defaults.json`, DR-0008) → **phải `git add -A` khi commit**. Gợi ý N2–N6, N8 (shell-quote id, trùng tên thư mục theo giây, mã thoát Drive lỗi trùng mã 1 → đổi 7, Studio bỏ cả dữ kiện khi thiếu nguồn, status `needs_sources` không tự mở lại, `_get_json` không giới hạn): đã sửa N2/N3/N4/N5 và `_get_json` 2 MB; N6 chấp nhận.
- Rủi ro merge: `studio.html` (cả 3 nhánh), `studio.py`, `demo.py` main(), `product_sources.py`, `.gitignore`, `TODO.md`.

### Tester (nguyên văn báo cáo)

Vòng cuối: toàn bộ ca PASS, không có bug nặng. Tổng khoảng 200+ phép kiểm tự động qua các vòng.

| Nhóm | Kết quả |
|------|---------|
| D-1…D-16 (DR-0002), D-11…D-13, E-1, E-2 (DR-0008), V-1, V-2 | PASS (phần nghe giọng/xem clip thật: cần người kiểm) |
| BUG-1: Studio PUT video có hook 7/8/10 từ → 200; 11 từ → 400; cảnh khác 7 từ → 400 | PASS (đã sửa, hook 10 từ) |
| Hook + số viết bằng chữ trong câu hỏi; "1.5 million"; "Two million" bị báo | PASS |
| `--skip-approval` approve lỗi (5/6/7) → Sheet `review`; status `skip` đặt tay không bị ghi đè | PASS |
| Drive lỗi: exit 7, 1 dòng `[DRIVE_FAILED]`, thư mục + post.txt giữ, Sheet không done; Studio `error_kind=drive_failed`; duyệt lại thay file cùng tên không tải trùng; `refresh.log`/`clip_*` không lên Drive | PASS |
| `--confirm`: manual / auto_fetch:false / domain đã bỏ khỏi hồ sơ → ghi `confirmed_by_hand` + `refresh.log`; id sai → exit 1 không ghi; thiếu `--refresh-facts` → argparse exit 2; id có ký tự shell bị bỏ | PASS |
| Luồng quá hạn → exit 6 → `--confirm` → approve (4) → render-only → approve (0) | PASS |
| run_row trùng tên thư mục (hậu tố -2), defaults.json hỏng → lỗi tiếng Việt, TravelSheet.find ưu tiên khớp chính xác | PASS |
| Kiểm số 40 câu: 38 đúng ý; 2 chấp nhận nhầm có chủ đích ("90 pages", "25 stars": đơn vị ngoài danh sách hồ sơ); "fifty-fifty" bị báo nhầm là số viết bằng chữ | giới hạn đã ghi trong spec H-1 |
| Studio 390 px / 1280 px (Chrome headless, ảnh chụp có khối lệnh `--confirm`): lệnh tự xuống dòng, không thấy cắt nội dung; chưa đo scrollWidth | PASS (xem ảnh) |
| Hồi quy: sản phẩm (PUT/render/approve, exit 4), thư mục bài tập (chỉ xem, 409), `demo.py --help`, /api/creator/videos, X-Studio / CORS / DNS rebinding / path traversal | 59/59 PASS |
| E2E dựng 2 video (nguồn 1080p; câu hỏi 14 từ) | PASS, review, 12–15 s dựng |
| RAM dựng | Đo riêng từng ffmpeg: đỉnh 509 MB (clip 4K), 367 MB (1080p), 303 MB (ảnh tĩnh); script E2E đo 3 GB là do sinh clip mẫu 4K trong cùng lệnh, không phải bước dựng (cần đo lại trên máy thật nếu muốn chắc) |

Ghi chú UX nhỏ (không chặn): sau khi Drive lỗi, danh sách Studio vẫn gắn nhãn "Đã duyệt" vì `_label()` chỉ dựa vào `post.txt` (ghi trước khi upload); banner vẫn đúng và nút Duyệt lại bấm được.

### Marketing

- Vòng 1, phần A (UX người vận hành): 2 Chặn (A1 chưa có hướng dẫn travel; A2 lệnh làm mới bắt mở Terminal, đường dẫn dễ sai), Nên sửa A3–A7 (banner mã 5/6, cảnh báo quá hạn sau khi bấm Duyệt, thông tin trước Duyệt, dữ kiện bị ẩn). Đã áp dụng: mục 4c và dòng lỗi mục 6 trong hướng dẫn vận hành, lệnh `cd` sẵn trong khung lệnh.
- Vòng 1, phần B (video mẫu giả, chỉ đánh giá hình thức): 0 Chặn; Nên sửa B1–B8 (hook chữ lớn không phải câu hỏi, câu "Phở lovers…" lạc đề không nguồn, ghi công gần mép, caption "Many travelers", câu >15 từ). Đã đưa thành quy tắc nội dung: hook = câu hỏi ≤10 từ; câu trả lời chỉ nói điều có trong dữ kiện và ≤15 từ/câu; dòng ghi công trong vùng an toàn. Quy tắc caption chỉ nằm trong prompt, không có code kiểm.
- Vòng 2: A1–A7 đều đã giải quyết, 0 Chặn. Nên sửa: tràn ngang ở 390 px (đã sửa), mục 4c chưa nói chạy lệnh ở đâu (đã sửa). Gợi ý đã làm: câu banner "dữ kiện bị ẩn", "mất khoảng 1 phút", tên dữ kiện cạnh id, dòng mục 6, mục (e) checklist.

### Bug đã ghi issue

- #15: `--keep-local` bị bỏ qua khi chạy `demo.py --exercise` (module `demo` nạp 2 lần). Có sẵn trên `main`, chưa sửa.
- #16: upload Drive lỗi nhưng luồng **sản phẩm** vẫn ghi `status=done`. Luồng travel đã đúng (exit 7). Chưa sửa.

### Rủi ro chấp nhận

- DNS rebinding / IP nội bộ khi tải trang nguồn: không kiểm. Rủi ro thấp (khoảng 12 domain allowlist, https:443, nội dung chỉ đi vào Groq).
- Kiểm số theo đơn vị là gần đúng (spec H-1): chấp nhận nhầm "90 pages", "25 stars" (đơn vị ngoài danh sách hồ sơ), báo nhầm "fifty-fifty". Người duyệt vẫn phải đối chiếu (checklist c).
- Quy tắc caption (không hashtag, không bịa) chỉ nằm trong prompt, code không kiểm. Người duyệt kiểm checklist (f).
- Chưa đo lại RAM dựng trên máy thật (số đo ở bảng Tester là trong môi trường kiểm).

### Người dùng phải tự kiểm

1. Dán `content/travel/seed-questions.csv` vào tab `Travel` (Chèn các hàng mới vào trang tính hiện tại).
2. Chạy video thật đầu tiên (`demo.py --travel --sheet`), nghe giọng edge-tts: "Phở", "Hội An", "Hà Nội"; sửa `pronunciations` trong `content/travel/destinations/vn.json` nếu sai.
3. Video visa người Mỹ: tự mở travel.state.gov chép câu về visa vào cột `facts_manual` (`claim | quote | url`, quote nguyên văn).
4. Xem Studio thật trên trình duyệt (banner mã 5/6/7, chip dữ kiện, nhãn "nhập tay", credits từng cảnh) và trên điện thoại.
5. Kiểm clip thật đúng địa danh, phụ đề tiếng Việt do Groq thật dịch, độ tự nhiên của tiếng Anh. Pixabay/Pexels/Wikimedia API thật chưa được gọi (cần `PEXELS_API_KEY` nếu muốn Pexels).
6. Thử `--confirm` trên video thật sau khi tự mở trang nguồn chính thức kiểm lại.
7. Drive thật và Sheet thật (mới chạy giả lập).

### Thứ tự merge và kiểm sau merge (Tech Lead)

- Thứ tự: `feat/studio-create-video` → `feat/gemini-quota` → `feat/travel-p1` (rebase sau cùng). File DR đánh số `DR-0002-…` của nhánh gemini-quota trùng số với DR-0002 travel: **nhánh gemini-quota phải tự đổi số** trước khi merge.
- Khi commit nhánh này: `git add -A` (có file mới chưa theo dõi: `travel.py`, `studio_travel.py`, `defaults.json`, DR-0008).
- Sau mỗi merge chạy: `.venv/bin/python -c "import travel, demo"`, `demo.py --help`, GET `/api/studio/videos`, `--render-only` trên 1 thư mục sản phẩm + 1 thư mục travel, kiểm `ERROR_KINDS` đủ 3, 4, 5, 6, 7 và mã của gemini-quota.
