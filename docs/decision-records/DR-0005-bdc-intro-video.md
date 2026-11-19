# DR-0005: Video 00 (mở đầu) của chuỗi Bát Đoạn Cẩm

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📋 Đề xuất, chờ người dùng trả lời câu hỏi mở (trước hết là Q-0) | 2026-11-13 | Claude (BA) | — |

Capability: `video-render` · Nhánh: `feat/bdc-intro-video` · Loại: việc vận hành + sửa nội dung giáo trình + tài liệu

Vai trò: **BA** = viết DR, cập nhật tài liệu · **Dev** = sửa chữ trong giáo trình (chỉ khi người dùng duyệt Q-6) · **Reviewer** = soát diff · **Tester** = chạy thử trên bản sao · **MKTG** = review video · **Người vận hành** = xem, nghe, gõ `y/n`.

Yêu cầu nguyên văn (2026-11-13): "tạo video 00 giới thiệu cho bài tập bát đoạn cầm".

> **Số DR.** Bản nháp đầu mang số DR-0002. Đổi thành DR-0005 vì ba worktree khác đang có DR chưa commit: DR-0002 (`clip-trim`, `gemini-quota`, hai file trùng số), DR-0003 (`cta-safe-zone`), DR-0004 (`agent-skills`). Người điều phối cần gán lại số cho hai bản DR-0002 kia trước khi merge.

> **Cập nhật 18:38 ngày 2026-11-13: video 00 đã được ai đó làm và duyệt ngoài DR này.** Xem H-13. Vì vậy câu hỏi đầu tiên là Q-0: bản trên Drive có phải bản cuối không. Phần còn lại của DR chỉ áp dụng nếu người dùng muốn làm lại hoặc chỉnh theo góp ý MKTG.

> **Review của MKTG (2026-11-13)**: ủng hộ dùng lại giọng cũ (phương án A). Lời đọc không có lỗi mức Chặn; đã tra DOI 10.3389/fmed.2022.995577 (17 RCT, 2022), khớp lời. Góp ý đã đưa vào: § Góp ý MKTG, § Các bước vận hành, D-4, D-13, Q-1, Q-6 … Q-8.

---

## Bối cảnh

**Vấn đề (gốc rễ)**:
Chuỗi Bát Đoạn Cẩm cần video mở đầu (số 00) trước khi đăng bài 1. Bản dựng ngày 2026-11-12 bị người vận hành đánh giá "chưa OK" và đã gỡ khỏi Studio. Hôm nay đã có đủ 6 clip riêng cho video mở đầu.

**Hiện trạng đã kiểm trong code và trên máy**:

| # | Sự việc | Nguồn kiểm |
|---|---------|-----------|
| H-1 | Giáo trình có video mở đầu: 6 cảnh, mỗi cảnh gắn một clip `intro_1.mp4` … `intro_6.mp4` | `content/exercise_curriculum.json` → `series[bdc].intro_video` |
| H-2 | `demo.py --exercise` làm video mở đầu trước khi làm bài kế tiếp, **chỉ khi** `intro_video.done` còn `false` | `exercise.py` → `next_item()` |
| H-3 | Đủ clip trong `storage/clips/bdc/` ở repo gốc: `intro_1…6.mp4` (720×1280, 9,96–10,03 giây) và `00.mp4` (3,42 giây) | `ffmpeg -i` từng file |
| H-4 | Bản dựng ngày 12/11 còn trong Thùng rác, đọc được: `script.json`, `audio_0…5.mp3`, `clip_0.mp4`, `video.mp4` | `~/.Trash/studio-xoa-20261113/20261112_143304_baitap_bdc_00_gioithieu/` |
| H-5 | Bản 12/11 dùng **một clip duy nhất** `00.mp4` (đứng yên 3,42 giây) cho cả 6 cảnh: `scene_clip = [0,0,0,0,0,0]` | `script.json` cũ |
| H-6 | `line`, `screen`, `text`, `kind` của bản 12/11 **giống hệt** giáo trình hiện tại ở cả 6 cảnh | So từng trường bằng script |
| H-7 | Giọng video bài tập luôn là nam Hà Nội (`nam_bac`): `choose_persona({"category": "tập luyện"})` khớp từ khoá `tap luyen` | `demo.py` → `PERSONA_KEYWORDS`; `exercise.py` → `run_next()`; `script.json` cũ |
| H-8 | 6 file giọng 12/11 không còn tiếng nổ ở mép: chạy `clean_gemini_audio` trên bản sao không đổi file nào | Chạy thử trong thư mục tạm |
| H-9 | Lúc 17:20 có một lần chạy `demo.py --exercise` không hoàn tất, để lại thư mục `20261113_172043_baitap_bdc_00_gioithieu` (thấy lúc 18:29: 6 clip, `audio_1.mp3`, `audio_0.mp3` 0 byte, không `script.json`). **Lúc 18:38 thư mục này đã không còn** | `ls -la` hai thời điểm |
| H-10 | Video bài tập duyệt bằng hỏi `y/n` trên Terminal, không theo `APPROVAL_MODE=web`. `approval_step` chỉ nhận đúng chữ `y` (sau khi bỏ khoảng trắng, đổi về chữ thường); `yes`, `có`, `ok` đều thành `rejected` | `exercise.py` → `finish()`; `demo.py` → `approval_step()` |
| H-11 | Gõ `y`: ghi `post.txt`, đặt `done = true` trong giáo trình, và vì `.env` có `DRIVE_FOLDER_ID` nên tải lên Drive rồi **xoá thư mục trên máy** (trừ khi có `--keep-local`). Sau đó video không còn trong Studio | `exercise.py` → `finish()`; `demo.py` → `move_to_drive()`; `api/studio.py` chỉ liệt kê thư mục có `video.mp4` |
| H-12 | `demo.py`, `exercise.py` ở repo gốc (`1ce153a`) giống hệt worktree (`155e27e`) | `diff` từng file |
| H-13 | **Video 00 đã được làm và duyệt lúc 18:30–18:33.** `TODO.md` ở repo gốc (chưa commit) ghi: "đã dựng `20261113_183051_baitap_bdc_00_gioithieu` (51.8s, 6 cảnh) và tải lên Google Drive (2026-11-13)". Giáo trình ở repo gốc (chưa commit) có `intro_video.done = true`. `storage/videos/` không còn thư mục bài tập nào | `git diff` ở repo gốc; `ls -la storage/videos/` lúc 18:38 |
| H-14 | `rerender()` lấy lời, chữ màn hình, tiêu đề, caption từ `script.json` **trong thư mục video**. Nó chỉ đọc giáo trình để chọn clip. Sửa chữ trong giáo trình không tự vào video dựng lại | `exercise.py` → `rerender()` dòng 664–685 |
| H-15 | Dòng "Bài vận động nhẹ, không phải phương pháp chữa bệnh" chỉ được vẽ cho cảnh loại `ex_end`. Cảnh cuối của video mở đầu là `ex_end_intro` nên **không có** dòng này trên hình. Caption của video mở đầu thì đã có câu này | `exercise.py` → `_overlay()` dòng 421–429; giáo trình → `intro_video.caption` |
| H-16 | Câu khuyên hỏi bác sĩ có sẵn trong giáo trình ở mục `safety` cấp gốc: "Người đang có bệnh, đau lưng, cao huyết áp, mới phẫu thuật nên hỏi bác sĩ trước khi tập." Mục này hiện không được đưa vào video hay caption nào | `content/exercise_curriculum.json` dòng 3–5; `grep` trong `exercise.py` |

