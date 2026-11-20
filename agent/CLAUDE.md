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
.venv/bin/python demo.py --sheet-row 2            # tạo video cho 1 dòng cụ thể trên Google Sheet / CSV (dòng >= 2)
.venv/bin/python demo.py --sheet --fill-only      # chỉ điền ô trống từ link TikTok, không làm video
.venv/bin/python demo.py --csv products.csv
.venv/bin/python demo.py --product "Tên SP" --price 189000 --images a.jpg,b.jpg \
                         --points "Ý 1|Ý 2|Ý 3" --style simple
.venv/bin/python demo.py --create-json storage/studio-logs/create-input.json  # Studio: tạo video sản phẩm mới
.venv/bin/python demo.py --rerender storage/videos/<thư mục>   # sau khi thêm canh_N.png; không gọi lại AI
.venv/bin/python demo.py --render-only storage/videos/<thư mục> [--revoice-all edge]  # Studio: đọc lại câu đã sửa + dựng
.venv/bin/python demo.py --approve storage/videos/<thư mục>     # Studio: post.txt → Drive → status=done
# Cờ khác: --skip-approval, --keep-local, --tab <tên tab>, --output-dir <dir>, --url, --notes

# Video du lịch Việt Nam tiếng Anh (tab Travel, không bán hàng; DR-0002, DR-0008)
.venv/bin/python demo.py --travel --sheet                       # 1 video/lần → status=review
.venv/bin/python demo.py --travel --refresh-facts storage/videos/<thư mục> [--confirm id1,id2]  # làm mới dữ kiện quá 30 ngày; --confirm = đã kiểm tay trang chính thức
# --approve / --render-only dùng chung lệnh trên, tự nhận thư mục travel qua topic.json

# Service local: app.html (đăng nhập TikTok, gửi video vào inbox) + trang Studio /studio (tạo mới, duyệt, sửa video)
.venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
# hoặc bấm đúp scripts/mo-studio.command (bật service nếu chưa chạy, mở http://127.0.0.1:8000/studio)

# Stack backend đầy đủ (đang hoãn, xem "Kiến trúc thực tế")
docker compose -f docker/docker-compose.yml up -d
```

- **Không có test suite hay linter.** Kiểm tra thay đổi bằng cách chạy chính pipeline (`simple` là mặc định, nhanh vì không cần ảnh nhân vật).
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
 → generate_script     Groq, JSON "segments" (kind: story | product | cta), style simple (mặc định, tự động hoàn toàn) | story (chỉ khi cần: cột `style`/`--style story`, cần ảnh nhân vật)
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

### Studio (DR-0001, DR-0007)

- Trang `http://127.0.0.1:8000/studio`, tiếng Việt, cho người vận hành: **tạo video sản phẩm mới** (`+ Tạo video mới` từ link TikTok Shop hoặc dòng Google Sheet `>= 2`, xem trước thông tin, sửa giá có đọc số bằng chữ tiếng Việt, tải tối đa 3 ảnh sản phẩm đầu vào) và **duyệt / sửa video**. **Không** đụng `app.html` (đang xét duyệt).
- `api/studio.py` chỉ đọc/ghi JSON, ảnh, rồi chạy `demo.py --create-json` / `--render-only` / `--approve` bằng subprocess (C-0001-2). Một job một lúc; log ở `storage/studio-logs/`, ảnh chuẩn bị tạo mới ở `storage/studio-logs/staging/`.
- Giá & ảnh người dùng nhập/tải trên Studio luôn ưu tiên hơn dữ liệu tự đọc từ Sheet/TikTok (C-0007-1); chỉ nhận giá `0` (ẩn giá) hoặc `>= 1000` VND (C-0007-2); ảnh sản phẩm tải lên lưu thành `anh_sp_{1..3}.<ext>` trong thư mục video (C-0007-3).
- Sửa lời đọc: chỉ đọc lại câu có `line != audio_line`, bằng `script.json → tts_provider` của video. Lỗi thì không đổi audio nào (exit 3), Studio đưa lựa chọn `--revoice-all edge`. Không trộn 2 bộ giọng (C-0001-1).
- API ghi bắt buộc header `X-Studio: 1`, không mở qua CORS (C-0001-3). Thư mục không có `product.json` → "Chỉ xem".
- Chi tiết: `docs/specs/architecture/capabilities/video-render.md` § Studio.

