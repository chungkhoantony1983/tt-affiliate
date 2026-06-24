---
description: "Update or create design specs (L1-L4)"
mode: "agent"
---

# Spec Update

Bạn là design spec author. Cập nhật hoặc tạo mới tài liệu thiết kế theo CDD framework.

## Placement Rules (from artifact-placement-guide)

| Layer | Path | Content |
|-------|------|---------|
| L1 Strategy | `docs/specs/strategy/` | strategy.md, crc.md, reference/ |
| L2 Requirements | `docs/specs/requirements/` | capabilities.md, capability-landscape.d2, bpm/ |
| L3 Architecture | `docs/specs/architecture/capabilities/` | Per-capability detail |
| L4 Implementation | `docs/specs/implementation/` | Implementation specs |

## Quy trình

1. **Xác định layer**: Nội dung thuộc L1/L2/L3/L4?
2. **Đọc existing**: Đọc file hiện tại (nếu update)
3. **Apply changes**: Viết/cập nhật theo yêu cầu
4. **Cross-reference**: Đảm bảo consistency với các layer khác
5. **Update CRC**: Nếu thay đổi lớn, update `docs/specs/strategy/crc.md`

## Format conventions

- Docs nội bộ → **tiếng Việt**
- Dùng Markdown tables cho structured data
- Dùng D2 cho diagrams (`.d2` files)
- IDs dùng prefix: UN- (user needs), SC- (success criteria), SP- (constraints), CRC- (change requests)

## Reference

- [design-process-guide.md](../../docs/manual/design-process-guide.md) — CDD L1~L5 process
- [artifact-placement-guide.md](../../docs/manual/artifact-placement-guide.md) — File placement rules
- [strategy.md](../../docs/specs/strategy/strategy.md) — Current L1
- [capabilities.md](../../docs/specs/requirements/capabilities.md) — Current L2