**Điều chưa biết**:
- Ai làm bản 18:30, có xem và nghe trước khi duyệt không, và bản đó ra giọng nào (Gemini model nào, hay edge-tts). Thư mục trên máy đã bị xoá nên BA không đọc được `script.json` của nó. Thời lượng 51,8 giây khác 52,0 giây của giọng 12/11, nên đây là bản thu giọng mới.
- Người vận hành chê bản 12/11 ở điểm nào. H-5 cho thấy hình là điểm yếu rõ nhất, nhưng đây là **suy đoán**.
- Số lượt giọng Gemini đã dùng hôm nay: ít nhất 2 (lần 17:20) cộng 6 nếu bản 18:30 dùng Gemini. Chính xác: chưa rõ.

**Ràng buộc**:
- Chi phí $0 (P02). Giọng Gemini miễn phí: 10 lượt/ngày cho mỗi model (nguồn: thông báo lỗi 429 trong `demo.py` → `_gemini_tts`; `.env.example`).
- Lời đọc video bài tập lấy nguyên văn giáo trình đã duyệt, không qua AI.
- Một video một bộ giọng (C-0001-1). Không đụng `app.html` (C-0001-4).

---

## Quyết định

> **Không sửa `*.py`. Nếu bản 18:30 trên Drive được người dùng nhận là bản cuối (Q-0) thì không dựng gì thêm; chỉ cập nhật tài liệu. Nếu cần làm lại hoặc chỉnh theo góp ý MKTG: dựng bằng lệnh có sẵn `demo.py --exercise-rerender` trên một thư mục chứa `script.json` + 6 file giọng đã có (0 lượt giọng), sau khi chỉnh chữ màn hình. Chữ màn hình sửa ở hai nơi: giáo trình (Dev, trong worktree) và bản `script.json` của thư mục video (bước vận hành).**

Nguồn giọng để dựng lại, theo thứ tự ưu tiên:
1. Thư mục bản 18:30 tải về từ Drive, nếu người dùng thấy giọng đó đạt.
2. Giọng 12/11 trong Thùng rác (phương án A ban đầu, MKTG ủng hộ).
3. Thu mới (phương án B), khi cả hai giọng trên không đạt hoặc khi đổi lời đọc.

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| E | Nhận bản 18:30 trên Drive là bản cuối, không dựng lại | Tuỳ Q-0 | $0, không việc gì thêm. Nhưng bản đó chưa qua review MKTG và mang nguyên các điểm MKTG nêu (cùng chữ, cùng clip) |
| A | Chép `script.json` + `audio_0…5.mp3` (từ Drive hoặc Thùng rác) sang thư mục mới, chỉnh chữ màn hình trong `script.json`, chạy `--exercise-rerender` | ⭐ khi cần làm lại | 0 lượt giọng, không phụ thuộc quota. Lời đã khớp giáo trình (H-6). `rerender()` xoá `clip_*.mp4` cũ rồi chép clip theo giáo trình; file giọng tìm theo tên trong thư mục mới |
| B | Tạo mới: `demo.py --exercise` | Dự phòng | 6 lượt trên `gemini-2.5-flash-preview-tts`. Thiếu lượt thì máy tự đọc lại cả 6 câu bằng `gemini-3.1-flash-tts-preview` (model của bài 2), rồi edge-tts, không hỏi trước. **Giờ còn phải đặt lại `intro_video.done = false` ở repo gốc** (H-2, H-13), nếu không lệnh sẽ nhảy sang bài 2 |
| C | Đưa nguyên thư mục 12/11 từ Thùng rác về `storage/videos/` | - | Kết quả như A, nhưng khôi phục cả `video.mp4`, `clip_0.mp4` cũ mà người dùng đã yêu cầu xoá |
| D | Sửa code để video bài tập duyệt trên Studio rồi mới làm | - | Ngoài yêu cầu. Đề xuất DR riêng (Q-5, MKTG ủng hộ) |
| F | Sửa `_overlay()` để cảnh `ex_end_intro` tự vẽ dòng miễn trừ | - | DR-0003 (`cta-safe-zone`, chưa merge) đang sắp lại toàn bộ `_overlay` và `VIDEO_BOX`; sửa ở đây sẽ đụng nhau. Đưa dòng miễn trừ vào `screen` của cảnh 6 đạt cùng kết quả mà không sửa code. Chuyển góp ý này sang DR-0003 |

---

## Góp ý MKTG và cách xử lý