### Du lịch (`travel.py`, capability `travel-content`)

- Video trả lời 1 câu hỏi của du khách về Việt Nam (EN + phụ đề VI), mọi câu có nguồn trích dẫn. Thư mục output có `topic.json`, `facts.json`, `credits.txt` (không có `product.json`). Hồ sơ điểm đến / đối tượng / trụ cột ở `content/travel/` (thêm nước = thêm JSON, không sửa code); câu hỏi đầu vào: `content/travel/seed-questions.csv` → tab `Travel`.
- Mã thoát: 3 đọc lại giọng lỗi · 4 chưa sẵn sàng · **5** số không khớp nguồn (`fact_check`) · **6** dữ kiện dễ đổi quá 30 ngày (`facts_stale`, chạy `--refresh-facts`) · **7** tải Drive lỗi (`drive_failed`, không `done`, thư mục còn).
- Studio hiện thư mục travel (nguồn, ảnh/bản quyền, checklist); chỉ edge-tts (không tốn Gemini); không tải `clip_*` / `img_*` lên Drive.
- Chi tiết: `docs/specs/architecture/capabilities/travel-content.md`, `DR-0002`, `DR-0008`.

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
- Bộ 17 skill SSoT tiếng Nhật trong `agent/skills/` đã được xoá (và tắt bắt lệnh trong `workflow_prompt_guard.py`) để không kích hoạt `workflow_step.py init` gây kẹt ở bước commit. Với dự án này, dùng các lệnh trong `agent/commands/` (`/feature`, `/bug`, `/merge-pr`, `/video-review`… xem dưới).
- `CLAUDE.md` ở repo root chỉ được chứa bảng PJ固有パス設定 (GL-006, `claude_md_guard.py`). Hướng dẫn cho dự án đặt ở file này.

### Làm song song & merge (observer)

Nhiều cửa sổ Claude (VS Code, terminal) hoặc nhiều người có thể làm cùng lúc, mỗi bên một worktree. `scripts/branch_observer.py` theo dõi mọi worktree, nhánh và PR:

- **Hook tự chạy** (`agent/settings.local.json`): đầu phiên báo nếu có nhánh đụng cùng file, `main` ở máy có commit chưa lên GitHub, hoặc còn nhánh đã merge chưa xoá. Trước mỗi lần Write/Edit, cảnh báo (không chặn) nếu file đó cũng đang bị sửa ở worktree hoặc nhánh khác. Mỗi file chỉ cảnh báo một lần mỗi phiên. Gặp cảnh báo này thì báo người dùng.
- `report --fetch`: nhánh nào đụng file nào, có xung đột thật không (`git merge-tree`), thứ tự merge gợi ý.
- `prune [--yes]`: xoá worktree + nhánh local + nhánh GitHub đã merge (nhận ra cả squash merge qua PR), kéo `main` ở máy lên nếu chỉ bị chậm.
- Merge PR bằng **`/merge-pr`** (quan sát → chọn thứ tự → merge → tự dọn nhánh). Không merge nhánh vào `main` ở máy: đó là nguyên nhân lệch nhánh ngày 2026-11-12.

Hook và lệnh này nằm ngoài `skills/`, `scripts/`, `hooks/`, `settings.json` của `agent/` vì sync ghi đè các chỗ đó.

`agent/scripts/sync.sh` (chạy từ SSoT bên ngoài) ghi đè `.claude/CLAUDE.md` và chạy `rsync --delete` trên `skills/`, `references/`. Nếu chạy `/sync`, kiểm tra lại nội dung file này. **Không đặt skill riêng của dự án trong `agent/skills/`** vì sẽ bị xoá. Agent và lệnh riêng của dự án nằm ở `agent/agents/` và `agent/commands/` (sync không đụng tới).

---

## Đội vai trò (agents) & workflow

Subagent trong `agent/agents/` (gọi bằng Agent tool, `subagent_type` = tên):

