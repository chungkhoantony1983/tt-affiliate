# DR-0009: Cắt clip bài tập trên Studio (không cần gõ lệnh ffmpeg)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📋 Đề xuất | 2026-11-12 | Claude (BA) | chờ chungkhoantony1983 |

Capability: `video-render` (phần video bài tập, `exercise.py`) · Nhánh: `feat/clip-trim` · Domain workflow: `spec`

Vai trò: **BA** = agent `ba` · **Dev** = agent `dev` · **Reviewer** = agent `reviewer` · **Tester** = agent `tester` · **MKTG** = agent `marketing`, đánh giá dưới góc nhìn người vận hành không rành kỹ thuật.

---

## Bối cảnh

**Vấn đề (gốc rễ)**:

Clip động tác cho video bài tập do người vận hành tạo trong app Gemini (chế độ Tạo video, khung Dọc 9:16) theo `storage/clips/<series>/prompts_*.txt`. API key không có Veo nên không tạo tự động được (`TODO.md` §M2c). Quan sát khi làm series Bát Đoạn Cẩm (`bdc`) ngày 2026-11-12:

- File Gemini tải về luôn có dạng `~/Downloads/gemini_generated_video_<mã>.mp4`, 720×1280, 24 fps, 10,03 giây, có tiếng AAC, có ngôi sao watermark nhỏ góc dưới phải.
- Cả 2 clip làm hôm đó đều đúng động tác trong 3–4,5 giây đầu, sau đó nhân vật tự làm thêm động tác thừa (nâng tay lên ngực). Nếu để nguyên, video dạy **sai động tác** (nội dung sức khoẻ).
- Đã phải cắt tay bằng ffmpeg: `01_1.mp4` = 0–4,5 s, `00.mp4` = 0–3,4 s, tham số `-an -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart`. Điểm cắt chọn bằng cách xem dải khung hình 5 fps. Kiểm lại file `storage/clips/bdc/01_1.mp4`: 4,50 s, h264 yuv420p, 720×1280, 24 fps, không có audio.

Người vận hành không rành kỹ thuật nên không tự làm được các bước: tìm thời điểm cắt, gõ lệnh ffmpeg, đổi tên đúng `00.mp4` / `01_1.mp4`, bỏ đúng thư mục.

Thêm hai điểm phát hiện khi đọc code:

1. **Danh sách clip còn thiếu trong `prompts_*.txt` bị cũ.** `write_prompts` / `write_intro_prompts` chỉ ghi lại file khi chạy `demo.py --exercise` đúng bài đó. Ví dụ `storage/clips/bdc/prompts_intro.txt` và `prompts_01.txt` vẫn liệt kê `00.mp4` (và `01_1.mp4`) dù 2 file này đã có. Vì vậy công cụ mới **không được** đọc danh sách thiếu từ `prompts_*.txt`. Phải tính từ giáo trình cộng với file có thật.
2. **Clip được lặp và làm chậm khi dựng.** `exercise.render` dùng `-stream_loop -1` và `setpts` với hệ số chậm tối đa `MAX_SLOWDOWN = 1.6`. Clip chỉ dùng hình (`[v:v]`), tiếng lấy từ giọng đọc. Một clip 3,4 s mà cảnh dài 7 s sẽ chạy chậm x1,6 rồi lặp lại, nên chỗ nối cuối → đầu lộ ra rõ. Người vận hành cần xem trước đoạn cắt **khi lặp** chứ không chỉ xem một lần.

**Lý do làm bây giờ**: người dùng yêu cầu ngày 2026-11-12. Series `bdc` cần 34 clip (đếm từ `content/exercise_curriculum.json`: `00.mp4` + `intro_1`, `intro_2` + 31 bước của 8 bài, tức 4×7 + 3). Đã có `00.mp4` và `01_1.mp4`, còn 32 clip phải tạo và cắt.

**Ràng buộc**:
- Chi phí $0 (P02). Không gọi Gemini/Groq API. FFmpeg chạy local (`imageio-ffmpeg`, đã có trong `requirements-demo.txt`).
- Không đổi `app.html` (C-0001-4, app TikTok đang xét duyệt).
- Theo DR-0001: xử lý video không nằm trong `api/studio.py` (C-0001-2); API ghi cần header `X-Studio` và Host local (C-0001-3).
- Không có test suite (`.claude/CLAUDE.md`).

---

## Quyết định

> **Thêm mục "Clip bài tập" vào trang Studio, đi theo đúng thứ tự làm việc thật: máy chọn sẵn bước còn thiếu đầu tiên của video sắp làm → người bấm "Chép gợi ý tạo video", tạo clip trong app Gemini, tải về → quay lại Studio, máy tự chọn file mới nhất chưa dùng → xem đoạn đã chọn tự lặp lại (đặt sẵn 0–4 giây), chỉnh điểm cắt bằng dải khung hình → bấm "Lưu thành Bài 1 · Bước 2" ngay cạnh đoạn lặp và mô tả động tác của bước đó → máy phát lại clip đã lưu và đưa nút "Làm bước tiếp theo". Phần xử lý video (đọc thông tin, trích khung hình, cắt) nằm trong `exercise.py`, gọi qua cờ mới của `demo.py`. Studio chỉ chạy subprocess, giống DR-0001. Điểm cắt do người chọn. Không tự phát hiện động tác thừa trong DR này; chỉ ghi lại các điểm người đã chọn để sau này đánh giá có nên làm gợi ý tự động hay không.**

