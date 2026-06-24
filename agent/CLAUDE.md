# TikTok Affiliate Automation — AI Workflow Framework

> **CDD (Capability Driven Design)**: Framework theo artifact-placement-guide.
> Design specs nằm tại `docs/specs/` (L1~L4). Agent chỉ chứa AI workflow tooling.

---

## Nguyên tắc cơ bản

- **Ngôn ngữ**: Tài liệu nội bộ và docs → **tiếng Việt**. Code/log/commit → **tiếng Anh**.
- **Tiền tệ**: VND (₫) cho revenue, USD ($) cho chi phí API/SaaS.
- **Số liệu**: Chỉ dùng số có nguồn gốc rõ ràng. Không ước đoán.
- **Secrets**: Không hardcode API keys. Luôn dùng `.env` (gitignored).
- **Storage**: Video/audio/ảnh render không commit vào git. Đặt trong `storage/`.

---

## Cấu trúc dự án

```
docs/                          ← Tài liệu thiết kế (CDD L1~L4)
├── manual/                    ← Framework guides (generic, reusable)
│   ├── design-process-guide.md    ← L1~L5 設計プロセス (SSoT)
│   ├── development-guide.md       ← GitHub + coding norms
│   ├── artifact-placement-guide.md ← File placement rules
│   ├── pj-process-guide.md        ← PJ management
│   ├── mock-prototype-guide.md    ← UI prototype guide
│   ├── driver-pattern.md          ← Driver pattern
│   └── templates/                 ← Doc templates
├── specs/                     ← Project-specific design artifacts
│   ├── strategy/              ← L1: Strategy + CRC
│   │   ├── strategy.md            ← §0~§7 (scope, actors, constraints)
│   │   ├── crc.md                 ← Change Request Catalog
│   │   └── reference/             ← Business sources
│   ├── requirements/          ← L2: Capabilities + BPM
│   │   ├── capabilities.md        ← Cap list + 5-axis overview
│   │   ├── capability-landscape.d2
│   │   └── bpm/                   ← Business process diagrams
│   ├── architecture/          ← L3: Cap detail + cross-cutting
│   │   └── capabilities/          ← Per-cap L3 detail
│   │       ├── script-gen.md
│   │       ├── video-render.md
│   │       ├── tiktok-publish.md
│   │       ├── shopee-sync.md
│   │       ├── analytics.md
│   │       └── n8n-orchestration.md
│   └── implementation/        ← L4: Implementation specs
├── decision-records/          ← DR (immutable after accept)
└── operations/                ← Ops guides (deploy, migration)

agent/                         ← AI Agent tooling (NOT design specs)
├── CLAUDE.md                  ← File này
├── references/                ← Rules, config
├── hooks/                     ← Automated guards
├── skills/                    ← AI-assisted workflows
└── scripts/                   ← Utility scripts

backend/                       ← L5: FastAPI source code
dashboard/                     ← L5: Streamlit UI
docker/                        ← Infrastructure
n8n/                           ← N8N workflow definitions
```

---

## Cách làm việc với Capabilities

### Chạy một task

```
/task capability:<tên> <mô tả việc cần làm>
```

Ví dụ:
- `/task capability:script-gen Tạo script video cho sản phẩm "Máy lọc không khí Xiaomi"`
- `/task capability:video-render Render video từ job_id=42`
- `/task capability:shopee-sync Sync tất cả sản phẩm trong store`

### Quy trình mỗi task

1. **Đọc CAPABILITY.md** của capability liên quan
2. **Xác nhận inputs** (product data, job_id, v.v.)
3. **Thực thi** theo workflow trong CAPABILITY.md
4. **Cập nhật status** trong database hoặc log
5. **Ghi summary** vào MEMORY.md nếu session dài

---

## Môi trường thực thi

| Môi trường | Điều kiện | Ghi chú |
|------------|-----------|---------|
| **Local Dev** | Máy desktop nhà, N8N tự host | Luôn bật, không tốn server cost |
| **CI/CD** | Không có (MVP) | Chưa cần trong phase đầu |
| **Production** | Cùng máy desktop | Docker Compose |

### N8N Setup
- URL: `http://localhost:5678`
- Cài trên Docker, chạy liên tục 24/7 trên desktop nhà
- Workflows định nghĩa trong `n8n/workflows/`

---

## AI Tools & Cost Strategy

### LLM (Script generation, reasoning)

| Ưu tiên | Tool | Tier | Chi phí | Dùng cho |
|---------|------|------|---------|---------|
| 1 | **Groq API** (Llama 3.1 70B) | Free | $0 | Bulk script generation |
| 2 | **Gemini 1.5 Flash** | Free (15 RPM) | $0 | Fallback, lifestyle content |
| 3 | **Claude API** (Haiku 3.5) | Pay-per-use | ~$0.80/1M | Quality-sensitive tasks |
| 4 | **Claude.ai Pro** | Web manual | $20/tháng | Complex reasoning, review |

> **Quan trọng**: Claude.ai Pro ($20/month) là **web interface**, KHÔNG phải API.
> Không thể gọi từ N8N. Dùng để review output chất lượng cao thủ công.

### TTS (Voiceover)

| Ưu tiên | Tool | Chi phí | Chất lượng |
|---------|------|---------|-----------|
| 1 | **edge-tts** (Microsoft) | Free | Tốt, có giọng Việt |
| 2 | **OpenAI TTS** | ~$15/1M chars | Rất tốt |
| 3 | **ElevenLabs** | $5-22/tháng | Tốt nhất |

### Video AI (optional, Phase 3+)
- **Kling AI**: ~$10-50/tháng cho AI video clips
- Chỉ dùng khi kênh đã ổn định và cần nâng quality

### Development IDE & Agent

| Tool | Chi phí | Vai trò |
|------|---------|---------|
| **Google Antigravity** (IDE + CLI + SDK) | Free | Agentic IDE: code generation, Gemini access, custom agents |
| **Claude.ai Pro** (web) | $20/tháng | Complex reasoning, architecture review, prompt engineering |
| **VS Code + Copilot** | Free | Standard coding, file editing |

> **Antigravity** (antigravity.google): Google's agentic development platform.
> - IDE: full-featured coding với Gemini AI tích hợp
> - CLI: autonomous coding agents trong terminal
> - SDK: build custom agents (có thể tạo agent cho video pipeline)
> - Cost: **$0** (miễn phí)

---

## Context Lock

Mỗi chat session làm việc với **một capability** tại một thời điểm.
Nếu cần làm nhiều capability → mở chat mới cho mỗi capability.

---

## Tham chiếu nhanh

| Cần gì | Đọc ở đâu |
|--------|-----------|
| Rules tổng quát | `references/rules/learned-rules.yaml` |
| Company values | `references/config/teams.yaml → company.principles` |
| AI personas | `references/config/teams.yaml → personas` |
| Style guide | `references/guides/document-style-guide.md` |
| Design process (CDD) | `develop_guide/design-process-guide.md` |
| CDD Review | `capabilities/CDD-REVIEW.md` |
| Export guide | `references/guides/export-standard.md` |
| Capability cụ thể | `capabilities/<tên>/CAPABILITY.md` |
| Feasibility & Cost | `FEASIBILITY.md` |
