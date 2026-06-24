---
description: "Analyze change impact across codebase"
mode: "agent"
---

# Change Impact

Phân tích ảnh hưởng của một thay đổi dự kiến.

## Input
User cung cấp: mô tả thay đổi, hoặc file/function cụ thể sẽ thay đổi.

## Quy trình

### 1. Identify change scope
- Files/functions sẽ bị modify
- New files/APIs sẽ được tạo

### 2. Trace dependencies
- Ai import/call vào code sẽ thay đổi?
- Database schema changes → migration needed?
- API contract changes → consumers affected?
- Config/env changes → deployment impact?

### 3. Risk assessment

| Area | Impact | Risk | Mitigation |
|------|--------|------|-----------|
| (component) | (mô tả) | 🔴/🟡/🟢 | (action) |

### 4. Test impact
- Tests nào sẽ cần update?
- Tests mới cần viết?
- Manual testing cần thiết?

### 5. Rollback plan
- Có thể rollback dễ dàng không?
- Data migration có reversible không?

## Output

```markdown
## Change Impact Report

### Proposed Change
(mô tả)

### Affected Components
- [ ] Backend API
- [ ] Database schema
- [ ] N8N workflows
- [ ] Dashboard UI
- [ ] Docker config
- [ ] External API contracts

### Risk Matrix
(table)

### Recommendation
(proceed / proceed with caution / needs redesign)
```
