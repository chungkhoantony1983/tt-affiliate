# DR-0014: Studio tạo video chủ đề khác và duyệt/sửa bố cục trước khi dựng

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã duyệt (2026-11-25, kèm trả lời Q-1…Q-6 ở § 11). PR 1 (sản phẩm + chủ đề chung) đã code và kiểm, xem § 12; phần du lịch để PR sau (Q-5) | 2026-11-25 | Claude (BA) | chungkhoantony1983 (2026-11-25) |

Capability: `video-render` (Studio), `script-gen`, `travel-content` · Nhánh: `feat/issue-38-studio-topic-layout` · GitHub issue: #38 · Cấp: L

Vai trò: **BA** = `ba` · **Dev** = `dev` · **Reviewer** = `reviewer` · **Tech Lead** = `techlead` (chạm `api/studio.py`, subprocess, khoá job, mã thoát, đổi tên file audio) · **Tester** = `tester` · **MKTG** = `marketing` (giao diện, chữ cho người vận hành).

> **Số DR**: quét mọi ref local/remote và mọi worktree ngày 2026-11-25 (fetch thành công), số lớn nhất là DR-0013 nên dùng DR-0014.
>
> **DR bị mở rộng**: **DR-0011** (đã duyệt, **chưa có dòng code nào trên `main`**: `grep` không thấy `stage`, `script_review`, `--continue`, `REVIEW_GATES` trong `demo.py`, `travel.py`, `studio.py`). DR này làm phần "cổng kịch bản" (`script_review`) của DR-0011 cho video tạo từ Studio, và nới hai chỗ DR-0011 đã cấm (xem § 7, dòng `supersedes`). **DR-0007** (form Tạo video mới) được mở rộng thêm loại video. **DR-0001** đổi một nhãn danh sách ("Chờ duyệt" → "Chờ duyệt đăng"). **DR-0010** (travel v2) và **DR-0009** (cắt clip) vẫn ở trạng thái Đề xuất, không mâu thuẫn, xem R-3.

---

## 1. Bối cảnh

### Vấn đề gốc (issue #38, người dùng 2026-11-25)

1. Studio chỉ tạo được video **sản phẩm** từ link TikTok Shop / dòng Sheet. Video chủ đề khác (bài tập, du lịch Việt Nam) phải ra lệnh terminal hoặc nhờ Claude desktop. Người vận hành không rành kỹ thuật nên bị kẹt.
2. Sau khi tạo, kịch bản bị **cố định số cảnh**: Studio chỉ sửa được câu đọc và chữ trên cảnh. Khi video "sai hẳn yêu cầu" (sai ý, thiếu ý, thừa cảnh), cách duy nhất là tạo lại từ đầu: tốn thêm lượt Groq, lượt Gemini TTS và thời gian dựng.

Người được lợi: người vận hành (tự làm video chủ đề trên Studio, sửa đúng chỗ sai), và kênh (ít video sai ý bị đăng).

### Đã đọc trong code (`origin/main` tại `b8e0fef`, đã có #35, #37)