Chi phí: **$0**. Mọi bước chạy FFmpeg trên máy. Không gọi API nào. Lượt tạo video trong app Gemini là việc người vận hành vẫn làm như cũ, công cụ không đổi số lượt đó (hạn mức lượt của app Gemini: chưa rõ, không có nguồn trong repo).

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Mục "Clip bài tập" trên Studio + cờ CLI trong `demo.py` (Studio gọi bằng subprocess) | ⭐ | Người vận hành chỉ bấm và nhìn, không cần đổi tên file hay biết thư mục. Studio đã có sẵn (DR-0001), mở bằng bấm đúp `scripts/mo-studio.command`. Cờ CLI tự có luôn cho người kỹ thuật hoặc agent dùng. Tên đích chọn từ danh sách nên không gõ sai |
| B | Chỉ làm script CLI (`demo.py --clip-cut … --start … --end …`) | - (chỉ làm như lớp bên dưới A) | Vẫn phải gõ lệnh và tự tìm số giây, tức là đúng việc người dùng muốn bỏ. Không xem được khung hình hay lặp thử |
| C | Chỉ viết hướng dẫn (QuickTime Player → Sửa → Cắt bớt, rồi đổi tên) | - | QuickTime xuất `.mov` (mã hoá tuỳ máy), trong khi `exercise.py` chỉ tìm đúng tên `.mp4`. Vẫn giữ tiếng, vẫn phải tự đổi tên và chép vào thư mục. Không xem được cảnh lặp. Nhiều bước thủ công nên dễ sai |
| D | Tự động cắt (phát hiện chuyển động thừa) rồi lưu luôn, không cần người chọn | - | Động tác đúng và động tác thừa đều là chuyển động chậm. Đo độ lệch khung hình không biết được động tác nào "đúng giáo trình". Cắt sai thì video dạy sai động tác (nội dung sức khoẻ). Hiện mới có 2 lần cắt tay làm dữ liệu, chưa đủ để kiểm một quy tắc |
| E | Chỉ sửa prompt (vd "rồi đứng yên giữ tư thế đến hết video") để Gemini không thêm động tác | - (không thay A) | Chưa kiểm chứng Gemini có làm theo không; clip vẫn dài ~10 s. Có thể thử riêng, xem câu hỏi mở Q-3 |

### Có nên tự gợi ý điểm cắt?

**Không làm trong DR này.** Trang đặt sẵn điểm bắt đầu = 0 s, điểm kết thúc = 4,0 s (nằm giữa 2 lần cắt tay đã có: 3,4 s và 4,5 s), ghi rõ là "điểm đặt sẵn, kéo lại theo mắt". Mỗi lần lưu, máy ghi một dòng vào `cut_log.jsonl` (clip nào, file gốc, bắt đầu, kết thúc). Khi có khoảng 10 dòng trở lên, BA đánh giá trong một DR mới xem cách $0 chạy local (vd tìm "khoảng lặng chuyển động" giữa 2,5 và 6 s bằng độ lệch giữa các khung hình) có khớp với điểm người chọn không (sai lệch ≤ 0,3 s). Nếu làm thì chỉ để **điền sẵn** điểm cắt, người vẫn phải bấm Lưu (C-0009-4).

Điểm đặt sẵn 4,0 giây chỉ giữ được **cùng với** việc đoạn chọn luôn tự lặp (MKTG, xem M-3): người thấy ngay đoạn 0–4 s lặp lại, nếu động tác chưa trọn hoặc đã lẫn động tác thừa thì nhận ra mà không cần bấm gì. Kèm dòng nhắc "Đặt sẵn 4 giây, xem đoạn lặp: động tác phải trọn vẹn và không có động tác thừa." và nút "Xem cả clip".

### Góp ý dễ dùng của MKTG trước khi code (2026-11-12) và cách đưa vào DR

| # | Mức | Góp ý | Đưa vào DR |
|---|-----|-------|-----------|
| M-1 | Chặn | Mọi file tải về đều tên `gemini_generated_video_<mã>`, còn đích lại chọn sau cùng, xa chỗ xem → dễ lưu động tác bài A vào bước B | Nút lưu nằm cạnh đoạn lặp, kèm mô tả động tác của **bước đích**; nhãn nút ghi tên đích ("Lưu thành Bài 1 · Bước 2"); danh sách file đánh dấu "Đã dùng cho Bài 1 · Bước 1" (đọc từ `cut_log.jsonl`). D-20, D-21, V-8 |
| M-2 | Nên sửa | Đảo luồng theo việc thật: chọn bước thiếu trước → chép gợi ý → làm trong Gemini → quay lại, file mới nhất tự chọn → cắt → lưu → "Đã lưu … Còn thiếu N clip." + "Làm bước tiếp theo" | Luồng hệ thống mới; D-22, V-1, V-4 |
| M-3 | Nên sửa | Đoạn chọn luôn tự lặp khi đổi điểm cắt; chọn "Bình thường / Chậm như trong video"; lưu xong tự phát file đã lưu tại chỗ; bỏ nút "Xem thử lặp"/"Xem lại" | Luồng + V-3, V-4 |
| M-4 | Nên sửa | Đầu trang ghi tiến độ "Bát Đoạn Cẩm: đã có 2/34 clip"; nhóm clip thiếu theo bài, bài cần cho video tiếp theo lên đầu; "Đã có" gập lại | `clip_catalog` thêm `group_label`, `needed_for_next`; D-1, V-1 |
| M-5 | Nên sửa | Tách 2 thông báo: thư mục Tải về chưa có video / máy chưa cho phép đọc Tải về (ghi đường bấm cụ thể trong Cài đặt hệ thống) | `reason` trong API; D-16 tách thành D-16a/b/c; V-9 |
| M-6 | Nên sửa | Ghi đè: báo "Đã có clip, lưu sẽ thay" ngay khi chọn đích; hộp xác nhận bằng lời thường, nút "Thay clip" / "Để sau"; không hiện tên thư mục kỹ thuật | Thao tác người dùng; V-5 |
| M-7 | Nên sửa | Đổi chữ: Series → "Bài tập"; Clip đích → "Lưu thành"; ±1 khung → "◀ Lùi một chút" / "Tiến một chút ▶"; x1,6 → "Chậm như trong video"; Tải về / Tải lên → "File vừa tải từ Gemini" / "Chọn file khác trên máy". Nhãn chính là mô tả động tác, tên file chữ nhỏ màu xám | Bảng nhãn giao diện; DD-2, V-7 |
| M-8 | Nên sửa | Báo lỗi phải nói bước tiếp theo; nút Lưu bị mờ thì ghi lý do cạnh nút | Bảng thông báo; D-9, D-10, D-23 |
| M-9 | Gợi ý | Trạng thái "Đang đọc video…" / "Đang lưu clip…"; khi 409: "Đang xử lý clip trước, đợi một chút." | Bảng thông báo; D-14 |
| M-10 | Gợi ý | Viết lại mục 4b bước 2 trong hướng dẫn vận hành theo M-2 (lấy gợi ý bằng nút trên Studio, không mở file txt); thêm lỗi M-5 vào mục 6 | SSoT; DD-2, DD-3 |

---

## Thay đổi cấu trúc

### Dữ liệu

