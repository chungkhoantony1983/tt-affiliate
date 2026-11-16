# Capability: travel-content

> **Mục đích**: Video ngắn trả lời một câu hỏi thật của du khách về du lịch, văn hoá, ẩm thực của một **điểm đến**,
> cho một **đối tượng** người xem, mọi câu có nguồn uy tín. Điểm đến, chủ đề, đối tượng là hồ sơ JSON: thêm nước,
> chủ đề hay đối tượng mới không cần sửa code (C-0002-5). Bản đầu: điểm đến `vn`, đối tượng `en-us`
> (tiếng Anh giọng Mỹ, phụ đề tiếng Việt).
>
> Quyết định và lý do: `docs/decision-records/DR-0002-travel-content.md`. Trạng thái: **thiết kế đã duyệt**,
> chưa có code.

---

## Overview

| | |
|--|--|
| **Khán giả** | Theo hồ sơ đối tượng. Bản đầu `en-us`: người nói tiếng Anh ở Mỹ, Canada, Úc; người Việt xem phụ đề |
| **Kênh** | Kênh TikTok hiện tại (quyết định 2026-11-15) |
| **Input** | Hàng trong tab `Travel` của Google Sheet: `question`, `destination`, `audience`, `pillar`, `source_urls`, `notes`, `facts_manual`, `status` |
| **Output** | `storage/videos/<ngày>_travel_<điểm đến>_<đối tượng>_<slug>/`: `video.mp4` (1080×1920, 25–60 s), `script.json`, `topic.json`, `facts.json`, `credits.txt`, `audio_N.mp3`, clip/ảnh |
| **Giọng** | Theo hồ sơ đối tượng; `en-us`: giọng Mỹ edge-tts (mặc định), Gemini TTS khi `TRAVEL_TTS_PROVIDER=gemini` |
| **Cost** | $0: Groq free, edge-tts free, Pixabay / Pexels / Wikimedia Commons API free |

---

## Hồ sơ (`content/travel/`)

```
content/travel/
├── destinations/
│   └── vn.json          tên nước theo ngôn ngữ, sources[] (domain, tier, pillars), pronunciations{lang: {...}},
│                        media_keywords, official_check_line
├── pillars.json         prep, getting-around, culture, food, places: volatile mặc định, min_tier, số đoạn answer, hashtag
└── audiences/
    └── en-us.json       voice_lang en-US, voices (edge / gemini, nam / nữ), subtitle_langs [vi], caption_lang en,
                         markets [US, CA, AU], base_hashtags, tone, labels (chữ cố định trên màn hình)
```

| Muốn | Làm |
|------|-----|
| Thêm nước (vd Thái Lan) | Tạo `destinations/th.json` (nguồn chính thức của nước đó, cách đọc tên riêng). Hàng Sheet ghi `destination=th` |
| Thêm chủ đề (vd `budget`) | Thêm một mục vào `pillars.json` |
| Thêm đối tượng (vd người Việt đi du lịch) | Tạo `audiences/vi.json`: giọng Việt, `subtitle_langs: []`, caption tiếng Việt, hashtag Việt |
| Một câu hỏi cho 2 đối tượng | Hai hàng Sheet cùng `question` gốc; dùng chung `facts.json`, chỉ viết lại lời + dựng lại |

`travel.py` kiểm hồ sơ khi nạp (thiếu trường, mã lạ, font không có chữ của ngôn ngữ phụ đề) và dừng trước khi gọi AI.
`topic.json` lưu `profile_snapshot` để dựng lại vẫn ra như cũ khi hồ sơ đổi.

---

## Trụ cột nội dung (`pillars.json`, bản đầu)

