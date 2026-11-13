# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## TikTok Affiliate Automation — AI Workflow Framework

> **CDD (Capability Driven Design)**: Framework theo artifact-placement-guide.
> Design specs nằm tại `docs/specs/` (L1~L4). Agent chỉ chứa AI workflow tooling.
> File này là `agent/CLAUDE.md` (`.claude` → symlink tới `agent/`).

---

## Nguyên tắc cơ bản

- **Ngôn ngữ**: Tài liệu nội bộ và docs → **tiếng Việt**. Code/log/commit → **tiếng Anh**.
- **Tiền tệ**: VND (₫) cho revenue, USD ($) cho chi phí API/SaaS.
- **Số liệu**: Chỉ dùng số có nguồn gốc rõ ràng. Không ước đoán.
- **Secrets**: Không hardcode API keys. Luôn dùng `.env` (gitignored).
- **Storage**: Video/audio/ảnh render không commit vào git. Đặt trong `storage/`.
- **Ưu tiên**: TikTok Shop Affiliate. Mọi việc liên quan Shopee đang tạm dừng (`SHOPEE_ENABLED=false`).
- **Tiến độ**: `TODO.md` là nơi theo dõi pipeline, milestone và quyết định đang mở. Cập nhật sau mỗi việc xong.

---

## Lệnh thường dùng

```bash
# Cài đặt (ffmpeg lấy qua imageio-ffmpeg, không cần Homebrew)
python3 -m venv .venv && .venv/bin/pip install -r requirements-demo.txt
cp .env.example .env                       # bắt buộc: GROQ_API_KEY

# Tạo video (demo.py)
.venv/bin/python demo.py --sheet                  # Google Sheet (SPREADSHEET_ID trong .env), tab "Tiktok"
.venv/bin/python demo.py --sheet --fill-only      # chỉ điền ô trống từ link TikTok, không làm video
.venv/bin/python demo.py --csv products.csv
.venv/bin/python demo.py --product "Tên SP" --price 189000 --images a.jpg,b.jpg \
                         --points "Ý 1|Ý 2|Ý 3" --style simple
.venv/bin/python demo.py --rerender storage/videos/<thư mục>   # sau khi thêm canh_N.png; không gọi lại AI
.venv/bin/python demo.py --render-only storage/videos/<thư mục> [--revoice-all edge]  # Studio: đọc lại câu đã sửa + dựng
.venv/bin/python demo.py --approve storage/videos/<thư mục>     # Studio: post.txt → Drive → status=done
# Cờ khác: --skip-approval, --keep-local, --tab <tên tab>, --output-dir <dir>, --url, --notes

# Service local: app.html (đăng nhập TikTok, gửi video vào inbox) + trang Studio /studio (duyệt, sửa video)
.venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
# hoặc bấm đúp scripts/mo-studio.command (bật service nếu chưa chạy, mở http://127.0.0.1:8000/studio)

# Stack backend đầy đủ (đang hoãn, xem "Kiến trúc thực tế")
docker compose -f docker/docker-compose.yml up -d
```

- **Không có test suite hay linter.** Kiểm tra thay đổi bằng cách chạy chính pipeline (`--style simple` nhanh hơn vì không cần ảnh nhân vật).
- `scripts/test_*.py`, `scripts/run_perfume.py`, `scripts/run_suitcase.py` là script Shopee, `raise SystemExit` ngay khi chạy, không phải test.

---

## Kiến trúc thực tế

### Hai lớp code

1. **MVP đang chạy**: script ở root `demo.py` + `product_sources.py` (Google Sheet, đọc trang TikTok Shop) + `drive_upload.py`. **Không import gì từ `backend/`.** Render bằng FFmpeg qua `subprocess` + Pillow (không dùng moviepy).
2. **`backend/`** (FastAPI + Celery + Postgres + Redis + N8N, thiết kế trong `docs/specs/`): **đang hoãn** đến khi M1–M3 trong `TODO.md` chứng minh có đơn. Chỉ một phần đang dùng thật: `backend/app/creator_main.py` + `app/api/creator.py` + `app/services/tiktok/`, phục vụ `app.html`; `app/api/studio.py` + `app/web/studio.html` cho trang Studio. Phần còn lại (`app/main.py`, Celery tasks) mới kiểm tra import, chưa test với Postgres/Redis/API thật.

### Luồng `demo.py`