| Agent | Vai trò | Sửa được gì |
|-------|---------|-------------|
| `ba` | Phân tích yêu cầu, chi phí, viết DR (bảng quyết định, DoD), cập nhật tài liệu SSoT sau khi xong. Skill: `dr-draft` | DR, docs, `TODO.md` |
| `dev` | **Dev full stack**: pipeline `demo.py` + FFmpeg/Pillow, backend FastAPI, Studio HTML/JS, script, Docker. Code theo DR đã duyệt, sửa lỗi do reviewer/tester/techlead báo hoặc từ GitHub issue. Làm trong worktree. Skill: `dev-selfcheck`, `sandbox-render`, `audio-check`, `voice-rules` | Code |
| `reviewer` | Soát diff so với DR: lỗi, bảo mật service local, hồi quy, ràng buộc `C-XXXX`. Skill: `voice-rules` | Chỉ đọc |
| `techlead` | Review và đề xuất tối ưu: hạ tầng, backend, bộ nhớ/hiệu năng, bảo mật, kiến trúc. Review DR/diff hoặc audit một vùng code; phân loại Bug / Tối ưu / Nợ kỹ thuật. Skill: `tech-audit`, `voice-rules` | Chỉ đọc |
| `tester` | Test theo bảng quyết định trên **bản sao** video, edge-tts, không Gemini/Drive/Sheet/TikTok thật. Skill: `sandbox-render`, `audio-check`, `voice-rules` | Chỉ thư mục tạm |
| `marketing` | (1) Review video trước khi đăng: hook 3s, không bịa, ràng buộc ngành hàng, CTA, vùng an toàn, caption → `marketing-review.md` + đề xuất sửa cho Studio. (2) Review độ dễ dùng giao diện/tài liệu cho người vận hành. (3) Review video du lịch Việt Nam tiếng Anh: dữ kiện có nguồn, bản quyền clip, tiếng Anh, phụ đề Việt (skill `travel-review`). (4) Phân tích hiệu quả bài đăng, tiếp cận người xem (skill `post-analytics`). Chế độ (1) dùng thêm skill `audio-check` (đo tiếng nổ, chép lời bằng Groq Whisper qua `scripts/transcript_check.py`) | `marketing-review.md`, `storage/analytics/` |

Model của từng agent khai báo ở trường `model:` / `effort:` trong frontmatter: `ba`, `techlead`, `reviewer` (phân tích, đề xuất, review) dùng `opus` + `effort: medium`; `dev`, `tester`, `marketing` (làm theo DR/checklist) dùng `sonnet` để tiết kiệm token. Alias `opus`/`sonnet` tự trỏ tới bản mới nhất. Đổi model = sửa frontmatter, không cần sửa lệnh.

Quy trình chung (`/feature`, `/bug`): **1 issue GitHub = 1 nhánh = 1 PR** (`Fixes #N`). Nhánh `feat/issue-N-<slug>`, `fix/issue-N-<slug>`, `chore/<slug>`. Issue tạo trước (mẫu `.github/ISSUE_TEMPLATE/feature.md` hoặc `bug.md`). Chỉ `/feature` và `/bug` tạo worktree; làm video không bao giờ tạo worktree. Hook vẫn chặn `git checkout`/`switch` ở repo gốc, merge bằng `/merge-pr`.

Người điều phối chọn **cấp** ở Phase 0, báo người dùng một dòng (người dùng đổi được) để không gọi thừa agent:

| Cấp | Khi nào | Vai trò | DR / cổng duyệt | Vòng sửa tối đa |
|-----|---------|---------|-----------------|-----------------|
| S | ≈ ≤3 file, không hành vi mới, không bảo mật | dev + tester | Không DR; nêu kế hoạch 2 dòng rồi làm | 1 |
| M | Hành vi mới trong một mảng | ba (DR ngắn) + dev + reviewer + tester; marketing chỉ khi có UI/video; techlead chỉ khi backend/hạ tầng/bảo mật | DR ngắn, dừng chờ duyệt | 1 |
| L | Nhiều mảng, bảo mật, kiến trúc, nhiều nhánh mở | Toàn bộ quy trình bên dưới | DR đầy đủ, dừng chờ duyệt | 2 |

Tiết kiệm token: một vòng Dev gom hết góp ý; chỉ chạy lại agent đã báo lỗi; dùng lại worktree/nhánh của issue; không gọi agent cho câu hỏi đọc file là trả lời được; giữa các agent chỉ chuyển đường dẫn (DR, spec), không dán tóm tắt dài; agent nền ghi kết quả ra file và trả tóm tắt ngắn.