| `pillar` | Ví dụ câu hỏi | Dữ kiện `volatile` |
|----------|---------------|:------------------:|
| `prep` | Visa, e-visa, thời điểm đẹp, SIM, tiền mặt hay thẻ | Có |
| `getting-around` | Grab hay taxi, tàu Bắc Nam, qua đường, lừa đảo thường gặp | Một phần (giá) |
| `culture` | Trang phục vào chùa, tip, Tết, cách chào | Không |
| `food` | Phở Bắc / Nam, bánh mì, ăn chay | Giá món |
| `places` | Hạ Long, Hội An, Sa Pa, Phong Nha, lịch trình 7 / 14 ngày | Giờ mở cửa, giá vé |

Mỗi video: **một câu hỏi**, đặt trong 3 giây đầu.

---

## Workflow

```
demo.py --travel --sheet [--destination vn] [--audience en-us]
 0. Nạp + kiểm hồ sơ điểm đến / chủ đề / đối tượng
 1. Chọn hàng đầu tiên status trống trong tab Travel
 2. research   tải source_urls (chỉ domain trong sources của hồ sơ điểm đến)
               Groq trích fact {claim, quote} → giữ fact có quote nguyên văn trong trang
               + facts_manual (claim | quote | url) nếu có
               0 fact → status=needs_sources, dừng
 3. write      Groq: segments hook / answer (2–4) / outro, line (ngôn ngữ đối tượng), subs{vi}, text, fact_ids
 4. check      C-0002-1, C-0002-4 → lỗi: hỏi lại Groq 1 lần → vẫn lỗi: needs_sources
 5. media      Pixabay video → Pexels video → ảnh Wikimedia Commons; credits (C-0002-3)
 6. voice      giọng của hồ sơ đối tượng, chữ qua pronunciations của điểm đến
 7. render     clip phủ khung · chữ lớn EN trên · phụ đề EN + VI dưới · outro nguồn + tháng năm
 8. status=review → Studio → demo.py --approve DIR → post.txt → Drive video_output/travel/<điểm đến>/<slug>/ → done
```

`--render-only DIR` / `--approve DIR` nhận thư mục travel nhờ `topic.json`.

---

## Nguồn dữ kiện cho phép của điểm đến `vn` (`destinations/vn.json → sources`)

| Tier | Domain | Tên | Dùng cho |
|:----:|--------|-----|----------|
| 1 | `evisa.gov.vn`, `evisa.xuatnhapcanh.gov.vn` | Cổng e-visa (vietnam.travel ghi cổng chính thức là `evisa.gov.vn`), Cục Quản lý xuất nhập cảnh | Visa, phí, thời hạn |
| 1 | `vietnam.travel` | Cục Du lịch Quốc gia Việt Nam | FAQ, đi lại, phép lịch sự, ẩm thực, thời tiết |
| 1 | `travel.gc.ca` | Chính phủ Canada | Nhập cảnh, an toàn, y tế (người Canada) |
| 1 | `travel.state.gov` | Bộ Ngoại giao Mỹ | Nhập cảnh, an toàn (người Mỹ) |
| 1 | `smartraveller.gov.au` | Chính phủ Úc | Nhập cảnh, an toàn, luật địa phương (người Úc) |
| 1 | `whc.unesco.org` | UNESCO World Heritage Centre | Di sản thế giới |
| 1 | `wwwnc.cdc.gov` | CDC Travelers' Health | Vaccine, bệnh thường gặp |
| 2 | `guide.michelin.com` | MICHELIN Guide | Quán được công nhận (Hà Nội, TP.HCM, Đà Nẵng) |
| 2 | `e.vnexpress.net`, `tuoitrenews.vn`, `vietnamnews.vn` | Báo chính thống tiếng Anh | Tin mới: luật, lễ hội, sự kiện |

Thử tải ngày 2026-11-16 (máy nhà, User-Agent trình duyệt): `travel.state.gov` 403, `whc.unesco.org` 403,
`smartraveller.gov.au` không phản hồi, hai cổng e-visa là trang ứng dụng không có chữ, `guide.michelin.com` 202 trống.
Các domain này có `auto_fetch: false` trong `vn.json`, chỉ dùng được qua cột `facts_manual`.
`vietnam.travel`, `travel.gc.ca`, `wwwnc.cdc.gov` và 3 báo tier 2 tải được.