| Đối tượng | Trước | Sau | Lý do |
|-----------|-------|-----|-------|
| Danh mục clip của một series | Rải trong `scene_clip_files`, `intro_clip_files`, `write_prompts`, `write_intro_prompts` | Hàm mới `exercise.clip_catalog(series)` trả về danh sách: `name`, `group` (`ready` / `intro` / `move`), `move_n`, `step`, `label` (mô tả tiếng Việt, vd "Bài 1 · Bước 2: Hít vào, nâng hai tay…"), `prompt` (đúng câu prompt như trong `prompts_*.txt`), `exists`, `group_label` (vd "Video mở đầu", "Bài 1: Hai tay nâng trời"), `needed_for_next` (true nếu clip thuộc video mà `next_item()` sẽ làm tiếp). `write_prompts` / `write_intro_prompts` dùng lại hàm này | Một nguồn duy nhất cho tên clip, prompt và danh sách còn thiếu. Không đọc `prompts_*.txt` vì file này có thể cũ |
| `storage/clips/<series>/<tên>.mp4` | Chép tay | Ghi bởi công cụ: H.264, `yuv420p`, không tiếng, `+faststart`, **giữ nguyên** độ phân giải và fps gốc. Ghi ra file tạm `.<tên>.tmp.mp4` rồi `os.replace` | Giống hệt cách đã cắt tay, `exercise.render` không phải đổi gì. Thay file nguyên khối nên lệnh dựng đang chạy song song không đọc phải file dở |
| `storage/clips/<series>/goc/<stem>_<YYYYmmdd_HHMMSS>.mp4` | Không có | Bản sao file gốc Gemini (10 s, còn tiếng), mỗi lần lưu một bản | Giữ file gốc để cắt lại sau mà không phải tạo lại trong Gemini. File trong Tải về **không bị đụng tới** |
| `storage/clips/<series>/cu/<stem>_<YYYYmmdd_HHMMSS>.mp4` | Không có | Clip cũ bị thay được chuyển vào đây, không xoá | Lỡ thay nhầm vẫn lấy lại được |
| `storage/clips/<series>/cut_log.jsonl` | Không có | Mỗi lần lưu thêm 1 dòng: `name`, `source` (tên file gốc), `source_size`, `source_mtime`, `start`, `end`, `saved_at`, `replaced` (true/false) | Truy vết; đánh dấu file Tải về "Đã dùng cho …" (khớp tên + dung lượng + thời gian sửa, M-1); dữ liệu để đánh giá gợi ý tự động sau này |
| `storage/clip-work/<mã phiên>/` | Không có | `source.mp4` (bản sao file đang cắt), `f_000.jpg…` (khung hình), `info.json`. Phiên cũ hơn 24 giờ bị xoá khi mở phiên mới | Không làm việc trực tiếp trên file ở Tải về. Thư mục ngoài `storage/clips` và `storage/videos` nên không lẫn vào clip hay Drive |
| `.gitignore` | — | Thêm `storage/clip-work/` | Không commit video. `storage/clips/` đã có sẵn trong `.gitignore` |
| `.env` → `CLIP_DOWNLOADS_DIR` | Không có | Tuỳ chọn, mặc định `~/Downloads` | Máy dùng thư mục Tải về khác vẫn chạy được |

`exercise.py` chỉ tìm clip theo tên chính xác trong `storage/clips/<series>/` (không duyệt thư mục con), nên `goc/`, `cu/`, `cut_log.jsonl` không ảnh hưởng tới việc dựng.

### Luồng hệ thống

```
Trước:  Gemini app → Tải về → (tự xem, tự tìm giây, gõ ffmpeg, đổi tên, chép vào storage/clips/<series>/) → demo.py --exercise

Sau:    Studio, mục "Clip bài tập"
          0. Đầu trang: "Bát Đoạn Cẩm: đã có 2/34 clip". Ô "Bài tập" (mặc định: bài tập đầu tiên còn thiếu clip)
             Danh sách thiếu nhóm theo bài, nhóm cần cho video tiếp theo lên đầu
             ("Video mở đầu: thiếu 2 clip, cần cho video tiếp theo"); nhóm "Đã có" gập lại
          1. Máy tự chọn bước thiếu đầu tiên của nhóm đầu → hiện mô tả động tác + nút "Chép gợi ý tạo video"
                └─ prompt lấy từ clip_catalog (không đọc prompts_*.txt)
          2. (Ngoài Studio) app Gemini: dán gợi ý, tạo video, tải về
          3. Quay lại trang (trang tự tải lại danh sách khi được mở lại, có nút "Tải lại danh sách")
             Khối "File vừa tải từ Gemini": máy tự chọn file mới nhất CHƯA dùng; file đã dùng ghi "Đã dùng cho Bài 1 · Bước 1"
             Hoặc "Chọn file khác trên máy" (tải file lên)
                └─ "Đang đọc video…" → demo.py --clip-frames SRC --out storage/clip-work/<mã>
          4. Đoạn 0–4 s tự lặp ngay. Dải khung hình: bấm một khung để nhảy tới; "Đặt điểm bắt đầu" / "Đặt điểm kết thúc";
             "◀ Lùi một chút" / "Tiến một chút ▶" (1 khung); "Bình thường / Chậm như trong video"; "Xem cả clip"
             Mỗi lần đổi điểm cắt, đoạn mới tự lặp lại (không có nút "Xem thử lặp")
          5. Cạnh đoạn lặp: mô tả động tác của bước đích + nút "Lưu thành Bài 1 · Bước 2"
             (đích đã có clip → ghi sẵn "Đã có clip, lưu sẽ thay" → hộp xác nhận "Thay clip" / "Để sau")
                └─ "Đang lưu clip…" → demo.py --clip-cut SRC --series S --name N --start A --end B [--replace]
          6. Khung xem tự phát lặp clip vừa lưu. "Đã lưu Bài 1 · Bước 2. Còn thiếu 31 clip." + nút "Làm bước tiếp theo"
             (chọn bước thiếu kế tiếp và chép luôn gợi ý của bước đó, quay về bước 2)
          → demo.py --exercise (như cũ)
```

### Luồng dữ liệu

