# skills/

Bộ 17 skill SSoT tiếng Nhật (`task`, `fix`, `review`, `re-review`, `survey`, `test-error`, `spec-update`, `change-impact`, `pm-planning`, `pj-init`, `issues`, `export`, `push`, `comment`, `cleanup`, `merge`, `sync`) đã được gỡ bỏ vì phụ thuộc vào `workflow_step.py` và không dùng trong dự án TikTok Affiliate.

**Không đặt skill riêng của dự án trong thư mục này.** `agent/scripts/sync.sh` chạy `rsync --delete` trên `skills/`, nên file lạ ở đây sẽ bị xoá. Skill riêng của dự án là file lệnh `agent/commands/<tên>.md` (= `.claude/commands/`). Agent khai báo skill ở trường `skills:` trong frontmatter. Mỗi skill có dòng `Mã nạp: <tên>/<phiên bản>` ngay sau frontmatter, và agent luôn có câu "đọc `.claude/commands/<tên>.md` nếu chưa có trong ngữ cảnh" (DR-0004, C-0004-1).

Lệnh và skill hiện có trong `agent/commands/` (bản chép cho Antigravity nằm ở `.agents/skills/`, chưa đồng bộ 4 skill mới của DR-0004, xem issue #27):

Lệnh quy trình:

- `/feature`: làm tính năng/thay đổi qua đội vai trò (`ba` → `dev` → `reviewer` + `tester` + `marketing` + `techlead`)
- `/bug`: tạo và xử lý GitHub issue cho bug
- `/merge-pr`: quan sát xung đột và merge PR an toàn qua `scripts/branch_observer.py`
- `/video-review`: điều phối `marketing` review video sản phẩm trước khi đăng

Skill gắn cho agent (khai báo trong `skills:`):

| Skill | Gắn cho | Việc |
|-------|---------|------|
| `dev-selfcheck` | `dev` | Sổ tay tự kiểm theo lớp |
| `sandbox-render` | `dev`, `tester` (người điều phối gõ `/sandbox-render`) | Dựng lại video trên bản sao (`scripts/sandbox_render.py`): không Gemini, không duyệt, không Drive/Sheet, không ghi giáo trình. Chưa hỗ trợ thư mục travel |
| `audio-check` | `dev`, `tester`, `marketing` | Đo tiếng nổ chỗ nối (`scripts/audio_seams.py`) + chép lời bằng Groq Whisper (`scripts/transcript_check.py`, không nhận thư mục travel) |
| `voice-rules` | `dev`, `reviewer`, `techlead`, `tester` | Quy tắc giọng đọc, chỗ có thể gọi Gemini |
| `dr-draft` | `ba` | Giữ số DR khi nhiều phiên song song, khung DR |
| `tech-audit` | `techlead` | Audit hạ tầng, backend, bộ nhớ, bảo mật, kiến trúc |
| `travel-review` | `marketing` | Review video du lịch Việt Nam tiếng Anh |
| `post-analytics` | `marketing` | Phân tích số liệu bài đăng TikTok Studio |
