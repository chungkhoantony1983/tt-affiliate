---
description: Tech Lead audit một vùng code (hạ tầng, backend, bộ nhớ/hiệu năng, bảo mật, kiến trúc) bằng checklist và lệnh đo riêng của dự án; phát hiện Loại Bug thì ghi issue qua /bug
argument-hint: <vùng cần audit, ví dụ "backend/app/api/studio.py" | "luồng render" | "bảo mật service local"> | (bỏ trống = toàn hệ thống đang chạy)
---

Mã nạp: tech-audit/1

Skill này là **sổ tay của agent `techlead`**. Gọi bằng lệnh thì bạn là người điều phối: giao **techlead** (chế độ 2: Audit) với vùng dưới đây, rồi xử lý kết quả theo mục "Sau khi có báo cáo". Nếu bạn chính là techlead thì làm theo checklist bên dưới.

Vùng cần audit:

$ARGUMENTS

## Bản đồ hệ thống (để chọn đúng chỗ soát)

| Mảng | File chính | Đang chạy thật? |
|------|-----------|------------------|
| Pipeline | `demo.py`, `product_sources.py`, `drive_upload.py`, `exercise.py` (nếu có) | Có |
| Service local | `backend/app/creator_main.py`, `app/api/creator.py`, `app/api/studio.py`, `app/services/tiktok/` | Có |
| Giao diện | `backend/app/web/studio.html`, `app.html` (C-0001-4: không đổi) | Có |
| Script vận hành | `scripts/mo-studio.command`, `scripts/review_frames.py`, `scripts/branch_observer.py` | Có |
| Backend đầy đủ | `backend/app/main.py`, Celery, `docker/`, `n8n/` | **Hoãn**: chỉ ghi Nợ kỹ thuật, không xếp Chặn |

## Checklist và lệnh đo

Mọi lệnh chạy **chỉ đọc**, hoặc trên **bản sao** dữ liệu trong `T=$(mktemp -d)`. Không gọi Gemini, Drive, Sheet, TikTok thật. Dọn `$T` khi xong.

### 1. Bảo mật

```bash
# subprocess: có shell=True hay ghép chuỗi lệnh từ dữ liệu người dùng không
grep -rn "subprocess\.\|os\.system\|shell=True" --include=*.py . | grep -v "\.venv\|\.worktrees"
# đường dẫn từ request: có resolve() + kiểm nằm trong storage/videos không
grep -n "Path(\|/ name\|folder" backend/app/api/studio.py | head -40
# CORS, header X-Studio, bind địa chỉ
grep -rn "CORSMiddleware\|allow_origins\|X-Studio\|require_studio\|--host\|0\.0\.0\.0" backend scripts
# secret có lọt vào log / response / git không
grep -rn "API_KEY\|token\|secret" --include=*.py backend demo.py | grep -i "print\|log\|return" | head
git ls-files | grep -iE "credential|token|\.env$|oauth"   # phải rỗng
```

Ràng buộc phải giữ: C-0001-3 (API ghi cần `X-Studio: 1`, không mở qua CORS), token TikTok chỉ trong bộ nhớ, service chỉ nghe `127.0.0.1`.

### 2. Bộ nhớ và hiệu năng

```bash
# đọc cả file lớn vào RAM
grep -rn "\.read()\|read_bytes()\|await request.body()" --include=*.py backend demo.py
# Pillow mở ảnh không đóng (nên dùng with Image.open(...))
grep -rn "Image.open" --include=*.py . | grep -v "with \|\.venv\|\.worktrees"
# đo RAM đỉnh khi dựng lại một video (trên bản sao, giọng edge, không Drive/Sheet)
cp -R storage/videos/<thư mục mẫu> "$T/"
TTS_PROVIDER=edge GEMINI_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= \
  /usr/bin/time -v .venv/bin/python demo.py --rerender "$T/<thư mục mẫu>" 2>&1 | grep -E "Maximum resident|Elapsed"
# dung lượng storage và log có tăng mãi không
du -sh storage/* 2>/dev/null; ls storage/studio-logs | wc -l
```