Không bao giờ là nguồn dữ kiện: blog du lịch, trang bán tour, Reddit, Wikipedia / Wikivoyage (chỉ để định hướng).
Visa, y tế, an toàn, luật: bắt buộc tier 1 (C-0002-4). Hai nguồn mâu thuẫn: không làm chủ đề đó cho tới khi người vận hành chốt.

---

## Dữ liệu

### `facts.json`

```json
[{"id": "f1", "claim": "US citizens need an e-visa or visa to enter Vietnam",
  "quote": "<đoạn nguyên văn trong trang>", "url": "https://…", "source_name": "U.S. Department of State",
  "tier": 1, "checked_on": "2026-11-15", "volatile": true}]
```

### `script.json` (khác video sản phẩm)

| Trường | Ý nghĩa |
|--------|---------|
| `kind: "travel"`, `lang`, `destination`, `audience` | Loại video, ngôn ngữ lời đọc, hồ sơ đã dùng |
| `voice` | Tên giọng lấy từ hồ sơ đối tượng |
| `segments[i].kind` | `hook` (câu hỏi) · `answer` · `outro` (nguồn + "Follow for more Vietnam tips") |
| `segments[i].line` / `subs` | Lời đọc / phụ đề theo ngôn ngữ, vd `{"vi": "…"}` |
| `segments[i].text` | Chữ lớn EN, ≤ 6 từ |
| `segments[i].fact_ids` | Bắt buộc với `answer` |
| `segments[i].media` | Chỉ số trong `media[]` |
| `media[]` | `{file, provider, id, page, author, license}` |
| `tts_provider`, `audio_line`, `duration`, `needs_render` | Như video sản phẩm (DR-0001) |

---

## Ràng buộc

| ID | Nội dung |
|----|----------|
| C-0002-1 | Segment `answer` có ≥ 1 fact hợp lệ; mọi con số trong `line` / `text` có trong `quote` của fact được trích |
| C-0002-2 | Fact `volatile` ≤ 30 ngày khi dựng và khi duyệt; outro + caption ghi nguồn và tháng năm |
| C-0002-3 | Media chỉ từ Pixabay / Pexels / Wikimedia Commons qua API, giấy phép trong danh sách cho phép, có `provider` + `page` + `license` |
| C-0002-4 | Nguồn dữ kiện chỉ trong `sources` của hồ sơ điểm đến; visa / y tế / an toàn / luật cần tier 1; kết thúc bằng "Check the official site before you go" |
| C-0002-5 | Code, prompt, Studio không chứa chữ riêng của nước / ngôn ngữ / đối tượng; mọi thứ đọc từ hồ sơ |
| C-0001-1 | Một bộ giọng / video (kế thừa) |

---

## Khung hình (1080×1920)

```
┌───────────────────────────┐
│  [chữ lớn EN, ≤ 6 từ]       │  y ≈ 220–420
│                           │
│        clip / ảnh         │  phủ toàn khung, làm tối nhẹ dưới chữ
│                           │
│  phụ đề EN (trắng, đậm)     │  y ≈ 1350–1450
│  phụ đề VI (vàng nhạt, nhỏ) │  y ≈ 1460–1530
│                           │  ≥ 380 px đáy + cột nút phải để trống cho UI TikTok
└───────────────────────────┘
outro: "Info as of Nov 2026 · Source: U.S. Department of State" + "Check the official site before you go"
ảnh CC BY / BY-SA: dòng nhỏ "Photo: <tác giả>, <giấy phép>" góc dưới trái
```

---

## `post.txt`

