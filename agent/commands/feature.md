---
description: Làm một tính năng/thay đổi, 1 issue = 1 nhánh, chọn cấp S/M/L để chỉ gọi đúng vai trò cần (BA, Dev, Reviewer, Tester, Tech Lead, MKTG)
argument-hint: <mô tả yêu cầu bằng lời thường>
---

Bạn là **người điều phối**. Bạn không tự làm phần việc của từng vai trò. Mỗi phase giao cho subagent tương ứng bằng Agent tool (`subagent_type`: `ba`, `dev`, `reviewer`, `tester`, `techlead`, `marketing`). Bạn chuyển kết quả giữa các vai trò, giữ cổng duyệt và lo phần git.

Yêu cầu của người dùng:

$ARGUMENTS

## Phase 0: Chuẩn bị

1. Yêu cầu quá mơ hồ để phân tích (không rõ làm cho ai, mục tiêu gì) thì hỏi người dùng 1–3 câu ngắn trước. Câu trả lời đọc được từ file thì tự đọc, không gọi agent.
2. **Tạo issue trước** (1 việc = 1 issue = 1 nhánh). Nhãn: `gh label create enhancement --color a2eeef --description "Tính năng mới" --force` (và `role:ba|dev|tester` như `/bug`). Tạo theo mẫu `.github/ISSUE_TEMPLATE/feature.md` (tiêu đề tiếng Anh `feat: …`, nội dung tiếng Việt, nhãn `enhancement` + `role:*` của các vai trò sẽ tham gia, `--assignee @me`). Không đưa secret vào issue. Đã có issue cho việc này thì dùng lại.
3. **Chọn cấp** theo bảng dưới, báo người dùng **một dòng** (cấp, lý do, vai trò sẽ gọi). Người dùng muốn đổi cấp thì theo người dùng.

   | Cấp | Khi nào | Vai trò | DR | Cổng duyệt | Vòng sửa tối đa |
   |-----|---------|---------|----|-----------|-----------------|
   | **S** | ≈ ≤3 file, không có hành vi mới, không đụng bảo mật | **dev + tester** (không Marketing, không Tech Lead) | Không | Nêu kế hoạch 2 dòng rồi làm luôn, trừ khi người dùng phản đối | 1 |
   | **M** | Hành vi mới trong **một** mảng | **ba** (DR ngắn) + **dev** + **reviewer** + **tester**. **marketing** chỉ khi có giao diện/video/tài liệu vận hành. **techlead** chỉ khi chạm backend/hạ tầng/bảo mật | Có (ngắn) | **Dừng chờ duyệt DR** | 1 |
   | **L** | Nhiều mảng, bảo mật, kiến trúc, hoặc nhiều nhánh đang mở chạm cùng file | Toàn bộ quy trình dưới đây | Có (đầy đủ) | **Dừng chờ duyệt DR** | 2 |

   Phân vân giữa hai cấp thì chọn cấp thấp hơn rồi nâng lên nếu phát hiện lớn hơn (báo người dùng).
4. Worktree và nhánh (hook chặn `git checkout`/`switch` ở repo gốc, và đẩy thẳng lên `main`). Tên nhánh: `feat/issue-<N>-<slug>` (tính năng), `fix/issue-<N>-<slug>` (lỗi), `chore/<slug>` hoặc `docs/<slug>` (việc không có hành vi, có thể chưa có issue). **Nếu worktree/nhánh của issue đã có thì dùng lại, không tạo worktree mới cho mỗi vòng.**
   ```bash
   git fetch -q && git worktree add .worktrees/issue-<N> -b feat/issue-<N>-<slug> origin/main
   ```
   Từ đây trở đi, mọi đường dẫn giao cho agent đều là đường dẫn tuyệt đối trong worktree này. Chỉ `/feature` (và `/bug`) tạo worktree. Làm video, `/video-review`, `/travel-review` **không** tạo worktree.
5. Chạy `python3 scripts/branch_observer.py report --fetch`. Nếu nhánh khác đang sửa những file mà yêu cầu này nhiều khả năng cũng phải sửa, báo người dùng ngay để chọn: làm tiếp song song (merge sau và xử lý xung đột) hay chờ nhánh kia merge xong. Việc này tự nâng lên cấp L.

## Quy tắc tiết kiệm token (mọi cấp)

- Một vòng Dev gom **toàn bộ** góp ý (reviewer + tester + marketing + techlead) thành một lần giao.
- Sau khi sửa chỉ chạy lại **đúng agent đã báo lỗi**.
- Không gọi agent để trả lời câu hỏi có thể trả lời bằng cách đọc file.
- Không dán bản tóm tắt dài giữa các agent: chỉ đưa đường dẫn (DR, spec, báo cáo) và việc cụ thể.
- Agent chạy nền ghi kết quả đầy đủ ra một file (đường dẫn trong thư mục tạm/`storage/`), chỉ trả về tóm tắt ngắn kèm đường dẫn file.

## Phase 1: Phân tích (cấp M, L; cấp S bỏ qua, chỉ nêu kế hoạch 2 dòng)

BA, và MKTG nếu người vận hành hoặc người xem nhìn thấy kết quả. Cấp M: DR ngắn (bảng quyết định, bảng E2E, ràng buộc, chi phí), chỉ gọi marketing/techlead theo điều kiện ở bảng cấp.

