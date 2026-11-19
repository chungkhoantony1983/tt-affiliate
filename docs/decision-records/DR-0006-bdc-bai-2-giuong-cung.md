# DR-0006: Video bài 2 (Giương cung bắn chim) của chuỗi Bát Đoạn Cẩm

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📋 Đề xuất (bản 3: thêm câu chào và câu nối bài trước ở cảnh 1), chờ người dùng duyệt bản cuối | 2026-11-14 | Claude (BA) | — |

Capability: `video-render` · Nhánh: `feat/bdc-bai-2` (đã ở `f65abc1`) · Loại: sửa nội dung giáo trình + sửa nhỏ `exercise.py` + vận hành + tài liệu

Vai trò: **BA** = DR, tài liệu · **Dev** = Dev-1 … Dev-8 · **Reviewer** = soát diff · **Tester** = chạy thử trên bản sao · **MKTG** = review bản dựng · **Người vận hành** = làm clip, chạy lệnh, nghe, gõ `y/n` · **Người điều phối** = git, đọc log thay người vận hành.

Yêu cầu nguyên văn (2026-11-13): "tiếp tục tạo video bát đoạn cẩm bài số 2".

> **Người vận hành chỉ cần đọc bảng V-1 … V-10 ở mục "Các bước vận hành".** Phần còn lại dành cho Dev, Tester, người điều phối.

> **Số DR.** DR-0006 vì các worktree khác đang có DR chưa commit: hai file DR-0002 (`clip-trim`, `gemini-quota`), DR-0003 (`cta-safe-zone`), DR-0004 (`agent-skills`), DR-0005 (`bdc-intro-video`). `origin/main` chỉ có DR-0001.

---

## Bối cảnh

**Vấn đề (gốc rễ)**: chuỗi Bát Đoạn Cẩm đã có video mở đầu và bài 1. Việc kế tiếp là bài 2. Bài 2 chưa có clip, và là bài đầu tiên dùng khung góc phụ (`angles`), tính năng chưa từng chạy thật.

### Người dùng đã quyết (2026-11-13/14)

| # | Quyết định | Hệ quả trong DR |
|---|-----------|-----------------|
| U-1 | Hai commit "update file" (`6940efc`, `f65abc1`) là của người dùng. Không có cửa sổ nào khác đang làm bài 2 | Dùng bản `f65abc1`. Nhánh đã được đưa lên `f65abc1` |
| U-2 | "làm bằng edge-tts cũng được" | Bài 2 thu giọng bằng edge-tts, **0 lượt Gemini** |
| U-3 | Đồng ý dời khung góc phụ và rút gọn chữ bước 1, 2 | Dev-1, Dev-2 là việc chính thức |
| U-4 | Câu bước 4: "viết dài hơn" | Đổi lời đọc bước 4 (Dev-3); nguyên văn chờ duyệt ở Q-B |
| U-5 | Cảnh 1: mở bằng câu chào thân thiện "chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm", rồi câu dẫn nối từ bài 1 | Dev-8. Đóng câu hỏi hook (Q-A của bản 2). MKTG lưu ý: câu chào đứng trước làm câu gợi tò mò đến muộn hơn với người xem mới. Người dùng chủ động chọn vì mục tiêu là người xem nhớ kênh và chuỗi bài. **Đây là quyết định của người dùng, không còn là câu hỏi mở** |
| U-6 | Người dùng tự tạo clip trong app Gemini | Các bước V-2 … V-4 giữ nguyên |

### Hiện trạng đã kiểm (code `f65abc1`; sha256 `exercise.py` bắt đầu `95bea417abb71833`, `demo.py` `c4c706cc922f4a4e`)

| # | Sự việc | Nguồn kiểm |
|---|---------|-----------|
| H-1 | Bài 2 trong giáo trình: 4 bước, `reps` "Mỗi bên 3 lần", `careful` "Gối không vượt quá mũi chân.", `angles = {"2": "back"}`, `done = false` | `content/exercise_curriculum.json` → `series[bdc].moves[1]` |
| H-2 | Video bài 2 có **6 cảnh**: chuẩn bị, 4 bước, kết. Lời đọc ghép nguyên văn từ giáo trình, không qua AI | `exercise.py` → `build_script()` (đã chạy hàm, không ghi file) |
| H-3 | Bài 2 cần **5 clip**: `02_1.mp4` … `02_4.mp4` (nhìn từ trước) và `02_2_back.mp4` (bước 2 nhìn từ sau). `00.mp4` dùng chung, đã có | `scene_clip_files()`, `_angle_wanted()` |
| H-4 | `storage/clips/bdc/` chưa có `02_*.mp4`, chưa có `prompts_02.txt`. Clip đang có đều 720×1280, 24 khung/giây; `00.mp4` dài 3,42 giây, clip bước khoảng 10 giây | `ls`; `ffmpeg -i` |
| H-5 | Không có clip bước nào: `demo.py --exercise` ghi `prompts_02.txt` rồi dừng (`needs_clips`), không thu giọng | `run_next()` |
| H-6 | Có ít nhất một clip bước: máy **đi tiếp, thu giọng**, bước thiếu mượn clip bước trước. Thiếu `02_2_back.mp4`: video ra không có khung góc phụ, **không báo gì** | `scene_clip_files()`, `scene_angle_files()` |
| H-7 | Máy chọn bài 2 khi video mở đầu và bài 1 đã `done`. Giáo trình `f65abc1` (repo gốc và nhánh này) thoả | `next_item()`; giáo trình |
| H-8 | **Ép edge-tts**: đặt `TTS_PROVIDER=edge` trước lệnh. Biến đặt trên dòng lệnh thắng `.env` (`load_env` dùng `setdefault`). Không có cờ riêng. Giọng `nam_bac` → `vi-VN-NamMinhNeural` | `demo.py` → `tts_provider()` dòng 382, `load_env()`, `_tts()` |
| H-9 | Giọng narrator của edge-tts đang đặt **nhanh hơn 10 %** (`VOICES["narrator"]` = `+10%`), dùng chung cho video sản phẩm. Không có tốc độ riêng theo loại cảnh. Đo trên video mở đầu (edge-tts): 182 từ / 44,6 giây ≈ 4,1 từ/giây | `demo.py` dòng 49–50; `script.json` video mở đầu |
| H-10 | Video mở đầu ngày 13/11 là giọng edge-tts (audio 48 kb/s, `tts_model = null`). Bài 2 dùng edge-tts thì cùng bộ giọng với video mở đầu. Giọng của bài 1: chưa rõ (thư mục không còn trên máy) | `storage/videos/20261113_183051_baitap_bdc_00_gioithieu/` |
| H-11 | Duyệt bằng `y/n` trên Terminal; chỉ `y`/`Y` là duyệt. Duyệt thì ghi `post.txt`, đặt bài 2 `done = true`, tải lên Drive `Bài tập - Bát Đoạn Cẩm/<thư mục>`, xoá thư mục trên máy | `finish()`; `demo.py` → `approval_step()`, `move_to_drive()` |
| H-12 | `--exercise-rerender` không thu giọng, lấy clip mới nhất trong `storage/clips/bdc/`, nhưng lấy **chữ** từ `script.json` của thư mục video, không đọc lại giáo trình | `rerender()` |
| H-13 | Cảnh bước không có chữ rút gọn: chữ trên hình là nguyên câu đọc. Cảnh "Chuẩn bị" lấy chữ từ `series.prepare`, cũng là lời đọc, dùng chung 8 bài | `build_script()`; `_overlay()` |
| H-14 | Bài 2 đã có miễn trừ ở lời kết, trên hình cảnh kết và trong caption | `build_script()`; `_overlay()` nhánh `ex_end` |
| H-15 | Cảnh ngắn hơn clip: máy chỉ phát **đoạn đầu** clip, dài bằng cảnh. Cảnh dài hơn clip: chạy chậm tối đa 1,6 lần, rồi phát tới-lui | `_clip_input()`, `MAX_SLOWDOWN` |
| H-16 | Prompt máy viết mở bằng "Over about eight seconds he …", trái với H-15 khi cảnh chỉ 3–5 giây. File prompt còn in dòng "Hết lượt… làm trước các clip lẻ 1, 3: clip thiếu sẽ mượn clip khác", khuyến khích đúng tình huống H-6 | `exercise.py` dòng 255, 261, 342 |
| H-17 | Bản `exercise.py` `f65abc1` (cắt khoảng lặng, hoà hình 0,3 giây, 24 khung/giây, che dấu ✦) đã chạy thật một lần với video mở đầu. Chưa từng chạy với khung góc phụ, cảnh `ex_end`, hay `00.mp4`. Chưa qua Reviewer | `script.json` video mở đầu có `speech_trim`; U-1 |

