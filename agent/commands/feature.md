---
description: Làm một tính năng/thay đổi theo đội vai trò BA → Dev → Reviewer + Tester + MKTG, có cổng duyệt DR
argument-hint: <mô tả yêu cầu bằng lời thường>
---

Bạn là **người điều phối**. Bạn không tự làm phần việc của từng vai trò. Mỗi phase giao cho subagent tương ứng bằng Agent tool (`subagent_type`: `ba`, `dev`, `reviewer`, `tester`, `marketing`). Bạn chuyển kết quả giữa các vai trò, giữ cổng duyệt và lo phần git.

Yêu cầu của người dùng:

$ARGUMENTS

## Phase 0: Chuẩn bị

1. Yêu cầu quá mơ hồ để BA phân tích (không rõ làm cho ai, mục tiêu gì) thì hỏi người dùng 1–3 câu ngắn trước.
2. Tạo worktree và nhánh mới (hook chặn `git checkout`/`switch` ở repo gốc, cũng như push thẳng lên `main`):
   ```bash
   git fetch -q && git worktree add .worktrees/<tên-ngắn> -b <feat|fix|docs>/<tên-ngắn> origin/main
   ```
   Từ đây trở đi, mọi đường dẫn giao cho agent đều là đường dẫn tuyệt đối trong worktree này.
3. Báo người dùng một dòng: tên nhánh, worktree, và vai trò sẽ tham gia.

## Phase 1: Phân tích (BA, và MKTG nếu người vận hành hoặc người xem nhìn thấy kết quả)

- Giao **ba**: yêu cầu nguyên văn + worktree. BA viết DR trong `docs/decision-records/` của worktree.
- Nếu thay đổi chạm tới thứ người vận hành dùng (Studio, tài liệu, lệnh) hoặc thứ người xem thấy (video, caption), giao thêm **marketing** (chế độ 2) đọc DR và góp ý từ góc người dùng. Chuyển góp ý cho BA cập nhật DR.

## Phase 2: Cổng duyệt (bắt buộc dừng)

Trình người dùng: đường dẫn DR, quyết định chính, chi phí (lượt Gemini, $), những gì **không** làm, và câu hỏi mở của BA.
**Dừng lại chờ người dùng đồng ý.** Người dùng muốn đổi thì quay lại Phase 1. Không có câu đồng ý rõ ràng thì không sang Phase 3.

## Phase 3: Triển khai (Dev)

Giao **dev**: worktree + DR + danh sách việc. Nhiều việc độc lập lớn thì có thể chia cho vài agent dev chạy song song, miễn là **không sửa chung một file**.

## Phase 4: Kiểm (Reviewer + Tester + MKTG, chạy song song)

Gửi trong **cùng một lượt** các Agent sau:
- **reviewer**: worktree + DR.
- **tester**: worktree + DR + thư mục video mẫu trong `storage/videos/` của repo gốc (tester tự copy ra thư mục tạm).
- **marketing** chế độ 2 nếu có giao diện hoặc tài liệu cho người vận hành; chế độ 1 trên **bản sao** video nếu thay đổi ảnh hưởng nội dung video.

Gom kết quả:
- Có phát hiện **Chặn**, test **FAIL** hoặc MKTG mức **Chặn** → giao lại **dev** đúng danh sách đó → chạy lại **chỉ** những agent đã báo lỗi.
- Tối đa 2 vòng sửa. Sau 2 vòng mà vẫn còn lỗi thì dừng, báo người dùng tình trạng và đề xuất cách xử lý.
- Mức "Nên sửa" và "Gợi ý": sửa luôn nếu nhỏ và nằm trong DR, còn lại ghi vào DR là việc sau.

## Phase 5: Tài liệu (BA)

Giao **ba**: cập nhật mục "Kết quả" trong DR (dán nguyên bảng của tester và reviewer) và mọi tài liệu SSoT DR đã liệt kê, gồm `TODO.md`, `.claude/CLAUDE.md`, spec L3 và hướng dẫn vận hành.

## Phase 6: Báo cáo

Báo người dùng bằng tiếng Việt, ngắn gọn:
- Đã làm gì (theo việc trong DR), file chính đã đổi.
- Kết quả kiểm: số PASS / FAIL / "Cần người kiểm", và **liệt kê rõ những việc người dùng phải tự kiểm** (nghe giọng, xem giao diện thật…).
- Việc còn lại, nếu có.
- Hỏi người dùng có muốn commit, push nhánh và mở PR không. **Chỉ làm khi người dùng đồng ý.** Commit message viết tiếng Anh. Không bao giờ push lên `main`.

## Lưu ý

- Agent không thấy được hội thoại này. Mỗi lần giao việc phải đưa đủ: worktree, DR, việc cụ thể, kết quả của vai trò trước nếu liên quan.
- Không tự sửa code thay Dev, không tự đánh PASS thay Tester.
- Không gọi Gemini để kiểm (quota 10 lượt/ngày của người vận hành).