- `GET /api/studio/clips` → `demo.py --clip-list` (in JSON ra stdout): danh sách series, mỗi series có `clip_catalog`. Series chưa soạn bước (vd `tcq24`) trả về danh sách rỗng kèm lý do.
- `GET /api/studio/clips/downloads` (cần `X-Studio`) → `{files, reason}`. `files`: file `.mp4` ở cấp đầu của `CLIP_DOWNLOADS_DIR`, mới nhất trước, tối đa 20: tên, dung lượng, thời gian, `used_for` (nhãn bước đã dùng file này, lấy từ `cut_log.jsonl` của mọi series; rỗng nếu chưa dùng). `reason`: `ok` / `empty` (thư mục đọc được nhưng không có video) / `no_permission` (macOS chặn, `PermissionError`) / `not_found` (thư mục không tồn tại). Chỉ đọc.
- `POST /api/studio/clips/source?from_downloads=<tên>` hoặc body là bytes file → chép vào `storage/clip-work/<mã>/source.mp4` → chạy `--clip-frames` → trả `{token, duration, fps, width, height, frames: [{t, url}], video_url}`. File không có luồng hình → 400.
- `GET /api/studio/clips/work/{token}/source.mp4`, `/work/{token}/{f_NNN.jpg}` → phục vụ file của phiên.
- `POST /api/studio/clips/save` `{token, series, name, start, end, replace}` → chạy `--clip-cut` → trả catalog mới, số clip còn thiếu, bước thiếu kế tiếp, URL file đã lưu.
- `GET /api/studio/clips/file/{series}/{name}` → phát clip đã lưu (name phải có trong catalog).

### Thao tác người dùng (mục "Clip bài tập")

| Thao tác | Gọi | Tốn gì |
|----------|-----|--------|
| Mở mục "Clip bài tập" (bài tập và bước thiếu đầu tiên đã chọn sẵn) | `GET /clips` | $0 |
| "Chép gợi ý tạo video" | Chỉ trên trình duyệt | $0 (lượt tạo video của app Gemini: ngoài công cụ) |
| Quay lại trang: file mới nhất chưa dùng tự được chọn; hoặc chọn file khác trong danh sách / "Chọn file khác trên máy" | `GET /clips/downloads`, `POST /clips/source` | $0, vài giây |
| Bấm khung hình, "Đặt điểm bắt đầu/kết thúc", "Lùi/Tiến một chút", "Bình thường / Chậm như trong video", "Xem cả clip" | Chỉ trên trình duyệt; đoạn chọn tự lặp | $0 |
| "Lưu thành <bước>" (đích đã có: "Thay clip" / "Để sau") | `POST /clips/save` | $0, vài giây |
| "Làm bước tiếp theo" (chọn bước thiếu kế tiếp + chép gợi ý) | Chỉ trên trình duyệt | $0 |
| Đổi bước đích bằng tay (mở nhóm khác hoặc nhóm "Đã có") | Chỉ trên trình duyệt | $0 |

**Số lần bấm cho một clip (trong Studio, không tính thao tác trong app Gemini):**

| Tình huống | Bấm |
|------------|-----|
| Điểm đặt sẵn 0–4 s đã đúng | 2: "Chép gợi ý tạo video" (hoặc "Làm bước tiếp theo" từ clip trước) + "Lưu thành …" |
| Phải chỉnh điểm kết thúc | 4: thêm bấm khung hình + "Đặt điểm kết thúc" (mỗi lần "Lùi/Tiến một chút" thêm 1) |
| Phải chỉnh cả điểm bắt đầu | 6 |
| Thay clip đã có | thêm 1 ("Thay clip") |
| Clip đầu tiên trong phiên | thêm 1 (chuyển sang mục "Clip bài tập") |

Thiết kế cũ trong bản nháp DR này cần khoảng 8 lần bấm (chọn file, khung hình, đặt điểm kết thúc, Xem thử lặp, mở danh sách đích, chọn đích, Lưu, Xem lại).

### Nhãn và thông báo trên giao diện (M-7, M-8, M-9)

Nhãn chính của mỗi clip là mô tả động tác (vd "Bài 1 · Bước 2: Hít vào, nâng hai tay lên ngang ngực…"); tên file (`01_2.mp4`) chỉ hiện chữ nhỏ màu xám. Không hiện tên thư mục kỹ thuật (`goc`, `cu`, `storage/…`).