**Kiểm lại trên `f65abc1` so với bản 1 của DR**: mã băm `exercise.py` trùng bản đã đọc hôm 13/11; số đo chữ của bài 2 không đổi (1655, 1633, 1634, 1555, 1479, 1602); `_angle_wanted()` không đổi. Khác: giáo trình trong nhánh giờ đã có `intro_video.done = true`, nên chạy thử trong bản sao của nhánh sẽ ra bài 2 (trước đây ra video mở đầu).

### Chữ trên hình (đo bằng `exercise._overlay()` với font thật, không ghi file)

Mốc **tạm** từ DR-0003 (chưa duyệt, đo trên một ảnh chụp iPhone): đáy an toàn y = 1570; cột nút phải của TikTok từ x ≈ 907, y ≈ 1053 trở xuống; máy dài cắt 54 px mỗi bên.

| Cảnh | Hiện tại: số dòng, mép dưới | Sau Dev-2/Dev-3: chữ trên hình | Số dòng, mép dưới |
|------|:---------------------------:|--------------------------------|:-----------------:|
| 1 Chuẩn bị | 3 dòng, 1655 | "Chân rộng bằng vai · gối hơi chùng · vai thả lỏng · thở đều" | 2 dòng, **1578** (vượt mốc tạm 8 px) |
| 2 Bước 1/4 | 3 dòng, 1633 | "Bước chân trái sang ngang, chùng gối vừa sức, hai tay bắt chéo trước ngực." | 2 dòng, 1556 |
| 3 Bước 2/4 | 3 dòng, 1634 | "Tay trái dựng ngón trỏ, đẩy sang trái; tay phải kéo về vai phải như kéo cung." | 2 dòng, 1557 |
| 4 Bước 3/4 | 2 dòng, 1555 | Giữ nguyên câu đọc | 2 dòng, 1555 |
| 5 Bước 4/4 | 1 dòng, 1479. Câu mới (22 từ) nếu để nguyên làm chữ: 3 dòng, 1633 | "Thu tay, đứng lên. Đổi bên: tay phải đẩy ngón trỏ, tay trái kéo dây cung." | 2 dòng, 1556 |
| 6 Kết | 1 + 1 dòng, 1602 | Không đổi | 1602 (vượt 32 px, như bài 1 đã duyệt: 1601) |

- Tiêu đề "Bài 2: Giương cung bắn chim" xuống 2 dòng, mép dưới y = 360, chạm sát mép trên khung clip. "Bài 2: Giương cung" thì 1 dòng.
- Gợi ý MKTG 1.5 (thêm "Lưu video để tập theo" vào cảnh 6): **không nhận**. Cảnh 6 đã vượt mốc 32 px; thêm một dòng cỡ 34 (cao 43 px + khoảng cách) đẩy xuống khoảng 1655.

### Khung góc phụ

- Hiện tại: rộng 250, cao 444 (clip 720×1280), ở x 816–1066, y 836–1280, nhãn ở y ≈ 792. Theo mốc tạm, phần x ≥ 907 và y ≥ 1053 nằm dưới cột nút; phần x > 1026 bị cắt trên máy dài.
- Clip chính 720×1280 đặt vừa khung cao 920 nên rộng 518 px, chiếm x 281–799. Bên trái còn dải x 0–281.
- Đặt **bên trái** (đề xuất MKTG 2.7), giữ bề rộng 250, mép trái x = 60 (ngoài phần bị cắt 54 px): khung chiếm x 60–310, **đè 29 px** lên mép trái của clip chính (phần nền, ở nửa dưới khung clip). Muốn không đè chút nào thì khung chỉ còn rộng 221 px; MKTG yêu cầu không thu nhỏ. BA chốt: bên trái, rộng 250, cho phép đè tối đa 30 px. Bên trái không có nút TikTok nên giữ canh đáy như cũ (y 836–1280).

**Điều chưa biết**: giọng của bài 1; thời lượng thật của bài 2; số lượt tạo video mỗi ngày trong app Gemini; vị trí chữ và khung nhỏ trên điện thoại thật.

**Ràng buộc**: chi phí $0 (P02). Lời đọc lấy nguyên văn giáo trình đã duyệt. Một video một bộ giọng (C-0001-1). Không đụng `demo.py`, Studio, `app.html` (C-0001-4). Video bài tập không gắn sản phẩm.

---

## Quyết định

> **Sửa giáo trình bài 2 và sửa nhỏ `exercise.py` (Dev-1 … Dev-8) trước, vì đổi lời bước 4 và đổi prompt phải có trước khi làm clip và thu giọng. Sau đó: người vận hành ghi `prompts_02.txt`, làm đủ 5 clip, thu giọng bằng edge-tts (`TTS_PROVIDER=edge`, $0, 0 lượt Gemini), lần đầu gõ `n`; MKTG xem bản dựng; dựng lại; người vận hành gõ `y`.**

Thứ tự này khác bản 1 của DR (vận hành trước, Dev sau) vì U-4 và góp ý MKTG 1.3, 2.1–2.3 đổi chính nội dung prompt: làm clip theo prompt cũ là tốn lượt tạo video cho clip sẽ phải làm lại.

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Dev sửa giáo trình + `exercise.py` → làm clip theo prompt mới → edge-tts → `n` → review → dựng lại → `y` | ⭐ | $0. Prompt và lời đúng ngay từ lần làm clip đầu. Không phụ thuộc lượt Gemini |
| B | Vận hành ngay bằng `f65abc1`, sửa sau | - | Prompt hiện tại cho tấn thấp, "eight seconds", `02_4` có "khép chân" (H-16, MKTG 1.3, 2.1–2.3); lời bước 4 sắp đổi. Clip và giọng làm bây giờ phải làm lại |
| C | Giọng Gemini | - | Người dùng chọn edge-tts (U-2). Hôm 13/11 hai model giọng bài tập đều lỗi lúc 18:30 |
| D | Giảm tốc độ đọc bằng cách sửa `VOICES` trong `demo.py` | - | Ngoài phạm vi (không đụng `demo.py`) và đổi luôn giọng video sản phẩm. Thay bằng Dev-6 trong `exercise.py` |
| E | Khung góc phụ lên góc trên phải (đề xuất của BA ở bản 1) | - | Vẫn sát cột nút và mép bị cắt; phải thu nhỏ còn khoảng 220 px. Bên trái không có nút, giữ được 250 px |

---

## Thay đổi cấu trúc

### Giáo trình `content/exercise_curriculum.json` (nguyên văn, trước → sau)

