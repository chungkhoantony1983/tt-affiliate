---
description: Dựng lại một thư mục video có sẵn trên bản sao trong thư mục tạm, chắc chắn không gọi TTS Gemini, không duyệt, không Drive/Sheet, không ghi giáo trình bài tập, không đụng storage/ thật
argument-hint: <storage/videos/<thư mục>> [--revoice-all-edge] [--keep]
---

Mã nạp: sandbox-render/1

Skill này là **sổ tay dùng chung của `dev`, `tester` và người điều phối** (chuẩn bị bản sao cho `marketing`, vì marketing không chạy `demo.py`). Dùng mỗi khi cần dựng lại một video **đã có** mà không làm hỏng dữ liệu thật và không tốn lượt Gemini (C-0004-2).

Đầu vào: $ARGUMENTS

## Lệnh

```bash
PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
$PY scripts/sandbox_render.py <repo gốc>/storage/videos/<thư mục> [--revoice-all-edge] [--keep]
```

- Chạy từ repo gốc hoặc worktree đều được. Code được dùng là code của nơi chứa `scripts/sandbox_render.py` (worktree thì là code đang sửa).
- Gọi bằng công cụ Bash với `timeout: 600000` (10 phút), hoặc `run_in_background: true` rồi chờ thông báo xong. Mặc định 2 phút của Bash thường không đủ. Script tự dừng `demo.py` (kể cả các tiến trình ffmpeg con) sau 540 giây, trước giới hạn 600 giây của Bash, để kịp dọn thư mục tạm.
- Bấm Ctrl-C hoặc tiến trình bị dừng (SIGINT/SIGTERM): script dừng cả nhóm tiến trình `demo.py` và vẫn xoá thư mục tạm (trừ khi có `--keep`).
- `--keep`: giữ thư mục tạm để xem tiếp (tester, người điều phối giao cho marketing). Không có thì script tự xoá khi xong.
- `--revoice-all-edge`: đọc lại **cả video** bằng edge-tts (thêm `--revoice-all edge` khi gọi `demo.py`). Chỉ dùng khi bản sao có câu đã sửa, hoặc khi ca test cần audio mới.

## Script làm gì

1. Tạo thư mục tạm `T`, chép thư mục video sang `T/storage/videos/<tên>`. Ảnh trong `product.json` là đường dẫn tương đối nằm ngoài thư mục video thì chép theo cùng đường dẫn sang `T`.
2. Chạy với thư mục làm việc là `T`: không có `.env`, không có `google-credentials.json`, và đặt rõ `GEMINI_API_KEY= GROQ_API_KEY= PIXABAY_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= TTS_PROVIDER=edge APPROVAL_MODE=web IMAGE_PROVIDER=manual` (không gọi Gemini, Groq, Pixabay hay API tạo ảnh).
3. **Video sản phẩm** (có `product.json`): có câu `line != audio_line` mà không có `--revoice-all-edge` thì **dừng trước** (exit ≠ 0), liệt kê số cảnh. Lý do: `revoice_changed()` đọc lại theo `script.json → tts_provider`, không theo `TTS_PROVIDER` (xem `voice-rules`). Không có gì cần đọc lại thì chạy `demo.py --render-only <bản sao>` bằng subprocess.
4. **Video bài tập** (không có `product.json`, `script.json` có `series_id`): chép `content/exercise_curriculum.json` và `storage/clips/<series_id>/` sang `T`, chặn `approval_step` (trả `False`), `exercise.mark_done` và `move_to_drive` (ném lỗi), rồi gọi `exercise.rerender`. Kết quả mong đợi `status=rejected`: dựng xong nhưng không tới bước đánh dấu giáo trình hay Drive.
5. **Video du lịch** (có `topic.json`, không có `product.json`): **chưa hỗ trợ** trong sandbox-render (xem `TODO.md`). Script dừng trước khi chép (exit 2) và báo rõ lý do. Cách thay thế: xem mục "Video du lịch" bên dưới.
6. In JSON: `sandbox_dir`, `status`, đường dẫn `video.mp4` trong bản sao, thời lượng, danh sách `audio_N.mp3` đã đổi, `post_txt_existed` (bản sao đã có sẵn `post.txt` chép từ bản gốc), `post_txt_created` (lần dựng này có tạo hoặc ghi lại `post.txt` không), `original_unchanged` (so hash mọi file của thư mục gốc trước và sau).