| Tình huống | Chữ hiển thị |
|------------|--------------|
| Ô chọn bài tập | "Bài tập" |
| Chọn đích | "Lưu thành" |
| Nguồn file | "File vừa tải từ Gemini" / "Chọn file khác trên máy" |
| Nhích 1 khung | "◀ Lùi một chút" / "Tiến một chút ▶" |
| Tốc độ lặp | "Bình thường" / "Chậm như trong video" |
| Dòng nhắc dưới đoạn lặp | "Đặt sẵn 4 giây, xem đoạn lặp: động tác phải trọn vẹn và không có động tác thừa." |
| Đích đã có clip | "Đã có clip, lưu sẽ thay" (hiện ngay khi chọn đích) |
| Hộp xác nhận thay | "Bài 1 · Bước 1 đã có clip. Thay bằng đoạn vừa cắt? Clip cũ vẫn được giữ lại trên máy." Nút "Thay clip" / "Để sau" |
| Sau khi lưu | "Đã lưu Bài 1 · Bước 2. Còn thiếu 31 clip." + "Làm bước tiếp theo" |
| Đang xử lý | "Đang đọc video…" / "Đang lưu clip…" |
| API trả 409 (thao tác khác đang chạy) | "Đang xử lý clip trước, đợi một chút." |
| `reason=empty` | "Thư mục Tải về chưa có video nào. Tải clip từ Gemini xong thì bấm Tải lại danh sách." |
| `reason=no_permission` | "Máy chưa cho phép Studio đọc thư mục Tải về. Mở Cài đặt hệ thống → Quyền riêng tư & Bảo mật → Tệp và thư mục → Terminal → bật Thư mục Tải về. Sau đó đóng cửa sổ Terminal của Studio và bấm đúp lại mo-studio.command. Hoặc bấm Chọn file khác trên máy." |
| `reason=not_found` | "Không tìm thấy thư mục Tải về. Bấm Chọn file khác trên máy." |
| Đoạn cắt < 1 s | "Đoạn cắt quá ngắn (dưới 1 giây). Bấm một khung hình xa hơn để đặt điểm kết thúc." |
| Điểm kết thúc ≤ điểm bắt đầu | "Điểm kết thúc phải nằm sau điểm bắt đầu. Bấm một khung hình phía sau rồi bấm Đặt điểm kết thúc." |
| File không phải video | "File này không phải video. Chọn đúng file gemini_generated_video… vừa tải." |
| Nút Lưu bị mờ (lý do ghi cạnh nút) | "Chưa chọn file video" / "Chưa chọn bước để lưu" / "Đoạn cắt quá ngắn" / "Đang lưu clip…" |

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 1 | `clip_catalog(series)`; `write_prompts` / `write_intro_prompts` dùng lại (nội dung file prompt không đổi); sửa dòng hướng dẫn số 4 trong file prompt: tải về rồi cắt và lưu bằng Studio, mục Clip bài tập | Dev | DR này | Code | `exercise.py` |
| 2 | `probe_clip`, `extract_frames` (5 fps, rộng 180 px), `cut_clip` (ghi tạm + `os.replace`, cất clip cũ vào `cu/`, chép gốc vào `goc/`, ghi `cut_log.jsonl`, cập nhật lại `prompts_*.txt` của nhóm đó nếu file đang tồn tại) | Dev | #1 | Code | `exercise.py` |
| 3 | Cờ `--clip-list [SERIES]`, `--clip-frames SRC --out DIR`, `--clip-cut SRC --series S --name N --start A --end B [--replace]`; exit code 5 = clip đích đã có mà không có `--replace`, exit 6 = đầu vào sai (tên không có trong catalog, thời điểm sai, không phải video) | Dev | #2 | Code | `demo.py` |
| 4 | API `/api/studio/clips…` (xem Luồng dữ liệu), khoá riêng cho thao tác clip (mỗi lúc một việc), dọn `clip-work` > 24 giờ | Dev | #3 | Code | `backend/app/api/studio.py` |
| 5 | Mục "Clip bài tập" trên Studio theo luồng mới (M-1…M-9): chuyển giữa "Video" và "Clip bài tập" (`/studio#clips`), tiến độ, nhóm theo bài, tự chọn bước thiếu và file mới nhất chưa dùng, chép gợi ý, đoạn chọn tự lặp, nút lưu ghi tên đích, xác nhận thay, "Làm bước tiếp theo", nhãn và thông báo đúng bảng trên | Dev + MKTG | #4 | HTML | `backend/app/web/studio.html` |
| 6 | `CLIP_DOWNLOADS_DIR` trong config; `.gitignore` thêm `storage/clip-work/` | Dev | #4 | Code | `backend/app/core/config.py`, `.gitignore` |
| 7 | Review: đường dẫn (Tải về, tên đích, token), ghi đè, khoá, hồi quy prompt và dựng bài tập, `app.html` không đổi | Reviewer | #1–6 | Ghi chú review | DR §Kết quả |
| 8 | Test theo bảng quyết định trên **bản sao** `storage/clips/bdc` và bản sao 2 file Gemini (đặt `CLIP_DOWNLOADS_DIR` trỏ tới thư mục tạm; không gọi TTS, không Drive) | Tester | #1–6 | Kết quả D/V | DR §Kết quả |
| 9 | Đánh giá dễ dùng trên bản đã code: chụp màn hình mục Clip bài tập (desktop), đi qua tình huống "clip có động tác thừa sau 4 giây" và "2 file Gemini tải liên tiếp", đối chiếu M-1…M-10, kiểm chữ không có thuật ngữ kỹ thuật | MKTG | #5 | Danh sách sửa | DR §Kết quả |
| 10 | Cập nhật tài liệu SSoT, ghi kết quả vào DR | BA | #1–9 | Docs | xem §SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | macOS hỏi quyền cho Terminal truy cập thư mục Tải về (service chạy từ Terminal qua `mo-studio.command`) | Danh sách Tải về trống hoặc lỗi | API trả `reason=no_permission` (khác `empty`); trang ghi đường bấm cụ thể trong Cài đặt hệ thống (bảng thông báo) và luôn có "Chọn file khác trên máy" |
| R-2 | Rủi ro | Trang web khác đọc danh sách file trong Tải về qua `localhost:8000` | Lộ tên file cá nhân | Endpoint `downloads`, `source`, `save` bắt buộc `X-Studio` + Host local (C-0001-3). CORS hiện cho phép origin GitHub Pages với `GET`, nên **không** để danh sách Tải về là GET không header |
| R-3 | Rủi ro | Tên đích hoặc tên file độc hại (`../`, `/etc/…`) | Ghi/đọc ngoài thư mục cho phép | Tên đích phải có trong `clip_catalog`; file Tải về chỉ nhận nếu có trong danh sách vừa liệt kê; token là chuỗi hex do server tạo; file khung hình theo regex `f_\d{3}\.jpg` |
| R-4 | Rủi ro | Trình duyệt tua không đúng khung hình (H.264 tua theo keyframe) | Khung người thấy khác khung cắt thật | Cắt bằng ffmpeg mã hoá lại (cắt chính xác tới khung). Sau khi lưu, trang phát lại file đã lưu để người xem đúng cái máy dùng. Chấp nhận sai lệch ±1 khung (1/24 s) |
| R-5 | Rủi ro | Thay nhầm clip đã có | Mất clip tốt | Báo "Đã có clip, lưu sẽ thay" ngay khi chọn đích + hộp xác nhận + clip cũ chuyển vào `cu/`, không xoá |
| R-8 | Rủi ro | Lưu động tác bài A vào bước B (mọi file tải về cùng kiểu tên, M-1) | Video dạy sai động tác | Chọn bước trước rồi mới tạo clip; nút lưu ghi tên bước và nằm cạnh mô tả động tác + đoạn lặp; file đã dùng được đánh dấu và không tự chọn lại |
| R-6 | Rủi ro | Đang chạy `demo.py --exercise` trong Terminal đúng lúc lưu clip | Lệnh dựng đọc file dở | Ghi file tạm rồi `os.replace` (thay nguyên khối) |
| R-7 | Rủi ro | Đoạn lặp trên trình duyệt chưa giống hệt khi dựng (tốc độ chậm thật phụ thuộc độ dài câu đọc, từ 1,0 đến 1,6) | Người thấy khác video thật một chút | Cho chọn 2 tốc độ: bình thường và chậm nhất (x1,6). Ghi chú trên trang. Kiểm lần cuối vẫn là xem video dựng thật |
| A-1 | Giả định | File Gemini là `.mp4` có luồng hình H.264 (quan sát 2 file ngày 2026-11-12) | Định dạng khác thì không đọc được | `--clip-frames` dùng ffmpeg đọc mọi định dạng ffmpeg hỗ trợ; không có luồng hình → báo lỗi tiếng Việt |
| A-2 | Giả định | Người vận hành làm trên máy Mac có file (Tải về) | Trên điện thoại không có file Gemini | Trang dùng được ở bề rộng máy tính; trên điện thoại chỉ cần không vỡ bố cục |
| A-3 | Giả định | Watermark ngôi sao của Gemini để nguyên | — | Không xoá hay che watermark trong DR này |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0009-1 | Công cụ không sửa, đổi tên hay xoá file trong thư mục Tải về; chỉ đọc và chép. Clip đã có trong `storage/clips` không bao giờ bị xoá: khi thay thì chuyển vào `cu/` | Giữ file gốc, lỡ tay vẫn lấy lại được | `exercise.py` (`cut_clip`), `api/studio.py` | — |
| C-0009-2 | Tên clip đích chỉ được lấy từ `exercise.clip_catalog()`. Hàm này là nguồn duy nhất cho tên clip, nội dung prompt và danh sách còn thiếu; không đọc danh sách thiếu từ `prompts_*.txt` | Tên sai thì `exercise.py` không tìm thấy clip; file prompt có thể cũ | `exercise.py`, `api/studio.py`, `studio.html` | — |
| C-0009-3 | Đọc thông tin, trích khung hình và cắt clip nằm trong `exercise.py`, gọi qua cờ của `demo.py`. `api/studio.py` không gọi ffmpeg trực tiếp (mở rộng C-0001-2) | Một nguồn logic; CLI và web cho cùng kết quả | `api/studio.py` | Khi chuyển sang backend đầy đủ (sau M1–M3) |
| C-0009-4 | Điểm cắt do người chọn và chỉ lưu khi người bấm Lưu. Gợi ý tự động (nếu làm sau này) chỉ được điền sẵn, không tự lưu | Nội dung sức khoẻ: cắt sai là dạy sai động tác | Mục Clip bài tập | — |
| C-0009-5 | Clip lưu ra: H.264, `yuv420p`, không tiếng, `+faststart`, giữ nguyên độ phân giải và fps gốc (không scale) | `exercise.render` tự scale/lặp/làm chậm; giữ giống clip đã cắt tay để không đổi kết quả dựng | `cut_clip` | — |
| C-0009-6 | Nút lưu luôn ghi tên bước đích và nằm cạnh đoạn lặp cùng mô tả động tác của bước đó; máy không tự chọn file đã dùng cho bước khác | Chống lưu nhầm động tác (M-1, chặn) | `studio.html` | — |