- Caption EN ngắn (câu hỏi + 1 dòng trả lời) + "Source: <tên nguồn>, <tháng năm>" + hashtag EN (vd `#vietnam #vietnamtravel #traveltips #visitvietnam`, thêm theo trụ cột).
- Checklist: **không** gắn sản phẩm; bật nhãn "Nội dung do AI tạo" (giọng máy); dán credits vào bình luận ghim nếu có ảnh CC BY / BY-SA.

---

## Chi tiết thực thi P1 (BA, 2026-11-16)

> Soát DR-0002 với code trên `main` (88f6cc9). DR đã merge nên không sửa (hook `agreement_hash_guard`); chi tiết
> thực thi ghi ở đây. **Không đổi quyết định hay ràng buộc nào của DR-0002.**

### Hồ sơ đã có (`content/travel/`)

| File | Trường thêm so với DR-0002 § Dữ liệu |
|------|--------------------------------------|
| `destinations/vn.json` | `sources[].name` theo ngôn ngữ, `sources[].auto_fetch`, `sources[].checked`; `hashtags` theo ngôn ngữ (hashtag của nước ở hồ sơ điểm đến, không ở `pillars.json` hay hồ sơ đối tượng, C-0002-5); `official_check_line` theo ngôn ngữ; `media_keywords.{default, places, required_tags_any}` |
| `pillars.json` | `fact_categories`, `tier1_categories`, `volatile_categories`, `tier1_keywords` (theo ngôn ngữ); `answer_segments: {min, max}`; `hashtags` theo ngôn ngữ |
| `audiences/en-us.json` | `script_lang`; `voices.{default, edge, gemini}`; `subtitle_font_check`; `subtitle_tone`; `labels` có chỗ trống `{month_year}` `{source}` `{destination}` `{author}` `{license}`; `month_names` |
| `seed-questions.csv` | 30 câu hỏi đầu, đúng cột tab `Travel`, để người vận hành nhập vào Sheet (Tệp → Nhập → Tải lên). 2 hàng `status=skip` vì hai trang nguồn mâu thuẫn |

Khoá bắt đầu bằng `_` trong hồ sơ là ghi chú, code bỏ qua.

### Điểm chốt cho code (đã gộp review Tech Lead 2026-11-16)

Cột "TL" là số mục trong review Tech Lead.

