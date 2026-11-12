# TODO — TikTok Shop Affiliate Pipeline

> Theo dõi tiến độ **riêng phần TikTok Shop Affiliate**: tìm sản phẩm trên TikTok → script → video → đăng TikTok (gắn giỏ hàng) → analytics.
> Cập nhật file này mỗi khi xong 1 việc. Thiết kế chi tiết xem `docs/specs/`, chiến lược xem `FEASIBILITY.md`.
>
> **Ngoài phạm vi hiện tại:** mọi thứ liên quan đến Shopee (sync, API, link affiliate Shopee).
>
> Ký hiệu: ✅ xong · 🟡 đang làm / làm dở · ⬜ chưa làm · ⛔ bị chặn (chờ bên ngoài)
>
> Cập nhật lần cuối: 2026-11-05

---

## 1. Pipeline

```
[1] Tìm sản phẩm ──▶ [2] Chấm điểm & chọn ──▶ [3] Script ──▶ [4] TTS + Video
     (TikTok Shop)        (products.csv)                          │
                                                                  ▼
[7] Analytics ◀── [6] Đăng TikTok + gắn giỏ hàng ◀── [5] Duyệt thủ công
     │
     └──▶ quay lại [2]: sản phẩm/hook nào thắng thì làm thêm
```

| # | Bước | Trạng thái | Hiện có gì | Còn thiếu |
|:-:|---|:-:|---|---|
| 0 | Điều kiện tài khoản | ⬜ | Kênh 1,100+ followers | Kiểm tra đã đủ điều kiện TikTok Shop Affiliate (VN) chưa, bật tính năng giỏ hàng / showcase |
| 1 | Tìm sản phẩm | ⬜ | — | Quy trình lấy sản phẩm từ TikTok Shop + tín hiệu trend |
| 2 | Chấm điểm & chọn | ⬜ | — | Tiêu chí chấm điểm, file `products.csv` |
| 3 | Script gen | ✅ | `demo.py`: prompt TikTok Shop (hook style, key_points, CTA giỏ hàng, caption), đọc `products.csv`; đã test với Groq thật | — |
| 4 | TTS + Video | ✅ | `demo.py`: edge-tts + hook → 1 cảnh/ảnh sản phẩm (tối đa 3) → CTA, zoom chậm, chữ tránh vùng UI TikTok | Chưa dùng clip video sản phẩm (chỉ ảnh) |
| 5 | Duyệt thủ công | ✅ | `approval_step()`: tự mở video để xem, y/n | — |
| 6 | Đăng + gắn giỏ hàng | 🟡 | Đăng tay: `post.txt` (caption + checklist) cạnh mỗi video · `tiktok_service.py` cho API sau này | API chờ TikTok duyệt. Gắn sản phẩm làm tay trong app (xem §5) |
| 7 | Analytics | ⬜ | `get_video_stats()` trong `tiktok_service.py` | Chưa thu thập; tạm ghi tay ở §4 |

**Tóm lại:** công cụ tạo video + bộ đăng tay đã sẵn sàng. **Đang thiếu:** tài khoản đủ điều kiện affiliate (M0), sản phẩm thật trong `products.csv` (M1), `GROQ_API_KEY`.

### Cách chạy

```bash
# Lần đầu
python3 -m venv .venv && .venv/bin/pip install -r requirements-demo.txt
cp .env.example .env      # điền GROQ_API_KEY

# Tạo video
.venv/bin/python demo.py --csv products.csv
.venv/bin/python demo.py --product "Tên SP" --price 189000 --images a.jpg,b.jpg --points "Ý 1|Ý 2|Ý 3"
```

Kết quả nằm trong `storage/videos/<ngày>_<tên-sp>/`: `video.mp4`, `post.txt` (caption + checklist đăng), `script.json`, `audio_N.mp3`.

