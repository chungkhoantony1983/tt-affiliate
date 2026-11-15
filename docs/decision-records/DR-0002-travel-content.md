# DR-0002: Video du lịch, văn hoá, ẩm thực Việt Nam bằng tiếng Anh (travel-content)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📝 Chờ duyệt | 2026-11-15 | Claude (BA) | chungkhoantony1983 (đã chốt kênh, giọng, hình ảnh, phụ đề ngày 2026-11-15; chờ duyệt DR) |

Capability: `travel-content` (mới) · Nhánh: `claude/project-thread-keb356` · Spec: `docs/specs/architecture/capabilities/travel-content.md`

Vai trò: **BA** viết DR + tài liệu · **Dev** code · **Reviewer** soát diff · **Tester** chạy bảng quyết định · **MKTG** review video (chế độ 1) và Studio (chế độ 2).

---

## Bối cảnh

**Vấn đề**: kênh hiện chỉ có video bán hàng (tiếng Việt) và video bài tập. Người dùng muốn thêm dòng video tiếng Anh giới thiệu du lịch, văn hoá, ẩm thực Việt Nam cho người nói tiếng Anh (Mỹ, Canada, Úc) và người Việt, trả lời những câu hỏi du khách thật sự đang tìm, lấy từ nguồn uy tín.

**Khác video sản phẩm**:

- Không bán hàng: không giỏ hàng, không CTA mua.
- Nội dung là **dữ kiện** (visa, phí, phép lịch sự, món ăn). Sai một con số visa là mất uy tín kênh. Vì vậy AI không được viết tự do: mọi câu phải trỏ về một trích dẫn nguyên văn từ trang nguồn được phép.
- Tiếng Anh: giọng đọc, chữ trên màn hình, caption, hashtag. Phụ đề tiếng Việt chạy kèm.

**Quyết định của người dùng (2026-11-15)**:

| # | Câu hỏi | Chốt |
|---|---------|------|
| U-1 | Kênh | Đăng trên **kênh TikTok hiện tại** |
| U-2 | Giọng | **Giọng Mỹ** |
| U-3 | Hình ảnh | **Pixabay hoặc nguồn trên Internet**, hiểu là nguồn có giấy phép cho dùng lại (Pixabay, Pexels, Wikimedia Commons CC/PD), ghi nguồn và giấy phép từng clip/ảnh |
| U-4 | Phụ đề tiếng Việt | **Có** |

**Ràng buộc hiện có**: chi phí $0 (P02); Gemini TTS 10 lượt/ngày mỗi model, đã chia cho video sản phẩm và bài tập; C-0001-1 (một bộ giọng/video); C-0001-2 (xử lý video chỉ ở script Python, Studio chỉ chạy subprocess); C-0001-4 (không đổi `app.html`); không có test suite.

Kế hoạch tổng thể (trụ cột nội dung, lộ trình P0–P3): doc "Kế hoạch capability travel-content" (claude.ai artifact, 2026-11-15). DR này chốt **P0 + P1** và phác P3.

---

## Quyết định

> **Thêm module `travel.py` (gọi qua `demo.py --travel`), theo khuôn `exercise.py`. Chủ đề lấy từ tab `Travel` trên Google Sheet. Với mỗi chủ đề, code tải các trang nguồn trong danh sách cho phép, Groq trích dữ kiện kèm trích dẫn nguyên văn, code kiểm trích dẫn có thật trong trang, Groq viết lời đọc tiếng Anh + phụ đề tiếng Việt chỉ từ các dữ kiện đó, code kiểm lại mọi con số. Hình là clip Pixabay / Pexels và ảnh Wikimedia Commons có giấy phép. Giọng Mỹ bằng edge-tts. Duyệt trên Studio như video sản phẩm.**

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Module riêng `travel.py`, dùng lại TTS / Drive / Sheet của `demo.py` và hàm dựng clip của `exercise.py` | ⭐ | Không đụng luồng sản phẩm. Khuôn đã chạy ổn với bài tập. Một nơi chứa logic travel |
| B | Thêm `style=travel` vào `generate_script` + `render_video` của `demo.py` | - | `render_video` xoay quanh ảnh sản phẩm, giá, CTA giỏ hàng; nhồi thêm nhánh làm hàm khó đọc, dễ hồi quy video bán hàng |
| C | Để Groq tự viết từ kiến thức sẵn có, người vận hành soát | - | Không kiểm được nguồn; model hay bịa số (đã thấy với thông số sản phẩm). Trái nguyên tắc "chỉ dùng số có nguồn" |
| D | Giáo trình JSON viết tay như `exercise_curriculum.json` | - | Chắc chắn đúng nhưng người vận hành phải tự viết mọi câu tiếng Anh. Giữ làm đường lui: cột `facts_manual` (xem Dữ liệu) |