C-0001-2, C-0001-3, C-0001-4 tiếp tục áp dụng (API clip ghi cần `X-Studio` + Host local; không đổi `app.html`).

supersedes: —

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `docs/specs/architecture/capabilities/video-render.md` | Mục mới "Clip bài tập trên Studio — DR-0009": luồng, cờ CLI, API, dữ liệu (`goc/`, `cu/`, `cut_log.jsonl`, `clip-work`) | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Mục 4b bước 2 viết lại theo luồng mới (M-10): mở Studio → Clip bài tập → "Chép gợi ý tạo video" (không mở file txt) → tạo trong Gemini, tải về → quay lại, kiểm file tự chọn → xem đoạn lặp, chỉnh điểm cắt → "Lưu thành …" → "Làm bước tiếp theo". Bỏ câu "Video bài tập … làm bằng công cụ khác" nếu không còn đúng. Mục 6 thêm 3 dòng lỗi: Tải về chưa có video, máy chưa cho phép đọc Tải về (đường bấm cụ thể), file không phải video | [ ] |
| `.claude/CLAUDE.md` | Lệnh thường dùng: `--clip-list`, `--clip-frames`, `--clip-cut`; ghi chú thư mục `storage/clips/<series>/goc|cu`, `storage/clip-work/` | [ ] |
| `TODO.md` | M2c: thêm việc "Cắt clip trên Studio (DR-0009)"; §5 ghi quyết định không tự gợi ý điểm cắt, chờ đủ dữ liệu `cut_log.jsonl` | [ ] |
| `.env.example` | `CLIP_DOWNLOADS_DIR` (tuỳ chọn, mặc định `~/Downloads`) | [ ] |

## File code thay đổi

- [ ] `exercise.py`: `clip_catalog`, `probe_clip`, `extract_frames`, `cut_clip`; `write_prompts` / `write_intro_prompts` dùng `clip_catalog`; câu hướng dẫn số 4 trong file prompt
- [ ] `demo.py`: cờ `--clip-list`, `--clip-frames`, `--clip-cut`, `--replace`, `--series`, `--name`, `--start`, `--end`, `--out` (Dev có thể gộp tên cờ nếu gọn hơn, nhưng phải ghi vào §Kết quả)
- [ ] `backend/app/api/studio.py`: các endpoint `/clips…`
- [ ] `backend/app/web/studio.html`: mục Clip bài tập
- [ ] `backend/app/core/config.py`: `CLIP_DOWNLOADS_DIR`
- [ ] `.gitignore`: `storage/clip-work/`
- Không đổi: `app.html`, `api/creator.py`, `exercise.render`, `scene_clip_files`, `intro_clip_files`, `summary_clip_files`, `creator_main.py` (CORS giữ nguyên)

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: code

