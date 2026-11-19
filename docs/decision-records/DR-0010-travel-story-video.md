# DR-0010: Travel v2 (phần 10a) — video kể chuyện 60–90 giây, thư viện cảnh quay riêng, lời bớt "mùi AI" (chưa dùng Gemini)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📋 Đề xuất (bản sửa lần 2 sau review Tech Lead và Marketing; U1–U4 đã được người dùng trả lời 2026-11-18). **Chờ: xác nhận duyệt DR + U5/U6** | 2026-11-18 | Claude (BA) | — |

Capability: `travel-content` · Nhánh: `feat/travel-story` (xếp trên `feat/travel-p1` = PR #17) · Chạm nhưng KHÔNG thay: C-0002-1, C-0002-3, C-0002-4, C-0002-5, C-0008-1, C-0008-2. **Không** thay DR-0008 quyết định 3: 10a vẫn chỉ dùng edge-tts.

> **Vì sao số 0010**: số 0002–0009 đã dùng hoặc có nhánh khác giữ chỗ. Nhánh `feat/gemini-quota` còn có file `DR-0002-gemini-tts-quota-fallback.md` (chưa commit) trùng số 0002; nên đổi số khi nhánh đó merge, không thuộc DR này.
>
> **Vì sao "10a"**: review Tech Lead (T12) chỉ ra Gemini cho travel phụ thuộc vào nhánh `feat/gemini-quota` (đang viết lại `_gemini_tts_prompt` trong `demo.py`, hiện là prompt tiếng Việt cho sản phẩm). Nên tách: **10a** (DR này) = thư viện cảnh quay, kiểm khớp hình, 5 nhịp, quy tắc lời, chuyển cảnh, edge-tts cải tiến, **không Gemini**. **10b** (DR riêng, viết sau khi `feat/gemini-quota` merge) = Gemini TTS cho travel; sẽ thay DR-0008 quyết định 3. Điều này **đổi lựa chọn người dùng đã chốt** ("Gemini 1 lượt cho cả video"), xem § 11 mục U1.

---

## 1. Bối cảnh

Người dùng xem video thật đầu tiên (`storage/videos/20261118_083204_travel_vn_en-us_what-s-the-difference-between-northern-a`, câu "What's the difference between Northern and Southern pho?").

| # | Phản hồi | Nguyên nhân gốc đã đọc trong code |
|---|----------|-----------------------------------|
| 1 | "Hình lạc đề" (cảnh 2 phở Bắc hiện cối xay gió, cảnh 4 đồi sương mù) | `build_media` + `_queries` + `candidate_ok` (`travel.py`): truy vấn = `visual` tự do của Groq + địa danh; `candidate_ok` chỉ kiểm thẻ AI, giấy phép, và thẻ có một chữ trong `required_tags_any` ("vietnam", "hanoi"...). **Không kiểm clip có đúng món / việc đang nói.** Hết clip mới thì `build_media` còn **dùng lại clip của cảnh trước** |
| 2 | "Không có sức hút, quá ngắn" (4 cảnh, ~15 s, 2 dữ kiện) | `pillars.json` `food.answer_segments` 2–4; `write_script` ép hook + 2–4 answer + outro, câu ≤ 15 từ, dòng ≤ 220 ký tự: là danh sách dữ kiện, không phải câu chuyện |
| 3 | "Giọng có mùi AI" | `voice_segments` đọc từng cảnh bằng edge-tts `rate +0%`, `pitch +0Hz`; lời theo `tone` (câu đều ~15 từ, cấm cảm thán) nghe như đọc danh sách |
| 4 | "Burn token nhanh quá" | Chạy `demo.py --travel` tốn **$0** (Groq free, edge-tts free, Pixabay free, dựng ~33 s cho video 15 s). Token bị đốt ở **quy trình nhiều agent khi phát triển**, không ở việc sản xuất video |

**Ràng buộc ngoài**: app TikTok đang xét duyệt (không đổi `app.html`, scope); Shopee tạm dừng; video vào inbox nháp, đăng tay; kênh chưa có quyền affiliate nên không bán hàng.

**Đã có sẵn** (đọc code 2026-11-18): dựng từng cảnh bằng FFmpeg (`_render_scene`: `-threads 2`, `x264 rc-lookahead=8 ref=2`), nối `concat` copy + âm thanh nối riêng (`render`), cắt cứng; `tts_text` / `apply_pronunciations`; kiểm dữ kiện (`check_script`, `numbers_missing`, `tier_needed`); nguồn theo `vn.json → sources`; hồ sơ `en-us.json` đã có khối `voices.gemini` nhưng `voice_segments` chỉ có nhánh edge.

---

## 2. Quyết định (phần 10a)

> **Video travel dạng "câu chuyện 4 nhịp" 60–90 s. Hình lấy từ thư viện cảnh quay thật do người vận hành quay một lần (tái dùng), thiếu thì hỏi người vận hành *trước khi gọi AI*, stock chỉ là dự phòng cho cảnh không phân biệt vùng và phải qua kiểm khớp. Cảnh chỉ miêu tả hình dùng loại cảnh `observe`. Chuyển cảnh dissolve chỉ giữa các nhịp, dựng frame-exact RAM-an toàn. Giọng: edge-tts cải tiến. Không Veo, không Gemini trong DR này.**

| # | Quyết định | Chi phí |
|---|-----------|---------|
| Q1 | Thư viện cảnh quay ở `BROLL_DIR` (mặc định `~/tiktok-broll`); **chỉ mục `index.json` nằm cạnh clip**, không trong git (chỉ có file mẫu trong git). Clip được **chuẩn hoá lúc nhập** (1080×1920, 25 fps, H.264, bỏ tiếng) | $0 |
| Q2 | Trước khi gọi Groq, kiểm đủ cảnh quay bắt buộc cho nhịp a/b; thiếu → mã **8**, Sheet `needs_broll`, liệt kê cảnh cần quay. Thiếu về sau (stock rỗng) → giữ `script.json` + `facts.json`, chạy lại bằng `--resume DIR` | $0 |
| Q3 | Cấu trúc 4 nhịp: hook → a → b → teaser; **không có outro** cho series này (nguồn + tháng năm ở dòng nhỏ cảnh cuối và caption); 8–10 cảnh nói, một cảnh có 1–2 clip | $0 |
| Q4 | 5 loại cảnh: `hook`, `answer` (có fact), **`observe`** (chỉ tả điều thấy trong clip của chính người vận hành), `bridge`, `teaser`. Mỗi loại có kiểm riêng, chạy cả khi Studio sửa (`strict=False`) | $0 |
| Q5 | Tách `style` (north / south: món kiểu nào) khỏi `filmed_at` (quay ở đâu). Lời chỉ nói "Hanoi" khi `filmed_at=hanoi` hoặc fact nói vậy, ngược lại nói "Northern-style" | $0 |
| Q6 | Dissolve chỉ giữa các nhịp (3 ranh giới); trong nhịp cắt cứng. Dựng frame-exact bằng muxer `segment` (§ 6.5) | $0 |
| Q7 | Giọng 10a: edge-tts cải tiến + lời kiểu nói + kiểm tự động các quy tắc § 6.4 | $0, 0 lượt Gemini |
| Q8 | Phụ đề: tiếng Anh theo cụm 3–6 từ bám tiếng nói; phụ đề tiếng Việt **tắt mặc định** cho series phở, bật bằng cờ `subtitles_vi` trong series; bản VI vẫn được viết và kiểm (số, nguồn) để người vận hành xem trên Studio, chỉ không vẽ lên video khi cờ tắt (người dùng chốt, U3) | $0 |
| Q9 | Tên quán chỉ khi có fact có nguồn **và** cảnh quay đúng quán đó. **Video đầu không nêu tên quán** (người dùng chốt, U4) | $0 |
| Q10 | Veo/Flow: ngoài phạm vi (§ 3.3) | — |

---

## 3. Chi phí (P02) và thông lượng

### 3.1 Chi phí một video (10a)

| Việc | Chạy bằng | $ / video | Lượt Gemini | Nguồn |
|------|-----------|-----------|-------------|-------|
| Trích dữ kiện + viết lời | Groq free | 0 | 0 | `CLAUDE.md`. **Ước tính chưa đo** (Tech Lead): ~10.000 token/video, ~16.000 nếu viết lại. Hạn mức free Groq: **chưa rõ**. Dev ghi `usage` mỗi lượt gọi và điền số thật vào "Kết quả" (T14) |
| Tìm clip | Thư viện (đĩa) → stock Pixabay/Pexels/Wikimedia (free) | 0 | 0 | `.env.example` |
| Giọng edge-tts | free | 0 | 0 | `CLAUDE.md` |
| Dựng 60–90 s | FFmpeg local | 0 | 0 | ≈ **3 phút** cho 75 s: ngoại suy từ 33 s / 15 s cộng 3 lệnh dissolve (T16). **Chưa đo**; Tester đo |
| **Tổng** | | **$0** | **0** | |

### 3.2 Thông lượng (người dùng chốt 2026-11-18, U2): **3–4 video/tuần ban đầu**

Mục tiêu cũ là 1–2 video/ngày. Marketing (M17) chỉ ra không thực tế: cùng một bộ clip phở thì mọi video phở lặp lại đúng cảnh múc nước dùng; mỗi món / series cần bộ cảnh quay riêng; chọn clip chưa dùng cần ≥ 2 biến thể mỗi cảnh. Hệ thống (máy) làm được 1–2 video/ngày ($0, ~3 phút máy); **giới hạn là nguồn cảnh quay và dữ kiện có nguồn**, không phải chi phí. Mục tiêu 10a: 3–4 video/tuần; tăng khi thư viện có thêm series.

### 3.3 Veo / Flow (số bên thứ ba, **CHƯA XÁC MINH**, không chọn)

Nguồn: thegenaimagazine.com/google-flow-pricing-2026-credits-cost-per-video, benchlm.ai/media-pricing/veo, magichour.ai/blog/veo-3-pricing; chưa đối chiếu trang Google. Giả định ~10 clip 8 s mỗi video.

| Gói | Giá | Clip/tháng | Đủ 300–600 clip/tháng? |
|-----|-----|-----------|------------------------|
| Pro, Veo 3.1 Lite | $19.99/tháng = 1.000 credit, ≈10 credit/clip | ≈100 | Không |
| Pro, Veo 3.1 Fast | như trên, ≈20 credit/clip | ≈50 | Không |
| Ultra, Lite | $99.99/tháng = 10.000 credit, ≈5 credit/clip | ≈2.000 | Đủ, cố định $99.99/tháng |
| API Fast ≈ $0,12/s (1080p) | ≈$9,6/video | | 30–60 video ≈ $290–580/tháng |
| API Lite ≈ $0,08/s | ≈$6,4/video | | 30–60 video ≈ $190–380/tháng |

Một nguồn nói API không có free tier. **Không chọn** vì: trả phí so với mục tiêu $0; cảnh AI của một quán có thật dễ gây hiểu lầm và cần nhãn AI; clip AI lỗi tốn thêm credit; cảnh quay thật tái dùng vô hạn, $0. (Không nên nói thư viện "tránh được nhãn AI" như lợi thế tuyệt đối: giọng tổng hợp, edge-tts hay Gemini, vẫn có thể phải bật công tắc nội dung AI khi đăng, xem C-0010-9.)

---

## 4. Phương án đã cân nhắc

| Chủ đề | Phương án | Chọn | Lý do |
|--------|-----------|------|-------|
| Hình | **A. Thư viện cảnh quay thật + hỏi trước khi gọi AI + stock có kiểm khớp (chỉ cảnh không phân biệt vùng)** | ⭐ | $0, thật, khớp lời vì thẻ do người quay gán |
| | B. Chỉ siết lọc stock | - | Không đủ cảnh "múc nước dùng", "thêm gia vị"; chỉ giữ làm dự phòng |
| | C. Veo / Flow | - | § 3.3 |
| | D. Vision API trả phí | - | Trái P02 |
| | E. Vision chạy máy (CLIP) | - | Nặng, không phân biệt phở Bắc/Nam đáng tin; để sau |
| Giọng | **A. edge-tts cải tiến (10a)** | ⭐ | $0, không phụ thuộc nhánh quota; Gemini để 10b |
| | B. Gemini 1 lượt cả video | - (để 10b) | Tách file dài thành cảnh không chắc đúng (silencedetect không ổn với giọng nói tự nhiên có dấu phẩy, T11) |
| | C. Gemini mỗi nhịp (~4 lượt/video) | đề xuất cho 10b | Sửa 1 câu chỉ đọc lại 1 nhịp; nhưng 4 lượt/video ăn quota (§ 7 của 10b) |
| | D. OpenAI TTS / ElevenLabs | - | Trả phí |
| Chuyển cảnh | **A. Dissolve từng ranh giới giữa các nhịp, dựng bằng muxer `segment` frame-exact** | ⭐ | T1: đo được 217 = 217 khung, RAM 270–390 MB |
| | B. Một `xfade` chuỗi nhiều cảnh | - | 2,8 GB RAM |
| | C. Cắt bằng `split` + `trim` 3 bộ mã hoá | - | ~800 MB |
| | D. Cắt cứng toàn bộ | - | Bị chê "không mượt" |

---

## 5. Thay đổi dữ liệu

### 5.1 `script.json` v2

Video cũ không có `format`: mọi chỗ đọc `beat`, `shot`, `transition`, `series` dùng `.get` (T10).

```jsonc
{
  "format": "story", "series": "pho-north-south",
  "segments": [{
    "kind": "hook|answer|observe|bridge|teaser",
    "beat": "hook|a|b|teaser",
    "line": "...", "text": "...", "subs": {"vi": "..."},     // subs.vi chỉ khi series bật
    "fact_ids": [],                                           // answer: ≥1; các loại khác: []
    "shots": [                                                // 1–2 clip mỗi cảnh (cắt cứng trong cảnh)
      {"need": {"subject": ["pho","noodle soup"], "style": "north", "action": "ladle"},
       "media": 3, "in": 0.0, "dur": 3.5}
    ],
    "transition": "dissolve|cut"                              // vào cảnh này; mặc định cut
  }],
  "media": [
    {"file": "clip_3.mp4", "provider": "library", "id": "pho_north_ladle_01",
     "type": "video", "license": "own work", "author": "own footage",
     "style": "north", "filmed_at": "hanoi", "stock": false},
    {"file": "clip_4.mp4", "provider": "pixabay", "id": "...", "page": "...", "license": "Pixabay Content License",
     "author": "...", "type": "video", "stock": true}       // stock: true = cờ để hiện nhãn "stock chưa xem" (thay "verified")
  ]
}
```

- `render` **không tin** `script.json`: với `provider: library` luôn đọc lại `index.json` (§ 5.4, `library_problem`).
- `hook`: `line` = câu hỏi nguyên văn; `text` trên màn hình ≤ 8 từ **do series cung cấp** (`hook_text`), tách khỏi `line` (M4). Ví dụ "Northern vs Southern pho?". Phần cảnh hook có 2 clip 1,5 s: bát phở Bắc nhìn từ trên xuống, rồi bát phở Nam cùng góc (`bowl-top`).
- **Loại cảnh**:

| Loại | Cho phép nói | Kiểm (chạy cả `strict=False`, T10) |
|------|--------------|-------------------------------------|
| `answer` | Chỉ điều fact trích nói | C-0002-1, C-0008-1, C-0002-4 như cũ |
| `observe` | Chỉ **tả điều thấy trong clip của người vận hành** (`own work`), vd "The broth goes in last, hot, right at the counter." | ≤ 12 từ; không chữ số; không so sánh / xếp hạng / khái quát ("than", "differ", "unlike", "always", "usually", "locals", "traditionally"); ≥ 1 từ (gốc) xuất hiện trong `description` hoặc `action` của clip; tên nơi chỉ khi bằng `filmed_at` của clip; clip phải `own work`; **mọi khẳng định Bắc vs Nam (rau, nước dùng trong, tương) vẫn cần fact** |
| `bridge` | Câu chuyển ("Let's start in Hanoi.") | ≤ 12 từ; không số; không tên riêng ngoài tên điểm đến / nơi trong series; không từ so sánh / tuyệt đối |
| `teaser` | Hẹn video sau, vd "Next time: where to try it in Hanoi. Follow, so you don't miss it." | như `bridge`; chỉ đăng khi video sau đã lên lịch |
| `hook` | Câu hỏi + gợi tò mò | như cũ + `text` ≤ 8 từ |

- Kiểm `observe` là **kiểm từ vựng**, không chứng minh lời đúng với hình. Cửa chốt là người duyệt trên Studio và MKTG. Ghi rõ ở Rủi ro.
- Từ cấm ở mọi cảnh `answer`/`observe`/`bridge`/`teaser`: best, top, authentic, real, famous, better, original, must, worth, "the secret" (M5, M7: "worth" bỏ luôn, là đánh giá).
- "Top street food" **không được nói** nếu nguồn không nói: dùng đúng nội dung nguồn, vd "Vietnam's official tourism site lists pho among its must-try dishes" (chỉ khi quote có ý này; không số "21" nếu quote không chứa số đó) (M5).
- Tên quán + clip chung → một nhãn nhỏ `labels.illustration` **một lần ở cảnh đó**, không phải mọi cảnh (M11).

### 5.2 Hồ sơ và series (một file, T15)

| File | Nội dung |
|------|----------|
| `content/travel/series/pho-north-south.json` (mới, **một file duy nhất** gồm nhịp / cảnh / shot / nguồn; tách khuôn riêng khi có series thứ hai) | `dish`, `subject`, `source_urls` theo nhịp, `hook_text`, `next_teaser` (EN + VI, người viết), `subtitles_vi` (true/false), `outro` (false), danh sách `shots` (id, `style`, `action`, `describes`, `mandatory`, `variants_min`), cảnh cho mỗi nhịp |
| `content/travel/audiences/en-us.json` | thêm `spoken_style`, danh sách từ cấm kiểu "mùi AI"; giữ nguyên `tone` cho video 4 cảnh |
| `content/travel/destinations/vn.json` | thêm `media_keywords.deny_tags` (chặn thẻ rõ ràng sai chủ đề) |
| Sheet tab `Travel` | **1 cột `series`**; trống = luồng cũ 4 cảnh. Trạng thái `needs_broll` **không bị bỏ qua** khi chạy lại (khác `needs_images`), để thêm clip xong là chạy tiếp |

Dựng 4 nhịp (mục tiêu 60–90 s, ~2,6 từ/giây ≈ 150–190 từ):

| Nhịp | Nội dung | Cảnh | Giây | Fact tối thiểu |
|------|----------|------|------|----------------|
| hook | Câu hỏi + bát phở Bắc, bát phở Nam cùng góc; cảnh 2: "Planning a trip to Vietnam, you'll want to know." + 1 fact nguồn nói phở thuộc món nên thử | 2 | 8–12 | 1 |
| a | Kiểu Bắc, quay ở `filmed_at`: bridge chuyển, observe múc nước dùng, observe/answer thêm hành, gia vị | 3–4 | 18–24 | 2 (nếu có) |
| b | Kiểu Nam: cùng trình tự và cùng góc | 3–4 | 18–24 | 2 |
| teaser | "Next time: where to try it in Hanoi." + dòng nhỏ nguồn, tháng năm | 1–2 | 6–8 | 0 (≥ 1 nếu nêu tên quán) |

**Không có outro** cho series này (M6): "Follow" nằm trong teaser; nguồn + tháng năm ở dòng nhỏ cảnh teaser và trong caption (giữ tinh thần C-0008-2). Câu "Check the official site before you go" (`official_check_line`) chỉ gắn khi có fact thuộc `tier1_categories` (visa, entry, health, safety, law), không gắn cho phở (C-0002-4 giữ nguyên).

### 5.3 Thư viện cảnh quay

```
~/tiktok-broll/              # BROLL_DIR; mặc định thư mục này, KHÔNG bắt người vận hành sửa .env
├── inbox/                   # người vận hành thả file gốc từ điện thoại (IMG_1234.MOV...)
├── clips/pho_north_ladle_01.mp4   # đã chuẩn hoá, tên do công cụ sinh
└── index.json               # chỉ mục, ghi nguyên tử (file tạm + os.replace) + khoá đơn giản
content/travel/broll/index.sample.json   # chỉ mẫu trong git
```

**Vì sao chỉ mục không trong git** (T4): worktree bị dọn thì mất; hai worktree thấy hai chỉ mục; xung đột merge. `.gitignore` không cần `storage/broll/` (thư viện ngoài repo); nếu người dùng đặt `BROLL_DIR` trong repo thì thêm vào `.gitignore`. Không lên Drive.

Mỗi mục `index.json`: `id`, `file`, `sha256` (của file đã chuẩn hoá, để `render` kiểm), `source_sha256` (của luồng video gốc, chống nhập trùng), `dish`, `style` (north|south|none), `filmed_at` (hanoi|saigon|other), `action`, `subject`, `description` (EN, người vận hành xác nhận), `shop` (tên quán nếu thật sự quay đúng quán, ngược lại null), `license` ("own work" hoặc tên giấy phép thật), `source` (URL https cho clip sưu tầm), `duration`, `added_on`.

**Nhập clip: `demo.py --travel --broll-add`** (bọc thành file `.command` bấm đúp như `mo-studio.command`), không bắt người vận hành đặt tên file (M16):
1. Liệt kê từng file trong `inbox/` (tên + độ dài). Với mỗi file hỏi **"Đây là cảnh số mấy?"** trong danh sách đánh số các cảnh còn thiếu của series (từ `shots`); hỏi một lần "Quay ở đâu? 1 Hà Nội · 2 Sài Gòn · 3 nơi khác"; hiện sẵn dòng mô tả tiếng Anh lấy từ `shots[].describes`, Enter để nhận, hoặc gõ để sửa.
2. Công cụ **tự sinh tên** `<dish>_<style>_<action>_<NN>.mp4` từ slug đã kiểm. Regex `^[a-z0-9-]+_[a-z0-9-]+_[a-z0-9-]+_\d{2}\.(mp4|mov)$` chỉ áp cho tên sinh ra; tên gốc từ điện thoại chỉ dùng để đọc (chuẩn hoá NFC/NFD tiếng Việt trước khi so).
3. **Một lệnh ffmpeg chuẩn hoá** (T3): xoay đúng chiều theo metadata (ffmpeg tự xoay), 1080×1920, 25 fps CFR, H.264 crf ~20, bỏ tiếng, cắt ≤ 15 s, tone-map HDR→SDR chỉ khi phát hiện HDR. Từ chối: file > ~500 MB hoặc > 60 s; cảnh < 5 s hoặc không dọc → **cảnh báo** (không chặn). Trùng theo `source_sha256` thì bỏ qua, không theo tên.
4. An toàn (T7): từ chối symlink; `resolve()` phải nằm trong `BROLL_DIR/inbox`, sau đó trong `BROLL_DIR/clips`; tên đích chỉ sinh từ slug đã kiểm.
5. **`ffprobe` không có** (chỉ có ffmpeg qua `imageio-ffmpeg`; `_clip_info` đọc stderr của `ffmpeg -i` và **không đọc được góc xoay**, nên clip dọc từ iPhone bị coi là ngang). Vì vậy: độ dài/khổ đo bằng ffmpeg **sau khi chuẩn hoá**, không dựa vào `_clip_info` trên file gốc (T2).
6. Cuối lệnh in bảng "đã có / **còn thiếu**" theo `mandatory` của series (thay cho lệnh `--broll-list` riêng, T15). Thư viện rỗng → nói rõ: "Thư viện cảnh quay đang trống tại <đường dẫn>. Hãy quay cảnh theo hướng dẫn rồi bấm Thêm cảnh quay".
7. Clip sưu tầm (không tự quay): bắt buộc `license` là tên giấy phép **thật** (Pixabay License / Pexels License / CC BY...; **không ghi "CC0" cho Pixabay hay Pexels**, M13) và `source` là URL https; từ chối host tiktok / instagram / google / facebook. CC BY / BY-SA phải hiện lời ghi công trên khung hình (nhãn `photo_credit` có sẵn).

**Dùng clip khi dựng** (T5): `os.link` vào thư mục video (lỗi EXDEV → `shutil.copy2`), **luôn đặt tên `clip_N.mp4`** (`drive_upload` bỏ qua tiền tố `clip_`; giữ tên gốc thì clip sẽ lên Drive).

**Chọn clip** (T15): đủ điều kiện (`subject`, `style`, `action` bắt buộc cho nhịp a/b) → ưu tiên clip chưa dùng trong video này; nếu còn nhiều, chọn giả ngẫu nhiên có hạt giống từ chủ đề (video cùng chủ đề dựng lại ra cùng kết quả) hoặc xoay theo `added_on`. Không có `usage.json`. Muốn tránh lặp giữa các video thì cần ≥ 2 biến thể mỗi cảnh (`variants_min`).

### 5.4 Kiểm tra bảo mật khi dựng: `library_problem(m)` (T6)

**Không** thêm `library` vào `PROVIDER_DOMAIN` (nó có `page` https, `PROVIDER_CDN`, `download_media`). Thêm hàm riêng:
- `id` phải có trong `index.json` (đọc lại lúc dựng, không tin `script.json`);
- `license` ∈ {"own work"} ∪ `LICENSE_OK`; `Path(file).name == file`; sha256 file trong thư mục video = `sha256` trong chỉ mục;
- clip sưu tầm có `source` https, host không thuộc danh sách cấm;
- `write_credits` dùng `.get` (clip thư viện không có `page`; `author` của clip tự quay cố định "own footage"); `build_media`/`download_media` không bao giờ nhận `library` (tránh `KeyError` ở `PROVIDER_CDN`).

### 5.5 Kiểm tra khớp hình (stock và thư viện)

- **Thư viện**: khớp thẻ do người vận hành gán (`subject`, `style`, `action`, `filmed_at`). Đáng tin vì chính họ quay.
- **Stock**, chỉ cho cảnh không phân biệt vùng (hook, cảnh dựng chung, establishing): truy vấn dựng từ `shot.subject + action`, **không** dùng `visual` tự do của Groq. Ứng viên chỉ dùng khi thẻ / tiêu đề / mô tả / slug chứa **từ khoá chủ đề nguyên từ**: nhiều từ ("noodle soup") khớp cả cụm; chuẩn hoá số nhiều và dấu gạch ("pho-bo" = "pho bo"); bỏ dấu tiếng Việt (NFD) trước khi so; test với tiêu đề Wikimedia (ngắn, không có thẻ). Giữ R-4 (tag nước/nơi) và D-8 (thẻ AI).
- **Cảnh nhịp a/b không bao giờ lấy stock** (stock không phân biệt phở Bắc/Nam).
- Không tìm được → **mã 8** (CLI), không dùng lại clip cảnh khác, không lấy bừa.
- Giới hạn: thẻ stock do người tải lên tự gán, có thể sai; khớp từ khoá chỉ chứng minh người tải *nói* clip là phở. Studio hiện chữ rõ "Stock, chưa ai xem" cùng hướng dẫn tay (§ 6.6).

### 5.6 Luồng

```
Sheet (series) → nạp series
 → PRE-CHECK (trước Groq, $0): thư viện có đủ cảnh bắt buộc nhịp a/b? Thiếu → mã 8, status needs_broll, in danh sách
 → research → extract_facts (Groq) → write_story (Groq) → check_script [≤1 lần viết lại, chỉ gửi phần lỗi]
 → ghi script.json + facts.json      (giữ lại nếu bước sau lỗi)
 → resolve_shots: thư viện → stock có kiểm (chỉ cảnh không phân vùng) → thiếu: mã 8; chạy lại: --resume DIR
 → voice edge-tts cải tiến → render (cảnh + dissolve giữa nhịp) → Studio duyệt → approve (như cũ)
```

---

## 6. Chi tiết thiết kế

### 6.1 Nghiên cứu dữ kiện
Nguồn đúng danh sách `vn.json → sources`: `vietnam.travel` (tier 1, `auto_fetch: true`, có trang "21 must-try Vietnamese dishes"); `guide.michelin.com` (tier 2, **`auto_fetch: false`**, trả 202 rỗng: dữ kiện Michelin do người vận hành dán `facts_manual`); báo `e.vnexpress.net`, `tuoitrenews.vn`, `vietnamnews.vn` (tier 2). **Không** dùng "dân mạng review". Fact: hook 1, mỗi nhịp a/b ≥ 2 nếu nguồn có, tối đa `MAX_FACTS` = 12; chọn đoạn theo từ khoá nhịp bằng `select_text` vì `PROMPT_CHARS_TOTAL` = 18.000. Dữ kiện về cách bưng ra / gia vị ở nguồn tier 1/2 có thể mỏng → đó là lý do có `observe`.
Tên quán: chỉ khi có fact nêu đúng tên trong quote. `check_script` kiểm "tên riêng ngoài danh sách" (danh sách = tên trong quote, series, hồ sơ).

### 6.2 Độ dài, nhịp độ
- 8–10 cảnh, **mỗi cảnh nói 1–2 clip 3–4 s** (cắt cứng trong cảnh), hoặc cắt vào/ra từ một clip dài (M9). Ước lượng tổng thời lượng theo số từ; ngoài 55–95 s → cảnh báo (không chặn `--render-only`).
- Đo thật sau TTS.

### 6.3 Giọng 10a
edge-tts cải tiến, $0, 0 lượt Gemini: lời kiểu nói (§ 6.4), `rate`/`pitch` đổi nhẹ theo vai trò câu, khoảng nghỉ chèn bằng code giữa câu (không SSML, vì `edge-tts==7.3.1`; Dev xác nhận), thử vài giọng edge tiếng Mỹ (tên cần kiểm bằng `edge-tts --list-voices`). Quy tắc riêng cho TTS (M18): số đổi sang chữ **chỉ cho chữ gửi TTS** (màn hình vẫn là chữ số; `tts_text` đã tách), không dùng ngoặc đơn, tên Việt qua `pronunciations`, một dấu phẩy mỗi 6–8 từ. Người dùng + MKTG nghe bản edge-tts cải tiến và trả lời "còn mùi AI không".
`_groq_json` hiện thử lại 3 lần liền nhau: thêm chờ 5 s / 20 s hoặc theo `retry-after` của Groq; thông báo tiếng Việt (T13).

### 6.4 Quy tắc lời "như người"
1. Viết để **nghe**: dạng rút gọn ("it's", "you'll").
2. Câu dài ngắn xen kẽ (câu 3–5 từ xen câu 10–15 từ). **Câu mẫu của bản trước ("Same noodles. Very different bowl.") bị bỏ**: là khẳng định không nguồn (M3). Mẫu dùng được phải từ `facts.json`, vd hook: "Hanoi pho or Saigon pho? Planning a trip to Vietnam, you'll want to know."; nhịp a: "Vietnam's official tourism site lists pho among the dishes to try. So let's start in Hanoi." + fact A1 nói thành lời, không số mới; teaser: "Next time: where to try it in Hanoi. Follow, so you don't miss it."
3. Mở bằng người xem ("you" hoặc một câu hỏi).
4. Không văn danh sách ("Firstly…", "Here are…"); không hai câu liền bắt đầu cùng một chữ.
5. Chuyển nhịp bằng `bridge` ngắn.
6. Danh sách từ "mùi AI" ("delve", "tapestry", "vibrant", "nestled", "bustling", "In conclusion", "Whether you're… or…") ở hồ sơ.
7. Vẫn không thêm số / dữ kiện / ý kiến / "I tried" / khen. **Vẫn cho phép đối chiếu có nguồn**: "In Hanoi, X. In Saigon, Y." với X, Y là fact.
8. **Tự động hoá thành cảnh báo trong `check_script`** (không chặn): số dạng rút gọn ≥ N lần; không 3 câu liền cùng độ dài ±2 từ; không hai câu liền cùng chữ đầu; hook mở bằng "you" hoặc câu hỏi; từ cấm; "Firstly/Secondly". Phần còn lại kiểm bằng nghe.
9. Teaser chỉ một câu ("Next time"), không hứa nội dung chưa kiểm chứng; chỉ hẹn khi video sau đã có lịch.

### 6.5 Chuyển cảnh frame-exact, RAM-an toàn (T1, đo trên clip tổng hợp 1080×1920 25 fps)

**Vấn đề đo được**: nối video bằng `concat -c copy` còn âm thanh nối riêng thì điểm cắt copy **không chính xác theo khung**: +2 khung mỗi chỗ cắt (229 so với 225 dự kiến; lệch ~0,8–1 s qua 9–10 chỗ). `ov = 0,3 s` cũng chỉ bằng 7,5 khung ở 25 fps.

**Giải pháp (chốt)**:
- `ov = 8 khung = 0,32 s`. Làm tròn **lên** mọi `scene_dur` thành bội của 0,04 s.
- Mỗi cảnh ở ranh giới nhịp (trừ cảnh cuối) dựng dài `dur + 0,32 s` bằng **một** bộ mã hoá, ghi 3 file bằng muxer `segment` tại khung 8 và N−8: `-force_key_frames expr:eq(n,8)+eq(n,N-8)` `-f segment -segment_frames 8,N-8 -reset_timestamps 1` (đo: đúng 8 / 109 / 8 khung, đỉnh RAM 270 MB).
- `xfade` **chỉ** trên cặp đầu 8 khung + đuôi 8 khung (đo 386 MB mỗi lệnh).
- Nối `concat` copy theo thứ tự: `head0? mid0 x01 mid1 x12 …` (đo: 217 = 217 khung).
- **Kiểm bắt buộc**: tổng số khung video == Σ số khung các cảnh, sai → dừng, không xuất video.
- Chỉ **3 ranh giới** (hook→a, a→b, b→teaser) dùng dissolve; trong nhịp cắt cứng (M9), nên chỉ ~3–4 lệnh `xfade`.
- **Không** dùng một `xfade` chuỗi nhiều cảnh (2,8 GB), **không** dùng `split` + `trim` 3 bộ mã hoá (~800 MB).
- Cắt cứng trong nhịp: Tech Lead xác nhận rằng các điểm cắt copy *giữa cảnh cùng nhịp* cũng đúng từng khung với cùng tham số mã hoá (nếu không thì tạm dùng cách mã lại hoặc `-bf 0`); kiểm tổng khung ở trên là chốt cuối.
- Một cảnh có 2 clip: ghép 2 clip bằng `concat` filter ngay trong lệnh mã hoá của cảnh đó. RAM chưa đo; Tester đo cảnh thật có lớp phụ đề.
- RAM mỗi lệnh < 1 GB (đo 270–390 MB trên clip tổng hợp); **cảnh thật có lớp phụ đề chưa đo**.
- Dự phòng: `fade` vào/ra đen 0,15 s nếu không đạt.

### 6.6 Studio (10a: nhỏ)
- Hiện nhịp, loại cảnh, nguồn clip trong `studio_travel.travel_detail`; thêm `.get` cho `beat/shot/transition/series` để thư mục cũ vẫn chạy (T10).
- Kiểm `bridge`/`teaser`/`observe` chạy cả khi sửa lời trên Studio (`strict=False`); thêm giới hạn ≤ 12 từ cho các loại này vào `studio_travel.MAX_*`.
- **Không có UI cho mã 8 ở giai đoạn A**: Studio không có luồng nào chạm `build_media` (`--render-only` không bao giờ đi tới đó; chỉ `--travel --sheet` đi tới). Giai đoạn A chỉ ghi dòng `[NEEDS_BROLL]` vào log + Sheet `needs_broll`. Thêm `8: "needs_broll"` vào `ERROR_KINDS` cùng giai đoạn B (T9).
- Nhãn "Stock, chưa ai xem": giai đoạn A **không có nút "Báo sai"** (chưa có "thay clip"); chỉ hiện chữ hướng dẫn việc tay ("Bỏ clip đúng vào thư viện cảnh quay rồi bấm Dựng lại video").
- Dùng từ **"cảnh quay"** thay "B-roll" ở mọi chỗ người vận hành thấy (M16).
- Giai đoạn B (nếu A đạt): "thay clip từng cảnh", `8` trong `ERROR_KINDS`, `--resume` từ Studio. API ghi mới cần `X-Studio: 1` (C-0001-3), tách PR.
- Phụ đề (M10): chữ tiếng Anh theo cụm 3–6 từ bám tiếng nói (thời điểm theo trọng số từ như `subtitle_chunks` hiện có; ước lượng, không khớp tuyệt đối từng từ); VI chỉ khi `subtitles_vi=true`, nhỏ, sát đáy vùng an toàn.

### 6.7 Thông báo thiếu cảnh quay (CLI và Studio sau này, không dùng chữ "exit 8", "needs_broll", "BROLL_DIR")
> Chưa dựng được video: còn thiếu N cảnh quay.
> • Cảnh 4: bát phở Hà Nội đang được múc nước dùng …
> Hãy quay mỗi cảnh 6–10 giây (quay dọc, không chữ), bỏ vào thư mục `<đường dẫn>/inbox`, bấm "Thêm cảnh quay", rồi bấm "Dựng lại video".

### 6.8 Quy trình người vận hành mỗi video
1. Thêm hàng ở tab `Travel`, cột `series`.
2. Chạy `demo.py --sheet --travel`. Nếu báo thiếu cảnh quay → quay, thả vào `inbox`, bấm "Thêm cảnh quay", chạy lại (hoặc `--resume`).
3. Xem Studio, sửa lời nếu cần, Dựng lại.
4. Duyệt → đăng tay. **Checklist `post.txt` thêm** (M12): nếu video có giọng tổng hợp (edge-tts hay Gemini) thì bật công tắc "nội dung do AI tạo" của TikTok khi đăng cho đến khi đã đọc xong hướng dẫn hiện hành của TikTok về nội dung AI và ghi URL + ngày vào `TODO.md`. (Chưa xác minh quy định đó: DR này không khẳng định nội dung quy định.)
- Công sức: 2 buổi quay đầu (một quán mỗi vùng; mua 2–3 bát mỗi buổi); sau đó mỗi video vài phút xem Studio + dán `facts_manual` khi cần. Thời gian cụ thể **chưa đo**.

### 6.9 Hướng dẫn quay cho người vận hành (đưa vào tài liệu vận hành, M15)
Quay dọc 9:16, ≥ 1080p, 30 fps; chạm giữ vào bát để khoá nét/sáng; lau ống kính. Mỗi lần quay 10–15 s **một hành động**, giữ yên 1 s trước và sau, quay 2 lần mỗi cảnh. Máy đặt tựa lên bàn hoặc hai tay giữ. Ánh sáng ban ngày gần cửa sổ hoặc đèn quán, không flash; hơi nóng lên đẹp nhất khi ngược sáng, ngay sau khi múc. Ba góc: 45° (góc người ăn), thẳng từ trên xuống, cận cảnh. **Hai bát Bắc và Nam cùng góc, cùng khung** (cho hook). Chỉ quay tay, **không mặt người khác, không biển hiệu đọc được** nếu chưa xin phép; hỏi chủ quán trước. Tắt tiếng. (Âm thanh tự nhiên rất nhỏ, tiếng húp, tiếng muôi, làm giọng đỡ "máy" hơn mọi chỉnh giọng; để giai đoạn B vì lúc nhập đang bỏ tiếng.)

**Danh sách cảnh cho series phở** (mỗi kiểu `north` và `south`):

| Nhóm | Cảnh | Bắt buộc? |
|------|------|-----------|
| hook | `bowl-top` (bát nhìn thẳng từ trên xuống, mỗi kiểu 1) | Có (2) |
| mỗi kiểu | `ladle` múc nước dùng · `serve` tay bưng bát ra khỏi quầy · `season` thêm hành / rau / gia vị | Có (3 mỗi kiểu = 6) |
| mỗi kiểu | `establish` mặt quầy / quán không biển hiệu · `noodles` chần bánh phở cho vào bát · `meat` xếp thịt · `steam` cận cảnh hơi nóng · `payoff` đũa nâng sợi phở / húp nước (cho teaser) | Không (cảnh phụ, đỡ lặp) |

**Bắt buộc tối thiểu: 8 cảnh (2 `bowl-top` + 6 cho nhịp a/b) × 2 lần quay = 16 clip. Bộ đầy đủ: 20 cảnh (2 + 9 × 2).** Hai con số này thay cho 12 / 16 không nhất quán của bản trước; mọi chỗ (Q-2, R-5, DoD) dùng đúng hai số này.

---

## 7. Phạm vi

| Trong phạm vi (10a) | Ngoài phạm vi |
|---------------------|---------------|
| Thư viện + `--broll-add` + chuẩn hoá; kiểm khớp; mã 8 + `--resume`; khuôn một series; `observe`/`bridge`/`teaser`; quy tắc lời + cảnh báo; edge-tts cải tiến; dissolve frame-exact; phụ đề EN theo cụm; Studio nhỏ; checklist AI | **Gemini TTS cho travel (DR-0010b)**; **không sửa `demo.py` về Gemini**; Veo/Flow; vision; Studio UI cho mã 8 (giai đoạn B); âm thanh nền (B); đổi `app.html`; Shopee |

Móc vào `demo.py` chỉ gồm: cờ `--travel --broll-add`, `--resume`, truyền mã 8; mỗi chỗ vài dòng (T17).

### 7.1 DR-0010b (chỉ phác thảo, viết sau)
Gemini cho travel sau khi `feat/gemini-quota` merge; yêu cầu nhánh đó cung cấp hàm công khai `gemini_tts_text(prompt, voice, out_path, models)` bọc reserve / hoàn lại / chặn; **không chép logic quota vào `travel.py`**. Thiết kế đề xuất (T11): **mỗi nhịp một lượt** (hook, a, b, teaser ≈ **4 lượt/video**, như video sản phẩm); âm 24 kHz PCM mono; tách trong nhịp bằng khoảng lặng gần nhất theo tỉ lệ từ; cache câu cố định theo (text, voice, model); sửa một cảnh = đọc lại một nhịp; `aresample=44100` sau khi cắt. Phương án khác: 1 lượt cả video + chọn điểm lặng gần nhất bằng quy hoạch động (cần đo). Cả hai phải đo thật trong thí nghiệm. A/B nghe (M19): ≥ 3 người nghe mù (có 1 người nói tiếng Anh bản ngữ), chọn Gemini nếu ≥ 2/3; tiêu chí: 3 giây đầu ấm, câu hỏi lên giọng, đều giọng và âm lượng 60–90 s, khoảng nghỉ hợp nhịp hình không tiếng click / cụt chữ, đọc tên Việt, mỏi tai, nghe trên loa điện thoại; công bằng: cùng hình và cùng lời; thay "lệch thời lượng ≤ 10%" bằng "tổng 60–90 s và mỗi đoạn tách khớp độ dài cảnh (không cụt chữ, không tràn sang cảnh sau)". Chi phí thật: mỗi lần sửa một dòng trên Studio = 1 lượt Gemini đọc lại cả nhịp (hoặc cả video); hạn mức 10 lượt/ngày dùng chung với video sản phẩm, bài tập. Thí nghiệm cho phương án mỗi-nhịp ≈ 4 lượt (+4 nếu chỉnh prompt), cho phương án 1 lượt ≈ 1 lượt (+1). Số lượt thí nghiệm cần người dùng duyệt ở DR 10b.

---

## 8. Ràng buộc

### 8.1 Ràng buộc mới

| Mã | Nội dung | Nơi áp dụng |
|----|----------|-------------|
| C-0010-1 | Cảnh có `shot.subject` phải có clip mà thẻ chứa từ khoá nguyên từ. Không có → mã **8**. Không dùng lại clip cảnh khác, không lấy bừa, trong video v2 | `travel.py` |
| C-0010-2 | Cảnh nhịp a/b chỉ lấy clip thư viện có đúng `style` và `action` (bắt buộc, không chỉ cộng điểm); không stock | `travel.py` |
| C-0010-3 | Tên một quán chỉ xuất hiện khi có fact tier ≤ 2 nêu đúng tên trong quote. Clip chung cho quán có tên: nhãn "Illustrative footage" một lần ở cảnh đó. Clip quay đúng quán (`shop` khớp) thì không cần nhãn | `travel.py` |
| C-0010-4 | `bridge` / `teaser` / `observe`: ≤ 12 từ, không chữ số, không so sánh / xếp hạng / từ tuyệt đối, tên riêng chỉ trong danh sách; `observe` chỉ gắn clip `own work` và chỉ tả điều thấy; mọi khẳng định Bắc vs Nam cần fact. Kiểm chạy cả `strict=False` | `travel.py`, `studio_travel.py` |
| C-0010-5 | Lời nói "Hanoi" / "Saigon" chỉ khi `filmed_at` của clip hoặc fact tương ứng; nếu không dùng "Northern-style" / "Southern-style" | `travel.py` |
| C-0010-6 | `index.json` nằm trong `BROLL_DIR`, ghi nguyên tử + khoá đơn giản, **không vào git** (chỉ mẫu). Clip sưu tầm: `license` là tên giấy phép thật thuộc `LICENSE_OK`, có `source` https, cấm tiktok / instagram / google / facebook / blog | `travel.py`, `.gitignore` |
| C-0010-7 | Chuyển cảnh: không một lệnh FFmpeg nào chứa nhiều hơn 2 cảnh; RAM mỗi lệnh ≤ 1 GB; tổng khung video == Σ khung các cảnh, sai thì dừng | `travel.py` |
| C-0010-8 | `render` kiểm clip thư viện bằng `library_problem` (đọc lại chỉ mục, kiểm sha256, tên file); `library` không bao giờ vào `PROVIDER_DOMAIN`, `download_media` | `travel.py` |
| C-0010-9 | `post.txt` có dòng nhắc bật công tắc nội dung AI cho video có giọng tổng hợp, kèm nhắc ghi URL + ngày vào `TODO.md` | `travel.py` (`write_post_kit`) |
| C-0010-10 | Mã 8 phát ra **trước** khi gọi Groq nếu thiếu cảnh bắt buộc nhịp a/b; thiếu muộn → giữ `script.json` + `facts.json`, `--resume` | `travel.py`, `demo.py` |
| C-0010-11 | Clip tự quay: chỉ tay, không mặt người khác, không biển hiệu đọc được nếu chưa xin phép; ghi rõ trong tài liệu vận hành | tài liệu |

### 8.2 Quan hệ với ràng buộc cũ
C-0002-1, C-0008-1, C-0002-2/C-0008-2, C-0002-4, C-0002-5, C-0001-1/-3: giữ nguyên. **Mở rộng** C-0002-3: clip thư viện đi qua `library_problem` riêng, không sửa `media_problem`/`PROVIDER_DOMAIN`. C-0002-4: dòng `official_check_line` chỉ cho video có fact `tier1_categories`. DR-0002 `tone` vẫn cho video 4 cảnh; video v2 dùng `spoken_style`. DR-0008 quyết định 3 giữ nguyên ở 10a.

---

## 9. Bảng quyết định (kiểm được)

| # | Điều kiện đầu vào | Kết quả mong đợi | Cách kiểm |
|---|-------------------|------------------|-----------|
| D-1 | Cảnh `subject=pho, style=north, action=ladle`; thư viện có clip khớp | Dùng clip đó, copy vào thư mục video tên `clip_N.mp4` (hardlink hoặc copy) | Thư viện giả 3 clip |
| D-2 | Stock trả clip thẻ "vietnam, windmill, turbine" cho cảnh hook | Bị loại; không clip khác → mã 8 sau Groq (nếu chưa pre-check); log nêu cảnh cần | Searcher giả |
| D-3 | Cảnh hook, stock có clip thẻ "pho, noodle soup, vietnam" | Dùng, cờ `stock: true`, Studio hiện "Stock, chưa ai xem" | Searcher giả |
| D-4 | Cảnh nhịp a, thư viện thiếu, stock có clip "pho" | Không dùng stock; mã 8 | Searcher giả |
| D-5 | Hai cảnh cần cùng clip, thư viện chỉ 1 clip | Không dùng lại trong cùng video; mã 8 (hoặc clip khác đủ điều kiện) | Thư viện giả |
| D-6 | Thư viện thiếu cảnh bắt buộc nhịp a/b khi bắt đầu `run_row` | Mã 8 **trước khi gọi Groq** (kiểm Groq không bị gọi), Sheet `needs_broll`, danh sách thiếu bằng tiếng Việt § 6.7 | Giả Groq báo lỗi nếu bị gọi |
| D-7 | Stock rỗng ở bước media (thiếu muộn) | `script.json` + `facts.json` còn; `--resume DIR` chạy lại từ bước media, không gọi Groq lại | Thư mục tạm |
| D-8 | Chạy lại hàng Sheet `needs_broll` sau khi thêm clip | Được xử lý (không bị bỏ qua) | Sheet giả |
| D-9 | `bridge`/`teaser` có chữ số, "famous", "best", tên riêng lạ | `check_script` báo lỗi; Groq viết lại 1 lần; vẫn sai → `needs_sources` | Script giả |
| D-10 | Cùng lỗi D-9 khi sửa trên Studio (`strict=False`) | Vẫn báo lỗi | Gọi `check_script(strict=False)` |
| D-11 | `observe` chứa "than", "usually", hoặc chữ số, hoặc không có từ nào trong `description` của clip | Báo lỗi | Script giả |
| D-12 | `observe` gắn clip stock hoặc clip không `own work` | Báo lỗi | Script giả |
| D-13 | `line` nói "Hanoi" nhưng clip `filmed_at=other`, không fact | Báo lỗi; lời phải là "Northern-style" | Script giả |
| D-14 | `line` có "famous", "best", "top", "authentic", "real", "better", "original", "must", "worth" trong cảnh answer/observe | Báo lỗi | Script giả |
| D-15 | `line` có tên quán không có trong quote nào | Mã 5 | Script giả |
| D-16 | Fact có tên quán; clip chung | Nhãn "Illustrative footage" một lần ở đúng cảnh | Khung hình |
| D-17 | **Thư mục video cũ thật** (`20261118_083204_…` trong worktree `travel-p1`) chạy `--render-only` | Dựng bình thường, không lỗi do thiếu `beat/shot/transition/series` | Bản sao |
| D-18 | Dựng video v2 8–10 cảnh, 3 ranh giới nhịp | Tổng khung == Σ khung cảnh (kiểm bắt buộc); âm thanh không lệch hình quá 1 khung; ≤ 4 lệnh xfade | `ffmpeg` đếm khung |
| D-19 | Tổng khung sai (cố ý) | Dừng, không xuất `video.mp4`, thông báo tiếng Việt | Giả lập |
| D-20 | Đỉnh RAM từng lệnh FFmpeg khi dựng cảnh thật có phụ đề | ≤ 1 GB | `/usr/bin/time -l` |
| D-21 | `render` với mục `provider: library` giả không có trong `index.json` | Raise lỗi (không tin `script.json`) | Test |
| D-22 | Clip thư viện bị thay file (sha256 khác chỉ mục) | Raise lỗi | Test |
| D-23 | Mục library có `id` hợp lệ nhưng `file` có `../` | Raise lỗi | Test |
| D-24 | `write_credits` với mục library (không `page`) | Không `KeyError`; tác giả "own footage" | Test |
| D-25 | `--broll-add` file `IMG_1234.MOV` iPhone dọc, HEVC, đang xoay | Một lệnh ffmpeg ra 1080×1920 25 fps H.264, đúng chiều, bỏ tiếng; tên do công cụ sinh | Clip mẫu |
| D-26 | `--broll-add` cùng một video nhập hai lần (tên khác) | Lần hai bị bỏ qua nhờ `source_sha256` | Clip mẫu |
| D-27 | File > ~500 MB hoặc > 60 s; symlink; tên có dấu tiếng Việt NFD | Từ chối (hai đầu) / chuẩn hoá NFC rồi xử lý | Thư mục tạm |
| D-28 | Clip sưu tầm có `source` từ host tiktok/instagram, hoặc `license` "CC0" cho nguồn Pixabay | Từ chối | Thư mục tạm |
| D-29 | `--broll-add` khi `inbox` trống / thư viện rỗng | Câu "Thư viện cảnh quay đang trống tại <đường dẫn>…"; cuối lệnh in bảng còn thiếu | Thư mục tạm |
| D-30 | Chọn clip với 2 biến thể cùng cảnh | Cùng chủ đề dựng lại ra cùng clip (hạt giống); không dùng clip đã dùng trong video này | Test |
| D-31 | Cảnh hook | `text` ≤ 8 từ, `line` = câu hỏi nguyên văn, 2 clip 1,5 s (`bowl-top` Bắc rồi Nam) | Script |
| D-32 | Series `outro: false` | Không có cảnh outro; dòng nguồn + tháng năm nằm trong cảnh teaser và caption; không có "Check the official site" khi không có fact tier 1 | Khung hình, `post.txt` |
| D-33 | `post.txt` video có giọng edge-tts | Có dòng nhắc bật công tắc nội dung AI + ghi URL/ngày | Đọc file |
| D-34 | `check_script` với lời không dùng dạng rút gọn / 3 câu liền cùng độ dài / hai câu liền cùng chữ đầu | Cảnh báo (không chặn) | Script giả |
| D-35 | `_groq_json` lỗi 429 | Chờ 5 s / 20 s (hoặc `retry-after`), thông báo tiếng Việt | Giả lập |
| D-36 | Mỗi lượt gọi Groq | Ghi `usage` token vào log | Đọc log |
| D-37 | Hồi quy: hàng Sheet `series` trống; video sản phẩm / bài tập `--render-only`, `--approve` | Không đổi hành vi (kể cả "dùng lại clip cảnh trước" của luồng 4 cảnh cũ) | Bản sao |
| D-38 | Phụ đề: `subtitles_vi=false` (mặc định series phở) | Video chỉ có chữ EN cụm 3–6 từ, không vẽ VI; `script.json` vẫn có `subs.vi` đã qua kiểm số và Studio hiện VI để người vận hành xem. Đặt `true` thì VI hiện nhỏ sát đáy vùng an toàn | Khung hình + Studio |
| D-39 | Studio mở thư mục v2 | Hiện nhịp, loại cảnh, nguồn clip; nhãn stock có hướng dẫn tay, không có nút "Báo sai"; không có chữ "B-roll" | MKTG |

## 10. E2E

| # | Kịch bản | Mong đợi |
|---|----------|----------|
| V-1 | Cùng câu hỏi phở Bắc/Nam, series `pho-north-south`, thư viện đủ 16 clip bắt buộc | Video 60–90 s, 4 nhịp, mọi cảnh có hình khớp lời (không cối xay gió), 3 dissolve giữa nhịp, hook có 2 bát cùng góc trong 3 s đầu. Tester ghi thời gian dựng và đỉnh RAM |
| V-2 | Thiếu clip `ladle` Sài Gòn | Mã 8 **trước Groq**, thông báo tiếng Việt § 6.7, Sheet `needs_broll`; thêm clip bằng `--broll-add` (không đổi tên tay) rồi chạy lại xong; không cảnh nào dùng stock lạc đề |
| V-3 | Nghe bản edge-tts cải tiến (người dùng + MKTG) | Ghi nhận "còn mùi AI" hay không; đây là kiểm bằng nghe, không phải PASS tự động |
| V-4 | Có fact tên quán (Michelin dán `facts_manual`) + clip quay đúng quán | Tên quán chỉ ở lời có fact; không cần nhãn minh hoạ |
| V-5 | **Mặc định video đầu (U4)**: không có tên quán | Không có tên quán nào trong `line`/`text`/`subs`/`caption`; không nhãn "Illustrative footage" (không có quán có tên); `check_script` chặn tên quán nếu Groq tự thêm |
| V-6 | Hàng không có `series` | Dựng như cũ |
| V-7 | MKTG review (travel-review) | Không mức "Chặn": hook 3 s, không bịa, `observe` không khẳng định, nhãn, vùng an toàn, caption |

---

## 11. Quyết định của người dùng

**Đã chốt (2026-11-18, từng câu trả lời tại cổng hỏi):**

| # | Chủ đề | Người dùng chọn | Hệ quả trong DR |
|---|--------|-----------------|-----------------|
| U1 | Giọng | Làm **10a trước**, Gemini để **10b**; 10a dùng edge-tts cải tiến | DR này không có Gemini, không thay DR-0008 quyết định 3; 10b chỉ phác thảo (§ 7.1). Chi phí 10a: 0 lượt Gemini (§ 3.1) |
| U2 | Thông lượng | **3–4 video/tuần** ban đầu | § 3.2 |
| U3 | Phụ đề tiếng Việt | **Tắt mặc định** cho series phở, bật bằng cờ `subtitles_vi`; VI vẫn được viết cho người vận hành xem trên Studio | Q8, D-38 |
| U4 | Tên quán | **Video đầu không nêu tên quán**; chỉ nêu khi đã có nguồn tin cậy **và** cảnh quay đúng quán đó | Q9, V-5 (mặc định), C-0010-3 |

**Giả định, chưa xác nhận (người dùng chưa được hỏi):**

| # | Chủ đề | Giả định của BA | Trạng thái |
|---|--------|-----------------|------------|
| U5 | Ai quay, công sức | Người dùng tự quay bằng điện thoại, 2 buổi (một quán mỗi vùng, 2–3 bát mỗi buổi), tối thiểu **16 clip**; hỏi phép chủ quán, chỉ quay tay, không biển hiệu. Chưa quay xong thì tạm tải tay clip Pixabay/Pexels ghi đúng tên giấy phép (không "CC0"), nhưng nhịp a/b vẫn cần clip có `style` rõ | **chưa xác nhận** |
| U6 | Thứ tự merge | #17 → gemini-quota → studio-create-video → 10a → 10b; BA nhờ người điều phối chạy lại `branch_observer` khi hai nhánh kia đã commit | **chưa xác nhận** |

**Chờ:** xác nhận duyệt DR (cả bản) + U5 / U6. Trạng thái giữ "Đề xuất" cho tới khi người dùng nói "đồng ý".

---

## 12. Rủi ro

| # | Rủi ro | Cách xử |
|---|--------|---------|
| R-1 | Thẻ stock sai; `observe` đạt kiểm từ vựng nhưng sai với hình | Nhịp a/b chỉ thư viện; Studio duyệt; MKTG |
| R-2 | Dữ kiện tier 1/2 về cách phục vụ phở mỏng | `observe` (có điều kiện) + `bridge`; không bịa |
| R-3 | Nguồn Michelin chặn bot | `facts_manual` do người vận hành dán |
| R-4 | Công sức quay | 16 clip bắt buộc, 2 buổi; tái dùng cho mọi video phở (nhưng lặp, xem U2) |
| R-5 | Hai worktree / máy thấy thư viện khác | `BROLL_DIR` mặc định cố định ngoài repo, chỉ mục cạnh clip |
| R-6 | Dissolve / frame-exact trên cảnh thật chậm hoặc ngốn RAM | Tester đo; dự phòng fade đen; kiểm tổng khung |
| R-7 | Hạn mức Groq free khi prompt dài | **Chưa rõ**; ghi `usage`, backoff |
| R-8 | `check_script` thêm nhiều loại cảnh gây hồi quy | D-17, D-37 bắt buộc, đo trên thư mục cũ thật |
| R-9 | Dữ liệu Veo là số bên thứ ba | Không dùng để quyết |
| R-10 | Quy định nhãn AI của TikTok chưa xác minh | Người vận hành đọc hướng dẫn hiện hành, ghi URL + ngày; tạm thời bật công tắc (C-0010-9) |

---

## 13. Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Cập nhật |
|----------|----------|
| `docs/specs/architecture/capabilities/travel-content.md` | Đã có con trỏ "Kế hoạch v2"; sau khi Dev xong: định dạng 4 nhịp, loại cảnh, thư viện, mã 8, dissolve |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | **Phải viết** (M20): "cảnh quay" là gì; cách thêm (danh sách đánh số, không đổi tên tay, bấm đúp `.command`); hướng dẫn quay (§ 6.9); xử lý thông báo thiếu cảnh quay; nhãn "stock chưa xem" nghĩa là gì và làm gì; dán `facts_manual` cho Michelin; **nghe thử giọng** (bản edge-tts cải tiến); bật công tắc nội dung AI khi đăng; sao lưu thư viện |
| `.claude/CLAUDE.md` | `--broll-add`, `--resume`, mã 8, `BROLL_DIR`, thư viện |
| `.env.example` | `BROLL_DIR` (mặc định `~/tiktok-broll`, không bắt buộc) |
| `TODO.md` | Dòng v2 (đã thêm); cập nhật khi xong; URL + ngày quy định AI |
| `content/travel/series/pho-north-south.json`, `broll/index.sample.json`, `audiences/en-us.json`, `destinations/vn.json` | Mới / sửa |
| DR-0008 | Không sửa (10a không thay quyết định 3) |

## 14. File code có thể đổi (cho Dev, BA không sửa)

`travel.py` (nạp series; `write_story`; `build_script` thêm `beat/shots/transition`, loại cảnh; `check_script`, cả `strict=False`; kiểm khớp; `library_problem`; chọn clip; `resolve_shots`; pre-check mã 8; `--resume`; `_groq_json` backoff + `usage`; `_render_scene`/`render` dissolve `segment`; `write_credits` dùng `.get`; `write_post_kit`; chữ phụ đề EN cụm) · `demo.py` (móc `--broll-add`, `--resume`, mã 8, hunk nhỏ) · `product_sources.py` (cột `series`; trạng thái `needs_broll` không bị bỏ qua) · `scripts/them-canh-quay.command` (mới) · `backend/app/api/studio_travel.py` (`.get`, `MAX_*` cho loại cảnh, hiển thị) · `studio.html` (nhãn stock + hướng dẫn tay) · `.gitignore` (nếu `BROLL_DIR` trong repo).

## 15. Kế hoạch theo vai trò

| Vai trò | Việc |
|---------|------|
| BA | Viết/sửa DR (xong), cập nhật SSoT, điền "Kết quả" từ báo cáo Tester |
| Tech Lead | Xác nhận dựng frame-exact cho cảnh thật (cả điểm cắt trong nhịp), đo RAM và thời gian; khoá/ghi nguyên tử chỉ mục; backoff Groq |
| Dev | Giai đoạn A theo § 14 trong `.worktrees/travel-story`; rebase sau mỗi bước merge; hunk `demo.py` nhỏ; khối Studio travel tách riêng |
| Reviewer | Đối chiếu C-0010-1…11, hồi quy D-17, D-37 |
| Tester | Bảng D-1…D-39 trên bản sao (edge-tts; không Gemini/Drive/Sheet/TikTok thật); đo RAM, thời gian; V-1, V-2, V-6; trích nguyên văn |
| MKTG | V-1, V-4, V-5, V-7; độ dễ dùng `--broll-add`, tài liệu, thông báo thiếu cảnh quay |
| Người dùng | Duyệt DR (chờ), xác nhận U5/U6, quay cảnh, nghe bản giọng (U1–U4 đã trả lời) |

Thứ tự merge (T17): (1) `travel-p1` PR #17 → (2) `gemini-quota` → (3) `studio-create-video` → (4) `travel-story` 10a → (5) 10b. Rebase sau mỗi bước.

## 16. Tiêu chí hoàn thành (DoD)

- [ ] D-1…D-39 đạt trên bản sao (Tester ghi nguyên văn); riêng D-17 chạy trên thư mục video cũ thật
- [ ] V-1, V-2, V-6 đạt; V-7 MKTG không "Chặn"; V-3 ghi nhận kết quả nghe
- [ ] Đo và ghi: thời gian dựng 60–90 s, đỉnh RAM từng lệnh (≤ 1 GB, cảnh thật có phụ đề), token Groq thật mỗi video
- [ ] Kiểm tổng khung video chạy được và chặn được
- [ ] Không có file video thư viện hay `index.json` thật trong git; chỉ file mẫu
- [ ] Hướng dẫn vận hành đã viết (§ 13) và MKTG xác nhận người không code làm theo được
- [ ] Hồi quy video sản phẩm, bài tập, travel 4 cảnh không đổi

## 17. Kết quả

*(BA điền sau khi Dev / Tester xong. Chưa có.)*

---

## 18. Xử lý review (Tech Lead T1–T17, Marketing M1–M20)

Ghi chú: người điều phối ghi "T1–T19" nhưng chỉ gửi nội dung T1–T17; T18, T19 chưa nhận được. Cột "Loại": **Nhận** = đã đưa vào DR đúng như đề xuất; **Khác** = nhận một phần / làm khác (nêu lý do); **Ngoài** = ngoài phạm vi 10a; **Người dùng** = cần người dùng quyết (§ 11).

| # | Loại | Xử lý |
|---|------|-------|
| T1 | Nhận | § 6.5: `ov` = 8 khung, `segment` muxer, kiểm tổng khung. Thêm: Tech Lead xác nhận cả điểm cắt trong nhịp (đo mới cho dissolve) |
| T2 | Nhận | § 5.3 mục 5: không có ffprobe; đo sau chuẩn hoá |
| T3 | Nhận | § 5.3 mục 3 |
| T4 | Nhận | § 5.3, C-0010-6: chỉ mục ở `BROLL_DIR`, mẫu trong git |
| T5 | Nhận | § 5.3: `os.link` / `copy2`, luôn `clip_N.mp4` |
| T6 | Nhận | § 5.4, C-0010-8, D-21…D-24 |
| T7 | Khác | Regex chỉ áp cho tên **công cụ sinh** (kết hợp M16: người vận hành chọn số cảnh, không đặt tên); symlink, `resolve()`, NFC/NFD đã đưa vào |
| T8 | Nhận | § 5.6, C-0010-10, D-6…D-8; `needs_broll` không bị bỏ qua khi chạy lại (thêm) |
| T9 | Nhận | § 6.6: giai đoạn A chỉ log + Sheet; `ERROR_KINDS` ở giai đoạn B |
| T10 | Nhận | § 5.1, § 6.6, D-10, D-17 |
| T11 | Khác | Đưa sang 10b (§ 7.1) vì Gemini tách khỏi 10a; ghi cả hai phương án |
| T12 | Nhận | Tách 10a / 10b; sửa mâu thuẫn "không sửa Gemini trong `demo.py`" (§ 7) |
| T13 | Nhận | § 6.3, D-35 |
| T14 | Nhận | § 3.1, D-36; chỉ gửi phần lỗi của `previous` khi viết lại (Dev) |
| T15 | Nhận | § 5.2 một file series; bỏ `usage.json`; bảng còn thiếu cuối `--broll-add`; `stock: true` thay `verified` |
| T16 | Nhận | § 3.1 (≈ 3 phút, Tester đo) |
| T17 | Nhận | § 15; BA nhờ người điều phối chạy lại `branch_observer` |
| T-thư viện | Nhận | § 5.5: nhiều từ, số nhiều, gạch, dấu NFD, test tiêu đề Wikimedia; mã 8 sớm là phương án dự phòng, không vision |
| M1 | Nhận | Loại cảnh `observe` (§ 5.1, C-0010-4); kiểm từ vựng + người duyệt; Bắc vs Nam vẫn cần fact |
| M2 | Nhận | `style` + `filmed_at`, C-0010-5 |
| M3 | Nhận | Bỏ câu mẫu, thay bằng câu từ `facts.json` (§ 6.4) |
| M4 | Nhận | `text` hook ≤ 8 từ do series cung cấp; 2 clip 1,5 s `bowl-top`; chỉ giữ "Follow, so you don't miss it" ở teaser |
| M5 | Nhận | § 5.1: nói đúng nội dung nguồn, cấm best/top/…; không số "21" nếu quote không có |
| M6 | Khác | Bỏ outro cho series phở; nhưng **vẫn giữ nguồn + tháng năm** ở cảnh teaser và caption (không bỏ hoàn toàn để giữ C-0008-2); câu "Check the official site" chỉ khi có fact tier 1 |
| M7 | Nhận | Teaser "Next time: where to try it in Hanoi."; "worth" cấm; chỉ đăng khi video sau có lịch |
| M8 | Người dùng | U4 |
| M9 | Nhận | 1–2 clip 3–4 s mỗi cảnh; dissolve chỉ 3 ranh giới nhịp |
| M10 | Khác | EN cụm 3–6 từ nhận; VI bật tắt thành cờ, **mặc định tắt là quyết định của người dùng** → U3 |
| M11 | Nhận | Nhãn một lần ở cảnh có quán + clip chung (C-0010-3) |
| M12 | Nhận | C-0010-9, § 3.3, § 6.8; sửa lại ý "không nhãn AI là lợi thế" (giọng tổng hợp vẫn có thể cần nhãn); không khẳng định quy định chưa xác minh |
| M13 | Nhận | § 5.3 mục 7: tên giấy phép thật (bỏ "CC0" cho Pixabay/Pexels); CC BY ghi công trên khung; C-0010-11 |
| M14 | Ngoài | Âm thanh nền thật: giai đoạn B (nhập đang `-an`, theo T3) |
| M15 | Nhận | § 6.9: 16 clip bắt buộc / 20 cảnh đầy đủ; thêm các cảnh thiếu; hướng dẫn quay; 2 buổi |
| M16 | Nhận | § 5.3 (chọn số cảnh, tự đổi tên, `.command`, mặc định `~/tiktok-broll`, thư viện trống, bắt buộc `action` nhịp a/b), § 6.6, § 6.7. Giai đoạn A không có nút "Báo sai" |
| M17 | Người dùng | U2 |
| M18 | Nhận | § 6.4 mục 8 và các quy tắc TTS (§ 6.3) |
| M19 | Khác | Tiêu chí A/B chuyển sang 10b (§ 7.1); 10a chỉ nghe bản edge-tts cải tiến (V-3) |
| M20 | Nhận | § 13: nội dung hướng dẫn vận hành phải viết |