Số đo dưới đây do BA dựng lớp chữ bằng chính `exercise._overlay()` với font thật, đo mép dưới của chữ trên khung 1080×1920. Mốc so sánh: `SAFE_BOTTOM = 1570` của DR-0003 (số đo từ ảnh chụp máy thật; DR-0003 chưa được duyệt, nên mốc này là tạm). MKTG ước "khoảng 175 px dưới cùng" bằng mắt; số đo thật là 273 và 283 px tính từ đáy.

### Chữ trên hình (không đổi `line`, 0 lượt giọng)

| # | Mức | Cảnh | Hiện tại (mép dưới) | Đề xuất của MKTG (mép dưới) | BA đề xuất đưa vào Q-6 |
|---|-----|------|---------------------|------------------------------|------------------------|
| M-1 | Nên sửa | 6 | "Ngày mai: Bài 1 · Hai tay nâng trời" (1500). Không có dòng miễn trừ (H-15) | "Ngày mai: Bài 1 · Hai tay nâng trời. Bài vận động nhẹ, không phải phương pháp chữa bệnh." → 3 dòng, **1638**, vượt mốc 68 px, tức tự tạo lại lỗi M-2 | "Ngày mai: Bài 1 · Hai tay nâng trời. Vận động nhẹ, không phải chữa bệnh." → 2 dòng, **1569** |
| M-1b | Nên sửa | Caption | Đã có "Bài vận động nhẹ, không phải phương pháp chữa bệnh." | Thêm "Đang có bệnh nên hỏi bác sĩ trước khi tập." | Nhận. Rút gọn từ `safety` (H-16) |
| M-2a | Nên sửa | 3 | 3 dòng, **1647** (vượt 77 px) | "17 thử nghiệm (2022): người lớn tuổi giữ thăng bằng tốt hơn" → 2 dòng, **1578** (vượt 8 px) | Nhận. Vượt 8 px so với mốc tạm; Tester xem khung hình |
| M-2b | Nên sửa | 5 | 3 dòng, **1637** (vượt 67 px) | "Sáng sớm hoặc chiều mát · đồ rộng · tránh lúc ăn no · khoảng 10 phút" → 2 dòng, **1567** | Nhận |
| M-3 | Gợi ý | Tiêu đề lớn | "Bát Đoạn Cẩm là gì?" → 1 dòng, mép dưới 266 | Ba phương án, đều thành 2 dòng: "8 động tác, truyền lại hơn 800 năm" (360), "Không dụng cụ, đứng tại chỗ, tập gì?" (360), "Ngồi nhiều, ít vận động? Xem bài này" (**374**) | Người dùng chọn (Q-7). Khung clip bắt đầu ở y = 360: hai phương án đầu chạm sát mép, phương án ba đè lên clip 14 px. Phương án đầu lặp ý với nhãn vàng cảnh 1 "8 động tác · hơn 800 năm" |
| M-4 | Gợi ý, chỉ khi làm B | Lời cảnh 1, 3 | "truyền lại hơn tám trăm năm"; câu cảnh 3 dài | Đổi thành "cái tên đã có hơn tám trăm năm" (`_sources` chỉ chứng minh **tên** có từ thế kỷ 12); tách câu cảnh 3 | Không làm trong A vì đổi `line` là phải thu lại (C-0005-2). Ghi vào Q-8 |

Cảnh 2 hiện ở 1576 (vượt mốc tạm 6 px), MKTG không nêu; để nguyên.

### Clip so với cảnh (MKTG xem khung hình)

| Clip | Mức | Nhận xét | Xử lý |
|------|-----|----------|-------|
| `intro_6` | Nên sửa | Lời mở cảnh nói "giương cung bắn chim", clip lại là đan tay đẩy lên đầu (động tác bài 1). Prompt yêu cầu tấn ngựa giương cung | Người dùng chọn tạo lại clip hay chấp nhận (Q-1) |
| `intro_3` | Gợi ý | Prompt là nhìn ngang, chuyển trọng tâm; clip là đẩy tay lên đầu. Clip 1, 3, 6 gần giống nhau | Như trên |
| `intro_5` | Gợi ý | Gần như đứng yên, lại chạy chậm 1,09 lần | Như trên |
| `intro_2` | Chấp nhận | Nửa người thay vì cận bàn tay | — |
| `intro_1`, `intro_4` | Khớp | — | — |
| Chung | Ghi nhận | Nền không đồng nhất: lối đá (1, 3, 5), bãi cỏ (2, 4), mép cỏ (6). Dấu sao Gemini ở góc dưới phải của `intro_3/5/6` | Việc mở sẵn trong `TODO.md` (chưa khoá được nền) |
| Bố cục | Nên sửa, ngoài phạm vi | Clip 720×1280 nên người chỉ chiếm ô hẹp giữa khung, hai bên nền mờ | R-6. Thuộc DR-0003 (`VIDEO_BOX`). Thêm lựa chọn vào Q-1 |

---

## Thay đổi cấu trúc

Không đổi luồng, API hay cấu trúc dữ liệu. Chỉ đổi **giá trị chữ** trong giáo trình, nếu người dùng duyệt Q-6:

| Đối tượng | Trước | Sau |
|-----------|-------|-----|
| `intro_video.segments[2].screen` | "Tổng hợp 17 thử nghiệm (2022): người lớn tuổi tập bài này giữ thăng bằng tốt hơn." | "17 thử nghiệm (2022): người lớn tuổi giữ thăng bằng tốt hơn" |
| `intro_video.segments[4].screen` | "Sáng sớm hoặc chiều mát · đồ rộng · không tập khi vừa ăn no · cả bài khoảng 10 phút" | "Sáng sớm hoặc chiều mát · đồ rộng · tránh lúc ăn no · khoảng 10 phút" |
| `intro_video.segments[5].screen` | "Ngày mai: Bài 1 · Hai tay nâng trời" | "Ngày mai: Bài 1 · Hai tay nâng trời. Vận động nhẹ, không phải chữa bệnh." |
| `intro_video.caption` | "… Bài vận động nhẹ, không phải phương pháp chữa bệnh." | Thêm cuối: " Đang có bệnh nên hỏi bác sĩ trước khi tập." |
| `intro_video.title` | "Bát Đoạn Cẩm là gì?" | Theo Q-7; mặc định giữ nguyên |

