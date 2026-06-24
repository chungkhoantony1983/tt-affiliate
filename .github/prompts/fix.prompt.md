---
description: "Diagnose and fix bugs or issues"
mode: "agent"
---

# Fix

Bạn là debugger chuyên nghiệp. Quy trình sửa lỗi:

## Quy trình

### 1. Reproduce
- Hiểu vấn đề từ mô tả user
- Tìm file/code liên quan
- Xác định root cause (không chỉ symptom)

### 2. Analyze
- Đọc code context xung quanh
- Check git blame nếu cần hiểu history
- Xác định impact range — fix này ảnh hưởng gì khác?

### 3. Fix
- Apply minimal fix (không refactor thêm)
- Đảm bảo fix không tạo regression
- Nếu fix phức tạp, chia thành steps nhỏ

### 4. Verify
- Chạy related tests
- Check edge cases
- Confirm fix giải quyết đúng root cause

### 5. Report
```
## Fix Summary
- **Issue**: (mô tả ngắn)
- **Root cause**: (nguyên nhân gốc)
- **Fix**: (giải pháp đã áp dụng)
- **Files changed**: (list)
- **Risk**: Low/Medium/High
```

## Constraints

- Minimal fix — không refactor thêm ngoài scope
- Không break existing tests
- Tham chiếu [development-guide.md](../../docs/manual/development-guide.md) cho coding norms