| # | TL | Chỗ | Chốt |
|---|----|-----|------|
| T-1 | #4 | Tải trang nguồn an toàn (`fetch_source(url)`) | Chỉ `https`. Lấy host bằng `urlsplit().hostname`; từ chối URL có userinfo (`user@host`) hoặc cổng khác 443. Khớp domain: `host == d` hoặc `host.endswith("." + d)` (không phải `endswith(d)`, để `evilvietnam.travel` bị loại). Tự xử lý redirect, kiểm lại host ở **mỗi** bước, tối đa 3 bước. Chỉ nhận `Content-Type` `text/html` hoặc `text/plain`. Đọc tối đa 2 MB (`read(2MB+1)`, quá thì bỏ trang), timeout 20 s. `auto_fetch=false` → không tải, log nêu domain + nhắc cột `facts_manual` |
| T-2 | #4 | HTML → chữ, so khớp quote (R-2) | Dùng `html.parser` của thư viện chuẩn (không thêm bs4). Bỏ `<script>/<style>`, thẻ thay bằng **dấu cách** (vietnam.travel tách số khỏi chữ bằng `<b>`), unescape, gộp khoảng trắng, chuẩn hoá nháy cong / gạch ngang, không phân biệt hoa thường. Lưu chữ đã tách vào `sources/src_N.txt` (bằng chứng, so quote trên file này). Gửi Groq có giới hạn số ký tự (Dev chọn, ghi hằng số), ưu tiên đoạn chứa từ khoá của câu hỏi. Quote dài tối thiểu khoảng 30 ký tự (quote quá ngắn kiểu "25" khớp ở đâu cũng được) |
| T-3 | — | Phân loại fact (C-0002-4, C-0002-2) | Fact có thêm `category` (Groq chọn trong `fact_categories`; lạ/trống → `general`). Cần tier 1 khi `category ∈ tier1_categories`, hoặc claim/quote chứa từ trong `tier1_keywords[ngôn ngữ]` (nguyên từ), hoặc `tier` kém hơn `pillar.min_tier`. `volatile = pillar.volatile or category ∈ volatile_categories` |
| T-4 | #15 | Kiểm số (C-0002-1) | Kiểm trên `line`, `text`, **`subs.*`, `hook`, `caption`** của video. So **giá trị số** sau chuẩn hoá (bỏ dấu phân cách hàng nghìn: `150,000` = `150.000` = 150000; giữ đơn vị tiền / `%`: `US$25` = `$25` = `USD $25` = `25 USD`). Số trong `subs` của một cảnh phải nằm trong quote của fact cảnh đó, như `line`. Prompt bắt viết số bằng chữ số; số viết bằng chữ ("twenty-five") → lỗi, Groq viết lại |
| T-5 | #2 | Sửa lời trên Studio rồi Dựng lại | `api/studio.py` **không** import `travel.py` (C-0001-2). PUT vẫn lưu và đặt `needs_render=true` (Duyệt vẫn bị chặn như video sản phẩm). Kiểm số chạy trong `travel.render_only`, **trước** khi đọc lại giọng. Sai → không đổi audio, không dựng, thoát mã **5** (`fact_check`), log nêu cảnh + con số. Studio thêm `ERROR_KINDS[5]` + câu báo tiếng Việt riêng |
| T-6 | #3 | Fact quá hạn (C-0002-2, D-11) | **Không** dùng lại mã 4 (Studio sẽ báo "cần dựng lại / thiếu ảnh", người vận hành bấm Dựng lại mãi không hết). Mã mới **6** (`facts_stale`): `--approve` **chặn** khi có fact `volatile` có `checked_on` quá 30 ngày. `--render-only` chỉ **cảnh báo** trong log, vẫn dựng (đọc spec "≤ 30 ngày khi dựng và khi duyệt" là: chặn ở duyệt, nhắc ở dựng). Studio thêm `ERROR_KINDS[6]` + câu báo chỉ cách làm mới. Lệnh mới `demo.py --travel --refresh-facts DIR`: tải lại trang (qua T-1), kiểm lại từng quote; còn → cập nhật `checked_on`; mất → bỏ fact, còn thiếu fact cho một cảnh `answer` → `status=needs_sources` |
| T-7 | #9 | Cập nhật Sheet sau Studio | Studio không truyền `--tab` (mặc định `Tiktok`). `travel.py` tự cập nhật tab `Travel`: `topic.json` lưu `tab` (từ `TRAVEL_TAB`, mặc định `Travel`) và khoá hàng (`question`, `destination`, `audience`) |
| T-8 | #11 | Drive | Chọn **(b)**: thêm tham số đường dẫn nhiều cấp vào `drive_upload.upload_video_folder` (khoảng 10 dòng; mặc định như cũ nên luồng sản phẩm / bài tập không đổi), để ra đúng `<gốc>/travel/<điểm đến>/<thư mục video>/` như DR. Không tải `clip_*` / `img_*` / `_pp_*` lên Drive (đã có link trang gốc trong `credits.txt`; dựng lại sau khi duyệt thì không làm được, chấp nhận) |
| T-9 | #7, #21 | Tải media | Ước độ dài cảnh theo số từ của `line`, ưu tiên hit có `duration` ≥ ước lượng (giữ thứ tự `media` trước `voice` của DR). Chọn bản có cạnh ngắn gần 1080 nhất (không lấy 4K). Bỏ file có `Content-Length` > khoảng 80 MB. Ghi ra `.part` theo luồng rồi `os.replace`; lỗi thì xoá `.part`. Wikimedia: lấy `thumburl` với `iiurlwidth=1920`; User-Agent chung của dự án, **không** ghi email. Thay clip sai cho từng cảnh trên Studio: để P1.1 |
| T-10 | #5 | Mã `destination` / `audience` / `pillar` lấy từ Sheet | Phải khớp `^[a-z0-9-]{1,16}$` **và** có hồ sơ tương ứng (`destinations/<mã>.json`, `audiences/<mã>.json`, khoá trong `pillars.json`), không thì dừng với thông báo tiếng Việt trước khi gọi AI. Tên thư mục video ghép qua `demo._slug` (chặn `../`, chặn thư mục lồng) |
| T-11 | #6 | Dựng video | **Không** import `exercise._pingpong`, `_clip_input`, `_fg_filter`, `render`: `reverse` giữ mọi khung hình trong RAM (Tech Lead đo 688 MB cho clip 720×1280 10 s, 1,44 GB cho 1080p 10 s), cho cảnh phố chạy ngược, và `delogo` làm mờ góc dưới phải mọi clip 720×1280. Chỉ import `exercise._clip_info`, `exercise._speech_bounds`. `travel.py` có hàm dựng riêng: scale về 1080 trước, phủ toàn khung; clip ngắn chậm lại tối đa 1,6×, rồi nối clip khác hoặc `tpad` giữ khung cuối, không chạy ngược; ảnh tĩnh dùng `zoompan`. Nợ kỹ thuật: tách phần dựng clip dùng chung ra `clipkit.py` sau (ghi `TODO.md`) |
| T-12 | #8 | Giọng đọc | `travel.py` có `_edge_tts(text, voice, rate, pitch)` riêng (chép vòng thử lại 6 lần của `demo._tts`). Giọng lấy từ `topic.json → profile_snapshot`, **không** bị `TTS_VOICE` trong `.env` ảnh hưởng. `travel.render_only` tự đọc lại câu đã sửa và tự xử lý `--revoice-all edge`, giữ cơ chế "lỗi thì không đổi audio nào" (exit 3). **P1 chỉ dùng edge-tts**; Gemini cho travel để sau khi nhánh quota Gemini merge (phải đi qua `quota_reserve` của nhánh đó). Ghim `edge-tts==7.3.1` trong `requirements-demo.txt` (bản đang chạy trên máy nhà, `pip show` 2026-11-16) |
| T-13 | #9 | Chỗ móc vào `demo.py` | Chỉ **2** chỗ: (a) dòng đầu của khối `if args.render_only or args.approve:`, **trước** khi đọc `product.json`: `if (d / "topic.json").is_file(): import travel; sys.exit(travel.main_existing(d, args))`; (b) nhánh `--travel` (kèm `--refresh-facts`, `--destination`, `--audience`) ngay sau khối `--exercise`. Mọi logic khác nằm trong `travel.py` |
| T-14 | #10 | `KEEP_LOCAL` | Lỗi trên `main`: chạy `demo.py` thì module là `__main__`, `import demo` trong `exercise.py` nạp bản thứ hai nên `demo.KEEP_LOCAL` luôn `False` (`--keep-local` không có tác dụng với `--exercise`). Người điều phối ghi issue. `travel.py` **không** đọc biến toàn cục này: nhận `keep_local` làm tham số |
| T-15 | #18 | Đọc tab `Travel` | Lớp mới `TravelSheet` đặt ở **cuối** `product_sources.py`, kèm `TRAVEL_SHEET_COLUMNS`. **Không** sửa `ProductSheet` (nhánh `studio-create-video` đang sửa nó) |
| T-16 | #12 | Studio | Logic travel ở file mới `backend/app/api/studio_travel.py` (`travel_detail`, `apply_travel_edit`). `studio.py` chỉ thêm chỗ móc: `_editable` nhận `topic.json`, `_title` (lấy `question`), cuối `video_detail`, `save_video`, `ERROR_KINDS` 5 / 6. `SegmentEdit` thêm `subs: Optional[Dict[str, str]]`: khoá phải thuộc `profile_snapshot.subtitle_langs`, giới hạn độ dài. **Làm sau cùng** (nhánh `studio-create-video` và nhánh quota Gemini đang sửa nhiều `studio.py` / `studio.html`). Không đụng `app.html` |
| T-17 | #13 | Chặn XSS link | `esc()` của `studio.html` không chặn `javascript:`. Phía server: URL của fact (cả `facts_manual`) phải là `https` + host thuộc nguồn cho phép (T-1); `page` của credits phải thuộc domain của provider (`pixabay.com`, `pexels.com`, `commons.wikimedia.org`). Phía HTML: chỉ gắn `href` khi bắt đầu bằng `https://`, thêm `rel="noopener noreferrer"` |
| T-18 | #14 | Phụ đề EN + VI | Chỉ còn khoảng 180 px cho hai dòng phụ đề. Cắt mỗi cảnh thành nhiều đoạn, mỗi đoạn ≤ 2 dòng, thời gian chia theo số ký tự. Groq trả `subs` cùng số đoạn với `line`. P1 vẽ bằng Pillow như code hiện có (không chuyển sang libass/.ass, để đỡ phụ thuộc bản build ffmpeg). `line` travel tối đa khoảng 220 ký tự (Studio chặn dài hơn) |
| T-19 | #16, #17 | File và git | Thêm thư mục cache mới (vd `storage/travel_cache/`) vào `.gitignore` (repo đang public). Ghi JSON kiểu atomic (file tạm rồi `replace`), ghi `script.json` / `facts.json` **trước** `video.mp4` |
| T-20 | #19 | Dùng chung `facts.json` cho nhiều đối tượng | **Ngoài P1** (P1 chỉ có `en-us`). Thiết kế giữ nguyên, làm khi có hồ sơ đối tượng thứ hai |

