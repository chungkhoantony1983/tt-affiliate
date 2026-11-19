---
trigger: always_on
---

# Hướng dẫn điều phối trên Antigravity (TikTok Affiliate)

Cấu hình `.agents/` này giúp Antigravity vận hành tương đương 100% với bộ `.claude` (`agent/`) của dự án:

## 1. Các Workflow chính (Skills trong `.agents/skills/`)

Khi người dùng gọi `/feature`, `/merge-pr`, `/video-review` (hoặc yêu cầu bằng lời tương ứng), **bắt buộc đọc `SKILL.md` tương ứng** trước khi làm:

- **`feature`** ([`.agents/skills/feature/SKILL.md`](../skills/feature/SKILL.md)): Quy trình 6 Phase làm tính năng/thay đổi qua đội vai trò `ba` → Cổng duyệt DR → `dev` → `reviewer` + `tester` + `marketing` (song song) → `ba` cập nhật SSoT → Báo cáo.
- **`merge-pr`** ([`.agents/skills/merge-pr/SKILL.md`](../skills/merge-pr/SKILL.md)): Quan sát xung đột bằng `scripts/branch_observer.py report --fetch`, gợi ý thứ tự merge PR qua GitHub API, và tự dọn nhánh/worktree (`prune --fetch --yes`).
- **`video-review`** ([`.agents/skills/video-review/SKILL.md`](../skills/video-review/SKILL.md)): Điều phối subagent `marketing` (chế độ 1) review tối đa 3 video song song, tổng hợp kết quả và áp dụng đề xuất qua API Studio khi người dùng đồng ý.

## 2. Cách gọi các Role Subagent (`ba`, `dev`, `reviewer`, `tester`, `marketing`)

Định nghĩa của 5 vai trò nằm tại `.agents/agents/`:
- [`ba.md`](../agents/ba.md) — Business Analyst (viết DR, phân tích chi phí, cập nhật SSoT)
- [`dev.md`](../agents/dev.md) — Developer (triển khai code trong worktree theo DR đã duyệt)
- [`reviewer.md`](../agents/reviewer.md) — Code Reviewer (chỉ đọc, soát diff so với DR và ràng buộc `C-XXXX`)
- [`tester.md`](../agents/tester.md) — Tester (chạy thật trên bản sao `$T`, `TTS_PROVIDER=edge`, không dùng Gemini/Drive/Sheet thật)
- [`marketing.md`](../agents/marketing.md) — Marketing Reviewer (Chế độ 1: review video; Chế độ 2: review giao diện/tài liệu cho người vận hành)

**Quy trình gọi subagent trên Antigravity:**
1. Nếu vai trò cần gọi (`ba`, `dev`, `reviewer`, `tester`, `marketing`) chưa có sẵn trong danh sách `Available subagents` của phiên hiện tại, hãy đọc file `.agents/agents/<role>.md` tương ứng và gọi công cụ `define_subagent` một lần (đặt `EnableWriteTools: true` để subagent có quyền chạy lệnh `run_command` và ghi file theo phạm vi vai trò).
2. Gọi `invoke_subagent(TypeName="<role>", Role="<mô tả ngắn>", Prompt="<đầy đủ đường dẫn worktree, DR, nhiệm vụ cụ thể>")`.
3. Ở các bước chạy song song (như Phase 4 của `feature` hoặc Bước 2 của `video-review`), gọi `invoke_subagent` cho tất cả các agent trong **cùng một lượt**, sau đó kết thúc lượt để chờ hệ thống trả kết quả của từng subagent về.

## 3. Ràng buộc an toàn Git & Quota (tương đương Hooks)

- **Không bao giờ** `git checkout` / `git switch` ở repo gốc; luôn làm việc trên worktree `.worktrees/<tên-ngắn>` với nhánh mới `-b <feat|fix|docs>/<tên-ngắn> origin/main`.
- **Không bao giờ** `git push` thẳng lên `main` hoặc merge nhánh vào `main` ở máy local.
- **Trước khi sửa file hoặc tạo nhánh**, kiểm tra xung đột song song bằng `python3 scripts/branch_observer.py report --fetch`.
- **Bảo vệ quota Gemini TTS (10 lượt/ngày)**: Không bao giờ gọi Gemini TTS khi test/kiểm thử; luôn xuất `TTS_PROVIDER=edge GEMINI_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID=`.