```
input (Sheet / CSV / CLI)
 → autofill_row        chỉ điền ô trống: product_sources.fetch_tiktok_product + Groq extract_product_facts
 → generate_script     Groq, JSON "segments" (kind: story | product | cta), style story | simple
 → choose_persona + generate_voiceovers   Gemini TTS mặc định; hết quota → cả video chuyển edge-tts
 → generate_story_images   IMAGE_PROVIDER=manual (mặc định) → ghi prompts.txt, status=needs_images
 → render_video        1080×1920, 25fps
 → duyệt               APPROVAL_MODE=web (mặc định): dừng, status=review → duyệt trên Studio (demo.py --approve)
                       APPROVAL_MODE=terminal: approval_step mở video, hỏi y/n
 → publish_to_tiktok   STUB: chỉ ghi post.txt (caption + checklist đăng tay)
 → move_to_drive       nếu có DRIVE_FOLDER_ID: upload rồi XOÁ thư mục local (trừ khi --keep-local)
 → sheet status=done
```

- **Thư mục output**: `storage/videos/<YYYYmmdd_HHMMSS>_<slug>/` gồm `video.mp4`, `post.txt`, `script.json`, `product.json`, `audio_N.mp3`, `prompts.txt`. `--rerender` dùng lại `script.json` + `product.json` + audio, nhận ảnh `canh_N.png`.
- **Cột `status`** (Sheet/CSV): trống = cần làm; `done`, `skip`, `needs_images`, `review` bị bỏ qua. Danh sách cột: `product_sources.SHEET_COLUMNS`.
- **Lưu ý**: `api/creator.py` chỉ liệt kê thư mục trong `storage/videos/` có `video.mp4`. Khi bật Drive, thư mục đã duyệt bị xoá nên không còn hiện trên `app.html` (dùng `--keep-local` nếu cần).
- **Prompt script** có ràng buộc chống bịa thông số, bịa trải nghiệm cá nhân. Ràng buộc riêng cho từng sản phẩm (vd sản phẩm sức khỏe) nằm ở cột `notes`.

### Studio (DR-0001)

- Trang `http://127.0.0.1:8000/studio`, tiếng Việt, cho người vận hành. **Không** đụng `app.html` (đang xét duyệt).
- `api/studio.py` chỉ đọc/ghi JSON, ảnh, rồi chạy `demo.py --render-only` / `--approve` bằng subprocess (C-0001-2). Một job một lúc; log ở `storage/studio-logs/`.
- Sửa lời đọc: chỉ đọc lại câu có `line != audio_line`, bằng `script.json → tts_provider` của video. Lỗi thì không đổi audio nào (exit 3), Studio đưa lựa chọn `--revoice-all edge`. Không trộn 2 bộ giọng (C-0001-1).
- API ghi bắt buộc header `X-Studio: 1`, không mở qua CORS (C-0001-3). Thư mục không có `product.json` → "Chỉ xem".
- Chi tiết: `docs/specs/architecture/capabilities/video-render.md` § Studio.

### TikTok

- App chỉ xin `user.info.basic` + `video.upload`: video vào **inbox nháp** của creator, **không** dùng Direct Post (`video.publish`).
- Content Posting API không gắn được sản phẩm TikTok Shop → gắn giỏ hàng luôn làm tay trong app.
- `app.html` (GitHub Pages) gọi `http://localhost:8000/api/creator`. CORS theo `CREATOR_WEB_ORIGIN`, middleware `PrivateNetworkAccess` cho Chrome. Token chỉ lưu trong bộ nhớ service.
- Các file `tiktok*.txt` ở root là file xác minh domain/URL prefix của TikTok, không xoá.

### Credentials ở root (gitignored)

- `google-credentials.json`: service account đọc/ghi Google Sheet (cần quyền Editor trên sheet).
- `google-oauth-client.json` + `google-drive-token.json`: OAuth tài khoản Google của người vận hành, để upload Drive (service account không có dung lượng Drive). Cách tạo: đầu file `drive_upload.py`.

---

## Git & hooks

Hook trong `agent/settings.json` chặn các thao tác sau:

- Push thẳng lên `main` → phải qua PR.
- `git checkout` / `git switch` ở repo root → dùng worktree: `git worktree add .worktrees/<tên> -b <branch> origin/main`.
- Sau khi gọi skill kiểu `/task`, `/fix`: phải chạy `workflow_step.py init` trước khi commit/push. **Hiện `workflow_step.py` không chạy được** (thiếu module `automation_engine`), nên các skill SSoT này bị kẹt ở bước commit. Với dự án này, dùng `/feature` (xem dưới).
- `CLAUDE.md` ở repo root chỉ được chứa bảng PJ固有パス設定 (GL-006, `claude_md_guard.py`). Hướng dẫn cho dự án đặt ở file này.

### Làm song song & merge (observer)

Nhiều cửa sổ Claude (VS Code, terminal) hoặc nhiều người có thể làm cùng lúc, mỗi bên một worktree. `scripts/branch_observer.py` theo dõi mọi worktree, nhánh và PR:

- **Hook tự chạy** (`agent/settings.local.json`): đầu phiên báo nếu có nhánh đụng cùng file, `main` ở máy có commit chưa lên GitHub, hoặc còn nhánh đã merge chưa xoá. Trước mỗi lần Write/Edit, cảnh báo (không chặn) nếu file đó cũng đang bị sửa ở worktree hoặc nhánh khác. Mỗi file chỉ cảnh báo một lần mỗi phiên. Gặp cảnh báo này thì báo người dùng.
- `report --fetch`: nhánh nào đụng file nào, có xung đột thật không (`git merge-tree`), thứ tự merge gợi ý.
- `prune [--yes]`: xoá worktree + nhánh local + nhánh GitHub đã merge (nhận ra cả squash merge qua PR), kéo `main` ở máy lên nếu chỉ bị chậm.
- Merge PR bằng **`/merge-pr`** (quan sát → chọn thứ tự → merge → tự dọn nhánh). Không merge nhánh vào `main` ở máy: đó là nguyên nhân lệch nhánh ngày 2026-11-12.

Hook và lệnh này nằm ngoài `skills/`, `scripts/`, `hooks/`, `settings.json` của `agent/` vì sync ghi đè các chỗ đó. Skill SSoT `merge` vẫn giữ nguyên.

`agent/scripts/sync.sh` (chạy từ SSoT bên ngoài) ghi đè `.claude/CLAUDE.md` và chạy `rsync --delete` trên `skills/`, `references/`. Nếu chạy `/sync`, kiểm tra lại nội dung file này. **Không đặt skill riêng của dự án trong `agent/skills/`** vì sẽ bị xoá. Agent và lệnh riêng của dự án nằm ở `agent/agents/` và `agent/commands/` (sync không đụng tới).

---

## Đội vai trò (agents) & workflow

Subagent trong `agent/agents/` (gọi bằng Agent tool, `subagent_type` = tên):

| Agent | Vai trò | Sửa được gì |
|-------|---------|-------------|
| `ba` | Phân tích yêu cầu, chi phí, viết DR (bảng quyết định, DoD), cập nhật tài liệu SSoT sau khi xong | DR, docs, `TODO.md` |
| `dev` | Code theo DR đã duyệt, sửa lỗi do reviewer/tester báo. Làm trong worktree | Code |
| `reviewer` | Soát diff so với DR: lỗi, bảo mật service local, hồi quy, ràng buộc `C-XXXX` | Chỉ đọc |
| `tester` | Test theo bảng quyết định trên **bản sao** video, edge-tts, không Gemini/Drive/Sheet/TikTok thật | Chỉ thư mục tạm |
| `marketing` | (1) Review video trước khi đăng: hook 3s, không bịa, ràng buộc ngành hàng, CTA, vùng an toàn, caption → `marketing-review.md` + đề xuất sửa cho Studio. (2) Review độ dễ dùng giao diện/tài liệu cho người vận hành | `marketing-review.md` |

Lệnh trong `agent/commands/`:

- `/feature <yêu cầu>`: worktree + nhánh → **ba** viết DR (thêm **marketing** nếu người dùng/người xem thấy kết quả) → **dừng chờ người dùng duyệt** → **dev** → **reviewer + tester + marketing** song song (tối đa 2 vòng sửa) → **ba** cập nhật tài liệu → báo cáo, hỏi trước khi commit/PR.
- `/video-review [thư mục…]`: **marketing** review từng video (bỏ trống = mọi video Chờ duyệt) → bảng tổng hợp → người dùng chọn đề xuất → áp dụng qua API Studio (`PUT` + `render`), **không** tự duyệt.
- Khung hình cho review: `.venv/bin/python scripts/review_frames.py storage/videos/<thư mục>` → `storage/review-frames/<thư mục>/` (gitignored).

---

## Cách làm việc với Capabilities

### Chạy một task

```
/task capability:<tên> <mô tả việc cần làm>
```

Ví dụ:
- `/task capability:script-gen Tạo script video cho sản phẩm "Máy lọc không khí Xiaomi"`
- `/task capability:video-render Rerender storage/videos/<thư mục>`
- `/task capability:social-publish Gửi video <thư mục> vào inbox TikTok`

### Quy trình mỗi task

1. **Đọc spec L3** của capability: `docs/specs/architecture/capabilities/<tên>.md`
2. **Xác nhận inputs** (product data, thư mục output, v.v.)
3. **Thực thi** theo workflow trong spec
4. **Cập nhật status** trong Sheet / `products.csv` (cột `status`)
5. **Cập nhật `TODO.md`** khi xong việc hoặc có quyết định mới

---

## Môi trường thực thi

