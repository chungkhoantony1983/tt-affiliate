---
description: Merge PR an toàn khi nhiều người / nhiều cửa sổ Claude làm song song. Xem nhánh nào đụng cùng file, gợi ý thứ tự merge, merge xong tự xoá nhánh và worktree
argument-hint: "[số PR …] (bỏ trống = xem mọi PR đang mở)"
---

Bạn điều phối việc merge. Mọi lệnh git chạy từ **repo gốc** (`git rev-parse --path-format=absolute --git-common-dir` → thư mục cha), không chạy từ trong worktree sắp xoá.

PR cần merge: $ARGUMENTS

## Bước 1: Quan sát (observer)

```bash
python3 scripts/branch_observer.py report --fetch
```

Đọc kết quả và báo người dùng ngắn gọn:
- **main ở máy có commit chưa lên GitHub** (`!! local main …`): dừng. Chuyển các commit đó sang nhánh mới + PR trước (`git worktree add .worktrees/<tên> -b <nhánh> main`, push nhánh, mở PR). Không merge gì vào `main` ở máy.
- **Nhánh đụng cùng file**: nêu từng cặp, file nào, mức độ:
  - `merges cleanly`: cùng file nhưng git tự gộp được. Merge theo thứ tự nào cũng được.
  - `CONFLICT on …`: sẽ xung đột thật. Nhánh merge sau phải gộp `origin/main` vào và tự xử lý.
  - `being edited now (uncommitted)`: có cửa sổ khác **đang sửa** file đó. Không merge nhánh này cho tới khi bên kia commit xong.
- **Thứ tự merge gợi ý**: nhánh đã xong (không còn file chưa commit), không xung đột với main, đã có PR, ít xung đột với nhánh khác, thay đổi nhỏ thì merge trước. Nhánh lớn hơn merge sau và gánh phần xung đột.

PR người dùng chọn không đứng đầu thứ tự, hoặc đang `CONFLICT` với một PR khác đang mở: nói rõ lý do và hỏi người dùng muốn merge PR nào trước. Không tự đổi thứ tự.

## Bước 2: Kiểm PR

```bash
gh pr view <số> --json number,title,state,mergeable,headRefName,statusCheckRollup
```

- `state` phải là `OPEN` (đã `MERGED` thì sang thẳng Bước 4 để dọn).
- `mergeable` là `CONFLICTING`: không merge. Trong worktree của nhánh đó chạy `git merge origin/main`, xử lý xung đột (gộp cả hai bên, không bỏ phần của bên kia), kiểm tra lại (file parse được, `demo.py --help` chạy được), commit, push, rồi quay lại Bước 1.
- Có check CI thất bại: dừng, báo người dùng.

## Bước 3: Merge

`gh pr merge` bị hook GP-014 chặn, dùng API. Mặc định **merge commit** (giống lịch sử repo); người dùng muốn squash thì đổi `merge_method=squash`.

```bash
gh api repos/{owner}/{repo}/pulls/<số>/merge -X PUT -f merge_method=merge
gh pr view <số> --json state   # phải là MERGED
```

Merge nhiều PR: làm **lần lượt** theo thứ tự ở Bước 1. Sau mỗi PR, chạy lại `report --fetch` vì thứ tự và xung đột có thể đã đổi.

## Bước 4: Dọn nhánh (tự động)

```bash
python3 scripts/branch_observer.py prune --fetch          # xem trước
python3 scripts/branch_observer.py prune --fetch --yes    # xoá
```

`prune` xoá worktree, nhánh local và nhánh trên GitHub của **mọi** nhánh đã merge (kể cả nhánh cũ còn sót), rồi kéo `main` ở máy lên bằng GitHub nếu `main` chỉ đang chậm hơn. Nó **không** xoá: `main`, worktree còn file chưa commit, worktree mà phiên hiện tại đang đứng trong đó. Nhánh nào bị bỏ qua thì báo lại người dùng.

Không cần hỏi lại trước khi chạy `--yes`, vì người dùng đã yêu cầu merge xong thì tự xoá. Chỉ dừng hỏi khi danh sách xem trước có thứ ngoài dự kiến (nhánh không liên quan đến PR vừa merge mà trông như còn đang làm dở).

## Bước 5: Báo cáo

Tiếng Việt, ngắn:
- PR đã merge (số, tiêu đề, cách merge).
- Nhánh và worktree đã xoá, nhánh bị bỏ qua và lý do.
- Kết quả `report` sau cùng: nhánh nào còn lại giờ đang `CONFLICT` với `main` và cần `git merge origin/main`.
