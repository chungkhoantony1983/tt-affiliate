---
name: video-review
description: >-
  Điều phối agent marketing review video đã dựng (hook 3 giây, nội dung, tuân thủ
  chính sách affiliate, chữ trên màn hình, caption) và đề xuất sửa cho Studio.
  Sử dụng skill này khi người dùng gọi /video-review hoặc yêu cầu review video trong storage/videos/.
---

# Quy trình `/video-review` — Marketing Review Video & Đề xuất cho Studio

Bạn là **người điều phối** việc review video. Phần review giao cho subagent **marketing** (chế độ 1). Bạn chỉ chọn video, gom kết quả và áp dụng đề xuất **khi người dùng đồng ý**.

> **Cách gọi subagent `marketing` trên Antigravity:**
> - Nếu `marketing` chưa có trong danh sách `Available subagents` của phiên hiện tại, đọc `.agents/agents/marketing.md` và gọi `define_subagent(Name="marketing", Description="...", SystemPrompt="...", EnableWriteTools=true)` một lần.
> - Sau đó dùng `invoke_subagent(TypeName="marketing", ...)` để giao việc.

## Bước 1: Chọn video

- Người dùng có chỉ định đường dẫn thì dùng đúng các thư mục đó.
- Bỏ trống thì lấy mọi thư mục trong `storage/videos/` (ở repo gốc, không phải worktree) có `video.mp4` và `product.json`, **không** có `post.txt` (chưa duyệt). Có `prompts.txt` thì vẫn lấy nhưng ghi chú là bản nháp.
- Thư mục đã có `marketing-review.md` mới hơn `video.mp4` thì bỏ qua, trừ khi người dùng nêu tên thư mục đó.
- Không có video nào thì báo người dùng rồi dừng.

## Bước 2: Review

Mỗi video giao một subagent **marketing**, tối đa 3 subagent chạy song song trong cùng một lượt (`invoke_subagent`). Prompt cho mỗi subagent gồm: chế độ 1, đường dẫn tuyệt đối tới thư mục video, và đường dẫn repo gốc (để chạy `.venv/bin/python scripts/review_frames.py`).

## Bước 3: Tổng hợp cho người dùng

| Video | Kết luận | Vấn đề chính | Lượt Gemini nếu sửa hết |
|-------|----------|--------------|-------------------------|

Kèm link tới từng `marketing-review.md`. Nhắc lại những việc **cần người kiểm** (nghe giọng…).

## Bước 4: Áp dụng đề xuất (chỉ khi người dùng đồng ý)

Hỏi người dùng muốn áp dụng đề xuất nào (tất cả / chỉ phần miễn phí / chọn từng mục / không). Nếu có áp dụng:

1. Lấy khối `Dữ liệu cho Studio` trong `marketing-review.md`, chỉ giữ các mục người dùng chọn.
2. Áp dụng **qua API Studio**, để dữ liệu được kiểm và chuẩn hoá giống hệt khi sửa tay (C-0001-2):
   - Service chưa chạy (`curl -s http://127.0.0.1:8000/health` lỗi) thì bật nền từ repo gốc: `.venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000`.
   - `GET /api/studio/videos/<thư mục>` để lấy danh sách cảnh hiện tại. Dựng `segments` **đủ mọi cảnh** (Studio yêu cầu đủ số cảnh): cảnh không đổi giữ nguyên `line`/`text`, cảnh có đề xuất thì thay.
   - `PUT /api/studio/videos/<thư mục>` với header `X-Studio: 1` và `Content-Type: application/json`.
   - Nếu có thay đổi cần dựng lại thì gọi `POST /api/studio/videos/<thư mục>/render` (header `X-Studio: 1`), rồi theo dõi `GET /api/studio/job` cho tới khi xong. Lỗi do hết quota Gemini thì báo người dùng và hỏi có muốn đọc lại toàn bộ bằng giọng miễn phí không (`{"revoice_all": "edge"}`). **Không tự chọn thay người dùng.**
3. **Không bấm duyệt (approve) thay người dùng.** Duyệt sẽ đưa video lên Drive và xoá thư mục khỏi máy. Báo người dùng mở Studio xem lại video mới rồi tự duyệt.
4. Muốn chạy lại review sau khi sửa thì dùng `/video-review <thư mục>`.

## Lưu ý

- Mỗi câu lời đọc sửa trên video Gemini tốn 1 lượt (10 lượt/ngày). Luôn nói rõ số lượt **trước** khi áp dụng.
- Đề xuất cần sửa code (chữ CTA cố định, bố cục) thì không áp dụng ở đây. Đề nghị người dùng chạy `/feature`.
