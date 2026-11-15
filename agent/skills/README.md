# skills/

Bộ 17 skill SSoT tiếng Nhật (`task`, `fix`, `review`, `re-review`, `survey`, `test-error`, `spec-update`, `change-impact`, `pm-planning`, `pj-init`, `issues`, `export`, `push`, `comment`, `cleanup`, `merge`, `sync`) đã được gỡ bỏ vì phụ thuộc vào `workflow_step.py` và không dùng trong dự án TikTok Affiliate.

Toàn bộ lệnh và skill thực tế của dự án nằm tại `agent/commands/` (và `.agents/skills/` cho Antigravity):

- `/feature` — Quy trình làm tính năng/thay đổi qua đội vai trò (`ba` → `dev` → `reviewer` + `tester` + `marketing` + `techlead`)
- `/bug` — Tạo và xử lý GitHub issue cho bug
- `/merge-pr` — Quan sát xung đột và merge PR an toàn qua `scripts/branch_observer.py`
- `/video-review` — Điều phối `marketing` review video sản phẩm trước khi đăng
- `/travel-review` — Review video du lịch Việt Nam tiếng Anh (gắn cho `marketing`)
- `/post-analytics` — Phân tích số liệu bài đăng TikTok Studio (gắn cho `marketing`)
- `/tech-audit` — Audit hạ tầng, backend, bộ nhớ, bảo mật, kiến trúc (gắn cho `techlead`)
- `/dev-selfcheck` — Sổ tay tự kiểm theo lớp (gắn cho `dev`)