`line` của cả 6 cảnh **không đổi**.

---

## Chi phí

| Việc | Tốn gì | Nguồn |
|------|--------|-------|
| Phương án E | $0 | — |
| Phương án A, kể cả chỉnh chữ màn hình | $0, 0 lượt giọng. `rerender()` không gọi TTS | `exercise.py` → `rerender()` |
| Phương án B | $0, 6 lượt Gemini TTS trên `gemini-2.5-flash-preview-tts` (đổi được bằng `EXERCISE_EXTRA_TTS_MODEL`) | `exercise.py` dòng 40, 654–656 |
| Hạn mức | 10 lượt/ngày mỗi model, free tier | `demo.py` → `_gemini_tts`; `.env.example` dòng 19, 26 |
| Lượt đã dùng hôm nay | Ít nhất 2; có thể thêm 6 (H-13). Chính xác: chưa rõ | — |
| Giờ hạn mức làm mới | Chưa rõ | — |
| Tạo lại clip `intro_6` (nếu chọn) | Lượt tạo video trong app Gemini của người vận hành. `TODO.md` ghi "Gemini Pro hết lượt 2026-11-13"; số lượt mỗi ngày: chưa rõ | `TODO.md` M2c |
| Drive | Duyệt lần nữa sẽ tải thêm một thư mục lên `video_output/Bài tập - Bát Đoạn Cẩm/`. Có ghi đè bản 18:30 hay tạo bản thứ hai: chưa rõ (chưa đọc `drive_upload.py`) | — |

Thời lượng phương án A với giọng 12/11: **52,0 giây** (tổng `scene_dur` trong `script.json` cũ). Mỗi clip khoảng 10 giây nên không cảnh nào chạy tới-lui; cảnh 5 chậm 1,09 lần (`exercise.py` → `_clip_input()`).

---

## Các bước vận hành

Mọi lệnh chạy ở **repo gốc**. Không cần merge hay pull trước để dựng lại (H-12, H-14). Riêng phương án B thì chữ màn hình lấy từ giáo trình của repo gốc, nên phải merge nhánh này trước, nếu không video B sẽ mang chữ cũ.

### Phương án A

| Bước | Ai làm | Việc | Thấy gì |
|------|--------|------|---------|
| A-0 | Người điều phối | Xác nhận không còn thư mục dở dang trong `storage/videos/` (lúc 18:38 đã sạch) | `storage/videos/` chỉ có thư mục sản phẩm |
| A-1 | Người điều phối, sau khi người dùng đồng ý (Q-2) | Tạo `storage/videos/<YYYYmmdd_HHMMSS>_baitap_bdc_00_gioithieu/`. **Chép** vào đó `script.json` và `audio_0.mp3` … `audio_5.mp3` từ nguồn giọng đã chọn | Thư mục có đúng 7 file |
| A-1b | Người điều phối | Chỉ khi Q-6/Q-7 được duyệt: trong `script.json` vừa chép, sửa `segments[2,4,5].screen`, `caption`, `hook` cho **trùng từng chữ** với giáo trình đã sửa trong worktree. Không đụng `line`, `audio_path`, `duration` | So lại bằng script: 6/6 `line` vẫn trùng, các trường đã sửa trùng giáo trình mới |
| A-2 | Người điều phối | `printf 'n\n' \| .venv/bin/python demo.py --exercise-rerender storage/videos/<thư mục mới>`. Trả lời sẵn `n` để máy chỉ dựng | `Clips: ['local:intro_1.mp4', …, 'local:intro_6.mp4']`, 6 dòng `Scene N`, `✅ Video: …`, rồi `rejected`. `rejected` ở đây nghĩa là "chưa duyệt, giữ file". Cửa sổ phát video sẽ tự bật trên máy |
| A-3 | MKTG | Review bản dựng | `marketing-review.md` |
| A-4 | Người vận hành | Bấm đúp `scripts/mo-studio.command` để mở Studio. Video hiện với nhãn **Chỉ xem**. **Trang này chỉ để xem. Duyệt làm ở Terminal (bước A-5).** Xem hết và nghe kỹ các con số: "tám trăm năm", "thế kỷ mười hai", "hai nghìn không trăm hai mươi hai", "mười bảy thử nghiệm", "mười phút" | Video khoảng 52 giây, mỗi cảnh một clip |
| A-5 | Người vận hành | Đạt: dán nguyên dòng lệnh người điều phối đưa sẵn (`.venv/bin/python demo.py --exercise-rerender storage/videos/<thư mục mới>`). **Máy dựng lại và mở video. Xem lại lần cuối rồi mới gõ.** Gõ **đúng một chữ `y`** rồi Enter. **Gõ `y` xong, video chỉ còn trên Drive, không còn trong Studio. Chưa chắc thì gõ `n`.** Thấy `Rejected` thì không mất gì, chạy lại lệnh. Chưa đạt vì giọng: báo người điều phối, sang B. Chưa đạt vì một clip: tạo lại clip đó trong app Gemini, bỏ vào `storage/clips/bdc/`, rồi **báo người điều phối dựng lại** | Gõ `y`: `Curriculum: Bát Đoạn Cẩm video mở đầu → done`, đường dẫn Drive, `Deleted local folder` |
| A-6 | Người vận hành | Đăng theo mục 4b bước 4 của hướng dẫn vận hành: không gắn sản phẩm, bật nhãn "Nội dung do AI tạo". **Đăng bài 1 đúng ngày hôm sau**: lời đọc, nhãn, chữ màn hình và caption của video này đều hứa "ngày mai" | Video lên kênh |

### Phương án B