### Bảng quyết định bổ sung (theo T-1, T-5, T-6, T-10, T-17)

DR-0002 đã khoá nên các dòng này ghi ở đây; Tester chạy cùng D-1…D-15 của DR.

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1b | URL nguồn: `http://vietnam.travel/...`; `https://evilvietnam.travel/...`; `https://vietnam.travel@evil.com/...`; `https://vietnam.travel:8443/...`; trang cho phép redirect sang domain lạ | Cả 5 bị từ chối trước khi đọc nội dung, log nêu lý do | Hàm kiểm (redirect giả lập bằng server local) |
| D-1c | Trang > 2 MB hoặc `Content-Type` không phải HTML / text | Bỏ trang, log nêu URL | Hàm kiểm |
| D-5b | `subs.vi` của cảnh có số khác `line` / quote (vd `30 USD` khi quote ghi `US$25`) | Bị chặn như D-5 | Hàm kiểm |
| D-11 (thay mã) | `--approve` với fact volatile `checked_on` 31 ngày trước | **exit 6**, thông báo tiếng Việt chỉ lệnh `--refresh-facts`; `--render-only` cùng thư mục: dựng được, log có cảnh báo | Sửa ngày trên bản sao |
| D-11b | `--refresh-facts` khi quote còn / mất trên trang | Còn: `checked_on` = hôm nay, duyệt được. Mất: fact bị bỏ, thiếu fact cho cảnh `answer` → `needs_sources` | Trang giả lập |
| D-12b | Sửa `line` trên Studio thêm số không có nguồn → Dựng lại | Job lỗi `error_kind=fact_check` (exit 5), audio cũ giữ nguyên, nút Duyệt vẫn bị chặn | TestClient + chạy thật |
| D-15b | Hàng Sheet có `destination=../x`, `audience=EN US`, hoặc mã không có hồ sơ | Dừng trước khi gọi AI, thông báo tiếng Việt | Hàm kiểm |
| D-16 | Fact / credits có URL `javascript:...` hoặc host ngoài danh sách | Server bỏ fact / media; HTML không gắn `href` | TestClient + đọc HTML |

