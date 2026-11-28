# TODO — TikTok Shop Affiliate Pipeline

> Theo dõi tiến độ **riêng phần TikTok Shop Affiliate**: tìm sản phẩm trên TikTok → script → video → đăng TikTok (gắn giỏ hàng) → analytics.
> Cập nhật file này mỗi khi xong 1 việc. Thiết kế chi tiết xem `docs/specs/`, chiến lược xem `FEASIBILITY.md`.
>
> **Ngoài phạm vi hiện tại:** mọi thứ liên quan đến Shopee (sync, API, link affiliate Shopee).
>
> Ký hiệu: ✅ xong · 🟡 đang làm / làm dở · ⬜ chưa làm · ⛔ bị chặn (chờ bên ngoài)
>
> Cập nhật lần cuối: 2026-11-22

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
| 4 | TTS + Video | ✅ | `demo.py`: edge-tts + hook → 1 cảnh/ảnh sản phẩm (tối đa 10) → CTA, zoom chậm, chữ tránh vùng UI TikTok | Chưa dùng clip video sản phẩm (chỉ ảnh) |
| 5 | Duyệt thủ công | ✅ | Trang **Studio** `http://127.0.0.1:8000/studio` (DR-0001, DR-0007): tạo video sản phẩm mới (từ link TikTok hoặc dòng Google Sheet, thêm ảnh, nhập/sửa giá có đọc chữ tiếng Việt), xem, sửa caption/hook/giá/lời đọc/ảnh, dựng lại, duyệt. `APPROVAL_MODE=terminal` giữ cách y/n cũ | — |
| 6 | Đăng + gắn giỏ hàng | 🟡 | Đăng tay: `post.txt` (caption + checklist) cạnh mỗi video · `tiktok_service.py` cho API sau này | API chờ TikTok duyệt. Gắn sản phẩm làm tay trong app (xem §5) |
| 7 | Analytics | ⬜ | `get_video_stats()` trong `tiktok_service.py` | Chưa thu thập; tạm ghi tay ở §4 |

**Tóm lại:** công cụ tạo video + bộ đăng tay đã sẵn sàng. **Đang thiếu:** tài khoản đủ điều kiện affiliate (M0), sản phẩm thật trong `products.csv` (M1), `GROQ_API_KEY`.

### Cách chạy

```bash
# Lần đầu
python3 -m venv .venv && .venv/bin/pip install -r requirements-demo.txt
cp .env.example .env      # điền GROQ_API_KEY

# Tạo video trên web Studio (khuyên dùng): bấm đúp scripts/mo-studio.command → "+ Tạo video mới"
# Hoặc tạo từ CLI:
.venv/bin/python demo.py --sheet-row 2
.venv/bin/python demo.py --csv products.csv
.venv/bin/python demo.py --product "Tên SP" --price 189000 --images a.jpg,b.jpg --points "Ý 1|Ý 2|Ý 3"
```

Kết quả nằm trong `storage/videos/<ngày>_<tên-sp>/`: `video.mp4`, `post.txt` (caption + checklist đăng), `script.json`, `audio_N.mp3`.

Tạo mới, duyệt và sửa: bấm đúp `scripts/mo-studio.command` → trang Studio (`http://127.0.0.1:8000/studio`). Video mới dừng ở `status=review`, duyệt trên web (DR-0001, DR-0007).

Style `story` (mặc định) cần ảnh nhân vật:
1. Lần chạy đầu tạo `video.mp4` bản nháp + `prompts.txt` (nhãn **Cần ảnh** trên Studio)
2. Mở Gemini app, dán gợi ý từng cảnh (nút **Chép gợi ý tạo ảnh**) trong cùng 1 chat → tải ảnh → **Tải ảnh lên** từng cảnh trên Studio
3. **Dựng lại video** trên Studio (không gọi lại AI, giữ nguyên script và giọng). Cách cũ vẫn chạy: `canh_N.png` + `demo.py --rerender`
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
- [x] Bug #41 (2026-11-28): ghi chú quyết định câu chuyện và giọng nam/nữ (`scripts/check_persona.py`). Còn lại: kịch bản có thể bỏ sót chứng chỉ/chứng nhận → người vận hành sửa tay khi duyệt