| Trường | Trước | Sau |
|--------|-------|-----|
| `series[bdc].welcome` (mới; câu chào đầu mỗi video bài, từ bài thứ hai của chuỗi) | không có | "Chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm." |
| **Lời đọc cảnh 1 của bài 2** (máy ghép, không phải một trường) | "Bát Đoạn Cẩm, bài 2: Giương cung bắn chim. Đứng thẳng, hai chân rộng bằng vai, gối hơi chùng, vai thả lỏng, thở đều bằng mũi." | "Chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm. Hôm qua mình tập Hai tay nâng trời, hôm nay mình tập bài 2, Giương cung bắn chim. Đứng thẳng, hai chân rộng bằng vai, gối hơi chùng, vai thả lỏng, thở đều bằng mũi." |
| `moves[1].steps[3]` (**lời đọc** bước 4) | "Thu tay, đứng lên, làm sang bên phải." | "Thu tay, đứng lên. Rồi đổi bên: bước chân phải sang ngang, tay phải đẩy ngón trỏ, tay trái kéo dây cung." |
| `moves[1].screens` (mới; chữ trên hình của 4 bước, ô trống = dùng câu đọc) | không có | `["Bước chân trái sang ngang, chùng gối vừa sức, hai tay bắt chéo trước ngực.", "Tay trái dựng ngón trỏ, đẩy sang trái; tay phải kéo về vai phải như kéo cung.", "", "Thu tay, đứng lên. Đổi bên: tay phải đẩy ngón trỏ, tay trái kéo dây cung."]` |
| `series[bdc].prepare_screen` (mới; chữ trên hình cảnh "Chuẩn bị", dùng cho mọi bài của chuỗi) | không có (dùng `prepare`) | "Chân rộng bằng vai · gối hơi chùng · vai thả lỏng · thở đều" |
| `moves[1].steps_en[0]` | "steps the left foot out to the side into a wide stance with knees bent as if riding a horse, crossing both wrists in front of the chest" | "steps the left foot out to the side into a shallow, comfortable horse stance, knees only slightly bent and not past the toes, crossing both wrists in front of the chest" |
| `moves[1].steps_en[1]` | "slowly extends the left arm to the left with the index finger pointing up, while the right hand pulls back to the right shoulder as if drawing a bow string" | "starts in a shallow horse stance with wrists crossed in front of the chest, then slowly extends the left arm to his left with the index finger pointing up, while the right hand pulls back to the right shoulder as if drawing a bow string" |
| `moves[1].steps_en[2]` | "holds the bow-drawing pose, eyes looking at the left index finger" | "is already, from the first frame, in a shallow horse stance, left arm fully extended to his left with the index finger pointing up, right fist pulled back beside the right shoulder with the elbow out; he holds still and turns his head to look at the left index finger" |
| `moves[1].steps_en[3]` | "releases the pose, straightens up, brings the feet together, then does the same bow-drawing motion to the right side" | "starts standing upright, then steps the right foot out into a shallow horse stance, extends the right arm to his right with the index finger up while the left hand pulls back to the left shoulder" |

Không đổi: `prepare`, `reps`, `careful`, `cue`, `angles`, `steps[0..2]` của bài 2; mọi trường của bài 1, 3–8, video mở đầu, tổng kết.

Hệ quả của câu bước 4 mới: lời kết vẫn "Làm mỗi bên 3 lần." (không đổi). `cue` "Ngồi tấn, một tay đẩy ngón trỏ, một tay kéo dây cung." vẫn đúng.

**Lời cảnh 1 mới, lý do chọn câu chữ** (so với đề xuất "…hôm nay mình Giương cung bắn chim"):
- Câu nối do máy ghép theo mẫu `Hôm qua mình tập {tên bài trước}, hôm nay mình tập bài {số}, {tên bài này}.` Có chữ "tập" ở cả hai vế vì mẫu phải đọc xuôi với mọi tên bài: "hôm nay mình Một tay nâng trời", "hôm nay mình Nhón gót" nghe cụt; "hôm nay mình tập bài 3, Một tay nâng trời" thì ổn. Mẫu này cùng kiểu với câu kết đang có: "Ngày mai mình tập bài 3, Một tay nâng trời nhé."
- Bỏ câu "Bát Đoạn Cẩm, bài 2: Giương cung bắn chim." vì câu chào đã nêu tên chuỗi, câu nối đã nêu số bài và tên bài; giữ lại là đọc tên bài hai lần liền nhau. Số bài vẫn được **đọc lên** ("bài 2") cho người chỉ nghe, không chỉ nằm ở tiêu đề.
- Phần tư thế chuẩn bị giữ nguyên từng chữ.
- "Hôm qua" giả định **mỗi ngày đăng một bài, đúng thứ tự**, giống giả định của câu kết "Ngày mai…". Đăng cách ngày thì câu này sai với người xem.
- Áp dụng khi **dựng mới** bài thứ hai trở đi của chuỗi có `welcome` (Bát Đoạn Cẩm: bài 2–8). Bài 1 (không có bài trước) và chuỗi chưa có `welcome` giữ mẫu cũ. Video mở đầu, tổng kết không đổi. Dựng lại video cũ (`--exercise-rerender`) lấy lời từ `script.json` nên không tự chèn câu chào (H-12).

**Ảnh hưởng tới cảnh 1** (ước tính, không phải số đo):
- Lời cảnh 1 từ 26 từ lên 48 từ. Tốc độ edge-tts đo được là 4,1 từ/giây ở mức `+10%` (H-9). Nếu Q-C chốt −10 % và coi tốc độ tỉ lệ thuận với mức đặt: 4,1 × 0,9 ÷ 1,1 ≈ 3,4 từ/giây → cảnh 1 dài khoảng **14–15 giây** (48 ÷ 3,4 + 0,25). Ở mức `+10%` hiện tại: khoảng 12 giây. Trước đây: khoảng 6,5 giây.
- Hình cảnh 1 là `00.mp4` (đứng yên, 3,42 giây): chạy chậm 1,6 lần rồi phát tới-lui, một vòng tới-lui khoảng 11 giây (H-15). Người xem thấy **một người gần như đứng yên suốt 14–15 giây đầu**, trong lúc lời nói về bài hôm qua và hôm nay (R-10). Xem Q-D.
- Chữ trên hình cảnh 1 vẫn là nhãn "Chuẩn bị" + dòng `prepare_screen` 2 dòng đã chốt; tiêu đề giữ. Trong khoảng 9 giây đầu, chữ "Chuẩn bị" hiện trước khi lời nói tới tư thế chuẩn bị.
- Cả video: 132 từ lên 154 từ, ước khoảng 48 giây ở 3,4 từ/giây, chưa tính phần giữ hình của Dev-6.

### `exercise.py`

| Đối tượng | Trước | Sau |
|-----------|-------|-----|
| Khung góc phụ | Phải, x 816–1066 | Trái, x 60–310 (clip 720×1280), rộng 250, canh đáy khung clip |
| Chữ cảnh bước | `line` | `screens[k-1]` nếu có và không rỗng; không thì `line` |
| Chữ cảnh "Chuẩn bị" | `series.prepare` | `series.prepare_screen` nếu có; không thì `prepare` |
| Lời cảnh 1 của video bài | `{tên chuỗi}, bài {n}: {tên bài}. {prepare}` | Chuỗi có `welcome` và bài có bài đứng trước: `{welcome} Hôm qua mình tập {tên bài trước}, hôm nay mình tập bài {n}, {tên bài}. {prepare}`. Còn lại: như cũ |
| Câu prompt clip bước và clip góc phụ | "Over about eight seconds he {en}." | "He {en}. The main action happens within the first three seconds, then he holds the final pose still until the end of the clip." |
| Dòng hướng dẫn trong file prompt | "(Hết lượt tạo video trong ngày thì làm trước các clip lẻ 1, 3: clip thiếu sẽ mượn clip khác.)" | "(Phải đủ mọi clip trong danh sách rồi mới chạy lệnh. Hết lượt tạo video thì để hôm sau làm tiếp.)" |
| Thiếu clip khi đã có ít nhất một clip bước | Im lặng | In cảnh báo liệt kê từng file còn thiếu (kể cả clip góc phụ) **trước** khi thu giọng. Vẫn chạy tiếp như cũ |
| Nhịp cảnh bước với edge-tts | Narrator `+10%`; cảnh dài bằng lời | Tốc độ đọc riêng cho video bài tập và độ dài tối thiểu của cảnh bước (Dev-6, số ở Q-C) |

---

## Việc của Dev

Làm trên nhánh này (`f65abc1`). Chỉ hai file: `exercise.py`, `content/exercise_curriculum.json`. Không đụng `demo.py`, Studio, `app.html`, `VIDEO_BOX`, `_overlay` ngoài phần nêu dưới.