| Bước | Ai làm | Việc | Thấy gì |
|------|--------|------|---------|
| B-0 | Người điều phối | Merge nhánh này (để chữ mới vào giáo trình ở repo gốc) và đặt lại `intro_video.done = false` | `git diff` ở repo gốc |
| B-1 | Người vận hành | `.venv/bin/python demo.py --exercise` | Dòng đầu phải là `🧘 Bát Đoạn Cẩm — video mở đầu`. Nếu là bài 2 hoặc `chưa có clip`: dừng, báo người điều phối |
| B-2 | Người điều phối đọc thay, hoặc người vận hành | Tìm dòng bắt đầu bằng `✅ Voiceover`. Trong ngoặc là `gemini, gemini-2.5-flash-preview-tts`: đúng dự kiến. Trong ngoặc có chữ `edge`, hoặc tên khác `gemini-2.5-flash-preview-tts`: máy đã hết lượt và tự đổi giọng, gõ `n` | — |
| B-3 | Người vận hành | Gõ `n` thì thư mục được giữ lại. Chạy lại B-1 vào ngày khác sẽ thu lại cả 6 câu | — |
| B-4 | Người vận hành | Giọng đạt: xem, nghe số như A-4, rồi gõ **đúng một chữ `y`** và Enter. Thấy `Rejected` thì không mất gì: chạy `--exercise-rerender` trên thư mục vừa tạo (không tốn lượt giọng) | Như A-5 |

### Sau khi duyệt

| Bước | Ai làm | Việc |
|------|--------|------|
| X-1 | Người điều phối | Đưa `intro_video.done = true` và sửa đổi `TODO.md` đang chưa commit ở repo gốc vào PR. Lưu ý nhánh này cũng sửa cùng hai file đó (chữ giáo trình, `TODO.md`), cần gộp tay |

---

## Việc của Dev

Chỉ làm sau khi người dùng duyệt Q-6 (và Q-7 nếu đổi tiêu đề). Một file, không có `*.py`:

| # | File | Việc |
|---|------|------|
| Dev-1 | `content/exercise_curriculum.json` (trong worktree) | Sửa `series[bdc].intro_video`: `segments[2].screen`, `segments[4].screen`, `segments[5].screen`, `caption` đúng như bảng § Thay đổi cấu trúc; `title` theo Q-7. Không đổi `line`, `kind`, `text`, `clip`, `clip_prompts`, `_sources`, `done`. Giữ định dạng file (2 khoảng trắng, `ensure_ascii=False`, xuống dòng cuối) để `mark_done()` không tạo diff thừa |

Nếu người dùng không duyệt Q-6: **không sửa gì**, Dev không có việc.

Không giao cho Dev trong DR này: `_overlay()` cho `ex_end_intro` (phương án F, chuyển DR-0003), bố cục `VIDEO_BOX` (DR-0003), duyệt trên Studio (DR riêng).

---

## Không làm

- Không sửa `demo.py`, `exercise.py`, Studio, `app.html`.
- Không đổi **lời đọc** (`line`) trong phương án A: lời đổi thì giọng cũ không dùng được (C-0005-2). Chữ màn hình (`screen`), tiêu đề (`title`), caption **được đổi** mà không ảnh hưởng giọng, nhưng phải qua người dùng duyệt (Q-6, Q-7) vì đây là nội dung người vận hành đã duyệt.
- Không sửa `_sources` (không đổi số liệu nào).
- Không làm lại clip thay người vận hành.
- Không chạy `--skip-approval`, không gõ `y` thay người vận hành (C-0005-1).
- Không đưa video bài tập vào luồng duyệt Studio, không thêm cờ "hết lượt Gemini thì dừng". Đề xuất DR riêng (DR-0002 của `gemini-quota` đã bàn phần quota).
- Không đăng TikTok thay người vận hành.

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 1 | Phân tích, viết DR, đưa góp ý MKTG vào | BA | Yêu cầu, code, storage, review MKTG | DR này | `docs/decision-records/` |
| 2 | Trả lời Q-0 … Q-8 | Người dùng | DR này | Quyết định | — |
| 3 | Sửa chữ trong giáo trình (nếu Q-6 được duyệt) | Dev | Q-6, Q-7 | Dev-1 | `content/exercise_curriculum.json` |
| 4 | Soát diff: chỉ các trường cho phép bị đổi | Reviewer | #3 | Ghi chú review | DR § Kết quả |
| 5 | Chạy thử trên bản sao theo bảng E2E | Tester | #3 | Kết quả V-x | DR § Kết quả |
| 6 | Dựng bản thật (A-0 … A-2) | Người điều phối | Q-0, Q-2 | Thư mục video chờ duyệt | `storage/videos/` |
| 7 | Review bản dựng | MKTG | #6 | `marketing-review.md` | Thư mục video |
| 8 | Xem, nghe, gõ `y`, đăng | Người vận hành | #6, #7 | Video trên Drive và trên kênh | — |
| 9 | Cập nhật tài liệu SSoT, `TODO.md` | BA | #3–#8 | Docs | xem § SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Người vận hành chê bản 12/11 vì giọng | Bản A không đạt | A tốn 0 lượt, thử trước không mất gì |
| R-2 | Rủi ro | B thiếu lượt, máy tự đổi giọng | Giọng khác dự kiến; mất lượt của bài 2 | B-2. Ưu tiên chạy B ngày khác |
| R-3 | Rủi ro | Có người duyệt trước khi người vận hành xem (H-13 có thể là một trường hợp như vậy) | Video chưa xem bị đánh dấu xong, lên Drive, xoá trên máy | C-0005-1. A-2 trả lời sẵn `n` |
| R-4 | Rủi ro | Thùng rác bị dọn | Mất giọng 12/11 | Làm A-1 sớm, hoặc dùng bản trên Drive |
| R-5 | Rủi ro | Lệnh tự mở trình phát video dù trả lời sẵn `n` | Cửa sổ bật trên máy người vận hành | Báo trước |
| R-6 | Rủi ro | Clip dọc 720×1280 đặt vừa khung 1080×920: người chiếm ô hẹp ở giữa | Cảnh toàn cảnh trông nhỏ | Q-1; sửa bố cục thuộc DR-0003 |
| R-7 | Rủi ro | Sửa giáo trình mà quên sửa `script.json` đã chép, hoặc sửa lệch nhau (H-14) | Video dựng lại vẫn mang chữ cũ; giáo trình và video lệch nhau | A-1b so bằng script; Tester kiểm D-13 |
| R-8 | Rủi ro | Nhiều cửa sổ làm cùng lúc trên repo gốc (H-9, H-13; 6 worktree đang mở) | Hai bên cùng dựng, cùng sửa giáo trình và `TODO.md` | Người điều phối chốt một bên làm video này. X-1 gộp tay |
| R-9 | Rủi ro | Mốc 1570 lấy từ DR-0003 chưa duyệt | Tiêu chí D-4 có thể đổi | Ghi rõ là mốc tạm; Tester ghi số đo thật, không chỉ đạt/không đạt |
| A-1 | Giả định | Giọng 12/11 hoặc giọng 18:30 đạt | Sai thì B | Q-0, Q-1 |
| A-2 | Giả định | `line` trong giáo trình không đổi từ giờ tới lúc dựng | Đổi thì H-6 hết đúng | Tester so lại ở V-1 |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0005-1 | Video bài tập chỉ được duyệt khi **người vận hành** đã xem và tự gõ `y`. Agent và script tự động không dùng `--skip-approval` và không trả lời `y` cho `--exercise` / `--exercise-rerender` | Duyệt là đánh dấu `done`, tải lên Drive và xoá bản trên máy (H-11). Giọng AI có thể đọc sai số | Mọi lần chạy `demo.py --exercise*` | Khi video bài tập có luồng duyệt trên Studio |
| C-0005-2 | Dùng lại giọng cũ cho một video bài tập chỉ khi `line` của mọi cảnh trong `script.json` trùng nguyên văn giáo trình hiện tại. Khác một chữ ở `line` thì thu lại cả video. Ràng buộc này **chỉ nói về `line`**: `screen`, `text`, `hook`, `caption` đổi được mà không cần thu lại | `--exercise-rerender` không so lời với giáo trình và không đọc lại câu đã đổi | Quy trình `--exercise-rerender` | Khi `rerender()` tự so và báo lệch |
| C-0005-3 | Khi dựng lại bằng `--exercise-rerender`, chữ trong `script.json` của thư mục video (`screen`, `text`, `hook`, `caption`) phải trùng giáo trình tại thời điểm duyệt | `rerender()` không đọc lại chữ từ giáo trình (H-14); nếu lệch, video đã đăng không còn khớp nguồn đã duyệt | Bước A-1b | Khi `rerender()` tự nạp lại chữ từ giáo trình |