### M2b — Giọng đọc, lưu trữ (2026-11-11)
- [x] Giọng Gemini TTS có chỉ dẫn cảm xúc thay edge-tts; tự cắt tiếng xoẹt ở mép mỗi câu
- [x] Chọn giọng theo sản phẩm: điện tử / máy móc / tập luyện → nam Hà Nội; sức khỏe / gia đình / còn lại → nữ Sài Gòn
- [x] Video đã duyệt tự tải lên Google Drive (`video_output/<sản phẩm>/`) rồi xoá bản trên máy
- [x] Video sản phẩm đầu tiên có giỏ hàng: Bột mè đen (2026-11-11)

### Giọng đọc (2026-11-13)
- [x] Hết tiếng xoẹt khi chuyển cảnh: Gemini để lại tiếng nổ ~40 ms (−6 dB) cách mép ~20 ms im lặng, hàm cắt cũ
      bỏ sót. Đã sửa `_trim_gemini_edges`; dựng lại (Studio / `--rerender`) tự làm sạch audio cũ, không gọi lại TTS
- [x] Giọng dự phòng: Gemini chính → `GEMINI_TTS_FALLBACK_MODELS` (2 model Gemini khác, 10 lượt/ngày mỗi model)
      → edge-tts. Cả video dùng một model; Studio đọc lại câu sửa bằng đúng model đó
- [ ] Gemini TTS đôi khi đọc bịa thêm câu (trà ô long: "mình mới mua… 120 ngàn"): cân nhắc tự kiểm bằng
      Whisper (Groq) sau khi đọc giọng. DR-0004 thêm cách kiểm tay cho agent (`/audio-check`, `scripts/transcript_check.py`);
      tự chạy trong pipeline/Studio cần DR riêng (DR-0004 Q-5, mặc định: để sau)

### M2c — Video bài tập hằng ngày, không bán hàng (2026-11-12)
Khung mọi chuỗi bài: **mở đầu** (gợi tò mò, nguồn gốc, dành cho ai, 1–2 điểm nổi bật có nguồn, tập khi nào) → **mỗi ngày 1 động tác** → **tổng kết** ≤ 3 phút.
- [x] `exercise.py` + `content/exercise_curriculum.json`: lời đọc lấy nguyên văn giáo trình, không qua AI
- [x] Bát Đoạn Cẩm: 8 động tác (đã duyệt), video mở đầu, video tổng kết
- [x] Clip đúng động tác làm bằng app Gemini theo `storage/clips/bdc/prompts_*.txt`; thiếu clip thì dừng trước khi đọc giọng
- [x] Clip bài 1 (01_1…01_4), bài 1 đã duyệt (2026-11-13)
- [x] Dựng: clip ngắn hơn lời đọc thì chạy tới-lui thay vì nhảy về đầu (hết giật); `angles` trong giáo trình
      (bài 2, 5, 6, 7, 8) thêm clip góc nghiêng/sau `NN_K_side|back.mp4`, hiện ở khung nhỏ cạnh clip chính
- [x] Khung cảnh cố định cho mọi clip: mô tả địa điểm chi tiết trong `character_en`; mỗi prompt một chat mới
- [x] Video mở đầu làm lại: đủ 6 clip đồng bộ `intro_1…6` trong `storage/clips/bdc/`, đã dựng `20261113_183051_baitap_bdc_00_gioithieu` (51.8s, 6 cảnh) và tải lên Google Drive (2026-11-13)
- [x] Marketing review video mở đầu (`marketing-review.md`) → tinh chỉnh dựng bài tập: cắt khoảng lặng đầu/cuối audio
      (chuyển cảnh 1,3s → 0,46s), hoà hình 0,3s giữa cảnh, xuất 24 fps theo clip Gemini, che dấu ✦ Gemini (delogo),
      dòng "không phải phương pháp chữa bệnh" ở cảnh cuối video mở đầu, rút gọn chữ cảnh 3 và 5. Video còn 46,9s (2026-11-13)