| # | File | Việc | Nghiệm thu (đo được) |
|---|------|------|----------------------|
| Dev-1 | `exercise.py`: `_angle_panel_box()`, hằng số khung | Khung góc phụ sang **trái** clip chính | Clip góc phụ 720×1280: hàm trả về x = 60, w = 250, h = 444, y + h = 1280. x + w ≤ 311 (đè clip chính ≤ 30 px). Nhãn nằm trong x 60–310, mép dưới nhãn ≤ mép trên khung. Không có phần nào của khung hay nhãn ở x ≥ 890 |
| Dev-2 | `exercise.py`: `build_script()`; giáo trình | Đọc `screens` của bài và `prepare_screen` của chuỗi; thêm dữ liệu như bảng trên | `build_script()` cho bài 2: `screen` cảnh 1, 2, 3, 5 trùng từng chữ với bảng; cảnh 4 không có `screen` hoặc bằng `line`. `line` của mọi cảnh không chứa chữ rút gọn. Bài không có `screens` (bài 3–8) cho cảnh bước như cũ. Mép dưới chữ đo bằng `_overlay`: cảnh 1 ≤ 1580; cảnh 2, 3, 5 ≤ 1570 |
| Dev-3 | Giáo trình: `moves[1].steps[3]` | Đổi lời đọc bước 4 đúng nguyên văn bảng trên (sau khi người dùng duyệt Q-B) | So chuỗi: trùng từng ký tự. `git diff` không có `steps` nào khác bị đổi |
| Dev-4 | Giáo trình: `moves[1].steps_en[0..3]` | Thay 4 câu như bảng trên | So chuỗi từng câu. Không còn "wide stance", "brings the feet together" trong bài 2. Bài khác không đổi |
| Dev-5 | `exercise.py`: `write_prompts()`, `_write_prompt_file()`, `run_next()` | (a) Câu prompt mới cho clip bước và clip góc phụ. (b) Thay dòng "clip lẻ 1, 3". (c) Cảnh báo thiếu clip | (a) `prompts_02.txt`: 5 prompt đều có "within the first three seconds" và "holds the final pose", không có "Over about eight seconds"; prompt `00.mp4` và `prompts_intro.txt` không đổi. (b) Không còn chữ "clip lẻ"; có "Phải đủ mọi clip". (c) Thiếu `02_2_back.mp4` hoặc thiếu clip bước: log có một dòng cảnh báo chứa đúng tên từng file thiếu, in trước dòng `Generating voiceover`; đủ clip thì không có dòng này |
| Dev-6 | `exercise.py`: `run_next()`, `render()` | (a) Khi giọng là edge-tts, video bài tập đọc narrator ở tốc độ riêng (hằng số trong `exercise.py`, không sửa `demo.py`; chỉ có hiệu lực trong lần chạy `--exercise`). (b) Cảnh `ex_step` dài tối thiểu một số giây: lời xong thì giữ hình, im lặng tới hết. Số cụ thể theo Q-C | (a) Tốc độ đọc đo trên bản dựng thử (tổng số từ ÷ tổng thời lượng lời trong `speech_trim`) thấp hơn 4,1 từ/giây; video sản phẩm dựng bằng `demo.py --product … --style simple` trong cùng bản sao vẫn dùng `+10%`. (b) Mọi `scene_dur` của `ex_step` ≥ mức tối thiểu; độ dài `video.mp4` = tổng `scene_dur` ± 0,2 giây; tiếng không lệch hình |
| Dev-7 | `exercise.py` | Không làm hỏng luồng cũ | Xem T-9 … T-11 |
| Dev-8 | `exercise.py`: `build_script()`; giáo trình: `series[bdc].welcome` | Câu chào + câu nối ở lời cảnh 1. Câu chào là một trường của chuỗi (`welcome`); câu nối máy tự ghép từ tên bài đứng trước trong `moves` và số, tên bài này, theo mẫu ở § Thay đổi cấu trúc. Không thêm trường theo từng bài. Chỉ đổi `line` của cảnh `ex_intro`; `kind`, `text`, `screen` của cảnh đó không đổi | `build_script()` bài 2: `line` cảnh 1 trùng từng ký tự câu "Sau" trong bảng. Bài 3: "…Hôm qua mình tập Giương cung bắn chim, hôm nay mình tập bài 3, Một tay nâng trời. Đứng thẳng…". Bài 1: `line` cảnh 1 trùng bản `f65abc1`. Chuỗi `tcq24` (không có `welcome`): mẫu cũ. `build_intro_script()`, `build_summary_script()` cho kết quả trùng `f65abc1`. `rerender()` không gọi `build_script()` (không đổi) |

Hướng dẫn vận hành § 4b: **BA sửa**, trong giai đoạn tài liệu của chính nhánh này (cùng PR với code), không hoãn sang đợt khác.

---

## Chi phí

| Việc | Tốn gì | Nguồn |
|------|--------|-------|
| Ghi `prompts_02.txt` | $0, không thu giọng | H-5 |
| Tạo 5 clip trong app Gemini | Lượt tạo video trong gói Gemini của người vận hành; clip sai phải tạo lại. Số lượt mỗi ngày: **chưa rõ** | `TODO.md` M2c |
| Thu giọng bài 2 bằng edge-tts | **$0, 0 lượt Gemini**, không giới hạn theo ngày. Thu lại bao nhiêu lần cũng $0 | H-8; U-2 |
| Dựng lại, chỉnh chữ, thay clip | $0 | H-12 |
| Drive | Thêm một thư mục video; dung lượng chưa rõ | — |

**Thời lượng dự kiến**: chưa rõ, chỉ ước được. 154 từ (sau Dev-3, Dev-8): ở 4,1 từ/giây (H-9) ≈ 38 giây lời; ở khoảng 3,4 từ/giây (nếu −10 %) ≈ 46 giây lời; cộng 6 × 0,25 + 0,8 giây và phần giữ hình của Dev-6. Xa mốc 3 phút.

---

## Các bước vận hành

Dán nguyên dòng vào Terminal. Làm sau khi người điều phối báo "code bài 2 đã sẵn sàng" (Dev xong, Tester đạt, repo gốc đã có bản mới).