**Giọng**: edge-tts `en-US-AndrewNeural` (nam) / `en-US-AvaNeural` (nữ), mặc định nam. Lý do: miễn phí không giới hạn, không ăn quota Gemini của video sản phẩm và bài tập. Gemini TTS bật được bằng `TRAVEL_TTS_PROVIDER=gemini` (khi đó dùng model riêng `TRAVEL_GEMINI_TTS_MODEL`). Tên giọng edge-tts cụ thể Dev kiểm lại bằng `edge-tts --list-voices` lúc làm.

---

## Thay đổi cấu trúc

### Dữ liệu

| Đối tượng | Nội dung |
|-----------|----------|
| Google Sheet, tab `Travel` (mới) | Cột: `question` (câu hỏi tiếng Anh, làm hook), `pillar` (`prep` / `getting-around` / `culture` / `food` / `places`), `source_urls` (mỗi dòng 1 URL, phải thuộc danh sách cho phép), `notes`, `facts_manual` (tuỳ chọn), `status`. `TRAVEL_SHEET_COLUMNS` trong `product_sources.py` |
| `content/travel_sources.json` (mới) | Danh sách nguồn cho phép: `domain`, `name`, `tier` (1 = cơ quan nhà nước / tổ chức quốc tế, 2 = báo chính thống, cẩm nang uy tín), `pillars`. Danh sách đầu tiên ở spec |
| `content/travel_pronunciations.json` (mới) | Cách đọc tên Việt cho giọng Mỹ, vd `"Phở": "fuh"`, `"Hội An": "hoy an"`. Chỉ đổi chữ gửi cho TTS, chữ trên màn hình giữ nguyên dấu |
| Thư mục video `storage/videos/<ngày>_travel_<slug>/` | Như video sản phẩm, **thay** `product.json` bằng `topic.json`; thêm `facts.json`, `credits.txt`, `clip_N.mp4` / `img_N.<ext>` |
| `topic.json` | `question`, `pillar`, `source_urls`, `notes`, `kind: "travel"` |
| `facts.json` | `[{id, claim, quote, url, source_name, tier, checked_on, volatile}]`. `quote` là đoạn nguyên văn có trong trang lúc tải; `volatile=true` cho visa, phí, giá, luật, giờ mở cửa |
| `script.json` | `lang: "en"`, `kind: "travel"`, `tts_provider`, `voice`, `hook`, `caption`, `hashtags`, `segments[]`: `kind` (`hook` / `answer` / `outro`), `line` (lời đọc EN), `line_vi` (phụ đề VI), `text` (chữ lớn EN, ≤ 6 từ), `fact_ids[]`, `media` (chỉ số trong `credits`), `audio_line`, `duration` |
| `credits.txt` + `script.json → media[]` | Mỗi clip/ảnh: `provider` (`pixabay` / `pexels` / `wikimedia`), `id`, `page` (URL trang), `author`, `license` (vd `Pixabay Content License`, `CC BY-SA 4.0`) |
| `status` (tab `Travel`) | Như tab sản phẩm: trống = cần làm; `review`, `done`, `skip`; thêm `needs_sources` (không trích được dữ kiện hợp lệ nào) |
| `.env` | `PEXELS_API_KEY` (tuỳ chọn), `PIXABAY_API_KEY` (đã có), `TRAVEL_TTS_PROVIDER` (`edge` mặc định), `TRAVEL_VOICE` (`en_us_male` mặc định / `en_us_female`), `TRAVEL_TAB` (`Travel`) |

### Luồng hệ thống

```
demo.py --travel [--sheet] [--tab Travel]
  → hàng đầu tiên status trống
  → research    tải từng source_url (chỉ domain trong travel_sources.json)
                → Groq trích fact {claim, quote} → code giữ fact có quote nằm nguyên văn trong trang
                → 0 fact hợp lệ: status=needs_sources, dừng (chưa tốn lượt TTS)
  → write       Groq viết segments EN + line_vi chỉ từ facts (id)
  → check       C-0002-1: mỗi segment answer có fact_ids hợp lệ; mọi con số trong line/text có trong quote
                của fact được trích; sai → gọi lại Groq 1 lần với danh sách lỗi → vẫn sai: dừng, status=needs_sources
  → media       mỗi segment: tìm clip Pixabay (bỏ hit gắn tag AI) → Pexels → ảnh Wikimedia Commons
                (chỉ giấy phép trong danh sách cho phép, C-0002-3); ghi credits
  → voice       edge-tts giọng Mỹ (hoặc Gemini nếu bật), chữ gửi TTS đã qua travel_pronunciations
  → render      1080×1920: clip phủ khung, chữ lớn EN phía trên, phụ đề EN + VI phía dưới (trong vùng an toàn),
                outro: "Info as of <tháng năm> · Source: <tên nguồn>" + "Check the official site before you go"
  → status=review, giữ thư mục → Studio
  → demo.py --approve DIR   → post.txt (caption EN + nguồn + credits) → Drive video_output/travel/<slug>/ → status=done
```