- [ ] Bản trên Google Drive là bản cũ 51,8s → thay bằng `video.mp4` mới trong thư mục local
- [ ] Gemini app không nhận ảnh khung đầu (ảnh người thật → lỗi) nên chưa khoá được nền bằng ảnh tham chiếu
- [ ] Đăng video mở đầu Bát Đoạn Cẩm, rồi bài 1
- [ ] Thái Cực Quyền 24 thức: soạn bước từng thức + mở đầu + tổng kết, người vận hành duyệt
- [ ] (Sau) Chuỗi Tabata không dụng cụ theo cùng khung

### M2d — Video du lịch Việt Nam tiếng Anh, không bán hàng (2026-11-15)
Capability mới `travel-content`: mỗi video trả lời 1 câu hỏi thật của du khách (visa, đi lại, văn hoá, ẩm thực),
giọng Mỹ + phụ đề tiếng Việt, mọi câu có nguồn uy tín. Thiết kế: DR-0002, `docs/specs/architecture/capabilities/travel-content.md`.
- [x] Lập kế hoạch, người dùng chốt: kênh hiện tại · giọng Mỹ · hình Pixabay / nguồn có giấy phép · có phụ đề VI (2026-11-15)
- [x] DR-0002 + spec L3
- [x] Người dùng duyệt DR-0002 (merge PR #11, 2026-11-15)
- [x] P0: hồ sơ `content/travel/` (điểm đến `vn`, đối tượng `en-us`, `pillars.json`) + 30 câu hỏi đầu ở `content/travel/seed-questions.csv` (2026-11-16, nhánh `feat/travel-p1`). Chi tiết thực thi: spec `travel-content.md` § Chi tiết thực thi P1
- [x] DR-0008 (supersedes C-0002-1, C-0002-2, D-11; số 0008 vì 0002–0007 thuộc nhánh khác): fact quá hạn chặn `--approve` bằng exit 6 (`demo.py --travel --refresh-facts DIR` để làm mới), kiểm số cả `subs`/`hook`/`caption`; P1 chỉ edge-tts; không upload `clip_*`/`img_*` lên Drive. Người dùng duyệt 2026-11-16
- [x] 2 hàng `skip` đã chốt nguồn (2026-11-16): hộ chiếu chỉ dùng trang visa-requirements, tàu Bắc-Nam chỉ dùng FAQ; hết `skip` trong `seed-questions.csv`
- [ ] **[Bạn]** Tạo tab `Travel` trên Google Sheet: Tệp → Nhập → tải `content/travel/seed-questions.csv` lên
- [ ] **[Bạn]** Nghe video phở (V-2) khi có, ghi từ đọc sai (tên món, địa danh Việt) để sửa `pronunciations` trong `content/travel/destinations/vn.json`
- [x] Bug [#15](https://github.com/chungkhoantony1983/tt-affiliate/issues/15): đã sửa (2026-11-19). `demo.py` chạy là `__main__` nên `exercise.py`/`travel.py` nạp bản `demo` thứ hai; thêm `sys.modules.setdefault("demo", ...)` trước `main()` để dùng chung một bản (`--keep-local` và các biến toàn cục khác nay khớp)
- [ ] **v2 (DR-0010, đề xuất 2026-11-18, nhánh `feat/travel-story`)**: sau video phở đầu (hình lạc đề, ~15 s, giọng "mùi AI"): bản sửa lần 2 sau review Tech Lead + Marketing: phần 10a = video 4 nhịp 60–90 s, thư viện cảnh quay riêng + kiểm khớp hình (thiếu cảnh quay → dừng trước khi gọi AI, mã 8), dissolve frame-exact, edge-tts cải tiến, không Gemini. Gemini = DR-0010b sau khi `gemini-quota` merge. Chi phí chạy video $0; Veo/Flow không chọn. Bạn đã chốt (2026-11-18): làm 10a trước, Gemini để 10b (U1) · 3–4 video/tuần (U2) · phụ đề VI tắt mặc định, vẫn viết để xem trên Studio (U3) · video đầu không nêu tên quán (U4). **Chờ: bạn xác nhận duyệt DR + U5 (bạn tự quay ≥ 16 clip, 2 buổi) và U6 (thứ tự merge #17 → gemini-quota → studio-create-video → 10a → 10b); 2 mục này là giả định, chưa xác nhận**
- [ ] Nợ kỹ thuật (Tech Lead 2026-11-16): tách phần dựng clip dùng chung của `exercise.py` / `travel.py` ra `clipkit.py`. `_pingpong` (filter `reverse`) giữ mọi khung hình trong RAM: đo được 688 MB cho clip 720×1280 10 s
- [ ] **[Bạn]** Video visa người Mỹ (V-1): travel.state.gov chặn tải tự động, cần mở trang bằng trình duyệt và chép câu về visa vào cột `facts_manual` (dạng `claim | quote | url`)
- [ ] Nợ kỹ thuật travel (kiểm cuối 2026-11-17, không chặn merge):
  - UX Studio: sau khi Drive lỗi, danh sách vẫn gắn nhãn "Đã duyệt" vì `_label()` chỉ dựa vào `post.txt` (ghi trước khi upload). Đề xuất: ghi dấu riêng (vd `drive.ok`) sau upload thành công, hoặc đọc kết quả job gần nhất; banner và nút Duyệt lại vẫn đúng
  - Reviewer gợi ý: hook dài cắt bằng "…" có thể kết thúc giữa cụm ("…from the…"); Studio báo "N dữ kiện bị ẩn" khi snapshot thiếu danh sách nguồn dù dữ kiện vẫn hiện (không link); tiền tố `refresh.` bỏ qua khi upload Drive hiện chỉ khớp `refresh.log`
  - Đo lại RAM dựng trên máy thật (ffmpeg đỉnh 509 MB với clip 4K trong môi trường kiểm; chưa đo trên máy nhà)
- [ ] Nợ kỹ thuật travel (BA ghi 2026-11-16):
  - Tách `travel.py` (khoảng 2000 dòng) thành `travel_render.py` / `travel_media.py` khi thêm TTS thứ hai hoặc nguồn media thứ 4
  - Module helper dùng chung cho `demo.py` / `exercise.py` / `travel.py` (hiện `travel.py` gọi hàm riêng tư `demo._font`, `_slug`, `_text_block`, `_wrap_px`, `_extract_json`, `_ffmpeg_bin`, `exercise._clip_info`, `_speech_bounds`)
  - Studio: nút **Làm mới nguồn** (hoặc file bấm đúp `.command`) thay cho dán lệnh vào Terminal khi gặp exit 6
  - Kiểm DNS-rebinding / IP riêng khi tải trang nguồn: chấp nhận, rủi ro thấp (chỉ tải host trong danh sách cho phép, https, không cổng lạ)
  - Ghim phiên bản các gói còn lại trong `requirements-demo.txt`: `pillow`, `mutagen`, `groq`, `gspread` (mới ghim `edge-tts==7.3.1`)
- [x] Bug [#16](https://github.com/chungkhoantony1983/tt-affiliate/issues/16): đã sửa (2026-11-19). `move_to_drive` trả `status=drive_failed` khi lỗi, `--approve` thoát mã 7 (như travel), không cập nhật Sheet, giữ thư mục + `post.txt`; Studio hiện thông báo Drive lỗi. Luồng bài tập: lỗi Drive cũng giữ thư mục nhưng curriculum đã đánh dấu done trước đó (nợ nhỏ)
- [x] Thiết kế mở rộng: thêm nước / chủ đề / đối tượng = thêm hồ sơ JSON, không sửa code (C-0002-5, 2026-11-15)
- [x] P1 (code): `travel.py` (research → check nguồn → script EN/VI → Pixabay/Pexels/Wikimedia → edge-tts en-US → dựng), Studio nhận thư mục travel, `--refresh-facts [--confirm]`, mã thoát 5/6/7. Reviewer cuối 0 Chặn / 0 Nên sửa, Tester cuối toàn PASS (2026-11-17), kết quả chi tiết ở DR-0008 § Kết quả. P1 chưa đóng hẳn: còn chờ bạn chạy dữ liệu thật (dòng **[Bạn]** bên dưới)
- [x] Merge `feat/travel-p1` (PR #17) và `feat/gemini-quota` (PR #24) vào `main`. Hai DR trùng số 0002 đã đổi số: clip-trim → DR-0009, gemini-quota → DR-0012 (kiểm 2026-11-19). `feat/studio-create-video` (DR-0007) đã merge (PR #26). Việc kiểm sau merge: DR-0008 § Kết quả
- [x] **V-0 nghe thử model Gemini phụ (DR-0012, 2026-11-20, người dùng nghe):** `gemini-3.1-flash-tts-preview`: không đọc chỉ dẫn, giọng Bắc đúng, đổi chữ nhỏ nhưng giữ ý, phân biệt mẹ/con rõ, vai mẹ "quá AI"; câu 5: người dùng thấy khác giọng chính (chưa nghe so trực tiếp), nhưng **chọn giữ** làm giọng phụ vì một video chỉ dùng một model (C-0012-1) và giọng giống người hơn; Studio vẫn ghi "Gemini phụ" trước khi duyệt. **Giữ trong mặc định.** `gemini-2.5-flash-preview-tts`: đọc sai chữ khi kịch bản đúng ("liên tục" → "liên túc"). **Đã gỡ khỏi `DEFAULT_TTS_FALLBACK_MODELS`** (PR chore/v0-fallback-models). Còn mở: chưa nghe giọng nữ Sài Gòn
- [ ] **[Bạn]** Việc còn lại để P1 xong: dán `seed-questions.csv` vào tab `Travel`; đặt `PEXELS_API_KEY` trong `.env` nếu muốn (tuỳ chọn); nghe phát âm trên video phở; dán `facts_manual` cho video visa người Mỹ; chạy video thật đầu tiên (`demo.py --travel --sheet`)
- [ ] P2: đăng 10–15 video, ghi % người xem US / CA / AU vào §4
- [ ] P3 (DR riêng): tự tìm chủ đề xu hướng (YouTube Data API, Google Trends)

### M2e — Xuất sang CapCut (DR-0013, issue #36, 2026-11-23)

- ✅ Code: `capcut_export.py`, `demo.py --capcut` / `--voice`, nút Studio "Xuất sang CapCut", chọn giọng khi tạo, `tools/capcut-mcp` (hiệu ứng theo bối cảnh, giọng edge-tts theo cảnh, công cụ `affiliate_*`)
- ⬜ Chờ người dùng thử trên CapCut thật (Mac, CapCut 9.8): mở dự án có tiếng, ảnh, chữ, hiệu ứng (E2E-3)
- Khung dự án CapCut 9.8 (`skeleton_v9`) để ngoài git: `~/.capcut-mcp/skeleton_v9`

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
| 2026-11-11 | Bột mè đen | 10% | simple, giọng Gemini nữ Sài Gòn | 19.3s | | | | Đã hiện giỏ hàng |

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
- **Studio duyệt & sửa video (DR-0001, 2026-11-12) + Tạo video sản phẩm mới trên Studio (DR-0007, 2026-11-14):** trang riêng `/studio` do service `creator_main` phục vụ, không đụng `app.html` (đang xét duyệt). Hỗ trợ tạo video mới từ link TikTok Shop hoặc dòng trên Google Sheet (`>= 2`), xem trước thông tin (`og_info` fallback khi bị chặn), tải tối đa 3 ảnh sản phẩm đầu vào, nhập/sửa giá có đọc số thành chữ tiếng Việt (ghi đè lên Sheet và kịch bản AI). Mọi xử lý video vẫn ở `demo.py` (`--create-json`, `--sheet-row`, `--render-only`, `--approve`, `--revoice-all edge`). Sửa lời đọc chỉ đọc lại câu đã sửa, bằng đúng bộ giọng của video; Gemini lỗi thì không đổi audio nào. Mỗi câu sửa trên video Gemini tốn 1 lượt, tạo video mới tốn ~4 lượt (10/ngày).
- **Đội vai trò AI (2026-11-12):** subagent `ba`, `dev`, `reviewer`, `tester`, `marketing` trong `agent/agents/`. Lệnh `/feature` (làm tính năng theo vai trò, có cổng duyệt DR) và `/video-review` (marketing review video trước khi duyệt). Đặt ở `agents/` và `commands/` vì `/sync` xoá mọi skill lạ trong `agent/skills/`. Các skill SSoT `/task`, `/fix` bị kẹt vì `workflow_step.py` thiếu module `automation_engine`. Lần chạy thử marketing trên video Bột mè đen phát hiện khung CTA "BẤM GIỎ HÀNG VÀNG" rộng gần hết màn hình, lấn sang cột nút bên phải của TikTok (đề xuất cho Dev, chưa sửa).
- **Duyệt trước khi dựng (DR-0011, đã duyệt 2026-11-19):** cổng duyệt kịch bản / ảnh nhân vật / hình từng cảnh trên Studio TRƯỚC khi đọc giọng và dựng, cho video sản phẩm, bài tập, du lịch. Làm theo thứ tự du lịch → sản phẩm → bài tập, hạ tầng chỉ sau khi PR #17 merge. `--skip-approval` vẫn dừng ở cổng kịch bản (bỏ hết cần `--no-gates`). Chi tiết: `docs/decision-records/DR-0011-duyet-truoc-khi-dung.md`.
- **MCP tạo dự án CapCut (2026-11-22, `tools/capcut_mcp/`):** MCP server (Python, MCP SDK v2) cho Claude dựng draft CapCut desktop: clip/ảnh, chữ, phụ đề SRT, giọng đọc, nhạc, mờ dần, zoom, chuyển cảnh thư viện (id lấy từ dự án có sẵn). CapCut không có API chính thức và không tự xuất .mp4: người dùng mở CapCut để xuất. Chưa thử mở draft trong CapCut thật; CapCut 8.7+/9.x nên ghi vào dự án trống do CapCut tạo (`into_existing`). 33 test `pytest` trong `tools/capcut_mcp/tests/`.
  - [ ] **[Bạn]** Thử 1 draft ngắn trên máy có CapCut, ghi lại bản CapCut và kết quả (mở được / bị từ chối)
- **Skill cho agent vai trò (DR-0004, nhánh `feat/agent-skills`, chưa merge):** 4 skill mới trong `agent/commands/` (`sandbox-render`, `audio-check`, `voice-rules`, `dr-draft`) + 3 script `scripts/sandbox_render.py`, `scripts/audio_seams.py`, `scripts/transcript_check.py`. Chi phí $0, 0 lượt Gemini (Groq Whisper miễn phí). **Trạng thái 2026-11-19: đã sửa vòng 1 và vòng 2, reviewer + tester kiểm lại đạt (7/7 ca), chờ V-1 và PR.** Quyết định vòng 1: `sandbox-render` chưa nhận thư mục travel (báo rõ), `transcript_check` từ chối thư mục travel, kết quả đo bản sao tách khỏi video thật, `post_txt_created` thay `post_txt_in_copy`, sửa frontmatter `travel-review.md` để nạp được skill. Chưa kiểm V-1 (nạp sẵn thực tế). Đồng bộ `.agents/` (Antigravity) để issue riêng [#27](https://github.com/chungkhoantony1983/tt-affiliate/issues/27). Số DR trống tiếp theo (quét 2026-11-19): **0013**.
  - [ ] Nợ kỹ thuật: `sandbox-render` hỗ trợ thư mục travel (chạy `demo.py --render-only` bằng subprocess với cùng `SAFE_ENV`; cần soát trước `travel.main_existing` không ghi Sheet/Drive). Ước lượng của người điều phối: khoảng 1–2 giờ
  - [ ] Nợ kỹ thuật: `scripts/review_frames.py` dùng cùng `output_dir()` như `audio_seams.py` (bản sao ghi vào `<thư mục>__sandbox/`); hiện khung hình của bản sao ghi đè khung hình của video thật cùng tên
  - [ ] Nợ kỹ thuật: renderer ghi `scene_start` / `scene_dur` vào `script.json` để `audio_seams.py` khỏi tự dựng lại mốc cảnh; gộp các hàm `parse_scenes` đang trùng
  - [ ] Nợ kỹ thuật: `transcript_check.py` hỗ trợ tiếng Anh cho video travel
  - [ ] Bug cần ghi issue riêng qua `/bug` (chưa tạo): (1) edge-tts không có timeout cho từng lần thử (vòng thử trong `demo.py`, dòng 806–815 sau khi rebase lên 4e348dc), mạng treo thì lệnh treo; (2) `--revoice-all edge` hỏng giữa chừng để lại thư mục trộn giọng cũ và mới, trái C-0001-1
- `.env.example` vẫn liệt kê `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` (phương án C). Giai đoạn này chỉ cần Groq.