Style `story` (mặc định) cần ảnh nhân vật:
1. Lần chạy đầu tạo `video.mp4` bản nháp + `prompts.txt`
2. Mở Gemini app, dán từng prompt trong cùng 1 chat → tải ảnh → lưu thành `canh_N.png` trong thư mục đó
3. `.venv/bin/python demo.py --rerender storage/videos/<thư mục>` → video hoàn chỉnh + `post.txt` (không gọi lại AI, giữ nguyên script và giọng)
Trong `products.csv`, đặt `status=done` cho sản phẩm đã làm để lần sau bỏ qua.

---

## 2. Mốc (Milestones)

### M0 — Sẵn sàng bán hàng trên TikTok
- [x] Tài khoản đủ điều kiện TikTok Shop Affiliate (người dùng xác nhận 2026-10-20)
- [x] Đã bật showcase / giỏ hàng
- [ ] Thử tay: thêm OMNIEAR vào showcase → đăng 1 video gắn sản phẩm đó (lần đăng 2026-10-20 chưa thấy mục "Sản phẩm" — xem §5)

### M1 — Tìm & chọn sản phẩm (bán thủ công, có cấu trúc)
Nguồn dữ liệu (miễn phí trước):
- **Affiliate Center / Sàn tiếp thị liên kết trong TikTok Shop:** danh sách sản phẩm, % hoa hồng, số đã bán
- **TikTok Creative Center** (Top Products, hashtag đang trend, top ads): xem sản phẩm nào đang được quảng cáo/viral
- **Video trend theo từ khoá:** tìm thủ công trên TikTok; sau này có thể dùng Apify TikTok Scraper (xem `affiliate-skills-main/shared/references/social-data-providers.md`)
- (Trả phí, để sau) FastMoss / Kalodata: số liệu doanh số TikTok Shop theo sản phẩm

Việc cần làm:
- [ ] Chốt 1–2 ngách phù hợp kênh (nhà cửa, mẹo vặt, làm đẹp…)
- [x] Tạo mẫu `products.csv`: `name, price, category, images, selling_points, product_url, commission_pct, sold_count, notes, status`
- [ ] Điền 5 sản phẩm thật đầu tiên (ảnh: lưu ảnh từ trang sản phẩm vào máy rồi ghi đường dẫn, hoặc dán URL ảnh)
- [ ] Định nghĩa điểm ưu tiên, ví dụ: `hoa hồng (₫) × độ hot (số bán / video trend) ÷ độ cạnh tranh`
- [ ] Mỗi tuần chọn 5–10 sản phẩm đưa vào CSV

### M2 — Tạo video từ CSV
- [x] Thêm `GROQ_API_KEY` vào `.env.example`; `demo.py` tự đọc `.env`
- [x] Prompt mới: hook style, `key_points` hiện trên màn hình, CTA giỏ hàng vàng, caption + hashtag
- [x] `demo.py` dùng ảnh sản phẩm thật (`--images` hoặc cột `images`, nhận cả đường dẫn và URL)
- [x] Chế độ batch: `demo.py --csv products.csv` → 1 video / sản phẩm
- [x] Cảnh CTA hướng đến giỏ hàng vàng + dòng "Video có gắn link tiếp thị liên kết"
- [x] Xuất `post.txt` (caption + checklist đăng tay) cho mỗi video
- [x] Cài môi trường: `.venv` + `requirements-demo.txt` (ffmpeg qua `imageio-ffmpeg`, không cần Homebrew)
- [x] Chạy thử với Groq thật (sản phẩm mẫu): ổn; đã chặn bịa thông số, bịa trải nghiệm cá nhân, hashtag có dấu
- [x] Chạy với sản phẩm thật đầu tiên (OMNIEAR tai nghe khuếch đại âm thanh) → video 14.8s, 5 cảnh
- [x] Đổi model mặc định sang `qwen/qwen3.8-27b` (gpt-oss-120b sai chính tả "khuế đại"); chuẩn hoá hashtag bằng code
- [x] Giá trống → video không hiện giá, script không nhắc giá
- [x] Mỗi key point 1 cảnh (dùng lại ảnh nếu ít ảnh)
- [x] Layout v2: ảnh sản phẩm full-width, mỗi cảnh chỉ 1 nhãn ngắn (giọng đọc đã đủ nội dung)
- [x] Style `story` (mặc định): tiểu phẩm nhân vật người Việt → sản phẩm → CTA; mỗi cảnh khớp đúng thời lượng câu thoại
- [x] Nhiều giọng: narrator, con_gai, con_trai, me, bo, ba, ong (edge-tts, chỉnh pitch/tốc độ cho người già)
- [x] `--style simple` / cột `style` trong CSV cho sản phẩm không cần tiểu phẩm
- [x] Gemini API key: hợp lệ nhưng free tier quota tạo ảnh = 0 (gói AI Plus không bao gồm API) → chọn làm ảnh thủ công
- [x] Chế độ ảnh thủ công (mặc định): `prompts.txt` cho từng cảnh nhân vật → tạo ảnh trong Gemini app → lưu `canh_N.png` → `demo.py --rerender <thư mục>`
- [ ] Tạo ảnh cho video OMNIEAR (cảnh 1, 2, 5) và rerender → **đăng video đầu tiên**
- [ ] (Khi có doanh thu) Bật billing Gemini API → `IMAGE_PROVIDER=gemini` để tự động hoá; truyền ảnh cảnh trước làm tham chiếu để giữ nhân vật
- [ ] Đưa tín hiệu trend vào prompt (cột `notes`: hook của video trend đang chạy)
- [ ] (Sau) Dạng `scenes[]` chi tiết theo `affiliate-skills-main/skills/content/tiktok-script-writer/SKILL.md`; hỗ trợ clip video sản phẩm

