---
description: Kiểm âm thanh của một video bằng máy (khung hình, tiếng nổ ở chỗ chuyển cảnh, chép lời bằng Groq Whisper để bắt đọc bịa/đọc thiếu). Kết quả chỉ là tín hiệu, câu bị gắn cờ chuyển thành "Cần người kiểm"
argument-hint: <storage/videos/<thư mục>> [--scenes 1,2]
---

Mã nạp: audio-check/1

Skill này là **sổ tay dùng chung của `tester`, `marketing`, `dev`**. Agent không nghe được âm thanh, nên skill này lấy **bằng chứng máy** cho phần nghe. Kết quả chỉ là **tín hiệu** (C-0004-3): không đánh PASS hay "Đạt" phần nghe chỉ dựa vào máy. Câu bị gắn cờ → "Cần người kiểm" kèm câu trích.

Đầu vào: $ARGUMENTS

```bash
PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
D=<thư mục video>      # nên là bản sao (skill sandbox-render --keep); script chỉ đọc thư mục này
```

Kết quả ghi vào `storage/review-frames/<thư mục>/` cho video thật, `storage/review-frames/<thư mục>__sandbox/` cho bản sao (trừ Bước 1, xem lưu ý dưới). Cả hai đều gitignored, không lên Drive. Thư mục video không bị ghi gì (C-0004-5).

- Thư mục **không** nằm trong `<repo>/storage/videos/` (vd bản sao trong thư mục tạm của `sandbox-render --keep`): `audio_seams.py` và `transcript_check.py` mặc định ghi vào `storage/review-frames/<thư mục>__sandbox/`, và JSON có `"sandbox": true`, `"source": "copy"`. Nhờ vậy kết quả của bản sao không ghi đè, không bị đọc nhầm là kết quả của video thật (video thật: `"sandbox": false`, `"source": "storage/videos"`).
- `--out-dir` nằm trong thư mục video hoặc trong bất kỳ `storage/videos/` nào thì bị từ chối (exit 1). Muốn ghi chỗ khác thì chọn thư mục ngoài `storage/videos/` (vd trong thư mục tạm).
- Lưu ý: `review_frames.py` (Bước 1) chưa tách như vậy, vẫn ghi vào `storage/review-frames/<thư mục>/` kể cả với bản sao, nên khung hình của bản sao ghi đè khung hình của video thật cùng tên (đã ghi `TODO.md`). Khung hình và `facts.json` đọc ở `<thư mục>/`, `seams.json` và `transcript.json` của bản sao đọc ở `<thư mục>__sandbox/`.

## Bước 1. Khung hình

```bash
$PY scripts/review_frames.py "$D"
```

Tạo `scene_N_start.jpg`, `scene_N_mid.jpg`, `facts.json`. Xem mọi khung bằng Read.

## Bước 2. Tiếng nổ ở chỗ nối ($0, chạy tại máy)

```bash
$PY scripts/audio_seams.py "$D"                 # đo audio trong video.mp4 ở từng mốc chuyển cảnh
$PY scripts/audio_seams.py "$D" --audio-files   # đo từng audio_N.mp3 riêng (Dev, sau khi sửa phần cắt)
```

- Mốc nối lấy từ `script.json` (mỗi cảnh `duration + GAP`, cảnh cuối thêm `END_HOLD`). Ngưỡng giống `_trim_gemini_edges`: im lặng ≤ −35 dB, tiếng nổ > −30 dB, sau đó phải có cửa sổ < −45 dB.
- Ghi `seams.json`, in bảng: cảnh, thời điểm, dB lớn nhất ở đuôi, `OK` hoặc `Nghi tiếng nổ`.

## Bước 3. Chép lời bằng Whisper (Groq, miễn phí, tốn lượt Groq)

```bash
$PY scripts/transcript_check.py "$D"                  # mọi cảnh: 1 lượt Groq / audio_N.mp3
$PY scripts/transcript_check.py "$D" --scenes 1,2     # chỉ các cảnh chọn (số cảnh tính từ 1)
# cờ thêm: --model <model Whisper> (mặc định whisper-large-v3), --extra-words <n> (mặc định 4)
```

- Khoá `GROQ_API_KEY` đọc từ `.env` của repo gốc. Không in khoá ra log, không chép khoá vào báo cáo.
- So bản chép với `audio_line` (thiếu thì `line`), sau khi bỏ dấu, chữ thường, bỏ dấu câu. Nên lỗi dấu của Whisper ("đọng" → "động") không bị coi là khác.
- Cờ **Nghi đọc bịa**: có chuỗi ≥ `--extra-words` từ liên tiếp không có trong lời, hoặc có con số (chữ số, "trăm/ngàn/nghìn/triệu/k") mà lời không có. Cờ **Nghi đọc thiếu**: một chuỗi ≥ 4 từ của lời không có trong bản chép.
- Ghi `transcript.json` (bản chép, đoạn thừa, đoạn thiếu từng cảnh) và in bảng tóm tắt.
- "%" được đọc là "phần trăm": lời "giảm 50%" và bản chép "giảm năm mươi phần trăm" không bị gắn cờ.
- HTTP 429 hoặc 5xx: script tự thử lại **1 lần** sau thời gian `retry-after` (mặc định 2 giây; server đòi chờ quá 20 giây thì không thử lại). Lần thử lại cũng tính là 1 lượt Groq.
- Lỗi mạng, thiếu khoá, HTTP 429/5xx sau lần thử lại → exit ≠ 0, `transcript.json` cũ bị xoá. Khi đó ghi "Chưa chép lời được: <lý do>", **không** coi là đạt.
- **Video du lịch** (có `topic.json`, lời tiếng Anh): script từ chối (exit ≠ 0, 0 lượt Groq) vì ngôn ngữ chép lời đang cố định tiếng Việt. Bỏ Bước 3, ghi phần chép lời là "Cần người kiểm".
- Đếm số lượt Groq đã gọi (`groq_calls` trong `transcript.json`, gồm cả lần thử lại) để báo lại.

## Dùng theo vai trò

| Vai trò | Dùng thế nào |
|---------|--------------|
| `tester` | Chạy trên bản sao (`sandbox-render --keep`). Gắn bảng của Bước 2, 3 vào cột bằng chứng. Ca có cờ → **Cần người kiểm**, không PASS phần nghe |
| `marketing` | Chạy cả 3 bước. Chỉ được gọi Groq qua `transcript_check.py`, không gọi Gemini, không chạy `demo.py`. Hạng mục C ("Không bịa") xét cả **lời thực đọc** trong `transcript.json`. Đoạn bị gắn cờ đưa vào mục "Cần người kiểm" của `marketing-review.md` kèm câu trích và cảnh. Báo số lượt Groq đã dùng |
| `dev` | Sau mỗi thay đổi ở phần cắt, ghép, fade audio: chạy Bước 2 (thêm `--audio-files` nếu sửa phần cắt từng clip). Sửa prompt TTS: chạy Bước 3 trên audio **đã có**, không tạo audio mới bằng Gemini |

## Mẫu ghi "Cần người kiểm"

```markdown
- Cảnh 2 (0:04–0:09): Whisper chép thêm "… bán có 120 ngàn một túi", không có trong lời. Nghe lại câu này.
- Chỗ nối sau cảnh 3 (0:14.2): Nghi tiếng nổ, −8 dB ở đuôi. Nghe lại chỗ chuyển cảnh.
- Không có cờ ở các cảnh còn lại (máy chỉ là tín hiệu, vẫn nên nghe lướt toàn bộ).
```