| Môi trường | Hiện tại | Ghi chú |
|------------|----------|---------|
| **Local Dev / chạy thật** | `.venv` trên máy desktop nhà | `demo.py` + service `creator_main` |
| **CI/CD** | Không có (MVP) | Chưa cần trong phase đầu |
| **Docker Compose + N8N** | Hoãn đến sau M1–M3 | `docker/docker-compose.yml`, N8N ở `http://localhost:5678`, workflow trong `n8n/workflows/` |

---

## AI Tools & Cost Strategy

### LLM (Script generation)

| Ưu tiên | Tool | Chi phí | Dùng cho |
|---------|------|---------|---------|
| 1 | **Groq API** (`GROQ_MODEL`, mặc định `qwen/qwen3.8-27b`) | Free | Script + trích thông tin sản phẩm trong `demo.py`. Không dùng `openai/gpt-oss-120b` (sai chính tả tiếng Việt) |
| 2 | **Claude API** (Haiku 3.5) | ~$0.80/1M | Quality-sensitive tasks (chưa dùng trong code) |
| 3 | **Claude.ai Pro** | $20/tháng | Complex reasoning, review thủ công |

> **Quan trọng**: Claude.ai Pro ($20/month) là **web interface**, KHÔNG phải API.
> Không thể gọi từ code/N8N. Dùng để review output chất lượng cao thủ công.

### TTS (Voiceover)

| Ưu tiên | Tool | Chi phí | Ghi chú |
|---------|------|---------|---------|
| 1 | **Gemini TTS** (`GEMINI_TTS_MODEL`, mặc định `gemini-3.8-flash-tts`) | Free tier 10 lượt/ngày (4 lượt/video) | Mặc định khi có `GEMINI_API_KEY` (`TTS_PROVIDER=gemini`) |
| 2 | **edge-tts** (Microsoft) | Free | Fallback; nhiều nhân vật bằng chỉnh pitch/tốc độ (`VOICES` trong `demo.py`) |
| 3 | **OpenAI TTS** / **ElevenLabs** | Trả phí | Chưa dùng |

Giọng narrator tự chọn theo danh mục/tên sản phẩm (`choose_persona`): điện tử, máy móc, ô tô, thể thao → nam Hà Nội; còn lại → nữ Sài Gòn. Ép một giọng: `GEMINI_TTS_PERSONA=nu_nam | nam_bac`.

### Ảnh nhân vật (style `story`)

- `IMAGE_PROVIDER=manual` (mặc định): người dùng tạo ảnh trong Gemini app theo `prompts.txt` → tải lên từng cảnh trên Studio → Dựng lại (hoặc lưu `canh_N.png` → `--rerender`).
- `IMAGE_PROVIDER=gemini` (`gemini-2.5-flash-image`) cần bật billing (free tier quota ảnh = 0). Pollinations không dùng được (xem `TODO.md` §5).

### Video AI (optional, Phase 3+)
- **Kling AI**: ~$10-50/tháng cho AI video clips
- Chỉ dùng khi kênh đã ổn định và cần nâng quality

---

## Context Lock

Mỗi chat session làm việc với **một capability** tại một thời điểm.
Nếu cần làm nhiều capability → mở chat mới cho mỗi capability.

---

## Cấu trúc tài liệu (CDD)

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
│   ├── requirements/          ← L2: Capabilities + BPM
│   ├── architecture/          ← L3: Cap detail + cross-cutting
│   │   └── capabilities/          ← script-gen, video-render, social-publish,
│   │                                ecommerce-sync (Shopee tạm dừng), analytics, n8n-orchestration
│   └── implementation/        ← L4: Implementation specs
├── decision-records/          ← DR (immutable after accept)
└── operations/                ← Hướng dẫn vận hành, quay demo app review

agent/                         ← AI Agent tooling (NOT design specs): references, hooks, skills, scripts
backend/  dashboard/  docker/  n8n/   ← L5 (đang hoãn, trừ phần creator)
```

---

## Tham chiếu nhanh

| Cần gì | Đọc ở đâu |
|--------|-----------|
| Tiến độ, quyết định đang mở | `TODO.md` |
| Vận hành hằng ngày (cho người không code) | `docs/operations/huong-dan-van-hanh-hang-ngay.md` |
| Quy trình app review TikTok | `docs/operations/tiktok-demo-recording.md` |
| Biến môi trường | `.env.example` |
| Capability cụ thể | `docs/specs/architecture/capabilities/<tên>.md` |
| Design process (CDD) | `docs/manual/design-process-guide.md` |
| Rules tổng quát | `agent/references/rules/learned-rules.yaml` |
| Company values / AI personas | `agent/references/config/teams.yaml` → `company.principles` / `personas` |
| Style guide | `agent/references/guides/document-style-guide.md` |
| Export guide | `agent/references/guides/export-standard.md` |
| Feasibility & Cost | `FEASIBILITY.md` |