### M3 — Đăng & học từ dữ liệu
- [ ] Đăng tay 10 video đầu, gắn sản phẩm, ghi kết quả vào §4
- [ ] Sau 2 tuần: rút ra ngách / kiểu hook / thời lượng thắng → cập nhật tiêu chí chấm điểm ở M1

### M4 — TikTok API (khi app được duyệt)
- [x] Đăng ký app TikTok for Developers, verify domain (3 file `tiktok*.txt`)
- [x] Terms / Privacy trên GitHub Pages
- [x] Xác minh URL prefix `https://chungkhoantony1983.github.io/tt-affiliate/` (file `tiktokYUeX…txt`)
- [x] Trang `app.html` + dịch vụ local `backend/app/creator_main.py`: đăng nhập TikTok, xem video, gửi vào inbox. Mới test với TikTok giả, chưa test với sandbox thật
- [ ] Cấu hình sandbox, chạy thử, quay demo theo `docs/operations/tiktok-demo-recording.md`
- [ ] ⛔ TikTok duyệt app. Kiểm tra trạng thái trên developers.tiktok.com
- [ ] Đăng thử 1 video. App chưa qua audit chỉ đăng được ở chế độ **private (SELF_ONLY)**
- [ ] Thay `publish_to_tiktok()` giả lập trong `demo.py` bằng `tiktok_service.py`
- [ ] Lấy stats tự động thay cho ghi tay

### Để sau
- Backend FastAPI / Celery / N8N tự động hoá: chỉ làm khi M1–M3 chứng minh có đơn
- Dashboard

---

## 3. Việc tiếp theo (làm ngay)

1. ~~Lấy `GROQ_API_KEY` → tạo `.env`~~ ✅
2. **[Bạn]** M0: kiểm tra điều kiện TikTok Shop Affiliate, bật showcase, thêm 1 sản phẩm vào showcase
3. **[Bạn]** Điền sản phẩm đó vào `products.csv` (kèm 2–3 ảnh)
4. Chạy `demo.py --csv products.csv` → đăng tay theo `post.txt` → **video đầu tiên lên sóng**

---

## 4. Nhật ký video đã đăng

| Ngày | Sản phẩm | Hoa hồng | Hook style | Thời lượng | Views (48h) | Click giỏ hàng | Đơn | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| 2026-10-20 | OMNIEAR tai nghe khuếch đại âm thanh | ? | story (con gái + mẹ) | 23.4s | | — (chưa gắn được giỏ hàng) | | Kênh SDC. Đăng tay, đã gắn nhãn AI. Thiếu mục "Sản phẩm" khi đăng → tài khoản chưa bật affiliate |