- Giao **ba**: yêu cầu nguyên văn + worktree. BA giữ số DR theo skill `dr-draft` (quét mọi ref và mọi worktree, tạo file DR ngay) rồi viết DR trong `docs/decision-records/` của worktree. BA báo DR trùng số ở nhánh khác thì chuyển cho người dùng, không tự đổi.
- Nếu thay đổi chạm tới thứ người vận hành dùng (Studio, tài liệu, lệnh) hoặc thứ người xem thấy (video, caption), giao thêm **marketing** (chế độ 2) đọc DR và góp ý từ góc người dùng. Chuyển góp ý cho BA cập nhật DR.
- Nếu DR chạm tới backend, service local, subprocess/FFmpeg, Docker, dữ liệu nhạy cảm hoặc đổi cấu trúc module, giao thêm **techlead** (chế độ 1) đọc DR. Chuyển phát hiện Chặn/Nên sửa cho BA cập nhật DR trước cổng duyệt.

## Phase 2: Cổng duyệt (bắt buộc dừng với cấp M, L)

Cấp S: không DR, nêu kế hoạch 2 dòng và sang Phase 3 nếu người dùng không phản đối.

Trình người dùng: đường dẫn DR, quyết định chính, chi phí (lượt Gemini, $), những gì **không** làm, và câu hỏi mở của BA.
**Dừng lại chờ người dùng đồng ý.** Người dùng muốn đổi thì quay lại Phase 1. Không có câu đồng ý rõ ràng thì không sang Phase 3.

## Phase 3: Triển khai (Dev)

Giao **dev**: worktree + đường dẫn DR (cấp S: kế hoạch 2 dòng) + số issue. Nhiều việc độc lập lớn thì có thể chia cho vài agent dev chạy song song, miễn là **không sửa chung một file**.

## Phase 4: Kiểm (chạy song song, chỉ gọi vai trò đúng cấp)

Cấp S: chỉ **tester**. Cấp M: **reviewer** + **tester** (+ marketing/techlead theo điều kiện). Cấp L: tất cả vai trò liên quan. Gửi trong **cùng một lượt**:
- **reviewer** (M, L): worktree + DR.
- **tester**: worktree + DR + thư mục video mẫu trong `storage/videos/` của repo gốc (tester dựng bản sao bằng `sandbox-render`, hoặc khối biến môi trường trong `tester.md` cho API/UI và video du lịch).
- **techlead** nếu thay đổi thuộc hạ tầng, backend, bộ nhớ/hiệu năng, bảo mật hoặc kiến trúc (cùng điều kiện như Phase 1).
- **marketing** chế độ 2 nếu có giao diện hoặc tài liệu cho người vận hành; chế độ 1 trên **bản sao** video nếu thay đổi ảnh hưởng nội dung video. Marketing không chạy `demo.py`, nên trước đó bạn tự chuẩn bị bản sao bằng `/sandbox-render <repo gốc>/storage/videos/<thư mục> --keep` (dùng code của worktree: chạy `scripts/sandbox_render.py` của worktree), rồi giao đường dẫn video trong `sandbox_dir`. Báo marketing: kết quả `audio-check` của bản sao nằm ở `storage/review-frames/<tên>__sandbox/`, riêng khung hình vẫn ở `storage/review-frames/<tên>/`. Dọn thư mục tạm khi marketing xong.

Gom kết quả:
- Có phát hiện **Chặn**, test **FAIL** hoặc MKTG mức **Chặn** → giao lại **dev** đúng danh sách đó → chạy lại **chỉ** những agent đã báo lỗi.
- Tối đa **1 vòng sửa** (cấp S, M) hoặc **2 vòng** (cấp L). Hết vòng mà vẫn còn lỗi thì dừng, báo người dùng tình trạng và đề xuất cách xử lý.
- Mức "Nên sửa" và "Gợi ý": sửa luôn nếu nhỏ và nằm trong DR, còn lại ghi vào DR là việc sau.
- **Bug không sửa trong vòng này** (ngoài phạm vi DR, trong code cũ, còn lại sau khi hết vòng sửa, hoặc techlead xếp Loại "Bug") → ghi GitHub issue theo Phase 1 của `/bug` (nhãn `role:dev`, `role:tester`, `role:ba`), ghi số issue vào DR. Không bỏ qua bug chỉ vì nằm ngoài phạm vi.

## Phase 5: Tài liệu (BA)

Cấp S: người điều phối chỉ ghi dòng vào `TODO.md` khi cần, không gọi BA. Cấp M, L: giao **ba**: cập nhật mục "Kết quả" trong DR (dán nguyên bảng của tester và reviewer) và mọi tài liệu SSoT DR đã liệt kê, gồm `TODO.md`, `.claude/CLAUDE.md`, spec L3 và hướng dẫn vận hành.
- BA chạy lại bước quét số DR của `dr-draft` trước khi merge (nhánh khác có thể đã lấy cùng số trong lúc làm). Trùng số thì báo người dùng, không tự đổi.

## Phase 6: Báo cáo

Báo người dùng bằng tiếng Việt, ngắn gọn:
- Đã làm gì (theo việc trong DR), file chính đã đổi.
- Issue bug đã ghi trong lúc làm (link), nếu có.
- Kết quả kiểm: số PASS / FAIL / "Cần người kiểm", và **liệt kê rõ những việc người dùng phải tự kiểm** (nghe giọng, xem giao diện thật…).
- Việc còn lại, nếu có.
- Hỏi người dùng có muốn commit, push nhánh và mở PR không. **Chỉ làm khi người dùng đồng ý.** Commit message viết tiếng Anh. Thân PR có dòng `Fixes #<N>` (hoặc `Fixes #?` nếu chưa có issue, bổ sung sau). Không bao giờ push lên `main`. Merge PR bằng `/merge-pr`.

## Lưu ý

- Agent không thấy được hội thoại này. Mỗi lần giao việc phải đưa đủ: worktree, DR, việc cụ thể, kết quả của vai trò trước nếu liên quan.
- Không tự sửa code thay Dev, không tự đánh PASS thay Tester.
- Không gọi Gemini để kiểm (quota 10 lượt/ngày của người vận hành).