Lệnh trong `agent/commands/`:

- `/feature <yêu cầu>` (cấp L đầy đủ; S/M cắt bớt vai trò theo bảng trên): issue → worktree + nhánh → **ba** viết DR (thêm **marketing** nếu người dùng/người xem thấy kết quả) → **dừng chờ người dùng duyệt** → **dev** → **reviewer + tester + marketing** song song, thêm **techlead** khi chạm backend/hạ tầng/bảo mật/hiệu năng/kiến trúc (tối đa 2 vòng sửa; bug không sửa trong vòng → issue qua `/bug`) → **ba** cập nhật tài liệu → báo cáo, hỏi trước khi commit/PR.
- `/bug <mô tả> | #<số>`: ghi bug thành **GitHub issue** (mẫu `.github/ISSUE_TEMPLATE/bug.md`, nhãn `bug` + `role:dev` + `role:tester` + `role:ba`, assignee là người dùng) → hỏi người dùng → **dev** sửa trong worktree `fix/issue-<số>-…` → **tester** (+ **reviewer**, **techlead** theo cấp) → **ba** ghi `TODO.md` → comment kết quả vào issue → hỏi trước khi commit/PR (`Fixes #<số>`). Bug tìm thấy trong `/feature` mà không sửa trong vòng đó cũng đi đường này.
- `/video-review [thư mục…]`: **marketing** review từng video (bỏ trống = mọi video Chờ duyệt) → bảng tổng hợp → người dùng chọn đề xuất → áp dụng qua API Studio (`PUT` + `render`), **không** tự duyệt.
- `/tech-audit <vùng>`: **techlead** audit hạ tầng, backend, bộ nhớ, bảo mật, kiến trúc → Bug thì ghi issue qua `/bug`, Nợ kỹ thuật thì **ba** ghi `TODO.md`.
- `/travel-review [thư mục…] | studio`: **marketing** review video du lịch (T1–T12) hoặc chức năng travel trên Studio.
- `/post-analytics [file số liệu]`: **marketing** phân tích số liệu TikTok Studio (người vận hành nhập, API không đọc được) → `storage/analytics/` → **ba** ghi điều rút ra vào `TODO.md`.
- `/dev-selfcheck`: sổ tay tự kiểm theo lớp của **dev** (agent tự dùng).
- `/sandbox-render <storage/videos/<thư mục>> [--revoice-all-edge] [--keep]`: dựng lại một video trên **bản sao** trong thư mục tạm (`scripts/sandbox_render.py`): không gọi Gemini, không duyệt, không Drive/Sheet, không ghi giáo trình bài tập; in JSON có `original_unchanged`. Dùng chung cho dev, tester, và người điều phối khi chuẩn bị bản sao cho marketing.
- `/audio-check <storage/videos/<thư mục>> [--scenes 1,2]`: khung hình + đo tiếng nổ ở chỗ nối (`scripts/audio_seams.py`, $0) + chép lời bằng Groq Whisper (`scripts/transcript_check.py`, 1 lượt Groq/cảnh) → `storage/review-frames/<thư mục>/`. Chỉ là tín hiệu: câu bị gắn cờ → "Cần người kiểm" (C-0004-3).
- Skill của agent khai báo ở trường `skills:` trong frontmatter, trỏ tới lệnh trong `agent/commands/` (không đặt ở `agent/skills/` vì `/sync` xoá). Ngoài các lệnh trên còn 2 skill chỉ để agent nạp: `voice-rules` (quy tắc giọng đọc, chỗ có thể gọi Gemini) và `dr-draft` (giữ số DR khi nhiều phiên song song, khung DR). Mỗi skill có dòng `Mã nạp: <tên>/<phiên bản>` ngay sau frontmatter để kiểm nạp sẵn; không đặt `disable-model-invocation: true`; agent luôn có câu "đọc `.claude/commands/<tên>.md` nếu chưa có trong ngữ cảnh" (C-0004-1). Các skill SSoT (`review`, `survey`, `fix`…) không gán cho agent vì cần `workflow_step.py` đang hỏng.
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