---

## 5. Vấn đề / quyết định đang mở

- **Không thấy mục "Sản phẩm" khi đăng (2026-10-20) dù tài khoản đã bật affiliate:** nghi do OMNIEAR chưa có trong showcase, hoặc người bán chưa mở hoa hồng affiliate cho sản phẩm này (sản phẩm đang chạy quảng cáo chưa chắc mở affiliate).
- **Đăng tự động:** API không gắn được giỏ hàng → hướng chọn: API đẩy video vào hộp thư nháp theo lịch + gắn sản phẩm tay ~30s/video. Trước mắt dùng TikTok Studio web để hẹn giờ.
- **Lấy dữ liệu sản phẩm TikTok Shop:** trang sản phẩm chặn bằng captcha khi truy cập tự động → không lấy được giá, ảnh phụ, mô tả. Link chia sẻ (`vt.tiktok.com/...`) chỉ cho tên + 1 ảnh (trong tham số `og_info`). Tạm thời: giá + thêm ảnh điền tay vào `products.csv`. Đổi đuôi URL ảnh thành `~tplv-aphluv4xwc-origin-jpeg.jpeg` để lấy ảnh gốc 2048px.
- **Sản phẩm nhạy cảm (sức khỏe):** điền ràng buộc vào cột `notes` (vd OMNIEAR: không phải thiết bị y tế, không chữa lãng tai). Luôn đọc lại script trước khi đăng.
- **Ảnh AI:** Pollinations miễn phí không dùng được (ảnh 576px, có watermark, sai prompt, sau đó trả 402). Đã chọn Gemini API (khoảng 0.04 USD/ảnh nếu hết free tier).
- **Không dùng nhân vật phim / người nổi tiếng:** vi phạm bản quyền / hình ảnh cá nhân, TikTok có thể gỡ video hoặc khoá tính năng affiliate. Chỉ dùng nhân vật AI tự tạo + bật nhãn "Nội dung do AI tạo".
- **Groq hiện chỉ có** `gpt-oss-120b`, `gpt-oss-20b`, `qwen/qwen3.8-27b` cho text (kiểm tra 2026-10-20).
- **Gắn giỏ hàng qua API:** theo tài liệu công khai, Content Posting API không có tham số gắn sản phẩm TikTok Shop. Nghĩa là dù API được duyệt, bước gắn sản phẩm vẫn phải làm tay trong app. Cần kiểm tra lại khi có quyền truy cập.
- **Backend đã merge từ bản update (2026-11-05):** adapter e-commerce (Shopee, Lazada, Google Sheets), TikTok OAuth, API `ecommerce`/`pipeline`/`social`, specs đổi tên `shopee-sync` → `ecommerce-sync`, `tiktok-publish` → `social-publish`. Mới kiểm tra import (18 route), chưa test với Postgres/Redis/API thật.
- **Shopee tạm dừng (quyết định 2026-11-05):** ưu tiên TikTok, không làm thêm gì liên quan Shopee. Code giữ lại nhưng tắt: `SHOPEE_ENABLED=false`, nút dashboard bị vô hiệu, `scripts/run_perfume.py`, `scripts/run_suitcase.py`, `scripts/test_workflow.py`, `scripts/test_pw.py` thoát ngay khi chạy. Khi làm lại: bật cờ và gỡ dòng `raise SystemExit` ở đầu các script.
- **Quyết định nghiệp vụ (từ session 2026-06-26):** niche Nhà cửa, Công nghệ, Đồ bếp, Phụ kiện ô tô · giá mục tiêu 100K–500K ₫ · commission ≥10% · budget 1–2 triệu ₫/tháng × 6 tháng.
- **TikTok app review (từ session 2026-06-26):** quy trình mới ở `docs/operations/tiktok-demo-recording.md`. Chỉ xin 2 scope: `user.info.basic`, `video.upload`, không dùng `video.publish`. Ghi chú cũ lưu ở tag `archive/docs-sa-requirement-design`.
- `.env.example` vẫn liệt kê `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` (phương án C). Giai đoạn này chỉ cần Groq.