| Bước | Ai | Việc | Thấy gì |
|------|----|------|---------|
| V-1 | Người vận hành | `cd /Users/mkstore/Documents/project/tiktok_affiliate && TTS_PROVIDER=edge .venv/bin/python demo.py --exercise` | `Bát Đoạn Cẩm — bài 2: Giương cung bắn chim: chưa có clip. Làm clip theo storage/clips/bdc/prompts_02.txt`. Thấy "video mở đầu" hoặc bài khác: dừng, báo người điều phối |
| V-2 | Người vận hành | Mở `storage/clips/bdc/prompts_02.txt`: 5 prompt. Vào gemini.google.com → Video → khung Dọc (9:16). **Mỗi prompt một cuộc trò chuyện mới** | 5 clip |
| V-3 | Người vận hành | Xem từng clip, sai một mục thì tạo lại: (1) **Tấn cao, vừa sức, gối không vượt mũi chân.** (2) Thấy cả người từ đầu tới chân. (3) Đúng bên: ở clip nhìn từ trước (`02_1`, `02_2`, `02_3`), tay đẩy ra có ngón trỏ dựng lên nằm bên **PHẢI màn hình**; ở `02_2_back` nằm bên **TRÁI màn hình** và phải thấy **lưng**; ở `02_4` (đổi bên) tay đẩy ra nằm bên **TRÁI màn hình**. (4) Động tác chính xong trong **3 giây đầu**, sau đó giữ yên. (5) Nền **giống `00.mp4` và `ref_bdc.png`: sân lát đá xám, hàng cây phía sau**; ra bãi cỏ thì tạo lại. (6) Cùng người: tóc bạc ngắn, áo trắng | — |
| V-4 | Người vận hành | Đổi tên đúng, bỏ vào `storage/clips/bdc/`. Rồi dán: `cd /Users/mkstore/Documents/project/tiktok_affiliate && ls storage/clips/bdc/02_*` | **Phải thấy đúng 5 dòng**: `02_1.mp4`, `02_2.mp4`, `02_2_back.mp4`, `02_3.mp4`, `02_4.mp4`. Chưa đủ 5 thì chưa làm bước sau |
| V-5 | Người vận hành | Dán lại đúng lệnh V-1. Máy thu giọng, dựng, tự mở video, hỏi `Approve? (y/n)`. **Lần đầu, dù video đẹp đến đâu, gõ `n` rồi Enter. Gõ `n` không mất gì.** | `Rejected — files kept`. Thư mục `storage/videos/<ngày_giờ>_baitap_bdc_02/` |
| V-6 | Người điều phối | Đọc log: dòng `✅ Voiceover (edge)`; dòng `Scene 3 … + Nhìn từ sau: local:02_2_back.mp4`; không có dòng cảnh báo thiếu clip | — |
| V-7 | — | **Từ đây không dán lại lệnh V-1**: nó sẽ thu giọng lần nữa và tạo thêm một thư mục thứ hai. Chỉ dùng lệnh dựng lại ở V-9b | — |
| V-8 | MKTG + người điều phối | Review bản dựng: khung nhỏ bên trái, chữ, tiêu đề 2 dòng có đè lên người không (đè thì đổi `hook` trong `script.json` thành "Bài 2: Giương cung" rồi dựng lại), clip có khớp lời. Cần thì thay clip trong `storage/clips/bdc/` | `marketing-review.md` |
| V-9a | Người vận hành | Mở `video.mp4` trong thư mục bài 2, nghe 4 chỗ có số: "bài hai", "một đến hai giây", "mỗi bên ba lần", "bài ba, Một tay nâng trời" | Đọc đúng cả 4 |
| V-9b | Người vận hành | Dán lệnh người điều phối đưa sẵn: `cd /Users/mkstore/Documents/project/tiktok_affiliate && .venv/bin/python demo.py --exercise-rerender storage/videos/<thư mục bài 2>`. Phải dựng lại vì máy chỉ hỏi `y/n` ngay sau khi dựng, và lần dựng này lấy clip, chữ mới nhất. Máy mở video, xem lần cuối, **lúc này mới gõ `y`** rồi Enter. Gõ `y` xong video chỉ còn trên Drive; chưa chắc thì gõ `n` | `Curriculum: Bát Đoạn Cẩm bài 2 → done`, đường dẫn Drive, `Deleted local folder` |
| V-10 | Người vận hành | Đăng theo `post.txt`: không gắn sản phẩm, bật nhãn "Nội dung do AI tạo". Muốn caption riêng cho bài 2 (gợi ý MKTG) thì dán câu này thay caption trong `post.txt`: "Bát Đoạn Cẩm – Bài 2: Giương cung bắn chim. Ngồi tấn vừa sức, một tay đẩy ngón trỏ, một tay kéo dây cung, mỗi bên 3 lần. Lưu lại để tập mỗi sáng. Bài vận động nhẹ, không phải phương pháp chữa bệnh." kèm 4 hashtag cũ. Lời kết hứa "ngày mai tập bài 3"; **chưa kịp làm bài 3 thì vẫn đăng bài 2** | Video lên kênh |

Người điều phối làm trước: (P-1) đưa bản đã merge của nhánh này về repo gốc; (P-2) so sha256 `exercise.py`, `demo.py` ở repo gốc với bản Tester đã thử, ngay trước V-1 và V-5.

---

## Không làm

- Không đổi lời đọc nào ngoài bước 4 của bài 2 và phần đầu lời cảnh 1 (câu chào + câu nối). Không đổi `prepare`, `reps`, `careful`, lời kết (C-0006-5).
- Không đổi lời của bài 1 đã duyệt, video mở đầu, video tổng kết.
- Không sửa `demo.py`, Studio, `app.html`, `VIDEO_BOX`, đáy an toàn, tiêu đề (thuộc DR-0003).
- Không gọi Gemini TTS. Không tạo clip, không gõ `y` thay người vận hành, không `--skip-approval`.
- Không thêm chữ "Lưu video để tập theo" vào cảnh 6 (không đạt mốc đo).
- Không làm lại bài 1 hay video mở đầu. `prepare_screen` chỉ có hiệu lực với video dựng mới; bài 1 đã duyệt giữ nguyên.
- Không sửa prompt (`steps_en`) của bài 3–8 trong đợt này dù chúng cũng có "as if riding a horse" (bài 5, 7): ghi thành việc mở trong `TODO.md`.
- Duyệt video bài tập trên Studio: việc mở ở DR-0005.

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output |
|---|------|---------|-------|--------|
| 1 | DR bản 2 | BA | Câu trả lời người dùng, góp ý MKTG | DR này |
| 2 | Duyệt DR, trả lời Q-B, Q-C, Q-D | Người dùng | DR này | Quyết định |
| 3 | Dev-1 … Dev-8 | Dev | #2 | Diff 2 file |
| 4 | Soát diff theo C-0006-5 và bảng nghiệm thu | Reviewer | #3 | Ghi chú review |
| 5 | T-1 … T-12 | Tester | #3 | Kết quả |
| 6 | Sửa § 4b và tài liệu SSoT | BA | #3–#5 | Docs trong cùng nhánh |
| 7 | PR, merge, P-1, P-2 | Người điều phối | #4–#6 | Repo gốc có bản mới |
| 8 | V-1 … V-5 | Người vận hành | #7 | 5 clip, thư mục video |
| 9 | V-6, V-8 | Người điều phối, MKTG | #8 | `marketing-review.md` |
| 10 | V-9a, V-9b, V-10 | Người vận hành | #9 | Video trên Drive, trên kênh |
| 11 | Điền § Kết quả, `TODO.md` | BA | #10 | Docs |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Chạy lệnh khi mới có một phần clip | Bản dựng dùng clip mượn. Với edge-tts không mất lượt nào, chỉ mất thời gian | V-4; Dev-5(b)(c); C-0006-1 |
| R-2 | Rủi ro | Phần khung góc phụ + hoà hình + che dấu ✦ chưa từng chạy (H-17) | Lệnh báo `error` khi dựng | T-3 trước khi vận hành |
| R-3 | Rủi ro | Gemini tạo clip sai bên, tấn thấp, nền bãi cỏ | Tạo lại, tốn lượt tạo video | V-3 |
| R-4 | Rủi ro | Mốc 1570 / 907 / 1053 / 54 là tạm | Tiêu chí có thể đổi | Tester ghi số đo; người vận hành xem trên điện thoại |
| R-5 | Rủi ro | Khung nhỏ đè 29 px lên mép trái clip chính, che khuỷu tay ở cảnh 3 | Mất một phần hình | V-8 xem bản dựng; nếu che thì thu khung còn 221 px (đổi một hằng số) |
| R-6 | Rủi ro | Câu prompt mới ("within the first three seconds… holds") cho clip gần như đứng yên | Cảnh dài nhìn tĩnh | V-3 mục (4); phát tới-lui vẫn chạy khi cảnh dài hơn clip |
| R-7 | Rủi ro | Số ở Dev-6 (tốc độ, độ dài tối thiểu) là lựa chọn thiết kế, không có nguồn | Có thể quá chậm hoặc chưa đủ chậm | Q-C; đổi hằng số rồi thu lại, $0 |
| R-8 | Rủi ro | Sau khi gõ `n`, dán lại lệnh V-1 | Thêm một thư mục, thu giọng lại | V-7 |
| R-9 | Rủi ro | Sửa giáo trình sau khi đã thu giọng | Video dựng lại vẫn mang chữ cũ (H-12) | Mọi sửa giáo trình xong trước V-1 |
| R-10 | Rủi ro | Cảnh 1 dài khoảng 14–15 giây trên clip đứng yên `00.mp4` phát tới-lui | Mở đầu tĩnh và dài; câu gợi tò mò đến muộn với người xem mới (U-5) | Q-D; MKTG xem bản dựng ở V-8. Đổi sau vẫn $0 với edge-tts (thu lại) |
| R-11 | Rủi ro | Đăng không đúng nhịp mỗi ngày một bài | Câu "Hôm qua mình tập…" sai với người xem | V-10 nhắc; nếu lịch đăng không đều thì cần đổi mẫu câu nối (DR mới hoặc sửa trước khi thu giọng) |
| A-1 | Giả định | Người dùng duyệt nguyên văn ở Q-B | Sai thì Dev-2, Dev-3 đổi chữ | Q-B |
| A-2 | Giả định | Giọng edge-tts `vi-VN-NamMinhNeural` chấp nhận được cho cả chuỗi | Sai thì quay lại Gemini, cần DR-0002 | U-2 |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0006-1 | Chỉ chạy `demo.py --exercise` để thu giọng cho một bài khi đã có **đủ mọi clip** bài đó cần, kể cả clip góc phụ | Có một clip là máy đã dựng với clip mượn; thiếu clip góc phụ thì khung nhỏ biến mất (H-6) | Vận hành video bài tập | Khi code tự dừng lúc thiếu clip |
| C-0006-2 | Bản `exercise.py` + `demo.py` dùng để dựng thật phải trùng mã băm với bản Tester đã chạy đạt | Code dựng bài tập từng được đổi thẳng trên `main` không qua review (U-1) | Bài 2 | Khi repo gốc sạch và trùng `origin/main` đã qua review |
| C-0006-3 | Trước khi gõ `y`, dòng `✅ Voiceover` phải đúng bộ giọng đã chọn (bài 2: `edge`) | Một video một bộ giọng; máy có thể tự đổi giọng | Mọi video bài tập | Khi có cờ dừng lúc đổi giọng (DR-0002 `gemini-quota`) |
| C-0006-4 | Video bài tập chỉ được duyệt khi người vận hành đã xem và tự gõ `y`. Agent, script không dùng `--skip-approval`, không trả lời `y` | Duyệt là đánh dấu `done`, tải Drive, xoá bản trên máy (H-11) | Mọi lần chạy `demo.py --exercise*` | Khi video bài tập duyệt được trên Studio |
| C-0006-5 | Trong DR này chỉ hai chỗ lời đọc được đổi: (1) `moves[1].steps[3]` (bước 4 bài 2); (2) phần đầu lời cảnh 1 của video bài, từ bài thứ hai của chuỗi có `welcome`: câu chào + câu nối thay cho "{tên chuỗi}, bài {n}: {tên bài}." Phần `prepare` trong cảnh 1, mọi cảnh bước khác, lời kết, bài 1, video mở đầu, video tổng kết giữ nguyên từng chữ. Chữ trên hình (`screens`, `prepare_screen`) và prompt (`steps_en`) không được làm đổi `line` của bất kỳ cảnh nào | Lời đọc là nội dung người vận hành đã duyệt; chữ trên hình tách khỏi lời | `build_script()`, giáo trình | DR mới |
| C-0006-7 | Câu chào và câu nối chỉ vào video **dựng mới**. Dựng lại (`--exercise-rerender`) không được tự đổi lời của video đã có giọng | Lời đổi mà giọng không thu lại thì tiếng và chữ lệch nhau; bài 1 và video mở đầu đã duyệt | `rerender()`, `build_script()` | — |
| C-0006-6 | Câu prompt clip bước phải yêu cầu động tác chính nằm ở đầu clip | Máy chỉ phát đoạn đầu clip khi cảnh ngắn hơn clip (H-15) | `write_prompts()` | Khi cách dựng đổi (vd chọn đoạn giữa clip) |