| Chỗ | Hiện trạng | Hệ quả cho DR này |
|-----|-----------|-------------------|
| `demo.py run_one` (dòng 1742) | `generate_script` (Groq) → `generate_voiceovers` → `generate_story_images` → `save_script` → `finish` (dựng ngay). Không có chỗ dừng trước giọng | Không có bước bố cục; giọng đọc tốn trước khi người thấy kịch bản |
| `demo.py run_create` (1616) | Nhận `--create-json` từ Studio, chỉ cho sản phẩm (bắt buộc `name`), gọi `run_one` | Chỗ thêm nhánh "chủ đề" |
| `demo.py generate_script` (124) | Groq trả `segments[]` có `kind` story / product / cta, `speaker`, `line`, `text`, `image_prompt`. Thử tối đa 3 lần | Không có trường "ý cảnh"; không nhận sườn |
| `demo.py generate_voiceovers` (825), `revoice_changed` (969) | Ghi `audio_{i}.mp3` **theo vị trí** `i` và lưu `seg["audio_path"]`; `revoice_changed` chỉ đọc lại cảnh có `line != audio_line`, làm file tạm `_new_audio_{i}` rồi mới thay (lỗi thì không đổi file nào, C-0001-1) | Thêm/xoá/đổi chỗ cảnh làm lệch `audio_{i}` ↔ `segments[i]` |
| `demo.py render_video` (1284, 1327) | Audio lấy từ `Path(seg["audio_path"]).name`; ảnh story lấy `canh_{i+1}.*` **theo vị trí**; ảnh cảnh product xoay vòng theo thứ tự `product.images`; cảnh `cta` vẽ "Video có gắn link tiếp thị liên kết" + "BẤM GIỎ HÀNG VÀNG" | Video chủ đề không được dùng cảnh `cta` này |
| `demo.py save_script` (1772), ghi `product.json` (1759) | `write_text` ghi đè trực tiếp (không qua file tạm) | `script.json` sắp chứa `stage`/`sid`: hỏng nửa chừng → `_read_json` trả `{}` → thư mục biến khỏi Studio (Tech Lead #3) |
| `capcut_export.py` (79, 127), `scripts/audio_seams.py` (163, 202), `travel.py` (1666, 1686) | Đọc `audio_{i}.mp3` theo vị trí | Bất biến "file thứ i thuộc cảnh thứ i" phải giữ sau mọi lần đổi bố cục (C-0014-1) |
| `api/studio.py save_video` (515) | `PUT` chỉ sửa `line`/`text`/hook/giá/caption; **400 "Số cảnh không khớp"** nếu số cảnh khác | Chỗ bị nới cho bước bố cục |
| `api/studio.py upload_image` (587), `_scene_image` (204) | Ghi/đọc `canh_{index+1}` theo vị trí | Đang sửa bố cục mà tải ảnh thì ảnh rơi sai cảnh (Tech Lead #5) |
| `api/studio.py _folders` (146) | Chỉ liệt kê thư mục có `video.mp4` | Thư mục đang ở bước bố cục (chưa dựng) không hiện |
| `api/studio.py _no_job_or_409` (302) | Gọi **ngoài** `_job_lock` ở các API ghi (519, 861, 888, 955); chỉ `_start_job` cầm khoá | `PUT` có thể ghi `script.json` đúng lúc `--continue` đang đọc (Tech Lead #7) |
| `api/studio.py ERROR_KINDS` (46) | 3, 4, 5, 6, 7 | Thêm 9, 12 |
| `api/studio.py` `Popen` (316, 336) | Không giới hạn thời gian, không có nút huỷ | Nợ kỹ thuật, ghi `TODO.md` § 5 |
| `drive_upload.py` (27) | `SKIP_PREFIXES = ("_scene_",)` | File tạm mới (`_bo_`, `_mv_`, `_new_audio_`) và bản sao lưu sẽ bị tải lên Drive nếu không sửa |
| `travel.py run_row` (1943), `_run_row_body` (1999) | Nhận 1 dòng Sheet/CSV (`question`, `destination`, `audience`, `pillar`, `source_urls`, `facts_manual`, `notes`) → research → `write_and_check` → `build_media` → `voice_segments` (edge) → `render` | Có điểm dừng tự nhiên sau `write_and_check`. Chưa nhận dữ liệu từ Studio |
| `travel.py check_script` (1002) | Hook đầu, outro cuối; số cảnh answer theo `pillars.json → answer_segments` (hiện 2–3, chỉ khi `strict`); mỗi answer có `fact_ids`; số phải có trong quote (C-0008-1) | Luật bố cục travel đã có, chỉ cần gọi lại |
| `exercise.py` | Lời đọc lấy **nguyên văn giáo trình** (`content/exercise_curriculum.json`), không qua Groq; clip làm tay | "Bát thủ cầm" trong yêu cầu hiểu là **Bát Đoạn Cẩm** (chuỗi `bdc` trong giáo trình). Xem Q-2 |

### Ràng buộc ngoài

- Không đổi `app.html`, scope TikTok (app đang xét duyệt, C-0001-4).
- Shopee tạm dừng. Kênh chưa có quyền affiliate (`TODO.md`), nên video **không bán hàng** (bài tập/mẹo/kiến thức, du lịch) là nội dung đăng được ngay.
- `api/studio.py` chỉ đọc/ghi JSON, ảnh và chạy `demo.py` bằng subprocess (C-0001-2, C-0011-3). API ghi cần `X-Studio: 1` (C-0001-3).

### Chi phí (P02)

| Việc | Công cụ | Chi phí | Nguồn |
|------|---------|---------|-------|
| AI viết kịch bản từ sườn, AI viết lại cảnh / cả kịch bản | Groq (`GROQ_MODEL`) | Free; mỗi lần bấm = 1 lời gọi, tối đa 3 lần thử (như `generate_script`). Hạn mức Groq free: **chưa rõ** | `agent/CLAUDE.md`, `demo.py:172` |
| Travel: đọc nguồn, Groq viết | Groq + tải trang | $0 | `travel.py` |
| Sửa bố cục (sửa, thêm, xoá, đổi chỗ) | Không gọi AI | $0 | — |
| Giọng đọc khi bấm "Dựng video theo bố cục này" lần đầu | Gemini TTS: **1 lượt / cảnh** (`generate_voiceovers` giữ `n = len(segments)` lượt). Free 10 lượt/ngày/model; thiếu lượt → cả video edge-tts $0 | `demo.py:839-845`, `.env.example:29` |
| Giọng khi quay lại bố cục rồi dựng lại | Gemini: **1 lượt / cảnh mới hoặc cảnh đổi lời**; đổi chỗ, xoá cảnh: 0 lượt. Travel: edge-tts, 0 lượt Gemini | `revoice_changed`, DR-0008 |
| Dựng FFmpeg | Máy nhà | $0 | — |

**Lợi ích**: hiện tạo video sản phẩm luôn tốn giọng trước khi người xem kịch bản. Sau DR này, video tạo từ Studio **không tốn lượt Gemini nào** cho tới khi người bấm dựng; video sai thì sửa cảnh sai (vài lượt) thay vì tạo lại (toàn bộ lượt + Groq). Không thêm chi phí trả phí.

---

## 2. Quyết định

> **Thêm bước "Soạn bố cục" (trạng thái `script_review` của DR-0011) cho mọi video tạo từ Studio. Tạo video (sản phẩm; bài tập/mẹo/kiến thức; du lịch) chỉ gọi Groq rồi dừng: chưa đọc giọng, chưa dựng. Trên Studio người vận hành thấy danh sách cảnh, được sửa, thêm, xoá, đổi chỗ, và bấm "AI viết lại" một cảnh hoặc cả kịch bản; bấm "Dựng video theo bố cục này" thì `demo.py --continue` mới đọc giọng (chỉ cảnh mới/đổi lời) và dựng. Video đã dựng, chưa duyệt, có nút "Sửa bố cục" để quay lại bước này. Mỗi cảnh có mã `sid` cố định do máy cấp; file nào thuộc cảnh nào đọc từ `audio_path` của cảnh; chỉ `demo.py`/`travel.py` đổi tên `audio_N`/`canh_N`, có nhật ký đổi tên để làm tiếp được khi bị ngắt. "+ Tạo video mới" có ba ô: Sản phẩm TikTok Shop, Bài tập / mẹo / kiến thức (demo.py, `product.json → kind: "topic"`, không giỏ hàng), Du lịch Việt Nam (travel.py, vẫn bắt buộc nguồn).**

### 2.1 Loại video và nơi xử lý

| Ô trên Studio (chữ hiển thị) | Xử lý bằng | Dữ liệu thư mục | Giọng mặc định |
|------------------------------|-----------|-----------------|----------------|
| **Sản phẩm TikTok Shop** (như cũ) | `demo.py --create-json` → `run_create` | `product.json` (như cũ) | Như cũ (Gemini nếu có key, chọn "miễn phí" được, DR-0013) |
| **Bài tập, mẹo, kiến thức (không bán hàng)** | `demo.py --create-json`, `spec.kind = "topic"` → nhánh mới `run_topic` | `product.json` với `kind: "topic"`, `price: 0`, không `product_url` | Theo Q-3 (đề xuất: giọng miễn phí) |
| **Du lịch Việt Nam, nói tiếng Anh, có nguồn** | `demo.py --create-json`, `spec.kind = "travel"` → `travel.run_row` với dòng dựng từ spec | `topic.json`, `facts.json` (như travel hiện tại) | edge-tts (DR-0008, không đổi) |

Ba ô to ngang hàng (không còn hai tầng "Chủ đề khác" → "Chủ đề chung"); ô được chọn sẵn là loại người dùng chọn lần trước (lưu trong `localStorage` của trình duyệt). Trong tài liệu, "chủ đề chung" = ô thứ hai.

Chuỗi bài tập theo giáo trình (`demo.py --exercise`, Bát Đoạn Cẩm, Thái Cực Quyền) **không đổi**: lời đọc vẫn lấy nguyên văn giáo trình, không qua AI. Ô "Bài tập, mẹo, kiến thức" dùng cho video lẻ có AI viết (xem Q-2).

### 2.2 Dữ liệu đầu vào

Mọi giới hạn độ dài và số dòng kiểm **ở server** (`Field(max_length=…)` của pydantic, đếm dòng sườn ở `studio.py`), không chỉ trên trang (C-0014-14).

**Bài tập, mẹo, kiến thức** (`POST /api/studio/create`, `kind: "topic"`):

| Trường (code) | Nhãn trên Studio | Bắt buộc | Giới hạn | Dùng cho |
|---------------|------------------|----------|----------|----------|
| `name` | Tên chủ đề | Có | 1–120 ký tự | Tên thư mục, tiêu đề Studio, ngữ cảnh cho Groq |
| `audience` | Người xem là ai | Không | ≤ 200 ký tự | Giọng văn của câu mở đầu |
| `outline` | Kịch bản sườn | Có | 2–12 dòng không trống, mỗi dòng ≤ 200 ký tự | Mỗi dòng = **một cảnh**, đúng thứ tự. Dòng 1 = cảnh mở đầu, dòng cuối = cảnh kết. Chữ đầu dòng kiểu `1.`, `-`, `Cảnh 2:` được bỏ đi |
| `notes` | Điều cần tránh / lưu ý | Không | ≤ 500 ký tự | Ràng buộc bắt buộc tuân thủ. Khi tên chủ đề hoặc sườn có chữ "tập" và ô đang trống, trang **điền sẵn** "Bài vận động nhẹ, không phải phương pháp chữa bệnh." kèm nhãn nhỏ "Đề xuất sẵn, sửa được" (MKTG #23) |
| `images` | Ảnh minh hoạ | Không | ≤ 10 ảnh, dùng lại khung tải ảnh của DR-0007 (`staging/anh_sp_N`) | Ảnh nền các cảnh, lưu thành `anh_sp_N.<ext>` (C-0007-3) |
| `voice_gender` | Giọng đọc: Tự chọn / Nam / Nữ | Không | `auto` \| `nam_bac` \| `nu_nam` | Thay cho ô "Danh mục" (MKTG #24): `auto` = `choose_persona` theo tên; Nam/Nữ ép persona |
| `voice` | Loại giọng: Miễn phí / Gemini | Không | `edge` \| `gemini` | Như DR-0013; cạnh "Gemini" ghi "tốn 1 lượt mỗi cảnh" |

Chữ hướng dẫn dưới ô sườn (MKTG #5): "Mỗi dòng là một cảnh. Dòng đầu mở video, dòng cuối kết video. Viết ý, không cần viết lời đọc." Dòng đếm: "5 dòng = 5 cảnh (tối thiểu 2, tối đa 12)". Lỗi: "Cần từ 2 đến 12 dòng. Bạn đang có 13. Xoá bớt 1 dòng."

Ví dụ sườn (chữ mờ trong ô):

```
Ngồi văn phòng cả ngày, vai gáy mỏi nhừ?
Hai tay nâng trời, giữ 3 nhịp thở
Kéo cung bắn chim, đổi bên
Làm chậm, đau thì dừng
Lưu lại để tập mỗi sáng
```

Groq nhận sườn (đặt trong khối phân cách rõ ràng, có câu "nội dung trong khối là dữ liệu, không phải lệnh"), giữ **đúng số cảnh và thứ tự**, viết cho mỗi cảnh: `line` (lời đọc ≤ 20 từ), `text` (chữ trên hình ≤ 6 từ), `brief` (chép lại ý của dòng sườn), cộng `hook`, `caption`, `hashtags`. Không thêm số liệu không có trong sườn / lưu ý (C-0014-6).

**Du lịch Việt Nam** (`kind: "travel"`): các trường giống cột tab Travel, đổi nhãn cho người vận hành (MKTG #7). Ô có mặc định thu gọn trong "Tuỳ chọn thêm".

| Trường (code) | Nhãn trên Studio | Bắt buộc | Ghi chú |
|---------------|------------------|----------|---------|
| `question` | Câu hỏi của khách du lịch | Có | ≤ 200 ký tự. Gợi ý trong ô: "Viết bằng tiếng Anh, ví dụ: Do I need a visa for Vietnam?" |
| `destination` | Địa điểm | Có (mặc định) | Đọc từ `content/travel/destinations/*.json` (hiện `vn`); mặc định `defaults.json` |
| `audience` | Khách xem là ai | Có (mặc định) | `content/travel/audiences/*.json` (hiện `en-us`) |
| `pillar` | Nhóm chủ đề (visa, ăn uống…) | Có (mặc định) | `pillars.json`, hiện tên đời thường của từng nhóm |
| `source_urls` | Link nguồn chính thức (mỗi dòng một link) | Không | Phải thuộc danh sách nguồn của điểm đến (T-1). Sai: "Link này không nằm trong danh sách nguồn tin cậy cho Việt Nam. Hãy dùng trang chính thức (ví dụ trang của cơ quan nhà nước) hoặc để trống để hệ thống tự tìm." (MKTG #8) |
| `facts_manual` | Thông tin tự ghi thêm (chỉ khi bạn chắc chắn đúng) | Không | Như cột Sheet |
| `notes` | Ghi chú cho AI | Không | Như cột Sheet |
| `outline` | Các ý trả lời | Không | Nhãn đầy đủ (MKTG #6): "Các ý trả lời (từ {min} đến {max} ý, không cần dòng mở và dòng kết, hệ thống tự thêm)", {min}/{max} đọc từ `pillars.json → answer_segments` của nhóm đang chọn. 0 dòng hoặc min..max dòng |

Video du lịch tạo từ Studio **không** thêm dòng vào tab Travel; `_set_sheet_status` không tìm thấy dòng nên không ghi gì (hành vi sẵn có, `travel.py:1726`).

Dưới nút "Viết kịch bản" của mọi loại (MKTG #26, #20): "Bước tiếp theo: xem và sửa bố cục, rồi mới dựng video. Bước này chỉ dùng AI viết chữ (miễn phí), chưa tốn lượt giọng đọc." Khi đang chạy: "Đang viết kịch bản, khoảng N phút. Bạn có thể đóng trang này, video sẽ hiện trong danh sách khi xong." (N do Dev đo trên máy thật, ghi vào hướng dẫn vận hành; DR không ước đoán.)

### 2.3 Mô hình dữ liệu bố cục (`script.json`)

| Trường | Trước | Sau | Ai ghi |
|--------|-------|-----|--------|
| `stage` | Không có | `"script_review"` khi đang ở bước bố cục; xoá khi dựng xong | `demo.py`/`travel.py` đặt khi tạo; Studio đặt khi "Sửa bố cục"; `--continue` xoá |
| `segments[i].sid` | Không có | Mã cảnh dạng `s1`…, khớp `^s[1-9]\d{0,3}$`, duy nhất trong video, không dùng lại | **Chỉ máy cấp**: `demo.py`/`travel.py` khi tạo; `studio.py` khi thêm cảnh (từ `next_sid`) hoặc khi mở bố cục thư mục cũ (`s1…sN` theo vị trí). Trình duyệt chỉ gửi lại `sid` đã có (C-0014-12) |
| `next_sid` | Không có | Số kế tiếp để cấp `sid` mới | Như trên |
| `segments[i].audio_path` | Có (`…/audio_{i}.mp3`) | **Bản đồ cảnh → file**: tên file cuối của `audio_path` cho biết file giọng (và ảnh `canh_{k+1}`, với `k` là số trong tên `audio_k`) của cảnh đó. Cảnh mới: không có `audio_path` | **Chỉ** `demo.py`/`travel.py`; `studio.py` không bao giờ ghi/xoá trường này (C-0014-1) |
| `segments[i].brief` | Không có | Ý của cảnh (tiếng Việt, ≤ 200 ký tự). Sản phẩm: Groq viết kèm; chủ đề: dòng sườn | Groq / người sửa |
| `segments[i].image_slot` | Không có | Tuỳ chọn: số ảnh minh hoạ (0–9) cho cảnh `product`/`topic`; không có = "Tự chọn" (xoay vòng như hiện nay) | Người chọn trên Studio |
| File `script.before-layout.json` | Không có | Bản `script.json` lúc bấm "Sửa bố cục" trên video đã dựng. **Bị `--continue` xoá ngay trước khi đổi tên file đầu tiên**; `--approve` cũng xoá | Studio ghi; "Bỏ các chỗ vừa sửa" chép lại (C-0014-10) |
| File `_rename_plan.json` | Không có | Nhật ký đổi tên của `--continue` (theo code, xem § 12.3): `{phase: 1\|2, moves: {"<sid>": [tên cũ, tên mới], "<sid>:img:<ext>": [canh cũ, canh mới]}, removed: {"a<k>": ["audio_<k>.mp3", "_bo_audio_<k>.mp3"], "i<k>": ["canh_<k>.<ext>", "_bo_canh_<k>.<ext>"]}, final: {sid: vị trí mới}, meta: {sid: {audio_line, duration, tts_model}}, tts_provider}`, ghi nguyên tử | `demo.py`/`travel.py`; xoá sau khi ghi xong `script.json` (C-0014-11) |
| `rewrite_request` | Không có | `{scenes: [sid…] \| "all", instruction: "…"}`, `instruction` ≤ 500 ký tự | Studio ghi trước khi chạy `--rewrite`; `demo.py` xoá sau khi chạy |
| `segments[i].kind` (chủ đề) | — | `topic` cho cảnh thân, `outro` cho cảnh kết; vẽ như cảnh `product` (ảnh + chữ), **không** có giá, "link tiếp thị", "giỏ hàng vàng" | Groq / người |

Không dùng trường `file_order` của bản đề xuất đầu (Tech Lead #8): ghi cảnh↔file ở 2 nơi (`audio_path` mà render dùng và `file_order`) dễ lệch nhau, và bản đầu để Studio ghi `file_order` cho thư mục cũ, trái C-0014-1.

Ghi `script.json` và `product.json` ở mọi nơi (kể cả `demo.save_script` và dòng 1759) theo cách nguyên tử: ghi `.tmp` rồi `os.replace` (C-0014-13).

### 2.4 Thao tác trên bước bố cục

**Tự lưu** (MKTG #1): trước mọi thao tác chạy việc nền hoặc đổi số cảnh (AI viết lại, Dựng, Thêm, Xoá, Đổi chỗ), trang gửi `PUT .../layout` với những gì đang có trên màn hình; lưu lỗi (400) thì dừng, không chạy thao tác, hiện lỗi ở cảnh đó. Khi có chữ chưa lưu, thanh dưới hiện "Có thay đổi chưa lưu"; rời trang thì hỏi "Bạn đã sửa chưa lưu. Lưu rồi rời trang?".

| Thao tác (nút trên Studio) | Nơi xử lý | Gọi AI? | Ảnh hưởng file khi dựng |
|----------------------------|-----------|---------|-------------------------|
| Sửa Ý cảnh / Lời đọc / Chữ trên hình / câu mở đầu / caption / chọn ảnh | `PUT /videos/{f}/layout` (chỉ ghi JSON) | Không | Cảnh đổi lời → đọc lại giọng (1 lượt Gemini nếu video dùng Gemini) |
| **+ Thêm cảnh ở đây** (có Ý cảnh; Lời đọc để trống được) | `PUT .../layout` | Không | Cảnh mới → đọc giọng 1 lượt |
| **Xoá cảnh** (hỏi xác nhận) | `PUT .../layout` | Không | File của cảnh đổi tên `_bo_*` (C-0014-4); 0 lượt |
| **↑ / ↓** | `PUT .../layout` | Không | Đổi tên file theo cảnh; 0 lượt. Cảnh lên vị trí 1 giữ giọng cũ (không đọc lại kiểu "câu mở đầu") |
| **AI viết lại cảnh này** (ô "Yêu cầu cho AI" tuỳ chọn) | Tự lưu → `POST .../rewrite {scenes:[sid], instruction}` → `demo.py --rewrite DIR` | Groq 1 lần (≤ 3 thử) | Đổi `line`/`text` (travel: thêm `subs`) của cảnh đó. Cảnh đã sửa tay (lời khác bản AI viết lần trước) → hỏi "Cảnh này bạn đã sửa tay. AI viết lại sẽ thay lời bạn gõ. Tiếp tục?". Sau khi viết xong, dưới cảnh hiện nút **Dùng lại câu cũ** (trang giữ câu cũ trong bộ nhớ cho tới lần lưu kế tiếp) (MKTG #10) |
| **AI viết lại cả kịch bản** | Tự lưu → `POST .../rewrite {scenes:"all", instruction}` | Groq 1 lần | Hỏi: "Lời đọc, chữ trên hình, câu mở đầu, caption và hashtag của mọi cảnh sẽ được viết lại. Cảnh và thứ tự giữ nguyên. Không hoàn tác." (MKTG #11) |
| **Dựng video theo bố cục này** | Tự lưu → `POST .../continue` (kèm `revoice_all` tuỳ chọn) → `demo.py --continue DIR` | Không (travel: `build_media` tìm clip cho cảnh mới, $0) | Kiểm luật → đọc giọng cảnh mới/đổi lời → đổi tên file → dựng → "Chờ duyệt đăng" |
| **Sửa bố cục** (video đã dựng, chưa duyệt) | Hỏi xác nhận (§ 4.4) → `POST .../layout/open` | Không | Chưa đụng file; video cũ vẫn xem được, nhãn "Video cũ, chưa theo bố cục mới" |
| **Bỏ các chỗ vừa sửa** | Hỏi xác nhận → `POST .../layout/cancel` | Không | Chép lại `script.before-layout.json`, xoá `stage`. 409 khi bản sao lưu không còn (đã từng bấm Dựng) (C-0014-10) |
| Tải ảnh nhân vật cho cảnh (`POST .../image?target=scene`) | — | — | **409 khi còn `stage`** ("Hãy dựng video theo bố cục mới trước, rồi tải ảnh nhân vật"), vì `canh_N` theo vị trí cũ (Tech Lead #5) |

Không có nút xoá bản nháp chưa dựng trong DR này (xem Q-6).

### 2.5 Trạng thái và quay lui

```
Tạo (Studio) ──Groq──▶ script_review ("Đang soạn bố cục", chưa có giọng, chưa có video)
                         │  ▲   sửa/thêm/xoá/đổi chỗ (PUT layout, tự lưu), AI viết lại (--rewrite)
                         │  │
     Dựng video theo bố cục này (--continue): kiểm → giọng (chỉ cảnh mới/đổi) → đổi tên file → dựng
                         ▼  │
                       review ("Chờ duyệt đăng", có video.mp4)
                         │  └── Sửa bố cục (layout/open) ──▶ quay lại script_review (video cũ giữ để xem)
                         │       Bỏ các chỗ vừa sửa (layout/cancel) ──▶ về review, không đổi gì
                         │  Sửa câu đọc + Dựng lại video (DR-0001, như cũ)
                         ▼
                 Duyệt & lưu (--approve) ──▶ post.txt → Drive → done   (bị chặn khi còn stage)
```

- Dựng lỗi **sau** khi đã đổi tên file: `stage` còn, bản sao lưu đã bị xoá nên nút "Bỏ các chỗ vừa sửa" ẩn; người bấm "Dựng video theo bố cục này" lần nữa (file đã khớp bố cục mới).
- `needs_images` (story thiếu ảnh nhân vật) giữ nguyên nghĩa (C-0011-4): sau `--continue`, video story thiếu ảnh vẫn ra `needs_images` như hiện nay. Cổng ảnh nhân vật / cổng hình của DR-0011 **không** làm trong DR này.
- Video đã duyệt (có `post.txt`) không có nút "Sửa bố cục"; chỗ nút hiện chữ "Video đã duyệt, không sửa bố cục được" (MKTG #17).
- Sheet: tạo video sản phẩm từ dòng Sheet → dòng được ghi `script_review` (thêm vào `SHEET_STATUS`, như DR-0011 § 5.1) để chạy `--sheet` không làm lại dòng đó; sau dựng → `review` như cũ. Chữ `script_review` chỉ ở Sheet; hướng dẫn vận hành giải thích "dòng đang soạn bố cục sẽ không bị chạy lại" (MKTG #25).

### 2.6 Hệ quả lên audio, ảnh, clip khi đổi bố cục

| File | Gắn với cảnh bằng | Khi đổi chỗ | Khi xoá cảnh | Khi thêm cảnh | Khi đổi lời |
|------|-------------------|-------------|--------------|---------------|-------------|
| `audio_{i}.mp3` | Vị trí `i`; `audio_path` của cảnh chỉ ra file cũ | Đổi tên theo nhật ký 2 pha | Đổi tên `_bo_audio_<k>.mp3` (`k` = số cũ; trùng tên thì thêm `_1`, `_2`…) | Đọc giọng mới vào `_new_audio_<sid>.mp3` rồi đổi tên | Đọc lại như `revoice_changed` |
| `canh_{i+1}.*` (ảnh nhân vật story) | Vị trí, đi cùng `audio_{i}` | Đi theo cảnh (mọi đuôi `.png`/`.jpg`… cùng số) | `_bo_canh_<k+1>.*` | Không có ảnh → story thiếu ảnh → `needs_images` như cũ | Giữ ảnh |
| `anh_sp_N.*` (ảnh sản phẩm / minh hoạ) | `product.json → images`, không theo cảnh | Không đổi | Không đổi | Không đổi | Không đổi |
| `img_N.jpg` (ảnh tải từ link) | Như trên | Không đổi | Không đổi | Không đổi | Không đổi |
| Travel `clip_*` / `script.media[]` | `segments[i].media` = chỉ số trong `media[]` (không theo vị trí) | Không đổi | Mục `media[]` bỏ dùng, file ở lại (không tải Drive như hiện nay) | `build_media` tìm clip cho cảnh chưa có `media` ($0) | Giữ clip |
| `video.mp4` | — | Giữ bản cũ tới khi dựng xong bản mới | — | — | — |
| `capcut.json` / dự án CapCut | — | Cũ; xuất lại sau khi dựng (DR-0013) | — | — | — |

Thứ tự trong `--continue` (C-0014-2, C-0014-11):

1. Còn `_rename_plan.json` từ lần trước → làm tiếp đúng pha ghi trong nhật ký, ghi `script.json`, xoá nhật ký, rồi mới làm tiếp các bước dưới.
2. Kiểm `sid` (C-0014-12) và luật bố cục (§ 4.3) bằng `layout_rules.py`. Sai → mã 9, không đổi gì.
3. Đọc giọng mọi cảnh mới/đổi lời vào `_new_audio_<sid>.mp3`, bằng đúng `tts_provider` + `tts_model` của video (C-0001-1). Lỗi → xoá file tạm, **không đổi file nào, không đổi `script.json`**, mã 3. Với `--revoice-all edge`: đọc lại **mọi** cảnh bằng edge-tts vào file tạm (thoát kẹt khi hết lượt Gemini, Tech Lead #9).
4. Xoá `script.before-layout.json` (từ đây không còn "Bỏ các chỗ vừa sửa", Tech Lead #1).
5. Ghi `_rename_plan.json` (phase 1) nguyên tử; pha 1: mọi file cần dời → `_mv_<sid>.*`, file của cảnh bị xoá → `_bo_*`; ghi `phase: 2`; pha 2: `_mv_<sid>.*` và `_new_audio_<sid>.mp3` → tên cuối `audio_{i}.mp3` / `canh_{i+1}.*`.
6. Cập nhật `audio_path`, `audio_line`, `duration` mọi cảnh; ghi `script.json` nguyên tử; xoá `_rename_plan.json`.
7. Dựng. Dựng lỗi: file đã khớp bố cục mới, `stage` còn, bấm lại được.

Video đầu tiên (chưa có giọng nào): bước 3 = `generate_voiceovers` như hiện nay (giữ chuỗi model dự phòng và chuyển edge cả video của DR-0012); bước 4–5 không có gì để làm.

---

## 3. Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Bước bố cục = `stage: script_review` của DR-0011 trên `script.json`; `sid` do máy cấp; bản đồ cảnh→file lấy từ `audio_path` sẵn có; chỉ `demo.py`/`travel.py` đổi tên file, có nhật ký; Studio chỉ ghi JSON; chủ đề dùng `product.json` với `kind: "topic"` | ⭐ | Dùng lại tên trạng thái và lệnh `--continue` đã duyệt ở DR-0011. Giữ mọi chỗ đọc `audio_{i}` (render, CapCut, `audio_seams`) không phải sửa. Không thêm trường bản đồ thứ hai. Chủ đề đi qua đúng `render_video`/`approve`/Studio `_editable` sẵn có |
| B | Đặt tên file theo `sid` (`audio_s3.mp3`), bỏ tên theo vị trí | — | Phải sửa `render_video`, `revoice_changed`, `capcut_export.py`, `audio_seams.py`, `transcript_check.py`, `sandbox_render.py`, travel; thư mục cũ phải đổi tên hàng loạt. Nhiều chỗ sửa hơn mà người vận hành không thấy khác |
| C | Đổi bố cục = luôn đọc lại giọng **toàn bộ** và bỏ file cũ | — | Mỗi lần sửa tốn đủ số lượt Gemini (1 lượt/cảnh, 10 lượt/ngày), đi ngược mục tiêu "không làm lại từ đầu" |
| D | Chủ đề có file riêng (`subject.json`) và hàm dựng riêng | — | Phải nhân đôi `render_video`, `approve`, `_editable`, `_title`, nhận dạng thư mục. `topic.json` đã là dấu hiệu của travel (`studio_travel.is_travel`) nên không dùng tên đó được |
| E | Studio gọi Groq trực tiếp cho "AI viết lại" | — | Vi phạm C-0001-2 / C-0011-3; `studio.py` không import `demo.py` |
| F | Thêm trường `file_order` riêng làm bản đồ cảnh→file (bản đề xuất đầu) | — | Hai nơi ghi cùng một thông tin (`audio_path` mà render dùng, và `file_order`), lệch nhau là gốc lỗi; Tech Lead #8 |

---

## 4. Thay đổi cấu trúc

### 4.1 Lệnh `demo.py`

| Lệnh | Việc | Mã thoát |
|------|------|----------|
| `demo.py --create-json FILE` với `kind: "topic"` | Groq viết từ sườn → `product.json` (`kind: topic`) + `script.json` (`stage: script_review`), **0 TTS, không dựng**; in `Studio folder: <tên>` (bắt buộc, `job_status` đọc dòng này) | 0; lỗi nhập/Groq → 1 (như hiện nay) |
| `demo.py --create-json FILE` với `kind: "travel"` | `travel.run_row` → research → `write_and_check` → dừng, `stage: script_review` (chưa `build_media`, chưa giọng); in `Studio folder:` | 0; `needs_sources` → 1 như hiện nay |
| `demo.py --create-json FILE` (sản phẩm) | Như cũ nhưng dừng sau `generate_script` ở `script_review`; in `Studio folder:` | 0 / 1 |
| `demo.py --continue DIR [--revoice-all edge]` | Chỉ cho thư mục có `stage`. Thứ tự § 2.6. Travel: `check_script(strict=False)` + `build_media` cảnh thiếu clip; travel chỉ nhận `edge` | 0; 3 giọng lỗi; 5 travel sai số; **9** không ở bước bố cục / `sid` sai / bố cục sai luật |
| `demo.py --rewrite DIR` | Đọc `rewrite_request`; prompt gửi kèm `sid` từng cảnh và nhận về `{sid: {line, text[, subs]}}`; ghép theo `sid`. Kết quả thiếu `sid` được yêu cầu, có `sid` lạ, hoặc vi phạm giới hạn của `layout_rules.py` = 1 lần thử hỏng (trong 3) (Tech Lead #10). Travel: thêm `check_script(strict=False)`. Xong thì xoá `rewrite_request` | 0; 5 travel sai số (giữ bản cũ); **12** hết 3 lần (`script.json` không đổi byte); 9 không ở bước bố cục |

Thư mục có `stage` bị chặn mã 9 với `--render-only`, `--approve`, `--rerender`, `--capcut` (C-0014-9; Tech Lead #6: `--rerender` hiện sẽ `KeyError` ở `demo.py:1327` với cảnh mới chưa có `audio_path`, hoặc ghi `review` lên Sheet cho bố cục chưa duyệt). Không thêm `REVIEW_GATES`, `--gates`, `--no-gates` (thuộc DR-0011, Q-1).

### 4.2 API Studio (`backend/app/api/studio.py`)

| Phương thức | Đường dẫn | Việc |
|-------------|-----------|------|
| GET | `/videos` | Liệt kê thêm thư mục có `script.json → stage` (kể cả chưa có `video.mp4`); `label = "layout"`; `updated` = mtime `script.json` khi chưa có video |
| GET | `/videos/{f}` | Thêm `stage`, `kind` (`product` / `topic` / `travel`), `can_cancel_layout` (còn bản sao lưu), mỗi cảnh thêm `sid`, `brief`, `image_slot`, `has_audio`, `needs_voice` (cảnh mới hoặc đổi lời), `locked` + `locked_reason` (cảnh không xoá/dời được, § 4.3); `video_url = null` khi chưa có video. Khi có `stage`, ảnh nhân vật của cảnh lấy theo số `k` trong `audio_path` (`canh_{k+1}`) thay vì vị trí |
| PUT | `/videos/{f}/layout` | Chỉ khi `stage = script_review`. Nhận danh sách cảnh `{sid?, kind, brief, line, text, image_slot?, fact_ids?, subs?}` + câu mở đầu/caption/hashtag/giá. Kiểm `sid` (C-0014-12) và luật (`layout_rules.py`), cấp `sid` mới cho cảnh không có `sid`, ghi `script.json`. Không đổi file nào |
| POST | `/videos/{f}/layout/open` | Video đã dựng, chưa duyệt: lưu `script.before-layout.json`, cấp `sid` cho thư mục cũ, đặt `stage` |
| POST | `/videos/{f}/layout/cancel` | Chép lại `script.before-layout.json`, xoá `stage`, xoá bản sao lưu. **409** khi không còn bản sao lưu |
| POST | `/videos/{f}/rewrite` | Ghi `rewrite_request`, chạy job `--rewrite` |
| POST | `/videos/{f}/continue` | Body `{revoice_all: null \| "edge"}`; chạy job `--continue` |
| POST | `/create` | Thêm `kind: "product" \| "topic" \| "travel"` và các trường § 2.2 |
| GET | `/travel-options` | Danh sách địa điểm / khách / nhóm chủ đề (kèm `answer_segments`) từ `content/travel/` (chỉ đọc JSON) |
| POST/PUT | `.../render`, `.../approve`, `.../capcut`, `PUT /videos/{f}`, `POST .../image?target=scene` | **409** khi còn `stage` (chữ § 4.4) |

- Mọi API ghi: `X-Studio: 1` (C-0001-3); kiểm job và ghi file **trong cùng `_job_lock`** mà `_start_job`/`_start_create_job` cầm (C-0014-14, Tech Lead #7).
- Mọi trường chữ mới có `max_length` ở pydantic; mọi chuỗi người gõ hoặc AI viết hiện lại trên trang đi qua `esc()` (Tech Lead #11).
- `ERROR_KINDS` thêm `9: "layout_not_ready"`, `12: "rewrite_failed"`.
- `job_status` trả thêm tên việc đang chạy bằng tiếng Việt cho câu 409 (MKTG #16).

### 4.3 Luật bố cục (một module `layout_rules.py` ở root, chỉ stdlib; `studio.py` kiểm khi `PUT` để báo ngay, `demo.py`/`travel.py` kiểm lại ở `--continue`/`--rewrite` theo C-0011-2)

| Loại | Luật | Sai thì |
|------|------|---------|
| Chung | 2–12 cảnh; `line` sau khi gộp khoảng trắng 1–300 ký tự (cảnh mới được để trống, nhưng `--continue` chặn); `brief` ≤ 200; `text` ≤ 60; `sid` theo C-0014-12 | 400 (PUT) / 9 |
| Sản phẩm | Đúng **1** cảnh `cta`, ở **cuối** (khoá: không xoá, không dời); cảnh `story` chỉ khi `style = story`; giá `0` hoặc `>= 1000` (C-0007-2) | 400 / 9 |
| Chủ đề | Chỉ `topic` + đúng 1 `outro` ở cuối (khoá); không có `cta`, `story` | 400 / 9 |
| Du lịch | Cảnh 1 `hook`, cảnh cuối `outro` (khoá cả hai); số cảnh `answer` trong `answer_segments.min..max` của nhóm chủ đề; mỗi `answer` có `fact_ids` có thật; số khớp quote (C-0008-1, `check_script(strict=False)`) | 400 / 9; sai số → 5 |

### 4.4 Giao diện Studio (chữ cụ thể, MKTG duyệt lại khi có bản chạy)

**Form tạo**: § 2.1, § 2.2. Nút "Viết kịch bản".

**Danh sách**: nhãn mới **"Đang soạn bố cục"** (màu khác), đổi nhãn cũ "Chờ duyệt" thành **"Chờ duyệt đăng"** (MKTG #19). Thẻ chưa có video hiện khung "Chưa dựng video". Đếm số video theo nhãn.

**Dải bước** (MKTG #3): "1 Soạn bố cục → 2 Dựng và xem thử → 3 Duyệt & lưu". Nút cuối giữ "Duyệt & lưu" (đã có, DR-0001) kèm câu hậu quả sẵn có.

**Thẻ cảnh** (MKTG #9, #13, #21, #22):
- Mặc định thu gọn, mở một thẻ một lúc; thẻ thu gọn hiện số cảnh, loại ("Mở đầu", "Nội dung", "Kêu gọi mua", "Kết"), một dòng lời đọc.
- Ba ô, mỗi ô có chú thích nhỏ: **Ý cảnh** "để AI hiểu, không hiện trong video" (thu gọn mặc định); **Lời đọc** "giọng sẽ đọc"; **Chữ trên hình** "chữ lớn trên video".
- Chọn ảnh bằng hình thu nhỏ của các ảnh minh hoạ, mặc định "Tự chọn". 0 ảnh: "Chưa có ảnh nào, video sẽ dùng nền trơn. Thêm ảnh?"
- Nút **↑ ↓** cao tối thiểu 44 px (đề xuất, Dev đo trên máy thật), **Xoá cảnh**, **AI viết lại cảnh này**. Cảnh khoá: nút ↑ ↓ Xoá mờ, chú thích "Cảnh này cố định vì video sản phẩm phải kết bằng lời kêu gọi mua" / "…vì video du lịch luôn mở bằng câu hỏi" / "…luôn kết bằng lời chào kênh". Kiểm ngay trên trang, không đợi lưu.
- Chấm "Cần đọc giọng" khi cảnh mới/đổi lời. Cảnh chưa có lời đọc: viền đỏ "Chưa có lời đọc, bấm 'AI viết lại cảnh này' hoặc tự gõ" (MKTG #12).
- Giữa các thẻ: **+ Thêm cảnh ở đây**. Cuối trang: ô "Yêu cầu cho AI" + **AI viết lại cả kịch bản**.
- Đang viết lại: "Đang viết lại cảnh 3… (thường vài giây)".

**Thanh dưới cố định** (không che nội dung, có khoảng đệm cuối trang): **Lưu** · **Dựng video theo bố cục này** · (xa hai nút trên, màu phụ) **Bỏ các chỗ vừa sửa**.
- Nút Dựng tắt khi còn cảnh lỗi; cạnh nút: "Chưa dựng được: cảnh 4 chưa có lời đọc" (bấm vào nhảy tới cảnh 4).
- Câu chi phí (MKTG #14): đủ lượt: "Sẽ đọc giọng N cảnh, khoảng N lượt Gemini, hôm nay còn M." Không đủ: "Không đủ lượt Gemini hôm nay (cần N, còn M). Cả video sẽ dùng giọng miễn phí (giọng khác hẳn)." kèm hai nút "Dùng giọng miễn phí cho cả video" (gửi `revoice_all: "edge"`) và "Để mai". Video giọng miễn phí: "Giọng miễn phí, không tốn lượt."

**Hộp xác nhận**:
- Sửa bố cục (MKTG #17): "Mở sửa bố cục. Video cũ vẫn giữ để xem. Bạn chưa duyệt đăng được cho tới khi dựng lại. Thêm hoặc đổi lời cảnh nào thì cảnh đó tốn 1 lượt đọc giọng."
- Bỏ các chỗ vừa sửa (MKTG #2): "Bỏ mọi thay đổi bố cục và quay về video cũ? Không khôi phục được."
- Xoá cảnh: "Xoá cảnh 3? Bạn vẫn có thể bấm 'Bỏ các chỗ vừa sửa' trước khi dựng."

**Câu lỗi** (mẫu "việc gì sai + ở đâu + làm gì tiếp", MKTG #15, #16):

| Khi | Câu |
|-----|-----|
| Mã 3 | "Đọc giọng bị lỗi, chưa đổi gì. Chọn: thử lại sau, hoặc đọc lại toàn bộ video bằng giọng miễn phí (giọng mọi cảnh sẽ thay đổi)." |
| Mã 5 (travel) | Dòng `[FACT_CHECK]` như hiện nay, ví dụ "Cảnh 2 có số 30 ngày không có trong nguồn đã lấy. Sửa số hoặc thêm link nguồn rồi bấm Dựng video theo bố cục này." |
| Mã 9 | "Chưa dựng được: <lý do theo luật, có số cảnh>. Sửa rồi bấm lại." |
| Mã 12 | "AI đang bận hoặc trả lời lỗi, kịch bản chưa đổi. Thử lại sau ít phút." |
| 409 đang có việc | "Đang có một việc khác chạy (<tên việc>). Đợi xong rồi bấm lại." |
| 409 còn bố cục | "Video đang soạn bố cục. Hãy bấm Dựng video theo bố cục này trước." |
| 409 không còn bản sao lưu | "Bố cục mới đã được dựng một phần, không quay về video cũ được nữa. Hãy bấm Dựng video theo bố cục này." |

Không lộ `stage`, `sid`, `exit`, `--continue`. Điện thoại 390 px không cuộn ngang.

---

## 5. Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 1 | Trả lời Q-1…Q-6, duyệt DR | Người dùng | DR | Trả lời | § 11 |
| 2 | Soát lại bản sửa 1 (§ 2.6 nhật ký đổi tên, C-0014-10…14) | Tech Lead | DR | Ghi chú | — |
| 3 | **Nhóm Dev 1** (`demo.py`, `travel.py`, `layout_rules.py`, `drive_upload.py`): `stage`, `sid`/`next_sid`, `--continue [--revoice-all edge]` theo § 2.6, `--rewrite` theo `sid`, `run_topic` + prompt sườn, `brief` trong `generate_script`, cảnh `topic`/`outro`, `post.txt` chủ đề, travel dừng sau `write_and_check`, `SHEET_STATUS` + `script_review`, mã 9/12, chặn `--render-only`/`--approve`/`--rerender`/`--capcut` khi có `stage`, ghi JSON nguyên tử, `--approve` xoá `_bo_*` và bản sao lưu, Drive bỏ qua mọi tên bắt đầu `_` và `script.before-layout.json`, `auto_export_capcut` bỏ qua `kind: topic` | Dev | DR § 2–4 | Code | root |
| 4 | **Nhóm Dev 2** (không sửa chung file với nhóm 1; chỉ import `layout_rules.py`): API § 4.2 với `_job_lock`, `_folders`/`_label`/`_editable` cho thư mục chưa dựng, 409 các chỗ § 4.2, `ERROR_KINDS`, `/travel-options`; giao diện § 4.4 | Dev | DR § 4.2–4.4 | Code | `backend/app/api/studio.py`, `studio_travel.py`, `backend/app/web/studio.html` |
| 5 | Soát diff: C-0014-x, C-0001-1/2/3, C-0007-x, C-0008-1, C-0011-1/4/6; hồi quy thư mục cũ; mọi chuỗi mới qua `esc()` | Reviewer + Tech Lead | Diff | Ghi chú | — |
| 6 | Test D-1…D-44 trên bản sao (`sandbox-render`), edge-tts, Groq/Gemini giả | Tester | DR § 10 | Kết quả nguyên văn | thư mục tạm |
| 7 | Review chữ và luồng trên Studio, chụp 390 px; review 1 video chủ đề mẫu | MKTG | Studio chạy local | Danh sách sửa | — |
| 8 | Đo thời gian "Viết kịch bản" (sản phẩm, chủ đề, du lịch) và "Dựng" trên máy nhà để ghi vào chữ chờ và hướng dẫn | Dev | Bản chạy | Số đo | Báo cáo Dev |
| 9 | Cập nhật tài liệu § 8 | BA | Kết quả | Docs | — |

---

## 6. Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Đổi tên `audio_N` giữa chừng bị ngắt (đóng cửa sổ `mo-studio.command`, tắt máy) | Video ghép sai giọng | Nhật ký `_rename_plan.json` ghi nguyên tử trước pha 1, ghi `phase: 2` giữa hai pha; lần chạy sau làm tiếp đúng pha; `script.json` ghi xong mới xoá nhật ký (C-0014-11, D-13a/b) |
| R-2 | Rủi ro | Hành vi Studio đổi: tạo video sản phẩm giờ dừng ở bố cục, thêm 1 lần bấm | Chậm hơn với người quen bấm một phát ra video | Q-4; nút "Dựng video theo bố cục này" nổi bật; dòng "Bước tiếp theo…" dưới form |
| R-3 | Phụ thuộc | DR-0010 (travel v2: 4 nhịp, thư viện cảnh quay, mã 8) và DR-0011 cổng hình chưa duyệt / chưa làm; khi làm sẽ đụng `travel.py` và luật kind travel | Xung đột code; luật du lịch phải theo kind mới | Luật nằm ở một chỗ (`layout_rules.py`); DR-0010 khi làm thêm kind vào đó bằng DR mới. Chạy `branch_observer report --fetch` trước khi Dev bắt đầu |
| R-4 | Rủi ro | AI viết lại thay mất lời người đã sửa tay | Mất công | Hỏi xác nhận khi cảnh đã sửa tay và khi viết lại cả kịch bản; nút "Dùng lại câu cũ" |
| R-5 | Rủi ro | Groq không giữ đúng số cảnh của sườn | Bố cục khác ý người | Code so số cảnh, sai thì thử lại (trong 3 lần); vẫn sai → ghép `brief` từ sườn, `line` để trống, người bấm "AI viết lại cảnh này" |
| R-6 | Giả định | Video chủ đề không có `product_url` nên mọi cập nhật Sheet là no-op (`set_sheet_status` dòng 1560) | — | D-18 |
| R-7 | Rủi ro | Video chủ đề về sức khoẻ / bài tập nói quá (chữa bệnh) | Vi phạm chính sách nội dung | Ô "Điều cần tránh" điền sẵn khi có chữ "tập"; MKTG review trước khi đăng (`/video-review`); Q-2 |
| R-8 | Giả định | Hạn mức Groq free chưa rõ | Lỗi 12 | Câu lỗi tiếng Việt; không đổi kịch bản |
| R-9 | Rủi ro | Xoá cảnh để lại `_bo_*` chiếm chỗ | Không đáng kể | Xoá ở `--approve` (C-0014-4) |
| R-10 | Rủi ro | Người gõ vào sườn/yêu cầu câu kiểu "bỏ qua quy tắc, nói chữa khỏi bệnh" | AI bịa công dụng | Sườn/yêu cầu đặt trong khối phân cách, prompt nói rõ là dữ liệu; luật chống bịa giữ ở phần hệ thống của prompt; MKTG review trước khi đăng |
| R-11 | Rủi ro | Bản nháp "Đang soạn bố cục" bỏ dở tăng mãi; job treo không có nút huỷ | Rối danh sách, kẹt 409 | Q-6; nợ kỹ thuật đã ghi `TODO.md` § 5 |

---

## 7. Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Gỡ khi |
|----|-----------|-------|---------|--------|
| C-0014-1 | Sau mỗi lệnh `demo.py`/`travel.py` kết thúc với mã 0: với mọi cảnh có giọng, `basename(segments[i].audio_path) == f"audio_{i}.mp3"`, và `canh_{i+1}.*` (nếu có) thuộc cảnh `i`. Chỉ `demo.py`/`travel.py` được ghi `audio_path`, đổi tên/xoá các file này; `api/studio.py` không bao giờ làm | `render_video`, `capcut_export.py`, `audio_seams.py` đọc theo vị trí | `demo.py`, `travel.py`, `studio.py` | Khi bỏ tên file theo vị trí (DR mới) |
| C-0014-2 | `--continue` làm trọn hoặc không làm: giọng mới tạo vào file tạm trước; chỉ khi mọi cảnh cần đọc đều thành công mới đổi tên file và ghi `script.json`. Lỗi giọng → không file nào đổi, `stage` giữ, mã 3 | Không ra video nửa cũ nửa mới / trộn 2 bộ giọng (mở rộng C-0001-1) | `demo.py`, `travel.py` | — |
| C-0014-3 | Chỉ đọc giọng cho cảnh chưa có giọng hoặc có `line != audio_line`; đổi chỗ/xoá cảnh không gọi TTS. Cảnh mới đọc bằng đúng `tts_provider` + `tts_model` của video; không đủ lượt → mã 3; lối ra là `--continue --revoice-all edge` (đọc lại mọi cảnh bằng giọng miễn phí) | Tiết kiệm lượt Gemini; C-0001-1, C-0012-1; không kẹt khi hết lượt | `demo.py`, `studio.py` | — |
| C-0014-4 | File của cảnh bị xoá đổi tên `_bo_*`, chỉ bị xoá khi `--approve`. Drive bỏ qua **mọi** tên file bắt đầu bằng `_` và `script.before-layout.json`, `_rename_plan.json` | Không mất ảnh tự tải trước khi duyệt; không tải file tạm lên Drive | `demo.py`, `travel.py`, `drive_upload.py` | — |
| C-0014-5 | Groq chỉ được gọi trong `demo.py`/`travel.py` (subprocess). "AI viết lại" nhận và trả theo `sid`; chỉ đổi `line`, `text`, `subs` (+ `hook`, `caption`, `hashtags` khi viết lại cả kịch bản); không đổi số cảnh, thứ tự, `sid`, `brief`, `kind`, `fact_ids`. Kết quả phải qua `layout_rules.py` mới được ghi | Người quyết bố cục; C-0001-2 | `demo.py`, `travel.py`, `studio.py` | — |
| C-0014-6 | Kịch bản sườn, "Ý cảnh", "Yêu cầu cho AI" là chỉ dẫn, không phải nguồn dữ kiện, và luôn nằm trong khối phân cách của prompt. Du lịch: mọi số vẫn phải có trong quote (C-0008-1). Chủ đề / sản phẩm: prompt cấm thêm số liệu, công dụng, cam kết không có trong sườn / lưu ý / điểm nổi bật | Chống bịa | `demo.py`, `travel.py` | — |
| C-0014-7 | Video `kind: "topic"` không có cảnh giỏ hàng, không có chữ "link tiếp thị liên kết", `post.txt` không có bước gắn sản phẩm; không xuất CapCut (Studio 409, `auto_export_capcut` bỏ qua) | Video không bán hàng; DR-0013 chỉ cho video sản phẩm | `demo.py`, `studio.py` | Khi có DR CapCut cho chủ đề |
| C-0014-8 | Mã thoát **12** = `rewrite_failed` (`script.json` không đổi). Mã **9** dùng đúng nghĩa C-0011-8 (`gate_not_ready`): thư mục không ở bước bố cục, `sid` sai, hoặc bố cục sai luật. Không dùng lại 3–8, 10–11 | Studio đọc mã thoát; 10–11 DR-0011 đã giữ chỗ | `demo.py`, `travel.py`, `studio.py` | — |
| C-0014-9 | Khi thư mục có `stage`: `--render-only`, `--approve`, `--rerender`, `--capcut` trả mã 9; API `render`, `approve`, `capcut`, `PUT /videos/{f}`, `POST .../image?target=scene` trả 409 | Một nơi sửa duy nhất khi đang ở bố cục; `canh_N` và `audio_N` theo bố cục cũ | `demo.py`, `studio.py` | — |
| C-0014-10 | `--continue` xoá `script.before-layout.json` **trước** khi đổi tên file đầu tiên. `layout/cancel` trả 409 khi không còn bản sao lưu | Huỷ sau khi file đã theo bố cục mới sẽ ghép sai giọng (Tech Lead #1) | `demo.py`, `travel.py`, `studio.py` | — |
| C-0014-11 | Đổi tên file trong `--continue` theo nhật ký `_rename_plan.json` ghi nguyên tử (`.tmp` + `os.replace`) trước pha 1, cập nhật `phase: 2` giữa hai pha; `script.json` ghi xong mới xoá nhật ký. Mọi lần `--continue` bắt đầu bằng việc làm tiếp nhật ký còn sót | Phục hồi chắc chắn khi bị ngắt ở bất kỳ pha nào (Tech Lead #2) | `demo.py`, `travel.py` | — |
| C-0014-12 | `sid` khớp `^s[1-9]\d{0,3}$`; mỗi `sid` trình duyệt gửi lên phải có trong `script.json` hiện tại và không trùng; cảnh mới do server cấp từ `next_sid`. `demo.py --continue` kiểm lại trước khi đụng file. Tên file chỉ được ghép từ `sid` đã qua kiểm | `sid` đi vào tên file: chặn ghi ra ngoài thư mục và ghi đè (Tech Lead #4) | `studio.py`, `demo.py`, `travel.py`, `layout_rules.py` | — |
| C-0014-13 | `script.json`, `product.json` và mọi file trạng thái mới ghi nguyên tử (`.tmp` + `os.replace`) ở mọi nơi | `script.json` là nguồn duy nhất của bố cục; hỏng nửa chừng làm mất thư mục khỏi Studio (Tech Lead #3) | `demo.py`, `travel.py`, `studio.py` | — |
| C-0014-14 | Mọi API ghi của Studio kiểm "đang có job" và ghi file trong cùng `_job_lock` mà việc khởi chạy job cầm; mọi trường chữ có giới hạn độ dài ở server | Không ghi chồng lúc `--continue` đang chạy (Tech Lead #7); không tin trình duyệt (Tech Lead #11) | `studio.py` | — |

**Giữ nguyên, không đổi**: C-0001-1, C-0001-2, C-0001-3, C-0001-4, C-0007-1, C-0007-2, C-0007-3 (ảnh minh hoạ chủ đề cũng lưu `anh_sp_N`), C-0008-1, C-0008-2, C-0011-1 (ở bước bố cục không TTS, không FFmpeg), C-0011-2, C-0011-3, C-0011-4, C-0011-6, C-0012-1, C-0013-1.

`supersedes: DR-0011 § 5.3 câu "Không thêm/xoá cảnh (giữ rule 'Số cảnh không khớp')" và DR-0011 § 14 phần "Thêm/xoá cảnh" (chỉ ở bước kịch bản; cắt clip, thay clip vẫn ngoài phạm vi); DR-0011 § 5.4 nhãn "Chờ duyệt kịch bản" đổi thành "Đang soạn bố cục"; nhãn "Chờ duyệt" (DR-0001) đổi thành "Chờ duyệt đăng". Phần còn lại của DR-0011 (cổng ảnh nhân vật, cổng hình, REVIEW_GATES, --skip-approval) giữ nguyên, chưa làm.`

---

## 8. Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Cập nhật | Xong |
|----------|----------|:----:|
| `docs/specs/architecture/capabilities/video-render.md` § Studio | Bước bố cục, trạng thái, API mới, bất biến file, nhật ký đổi tên, mã 9/12, nhãn mới | [x] (mục "Soạn bố cục trước khi dựng & video chủ đề") |
| `docs/specs/architecture/capabilities/script-gen.md` | Sườn → kịch bản, `brief`, `--rewrite` theo `sid`, chủ đề | [x] |
| `docs/specs/architecture/capabilities/travel-content.md` | Tạo từ Studio, dừng sau `write_and_check`, luật bố cục travel | [x] chỉ ghi "chưa làm, PR sau"; nội dung chi tiết cập nhật ở PR du lịch |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | "Tạo video bài tập / mẹo / du lịch", "Sửa bố cục": bấm gì, thấy gì, tốn gì, thời gian chờ đo được, chữ `script_review` trên Sheet, cách dọn bản nháp (theo Q-6) | [x] Bước 3b, mục 4d, bảng lỗi mục 6. **Không** ghi số phút chờ (chưa đo) |
| `.claude/CLAUDE.md` (file thật `agent/CLAUDE.md`) | Lệnh `--continue [--revoice-all edge]`, `--rewrite`, `--create-json` kind, mã 9/12, luồng `demo.py`, `layout_rules.py` | [x] |
| `TODO.md` | Dòng tiến độ #38, phần DR-0011 đã làm; nợ kỹ thuật | [x] M2f + § 5 |
| `.env.example` | Không đổi (không thêm biến) | — |

---

## 9. File thay đổi (cho Dev, BA không sửa)

| File | Mới / sửa | Nội dung |
|------|-----------|----------|
| `layout_rules.py` | **Mới** | Luật § 4.3 và kiểm `sid`, chỉ stdlib; `demo.py`, `travel.py`, `studio.py` cùng import |
| `demo.py` | Sửa | `run_create` (kind), `run_topic`, prompt sườn, `brief`, `sid`, `--continue`, `--rewrite`, nhật ký đổi tên, cảnh `topic`/`outro`, `post.txt` chủ đề, `SHEET_STATUS`, mã 9/12, chặn 4 lệnh khi có `stage`, `save_script` + `product.json` nguyên tử |
| `travel.py` | Sửa | Nhận spec từ Studio, dừng ở `script_review`, `--continue` (check → `build_media` cảnh thiếu → giọng → đổi tên → dựng), rewrite theo `sid` có `check_script` |
| `drive_upload.py` | Sửa | Bỏ qua mọi tên bắt đầu `_`, `script.before-layout.json` |
| `backend/app/api/studio.py` | Sửa | § 4.2 |
| `backend/app/api/studio_travel.py` | Sửa | Dùng `layout_rules.py`, `travel-options` |
| `backend/app/web/studio.html` | Sửa | § 4.4 |
| `app.html`, `backend/app/api/creator.py`, `exercise.py`, `capcut_export.py` | Không đổi | |

---

## 10. Tiêu chí hoàn thành (DoD)

### 10.1 Bảng quyết định cho code

Mọi dòng chạy trên **bản sao** thư mục (`sandbox-render`) hoặc thư mục tạm; Groq và Gemini giả (đếm lời gọi), edge-tts thật hoặc giả; không Drive/Sheet/TikTok thật.

| # | Loại | Điều kiện đầu vào | Kết quả mong đợi | Cách kiểm |
|---|------|-------------------|------------------|-----------|
| D-1 | Bình thường | `--create-json` sản phẩm (link + giá 189000) | Thư mục mới có `product.json`, `script.json` với `stage=script_review`, mỗi cảnh có `sid` khác nhau và `brief`; **0** lời gọi TTS; không có `audio_*.mp3`, `video.mp4`; log có `Studio folder:`; exit 0 | TTS giả đếm = 0; `ls` |
| D-2 | Bình thường | `--create-json` `kind: topic`, sườn 5 dòng, 2 ảnh | `product.json.kind=topic`, `price=0`; đúng 5 cảnh, `brief` = 5 dòng sườn (đã bỏ "1.", "-"); cảnh cuối `outro`; không cảnh `cta`; 0 TTS; log có `Studio folder:` | `jq` so `brief` với sườn |
| D-3 | Bình thường | `--create-json` `kind: travel`, câu hỏi + 1 `source_urls` hợp lệ, 2 ý trả lời | `topic.json`, `facts.json`, `script.json` (`stage=script_review`, hook + 2 answer + outro); không `clip_*`, audio, video; log có `Studio folder:` | `ls`, searcher giả đếm = 0 |
| D-4 | Bình thường | D-1 rồi `--continue` | Giọng mọi cảnh 1 lần (Gemini giả: số lời gọi = số cảnh), `video.mp4` có, `stage` bị xoá; với mọi `i`: `basename(audio_path) == audio_{i}.mp3`; trạng thái `review` | Đếm lời gọi; `jq` |
| D-5 | Bình thường | Video đã dựng 5 cảnh (`s1..s5`); `layout/open`; đổi chỗ s2↔s4; `--continue` | **0** lời gọi TTS; `md5(audio_1.mp3)` mới = `md5(audio_3.mp3)` cũ và ngược lại; bất biến C-0014-1 đúng; video dài bằng cũ ±0,1 s | So hash |
| D-6 | Bình thường | Như D-5, xoá s3 | 0 TTS; còn `audio_0..3`; `_bo_audio_2.mp3` có; video 4 cảnh | `ls`, `ffprobe` |
| D-7 | Bình thường | Như D-5, thêm cảnh mới sau s2 có `line` | Đúng **1** lời gọi TTS, cùng `tts_model` với các cảnh khác; `audio_2.mp3` = cảnh mới; audio cũ khác chỉ đổi tên (hash giữ) | Đếm lời gọi + hash |
| D-8 | Bình thường | Như D-5, sửa `line` cảnh s4 | 1 lời gọi TTS; audio khác hash giữ nguyên | Hash |
| D-9 | Bình thường | `rewrite` cảnh s2 với yêu cầu "ngắn hơn" | Groq giả 1 lời gọi, prompt có `sid` s2; chỉ `line`/`text` của s2 đổi; `sid`, `brief`, số cảnh, thứ tự giữ; `rewrite_request` bị xoá; 0 TTS | `jq` diff |
| D-10 | Bình thường | `rewrite` `all` | Mọi `line` đổi, hook/caption đổi; số cảnh, `sid`, `brief`, `kind` giữ | `jq` diff |
| D-11 | Bình thường | Story có ảnh `canh_2.png`, dời cảnh 2 tới vị trí 4, `--continue` | Ảnh thành `canh_4.png` (hash giữ); khung hình cảnh 4 là ảnh đó | Hash + `review_frames.py` |
| D-12 | Lỗi | Gemini giả lỗi quota khi đọc cảnh mới ở D-7 | Mã 3; không `audio_*` nào đổi hash; `script.json` giữ nguyên byte; `stage` còn; `script.before-layout.json` còn; không `_new_audio_*`, `_mv_*`, `_rename_plan.json` sót | Hash toàn thư mục |
| D-13a | Lỗi | Giả lập ngắt trong pha 1 (nhật ký `phase: 1`, một số file đã thành `_mv_*`), chạy lại `--continue` | Làm tiếp đúng nhật ký; mọi `audio_{i}` khớp cảnh `i` (hash so bản mong đợi); nhật ký bị xoá; exit 0 | Tạo trạng thái giả trên bản sao |
| D-13b | Lỗi | Như trên nhưng ngắt trong pha 2 (nhật ký `phase: 2`, `script.json` còn bản cũ) | Như D-13a | Như trên |
| D-14 | Lỗi | Groq giả trả JSON hỏng 3 lần khi `--rewrite` | Mã 12; `script.json` không đổi byte; job `error_kind=rewrite_failed`, câu § 4.4 | Hash + `GET /job` |
| D-15 | Lỗi | Travel `--rewrite` cảnh trả lời ra số không có trong quote (cả lần hỏi lại) | Mã 5; dòng `[FACT_CHECK]`; `script.json` giữ bản cũ | Groq giả |
| D-16 | Lỗi | `PUT .../layout` video sản phẩm bỏ cảnh `cta` / đặt `cta` giữa | 400 "Video sản phẩm cần đúng 1 cảnh Kêu gọi mua ở cuối" | API test |
| D-17 | Lỗi | `PUT .../layout` travel xoá hook, dời outro, 4 answer khi nhóm max 3, answer không `fact_ids` | 400 từng trường hợp | API test |
| D-18 | Lỗi | `--continue` / `--rewrite` trên thư mục không có `stage` | Mã 9, không đổi file | Bản sao thư mục cũ |
| D-19 | Lỗi | Tạo chủ đề: sườn 1 dòng, 13 dòng, dòng 201 ký tự; tên trống; tên 121 ký tự (gửi thẳng API, bỏ qua trang) | 400 trước khi chạy job, không tạo thư mục | API test |
| D-20 | Biên | Sườn đúng 2 dòng và đúng 12 dòng; dòng 200 ký tự | Nhận; số cảnh = số dòng | API + Groq giả |
| D-21 | Biên | Thêm cảnh mới `line` trống rồi `--continue` | Mã 9 "Cảnh N chưa có lời đọc" | Bản sao |
| D-22 | Biên | Chủ đề 0 ảnh | Tạo được; dựng ra nền trơn không lỗi | Bản sao |
| D-23 | Biên | `layout/open` rồi `layout/cancel` không sửa gì | `script.json` trùng byte với trước khi mở; `video.mp4` không đổi; nhãn về "Chờ duyệt đăng"; bản sao lưu bị xoá | Hash |
| D-24 | Biên | Đang chạy `--continue`, gọi `rewrite`, `PUT layout`, `layout/cancel` | 409 "Đang có một việc khác chạy (…)"; `script.json` không đổi | API test |
| D-25 | Hồi quy | Thư mục cũ (không `sid`, có `video.mp4`): sửa câu + Dựng lại (DR-0001), Duyệt & lưu | Như trước: `PUT /videos/{f}` 200, `--render-only` chỉ đọc lại câu đổi, `--approve` chạy | Bản sao thư mục cũ |
| D-26 | Hồi quy | `--render-only` / `--approve` / `--rerender` / `--capcut` khi có `stage`; API `render` / `approve` / `capcut` / `PUT /videos/{f}` khi có `stage` | Mã 9 / 409 "Video đang soạn bố cục…"; Sheet không đổi | CLI + API |
| D-27 | Hồi quy | `--sheet`, `--csv`, `--product`, `--travel --sheet`, `--exercise` (CLI) | Chạy như `main` (không dừng ở bố cục, theo đề xuất Q-1) | So đầu ra trên dữ liệu giả |
| D-28 | Hồi quy | Video chủ đề: dựng + duyệt | Khung hình cuối không có "GIỎ HÀNG", "link tiếp thị"; `post.txt` không có "Thêm liên kết → Sản phẩm"; không tạo dự án CapCut; `_bo_*` và bản sao lưu bị xoá trước khi tải Drive | `review_frames.py` + `grep` |
| D-29 | Hồi quy | API ghi mới thiếu `X-Studio: 1` hoặc Host khác `127.0.0.1`/`localhost` | 403 | API test |
| D-30 | Hồi quy | Tạo sản phẩm từ dòng Sheet (CSV giả) | Dòng ghi `script_review`; `--sheet` lại không làm dòng đó; sau `--continue` → `review` | CSV giả |
| D-31 | Lỗi | D-5 nhưng dựng (FFmpeg giả) lỗi sau khi đã đổi tên; rồi gọi `layout/cancel` | `script.before-layout.json` không còn; `layout/cancel` trả 409 với câu § 4.4; `GET` trả `can_cancel_layout=false`; bất biến C-0014-1 vẫn đúng | Bản sao + API |
| D-32 | Lỗi | `PUT .../layout` với `sid` = `../../x`, `s0`, `s2/a`, `S2`, `s12345`, `sid` không có trong `script.json`, hai cảnh cùng `s2` | 400 từng trường hợp; không file nào được tạo ngoài thư mục | API test + `find` |
| D-33 | Lỗi | Sửa tay `script.json` bản sao cho có `sid` lạ rồi chạy `--continue` | Mã 9 trước khi đụng file (hash toàn thư mục giữ nguyên) | Bản sao |
| D-34 | Lỗi | Gemini giả hết lượt ở D-7; gọi `POST .../continue {revoice_all:"edge"}` | Mọi cảnh đọc lại bằng edge-tts, `tts_provider=edge`, 0 lời gọi Gemini, dựng xong; trước đó `--continue` không cờ trả mã 3 | Đếm lời gọi |
| D-35 | Lỗi | `POST .../image?target=scene` khi có `stage` | 409; không `canh_*` nào đổi | API test |
| D-36 | Biên | Giả lập ghi `script.json` bị ngắt (còn `script.json.tmp`, `script.json` bản cũ nguyên vẹn) | Thư mục vẫn hiện trên Studio với bản cũ | Bản sao + `GET /videos` |
| D-37 | Lỗi | Groq giả cho `--rewrite` lần 1 trả thiếu `sid` được yêu cầu, lần 2 trả `sid` lạ, lần 3 trả `line` 400 ký tự | Mã 12, `script.json` không đổi byte; đúng 3 lời gọi | Groq giả |
| D-38 | Lỗi | Gọi `PUT .../layout` song song với `POST .../continue` (cùng lúc) 20 lần | Mỗi cặp: hoặc PUT xong rồi job chạy, hoặc PUT nhận 409; không lần nào `script.json` bị ghi khi job đang chạy | Script gọi đồng thời |
| D-39 | Hồi quy | `--approve` thư mục có `_bo_*`, `_mv_*` sót, `script.before-layout.json` (Drive giả) | Danh sách file tải lên không có tên nào bắt đầu bằng `_` hay `script.before-layout.json`, `_rename_plan.json` | Drive giả ghi danh sách |
| D-40 | Lỗi | Sườn chứa `<img src=x onerror=alert(1)>`; AI trả lời chứa thẻ HTML | Trang hiện chữ thô, không chạy script | Mở Studio, kiểm DOM |
| D-41 | Biên | Studio: sửa lời cảnh 2 (chưa bấm Lưu) rồi bấm "AI viết lại cảnh 3" | Lời cảnh 2 đã được lưu trước khi job chạy (`script.json` có chữ mới); cảnh 3 được viết lại | Trình duyệt + `jq` |
| D-42 | Biên | Studio: cảnh sản phẩm `cta`, travel hook/outro | Nút ↑ ↓ Xoá mờ, có chú thích lý do; cảnh khác bình thường | Trình duyệt |
| D-43 | Biên | Studio: lượt Gemini còn 2, video cần 5 cảnh | Thanh dưới hiện câu "Không đủ lượt Gemini…" + 2 nút; chọn giọng miễn phí gửi `revoice_all:"edge"` | Trình duyệt + `--tts-status` giả |
| D-44 | Biên | Studio: "AI viết lại cảnh này" xong, bấm "Dùng lại câu cũ" | Lời cảnh về câu trước khi viết lại (sau khi Lưu, `script.json` có câu cũ) | Trình duyệt |

### 10.2 Tài liệu

| # | Tài liệu | Mong đợi |
|---|----------|----------|
| DD-1 | Hướng dẫn vận hành | Mục tạo video bài tập/mẹo/du lịch và "Sửa bố cục": nút, nhãn đúng § 4.4, lượt giọng, thời gian chờ đo được; không có chữ `stage`, `sid`, `exit`, `--continue` |
| DD-2 | `.claude/CLAUDE.md` | Lệnh, mã 9/12, luồng có bước bố cục, `kind: topic`, `layout_rules.py` |
| DD-3 | Spec L3 (3 file § 8) | Khớp tên API, nhãn Studio, luật § 4.3, C-0014-1/10/11 |

### 10.3 E2E

| # | Kịch bản | Mong đợi |
|---|----------|----------|
| V-1 | "Bài tập, mẹo, kiến thức": "Bát Đoạn Cẩm cho dân văn phòng", sườn 5 dòng, 3 ảnh, giọng miễn phí → Viết kịch bản → sửa 1 câu, xoá 1 cảnh, thêm 1 cảnh, AI viết lại 1 cảnh → Dựng video theo bố cục này → xem → Duyệt & lưu | Video 5 cảnh đúng thứ tự sườn đã sửa, không có giỏ hàng; 0 lượt Gemini; Groq = 1 (viết) + 1 (viết lại) |
| V-2 | Sản phẩm từ link (Gemini giả) → bố cục → dựng → thấy sai ý → Sửa bố cục → đổi chỗ 2 cảnh, sửa 1 câu → dựng lại | Lần 1: N lời gọi TTS; lần 2: đúng 1; video theo thứ tự mới |
| V-3 | Du lịch từ Studio: câu hỏi + nguồn, 2 ý → bố cục → thêm số sai → Dựng | Bị chặn với câu tiếng Việt (mã 5); sửa → dựng được; 0 lượt Gemini |
| V-4 | Thư mục cũ (trước DR) mở trên Studio, sửa câu, dựng lại, duyệt | Như DR-0001 |
| V-5 | Điện thoại 390 px: tạo chủ đề + bố cục 12 cảnh | Không cuộn ngang, thanh dưới không che thẻ cuối, nút ↑ ↓ bấm được |
| V-6 | Sửa bố cục video đã dựng → đổi chỗ 2 cảnh → Dựng (đóng cửa sổ `mo-studio.command` giữa lúc dựng) → mở lại Studio → Dựng lại | Video đúng thứ tự mới, giọng đúng cảnh; không còn "Bỏ các chỗ vừa sửa" |
| V-7 | Gemini giả hết lượt khi dựng video sản phẩm → chọn "Dùng giọng miễn phí cho cả video" | Dựng xong cùng ngày, giọng miễn phí cả video |

### 10.4 Cổng chất lượng

- [ ] D-1…D-44 (gồm D-13a/b), DD-1…DD-3, V-1…V-7 đạt; kết quả Tester chép nguyên văn vào § 12.
- [ ] `git diff origin/main -- app.html backend/app/api/creator.py exercise.py capcut_export.py` rỗng.
- [ ] Không vi phạm C-0014-1…14 và các ràng buộc "giữ nguyên" ở § 7.
- [ ] Tài liệu § 8 đối chiếu code (tên lệnh, cờ, nhãn Studio).
- [ ] MKTG chụp 390 px và duyệt chữ § 4.4 trên bản chạy.

---

## Những gì KHÔNG làm

- Cổng ảnh nhân vật, cổng hình/clip, `REVIEW_GATES*`, `--gates`, `--no-gates`, đổi nghĩa `--skip-approval` (DR-0011, làm sau).
- Bước bố cục cho chạy CLI hàng loạt (`--sheet`, `--csv`, `--travel --sheet`) và cho chuỗi bài tập `--exercise` (Q-1, Q-2).
- Tải clip video cho từng cảnh của video chủ đề (chỉ ảnh); cắt clip (DR-0009); thư viện cảnh quay travel (DR-0010).
- Hoàn tác nhiều bước (undo) trong bố cục (chỉ có "Dùng lại câu cũ" cho lần AI viết lại gần nhất và "Bỏ các chỗ vừa sửa").
- Nút xoá bản nháp / "Bỏ video này" (Q-6; DR-0011 Q5 người dùng đã chọn để sau).
- Nút "Dừng việc đang chạy" và giới hạn thời gian job (nợ kỹ thuật, `TODO.md` § 5).
- Thêm dòng vào tab Travel khi tạo du lịch từ Studio.
- Đăng TikTok tự động, đổi `app.html`, scope TikTok, Shopee. Dịch vụ AI trả phí, tạo ảnh bằng API.

---

## 11. Câu hỏi mở cho người dùng

| # | Câu hỏi | Đề xuất của BA | Trả lời |
|---|---------|----------------|---------|
| Q-1 | Bước bố cục chỉ áp dụng cho video **tạo từ Studio**, hay cả chạy hàng loạt `--sheet`/`--csv` (DR-0011 đã chốt là dừng cả hàng loạt)? | Chỉ Studio trong DR này (CLI chạy như cũ, ít rủi ro); phần hàng loạt làm khi làm DR-0011 GĐ 0 đầy đủ | **Chỉ Studio** (2026-11-25) |
| Q-2 | "Bài tập bát thủ cầm": ý bạn là **Bát Đoạn Cẩm** (đã có giáo trình, lời không qua AI, clip làm tay)? Video bài tập tạo bằng ô "Bài tập, mẹo, kiến thức" sẽ do AI viết lời và **chỉ dùng ảnh**, không dùng clip động tác. Như vậy được không, hay bạn muốn Studio sửa/thêm bài trong giáo trình (việc khác, DR riêng)? | Chuỗi giáo trình giữ nguyên; ô mới cho video lẻ; ô "Điều cần tránh" điền sẵn câu an toàn khi có chữ "tập" | **Chưa trả lời**. Làm theo mặc định: chủ đề chung chỉ dùng ảnh, không clip động tác; giáo trình giữ nguyên |
| Q-3 | Giọng mặc định cho video bài tập/mẹo/kiến thức: miễn phí (edge-tts) hay Gemini (1 lượt/cảnh, chung 10 lượt/ngày với video sản phẩm)? | Miễn phí mặc định, để dành lượt Gemini cho video bán hàng; đổi được trên form | **Miễn phí (edge-tts) mặc định** |
| Q-4 | Tạo video **sản phẩm** trên Studio cũng dừng ở bố cục (thêm 1 lần bấm, nhưng không tốn lượt giọng trước khi bạn xem)? | Có, đúng tinh thần DR-0011 đã duyệt | **Có** |
| Q-5 | Thứ tự làm: (a) bố cục + quay lui cho sản phẩm, (b) bài tập/mẹo/kiến thức, (c) du lịch từ Studio. Làm hết trong 1 PR hay chia? | 1 issue #38, Dev giao theo thứ tự a → b → c; nếu c kéo dài thì tách PR riêng | **Chia 2 PR**: PR này = (a) + (b); du lịch (c) PR sau |
| Q-6 | (MKTG #18) Bản nháp "Đang soạn bố cục" tạo nhầm sẽ nằm mãi trong danh sách. Thêm ngay nút **"Xoá bản nháp chưa dựng"** (chỉ thư mục chưa có `video.mp4`, hỏi xác nhận 2 lần, không đụng video đã dựng)? Đây là thao tác xoá; lần trước (DR-0011 Q5) bạn chọn để sau | Thêm, vì chỉ xoá bản nháp chưa tốn giọng/dựng; nếu không, hướng dẫn vận hành ghi cách dọn tay | **Để sau** (ghi nợ `TODO.md` § 5; hướng dẫn vận hành ghi cách dọn tay) |

---

## 12. Kết quả

### 12.1 Việc đã làm (PR 1: sản phẩm + chủ đề chung, nhánh `feat/issue-38-studio-topic-layout`)

| Việc | Trạng thái |
|------|-----------|
| `layout_rules.py` (luật bố cục, `sid`, `norm_line`, làm sạch sườn) + `scripts/selfcheck_layout.py` | Xong |
| `demo.py`: `stage`, `sid`, `--continue [--revoice-all edge]`, `--rewrite`, nhật ký đổi tên, `run_topic`, cảnh `topic`/`outro`, `post.txt` chủ đề, mã 9/12, chặn 4 lệnh khi có `stage`, ghi JSON nguyên tử, `image_slot` trong `render_video` | Xong |
| `drive_upload.py`: bỏ qua mọi tên bắt đầu `_` và `script.before-layout.json` | Xong |
| `api/studio.py` + `studio.html`: API § 4.2 (trừ `/travel-options`), khoá job, 409, giao diện bố cục, form "Bài tập, mẹo, kiến thức" | Xong |
| Du lịch từ Studio (`kind: travel`, luật bố cục travel, `/travel-options`, D-3/D-15/D-17/V-3) | **Chưa làm**, PR sau (Q-5). Studio trả 400 "Loại video chưa hỗ trợ"; thư mục travel mở bố cục trả 409; ô Du lịch trên form mờ, ghi "Sắp có trên Studio" |

### 12.2 Review và cách xử lý (2 vòng sửa)

- **Reviewer + Tech Lead, Chặn**:
  - A1: nhật ký đổi tên gán `audio_path` theo vị trí lúc chạy lại; nếu bị ngắt rồi người sửa bố cục thì cảnh nhận sai giọng. Sửa bằng cách thêm khoá `final` (sid → vị trí) vào nhật ký. Danh sách cảnh khác lúc bị ngắt thì trả mã 9. Thêm ca D-13c.
  - B1: còn nhật ký đổi tên mà Studio vẫn cho sửa bố cục. Sửa: `PUT layout`/`rewrite`/`cancel` trả 409 "Lần dựng trước bị ngắt giữa chừng…"; trang khoá ô sửa.
- **Nên sửa, đã sửa**:
  - Dùng chung `norm_line` ở `demo.py` và Studio (để khoảng trắng thừa không bị đọc lại tốn lượt).
  - `image_slot` được dùng khi dựng.
  - Tải ảnh sản phẩm trả 409 khi đang soạn bố cục (vì "Bỏ các chỗ vừa sửa" không chép lại `product.json`).
  - `--continue --revoice-all` chỉ nhận `edge`.
  - `run_topic` gọi Groq trước khi tạo thư mục.
  - Dời mọi đuôi `canh_N.*`.
  - Lần đọc giọng đầu cất `audio_*`/`canh_*` lạ thành `_bo_*`.
  - Kiểm `stage` trong khoá job.
- **Marketing** (chế độ 2, đọc mã): 3 mục Chặn cũ đã vào giao diện. Các Nên sửa N1–N6 đã xử lý ở vòng 1:
  - Chữ xác nhận xoá cảnh nay đúng hành vi.
  - Nút "Lưu" đổi thành "Lưu bố cục", có nhắc "Dựng sẽ tự lưu".
  - Câu lỗi mã 5 và 409.
  - Nút trên điện thoại cao ≥ 44 px.
  - Không ghi số phút chờ vì chưa đo.
  - Từ trang tạo video tới video chủ đề: tối đa 6 lần bấm, 2 lần chờ.
- **Không làm trong PR này** (ghi `TODO.md` § 5):
  - Tech Lead #7: đọc ảnh tải lên 15 MB một lần vào bộ nhớ.
  - Nút "Dừng việc đang chạy".
  - Bản nháp bỏ dở.
  - Đọc lại giọng sau khi bị ngắt ở lần đọc đầu.
  - Bug `--csv` làm lại dòng `script_review`/`review`: có từ trước, không do #38; người điều phối đã ghi issue #39.

### 12.3 Chỗ code khác DR (DR đã sửa cho khớp, hoặc ghi lại đây)

| Chỗ trong DR | Code thực tế |
|--------------|--------------|
| § 2.3 nhật ký `_rename_plan.json` | Thêm khoá `final` (sid → vị trí mới), `meta` (sid → `audio_line`, `duration`, `tts_model` của giọng mới), `tts_provider`; khoá ảnh dạng `"<sid>:img:<ext>"`; khoá file cảnh xoá dạng `a<k>` (audio) / `i<k>` (ảnh). Đã sửa § 2.3 |
| § 2.6, C-0014-4: tên file cảnh xoá `_bo_audio_<sid>` | `_bo_audio_<k>.mp3` và `_bo_canh_<k+1>.<ext>` theo số cũ (trùng thì thêm `_1`…). Đã sửa § 2.6, D-6 |
| § 4.2 `PUT .../layout` nhận giá | **Không nhận `price`**. Giá sửa ở màn hình thường sau khi dựng (như DR-0007) |
| § 4.2 cảnh gửi lên có `kind` | Cảnh đã có `sid` **giữ `kind` cũ** (bỏ qua `kind` trình duyệt gửi); chỉ cảnh mới bị kiểm `kind` |
| D-14 "`script.json` không đổi byte" sau mã 12 | `rewrite_request` (Studio ghi trước khi chạy) còn lại trong `script.json`; nội dung cảnh, hook, caption không đổi. Studio xoá `rewrite_request` ở lần Lưu bố cục kế tiếp. Giữ D-14 với nghĩa "kịch bản không đổi" |
| § 4.1 `--continue --revoice-all` | Chỉ nhận `edge`; `gemini` bị từ chối (CLI lỗi tham số, API 400) |
| § 2.3 `file_order` | Đã bỏ từ bản sửa 1; code không có trường này |
| § 4.2 `/travel-options` | Chưa làm (thuộc PR du lịch) |

### 12.4 Kết quả test (Tester, chép từ báo cáo `test-38.md`; không sửa chữ "Kết quả")

Cách chạy: TestClient + `demo.py` thật của worktree qua lớp giả Groq/TTS/Gemini (đếm lời gọi); không Gemini/Drive/Sheet/TikTok/Groq thật. Hash toàn bộ `storage/videos` của repo gốc trước/sau không đổi. Đối chứng `scripts/selfcheck_layout.py`: ALL OK.

| ID | Kết quả |
|----|---------|
| D-1, D-2, D-4, D-5 (không đo độ dài video: render giả), D-6, D-7, D-8, D-9 | PASS |
| D-10 | PASS (nhờ selfcheck dev) |
| D-11 (story dời `canh_N`) | **Cần người kiểm** |
| D-12 | PASS |
| D-13a/b (giết tiến trình tại 12 điểm đổi tên khác nhau, chạy lại đều exit 0, audio đúng cảnh) | PASS |
| D-13c (ngắt rồi sửa bố cục, thêm ở vòng sửa 1) | PASS (theo người điều phối; selfcheck dev) |
| D-14 | PASS (xem Ghi chú N-1: `rewrite_request` còn trong `script.json`) |
| D-16, D-18, D-19, D-20, D-21, D-22, D-23, D-24 | PASS |
| D-25 (hồi quy video cũ, gồm sandbox-render `--render-only` thật, `original_unchanged: true`) | PASS |
| D-26 (`--render-only/--approve/--rerender/--capcut` exit 9; API 409 "Video đang soạn bố cục…") | PASS |
| D-27 | PASS (một phần: chỉ `--product`) |
| D-28 | PASS (nội dung thật cần người xem) |
| D-29, D-30, D-31, D-32, D-33, D-34 (`revoice_all=gemini` = 400), D-35, D-36, D-37 | PASS |
| D-38 | PASS (một phần) |
| D-39 | PASS (nhờ selfcheck) |
| D-40, D-41, D-43, D-44 | **Cần người kiểm** (giao diện) |
| D-42 | PASS (API) / Cần người kiểm (UI) |
| D-3, D-15, D-17 | Không áp dụng (du lịch, PR sau) |
| Ảnh sản phẩm khi đang soạn bố cục (vòng sửa 1, B2) | PASS (409) |
| `norm_line` dùng chung (vòng sửa 1) | PASS |
| `image_slot` dùng khi dựng (vòng sửa 1) | PASS |
| V-1 | PASS (API) / UI Cần người kiểm |
| V-2 | PASS (tương đương) |
| V-3 | Không áp dụng |
| V-4 | PASS |
| V-5 (390 px) | **Cần người kiểm** |
| V-6 | PASS (tương đương) |
| V-7 | PASS (API) / UI Cần người kiểm |

Ghi chú của Tester (không phải FAIL): N-1 `rewrite_request` còn sau mã 12; N-2 `kind` cảnh cũ bị bỏ qua; N-3 `--csv` làm lại dòng `script_review` (bug có từ trước, issue #39); N-4 `--rerender` in thêm `Studio folder:`; N-5 sổ lượt Gemini ghi theo đường dẫn của `demo.py`, test có thể ghi vào sổ thật. Bug ngoài phạm vi: không có.

**Còn chờ người dùng tự kiểm**: giao diện thật trên máy (D-40, D-41, D-42 UI, D-43, D-44, V-5 390 px), nghe giọng một video chủ đề thật, D-11 (video story có ảnh nhân vật rồi dời cảnh).

---

## 13. Xử lý review DR (2026-11-25)

Nguồn: báo cáo Tech Lead (15 mục) và Marketing chế độ 2 (26 mục) trên bản đề xuất đầu.

| Mục | Mức | Xử lý | Chỗ trong DR |
|-----|-----|-------|--------------|
| TL #1 Huỷ sau khi đã đổi tên file | Chặn | Nhận | C-0014-10, § 2.6 bước 4, D-31, V-6 |
| TL #2 Đổi tên 2 pha không phục hồi chắc | Chặn | Nhận (nhật ký `_rename_plan.json`) | C-0014-11, § 2.6 bước 1, 5, D-13a/b |
| TL #4 `sid` từ trình duyệt vào tên file | Chặn | Nhận | C-0014-12, D-32, D-33 |
| TL #3 Ghi JSON không nguyên tử | Nên sửa | Nhận | C-0014-13, D-36 |
| TL #5 Tải ảnh cảnh khi đang soạn bố cục | Nên sửa | Nhận | C-0014-9, § 2.4, § 4.2, D-35 |
| TL #6 `--rerender`, `--capcut` khi có `stage` | Nên sửa | Nhận | C-0014-9, § 4.1, D-26 |
| TL #7 Kiểm job ngoài khoá | Nên sửa | Nhận | C-0014-14, D-38 |
| TL #9 Kẹt khi hết lượt Gemini | Nên sửa | Nhận (`--continue --revoice-all edge`) | C-0014-3, § 4.1, D-34, V-7 |
| TL #8 Bản đồ cảnh↔file ở 3 nơi | Gợi ý | Nhận: bỏ `file_order`, dùng `audio_path` | § 2.3, phương án F, C-0014-1 |
| TL #10 Rewrite ghép theo vị trí | Gợi ý | Nhận: theo `sid`, qua `layout_rules.py` | § 4.1, C-0014-5, D-37 |
| TL #11 Giới hạn ở server, `esc()` | Gợi ý | Nhận | C-0014-14, § 4.2, D-19, D-40, R-10 |
| TL #12 Drive tải file tạm | Gợi ý | Nhận (bỏ qua mọi tên bắt đầu `_`) | C-0014-4, D-39 |
| TL #14 Luật bố cục ở 2 nơi | Nợ | Nhận ngay (module nhỏ, chỉ stdlib) | `layout_rules.py`, § 4.3, § 9 |
| TL #13 Thư mục lỗi / bỏ dở | Nợ | Việc sau, ghi `TODO.md` § 5; phần nút xoá hỏi người dùng | Q-6 |
| TL #15 Job không timeout / không huỷ | Nợ | Việc sau, ghi `TODO.md` § 5 | "Những gì KHÔNG làm" |
| MKTG #1 Mất chữ chưa lưu | Chặn | Nhận (tự lưu trước mọi thao tác) | § 2.4, D-41 |
| MKTG #2 Hai tên nút Huỷ, không xác nhận | Chặn | Nhận: "Bỏ các chỗ vừa sửa" + xác nhận | § 2.4, § 4.4 |
| MKTG #3 Hai chữ "Duyệt" | Chặn | Nhận: "Dựng video theo bố cục này", dải bước mới | § 2, § 4.4 |
| MKTG #4 Nhãn loại mơ hồ | Nên sửa | Nhận, gộp thành 3 ô (cả đề xuất gộp tầng) | § 2.1 |
| MKTG #5, #6, #7, #8 Chữ form | Nên sửa | Nhận | § 2.2 |
| MKTG #9, #12, #13, #21, #22 Thẻ cảnh | Nên sửa | Nhận (44 px là đề xuất, Dev đo) | § 4.4, D-42, V-5 |
| MKTG #10, #11 AI viết lại | Nên sửa | Nhận | § 2.4, D-44 |
| MKTG #14, #15 Lượt Gemini, lỗi giọng | Nên sửa | Nhận | § 4.4, D-43, V-7 |
| MKTG #16 Câu lỗi | Nên sửa | Nhận | § 4.4 |
| MKTG #17 Xác nhận Sửa bố cục | Nên sửa | Nhận | § 2.5, § 4.4 |
| MKTG #18 Xoá bản nháp | Nên sửa | **Chưa nhận**: là thao tác xoá, người dùng đã chọn để sau ở DR-0011 Q5, nên hỏi lại | Q-6 |
| MKTG #19 Nhãn danh sách | Nên sửa | Nhận (đổi cả nhãn cũ "Chờ duyệt") | § 4.4, `supersedes` |
| MKTG #20 Thời gian chờ | Nên sửa | Nhận; số phút do Dev đo, DR không ước đoán | § 2.2, việc #8 |
| MKTG #23 Điền sẵn "Điều cần tránh" | Gợi ý | Nhận | § 2.2 |
| MKTG #24 "Danh mục" → "Giọng đọc" | Gợi ý | Nhận cho ô bài tập/mẹo/kiến thức | § 2.2 |
| MKTG #25 Chữ `script_review` trên Sheet | Gợi ý | Nhận (ghi trong hướng dẫn vận hành) | § 2.5, § 8 |
| MKTG #26 Dòng "Bước tiếp theo" | Gợi ý | Nhận | § 2.2 |
| MKTG "mặc định loại gần nhất" | Gợi ý | Nhận (`localStorage`) | § 2.1 |

---

## Liên quan

- DR-0001 (Studio sửa câu, C-0001-1/2/3), DR-0007 (Tạo video mới, C-0007-x), DR-0008 (travel mã thoát, edge-tts), DR-0011 (cổng duyệt trước khi dựng, bị mở rộng), DR-0012 (quota Gemini, C-0012-1), DR-0013 (CapCut, C-0013-1). DR-0009, DR-0010: đang đề xuất, xem R-3.
- Code: `demo.py` (`run_create`, `run_one`, `generate_script`, `generate_voiceovers`, `revoice_changed`, `render_video`, `save_script`, `render_only`, `approve`), `travel.py` (`run_row`, `_run_row_body`, `write_and_check`, `check_script`, `render_only`), `backend/app/api/studio.py`, `backend/app/api/studio_travel.py`, `backend/app/web/studio.html`, `drive_upload.py`, `capcut_export.py`, `scripts/audio_seams.py`.
- Review: báo cáo Tech Lead và Marketing ngày 2026-11-25 (§ 13).
- Issue: #38.
