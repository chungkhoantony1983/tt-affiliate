---
description: "Execute a task with planning → implementation → verification"
mode: "agent"
---

# Task

Bạn là AI agent thực hiện task theo quy trình có kỷ luật.

## Quy trình

### 1. Phân tích yêu cầu
- Đọc yêu cầu → xác định capability liên quan (xem `docs/specs/requirements/capabilities.md`)
- Đọc L3 detail tại `docs/specs/architecture/capabilities/{cap}.md` nếu có

### 2. Lập kế hoạch
- Liệt kê các bước cần làm (dùng todo list)
- Xác định files cần tạo/sửa
- Ước lượng impact

### 3. Thực thi
- Implement từng bước
- Commit message format: `type(scope): description` (tiếng Anh)
- Types: feat, fix, refactor, docs, chore, test

### 4. Kiểm tra
- Chạy test nếu có
- Verify không break existing functionality
- Confirm output đúng yêu cầu

### 5. Báo cáo
- Tóm tắt những gì đã làm
- List files changed
- Note nếu có issues cần follow-up

## Constraints

- Đọc [CLAUDE.md](../../agent/CLAUDE.md) cho project rules
- Code/commit/log → tiếng Anh
- Docs/báo cáo → tiếng Việt
- Không hardcode secrets
- Video/audio → `storage/` (gitignored)
