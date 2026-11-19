---
description: BA giữ số DR không trùng khi nhiều phiên chạy song song (quét mọi ref local/remote và mọi worktree), tạo file DR ngay, rồi viết DR tiếng Việt theo khung DR-0001
argument-hint: <tiêu đề ngắn của DR>
---

Mã nạp: dr-draft/1

Skill này là **sổ tay của agent `ba`** để đánh số và dựng khung DR. Mục tiêu: không còn hai DR trùng số giữa các phiên chạy song song (như DR-0002 từng bị 3 bản dùng), và mọi DR cùng một khung tiếng Việt (C-0004-4).

Tiêu đề DR: $ARGUMENTS

## Bước giữ số

1. Lấy ref mới (chỉ fetch, không checkout):
   ```bash
   R=$(git rev-parse --path-format=absolute --git-common-dir)/..   # repo gốc, chạy được cả từ worktree
   git -C "$R" fetch -q || echo "FETCH FAILED"
   ```
   Fetch lỗi thì vẫn làm tiếp với ref đã có, và ghi "chưa fetch được, dùng ref local/remote theo lần fetch gần nhất" vào DR.
2. Liệt kê mọi số DR đang có (mọi ref local và remote, cộng thư mục DR của repo gốc và mọi worktree, kể cả file chưa commit):
   ```bash
   { for ref in $(git -C "$R" for-each-ref --format='%(refname)' refs/heads refs/remotes); do
       git -C "$R" ls-tree -r --name-only "$ref" -- docs/decision-records; done
     ls "$R"/docs/decision-records "$R"/.worktrees/*/docs/decision-records 2>/dev/null
   } | grep -o 'DR-[0-9]\{4\}' | sort -u
   ```
   Muốn biết số nào ở đâu (để báo trùng): `ls "$R"/.worktrees/*/docs/decision-records/DR-*.md` và `git -C "$R" ls-tree --name-only origin/main docs/decision-records/`.
3. **Số mới = số lớn nhất + 1**, 4 chữ số. **Tạo file ngay** `docs/decision-records/DR-XXXX-<kebab-title>.md` trong worktree, chỉ cần tiêu đề và dòng trạng thái `📋 Đề xuất`, để các phiên khác quét thấy số đã có người dùng.
4. **Trước khi merge** (Phase 5 của `/feature`), chạy lại bước 2. Trùng số với DR đã lên `main` thì đổi số DR **chưa** merge: đổi tên file và mọi `C-XXXX-n`, `DR-XXXX` bên trong. DR đã merge thì không sửa.
5. Thấy trùng số giữa các bản nháp, hoặc giữa nháp và `main`, ở nhánh **khác**: ghi vào báo cáo cho người điều phối. Không tự đổi DR của nhánh khác.

## Khung DR

Mẫu gốc tiếng Nhật: `.claude/references/templates/dr-workplan-template.md`. DR dự án viết **tiếng Việt** với tiêu đề mục như DR-0001:

| Mục trong mẫu | Tiêu đề trong DR | Ghi chú |
|---------------|------------------|---------|
| ヘッダ | `# DR-XXXX: <tiêu đề>` + bảng Trạng thái / Ngày / Đề xuất / Duyệt | Trạng thái: 📋 Đề xuất → ✅ Đã duyệt |
| コンテキスト | Bối cảnh | Vấn đề gốc, bằng chứng, lý do làm bây giờ, ràng buộc ngoài, chi phí |
| 決定 | Quyết định | Một đoạn ngắn in đậm |
| 選択肢 | Các phương án | 2–4 phương án, cột Chọn ⭐ và Lý do (cả phương án bị loại) |
| 構造変更 | Thay đổi cấu trúc | Dữ liệu/file (Trước / Sau / Lý do), luồng |
| 作業計画 | Kế hoạch công việc | # / Việc / Vai trò / Input / Output / Vị trí |
| リスク・前提条件 | Rủi ro và giả định | R-n, A-n: ảnh hưởng và cách xử lý |
| 制約事項 | Ràng buộc mới | `C-XXXX-n`: lý do, phạm vi, điều kiện gỡ; dòng `supersedes:` |
| 影響を受けるSSoT | Tài liệu SSoT bị ảnh hưởng | Kèm cột Xong |
| 実装への影響 | File thay đổi | Mới / sửa / không đổi |
| 完了基準 | Tiêu chí hoàn thành (DoD) | Bảng quyết định code, bảng tài liệu, E2E, cổng chất lượng |
| — | Những gì KHÔNG làm | |
| — | Câu hỏi mở cho người dùng | Q-n / Câu hỏi / Đề xuất của BA / Trả lời |
| 実績 | Kết quả | Điền sau khi Dev, Reviewer, Tester, MKTG xong |
| — | Liên quan | DR, code nguồn, sự cố |

## Quy tắc nội dung

- Mỗi dòng `D-n` kiểm được: điều kiện đầu vào cụ thể, kết quả mong đợi đo được, cách kiểm (lệnh, so hash, `grep` log). Có đủ loại bình thường / lỗi / biên / hồi quy.
- Chi phí ghi rõ: lượt Gemini (10/ngày/model), Groq, $. Số không có nguồn thì ghi "chưa rõ".
- Kế hoạch chia theo vai trò BA / Dev / Reviewer / Tester / MKTG. Thêm **Tech Lead** khi chạm backend, service local, subprocess/FFmpeg, Docker, bảo mật, hiệu năng hay kiến trúc.
- Việc Dev độc lập lớn thì chia nhóm **không sửa chung file** để chạy song song.
- Mọi kiểm thử chạy trên bản sao (skill `sandbox-render`), không gọi Gemini.