Đang áp dụng, không đổi: C-0001-1, C-0001-4.

supersedes: —

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `TODO.md` (M2c) | Kết quả thật của video mở đầu. Gộp với sửa đổi chưa commit ở repo gốc (H-13). Thêm việc mở: duyệt video bài tập trên Studio; dòng miễn trừ cho `ex_end_intro` trong `_overlay` (chuyển DR-0003) | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` § 4b | (1) Sửa "Làm trong **cùng một cuộc trò chuyện**": code và `prompts_*.txt` ghi **mỗi prompt một cuộc trò chuyện mới**. (2) Tên clip mở đầu `intro_1…6.mp4`. (3) Gõ đúng một chữ `y`; gõ xong video chỉ còn trên Drive. (4) Studio chỉ để xem video bài tập, duyệt ở Terminal. (5) Video mở đầu tốn 6 lượt giọng, model riêng; cách đọc dòng `✅ Voiceover`. (6) Đăng bài 1 ngay hôm sau video mở đầu. (7) Dựng lại không tự lấy chữ mới từ giáo trình | [ ] |
| Cùng file, dòng 212 | "Video bài tập … làm bằng công cụ khác" → làm bằng `demo.py --exercise` | [ ] |
| `docs/specs/architecture/capabilities/video-render.md` | Thêm mục "Video bài tập" (luồng `exercise.py`, tên clip, ba loại video, model giọng, duyệt `y/n`, `rerender` lấy chữ từ `script.json`). Sửa dòng 194 "làm ngoài repo" | [ ] |
| `agent/CLAUDE.md` | Thêm `--exercise`, `--exercise-rerender`, `--allow-stock`; `exercise.py` + giáo trình; model giọng video bài tập | [ ] |
| `.env.example` | Thêm `EXERCISE_EXTRA_TTS_MODEL` (code đã đọc, file mẫu chưa có) | [ ] |
| `content/exercise_curriculum.json` | Dev-1 (nếu duyệt); `intro_video.done = true` do `mark_done()` ghi | [ ] |

## File thay đổi

- [ ] `content/exercise_curriculum.json`: Dev-1, chỉ khi Q-6 được duyệt
- Không đổi: mọi file `*.py`, `*.html`, `*.command`

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: hành vi

| # | Loại | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|------|-----------|------------------|-----------|
| D-1 | Bình thường | Thư mục chỉ có `script.json` + `audio_0…5.mp3`; đủ `intro_1…6.mp4`; `--exercise-rerender`, trả lời `n` | `clips` = 6 mục `local:intro_1.mp4` … `local:intro_6.mp4` đúng thứ tự, `scene_clip = [0,1,2,3,4,5]`, `stock = false`. Có `video.mp4`. Kết quả `rejected`, thư mục còn | Chạy trên bản sao, đọc `script.json` |
| D-2 | Bình thường | Như D-1 | 6 file `audio_*.mp3` không đổi (kích thước, mtime). Log không có dòng `Generating voiceover` | So `ls -la` trước và sau |
| D-3 | Bình thường | Như D-1, giọng 12/11 | Video 1080×1920, dài 52,0 giây (±0,5), có tiếng | `ffmpeg -i video.mp4` |
| D-4 | Bình thường | Như D-1, sau khi áp chữ mới (A-1b). Trích 1 khung giữa mỗi cảnh ở đúng 1080×1920 (không thu nhỏ) | (a) Mỗi cảnh một clip khác nhau. (b) Nhãn vàng lần lượt: "8 động tác · hơn 800 năm", "Nguồn gốc", "Điểm nổi bật", "Dành cho ai", "Tập khi nào", "Bắt đầu từ ngày mai". (c) Không có chữ "Hình minh hoạ". (d) Khối chữ dưới nhãn vàng **không quá 2 dòng** ở cả 6 cảnh. (e) Mép dưới của chữ: Tester ghi số y cho từng cảnh; mong đợi cảnh 3 ≤ 1580, cảnh 5 ≤ 1570, cảnh 6 ≤ 1570 (số BA đo: 1578, 1567, 1569). (f) Cảnh 6 có chữ "không phải chữa bệnh" | Đo (e): dựng lớp chữ bằng `exercise._overlay(script, i)` rồi lấy `getchannel('A').getbbox()[3]`; hoặc trên khung hình, tìm hàng pixel thấp nhất còn chữ trắng viền đen dưới nhãn vàng |
| D-5 | Bình thường | Bản sao có `intro_video.done = false`; `--exercise` với edge-tts, trả lời `n` | Dòng đầu `Bát Đoạn Cẩm — video mở đầu`; thư mục `…_baitap_bdc_00_gioithieu`; 6 audio mới; `voice_persona = nam_bac`; chữ màn hình là chữ mới của giáo trình; `rejected` | Chạy trên bản sao, không `.env` |
| D-6 | Lỗi | Thư mục không có `script.json`; `--exercise-rerender` | Kết quả `error`, không tạo `video.mp4`, giáo trình không đổi | Chạy trên bản sao |
| D-7 | Lỗi | Xoá `audio_3.mp3` trong bản sao; `--exercise-rerender` | Kết quả `error` (FFmpeg), giáo trình không đổi | Chạy trên bản sao |
| D-8 | Biên | Thiếu `intro_4.mp4` trong bản sao; `--exercise-rerender` | Vẫn dựng; cảnh 4 dùng `00.mp4` (clip đầu tiên có sẵn trong danh sách `00.mp4`, `intro_1…6`) | Đọc `clips`, `scene_clip` |
| D-9 | Biên | `storage/clips/bdc/` trống, `done = false`; `--exercise` | `needs_clips`; `prompts_intro.txt` liệt kê 7 clip; không có `audio_*`; không tạo thư mục video | Chạy trên bản sao |
| D-10 | Biên | Trả lời `y` cho `--exercise-rerender` trên bản sao, không `DRIVE_FOLDER_ID` | `post.txt` có caption mới (có "hỏi bác sĩ") và dòng "KHÔNG gắn sản phẩm"; giáo trình **bản sao** có `intro_video.done = true`; thư mục giữ lại; `ready_for_manual_upload` | Chạy trên bản sao |
| D-11 | Biên | Trả lời `yes`, rồi `Y`, cho `--exercise-rerender` trên bản sao | `yes` → `rejected`, không có `post.txt`, giáo trình không đổi. `Y` → duyệt như D-10 | Chạy trên bản sao |
| D-12 | Hồi quy | `intro_video.done = true` trong bản sao; `--exercise` | Việc kế tiếp là bài 2: `needs_clips` + `prompts_02.txt`. Video mở đầu không bị làm lại | Chạy trên bản sao |
| D-13 | Hồi quy | Sau Dev-1, chỉ sửa giáo trình, **không** sửa `script.json` đã chép; `--exercise-rerender` | Video vẫn mang chữ cũ (xác nhận H-14, lý do có bước A-1b) | Xem khung hình cảnh 3 |
| D-14 | Hồi quy | `git diff origin/main` của nhánh | Không đổi `*.py`, `*.html`, `*.command`. Trong giáo trình chỉ đổi các trường liệt kê ở Dev-1; 6 `line` giữ nguyên từng chữ | `git diff --stat`; so `line` bằng script |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | Hướng dẫn vận hành § 4b | Sửa | "Mỗi prompt một cuộc trò chuyện mới"; có `intro_1…6.mp4`; "gõ đúng một chữ `y`"; "gõ xong video chỉ còn trên Drive" | So với `exercise.py`, `demo.py` → `approval_step()` |
| DD-2 | `video-render.md` | Thêm | Có mục "Video bài tập", khớp code; không còn "làm ngoài repo" | So với `exercise.py` |
| DD-3 | `agent/CLAUDE.md`, `.env.example` | Thêm | 3 cờ `--exercise*`; `EXERCISE_EXTRA_TTS_MODEL` mặc định đúng như `exercise.py` dòng 40 | `grep` |
| DD-4 | `TODO.md` | Sửa | Phản ánh đúng bản nào là bản cuối của video mở đầu | Đọc lại |

### Kiểm tra E2E (Tester)

Điều kiện chung: chạy trong **bản sao** repo ở thư mục tạm, không `.env` (edge-tts, không Drive, không Sheet). Chép `storage/clips/bdc/*.mp4` và 7 file của bản 12/11 vào bản sao. Không gọi Gemini; không đụng `storage/` thật, Drive, Sheet, TikTok. Câu trả lời `y/n` đưa qua stdin. Lệnh sẽ tự mở trình phát video trên macOS.

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| V-1 | Lời cũ khớp giáo trình sau Dev-1 | So `line` 6 cảnh giữa `script.json` cũ và giáo trình trong bản sao | Trùng 6/6 | — | — |
| V-2 | Phương án A | D-1 … D-4 | Đạt; ghi số đo y của D-4(e) cho từng cảnh | — | — |
| V-3 | Phương án B bằng edge-tts | D-5 | Đạt. Ghi rõ là giọng edge-tts | — | — |
| V-4 | Lỗi và biên | D-6 … D-9 | Đạt | — | — |
| V-5 | Duyệt | D-10, D-11, D-12 | Đạt | — | — |
| V-6 | Chữ giáo trình không tự vào video dựng lại | D-13 | Đạt | — | — |
| V-7 | Không đụng dữ liệu thật | So `ls -la storage/videos/`, `storage/clips/bdc/` và `git status` ở repo gốc trước và sau | Không đổi | — | — |
| V-8 | Bản dựng thật | Sau A-2: lặp D-1 … D-4 trên thư mục thật (chỉ đọc) | Đạt | — | — |
| V-9 | Người vận hành nghe số | A-4 | Xác nhận 5 con số đọc đúng | — | — |

Tester không kiểm được, phải ghi là chưa kiểm: giọng Gemini thật khi thu mới, tải lên Drive thật, nghe bằng tai, vị trí chữ trên máy điện thoại thật.

### Cổng chất lượng

- [ ] Người dùng đã trả lời Q-0, Q-1, Q-2, Q-6
- [ ] Đã kiểm hết bảng quyết định trên bản sao
- [ ] Bản dựng thật đạt V-8, MKTG đã review, người vận hành đã nghe số (V-9)
- [ ] Người vận hành tự gõ `y` (C-0005-1)
- [ ] Chữ trong `script.json` đã duyệt trùng giáo trình (C-0005-3)
- [ ] Không đổi `*.py` (D-14)
- [ ] Đã cập nhật tài liệu SSoT
- [ ] Số DR của các worktree khác đã được gán lại, không trùng

---

## Câu hỏi mở cho người dùng

| # | Câu hỏi | Vì sao cần | Mặc định nếu không trả lời |
|---|---------|-----------|---------------------------|
| Q-0 | Lúc 18:30 hôm nay đã có một video mở đầu được dựng, duyệt và tải lên Drive (`20261113_183051_baitap_bdc_00_gioithieu`, 51,8 giây). Bạn đã xem và nghe bản đó chưa? Đó có phải bản cuối để đăng không? | Nếu phải: không dựng gì thêm. Nếu chưa xem, hoặc muốn áp góp ý MKTG: làm tiếp phương án A | Coi như chưa chốt; không đăng |
| Q-1 | Bản 12/11 "chưa OK" ở điểm nào: **hình lặp một clip**, **hình nhỏ, hai bên mờ**, **giọng**, hay **lời**? Và clip `intro_6` (lời nói "giương cung", hình là đẩy tay lên đầu): tạo lại hay chấp nhận? | Hình lặp: A. Hình nhỏ: cần sửa bố cục (DR-0003), A chưa giải quyết. Giọng: B. Lời: sửa giáo trình rồi B | Không tự chọn |
| Q-2 | Dùng giọng nào để dựng lại: bản 18:30 (tải về từ Drive) hay bản 12/11 (chép từ Thùng rác, để nguyên Thùng rác)? | Hai bản thu khác nhau; chép lại từ nơi người dùng đã xoá cần được đồng ý | Chờ |
| Q-3 | Ai chạy `demo.py --exercise` lúc 17:20 và 18:30? Có cửa sổ làm việc nào khác đang làm cùng video này không? | Tránh hai bên cùng dựng, cùng dùng lượt giọng (R-8) | — |
| Q-4 | Nếu phải làm B: chạy hôm nay hay để ngày khác? | Hôm nay đã dùng ít nhất 2 lượt, có thể 8, trên model của video mở đầu | Để ngày khác |
| Q-5 | Có mở việc riêng để video bài tập duyệt được trên Studio không? (MKTG ủng hộ) | Người vận hành không rành kỹ thuật đang phải gõ `y/n` trên Terminal | Ghi vào `TODO.md` là việc mở |
| Q-6 | Duyệt 4 chỗ sửa chữ (không đổi lời đọc): cảnh 3, cảnh 5, cảnh 6 thêm "Vận động nhẹ, không phải chữa bệnh.", caption thêm "Đang có bệnh nên hỏi bác sĩ trước khi tập."? Xem bảng § Thay đổi cấu trúc | Đây là nội dung bạn đã duyệt trong giáo trình; đổi cần bạn đồng ý | Không sửa |
| Q-7 | Tiêu đề lớn: giữ "Bát Đoạn Cẩm là gì?" hay đổi sang một trong ba phương án ở M-3? | Phương án mới thành 2 dòng, chạm hoặc đè mép trên khung clip | Giữ nguyên |
| Q-8 | Khi nào thu giọng mới (B), có đổi "truyền lại hơn tám trăm năm" thành "cái tên đã có hơn tám trăm năm" và tách câu cảnh 3 không? | Nguồn dẫn chỉ chứng minh tên có từ thế kỷ 12. Đổi lời là phải thu lại 6 câu | Không đổi |

---

## Kết quả

Chưa thực hiện. BA điền sau khi Tester, MKTG và người vận hành xong.

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR liên quan | DR-0001 (C-0001-1, C-0001-4; giả định A-1 "video bài tập do script ngoài repo tạo" không còn đúng). DR-0003 trong worktree `cta-safe-zone` (vùng an toàn, `_overlay`, `VIDEO_BOX`; chưa merge). DR-0002 trong worktree `gemini-quota` (sổ đếm lượt giọng; chưa merge). DR-0002 trong worktree `clip-trim` (clip bài tập trên Studio; chưa merge) |
| Code đã đọc | `exercise.py` (toàn bộ), `demo.py` (`choose_persona`, `generate_voiceovers`, `gemini_tts_models`, `clean_gemini_audio`, `_text_block`, `_pill`, `approval_step`, `move_to_drive`, `main`), `backend/app/api/studio.py` (lọc danh sách, `view_only`) |
| Chưa đọc | `drive_upload.py` (hành vi khi tải trùng tên thư mục) |
| Dữ liệu đã đọc | `content/exercise_curriculum.json` (worktree và repo gốc); `storage/clips/bdc/`, `storage/videos/` ở repo gốc; thư mục bản 12/11 trong Thùng rác; `git diff` chưa commit ở repo gốc |
| Review | MKTG 2026-11-13 (người điều phối chuyển lại) |