### Kiểm E2E: nguồn dùng được

- **V-1** (visa người Mỹ): cổng e-visa và `travel.state.gov` không tải tự động được. vietnam.travel không có câu nói thẳng "người Mỹ cần visa" (chỉ có danh sách nước miễn visa, không có Mỹ). Chạy V-1 với hàng 1 của `seed-questions.csv` **và** `facts_manual` chép từ travel.state.gov mở bằng trình duyệt; thiếu `facts_manual` thì đúng là ra `needs_sources`. Đường tải tự động kiểm bằng hàng "Do Canadians need a visa" (`travel.gc.ca`).
- **V-2** (phở Bắc / Nam): đoạn so sánh ở `vietnam.travel/things-to-do/21-must-try-vietnamese-dishes/`, không có ở trang "Must-try noodles".

### Việc #7 của DR

Đã có skill `agent/commands/travel-review.md` (T1–T12) và chế độ 3 trong `agent/agents/marketing.md` (PR #12).
Còn lại: MKTG đối chiếu checklist với video mẫu.

---

## Lộ trình

| Giai đoạn | Nội dung | Cổng |
|-----------|----------|------|
| P0 | DR-0002, spec này, hồ sơ `vn` / `en-us` / `pillars`, 30 câu hỏi đầu | Người dùng duyệt DR |
| P1 | `travel.py` + Studio như DR-0002 | 5 video, MKTG không mức "Chặn", tester đạt bảng quyết định |
| P2 | Đăng tay 10–15 video, ghi views 48h, thời gian xem, % người xem US / CA / AU, lượt lưu | Ít nhất một trụ cột có phần lớn người xem nước ngoài |
| P3 | `travel.py discover` (YouTube Data API, Google Trends theo `markets` của đối tượng), tự tìm URL nguồn, nhắc kiểm lại fact | DR riêng |
| Sau P2 | Thêm hồ sơ điểm đến / đối tượng thứ hai (vd `audiences/vi.json`) | Chỉ khi `vn` + `en-us` có người xem |

---

## Files (dự kiến)

| File | Vai trò |
|------|---------|
| `travel.py` | research / write / check / media / voice / render / finish |
| `content/travel/destinations/vn.json` | Hồ sơ điểm đến Việt Nam |
| `content/travel/pillars.json` | Danh sách chủ đề |
| `content/travel/audiences/en-us.json` | Hồ sơ đối tượng tiếng Anh giọng Mỹ, phụ đề VI |
| `content/travel/seed-questions.csv` | 30 câu hỏi đầu để nhập vào tab `Travel` |
| `demo.py` | 2 chỗ móc (T-13): `--travel` / `--refresh-facts`; `--render-only` / `--approve` chuyển sang `travel.py` khi có `topic.json` |
| `product_sources.py` | `TRAVEL_SHEET_COLUMNS` + lớp `TravelSheet` ở cuối file (T-15) |
| `drive_upload.py` | Tham số đường dẫn nhiều cấp, bỏ qua `clip_*` / `img_*` (T-8) |
| `requirements-demo.txt` | Ghim `edge-tts==7.3.1` (T-12) |
| `.gitignore` | Thư mục cache travel (T-19) |
| `backend/app/api/studio_travel.py` (mới) | `travel_detail`, `apply_travel_edit` (T-16) |
| `backend/app/api/studio.py`, `backend/app/web/studio.html` | Chỉ chỗ móc + hiển thị travel, làm sau cùng (T-16, T-17) |
| Không đổi | `app.html`, `api/creator.py`, `exercise.py` (chỉ import `_clip_info`, `_speech_bounds`), `ProductSheet` |