## Đọc kết quả

| Thấy gì | Nghĩa là |
|---------|----------|
| `original_unchanged: false` | **Lỗi nghiêm trọng**: bản gốc bị đổi. Dừng, báo người điều phối ngay |
| Exit 2 kèm danh sách cảnh | Bản sao có câu đã sửa. Chạy lại với `--revoice-all-edge` nếu ca test cho phép đổi giọng |
| Exit 2, lỗi "travel folder (topic.json) is not supported" | Video du lịch, chưa hỗ trợ. Dùng cách thay thế ở mục "Video du lịch" |
| `status=review` (sản phẩm) / `status=rejected` (bài tập), exit 0 | Bình thường |
| `post_txt_created: true` (exit 1) | **Sai**: lần dựng đã tới bước duyệt. Báo người điều phối |
| `post_txt_existed: true`, `post_txt_created: false` | Bình thường: `post.txt` chép sẵn từ bản gốc (video bài tập đã duyệt), lần dựng không ghi lại. Với video sản phẩm, `demo.py --render-only` xoá `post.txt` cũ của bản sao (cần duyệt lại), cũng không tính là lỗi |
| `status=timeout`, `timed_out: true` (exit 1) | `demo.py` chạy quá 540 giây (edge-tts hoặc ffmpeg bị treo), đã bị dừng cả nhóm tiến trình. Chạy lại một lần; lặp lại thì báo kèm `render.log` (dùng `--keep`) |

Sau khi dựng: xem khung hình bằng `$PY scripts/review_frames.py <video trong bản sao>`, đo âm thanh bằng skill `audio-check`.

## Lưu ý

- Thư mục cũ thiếu `tts_provider` thì `clean_gemini_audio` coi là `gemini` và có thể cắt lại audio trong bản sao (chỉ chạy ffmpeg tại máy, không gọi mạng). Vì vậy audio của bản sao có thể khác bản gốc.
- Ảnh là URL thì vẫn tải từ mạng ($0).
- Skill này **chỉ** thay phần dựng lại thư mục có sẵn. Test API Studio bằng TestClient, bật giao diện, hay tạo video mới bằng `--product` thì vẫn dùng khối biến môi trường trong `dev-selfcheck` / `tester.md`.
- Không bao giờ trỏ `--output-dir` hay chạy `demo.py` trực tiếp trên `storage/videos/` thật.

## Video du lịch (chưa hỗ trợ)

Thư mục có `topic.json` bị từ chối (exit 2): sandbox-render chưa hỗ trợ travel, việc này đang ghi ở `TODO.md`. Cách thay thế, theo khối biến môi trường trong `dev-selfcheck` (§ Chuẩn bị):

```bash
WT=<worktree đang test, hoặc repo gốc>; PY=<repo gốc>/.venv/bin/python
T=$(mktemp -d); mkdir -p "$T/storage/videos"
cp -R <repo gốc>/storage/videos/<thư mục travel> "$T/storage/videos/"
export TTS_PROVIDER=edge GEMINI_API_KEY= GROQ_API_KEY= PIXABAY_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= APPROVAL_MODE=web IMAGE_PROVIDER=manual
cd "$T" && $PY $WT/demo.py --render-only "$T/storage/videos/<thư mục travel>"
```

- Travel chỉ dùng edge-tts nên không tốn Gemini. Không chạy `--approve` (tải Drive) hay `--refresh-facts` (gọi mạng) trên bản sao nếu ca test không cần.
- Tự so hash thư mục gốc trước và sau, tự dọn `$T`: không có `original_unchanged` hay tự xoá như script.
- Chép lời (`transcript_check.py`) cũng không nhận thư mục travel (lời tiếng Anh), xem `audio-check`.
- Dọn thư mục tạm khi xong nếu đã dùng `--keep`.
