---
description: Marketing review video du lịch / văn hoá / ẩm thực Việt Nam tiếng Anh (DR-0002) và chức năng travel trên Studio, kiểm dữ kiện có nguồn, bản quyền clip, tiếng Anh, phụ đề Việt
argument-hint: "[storage/videos/<ngày>_travel_<slug> …] | studio (review chức năng travel trên Studio)"
---

Mã nạp: travel-review/1

Skill này là **sổ tay của agent `marketing`** cho dòng video travel (capability `travel-content`, DR-0002). Gọi bằng lệnh thì bạn là người điều phối: giao **marketing** từng thư mục (chế độ 3) hoặc chế độ 2 nếu đầu vào là `studio`, rồi tổng hợp giống `/video-review`.

Đầu vào: $ARGUMENTS

Nếu DR-0002 chưa merge vào `main` hoặc chưa có thư mục nào chứa `topic.json` với `kind: "travel"`, báo lại "chưa có video travel để review" và dừng.

## Chế độ 3: Review video travel

### Đầu vào và dữ liệu

Thư mục `storage/videos/<ngày>_travel_<slug>/` có `video.mp4`, `script.json` (`lang: "en"`, `kind: "travel"`), `topic.json`, `facts.json`, `credits.txt`.

```bash
.venv/bin/python scripts/review_frames.py storage/videos/<thư mục>
```

Xem mọi khung hình. Đọc `script.json`, `topic.json`, `facts.json`, `credits.txt`, `post.txt` nếu có. Không nghe được âm thanh: phát âm và giọng đưa vào "Cần người kiểm".

### Bảng chấm (thay bảng A–K của video sản phẩm)

| Mã | Hạng mục | Đạt khi |
|----|----------|---------|
| T1 | **Hook câu hỏi** | Cảnh 1 là đúng câu du khách hay hỏi (`topic.question`), tiếng Anh tự nhiên, ≤ 8 từ trên màn hình, đọc được ở `scene_1_start`. Không mở bằng "Welcome to my channel" hay tên kênh |
| T2 | **Mọi câu có nguồn** (C-0002-1) | Mỗi segment `answer` có `fact_ids`; mọi con số (tiền, ngày, %, số lượng) trong `line` / `text` / caption có trong `quote` của fact được trích. Không có khẳng định nào ngoài `facts.json` |
| T3 | **Nguồn đúng hạng** (C-0002-4) | Visa, y tế, an toàn, luật: nguồn `tier=1`. Video loại này kết thúc bằng "Check the official site before you go" |
| T4 | **Còn hạn** (C-0002-2) | Fact `volatile` có `checked_on` ≤ 30 ngày tính đến ngày review. Màn hình cuối và caption có nguồn + tháng năm |
| T5 | **Bản quyền hình** (C-0002-3) | Mỗi clip/ảnh trong `credits.txt` có `provider` (pixabay / pexels / wikimedia), `page`, `author`, `license` trong danh sách cho phép. Ảnh CC BY / BY-SA có ghi công trên khung. Không có logo, watermark, người nổi tiếng |
| T6 | **Đúng địa danh / món** | Clip khớp nội dung đang nói (Hạ Long là Hạ Long, phở là phở), không phải cảnh nước khác. Nghi ngờ thì ghi "Cần người kiểm" kèm khung hình |
| T7 | **Tiếng Anh** | Đúng ngữ pháp, giọng văn tự nhiên với người Mỹ/Canada/Úc, câu ≤ 15 từ, không dịch word-by-word từ tiếng Việt, không giọng quảng cáo |
| T8 | **Tên tiếng Việt** | Chữ trên màn hình giữ dấu (Phở, Hội An). Chữ gửi TTS đã qua `content/travel_pronunciations.json` (xem log hoặc `audio_line`). Phát âm thật: "Cần người kiểm" |
| T9 | **Phụ đề Việt** | `line_vi` đúng nghĩa câu EN, đúng chính tả có dấu, không dài hơn khung; phụ đề EN + VI nằm trong vùng an toàn (không trong 350 px dưới cùng của khung 1920) |
| T10 | **Giá trị cho người xem** (P01) | Người xem học được điều cụ thể dùng được ngay (thủ tục, cách ăn, phép lịch sự). Văn hoá Việt được trình bày tôn trọng, không rập khuôn, không chê vùng miền |
| T11 | **Kỹ thuật** | MP4, H.264, AAC, 1080×1920, 15–60 giây (`facts.json` của review_frames) |
| T12 | **Caption và hashtag** | Caption tiếng Anh 1–2 câu + nguồn + credits theo `post.txt`. Hashtag tiếng Anh viết thường, tối đa 6, liên quan (ví dụ `#vietnamtravel #vietnamfood`). **Không** có `#tiktokshop`, không giỏ hàng, không CTA mua |

Chấm **Đạt / Cần sửa / Không đạt / Cần người kiểm**, kèm bằng chứng (khung hình, câu trích, `fact_id`, dòng `credits.txt`).

**Kết luận:**
- ⛔ **Không nên đăng**: T2, T3, T4 hoặc T5 "Không đạt" (thông tin sai/hết hạn hoặc vi phạm bản quyền: mất uy tín kênh, có thể bị gỡ).
- ✏️ **Sửa rồi đăng**: còn hạng mục khác "Cần sửa" / "Không đạt".
- ✅ **Đăng được**: không còn gì phải sửa.

### Đề xuất sửa (theo đúng những gì Studio sửa được cho video travel)

| Sửa ở đâu | Ghi chú | Chi phí |
|-----------|---------|---------|
| Caption, Hashtag | — | Miễn phí, không dựng lại |
| Chữ lớn `text`, lời đọc `line` (EN), phụ đề `line_vi` | Sửa `line` có số mới: Studio kiểm lại C-0002-1, số không có trong quote thì bị chặn | edge-tts: miễn phí; Gemini (nếu `TRAVEL_TTS_PROVIDER=gemini`): 1 lượt/câu |
| Clip/ảnh sai địa danh, thiếu giấy phép | Chuyển **Dev** hoặc người vận hành chọn clip khác | Miễn phí |
| Thiếu dữ kiện, nguồn sai hạng, fact hết hạn | Người vận hành thêm URL nguồn tier 1 vào tab `Travel` rồi chạy lại | ~3–5 lượt Groq, $0 |

Đưa thêm 2–3 hook câu hỏi thay thế, dựa trên câu du khách thật sự tìm (không bịa số liệu tìm kiếm).

### Ghi báo cáo

Ghi `storage/videos/<thư mục>/marketing-review.md` theo khung của chế độ 1 trong `agent/agents/marketing.md`, thay bảng chấm bằng T1–T12. Khối "Dữ liệu cho Studio" dùng các trường của video travel: `caption`, `hashtags`, `segments: [{index, text, line, line_vi}]`.

## Chế độ 2 cho chức năng travel trên Studio

Ngoài 8 điểm của chế độ 2, soát thêm:
1. Người vận hành thấy được **danh sách dữ kiện + nguồn (link bấm được)** trước khi bấm Duyệt.
2. Fact sắp hết hạn hoặc đã hết hạn được báo rõ, nói việc cần làm (thêm nguồn mới / chạy lại).
3. Ô phụ đề Việt từng cảnh dễ tìm, sửa xong biết phải bấm "Dựng lại".
4. Lỗi "số không có nguồn" nói rõ số nào, câu nào, và cách sửa.
5. Credits xem được, người vận hành hiểu khi nào phải ghi công.
6. Video travel không hiện các ô của video bán hàng (giá, giỏ hàng, ảnh sản phẩm).
