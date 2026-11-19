# DR-0004: Gắn skill cho các agent vai trò (ba, dev, reviewer, techlead, tester, marketing)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| ✅ Đã duyệt (bản sửa sau duyệt, xem § Nhật ký thay đổi) | 2026-11-13, sửa 2026-11-16, 2026-11-19 | Claude (BA) | Người dùng: "Đồng ý" (theo mọi đề xuất của BA) |

Phạm vi: công cụ AI của dự án (`agent/`), không thuộc capability nào · Nhánh: `feat/agent-skills` · Worktree: `.worktrees/agent-skills`

Vai trò: **BA** = agent `ba` · **Dev** = agent `dev` · **Reviewer** = agent `reviewer` · **Tech Lead** = agent `techlead` · **Tester** = agent `tester` · **MKTG** = agent `marketing`.

**Vì sao số 0004**: kiểm lại ngày 2026-11-19 theo C-0004-4 (mọi ref local + remote qua `git for-each-ref`, đối chiếu `git ls-remote --heads origin` khớp ref remote; cộng thư mục `docs/decision-records/` của mọi worktree trong `git worktree list`, kể cả file chưa commit):

| Nơi | Số DR |
|-----|-------|
| `origin/main` 4e348dc (đã merge) | DR-0001-video-review-studio, DR-0002-travel-content, DR-0003-vung-an-toan-chu-tren-video, DR-0005-bdc-intro-video, DR-0008-travel-p1-fact-check-exit-codes, DR-0009-cat-clip-bai-tap-tren-studio, DR-0010-travel-story-video, DR-0011-duyet-truoc-khi-dung, DR-0012-gemini-tts-quota-fallback |
| `main` ở máy d0d1941 (chậm hơn `origin/main`) | như trên, trừ DR-0012 |
| Nhánh/worktree `feat/bdc-bai-2` (nháp) | DR-0006-bdc-bai-2-giuong-cung |
| Nhánh/worktree `feat/studio-create-video` (nháp) | DR-0007-studio-tao-video-san-pham |
| Worktree `agent-skills` (DR này, chưa commit) | DR-0004-skill-cho-agent-vai-tro |
| Nhánh `feat/gemini-quota`, `docs/sa_requirement_design`, tag `archive/docs-sa-requirement-design` | không có số mới (gemini-quota đã merge thành DR-0012) |

Số 0004 đã được file này giữ từ 2026-11-13 và không trùng ai, nên giữ nguyên. Số lớn nhất ở mọi nơi là 0012, nên số tiếp theo còn trống là **0013**. Việc trùng số 0002 trước đây đã xong: `clip-trim` đổi thành DR-0009, `gemini-quota` đổi thành DR-0012 (cả hai đã lên `main`). Hiện không còn số nào bị trùng.

---

## Bối cảnh

**Vấn đề gốc** (cập nhật theo `main` 88f6cc9):