`demo.py --travel --render-only DIR` và `--approve DIR` tự nhận thư mục travel nhờ `topic.json`.

### Studio (DR-0001)

- `api/studio.py`: thư mục có `topic.json` được nhận là **travel**, không phải "Chỉ xem". Cho sửa `caption`, `hashtags`, `text`, `line`, `line_vi` từng cảnh; cho chạy `render` và `approve` (gọi `demo.py --render-only` / `--approve` như cũ).
- Trang Studio hiện thêm: danh sách dữ kiện (claim + nguồn, có link), ô phụ đề VI từng cảnh, credits. Đây là bước người vận hành **duyệt dữ kiện** ở P1 (gộp với duyệt video).
- Sửa `line` (EN) trên Studio: code chạy lại kiểm số (C-0002-1). Số mới không có trong quote → Studio báo lỗi, không dựng.

### Thao tác người vận hành

| Thao tác | Ở đâu | Tốn gì |
|----------|-------|--------|
| Thêm câu hỏi + 1–3 URL nguồn vào tab `Travel` | Google Sheet | $0 |
| Chạy `demo.py --travel --sheet` | Terminal (sau này nút trên Studio) | ~3–5 lượt Groq / video, $0 |
| Xem video, đọc dữ kiện + nguồn, sửa chữ / phụ đề, Dựng lại, Duyệt | Studio | $0 (edge-tts) |
| Đăng tay theo `post.txt` (không gắn sản phẩm) | App TikTok | $0 |

---

## Kế hoạch công việc

