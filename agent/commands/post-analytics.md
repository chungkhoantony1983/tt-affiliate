---
description: Marketing phân tích hiệu quả bài đăng TikTok và mức tiếp cận người xem (sản phẩm, bài tập, du lịch) từ số liệu người vận hành nhập, rút ra kiểu hook/thời lượng/chủ đề thắng và đề xuất video tiếp theo
argument-hint: <file số liệu (CSV xuất từ TikTok Studio hoặc bảng dán tay)> | (bỏ trống = dùng nhật ký § 4 trong TODO.md)
---

Mã nạp: post-analytics/1

Skill này là **sổ tay của agent `marketing`** (chế độ 4: Phân tích hiệu quả). Gọi bằng lệnh thì bạn là người điều phối: giao **marketing** đầu vào dưới đây, trình kết quả cho người dùng, rồi giao **ba** ghi phần đã chốt vào `TODO.md`.

Đầu vào: $ARGUMENTS

## Số liệu lấy từ đâu

App TikTok chỉ có scope `user.info.basic` + `video.upload`, **không đọc được số liệu qua API**. Mọi con số đến từ người vận hành:

- **TikTok Studio** (web hoặc app) → Analytics → từng video: Views, Likes, Comments, Shares, Saves, Average watch time, Watched full video (%), Traffic source (For You / Following / Search / Profile…), Viewers by country / gender / age, New followers.
- Video affiliate: TikTok Shop / Affiliate Center → click giỏ hàng, đơn, hoa hồng.
- `TODO.md` § 4 "Nhật ký video đã đăng" (ngày, sản phẩm, hook style, thời lượng, views 48h, click, đơn).

Thiếu số nào thì để trống và ghi "chưa có số", **không ước đoán**. Không dùng benchmark ngoài (tỉ lệ ER "chuẩn ngành", lượt xem kỳ vọng) khi không có nguồn; chỉ so các video **của chính kênh** với nhau.

## Ghép dữ liệu video

Với mỗi video có số liệu, tìm thư mục tương ứng (local `storage/videos/` hoặc theo tên trong nhật ký) để lấy đặc điểm nội dung:

| Đặc điểm | Lấy ở đâu |
|----------|-----------|
| Dòng nội dung | `product.json` → sản phẩm · `topic.json` `kind: travel` → du lịch (trụ cột `pillar`) · còn lại → bài tập |
| Kiểu hook, chữ hook | `script.json` → `hook`, `hook_style` (nếu có), cảnh 1 |
| Thời lượng | `facts.json` của `scripts/review_frames.py`, hoặc nhật ký |
| Giọng | `script.json` → `tts_provider`, `voice_persona` / `voice` |
| Ngày giờ đăng | nhật ký / người vận hành |

Thư mục đã lên Drive (bị xoá local) thì chỉ dùng thông tin trong nhật ký.

## Chỉ số tính

| Chỉ số | Công thức | Đọc thế nào |
|--------|-----------|-------------|
| Engagement rate (ER) | (likes + comments + shares) / views × 100 | So giữa các video của kênh |
| Save rate | saves / views × 100 | Video hữu ích (travel, bài tập) thường thắng ở chỉ số này |
| Tỉ lệ xem hết | "Watched full video" | Hook và nhịp có giữ được người xem không |
| Thời gian xem TB / thời lượng | avg watch time / duration | < 30%: người xem bỏ sớm, soát hook 3 giây |
| Tỉ lệ For You | lượt từ For You / views | Mức thuật toán đẩy đi, tức **tiếp cận người mới** |
| Follow / 1.000 views | new followers / views × 1.000 | Kênh có giữ chân được người xem không |
| Click giỏ / views, đơn / click | (affiliate) | Hiệu quả bán hàng |
| % người xem US / CA / AU | Viewers by country | (travel) Cổng P2 của DR-0002: có trụ cột nào phần lớn người xem nước ngoài không |

Ít hơn 3 video trong một nhóm thì không kết luận cho nhóm đó, chỉ ghi "chưa đủ dữ liệu".

## Phân tích

1. **Bảng từng video** với các chỉ số trên, xếp theo views 48h (hoặc 7 ngày nếu cùng mốc cho mọi video).
2. **So nhóm**: theo dòng nội dung, kiểu hook (question / shock / relatable / bold_claim / story), khoảng thời lượng, giọng, trụ cột travel, khung giờ đăng. Nêu rõ số video mỗi nhóm.
3. **Tiếp cận**: tỉ lệ For You, quốc gia, độ tuổi/giới. Travel: người xem nước ngoài có tăng theo thời gian không (R-5 của DR-0002). Kênh dùng chung nên ghi rõ video sản phẩm tiếng Việt và video travel tiếng Anh có kéo người xem của nhau không (follow mới đến từ video nào).
4. **Video tốt nhất và kém nhất**: mở `marketing-review.md` (nếu còn) và khung hình để chỉ ra điểm khác biệt cụ thể ở hook, chữ, nhịp. Đây là **nhận định**, ghi rõ là ý kiến.

## Báo cáo

Ghi `storage/analytics/YYYY-MM-DD-bao-cao.md` (gitignored, có thể chứa số liệu riêng của kênh):

````markdown
# Báo cáo hiệu quả: <khoảng ngày>

Số video: N (sản phẩm a · bài tập b · travel c). Nguồn số liệu: <TikTok Studio, ngày lấy>.

## Kết luận chính (≤ 5 dòng)

## Từng video
| Ngày | Video | Dòng | Hook | Thời lượng | Views 48h | Xem hết % | ER % | Save % | For You % | Follow/1k | Click | Đơn |

## So nhóm
| Nhóm | Số video | Views TB | Xem hết TB | ER TB | Ghi chú |

## Tiếp cận người xem

## Đề xuất (video tiếp theo)
| # | Đề xuất | Dựa trên số nào | Thử thế nào (để so được lần sau) |

## Đề nghị ghi vào TODO.md
- § 4: các ô còn trống điền được: …
- § M3 / travel P2: điều rút ra: …
````

Đề xuất phải thử được và so được: mỗi lần chỉ đổi một yếu tố (hook, thời lượng, giờ đăng), ghi rõ sẽ so với video nào.

## Giới hạn

- Chỉ ghi file báo cáo trong `storage/analytics/`. Không sửa `TODO.md` (việc của BA), không sửa video.
- Không đăng nhập TikTok, không gọi API ngoài để lấy số liệu.

## Trả về cho người điều phối

Kết luận chính, 3 đề xuất ưu tiên, đường dẫn báo cáo, danh sách ô cần BA ghi vào `TODO.md`.