Đang áp dụng, không đổi: C-0001-1, C-0001-4.

supersedes: —

---

## Tài liệu SSoT bị ảnh hưởng

BA sửa trong cùng nhánh, sau khi Dev xong (việc #6). (†) = trùng danh sách DR-0005, DR nào merge trước thì làm.

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` § 4b | (1) "cùng một cuộc trò chuyện" → "mỗi prompt một cuộc trò chuyện mới". (2) Bỏ "Hết lượt… làm trước bước 1 và 3… mượn clip"; thay bằng "đủ mọi clip mới chạy lệnh" + lệnh `ls`. (3) Clip góc phụ `NN_K_side.mp4` / `NN_K_back.mp4`, khung nhỏ bên trái. (4) Lệnh edge-tts `TTS_PROVIDER=edge …`. (5) Lần đầu gõ `n`; sau đó chỉ dùng `--exercise-rerender`. (6) Mục kiểm clip: tấn cao, trái/phải trên màn hình, 3 giây đầu, nền như `00.mp4`. (7) † gõ đúng một chữ `y` | [ ] |
| Cùng file, dòng 212 | † "làm bằng công cụ khác" → làm bằng `demo.py --exercise` | [ ] |
| `docs/specs/architecture/capabilities/video-render.md` | † Mục "Video bài tập": luồng, tên clip, `screens`, `prepare_screen`, khung góc phụ, độ dài tối thiểu cảnh bước, tốc độ edge-tts, hành vi thiếu clip. Sửa dòng 194 | [ ] |
| `agent/CLAUDE.md` | † Cờ `--exercise*`; `TTS_PROVIDER=edge` cho video bài tập | [ ] |
| `.env.example` | † `EXERCISE_EXTRA_TTS_MODEL`; biến mới của Dev-6 nếu Dev cho cấu hình qua môi trường | [ ] |
| `TODO.md` (M2c) | Bài 2: kết quả thật. Việc mở: prompt "riding a horse" của bài 5, 7; cảnh 6 vượt mốc đáy; tiêu đề 2 dòng | [ ] |
| `content/exercise_curriculum.json` `_doc` | Mô tả `screens`, `prepare_screen`, clip góc phụ | [ ] |

## File thay đổi

- [ ] `exercise.py`: Dev-1, Dev-2, Dev-5, Dev-6, Dev-8
- [ ] `content/exercise_curriculum.json`: Dev-2, Dev-3, Dev-4, Dev-8 (`welcome`)
- [ ] Tài liệu ở bảng trên
- Không đổi: `demo.py`, `backend/`, `*.html`, `*.command`

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: hành vi

Chạy trên bản sao của nhánh sau Dev, edge-tts. "Clip thay thế" = chép `01_1…01_4.mp4` thành `02_1…02_4.mp4`, `01_2.mp4` thành `02_2_back.mp4`.

| # | Loại | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|------|-----------|------------------|-----------|
| D-1 | Bình thường | Có `00.mp4`, không có `02_*`; `--exercise` | `needs_clips`. `prompts_02.txt` có 5 mục: `02_1`, `02_2`, `02_3`, `02_4`, `02_2_back`; không có `00.mp4`. Mỗi prompt chứa câu `steps_en` mới, "within the first three seconds", "holds the final pose"; không có "Over about eight seconds", "wide stance", "brings the feet together". Prompt `02_2_back` có "back view from behind him", không có "front view". File có "MỖI PROMPT MỘT CUỘC TRÒ CHUYỆN MỚI" và "Phải đủ mọi clip", không có "clip lẻ". Không có `audio_*`, không tạo thư mục video | Đọc file; `ls` |
| D-2 | Bình thường | Đủ 5 clip thay thế; `--exercise`, trả lời `n` | Thư mục `…_baitap_bdc_02`. `script.json`: 6 cảnh `ex_intro, ex_step×4, ex_end`; nguồn clip `00, 02_1, 02_2, 02_3, 02_4, 02_2_back`; `scene_clip = [0,1,2,3,4,0]`; `scene_angle` chỉ ở vị trí 2: `{"clip": 5, "label": "Nhìn từ sau"}`; `voice_persona = nam_bac`; mọi `tts_model = null`. Log: `✅ Voiceover (edge)`, `Scene 3 … + Nhìn từ sau`, không có cảnh báo thiếu clip. `rejected`; giáo trình bản sao không đổi | `script.json`, log |
| D-3 | Bình thường | Bản dựng D-2 | `line` cảnh 1 = "Chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm. Hôm qua mình tập Hai tay nâng trời, hôm nay mình tập bài 2, Giương cung bắn chim. Đứng thẳng, hai chân rộng bằng vai, gối hơi chùng, vai thả lỏng, thở đều bằng mũi.", trùng từng ký tự. `line` cảnh 5 = câu bước 4 mới, trùng từng ký tự. `line` cảnh 2–4, 6 trùng bản dựng từ `f65abc1`. `screen` cảnh 1, 2, 3, 5 trùng bảng § Thay đổi cấu trúc; nhãn cảnh 1 vẫn "Chuẩn bị". Ghi `scene_dur` cảnh 1 và việc `00.mp4` phát tới-lui mấy vòng | So chuỗi bằng script; log |
| D-4 | Bình thường | Bản dựng D-2; 1 khung giữa mỗi cảnh, 1080×1920 | (a) Chỉ cảnh 3 có khung nhỏ viền trắng, ở x 60–310, y 836–1280, nhãn "Nhìn từ sau" phía trên. (b) Không có gì của khung ở x ≥ 890. (c) Chữ dưới nhãn vàng ≤ 2 dòng ở cảnh 1–5; mép dưới: cảnh 1 ≤ 1580, cảnh 2–5 ≤ 1570; cảnh 6 ghi số đo (dự kiến 1602). (d) Cảnh 6 có "Gối không vượt quá mũi chân." và dòng miễn trừ. (e) Không có "Hình minh hoạ". (f) Tiêu đề: ghi mép dưới (dự kiến 360) và có đè lên đầu người không | `_overlay(...).getchannel('A').getbbox()`; xem khung hình |
| D-5 | Bình thường | Bản dựng D-2 | Độ dài `video.mp4` = tổng `scene_dur` ± 0,2 giây. Mọi `scene_dur` của `ex_step` ≥ mức tối thiểu của Dev-6. Tốc độ đọc < 4,1 từ/giây (ghi số). Không khung đen ở 5 chỗ chuyển cảnh. Khung nhỏ chạy suốt cảnh 3. Trong đoạn giữ hình sau lời, không có tiếng | `ffmpeg -i`; `silencedetect`; trích khung |
| D-6 | Biên | Chỉ có `02_1.mp4`; `--exercise`, `n` | Log có cảnh báo nêu đủ 4 tên `02_2.mp4`, `02_3.mp4`, `02_4.mp4`, `02_2_back.mp4`, in trước `Generating voiceover`. Vẫn dựng: `scene_clip = [0,1,1,1,1,0]`, `scene_angle` toàn `null` | Log, `script.json` |
| D-7 | Biên | Đủ 4 clip bước, thiếu `02_2_back.mp4`; `--exercise`, `n` | Cảnh báo nêu `02_2_back.mp4`. Dựng được, không có khung nhỏ. `prompts_02.txt` còn 1 mục | Log, file |
| D-8 | Biên | Chỉ có `02_2_back.mp4`; `--exercise` | `needs_clips`, không thu giọng | `ls` |
| D-9 | Bình thường | Thư mục D-7, thêm `02_2_back.mp4`; `--exercise-rerender`, `n` | Cảnh 3 có khung nhỏ bên trái; 6 `audio_*` không đổi (kích thước, mtime); log không có `Generating voiceover` | `ls -la` trước/sau |
| D-10 | Bình thường | Thư mục D-2; `--exercise-rerender`, `y`; không `DRIVE_FOLDER_ID` | `post.txt` có caption "Bát Đoạn Cẩm – Bài 2: Giương cung bắn chim. …" + 4 hashtag + "KHÔNG gắn sản phẩm". Giáo trình bản sao: bài 2 `done = true`, bài 3 `false`; `screens`, `prepare_screen`, `steps_en` còn nguyên sau khi `mark_done()` ghi lại file. Thư mục giữ lại | Đọc file; `git diff` trong bản sao chỉ có một dòng `done` |
| D-11 | Biên | Thư mục D-2; `--exercise-rerender`, trả lời `yes` | `rejected`; không có `post.txt`; giáo trình không đổi | Đọc file |
| D-12 | Lỗi | Xoá `audio_2.mp3` trong bản sao thư mục D-2; `--exercise-rerender` | `error`; giáo trình không đổi | Log |
| D-13 | Hồi quy: bài không có `angles`, không có `screens` | Sau D-10, chép `01_1…01_4` thành `03_1…03_4`; `--exercise`, `n` | Bài 3: `prompts_03.txt` không có mục góc phụ; `scene_angle` toàn `null`; không khung nhỏ ở cảnh nào; chữ cảnh bước = `line`; chữ cảnh 1 = `prepare_screen`. `line` cảnh 1 = "Chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm. Hôm qua mình tập Giương cung bắn chim, hôm nay mình tập bài 3, Một tay nâng trời. Đứng thẳng, hai chân rộng bằng vai, gối hơi chùng, vai thả lỏng, thở đều bằng mũi." | `script.json`, khung hình |
| D-14 | Hồi quy: bài 1 | `build_script()` cho bài 1 trên nhánh so với `f65abc1` | Giống nhau mọi trường, trừ `screen` cảnh 1 (= `prepare_screen`). 6 `line` trùng từng ký tự; cảnh 1 **không** có câu chào | So bằng script |
| D-18 | Hồi quy: dựng lại không đổi lời | Tạo thư mục bài 1 bằng bản `f65abc1` trong bản sao (đặt tạm bài 1 `done = false`, edge-tts, `n`), rồi `--exercise-rerender` thư mục đó bằng bản của nhánh, `n`. Làm tương tự với bản sao thư mục video mở đầu (D-15) | `line` mọi cảnh trong `script.json` sau khi dựng lại trùng trước khi dựng lại; không có "Chào mừng" trong bài 1 và video mở đầu; file `audio_*` không đổi | So `script.json` trước/sau; `ls -la` |
| D-19 | Biên: chuỗi không có `welcome` | Trong bản sao, xoá `welcome` của `bdc`; `build_script()` bài 2 | `line` cảnh 1 = "Bát Đoạn Cẩm, bài 2: Giương cung bắn chim. Đứng thẳng…" (mẫu cũ), không lỗi | Gọi hàm |
| D-15 | Hồi quy: video mở đầu | Bản sao thư mục `20261113_183051_baitap_bdc_00_gioithieu` (chỉ `script.json` + `audio_0…5.mp3`) + `intro_1…6.mp4`; `--exercise-rerender`, `n`, chạy trên `f65abc1` và trên nhánh | Hai lần cho cùng `scene_dur` từng cảnh và cùng độ dài video (± 0,1 giây); lớp chữ `_overlay` của 6 cảnh giống hệt nhau (so từng pixel) | `script.json`; so ảnh |
| D-16 | Hồi quy: video sản phẩm | Trong bản sao, `demo.py --product "Thử" --points "A\|B" --style simple --skip-approval` bằng edge-tts, trước và sau khi chạy `--exercise` | Tốc độ narrator vẫn `+10%` (Dev-6 không rò sang); lệnh không lỗi | Đọc code + chạy |
| D-17 | Hồi quy: phạm vi diff | `git diff f65abc1` của nhánh | Chỉ `exercise.py`, `content/exercise_curriculum.json`, tài liệu. Trong giáo trình: `steps` chỉ đổi `moves[1].steps[3]`; `steps_en` chỉ đổi của bài 2; thêm `screens`, `prepare_screen`; không đổi `done` nào | `git diff --stat`; so bằng script |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | Hướng dẫn § 4b | Sửa | Không còn "cùng một cuộc trò chuyện", không còn "mượn clip"; có lệnh `TTS_PROVIDER=edge …`, lệnh `ls`, "lần đầu gõ `n`" | `grep`; so với `exercise.py` |
| DD-2 | `video-render.md` | Thêm | Mục "Video bài tập" khớp code của nhánh | So với `exercise.py` |
| DD-3 | File prompt máy viết và § 4b | Nhất quán | Hai nơi nói cùng một quy tắc về số chat và đủ clip | Đọc đối chiếu |
| DD-4 | DR § Kết quả | Thêm | Kết quả Tester chép nguyên văn | Đối chiếu báo cáo |

### Kiểm tra của Tester

Điều kiện chung: làm trong **thư mục tạm**, là bản sao của nhánh sau Dev (ghi sha256 `exercise.py`, `demo.py`). Chép `00.mp4`, `01_1…01_4.mp4`, `intro_1…6.mp4` vào `storage/clips/bdc/` của bản sao rồi tạo clip thay thế. Không `.env`; chạy với `env -u GEMINI_API_KEY -u DRIVE_FOLDER_ID TTS_PROVIDER=edge`. Không Gemini, Drive, Sheet, TikTok. Không ghi gì vào `storage/` hay giáo trình của repo gốc. `y/n` đưa qua stdin. Lệnh tự mở trình phát video trên macOS.

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| T-1 | File prompt | D-1 | Đạt | — | — |
| T-2 | Dừng khi không có clip bước | D-8 | Đạt | — | — |
| T-3 | Dựng bài 2 có góc phụ | D-2, D-3 | Đạt | — | — |
| T-4 | Bố cục | D-4; ghi toạ độ khung nhỏ và mép dưới chữ 6 cảnh | Đạt | — | — |
| T-5 | Nhịp và độ mịn | D-5; ghi `scene_dur` từng cảnh, tốc độ đọc | Đạt | — | — |
| T-6 | Thiếu clip, cảnh báo | D-6, D-7, D-9 | Đạt | — | — |
| T-7 | Duyệt | D-10, D-11 | Đạt | — | — |
| T-8 | Lỗi | D-12 | Đạt | — | — |
| T-9 | Hồi quy bài không góc phụ | D-13 | Đạt | — | — |
| T-10 | Hồi quy bài 1, video mở đầu | D-14, D-15, D-18 | Đạt | — | — |
| T-14 | Câu chào và câu nối | D-3 (bài 1 → bài 2), D-13 (bài 2 → bài 3), D-19; nghe thử `audio_0.mp3` của bài 2 và ghi độ dài | Đạt; ghi `scene_dur` cảnh 1 | — | — |
| T-11 | Hồi quy video sản phẩm, phạm vi diff | D-16, D-17 | Đạt | — | — |
| T-12 | Không đụng dữ liệu thật | So `ls -la storage/videos/`, `storage/clips/bdc/`, `git status` ở repo gốc trước và sau | Không đổi | — | — |
| T-13 | Bản dựng thật (sau V-5) | Lặp D-2 … D-5 trên thư mục thật, chỉ đọc; so sha256 code | Đạt | — | — |

Tester không kiểm được, ghi là chưa kiểm: clip Gemini thật của bài 2, nghe bằng tai, tải Drive thật, hình trên điện thoại thật.

### Cổng chất lượng

- [ ] Người dùng đã duyệt DR bản 2 và nguyên văn ở Q-B
- [ ] Reviewer xác nhận C-0006-5 (chỉ bước 4 và phần đầu cảnh 1 đổi lời), C-0006-7, và không đụng `demo.py`, Studio, `app.html`
- [ ] Tester đạt T-1 … T-12
- [ ] § 4b đã sửa trong cùng nhánh (DD-1, DD-3)
- [ ] Đủ 5 clip trước khi thu giọng (C-0006-1); mã băm trùng (C-0006-2); giọng `edge` (C-0006-3)
- [ ] MKTG đã review bản dựng thật; người vận hành đã nghe 4 chỗ có số
- [ ] Người vận hành tự gõ `y` (C-0006-4)
- [ ] Số DR của các worktree khác đã được gán lại, không trùng

---

## Câu hỏi mở cho người dùng

| # | Câu hỏi | Vì sao cần | Mặc định nếu không trả lời |
|---|---------|-----------|---------------------------|
| Q-A | Đã đóng: người dùng chọn câu chào + câu dẫn nối từ bài 1 (U-5, Dev-8) | — | — |
| Q-B | Chờ duyệt. Duyệt nguyên văn: **lời cảnh 1** "Chào mừng các bạn quay lại với chuỗi bài tập Bát Đoạn Cẩm. Hôm qua mình tập Hai tay nâng trời, hôm nay mình tập bài 2, Giương cung bắn chim." (rồi tới phần tư thế chuẩn bị như cũ; mẫu này dùng cho bài 3–8 với tên bài tương ứng), **lời đọc bước 4** "Thu tay, đứng lên. Rồi đổi bên: bước chân phải sang ngang, tay phải đẩy ngón trỏ, tay trái kéo dây cung." và **4 dòng chữ trên hình** (Chuẩn bị, bước 1, bước 2, bước 4) ở bảng "Chữ trên hình"? Dòng "Chuẩn bị" mới sẽ dùng cho cả bài 3–8 | Đây là nội dung bạn duyệt trong giáo trình | Chờ; Dev chưa bắt đầu Dev-2, Dev-3 |
| Q-C | Với giọng edge-tts, cảnh bước chỉ dài 2,5–5 giây, khó nhìn theo. Đề xuất: giọng video bài tập đọc **chậm hơn 10 %** so với tốc độ gốc của giọng (hiện đang nhanh hơn 10 %), và mỗi cảnh bước dài **ít nhất 5 giây** (đọc xong thì giữ hình). Hai con số này là lựa chọn thiết kế, chưa có nguồn. Đồng ý, hay muốn số khác? | Quyết định nhịp của cả chuỗi. Đổi sau cũng được, $0 | Chờ duyệt. Nếu không trả lời: dùng −10 % và 5 giây; Tester báo số đo, MKTG xem bản dựng |
| Q-D | Cảnh mở đầu giờ dài khoảng 14–15 giây (ước tính) và hình là một người đứng yên. Có muốn lúc đọc câu chào và "Hôm qua mình tập Hai tay nâng trời" thì chiếu **clip của bài hôm qua** (đã có sẵn `01_3.mp4`, không phải tạo clip mới), tới phần tư thế chuẩn bị mới chuyển sang clip đứng yên không? | Làm thì thêm một việc Dev (tách cảnh 1 thành hai cảnh), $0. Không làm thì mở đầu tĩnh | Không làm trong đợt này; xem bản dựng thật rồi quyết |

---

## Kết quả

Chưa thực hiện. BA điền sau khi Dev, Reviewer, Tester, MKTG và người vận hành xong.

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR liên quan | DR-0001 (C-0001-1, C-0001-4). DR-0005 `bdc-intro-video` (chưa duyệt). DR-0003 `cta-safe-zone` (số đo vùng an toàn; chưa duyệt). DR-0002 `gemini-quota` (chưa duyệt) |
| Góp ý đã đưa vào | MKTG 2026-11-14: 1.1 (U-5, Dev-8), 1.3 (Dev-4, V-3), 1.5 (không nhận), 1.6 (V-10), 1.7 (V-8), 2.1 (Dev-5a, C-0006-6), 2.2–2.3 (Dev-4), 2.4–2.5 (V-3), 2.7 (Dev-1), 2.8 (Dev-2), 4.1 (Dev-5b, § 4b), 4.2 (V-4, Dev-5c), 4.3–4.8 (bảng V, bảng T) |
| Code đã đọc | `exercise.py` `f65abc1` (toàn bộ); `demo.py`: `VOICES`, `load_env`, `tts_provider`, `_tts`, `generate_voiceovers`, `gemini_tts_models`, `choose_persona`, `_text_block`, `_pill`, `approval_step`, `move_to_drive`, nhánh `--exercise*`; `drive_upload.py` → `upload_video_folder` |
| Đã chạy (không ghi file) | `build_script()`, `_overlay()` cho bài 2 và từng câu chữ đề xuất; `_clip_info()`; `_angle_wanted()` |
| Chưa làm | Chưa chạy `demo.py --exercise`. Chưa dựng thử khung góc phụ. Chưa chạy edge-tts với tốc độ mới. Chưa xem clip bài 2 (chưa có) |