| # | Việc | Vai trò | Output | Vị trí |
|---|------|---------|--------|--------|
| 1 | Danh sách nguồn + cách đọc tên Việt + 30 câu hỏi đầu (từ FAQ vietnam.travel, Google Trends US/CA/AU) | BA | JSON + tab Sheet | `content/`, Sheet |
| 2 | Đọc tab `Travel`, `research` (tải trang, trích fact, kiểm quote), `write`, `check` | Dev | Code | `travel.py`, `product_sources.py` |
| 3 | `media`: Pixabay (dùng lại `exercise._pixabay_search` pattern), Pexels, Wikimedia Commons API; credits | Dev | Code | `travel.py` |
| 4 | Giọng Mỹ edge-tts + pronunciations; render clip + phụ đề EN/VI + outro nguồn | Dev | Code | `travel.py` (dùng `exercise._clip_input`, `_pingpong`, `demo._font`…) |
| 5 | CLI `--travel`, nhận thư mục travel ở `--render-only` / `--approve`; `post.txt` EN | Dev | Code | `demo.py`, `travel.py` |
| 6 | Studio nhận thư mục travel, hiện facts / phụ đề VI / credits | Dev + MKTG | Code + HTML | `api/studio.py`, `web/studio.html` |
| 7 | Checklist marketing cho travel (hook câu hỏi, phát âm, nguồn trên màn hình, tiếng Anh tự nhiên) | BA + MKTG | Docs | `agent/agents/marketing.md` |
| 8 | Review | Reviewer | Ghi chú | DR § Kết quả |
| 9 | Test theo bảng quyết định (Groq giả lập bằng file JSON có sẵn khi cần, edge-tts, không Drive/Sheet/Gemini thật) | Tester | V-x | DR § Kết quả |
| 10 | MKTG review 2 video mẫu (chế độ 1) | MKTG | `marketing-review.md` | thư mục video |
| 11 | Cập nhật tài liệu SSoT | BA | Docs | xem § SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Cách xử lý |
|---|------|----------|------------|
| R-1 | Rủi ro | Trang nguồn chặn truy cập tự động (captcha, 403) như trang TikTok Shop | Báo rõ URL nào lỗi. Đường lui: cột `facts_manual` (người vận hành dán `claim | quote | url`), vẫn qua C-0002-1 |
| R-2 | Rủi ro | Groq trích quote không nguyên văn | Code so khớp sau khi chuẩn hoá khoảng trắng / dấu nháy; không khớp thì bỏ fact |
| R-3 | Rủi ro | Dữ kiện đúng lúc dựng nhưng đổi sau khi đăng (visa) | Màn hình cuối ghi tháng năm; `--approve` từ chối nếu fact `volatile` có `checked_on` quá 30 ngày (C-0002-2) |
| R-4 | Rủi ro | Clip Pixabay không đúng địa danh (vd "Ha Long" ra cảnh Thái Lan) | Tìm theo từ khoá có tên địa danh + bắt buộc tag chứa "vietnam" hoặc tên địa danh; không có thì dùng ảnh Wikimedia Commons của đúng địa danh. MKTG soát ở bước duyệt |
| R-5 | Rủi ro | Kênh hiện tại có người xem Việt, thuật toán ít đẩy cho US/CA/AU | Chấp nhận theo U-1. Đo % quốc gia ở P2 (TikTok Analytics), ghi `TODO.md` |
| R-6 | Rủi ro | Phụ đề VI do Groq dịch sai chính tả | Model `qwen/qwen3.8-27b` (đã chọn vì đúng chính tả); người vận hành sửa `line_vi` trên Studio |
| R-7 | Rủi ro | Wikimedia Commons: giấy phép BY-SA yêu cầu ghi công đúng cách | Ghi tác giả + giấy phép + link trong `credits.txt` và caption; chữ nhỏ trên khung khi dùng ảnh BY/BY-SA |
| A-1 | Giả định | edge-tts có giọng `en-US-*Neural` chạy được từ máy nhà | Dev kiểm ở việc 4 |
| A-2 | Giả định | Pexels API miễn phí với API key | Không có key thì bỏ qua Pexels |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0002-1 | Mỗi segment `answer` có ≥ 1 `fact_id` hợp lệ. Mọi con số (tiền, ngày, %, số lượng) trong `line` / `text` phải xuất hiện trong `quote` của fact được trích. Code kiểm trước khi gọi TTS và trước khi dựng lại | Không có câu nào thiếu nguồn | `travel.py` | — |
| C-0002-2 | Fact `volatile` chỉ dùng khi `checked_on` ≤ 30 ngày; `--approve` từ chối (exit 4) nếu quá hạn. Màn hình cuối và caption ghi nguồn + tháng năm | Visa, phí, luật đổi thường xuyên | `travel.py` | — |
| C-0002-3 | Chỉ dùng clip/ảnh có giấy phép cho dùng lại, lấy qua API của Pixabay, Pexels, Wikimedia Commons (giấy phép: Pixabay/Pexels License, CC0, PD, CC BY, CC BY-SA). Mỗi media phải có `provider`, `page`, `license`; thiếu thì không dựng. Không lấy ảnh từ Google, Instagram, TikTok, blog | Bản quyền (U-3) | `travel.py` | — |
| C-0002-4 | Nguồn dữ kiện chỉ thuộc `content/travel_sources.json`. Dữ kiện visa / y tế / an toàn / luật phải có nguồn `tier=1`. Video loại này kết thúc bằng "Check the official site before you go" | Không tư vấn thay cơ quan chức năng | `travel.py` | — |

supersedes: —

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `docs/specs/architecture/capabilities/travel-content.md` | Spec L3 mới | [x] (bản thiết kế, cập nhật sau khi code) |
| `docs/specs/architecture/capabilities/video-render.md` | § Studio: thư mục travel | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Cách thêm câu hỏi + nguồn, chạy, duyệt, đăng video travel | [ ] |
| `.claude/CLAUDE.md` | Lệnh `--travel`, capability mới trong cấu trúc tài liệu | [ ] |
| `TODO.md` | Mốc M2d travel-content | [x] |
| `.env.example` | `PEXELS_API_KEY`, `TRAVEL_*` | [ ] |
| `agent/agents/marketing.md` | Checklist travel | [ ] |

## File code thay đổi (dự kiến)

- `travel.py` (mới), `content/travel_sources.json` (mới), `content/travel_pronunciations.json` (mới)
- `demo.py`: `--travel`, nhận thư mục travel ở `--render-only` / `--approve`
- `product_sources.py`: `TRAVEL_SHEET_COLUMNS`, đọc tab theo cột riêng
- `backend/app/api/studio.py`, `backend/app/web/studio.html`: thư mục travel
- Không đổi: `app.html`, `api/creator.py`, luồng video sản phẩm, `exercise.py` (chỉ import hàm)

---

## Tiêu chí hoàn thành (DoD)

