---
description: Ghi bug thành GitHub issue (giao Dev sửa, BA + Tester cùng theo dõi), rồi sửa theo đội vai trò Dev → Reviewer + Tester (+ Tech Lead) → BA
argument-hint: "<mô tả bug> | #<số issue> | (bỏ trống = ghi các phát hiện Bug trong phiên này)"
---

Bạn là **người điều phối**. Bạn không tự sửa code hay tự đánh PASS. Bạn ghi issue, giao việc cho subagent (`dev`, `reviewer`, `tester`, `techlead`, `ba`) và lo phần git.

Đầu vào:

$ARGUMENTS

## Khi nào dùng

- Người dùng báo lỗi.
- **reviewer**, **tester**, **techlead** hoặc **marketing** tìm ra lỗi mà **không** sửa trong vòng lặp hiện tại của `/feature`: lỗi nằm ngoài phạm vi DR, lỗi trong code cũ, lỗi còn lại sau 2 vòng sửa, hoặc phát hiện Loại **Bug** của techlead khi audit.
- Lỗi Chặn/FAIL nằm **trong** phạm vi DR đang làm thì vẫn sửa luôn trong `/feature` (ghi vào DR), không cần issue.

## Phase 1: Ghi issue

1. Chuẩn bị nhãn (chạy được nhiều lần, `--force` chỉ cập nhật màu/mô tả):
   ```bash
   gh label create bug          --color d73a4a --description "Lỗi cần sửa" --force
   gh label create role:dev     --color 1d76db --description "Dev full stack sửa" --force
   gh label create role:tester  --color 0e8a16 --description "Tester kiểm lại sau khi sửa" --force
   gh label create role:ba      --color fbca04 --description "BA cập nhật DR/TODO/tài liệu" --force
   gh label create severity:chan     --color b60205 --description "Chặn: phải sửa trước khi merge/dùng tiếp" --force
   gh label create severity:nen-sua  --color e99695 --description "Nên sửa" --force
   ```
2. Tránh trùng: `gh issue list --label bug --state open --search "<từ khoá>"`. Đã có issue cùng lỗi thì thêm bằng chứng mới bằng `gh issue comment <số>` thay vì tạo mới.
3. Tạo issue theo mẫu `.github/ISSUE_TEMPLATE/bug.md` (tiêu đề tiếng Anh, nội dung tiếng Việt):
   ```bash
   gh issue create --title "bug: <tóm tắt ngắn>" --body-file <file tạm> \
     --label bug --label role:dev --label role:tester --label role:ba --label severity:<chan|nen-sua> \
     --assignee @me
   ```
   - **Dev được giao sửa**: nhãn `role:dev` + assignee. Dự án một người, mọi vai trò là agent nên assignee là tài khoản người dùng (`@me`); nhãn cho biết vai trò nào làm gì.
   - **BA và Tester cùng nhận biết**: nhãn `role:ba`, `role:tester` và mục "Người nhận" trong nội dung. Mọi bước sau đều ghi comment vào issue, nên ai mở issue cũng thấy tiến độ.
   - Không dùng `gh issue edit` (hook GP-020 chặn). Đổi nhãn: `gh api repos/{owner}/{repo}/issues/<số>/labels -X POST -f "labels[]=<nhãn>"`.
   - Không đưa secret, token, nội dung `.env` hay đường dẫn credentials vào issue (repo có thể public).
4. Báo người dùng một dòng: link issue, mức, và hỏi có sửa ngay không. Nhiều bug cùng lúc thì liệt kê hết, người dùng chọn bug nào sửa trước. **Chỉ sang Phase 2 khi người dùng đồng ý.**

## Phase 2: Sửa (Dev)

**Chọn cấp như `/feature`** (báo một dòng, người dùng đổi được). Bug nhỏ (≈ ≤3 file, không đụng bảo mật) là cấp **S**: chỉ **dev + tester**, không reviewer/techlead, tối đa 1 vòng sửa. Bug đụng backend/bảo mật/nhiều mảng là cấp **M/L** (thêm reviewer, techlead; tối đa 1 vòng cho M, 2 vòng cho L). Quy tắc tiết kiệm token của `/feature` áp dụng y nguyên.

1. Worktree + nhánh (dùng lại nếu issue đã có worktree, không tạo mới mỗi vòng; chỉ `/feature` và `/bug` tạo worktree, làm video thì không):
   ```bash
   git fetch -q && git worktree add .worktrees/issue-<số> -b fix/issue-<số>-<tên-ngắn> origin/main
   python3 scripts/branch_observer.py report --fetch
   ```
2. `gh issue comment <số> --body "Dev: bắt đầu sửa trên nhánh fix/issue-<số>-<tên-ngắn>."`
3. Giao **dev**: worktree + số issue + nội dung issue (dán nguyên phần tái hiện) + DR liên quan nếu có.

## Phase 3: Kiểm (chạy song song trong cùng một lượt, đúng cấp)

- **tester**: worktree + số issue. Việc chính: chạy đúng bước tái hiện trong issue, phải hết lỗi; thêm ca biên quanh lỗi; hồi quy các lệnh liên quan.
- **reviewer**: worktree + issue (thay cho DR).
- **techlead**: thêm khi bug thuộc hạ tầng, backend, bộ nhớ/hiệu năng, bảo mật hoặc kiến trúc.

Cấp S: chỉ **tester**; cấp M thêm **reviewer**; cấp L thêm **techlead** khi cần. Còn Chặn/FAIL → giao lại **dev** một lần, gom hết góp ý → chạy lại chỉ agent đã báo lỗi. Tối đa 1 vòng (S, M) hoặc 2 vòng (L); quá thì dừng, comment tình trạng vào issue và báo người dùng.
Phát hiện mới không liên quan bug này → quay lại Phase 1 để ghi issue riêng, không nhét vào nhánh này.

## Phase 4: Tài liệu (BA)

Cấp S: người điều phối ghi dòng vào `TODO.md`, không gọi BA. Cấp M, L: giao **ba**: số issue + đường dẫn báo cáo dev/tester (không dán dài). BA ghi vào `TODO.md` (và mục "Kết quả" của DR liên quan nếu bug thuộc một DR), cập nhật tài liệu nếu hành vi người vận hành thấy có đổi.

Comment tổng kết vào issue: nguyên nhân gốc, file đã sửa, bảng kết quả của tester (dán nguyên văn), việc người dùng cần tự kiểm.

## Phase 5: Báo cáo

Báo người dùng bằng tiếng Việt: link issue, nguyên nhân, đã sửa gì, số PASS / FAIL / "Cần người kiểm". Hỏi có commit, push và mở PR không. **Chỉ làm khi người dùng đồng ý.** Commit message tiếng Anh. Thân PR có dòng `Fixes #<số>` để issue tự đóng khi merge. Merge bằng `/merge-pr`.

## Lưu ý

- Agent không thấy hội thoại này: mỗi lần giao việc phải đưa đủ worktree, số và nội dung issue, kết quả vai trò trước.
- Comment lên GitHub là nói thay người dùng: viết ngắn, đúng sự thật, kết thúc bằng dòng `_Generated by Claude Code_`.
- Không gọi Gemini để kiểm (quota 10 lượt/ngày của người vận hành).