Dữ liệu test: bản sao `storage/clips/bdc` (có `00.mp4`, `01_1.mp4`, `prompts_01.txt`, `prompts_intro.txt`) và bản sao 2 file `gemini_generated_video_*.mp4` trong một thư mục tạm làm `CLIP_DOWNLOADS_DIR`.

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1 | `demo.py --clip-list bdc` khi có `00.mp4`, `01_1.mp4` | JSON có `00.mp4`, `intro_1.mp4`, `intro_2.mp4`, `01_1.mp4`…`08_3.mp4` (34 mục: 1 + 2 + 4×7 + 3, đúng theo số bước trong giáo trình); `exists=true` đúng cho `00.mp4`, `01_1.mp4`; các mục khác `false`; mỗi mục có `label` tiếng Việt, `group_label` và `prompt`; khi `intro_video.done=false`, chỉ các mục nhóm "Video mở đầu" (`00.mp4`, `intro_1.mp4`, `intro_2.mp4`) có `needed_for_next=true` | Chạy lệnh, đếm và so với giáo trình + `next_item()` |
| D-2 | Series chưa soạn bước (`tcq24`) | Danh sách rỗng + lý do "chưa soạn giáo trình"; không lỗi | `--clip-list tcq24` |
| D-3 | Hồi quy: `write_prompts` / `write_intro_prompts` sau khi dùng `clip_catalog` | Nội dung `prompts_01.txt`, `prompts_intro.txt` giống hệt bản cũ, chỉ khác dòng hướng dẫn số 4 (đã chủ ý đổi) | Sinh file bằng code cũ và mới trên cùng bản sao thư mục, `diff` |
| D-4 | `--clip-frames` trên file Gemini 10,03 s | `info.json`: thời lượng ≈ 10,03 s, 24 fps, 720×1280; khoảng 50 ảnh `f_000.jpg…` (5 fps), mỗi ảnh rộng 180 px | Chạy lệnh, đếm file, mở 1 ảnh |
| D-5 | `--clip-cut` file Gemini, `--name 01_2.mp4 --start 0 --end 4.5`, đích chưa có | `01_2.mp4` dài 4,50 s ± 1/24 s, h264, yuv420p, 720×1280, 24 fps, **không** có luồng tiếng; bản gốc nằm trong `goc/01_2_<giờ>.mp4`; `cut_log.jsonl` thêm 1 dòng đúng `start`/`end`; file trong thư mục Tải về giữ nguyên (cùng dung lượng và thời gian sửa) | Chạy lệnh, `ffmpeg -i` đọc thông tin, so mtime file gốc |
| D-6 | Cắt từ giữa: `--start 1.0 --end 3.0` | File dài 2,00 s ± 1/24 s; khung đầu của file = khung tại 1,0 s của bản gốc (sai ≤ 1 khung) | So ảnh khung đầu file cắt với khung trích tại 1,0 s bản gốc |
| D-7 | Đích đã có (`01_1.mp4`), không `--replace` | Exit 5, không file nào thay đổi | Chạy lệnh, so mtime |
| D-8 | Đích đã có, có `--replace` | `01_1.mp4` mới; bản cũ nằm trong `cu/01_1_<giờ>.mp4` cùng dung lượng với bản cũ; `cut_log` có `replaced=true` | Chạy lệnh, so dung lượng |
| D-9 | Đầu vào sai: `--end` ≤ `--start`; `--end` > thời lượng; `--start` < 0; tên không có trong catalog (`../x.mp4`, `99_1.mp4`); file không phải video (ảnh, file text) | Exit 6, thông báo tiếng Việt nói bước tiếp theo (đúng bảng thông báo), không tạo file nào trong `storage/clips` | Chạy từng trường hợp |
| D-10 | Biên: đoạn cắt < 1,0 s | Từ chối (exit 6) "Đoạn cắt quá ngắn (dưới 1 giây). Bấm một khung hình xa hơn để đặt điểm kết thúc." | Chạy lệnh |
| D-11 | Lưu clip của nhóm đang có `prompts_01.txt` | `prompts_01.txt` không còn liệt kê clip vừa lưu (và cả clip đã có từ trước như `00.mp4`, `01_1.mp4`) | Mở file sau khi lưu |
| D-12 | API: `GET /clips/downloads`, `POST /clips/source`, `POST /clips/save` không có `X-Studio` hoặc Host lạ | 403 | TestClient |
| D-13 | API: `from_downloads` là tên không có trong danh sách (`../.ssh/x`, tên lạ); token lạ (`../`, không phải hex); `save` với `name` ngoài catalog | 404 / 400, không đọc hay ghi file ngoài thư mục cho phép | TestClient |
| D-14 | API: đang có một thao tác clip chạy, gửi thao tác thứ hai | 409, `detail` = "Đang xử lý clip trước, đợi một chút." | TestClient (giữ khoá) |
| D-15 | API: `save` đích đã có, `replace=false` | 409 kèm thông báo "Đã có clip này" để trang hỏi xác nhận; `replace=true` thì lưu | TestClient |
| D-16a | `CLIP_DOWNLOADS_DIR` đọc được nhưng không có `.mp4` | `files=[]`, `reason=empty` | TestClient với thư mục tạm rỗng |
| D-16b | `CLIP_DOWNLOADS_DIR` không đọc được (`PermissionError`, giống macOS chặn) | `files=[]`, `reason=no_permission` (**không** được trả `empty`); `POST /clips/source` bằng tải file lên vẫn chạy | TestClient với thư mục `chmod 000` (hoặc giả lập `PermissionError`) |
| D-16c | `CLIP_DOWNLOADS_DIR` không tồn tại | `files=[]`, `reason=not_found` | TestClient với đường dẫn sai |
| D-17 | Phiên `clip-work` cũ hơn 24 giờ | Bị xoá khi mở phiên mới; phiên mới không bị xoá | Đổi mtime thư mục giả, gọi `source` |
| D-18 | Hồi quy dựng bài tập: `demo.py --exercise-rerender <bản sao thư mục bài tập>` dùng clip vừa cắt | Dựng được, log "Scene … local:01_2.mp4"; không lỗi ffmpeg | Chạy trên bản sao, không gọi TTS (rerender dùng giọng có sẵn) |
| D-20 | Sau khi lưu `01_2.mp4` từ file A, gọi `GET /clips/downloads` | File A có `used_for` = nhãn "Bài 1 · Bước 2"; file B chưa dùng có `used_for` rỗng. Đổi tên file A thành file khác cùng tên nhưng khác dung lượng thì không bị coi là đã dùng | TestClient |
| D-21 | Trang: có 2 file trong Tải về, file mới nhất đã dùng | Trang tự chọn file mới nhất **chưa** dùng; không có file nào chưa dùng thì không tự chọn, ghi "Chưa có file mới từ Gemini" | Tester mở trang, đổi mtime file thử |
| D-22 | `save` thành công | Phản hồi có số clip còn thiếu (giảm 1 so với trước) và bước thiếu kế tiếp theo thứ tự nhóm (cần cho video tiếp theo trước) | TestClient |
| D-23 | Trang: nút Lưu khi chưa chọn file / chưa chọn bước / đoạn < 1 s / đang lưu | Nút mờ, lý do ghi cạnh nút đúng bảng thông báo | Tester thao tác từng trường hợp |
| D-19 | Hồi quy Studio + creator: `/api/studio/videos`, các API video DR-0001, `/api/creator/videos`, `app.html` | Hành vi như cũ; `app.html` không có diff | TestClient + `git diff --stat` |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | `video-render.md` | Thêm | Có mục DR-0009, tên cờ/API/thư mục khớp code | Đối chiếu với `demo.py --help` và `studio.py` |
| DD-2 | Hướng dẫn vận hành mục 4b | Sửa | Không còn bước "đổi tên file, chép vào thư mục" hay lệnh ffmpeg; nhãn nút khớp `studio.html` | So chữ trong hướng dẫn với nhãn trên trang |
| DD-3 | Hướng dẫn vận hành mục 6 | Thêm | Có dòng lỗi quyền thư mục Tải về và file không phải video | Xem diff |
| DD-4 | `.claude/CLAUDE.md`, `TODO.md`, `.env.example` | Đồng bộ | Khớp tên cờ và biến môi trường trong code | Đối chiếu chéo |