1. Từ PR #10–#13, đã có 4 skill riêng của dự án: `dev-selfcheck` (dev), `tech-audit` (techlead), `travel-review` và `post-analytics` (marketing). Cả 4 là file lệnh trong `agent/commands/`, khai báo ở trường `skills:` trong frontmatter agent. `ba`, `reviewer` và `tester` vẫn chưa có skill nào. Những việc nhiều vai trò cùng làm (dựng thử trên bản sao, kiểm âm thanh, quy tắc giọng đọc) chưa có chỗ dùng chung. Mỗi lần người điều phối phải tự viết lại.
2. 17 skill SSoT tiếng Nhật trong `agent/skills/` đã bị xoá (PR #13), chỉ còn `agent/skills/README.md`. Quy ước mới trong `agent/CLAUDE.md`: "Skill của agent khai báo ở trường `skills:` trong frontmatter, trỏ tới lệnh trong `agent/commands/` (không đặt ở `agent/skills/` vì `/sync` xoá)". `sync.sh` không đụng tới `agents/` và `commands/`.
3. `dev-selfcheck` đã có phần "Chuẩn bị" (mktemp, `TTS_PROVIDER=edge`, `GEMINI_API_KEY=` …), giống khối "Môi trường cô lập" trong `tester.md`. Nhưng cả hai **chưa đủ** để dựng lại một thư mục có sẵn mà chắc chắn không tốn lượt Gemini (R-3) hay ghi vào giáo trình (G-1).

**Thiếu sót đã gặp thật** (nội dung cho skill mới):

| # | Vai trò | Thiếu gì | Bằng chứng |
|---|---------|----------|------------|
| G-1 | tester, dev | Không có cách dựng thử trên **bản sao** mà chắc chắn không gọi TTS, không duyệt, không Drive, không đánh dấu giáo trình | 2026-11-13: người điều phối phải tự viết script: copy thư mục, monkeypatch `demo.approval_step` trả `False`, cho `exercise.mark_done` ném lỗi, thay `exercise.LOCAL_CLIPS`. Lý do: `exercise.finish()` gọi `demo.approval_step` (hỏi y/n). Với `--skip-approval` thì nó gọi `mark_done`, ghi vào `content/exercise_curriculum.json` (file có trong git), rồi lên Drive nếu có `DRIVE_FOLDER_ID`. Khối biến môi trường của `dev-selfcheck` / `tester.md` không chặn được các bước này |
| G-2 | tester, marketing | Không bắt được chuyện giọng Gemini **đọc bịa** | Video trà ô long (2026-11-13): câu 2 tự thêm "mọi người có coi cái món trà mình mới mua hôm qua chưa… bán có 120 ngàn một túi", câu này không có trong lời. `TODO.md` § Giọng đọc còn mở việc "cân nhắc tự kiểm bằng Whisper (Groq)". MKTG không nghe được âm thanh nên hiện chỉ ghi "Cần người kiểm" |
| G-3 | tester, dev, marketing | Không có cách đo tiếng nổ ở chỗ chuyển cảnh | Burst ~40 ms ở −6 dB, cách mép cuối ~20 ms im lặng. Đã sửa ở `demo._trim_gemini_edges` + `clean_gemini_audio` (PR #9), nhưng cách đo chỉ nằm trong hội thoại |
| G-4 | dev, reviewer, techlead, tester | Quy tắc giọng đọc chưa được ghi cho agent | `dev.md` chỉ nhắc C-0001-1. Các điểm sau chưa ghi: chuỗi dự phòng `gemini_tts_models()`, `seg["tts_model"]`, model `-lite` đọc to chỉ dẫn đạo diễn (`exercise.py`, ghi chú trên `DEFAULT_TTS_MODEL`), và `revoice_changed()` dùng `script.json → tts_provider` chứ **không** theo biến `TTS_PROVIDER` (xem R-3). `techlead.md` có soát "gọi Groq/Gemini nhiều hơn cần" nhưng không có danh sách chỗ có thể gọi Gemini |
| G-5 | ba | Không có quy tắc đánh số DR khi nhiều phiên chạy song song | Lúc viết (2026-11-16) có 3 DR cùng dùng số 0002 (sau đó đã đổi thành DR-0009, DR-0012, xem bảng ở trên). `ba.md` chỉ ghi "số lớn nhất hiện có + 1", tức chỉ nhìn một thư mục |

**Lý do làm bây giờ**: người dùng yêu cầu 2026-11-13: "hãy tìm skill tương ứng phù hợp rồi làm theo /feature", rồi "hãy check lại xem phần các agent đã có skill tương ứng của nó chưa".

**Ràng buộc**:

- Chi phí **$0**. **Không** dùng lượt Gemini nào: không khi làm, không khi kiểm, và không skill nào được gọi Gemini.
- Không đổi `app.html` (C-0001-4). Không đổi hành vi `demo.py`, `exercise.py`, Studio. DR này chỉ thêm công cụ cho agent.
- Shopee tạm dừng. Kênh chưa có quyền affiliate. Hai việc này không liên quan trực tiếp tới DR.

**Thông tin Claude Code** (người điều phối đã đối chiếu tài liệu `sub-agents.md`, `skills.md` cho bản 2.1.323 cài trên máy):

- Frontmatter subagent có trường `skills` dạng danh sách YAML: "The full content of each listed skill is injected into the subagent's context at startup", tối đa 32 skill. Skill có `disable-model-invocation: true` thì không nạp sẵn được. Skill không tìm thấy thì bị bỏ qua, chỉ có một dòng log debug.
- Tài liệu xác nhận nạp sẵn từ `.claude/skills/<name>/SKILL.md`. Việc `skills:` trỏ tới file lệnh `.claude/commands/<name>.md` là **quy ước repo đang dùng**, tài liệu không ghi rõ và **chưa ai kiểm thực tế** (kể cả 4 skill đã có). V-1 kiểm việc này.
- Các agent đã có skill đều có sẵn câu dự phòng: "Nếu nội dung skill chưa có trong ngữ cảnh thì đọc file `.claude/commands/<tên>.md`" (`techlead.md`, `marketing.md`, `dev.md`). DR này dùng lại cách đó cho mọi agent.

---

## Quyết định

> **Skill riêng của dự án là file lệnh `agent/commands/<tên>.md` (= `.claude/commands/`), khai báo bằng trường `skills:` trong frontmatter agent, theo đúng quy ước đang có (`dev-selfcheck`, `tech-audit`…). `/sync` không ghi đè thư mục này (`agent/CLAUDE.md` § Git & hooks), nên không cần script kiểm sau sync. Tạo 4 skill mới không tiền tố: `sandbox-render`, `audio-check`, `voice-rules`, `dr-draft`, cùng 3 script hỗ trợ trong `scripts/`. `sandbox-render` là skill dùng chung (dev, tester, người điều phối); `dev-selfcheck` và `tester.md` trỏ sang nó thay vì tự lặp lại. Mỗi agent có câu "nếu skill chưa có trong ngữ cảnh thì đọc file". Không gắn skill SSoT hay skill bên ngoài nào.**

Trước khi coi là xong, phải kiểm nạp sẵn thực tế (V-1), cho cả skill mới lẫn 4 skill đã có. Nếu V-1 thất bại: không chép nội dung vào file agent, mà dựa vào câu "đọc file `.claude/commands/<tên>.md`" (đã có trong mọi agent sau DR này) và ghi kết quả vào § Kết quả + `agent/CLAUDE.md`.

---

## Các phương án

### Nơi đặt skill riêng

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | `agent/commands/<tên>.md` + `skills:` trong agent, giống 4 skill đã có | ⭐ | Đúng quy ước mới trên `main`. `/sync` không đụng `commands/`, nên bỏ được rủi ro bị xoá. Người dùng và người điều phối gõ được `/<tên>`. Điểm chưa chắc (nạp sẵn từ `commands/`) là điểm chung với 4 skill đã có, kiểm bằng V-1, và có câu dự phòng "đọc file" |
| B | `agent/skills/<tên>/SKILL.md` (phương án A của bản đã duyệt) | - | Đây là nơi tài liệu nói chắc chắn nạp sẵn được. Nhưng `agent/CLAUDE.md` giờ cấm đặt skill ở đây vì `/sync` chạy `rsync --delete` xoá mất. Phải thêm `check_agent_skills.py` và bước `git restore` chỉ để vá rủi ro đó. Đi ngược quy ước vừa thống nhất ở PR #13 |
| C | `.claude/skills` lồng trong thư mục con, hoặc plugin trong repo | - | Giữ nguyên lý do loại của bản đã duyệt: chỉ nạp khi đọc file trong thư mục con; plugin cần khai báo trong `settings.json` (bị sync ghi đè) hoặc `--plugin-dir` mỗi phiên; cả hai chưa xác minh với `skills:` |
| D | Không dùng skill, chép quy trình thẳng vào từng file agent | - | Cùng một nội dung (bản sao, kiểm âm thanh, quy tắc giọng) phải chép vào 3–4 file và dễ lệch nhau. Không còn cần làm dự phòng, vì câu "đọc file `.claude/commands/<tên>.md`" đã thay vai trò đó |

### Phần thử trên bản sao: skill riêng hay mở rộng `dev-selfcheck`

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| S-1 | Skill dùng chung `sandbox-render` (+ script `scripts/sandbox_render.py`). `dev-selfcheck` giữ phần "Chuẩn bị" cho lớp API và giao diện, còn dòng lớp Pipeline và mục hồi quy trỏ sang `sandbox-render`. `tester.md` § Môi trường cô lập giữ khối biến môi trường (dùng cho TestClient), thêm câu: dựng lại thư mục có sẵn thì dùng `sandbox-render` | ⭐ | Tester không phải nạp cả sổ tay theo lớp của dev (API, giao diện, kiểm chéo, phần lớn không dùng). Nội dung chặn Gemini, chặn giáo trình chỉ viết một chỗ. Người điều phối gõ `/sandbox-render` để chuẩn bị bản sao cho marketing (marketing không được chạy `demo.py`) |
| S-2 | Mở rộng `dev-selfcheck`, gắn nó cho cả tester | - | `dev-selfcheck` tự nhận là "sổ tay tự kiểm của agent `dev`". Gắn cho tester thì nạp thêm khoảng 44 dòng không liên quan, và giọng văn "Dev tự kiểm" lẫn với vai trò tester |
| S-3 | Không thêm gì, giữ khối biến môi trường ở 2 chỗ như hiện nay | - | Không giải quyết G-1. Khối biến môi trường không chặn được `revoice_changed()` gọi Gemini theo `script.json` (R-3), cũng không chặn `exercise.finish()` ghi giáo trình |

### Dùng skill có sẵn hay tạo mới

| Nguồn | Skill đã xét | Kết luận | Lý do |
|-------|--------------|----------|-------|
| Skill riêng đã có | `dev-selfcheck`, `tech-audit`, `travel-review`, `post-analytics` | Giữ nguyên chỗ gắn. Chỉ sửa `dev-selfcheck` (trỏ sang `sandbox-render`, `audio-check`) và thêm dòng `Mã nạp:` cho cả 4 | Đã đúng vai trò. Thêm dòng mốc để V-1 kiểm luôn 4 skill này |
| SSoT (`review`, `test-error`, `survey`, `spec-update`…) | — | Không gắn | Đã bị xoá khỏi repo (PR #13). Cần `workflow_step.py` đang hỏng |
| `~/Downloads/affiliate-skills-main` (MIT) | `content/tiktok-script-writer`, `meta/compliance-checker` | Không gắn | Viết cho thị trường Mỹ: CTA "link in bio" trái với hạng mục E của marketing, nhắm video 30–60 s trong khi dự án nhắm 20–30 s, `compliance-checker` xoay quanh FTC. Nằm ngoài repo. Giữ làm tài liệu tham khảo |
| Plugin chính thức (`claude-plugins-official`) | `code-review`, `pr-review-toolkit`, `claude-security`, `skill-creator` | Không gắn | Chưa cài hay bật. Bật plugin là thay đổi môi trường của người dùng (Q-3, mặc định "chưa cần") |
| Skill tự tạo | 4 skill bên dưới | ⭐ | Mỗi skill lấp đúng một thiếu sót G-1…G-5 và dùng được cho nhiều vai trò |

### Tên skill

Bỏ tiền tố `tta-`: tiền tố chỉ cần để tách khỏi skill SSoT cùng thư mục `agent/skills/`, mà nay skill nằm ở `commands/` và SSoT đã bị xoá. Tên theo kiểu `dev-selfcheck` (tiếng Anh ngắn, kebab-case). Đã đối chiếu không trùng 8 lệnh có sẵn (`bug`, `dev-selfcheck`, `feature`, `merge-pr`, `post-analytics`, `tech-audit`, `travel-review`, `video-review`). Chọn `audio-check` thay vì `video-qa` để không nhầm với `/video-review`.

### Script kiểm skill `check_agent_skills.py` (của bản đã duyệt)

**Bỏ.** Script này sinh ra để phát hiện `/sync` xoá `agent/skills/tta-*`; rủi ro đó không còn. Lỗi còn lại (gõ sai tên trong `skills:`) bắt bằng lệnh kiểm một dòng trong DD-2 và bằng V-1.

---

## Ánh xạ agent → skill

| Agent | Skill gắn (`skills:`) sau DR | Có sẵn / mới | Dùng để |
|-------|------------------------------|--------------|---------|
| `ba` | `dr-draft` | Mới | Giữ số DR khi nhiều phiên song song (G-5). Khung DR tiếng Việt theo văn phong DR-0001 |
| `dev` | `dev-selfcheck`, `sandbox-render`, `audio-check`, `voice-rules` | Có sẵn + 3 mới | Tự kiểm theo lớp. Dựng lại trên bản sao (G-1). Đo lại tiếng nổ và chép lời sau khi sửa phần audio (G-2, G-3). Quy tắc giọng khi sửa TTS (G-4) |
| `reviewer` | `voice-rules` | Mới | Soát C-0001-1, chuỗi model, chỗ có thể gọi Gemini ngoài ý muốn (G-4) |
| `techlead` | `tech-audit`, `voice-rules` | Có sẵn + 1 mới | Hạng mục "gọi Groq/Gemini nhiều hơn cần" và kiến trúc TTS có danh sách nguồn cụ thể (G-4) |
| `tester` | `sandbox-render`, `audio-check`, `voice-rules` | 3 mới | Môi trường cô lập dựng sẵn (G-1). Bằng chứng máy cho phần âm thanh (G-2, G-3). Biết lệnh nào có thể gọi Gemini (G-4) |
| `marketing` | `travel-review`, `post-analytics`, `audio-check` | 2 có sẵn + 1 mới | Có bản chép lời và số đo tiếng nổ, thay cho một phần "Cần người kiểm" (G-2, G-3). Không gắn `sandbox-render` vì marketing không chạy `demo.py`; bản sao do người điều phối chuẩn bị bằng `/sandbox-render`. Bảng chấm A–K **giữ trong `marketing.md`** |

Không tách bảng chấm marketing hay danh sách soát bảo mật của reviewer thành skill riêng, vì mỗi thứ chỉ một agent dùng.

---

## Nội dung từng skill mới

Quy ước chung (theo định dạng `dev-selfcheck.md`, `tech-audit.md`):

- File `agent/commands/<tên>.md`, viết tiếng Việt. Frontmatter chỉ có `description` (≤ 1.536 ký tự) và `argument-hint` nếu skill nhận đối số. Không có `name:` (tên lấy từ tên file). **Không** đặt `disable-model-invocation: true`, vì đặt thì không nạp sẵn được.
- Câu mở đầu nói rõ skill này là sổ tay của ai, như các skill đã có ("Skill này là **sổ tay dùng chung của `dev`, `tester`** …").
- Dòng mốc `Mã nạp: <tên>/1` nằm ngay sau frontmatter, dùng cho kiểm V-1. Thêm dòng mốc tương tự vào 4 skill đã có (`dev-selfcheck/1`, `tech-audit/1`, `travel-review/1`, `post-analytics/1`), không đổi gì khác trong `tech-audit`, `travel-review`, `post-analytics`.
- Dài tối đa khoảng 120 dòng, vì toàn văn được chèn vào ngữ cảnh agent mỗi lần chạy. Chi tiết dài để trong docstring của script.
- Lệnh trong skill gọi Python bằng `PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python`, chạy được cả ở repo gốc lẫn worktree.

### 1. `sandbox-render`: dựng thử trên bản sao (G-1, dùng chung dev, tester, người điều phối)

- **Mục đích**: dựng lại một video trong thư mục tạm. Không gọi TTS, không duyệt, không Drive, không Sheet, không ghi `content/exercise_curriculum.json`, không đụng `storage/` thật.
- **`argument-hint`**: `<storage/videos/<thư mục>> [--revoice-all-edge] [--keep]`.
- **Script hỗ trợ (mới)**: `scripts/sandbox_render.py <thư mục video> [--revoice-all-edge] [--keep]`
  1. Tạo thư mục tạm `T` và chép thư mục video sang `T/storage/videos/<tên>`. Nếu `product.json` có ảnh là đường dẫn tương đối (không phải URL, không nằm trong thư mục video) thì chép ảnh đó sang `T` theo cùng đường dẫn tương đối.
  2. **Chạy với thư mục làm việc là `T`**. Khi đó không có `.env` hay `google-credentials.json`, nên `load_env()` không nạp khoá nào và `set_sheet_status()` tự bỏ qua. Script còn đặt rõ `GEMINI_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= TTS_PROVIDER=edge APPROVAL_MODE=web`.
  3. **Video sản phẩm** (có `product.json`): trước khi chạy, nếu có câu `line != audio_line` mà không có `--revoice-all-edge` thì **dừng** (exit ≠ 0), liệt kê số cảnh và gợi ý dùng `--revoice-all-edge`. Lý do: `revoice_changed()` đọc lại bằng `script.json → tts_provider` chứ không theo biến môi trường (R-3). Không có gì cần đọc lại thì chạy `demo.py --render-only <bản sao>` bằng subprocess (giống Studio, C-0001-2). Có `--revoice-all-edge` thì thêm `--revoice-all edge`.
  4. **Video bài tập** (không có `product.json`, `script.json` có `series_id`): chép `content/exercise_curriculum.json` và `storage/clips/<series_id>/` sang `T`. Import `demo` và `exercise` từ code của worktree, rồi monkeypatch: `demo.approval_step` → trả `False`, `exercise.mark_done` → ném lỗi, `demo.move_to_drive` → ném lỗi. Sau đó gọi `exercise.rerender(bản sao, skip_approval=False)`. Kết quả mong đợi là `status=rejected` ngay sau khi dựng xong, nên không tới được `mark_done` hay Drive.
  5. In ra JSON gồm: `sandbox_dir`, `status`, đường dẫn `video.mp4` trong bản sao, thời lượng, danh sách `audio_N.mp3` đã đổi (so hash trước và sau), và `original_unchanged: true/false` (so hash mọi file của thư mục gốc trước và sau).
  6. Xoá `T` khi xong, trừ khi có `--keep` (tester cần giữ để xem tiếp bằng `audio-check`).
- **Ghi chú trong skill**: thư mục cũ thiếu `tts_provider` thì `clean_gemini_audio` coi là `gemini` và có thể cắt lại audio trong bản sao (chỉ chạy ffmpeg tại máy, không gọi mạng), nên audio của bản sao có thể khác bản gốc. Ảnh là URL thì vẫn tải từ mạng, $0. Test API Studio (TestClient) hay tạo video mới bằng `--product` thì vẫn dùng khối biến môi trường trong `dev-selfcheck` / `tester.md`; skill này chỉ thay phần dựng lại thư mục có sẵn.

### 2. `audio-check`: kiểm âm thanh bằng máy (G-2, G-3, dùng chung tester, marketing, dev)

- **Mục đích**: lấy bằng chứng máy cho phần agent không nghe được. Kết quả chỉ là **tín hiệu**. Câu bị gắn cờ vẫn chuyển thành "Cần người kiểm", không tự kết luận đạt hay hỏng phần nghe (C-0004-3).
- **`argument-hint`**: `<storage/videos/<thư mục>> [--scenes 1,2]`. Người dùng gõ `/audio-check <thư mục>` được.
- **Bước 1. Khung hình** (đã có): `$PY scripts/review_frames.py <thư mục>` tạo `storage/review-frames/<thư mục>/`.
- **Bước 2. Tiếng nổ ở chỗ nối, script mới `scripts/audio_seams.py <thư mục>`** ($0, chạy tại máy):
  - Giải mã audio của `video.mp4` sang PCM mono bằng ffmpeg của `imageio_ffmpeg`. Mốc nối lấy từ `script.json`: mỗi cảnh dài `duration + GAP` (cảnh cuối cộng thêm `END_HOLD`), dùng lại `scene_spans()` của `review_frames.py` hoặc import `GAP`/`END_HOLD` từ `demo.py` để số liệu không lệch nhau.
  - Ở mỗi mốc, tính RMS theo cửa sổ 20 ms trong đoạn từ 400 ms trước khi hết lời đến hết `GAP`. Dùng **đúng ngưỡng của `_trim_gemini_edges`**: im lặng ≤ −35 dB, tiếng nổ > −30 dB, sau đó phải có cửa sổ < −45 dB. Gắn cờ khi có một đoạn ồn ngắn (≤ 8 cửa sổ) tách khỏi lời đọc bằng khoảng lặng.
  - Ghi `storage/review-frames/<thư mục>/seams.json` (bản sao: `<thư mục>__sandbox/`, JSON có `"sandbox": true`) và in bảng: cảnh, thời điểm, dB lớn nhất ở đuôi, `OK` hoặc `Nghi tiếng nổ`.
  - Có thêm cờ `--audio-files` để đo từng `audio_N.mp3` riêng lẻ (Dev dùng sau khi sửa phần cắt).
- **Bước 3. Chép lời bằng Whisper, script mới `scripts/transcript_check.py <thư mục> [--scenes 1,2]`**:
  - Với mỗi `audio_N.mp3`: gọi Groq `whisper-large-v3` qua `https://api.groq.com/openai/v1/audio/transcriptions`, ngôn ngữ `vi`. Khoá là `GROQ_API_KEY`, đọc từ `.env` của repo gốc (không in khoá ra log). Không thêm biến môi trường mới. Model đổi được bằng cờ `--model`.
  - So bản chép với `audio_line` (thiếu thì dùng `line`). Trước khi so, chuẩn hoá: chữ thường, bỏ dấu (NFD bỏ dấu, `đ` → `d`), bỏ dấu câu. Nhờ vậy lỗi dấu của Whisper như "đọng" → "động" không bị coi là khác.
  - Gắn cờ **Nghi đọc bịa** khi bản chép có một chuỗi từ liên tiếp không có trong lời, dài ≥ `--extra-words` (mặc định 4, chỉnh lại theo D-9 và D-8). Cũng gắn cờ khi bản chép có con số (chữ số, hoặc chữ "trăm/ngàn/nghìn/triệu/k") mà lời không có. Gắn cờ **Nghi đọc thiếu** khi một chuỗi ≥ 4 từ của lời không có trong bản chép.
  - Ghi `storage/review-frames/<thư mục>/transcript.json` (bản sao: `<thư mục>__sandbox/`) (bản chép, đoạn thừa, đoạn thiếu cho từng cảnh) và in bảng tóm tắt. File nằm ngoài thư mục video nên không bị đẩy lên Drive.
  - Lỗi mạng, thiếu khoá hay HTTP 429 thì báo rõ và exit ≠ 0, không ghi kết quả nửa vời là đạt.
- **Cách dùng theo vai trò** (ghi trong skill): tester gắn kết quả vào cột bằng chứng. Marketing đưa đoạn bị gắn cờ vào mục "Cần người kiểm" của `marketing-review.md` kèm câu trích, và hạng mục C ("Không bịa") xét cả **lời thực đọc**. Marketing chỉ được gọi Groq qua `transcript_check.py` (người dùng đã đồng ý ở Q-1). Dev chạy Bước 2 sau mỗi thay đổi ở phần cắt hay ghép audio.

### 3. `voice-rules`: quy tắc giọng đọc (G-4, dùng chung dev, reviewer, techlead, tester)

- **Mục đích**: danh sách quy tắc để làm và soát, không có script, không nhận đối số.
- **Nội dung** (mỗi ý kèm tên hàm hoặc file làm nguồn):
  1. Một video dùng một engine và một model (C-0001-1). `generate_voiceovers` thử lần lượt `gemini_tts_models()` = `GEMINI_TTS_MODEL` → `GEMINI_TTS_FALLBACK_MODELS` → edge-tts. Model nào lỗi thì **đọc lại cả video** bằng model kế tiếp, không ghép.
  2. `seg["tts_model"]` ghi model đã dùng. `revoice_changed()` đọc lại câu sửa bằng đúng `tts_provider` và model đó. Lỗi thì không đổi file nào (exit 3), Studio đưa lựa chọn `--revoice-all edge`.
  3. `revoice_changed()` lấy engine từ `script.json → tts_provider`, **không** theo `TTS_PROVIDER`. Khi kiểm thì luôn để trống `GEMINI_API_KEY`, hoặc dùng `sandbox-render`.
  4. Quota: mỗi model Gemini TTS free 10 lượt/ngày (`.env.example`, thông báo lỗi trong `_gemini_tts`). Video sản phẩm dùng `gemini-3.8-flash-tts`. Video bài tập dùng `gemini-3.1-flash-tts-preview` (động tác, `exercise.DEFAULT_TTS_MODEL`) và `gemini-2.5-flash-preview-tts` (mở đầu, tổng kết, `exercise.EXTRA_TTS_MODEL`). Hai model dự phòng của video sản phẩm chính là model của video bài tập, nên dùng chung lượt. **Không gọi Gemini khi kiểm.**
  5. Không dùng model `-lite`: nó đọc to phần chỉ dẫn đạo diễn (`exercise.py`, ghi chú trên `DEFAULT_TTS_MODEL`, 2026-11-12). Prompt phải giữ khung `AUDIO PROFILE / DIRECTOR'S NOTES / TRANSCRIPT` (`_gemini_tts_prompt`).
  6. Tiếng nổ ở mép: `_trim_gemini_edges` cắt tiếng click đầu clip và tiếng nổ cuối clip. `clean_gemini_audio` làm sạch lại audio cũ khi dựng lại mà không gọi TTS. `render_video` thêm fade 15 ms ở đầu và 30 ms ở cuối. Sửa phần này thì kiểm bằng `audio-check` Bước 2.
  7. Gemini có thể đọc thêm câu không có trong lời (vụ trà ô long). Sửa prompt TTS thì kiểm bằng `audio-check` Bước 3 trên audio **đã có**, không tạo audio mới.
  8. Chọn giọng: `choose_persona` (điện tử, máy móc, ô tô, thể thao → `nam_bac`; còn lại → `nu_nam`). Ép giọng bằng `GEMINI_TTS_PERSONA`.

### 4. `dr-draft`: đánh số và khung DR (G-5, cho ba)

- **Mục đích**: không còn 2 DR trùng số giữa các phiên chạy song song. Viết DR tiếng Việt cùng khung với DR-0001.
- **`argument-hint`**: `<tiêu đề ngắn của DR>`.
- **Bước giữ số**:
  1. `git -C <repo gốc> fetch -q` (chỉ lấy về, không checkout). Fetch lỗi thì vẫn làm tiếp với ref đã có và ghi "chưa fetch được" vào DR.
  2. Liệt kê mọi số DR đang có ở: mọi ref local và remote (`git ls-tree -r --name-only <ref> -- docs/decision-records`), `docs/decision-records/` của repo gốc và của mọi `.worktrees/*/`, kể cả file chưa commit. Lệnh mẫu một dòng đặt sẵn trong skill.
  3. Số mới = số lớn nhất + 1. **Tạo file DR ngay**, có tiêu đề và trạng thái 📋, để các phiên khác thấy số đó đã có người dùng.
  4. Trước khi merge, chạy lại bước 2. Nếu trùng số với DR đã lên `main` thì đổi số DR **chưa** merge (DR đã merge thì không sửa). Đổi cả tên file lẫn mọi `C-XXXX-n` bên trong.
  5. Thấy trùng số giữa các bản nháp hoặc giữa nháp và `main` (như DR-0002 hiện nay) thì ghi vào báo cáo cho người điều phối, không tự đổi DR của nhánh khác.
- **Khung**: bảng ánh xạ tiêu đề mục của mẫu tiếng Nhật `.claude/references/templates/dr-workplan-template.md` sang tiêu đề tiếng Việt DR-0001 đang dùng (Bối cảnh / Quyết định / Các phương án / Thay đổi cấu trúc / Kế hoạch công việc / Rủi ro và giả định / Ràng buộc mới / Tài liệu SSoT bị ảnh hưởng / Tiêu chí hoàn thành (DoD) / Những gì KHÔNG làm / Câu hỏi mở / Kết quả / Liên quan), kèm quy tắc kiểm được cho từng dòng D-n và vai trò Tech Lead khi chạm backend, hạ tầng, bảo mật, hiệu năng, kiến trúc.

---

## Thay đổi cấu trúc

### Dữ liệu / file

| Đối tượng | Trước | Sau | Lý do |
|-----------|-------|-----|-------|
| Frontmatter `agent/agents/*.md` | `dev`, `techlead`, `marketing` có `skills:`; `ba`, `reviewer`, `tester` chưa có | 6 agent có `skills:` theo bảng ánh xạ | Nạp sẵn skill khi agent khởi động |
| `agent/commands/` | 8 lệnh | Thêm `sandbox-render.md`, `audio-check.md`, `voice-rules.md`, `dr-draft.md`. Sửa `dev-selfcheck.md`; thêm dòng `Mã nạp:` vào `tech-audit.md`, `travel-review.md`, `post-analytics.md`; sửa `feature.md`, `video-review.md` | G-1…G-5, V-1 |
| `scripts/` | `review_frames.py`, `branch_observer.py`… | Thêm `sandbox_render.py`, `audio_seams.py`, `transcript_check.py` | Skill gọi script, không chép code vào skill |
| `storage/review-frames/<thư mục>/` | Khung hình + `facts.json` | Thêm `seams.json`, `transcript.json`; bản sao ghi vào `<thư mục>__sandbox/` | Đã gitignored, không lên Drive |

### Luồng

```
/feature
  Phase 1  ba ── dr-draft ──► giữ số DR (quét main + nhánh + worktree) → tạo file DR ngay
  Phase 3  dev ── dev-selfcheck (theo lớp) · sandbox-render (dựng lại) · audio-check (đo lại audio) · voice-rules (sửa TTS)
  Phase 4  reviewer ── voice-rules (soát)
           techlead ── tech-audit · voice-rules (khi chạm TTS / chi phí gọi API)
           tester ── sandbox-render --keep → audio-check trên bản sao → bảng PASS/FAIL/Cần người kiểm
           người điều phối ── /sandbox-render --keep → giao bản sao cho marketing
           marketing ── audio-check (khung hình + tiếng nổ + chép lời) → marketing-review.md
/video-review
  marketing ── audio-check → mục "Cần người kiểm" có câu trích Whisper thay vì chỉ "nghe toàn bộ"
```

---

## Kế hoạch công việc

Dev chia được thành **2 nhóm không đụng chung file**, làm song song được. Nhóm B dùng tên script và tên cờ đúng như § Nội dung; xong cả hai nhóm thì Dev đối chiếu `--help` của từng script với chữ trong skill (DD-1).

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| A1 | `sandbox_render.py` (sản phẩm và bài tập, chặn đọc lại bằng Gemini, so hash bản gốc) | Dev (nhóm A) | §Nội dung 1 | Script | `scripts/sandbox_render.py` |
| A2 | `audio_seams.py` (ngưỡng lấy từ `_trim_gemini_edges`, mốc nối lấy từ `script.json`) | Dev (nhóm A) | §Nội dung 2 | Script | `scripts/audio_seams.py` |
| A3 | `transcript_check.py` (Groq Whisper, so khớp bỏ dấu, gắn cờ bịa/thiếu/số lạ; ghi giới hạn free của Groq vào docstring theo tài liệu chính thức, R-5) | Dev (nhóm A) | §Nội dung 2 | Script | `scripts/transcript_check.py` |
| B1 | Viết 4 skill mới (dòng mốc, ≤ ~120 dòng, tiếng Việt, định dạng như `dev-selfcheck.md`) | Dev (nhóm B; BA soát chữ) | §Nội dung 1–4 | Skill | `agent/commands/{sandbox-render,audio-check,voice-rules,dr-draft}.md` |
| B2 | Sửa skill đã có: `dev-selfcheck.md` (dòng lớp Pipeline và mục hồi quy trỏ sang `sandbox-render`; thêm dòng "sửa phần audio → `audio-check` Bước 2"; phần Chuẩn bị giữ cho API/giao diện). Thêm dòng `Mã nạp: <tên>/1` vào `dev-selfcheck.md`, `tech-audit.md`, `travel-review.md`, `post-analytics.md` | Dev (nhóm B) | §Phương án S-1, §Quy ước chung | Skill | `agent/commands/*.md` |
| B3 | Thêm hoặc bổ sung `skills:` cho 6 agent theo bảng ánh xạ. Mỗi skill có câu "nếu nội dung chưa có trong ngữ cảnh thì đọc `.claude/commands/<tên>.md`" như `techlead.md`. Sửa câu chữ: `tester.md` § Môi trường cô lập thêm câu trỏ `sandbox-render`; `marketing.md` thay "Không gọi Groq hay Gemini" bằng "Chỉ gọi Groq qua `scripts/transcript_check.py`; không gọi Gemini, không chạy `demo.py`", mẫu "Cần người kiểm" dùng kết quả `audio-check`, "Trả về" thêm số lượt Groq đã dùng; `ba.md` thay "Số DR = số lớn nhất hiện có + 1" bằng tham chiếu `dr-draft`; `reviewer.md`, `techlead.md` mục chi phí trỏ `voice-rules` | Dev (nhóm B) | Bảng ánh xạ | File agent | `agent/agents/*.md` |
| B4 | `video-review.md` Bước 3: thêm cột "Lượt Groq". `feature.md` Phase 1: BA giữ số DR theo `dr-draft`; Phase 4: người điều phối chuẩn bị bản sao cho marketing bằng `/sandbox-render --keep` | Dev (nhóm B) | B3 | Command | `agent/commands/{video-review,feature}.md` |
| B5 | `agent/CLAUDE.md` § Đội vai trò: ghi skill của từng agent trong bảng (như dòng `dev`, `techlead` đang có); thêm `/sandbox-render`, `/audio-check` vào danh sách lệnh; thêm `voice-rules`, `dr-draft` vào câu về skill của agent | Dev (nhóm B) | B1–B4 | Docs agent | `agent/CLAUDE.md` |
| 8 | Soát diff: không đổi `demo.py`, `exercise.py`, `backend/`, `app.html`; script không gọi Gemini; không ghi vào `storage/videos/` thật; khoá Groq không lọt ra log; không có file mới trong `agent/skills/` | Reviewer | A1–B5 | Bảng phát hiện | DR §Kết quả |
| 9 | Soát `transcript_check.py` (gửi audio ra Groq, xử lý khoá, timeout) và `sandbox_render.py` (subprocess, monkeypatch, dọn thư mục tạm) | Tech Lead | A1–A3 | Bảng phát hiện | DR §Kết quả |
| 10 | Test theo D-1…D-13 trên **bản sao**; tạo mẫu lỗi tổng hợp bằng edge-tts/ffmpeg ($0) | Tester | A1–B5 | Bảng PASS/FAIL | DR §Kết quả |
| 11 | Kiểm nạp sẵn thực tế V-1 trong một phiên Claude Code **mở tại worktree** | Người điều phối (+ người dùng mở phiên) | B1–B3 | Bằng chứng V-1 | DR §Kết quả |
| 12 | MKTG chạy thử `/video-review` với `audio-check` trên bản sao 1 video, góp ý báo cáo có dễ đọc không | MKTG | A3, B3 | Góp ý | DR §Kết quả |
| 13 | Cập nhật tài liệu SSoT | BA | 1–12 | Docs | §Tài liệu SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | `skills:` trỏ tới `.claude/commands/<tên>.md` không được nạp sẵn (tài liệu chỉ xác nhận `.claude/skills/`; symlink `.claude → agent`; phiên bản Claude Code). Rủi ro này đã có với 4 skill hiện tại | Skill không vào ngữ cảnh, agent làm thiếu bước | V-1 bắt buộc, kiểm cả 4 skill đã có. Mọi agent có câu "đọc file `.claude/commands/<tên>.md` nếu chưa có trong ngữ cảnh". Thất bại thì ghi vào §Kết quả và `agent/CLAUDE.md`; muốn chuyển sang `.claude/skills/` thì cần DR mới (xung đột với `/sync`) |
| R-2 | Rủi ro | Lệnh `/sandbox-render`, `/audio-check` hiện trong menu `/` của người dùng | Người vận hành gõ nhầm | Không hại: cả hai chỉ đọc thư mục thật, ghi vào thư mục tạm hoặc `storage/review-frames/`. `audio-check` Bước 3 tốn lượt Groq free (R-5) |
| R-3 | Rủi ro | `revoice_changed()` gọi Gemini theo `script.json → tts_provider` dù đã đặt `TTS_PROVIDER=edge`, nếu bản sao có câu đã sửa và còn `GEMINI_API_KEY` | Tốn lượt Gemini của người vận hành | `sandbox_render.py` chạy ở cwd tạm, không có `.env`, đặt `GEMINI_API_KEY=` rỗng, và dừng trước nếu có câu cần đọc lại mà không có `--revoice-all-edge` (D-2) |
| R-4 | Rủi ro | Whisper chép sai hoặc tự "ảo giác" ở đoạn im lặng, gây báo nhầm | Người dùng phải nghe lại câu không có lỗi | Kết quả chỉ là tín hiệu (C-0004-3). Ngưỡng `--extra-words` chỉnh theo D-8/D-9. Báo nhầm thì vẫn chỉ tốn công nghe một câu |
| R-5 | Rủi ro | Hạn mức free của Groq cho Whisper: **chưa rõ** (repo và `.env.example` không ghi) | Gọi nhiều có thể bị 429, chen vào lượt Groq dùng để viết kịch bản | Mỗi video gọi bằng số câu (4–10). Dev đọc tài liệu chính thức của Groq và ghi giới hạn vào docstring. 429 thì exit ≠ 0, báo rõ (D-11) |
| R-6 | Rủi ro | Mỗi skill nạp sẵn làm dài ngữ cảnh của agent | Tốn token, agent chậm hơn | Mỗi skill mới ≤ ~120 dòng, chi tiết để trong script. Mỗi agent nhiều nhất 4 skill (`dev`) |
| R-7 | Rủi ro | `sandbox-render` và khối biến môi trường trong `dev-selfcheck` / `tester.md` lệch nhau theo thời gian | Hai cách chuẩn bị khác nhau | Khối biến môi trường chỉ dùng cho API/giao diện/tạo video mới; dựng lại thư mục có sẵn luôn qua `sandbox-render` (B2, B3). Reviewer soát câu trỏ |
| A-1 | Giả định | Phiên điều phối chạy ở repo gốc nạp `agent/` của **`main`**, nên skill mới chỉ có hiệu lực sau khi merge | Không kiểm được trong phiên hiện tại | V-1 chạy trong phiên Claude Code mở tại `.worktrees/agent-skills` (symlink `.claude → agent` có trong worktree) |
| A-2 | Giả định | Không còn file audio gốc của vụ trà ô long (thư mục không có trong `storage/videos/`) | Không có mẫu lỗi thật cho Whisper | Tester tạo mẫu tổng hợp ($0): edge-tts đọc lời + câu thừa có số, `audio_line` giữ lời gốc (D-9). Có file từ Drive thì thêm ca test (Q-4) |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0004-1 | Skill riêng của dự án là file `agent/commands/<tên>.md`, gắn cho agent bằng `skills:`. Không đặt ở `agent/skills/`. Tên kebab-case, không trùng lệnh có sẵn. Có dòng `Mã nạp: <tên>/<phiên bản>` ngay sau frontmatter. Không đặt `disable-model-invocation: true` | `/sync` xoá `agent/skills/`; dòng mốc để kiểm nạp sẵn; `disable-model-invocation` chặn nạp sẵn | `agent/commands/`, `agent/agents/*.md` | Khi V-1 cho thấy `commands/` không nạp sẵn được và có DR mới chọn nơi khác |
| C-0004-2 | Skill và script cho agent không gọi Gemini, không ghi vào `storage/videos/` thật, Drive, Sheet hay `content/exercise_curriculum.json`. Muốn dựng thì dựng trên bản sao trong thư mục tạm | Quota Gemini 10 lượt/ngày của người vận hành; dữ liệu thật không quay lại được | `scripts/sandbox_render.py`, `audio_seams.py`, `transcript_check.py`, 4 skill mới | — |
| C-0004-3 | Kết quả Whisper và đo tiếng nổ chỉ là tín hiệu. Phần nghe không được đánh PASS hay "Đạt" chỉ dựa vào máy. Câu bị gắn cờ → "Cần người kiểm" kèm câu trích | Whisper sai dấu và có thể ảo giác; agent không nghe được | tester, marketing, dev | Khi có kiểm chứng tỉ lệ báo đúng/sai trên nhiều video (DR mới) |
| C-0004-4 | Số DR mới = số lớn nhất trên mọi ref local/remote và mọi worktree + 1. Tạo file ngay khi lấy số. Trùng số thì đổi DR chưa merge; DR đã lên `main` giữ số | Tránh trùng như DR-0002 hiện nay; DR đã merge không được sửa | agent `ba`, `dr-draft` | — |
| C-0004-5 | Script kiểm chỉ đọc thư mục video. Kết quả ghi vào `storage/review-frames/<thư mục>/` (video thật), `storage/review-frames/<thư mục>__sandbox/` (bản sao) hoặc thư mục tạm; từ chối `--out-dir` trong thư mục video hay `storage/videos/` | Không làm bẩn thư mục sẽ được đẩy lên Drive | `audio_seams.py`, `transcript_check.py` | — |

supersedes: —

(Ràng buộc DR-0001 giữ nguyên, nhất là C-0001-1 và C-0001-2: `sandbox_render.py` gọi `demo.py` bằng subprocess cho video sản phẩm. Riêng video bài tập phải import vì cần monkeypatch. Đây là script kiểm, không phải service `api/studio.py`, nên không thuộc phạm vi C-0001-2.)

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `agent/CLAUDE.md` | § Đội vai trò: skill của từng agent; lệnh `/sandbox-render`, `/audio-check`; câu về skill của agent nhắc C-0004-1 (dòng mốc). Không đổi § Git & hooks (quy ước `commands/` đã đúng) | [ ] |
| `TODO.md` | Việc "tự kiểm bằng Whisper" → đã có công cụ cho agent (chưa tự động trong pipeline). Ghi quyết định DR-0004. Ghi việc còn mở: `clip-trim` và `gemini-quota` phải đổi số DR trước khi merge | [ ] |
| `agent/agents/*.md`, `agent/commands/*.md` | Dev sửa theo B1–B4. BA đối chiếu khi cập nhật Kết quả | [ ] |
| `agent/skills/README.md` | Danh sách lệnh/skill thực tế: thêm 4 skill mới (chỉ sửa README, không thêm file khác vào `agent/skills/`; `/sync` có thể xoá README này, không sao) | [ ] |
| `docs/specs/architecture/capabilities/video-render.md` | Không đổi hành vi dựng. Chỉ thêm một dòng tham chiếu `audio_seams.py` ở phần giọng đọc nếu spec có mục đó | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | **Không đổi**: người vận hành không dùng agent | — |
| `.env.example` | **Không đổi**: Whisper dùng `GROQ_API_KEY` đã có, không thêm biến | — |

## File thay đổi

- [ ] Nhóm A (mới): `scripts/sandbox_render.py`, `scripts/audio_seams.py`, `scripts/transcript_check.py`
- [ ] Nhóm B (mới): `agent/commands/sandbox-render.md`, `audio-check.md`, `voice-rules.md`, `dr-draft.md`
- [ ] Nhóm B (sửa): `agent/commands/dev-selfcheck.md`, `tech-audit.md`, `travel-review.md`, `post-analytics.md` (chỉ dòng mốc với 3 file sau), `feature.md`, `video-review.md`
- [ ] Nhóm B (sửa): `agent/agents/{ba,dev,reviewer,techlead,tester,marketing}.md`, `agent/CLAUDE.md`
- [ ] BA (sửa, sau khi xong): `TODO.md`, `agent/skills/README.md`, có thể `docs/specs/architecture/capabilities/video-render.md`
- Không đổi: `demo.py`, `exercise.py`, `product_sources.py`, `drive_upload.py`, `backend/`, `app.html`, `scripts/review_frames.py`, `scripts/branch_observer.py`, `agent/settings.json`, `agent/settings.local.json`, `agent/scripts/sync.sh`, `agent/hooks/`. Không tạo file hay thư mục mới trong `agent/skills/`

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: code (script)

Mọi ca chạy trên **bản sao** trong thư mục tạm, không có `.env`, không gọi Gemini. "Hash bản gốc" nghĩa là `shasum` mọi file trong thư mục `storage/videos/<mẫu>` của repo gốc, so trước và sau.

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1 | Bình thường: `sandbox_render.py` trên thư mục sản phẩm không có câu sửa (vd `20261111_114841_bot-me-den`) | Exit 0. JSON có `status=review`, `original_unchanged=true`. Log không có dòng "Generating voiceover" hay "Re-voicing". Không có `post.txt` trong bản sao. Thư mục tạm bị xoá (không `--keep`) | Chạy thật; so hash bản gốc; `grep` log |
| D-2 | Lỗi: bản sao có `segments[1].line != audio_line`, `tts_provider=gemini`, không `--revoice-all-edge` | Dừng **trước** khi chạy `demo.py`, exit ≠ 0, báo "cảnh 2" + gợi ý `--revoice-all-edge`. Không file nào đổi | Sửa `script.json` trong một bản sao mẫu rồi chạy; so hash |
| D-3 | Như D-2 nhưng có `--revoice-all-edge` | Exit 0. Mọi `audio_N.mp3` trong bản sao đều đổi (hash khác), `tts_provider=edge`. Bản gốc không đổi | Chạy thật (edge, $0) |
| D-4 | Bình thường: thư mục bài tập `20261112_143304_baitap_bdc_00_gioithieu` | `status=rejected` sau khi dựng; có `video.mp4` mới trong bản sao. `content/exercise_curriculum.json` và `storage/clips/` của repo **không đổi** (hash). Không hỏi y/n (chạy với stdin đóng `</dev/null` không bị treo). Không gọi TTS | Chạy thật; so hash; `timeout` |
| D-5 | Biên: đường dẫn không tồn tại / thư mục không có `script.json` / thư mục có dấu cách hoặc tiếng Việt có dấu | 2 ca đầu: exit ≠ 0 với thông báo rõ. Ca cuối: chạy bình thường | Chạy thật |
| D-6 | Biên: `product.json` có ảnh là đường dẫn tương đối ngoài thư mục video | Ảnh được chép sang thư mục tạm, khung hình cảnh sản phẩm có ảnh (không phải nền trống) | Bản sao sửa `images` trỏ tới một file mẫu; xem khung bằng `review_frames.py` |
| D-7 | Bình thường: `audio_seams.py` trên video đã làm sạch (bản sao `bot-me-den_gemini_nam` sau khi qua D-1) | Mọi mốc `OK`; có `seams.json` trong `storage/review-frames/<thư mục>__sandbox/` (vì là bản sao, JSON `"sandbox": true`); thư mục video không đổi | Chạy thật; so hash |
| D-8 | Lỗi có chủ ý: bản sao có `audio_1.mp3` được nối thêm 20 ms im lặng + 40 ms sóng sin ở −6 dBFS vào cuối (tạo bằng ffmpeg), rồi dựng bằng D-1 | Mốc sau cảnh 2 (index 1) bị gắn `Nghi tiếng nổ`; các mốc khác `OK` | Chạy thật |
| D-9 | Lỗi có chủ ý (Whisper): bản sao có `audio_1.mp3` = edge-tts đọc `line` + câu "mọi người có coi cái món trà mình mới mua hôm qua chưa, bán có 120 ngàn một túi"; `audio_line` giữ lời gốc | Cảnh 2 gắn `Nghi đọc bịa`, trích được đoạn thừa và số `120`/"ngàn". Các cảnh còn lại không có cờ bịa | Chạy thật (Groq, $0) |
| D-10 | Biên (so khớp): hàm so khớp nhận lời "nước đọng lại" và bản chép "nước động lại"; lời "giá 189.000đ" và bản chép "giá một trăm tám mươi chín nghìn đồng" | Ca 1: không gắn cờ (khác dấu). Ca 2: ghi lại kết quả thực tế. Nếu bị gắn cờ số lạ thì Dev quyết định xử lý và ghi vào DR §Kết quả (đọc số thành chữ là chuyện bình thường của TTS) | Gọi hàm so khớp trực tiếp bằng Python, không gọi mạng |
| D-11 | Lỗi: không có `GROQ_API_KEY` / khoá sai / mạng lỗi | Exit ≠ 0, thông báo rõ, không ghi `transcript.json` kiểu "đạt". Khoá không xuất hiện trong output | Chạy với `GROQ_API_KEY=` và `GROQ_API_KEY=invalid` |
| D-12 | Biên: `audio_seams.py --audio-files` và `transcript_check.py --scenes 1` trên thư mục bài tập (không có `product.json`) | Chạy được, chỉ đo/chép đúng các file được chọn; `transcript_check.py --scenes 1` gọi Groq đúng 1 lần (đếm trong log) | Chạy thật trên bản sao |
| D-13 | Hồi quy | `git diff origin/main --stat` không có `demo.py`, `exercise.py`, `backend/`, `app.html`, `scripts/review_frames.py`, `scripts/branch_observer.py`, `agent/settings*.json`, `agent/hooks/`, và không có file mới trong `agent/skills/` (ngoài sửa `README.md`). `review_frames.py` trên cùng bản sao cho cùng danh sách file như trước | `git diff --stat`; chạy `review_frames.py` |

### Bảng quyết định: tài liệu và frontmatter

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | 4 skill mới | Thêm | Tiếng Việt, frontmatter chỉ `description` (+ `argument-hint`), có dòng mốc ngay sau frontmatter, ≤ ~120 dòng, không có `disable-model-invocation`. Tên lệnh và cờ khớp `--help` của script thật | `wc -l`; `grep -c '^Mã nạp:'`; đối chiếu `--help` của từng script |
| DD-2 | 6 file agent | Sửa | `skills:` đúng bảng ánh xạ, YAML hợp lệ. Mọi tên trong `skills:` có file `agent/commands/<tên>.md` tương ứng. Mỗi agent có câu "đọc `.claude/commands/<tên>.md` nếu chưa có trong ngữ cảnh". Không còn câu mâu thuẫn (marketing "Không gọi Groq"; ba "số lớn nhất hiện có + 1") | Parse YAML bằng `$PY -c "import yaml…"`, với mỗi tên kiểm `test -f agent/commands/<tên>.md`; xem diff |
| DD-3 | 4 skill đã có | Sửa | Có dòng mốc. `dev-selfcheck` trỏ `sandbox-render` ở lớp Pipeline và hồi quy, trỏ `audio-check` khi sửa audio. `tech-audit`, `travel-review`, `post-analytics` không đổi gì khác | Xem diff |
| DD-4 | `agent/CLAUDE.md`, `TODO.md`, `agent/skills/README.md` | Đồng bộ | Bảng Đội vai trò ghi đủ skill của 6 agent; danh sách lệnh có `/sandbox-render`, `/audio-check`. `TODO.md` có việc đổi số DR của `clip-trim`, `gemini-quota` (2026-11-19: đã xong, thành DR-0009 và DR-0012). `agent/skills/README.md` ghi skill riêng nằm ở `agent/commands/` | Đối chiếu chéo với frontmatter thật |

### Kiểm tra E2E

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| V-1 | **Nạp sẵn thực tế** (cả skill mới và 4 skill đã có) | Mở **phiên Claude Code mới tại `.worktrees/agent-skills`**. Gọi lần lượt 6 agent với prompt: "Không dùng công cụ nào. Liệt kê mọi dòng bắt đầu bằng `Mã nạp:` có trong ngữ cảnh của bạn." | Mỗi agent trả **đúng** các dòng mốc của skill đã gắn, không hơn không kém (vd `ba` chỉ có `dr-draft/1`; `techlead` có `tech-audit/1`, `voice-rules/1`). Transcript không có lời gọi Read hay Skill tới file lệnh. Nếu sai: chạy lại với `claude --debug` để xem log "skill not found", rồi theo R-1 | **Đạt.** Phiên `claude -p` mới tại worktree. 6 agent trả đúng dòng mốc theo bảng ánh xạ (ba: dr-draft · techlead: tech-audit, voice-rules · reviewer: voice-rules · dev: dev-selfcheck, sandbox-render, audio-check, voice-rules · tester: sandbox-render, audio-check, voice-rules · marketing: travel-review, post-analytics, audio-check). Không agent nào gọi Read/Skill. Model tự báo khớp frontmatter: ba/techlead/reviewer `claude-opus-5-5`, dev/tester/marketing `claude-sonnet-5-5` | 2026-11-19 |
| V-2 | Người dùng gọi được lệnh | Trong phiên ở V-1, gõ `/audio-check <bản sao>` và `/sandbox-render <thư mục mẫu>` | `audio-check` ra bảng tiếng nổ + chép lời; `sandbox-render` in JSON có `original_unchanged=true` | **Đạt.** `/sandbox-render <bài tập mẫu> --keep`: `status=rejected`, `original_unchanged=true`, `repo_data_unchanged=true`, `post_txt_created=false`. `/audio-check <bản sao> --scenes 1`: 0/6 mốc nổ, chép lời cảnh 1 similarity 0,958 (1 lượt Groq), kết quả ở `<thư mục>__sandbox/`. Shasum thư mục gốc trước/sau giống nhau | 2026-11-19 |
| V-3 | Tester dùng skill thay script tự viết | Giao tester ca D-3 của DR-0001 (sửa hook rồi dựng lại) trên mẫu `bot-me-den` | Tester dùng `sandbox_render.py`, không tự viết monkeypatch; bản gốc không đổi | — | — |
| V-4 | Marketing dùng `audio-check` | `/video-review` trên bản sao 1 video | `marketing-review.md` có kết quả tiếng nổ + chép lời. "Cần người kiểm" nêu câu cụ thể thay vì chỉ "nghe toàn bộ". Bảng tổng hợp có cột Lượt Groq | — | — |
| V-5 | BA giữ số DR | Giao `ba` một yêu cầu giả, chỉ xin số DR | Trả về số lớn nhất ở mọi nơi + 1 (lúc sửa DR này, 2026-11-19, là **0013**; số này tăng khi có DR mới nên Tester quét lại lúc kiểm), tạo file ngay, và báo nếu có số trùng (lúc 2026-11-19: không có) | — | — |
| V-6 | Dev dùng `dev-selfcheck` + `sandbox-render` | Giao dev một sửa nhỏ giả định ở lớp Pipeline (không commit) | Báo cáo của Dev có cột "Tự kiểm bằng cách nào" ghi lệnh `sandbox_render.py`, không tự dựng bản sao bằng tay | — | — |

### Cổng chất lượng

- [ ] Đã kiểm hết D-1…D-13, DD-1…DD-4, V-1…V-6
- [ ] V-1 đạt cho cả 6 agent (nếu không: ghi trong §Kết quả theo R-1)
- [ ] Không hồi quy (D-13)
- [ ] Không vi phạm C-0001-x và C-0004-x; 0 lượt Gemini đã dùng
- [ ] Xong mọi việc trong kế hoạch
- [ ] Đã cập nhật tài liệu SSoT

---

## Những gì KHÔNG làm

- Không tự động chạy Whisper hay đo tiếng nổ trong pipeline `demo.py` (sau khi tạo giọng) hay trên Studio. Đó là thay đổi hành vi sản phẩm, cần DR riêng nếu người dùng muốn (Q-5).
- Không tạo file hay thư mục mới trong `agent/skills/` (chỉ BA sửa `README.md`). Không khôi phục skill SSoT đã xoá. Không sửa `agent/scripts/sync.sh`, `agent/settings*.json`, `agent/hooks/`.
- Không tạo `scripts/check_agent_skills.py` (đã bỏ, xem §Các phương án).
- Không sửa nội dung `tech-audit.md`, `travel-review.md`, `post-analytics.md` ngoài dòng mốc.
- Không cài hay bật plugin nào (`skill-creator`, `pr-review-toolkit`…).
- Không chép skill từ `affiliate-skills-main` vào repo.
- Không đổi số hay nội dung các DR nháp trên worktree khác (lúc viết: DR-0002 `clip-trim`, DR-0002 `gemini-quota`, DR-0003, DR-0005…0007; hai bản trùng số đã được chính nhánh đó đổi thành DR-0009, DR-0012). Chỉ báo việc phải đổi số cho người điều phối và ghi vào `TODO.md`.
- Không tách bảng chấm A–K của marketing hay danh sách soát bảo mật của reviewer thành skill.
- Không gọi Gemini ở bất kỳ bước nào.
- Không đồng bộ `.agents/` (bản chép cho Antigravity, PR #14) với 4 skill mới và phần sửa agent. Người dùng quyết định để issue riêng #27.

---

## Câu hỏi mở cho người dùng

| # | Câu hỏi | Đề xuất của BA | Trả lời |
|---|---------|----------------|---------|
| Q-1 | Cho agent `marketing` gọi Groq Whisper (miễn phí, khoảng 4–10 lần mỗi video) qua `transcript_check.py` không? | Đồng ý, chỉ qua script này | **Đồng ý** (người dùng duyệt theo đề xuất) |
| Q-2 | (Bản đã duyệt) Thêm `--exclude='tta-*'` vào `sync.sh` ở SSoT? | — | **Không còn cần**: skill đã chuyển sang `agent/commands/`, sync không đụng |
| Q-3 | Có muốn bật plugin chính thức `skill-creator` hay `pr-review-toolkit` cho reviewer không? Miễn phí nhưng thay đổi môi trường Claude Code của bạn | Chưa cần | Chưa trả lời → mặc định: chưa cần |
| Q-4 | Trên Drive còn `audio_1.mp3` gốc của video trà ô long (bản có câu bịa) không? | Nếu còn, gửi đường dẫn để thêm một ca test với lỗi thật | Chưa trả lời → mặc định: chỉ kiểm bằng mẫu tổng hợp (D-9) |
| Q-5 | Sau DR này, có muốn một DR riêng để tự chạy chép lời Whisper ngay sau khi tạo giọng, rồi cảnh báo trên Studio không? | Để sau, khi đã có số liệu báo đúng/sai từ C-0004-3 | Chưa trả lời → mặc định: để sau |
| Q-6 | Các DR nháp trùng số thì nhánh nào giữ số? | Nhánh merge trước giữ số, nhánh còn lại đổi số trước khi merge (C-0004-4) | **Đồng ý**. Áp dụng: DR-0002-travel-content đã lên `main` giữ 0002; `clip-trim` và `gemini-quota` phải đổi số (2026-11-19: đã đổi thành DR-0009, DR-0012) |

Chi phí: **$0**, **0 lượt Gemini**. Groq Whisper miễn phí; hạn mức chưa rõ (R-5). Edge-tts miễn phí (chỉ dùng ở D-3, D-9).

---

## Nhật ký thay đổi

| Ngày | Thay đổi |
|------|----------|
| 2026-11-13 | Bản đề xuất; người dùng duyệt "Đồng ý" theo mọi đề xuất của BA |
| 2026-11-16 | **Sửa sau khi duyệt** vì `main` đổi quy ước (PR #10–#13: xoá 17 skill SSoT, skill riêng đặt ở `agent/commands/` + `skills:`, thêm agent `techlead` và skill `dev-selfcheck`, `tech-audit`, `travel-review`, `post-analytics`). Đổi: nơi đặt skill (`agent/skills/tta-*` → `agent/commands/<tên>.md`), bỏ tiền tố `tta-` (tên mới `sandbox-render`, `audio-check`, `voice-rules`, `dr-draft`), bỏ `check_agent_skills.py`, `dev-selfcheck` trỏ sang `sandbox-render` thay vì lặp lại, thêm `techlead` vào ánh xạ (`voice-rules`), thêm dòng mốc cho 4 skill đã có để V-1 kiểm luôn, cập nhật số DR thực tế. **Phạm vi và chi phí không đổi**: vẫn 4 skill + 3 script kiểm, $0, 0 lượt Gemini; quy tắc giọng đọc, Whisper, đo tiếng nổ giữ như bản đã duyệt |
| 2026-11-19 | **Vòng review 1** (Reviewer, Tester, Tech Lead, MKTG; nhánh vừa rebase lên `origin/main` 4e348dc). Quyết định: (1) `sandbox-render` **chưa hỗ trợ** thư mục travel (có `topic.json`): script dừng với thông báo rõ, việc hỗ trợ ghi vào `TODO.md` mục nợ kỹ thuật; (2) `transcript_check.py` **từ chối** thư mục travel (lời tiếng Anh, phần so khớp hiện chỉ làm cho tiếng Việt); (3) kết quả đo của bản sao ghi **tách khỏi** kết quả của video thật, không ghi đè lẫn nhau; (4) sửa frontmatter `agent/commands/travel-review.md` để V-1 nạp được skill. Việc này **ngoài phạm vi ban đầu** (§ Những gì KHÔNG làm chỉ cho thêm dòng mốc), chấp nhận vì không sửa thì V-1 không đạt; (5) trường JSON `post_txt_created` (lần chạy này có tạo `post.txt` không) thay cho `post_txt_in_copy`, vì bản sao có thể đã chép sẵn `post.txt` từ bản gốc. Cập nhật bảng số DR (số trống tiếp theo: 0013) và thêm mục `.agents/` (#27) vào § Những gì KHÔNG làm. Chi phí không đổi: $0, 0 lượt Gemini. Dev sửa thêm frontmatter `agent/commands/bug.md` (cùng lỗi: ` #<số issue>` bị YAML hiểu là chú thích), ngoài phạm vi ban đầu, cùng lý do như (4) |
| 2026-11-19 | **Vòng sửa 2** (sau re-review): ghi đường dẫn `<thư mục>__sandbox/` vào Bước 2/3, bảng file, C-0004-5, D-7; `is_real_folder` so với đường dẫn đã resolve (đúng khi `storage/videos` là symlink); `review_frames.py` chưa tách thư mục bản sao, ghi nợ kỹ thuật trong `TODO.md` |
| 2026-11-19 | **Model theo vai trò** (người dùng yêu cầu, để tiết kiệm token): thêm `model:` / `effort:` vào frontmatter agent: `ba`, `techlead`, `reviewer` → `opus` + `effort: medium`; `dev`, `tester`, `marketing` → `sonnet`. Ghi 1 dòng ở `agent/CLAUDE.md` § Đội vai trò. V-1 xác nhận model đúng. Issue: #30 |

---

## Kết quả

(Điền sau khi Dev, Reviewer, Tech Lead, Tester, MKTG xong.)

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR liên quan | DR-0001 (C-0001-1, C-0001-2, C-0001-4); DR-0002-travel-content (skill `travel-review`) |
| Code nguồn | `demo.py` (`_trim_gemini_edges`, `clean_gemini_audio`, `gemini_tts_models`, `generate_voiceovers`, `revoice_changed`, `render_only`, `render_video`, `approval_step`, `move_to_drive`, `load_env`, `set_sheet_status`, `GAP`, `END_HOLD`), `exercise.py` (`finish`, `mark_done`, `rerender`, `LOCAL_CLIPS`, `CURRICULUM`, `DEFAULT_TTS_MODEL`, `EXTRA_TTS_MODEL`), `scripts/review_frames.py` |
| Skill đã có | `agent/commands/dev-selfcheck.md`, `tech-audit.md`, `travel-review.md`, `post-analytics.md` |
| Công cụ | `agent/scripts/sync.sh` (`rsync -a --delete` trên `skills/`, `references/`, `scripts/`, `hooks/`; `cp` cho `CLAUDE.md`, `settings.json`; không đụng `agents/`, `commands/`) |
| Tài liệu Claude Code | `code.claude.com/docs/en/sub-agents.md`, `skills.md` (người điều phối đối chiếu, bản 2.1.323) |
| Sự cố | Trà ô long, câu 2 đọc bịa (2026-11-13); tiếng nổ chuyển cảnh (PR #9) |
| Tham khảo không dùng | `~/Downloads/affiliate-skills-main/skills/content/tiktok-script-writer`, `meta/compliance-checker` |