Trên macOS không có `/usr/bin/time -v` thì dùng `/usr/bin/time -l` (dòng `maximum resident set size`).

Soát thêm: tiến trình FFmpeg con khi job bị huỷ hoặc timeout có bị bỏ lại không (`ps aux | grep ffmpeg` sau khi job lỗi); việc nào render lại dù đầu vào không đổi; số lần gọi Groq/Gemini cho một video so với mức cần.

### 3. Backend

- Mỗi API ghi: bấm 2 lần liên tiếp thì sao (idempotent, hay báo 409 vì đang có job)?
- Ghi JSON: ghi file tạm rồi `os.replace`, hay ghi đè trực tiếp (mất dữ liệu khi máy tắt giữa chừng)?
- Thư mục video cũ thiếu trường mới: có `KeyError` không?
- Subprocess: có timeout, có bắt mã thoát (exit 3, exit 4 theo DR) và trả lỗi tiếng Việt có việc cần làm tiếp không?

Kiểm nhanh bằng TestClient trên bản sao:

```bash
cd "$T" && mkdir -p storage/videos && cp -R <repo>/storage/videos/<thư mục mẫu> storage/videos/
<repo>/.venv/bin/python -c "
import sys; sys.path.insert(0, '<repo>/backend')
from fastapi.testclient import TestClient
from app.creator_main import app
c = TestClient(app, base_url='http://127.0.0.1')   # hostname phải là máy local, nếu không mọi API ghi đều 403
print(c.get('/api/studio/videos').status_code)
print(c.put('/api/studio/videos/x', json={}).status_code)   # thiếu X-Studio: phải bị chặn
print(c.get('/api/studio/videos/..%2F..%2Fetc').status_code) # path traversal: phải 404
"
```

### 4. Hạ tầng

- `requirements*.txt`: gói không dùng, gói chưa ghim phiên bản, gói có lỗ hổng đã biết (`.venv/bin/pip list --outdated` để tham khảo, không tự nâng).
- `scripts/mo-studio.command`: cổng 8000 đã bị chiếm thì sao, service chết thì người vận hành biết bằng cách nào.
- `.gitignore`: mọi thư mục trong `storage/` sinh ra file lớn hoặc dữ liệu riêng đều bị bỏ qua.
- Docker/N8N đang hoãn: chỉ ghi chỗ lệch giữa `docker/` và code hiện tại là Nợ kỹ thuật.

### 5. Kiến trúc

```bash
grep -rn "from backend\|import backend\|from app\." demo.py product_sources.py drive_upload.py   # phải rỗng
```

- Logic nào bị chép ở nhiều file (TTS, font, đường dẫn storage)? Có nên gom không, gom thì tốn bao nhiêu công?
- Module nào quá lớn hoặc làm quá nhiều việc (ví dụ `demo.py`)? Đề xuất tách chỉ khi có lý do cụ thể (sắp thêm tính năng đụng vào, hay lỗi lặp lại ở đó).
- Mỗi đề xuất kiến trúc phải nói: lợi gì, tốn gì, có cần DR mới không.

## Báo cáo

Dùng đúng bảng trong `agent/agents/techlead.md` (Mảng / Loại / Mức / File:dòng / Vấn đề & kịch bản / Đề xuất). Ghi kèm lệnh đã chạy và số đo thật.

## Sau khi có báo cáo (người điều phối)

1. Trình người dùng bảng tóm tắt: số phát hiện theo Mảng và Mức, 3 việc nên làm trước.
2. Phát hiện Loại **Bug**: hỏi người dùng rồi ghi issue theo Phase 1 của `/bug` (mỗi bug một issue, ghi "Ai phát hiện: techlead, audit <vùng>").
3. Loại **Tối ưu** lớn hoặc đổi kiến trúc: đề xuất làm qua `/feature` (cần DR). Loại **Nợ kỹ thuật**: giao **ba** ghi vào `TODO.md` § 5.
4. Không tự sửa code.
