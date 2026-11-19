---
description: Cách Dev full stack tự kiểm từng lớp (pipeline, API Studio, giao diện HTML/JS, script) trên bản sao, không tốn quota Gemini, trước khi giao cho Reviewer/Tester
argument-hint: <worktree> [lớp: pipeline | api | ui | script]
---

Skill này là **sổ tay tự kiểm của agent `dev`**. Dùng sau mỗi việc trong DR hoặc sau khi sửa bug từ issue. Mục tiêu: Reviewer/Tester không gặp lỗi mà Dev đã có thể tự thấy.

Đầu vào: $ARGUMENTS

## Chuẩn bị (mọi lớp)

```bash
WT=<worktree>
PY=$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
T=$(mktemp -d); mkdir -p "$T/storage/videos"
cp -R <repo gốc>/storage/videos/<thư mục mẫu> "$T/storage/videos/"
export TTS_PROVIDER=edge GEMINI_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= APPROVAL_MODE=web
```

Không bao giờ chạy trên `storage/videos/` thật. Dọn `$T` khi xong.

## Theo lớp

| Lớp đã sửa | Kiểm tối thiểu |
|------------|----------------|
| **Pipeline** (`demo.py`, `product_sources.py`, `exercise.py`, `travel.py`…) | `$PY -c "import ast,sys; ast.parse(open('$WT/demo.py').read())"`; chạy đúng lệnh bị ảnh hưởng trên bản sao (`--rerender`, `--render-only`, `--style simple --product ...`); trích khung hình bằng `$PY $WT/scripts/review_frames.py <thư mục trong $T>` và xem bằng Read |
| **API** (`backend/app/api/*.py`) | Chạy từ `$T`, `sys.path.insert(0, '$WT/backend')`, `TestClient(app, base_url="http://127.0.0.1")` (để qua kiểm hostname local): ca bình thường, thiếu header `X-Studio` (phải 403), tên thư mục lạ / `../` (phải 404), thư mục cũ thiếu trường mới |
| **Giao diện** (`backend/app/web/studio.html`) | Bật service từ `$T`: `$PY -m uvicorn --app-dir $WT/backend app.creator_main:app --port 8765`; chụp màn hình bằng Chrome/Chromium headless ở 390 px và 1280 px; mở console xem lỗi JS. Mọi chữ hiện ra là tiếng Việt, không có từ kỹ thuật |
| **Script** (`scripts/`, `.command`) | Chạy với đường dẫn có dấu cách và chữ có dấu; chạy lần 2 (đã chạy rồi) không hỏng gì |
| **Cấu hình** (`.env.example`, `requirements*.txt`) | Biến mới có giá trị mặc định an toàn; thiếu biến thì báo lỗi rõ, không crash khó hiểu |

## Kiểm chéo lớp (full stack)

- Đổi trường trong `script.json` / `product.json` / `topic.json` → kiểm cả nơi ghi (`demo.py`), nơi đọc (`api/studio.py`) và nơi hiện (`studio.html`).
- Đổi mã thoát của `demo.py` → kiểm `api/studio.py` hiểu mã đó và Studio hiện thông báo đúng.
- Đổi API mà `app.html` dùng (`/api/creator`) → **dừng**, C-0001-4.

## Hồi quy nhanh trước khi báo xong

```bash
cd "$T" && $PY $WT/demo.py --product "Test" --price 100000 --images <ảnh mẫu> --points "A|B|C" --style simple --skip-approval --output-dir "$T/out"
```

Ghi kết quả từng bước vào cột "Tự kiểm bằng cách nào" trong báo cáo của Dev.