### Kiểm tra E2E

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| V-1 | Mở mục Clip bài tập | Bấm đúp `mo-studio.command`, chuyển sang "Clip bài tập" | Đầu trang "Bát Đoạn Cẩm: đã có 2/34 clip"; nhóm "Video mở đầu: thiếu 2 clip, cần cho video tiếp theo" ở trên cùng; bước "Video mở đầu" đầu tiên còn thiếu đã được chọn sẵn, có nút "Chép gợi ý tạo video"; nhóm "Đã có" đang gập | — | — |
| V-2 | Lấy file Gemini | Bấm "Chép gợi ý tạo video", dán ra trình soạn thảo để xem; chép 1 file Gemini thử vào thư mục Tải về thử, quay lại trang | Gợi ý giống phần prompt của bước đó; file mới tự được chọn, "Đang đọc video…" rồi hiện video + dải khung hình; bấm 1 khung hình thì video nhảy tới đó | — | — |
| V-3 | Đoạn lặp | Không bấm gì; sau đó đổi điểm kết thúc sang 4,5 s; bật "Chậm như trong video"; bấm "Xem cả clip" | Ngay khi mở, đoạn 0–4 s tự lặp; đổi điểm cắt thì đoạn mới tự lặp; chậm thì phát chậm hơn; "Xem cả clip" phát cả 10 s | — | — |
| V-4 | Lưu clip mới | Chọn bước "Bài 1 · Bước 2", bấm "Lưu thành Bài 1 · Bước 2", rồi "Làm bước tiếp theo" | Nút ghi đúng tên bước; "Đang lưu clip…" → "Đã lưu Bài 1 · Bước 2. Còn thiếu N clip."; clip vừa lưu tự phát lặp tại chỗ; "Làm bước tiếp theo" chọn bước thiếu kế tiếp và chép gợi ý | — | — |
| V-5 | Thay clip đã có | Mở nhóm "Đã có", chọn "Bài 1 · Bước 1" | Ngay khi chọn hiện "Đã có clip, lưu sẽ thay"; bấm lưu → hộp "Bài 1 · Bước 1 đã có clip. Thay bằng đoạn vừa cắt? Clip cũ vẫn được giữ lại trên máy."; "Để sau" thì không đổi gì; "Thay clip" thì thay | — | — |
| V-6 | Clip cắt dùng được khi dựng | Chạy `demo.py --exercise-rerender` trên bản sao một thư mục bài tập | Video dựng xong, cảnh dùng clip mới, không có động tác thừa | — | — |
| V-7 | MKTG | Chụp màn hình mục Clip bài tập (desktop; bề rộng điện thoại không vỡ bố cục) | Không có chữ kỹ thuật (ffmpeg, token, JSON, mtime, tên thư mục); nhãn đúng bảng nhãn; nhãn chính là mô tả động tác, tên file chữ nhỏ màu xám | — | — |
| V-8 | Chống lưu nhầm (M-1) | Tải 2 file Gemini liên tiếp; lưu file 1 cho Bài 1 · Bước 2; quay lại danh sách | File 1 ghi "Đã dùng cho Bài 1 · Bước 2"; máy tự chọn file 2; nút lưu luôn đứng cạnh mô tả động tác của bước đích | — | — |
| V-9 | Thông báo thư mục Tải về | (a) Trỏ `CLIP_DOWNLOADS_DIR` tới thư mục rỗng; (b) thư mục bị chặn quyền | (a) và (b) ra 2 thông báo khác nhau đúng bảng thông báo; "Chọn file khác trên máy" vẫn dùng được | — | — |

### Cổng chất lượng

- [ ] Đã kiểm hết bảng quyết định
- [ ] Không có hồi quy (D-3, D-18, D-19)
- [ ] Không vi phạm C-0001-1…4 và C-0009-1…6
- [ ] Xong mọi việc trong kế hoạch
- [ ] Đã cập nhật tài liệu SSoT

---

## Kết quả

> BA điền sau khi Dev / Reviewer / Tester / MKTG xong.

### Triển khai

| # | Việc | Kết quả | Ghi chú |
|---|------|---------|---------|
| — | — | — | — |

### Review

| # | Góp ý | Xử lý |
|---|-------|-------|
| — | — | — |

### Test

(Chép nguyên văn từ báo cáo Tester.)

---

## Câu hỏi mở cho người dùng

| # | Câu hỏi | Mặc định nếu không trả lời |
|---|---------|----------------------------|
| Q-1 | Điểm kết thúc đặt sẵn 4,0 giây, kèm đoạn tự lặp, dòng nhắc và nút "Xem cả clip" (MKTG đồng ý với điều kiện có tự lặp). Đồng ý không? | 4,0 giây |
| Q-2 | Khi đủ khoảng 10 lần cắt, có muốn làm thêm gợi ý điểm cắt tự động (chỉ điền sẵn, vẫn phải bấm Lưu) không? | Không làm cho tới khi người dùng đồng ý, theo DR mới |
| Q-3 | Có muốn thử riêng việc thêm câu "rồi đứng yên giữ tư thế đến hết video" vào prompt trên 2–3 bước để xem Gemini còn thêm động tác thừa không? MKTG thấy đáng thử. Nếu đổi thì đổi ở nguồn mà nút "Chép gợi ý tạo video" đọc (`exercise.py` qua `clip_catalog` + `steps_en` trong giáo trình), không sửa tay file txt | Không đổi prompt trong DR này |
| Q-4 | "Làm bước tiếp theo" vừa chọn bước kế tiếp vừa **chép luôn** gợi ý của bước đó (bớt 1 lần bấm). Có muốn tách thành 2 nút không? | Gộp (1 nút) |

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR trước | `DR-0001-video-review-studio.md` (Studio, C-0001-1…4) |
| Code hiện có | `exercise.py` (`scene_clip_files`, `intro_clip_files`, `summary_clip_files`, `write_prompts`, `write_intro_prompts`, `render`, `MAX_SLOWDOWN`), `backend/app/api/studio.py`, `backend/app/web/studio.html`, `scripts/review_frames.py` (cách gọi ffmpeg qua `imageio_ffmpeg`, đọc thông tin bằng `ffmpeg -i`) |
| Dữ liệu quan sát | `storage/clips/bdc/01_1.mp4` (0–4,5 s), `storage/clips/bdc/00.mp4` (0–3,4 s), 2 file `~/Downloads/gemini_generated_video_*.mp4` ngày 2026-11-12 |
