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
| 1 | `evisa.xuatnhapcanh.gov.vn` | Cổng e-visa, Cục Quản lý xuất nhập cảnh | Visa, phí, thời hạn |
| 1 | `vietnam.travel` | Cục Du lịch Quốc gia Việt Nam | FAQ, đi lại, phép lịch sự, ẩm thực, thời tiết |
| 1 | `travel.gc.ca` | Chính phủ Canada | Nhập cảnh, an toàn, y tế (người Canada) |
| 1 | `travel.state.gov` | Bộ Ngoại giao Mỹ | Nhập cảnh, an toàn (người Mỹ) |
| 1 | `smartraveller.gov.au` | Chính phủ Úc | Nhập cảnh, an toàn, luật địa phương (người Úc) |
| 1 | `whc.unesco.org` | UNESCO World Heritage Centre | Di sản thế giới |
| 1 | `wwwnc.cdc.gov` | CDC Travelers' Health | Vaccine, bệnh thường gặp |
| 2 | `guide.michelin.com` | MICHELIN Guide | Quán được công nhận (Hà Nội, TP.HCM, Đà Nẵng) |
| 2 | `e.vnexpress.net`, `tuoitrenews.vn`, `vietnamnews.vn` | Báo chính thống tiếng Anh | Tin mới: luật, lễ hội, sự kiện |

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
| `demo.py` | `--travel`; dispatch `--render-only` / `--approve` theo `topic.json` |
| `product_sources.py` | `TRAVEL_SHEET_COLUMNS` |
| `backend/app/api/studio.py`, `backend/app/web/studio.html` | Thư mục travel trên Studio |