### Bảng quyết định: code

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1 | `source_urls` có domain không thuộc danh sách cho phép | URL đó bị bỏ, log nêu tên domain | Chạy thật với URL giả |
| D-2 | Groq trả fact có `quote` không nằm trong trang | Fact bị bỏ | Hàm kiểm + JSON giả lập |
| D-3 | Không còn fact hợp lệ nào | `status=needs_sources`, không có file audio nào | Chạy thật |
| D-4 | Segment `answer` không có `fact_ids` / có id lạ | Bị chặn trước TTS | Hàm kiểm + JSON giả lập |
| D-5 | `line` có số `$30` nhưng quote chỉ có `US$25` | Bị chặn, lỗi nêu đúng số | Hàm kiểm |
| D-6 | Fact visa có nguồn `tier=2` | Bị chặn (C-0002-4) | Hàm kiểm |
| D-7 | Media thiếu `license` hoặc giấy phép ngoài danh sách | Không dựng | Hàm kiểm |
| D-8 | Hit Pixabay có tag "ai generated" | Bị bỏ | Hàm kiểm |
| D-9 | Dựng đủ | `video.mp4` 1080×1920, có phụ đề EN + VI, màn hình cuối có nguồn + tháng năm; `credits.txt` đủ dòng | Chạy thật (edge) + khung hình `scripts/review_frames.py` |
| D-10 | Tên Việt có trong `travel_pronunciations.json` | Chữ gửi TTS đã đổi, chữ trên màn hình còn dấu | Đọc `script.json` + log |
| D-11 | `--approve` với fact volatile `checked_on` 31 ngày trước | exit 4, thông báo tiếng Việt | Sửa ngày trên bản sao |
| D-12 | Studio: thư mục travel | Hiện facts, phụ đề VI, credits; sửa `line_vi` → Dựng lại → video mới; sửa `line` thêm số không có nguồn → lỗi, không dựng | TestClient + chạy thật |
| D-13 | Hồi quy: video sản phẩm (`--csv`, `--sheet`), `--exercise`, Studio thư mục sản phẩm / bài tập, `/api/creator` | Như cũ | Đọc diff + chạy `--style simple` trên CSV mẫu |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Cách kiểm |
|---|-----------|----------|-----------|
| DD-1 | `travel-content.md` | Khớp code thật (lệnh, cột, file) | Đối chiếu |
| DD-2 | Hướng dẫn vận hành | Có mục video travel, không chữ kỹ thuật thừa | MKTG chế độ 2 |
| DD-3 | `.claude/CLAUDE.md`, `TODO.md`, `.env.example` | Đồng bộ | Đối chiếu chéo |

### Kiểm tra E2E

| # | Hạng mục | Cách làm | Mong đợi |
|---|----------|----------|----------|
| V-1 | Video visa | Câu hỏi "Do Americans need a visa for Vietnam?", nguồn cổng e-visa + travel.state.gov | Mọi số trong video có trong `facts.json`, nguồn tier 1, outro có tháng năm |
| V-2 | Video ẩm thực | "What is the difference between Northern and Southern pho?", nguồn vietnam.travel | Clip đúng món / thành phố, phát âm "pho" đúng |
| V-3 | MKTG | Review V-1, V-2 | Không mức "Chặn" |
| V-4 | Người dùng | Nghe giọng Mỹ, đọc phụ đề VI | Người dùng xác nhận |

### Cổng chất lượng

- [ ] Đã kiểm hết bảng quyết định
- [ ] Không có hồi quy
- [ ] Không vi phạm ràng buộc hiện có
- [ ] Xong mọi việc trong kế hoạch
- [ ] Đã cập nhật tài liệu SSoT

---

## Ngoài phạm vi DR này

- **P3 tự động tìm chủ đề** (`travel.py discover`: YouTube Data API + Google Trends API alpha + chấm điểm → ghi top 10 vào tab `Travel`). Làm DR riêng sau khi 10–15 video đầu có số liệu (P2).
- Tự tìm URL nguồn cho câu hỏi (P3). P1 người vận hành dán URL.
- Nhắc kiểm lại video cũ khi luật đổi.
- Kiếm tiền từ video travel.

---

## Kết quả

(Điền sau khi triển khai.)

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| Kế hoạch | Doc "Kế hoạch capability travel-content" (2026-11-15) |
| Khuôn tham khảo | `exercise.py` (video không bán hàng, Pixabay, dựng clip), DR-0001 (Studio) |
| Nguồn đã mở khi lập kế hoạch | [vietnam.travel FAQ](https://vietnam.travel/node/143), [Vietcetera visa guide 2026](https://vietcetera.com/amp/en/vietnam-visa-immigration-master-guide-2026-comprehensive-legal-practical-framework) (tier 2, chỉ để định hướng), [Google Trends API alpha](https://developers.google.com/search/blog/2025/07/trends-api) |
