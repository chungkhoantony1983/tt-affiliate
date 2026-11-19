# DR-0012: Sổ đếm lượt Gemini TTS, kiểm tra trước khi lồng tiếng và hiển thị giọng đọc

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| Đã duyệt, đang triển khai (bản 3: ghi câu trả lời Q-1…Q-6) | 2026-11-13 | Claude (BA) | chungkhoantony1983, 2026-11-13 (người điều phối chuyển lời) |

Capability: `video-render` · Nhánh: `feat/gemini-quota` · Domain workflow: `spec`

Vai trò: **BA** = `ba` · **Dev** = `dev` · **Reviewer** = `reviewer` · **Tester** = `tester` · **MKTG** = `marketing` (đánh giá chữ trên Studio, thông báo trên Terminal và tài liệu dưới góc nhìn người vận hành không rành kỹ thuật).

> **Nền so sánh đã đổi.** Nhánh này tạo từ `22caf14`, nhưng `origin/main` hiện là `1ce153a` (PR #9, merge 2026-11-13). PR #9 **đã có sẵn chuỗi giọng dự phòng**. DR này viết theo `1ce153a`. Trước khi Dev bắt đầu, người điều phối phải đưa `origin/main` vào nhánh (xem R-8).

---

## Bối cảnh

**Yêu cầu nguyên văn (2026-11-13)**: "Do Gemini cũng có những hạn chế khi tạo video trong một khoảng thời gian nên nên có cơ chế: ưu tiên dùng gemini; check khi chuẩn bị tạo video với gemini xem có thể hết token chưa; nếu bị báo hết thì nên dùng một trình khác để tạo như là một backup (groq hoặc chatgpt hoặc cái free khác)."

**Gemini được dùng ở đâu (đã đọc code)**:

| Việc | Ai gọi | Code đo được hạn mức? |
|------|--------|:---:|
| Viết kịch bản | Groq (`generate_script`), **không** phải Gemini | — |
| Lồng tiếng (TTS) | `demo.py` → `_gemini_tts` gọi Gemini API | Có, bằng cách tự đếm |
| Ảnh nhân vật | Mặc định `IMAGE_PROVIDER=manual`: người vận hành tạo trong app Gemini | Không |
| Clip động tác bài tập | Người vận hành tạo trong app Gemini | Không |

Chỗ duy nhất code tự gọi Gemini và có thể hết lượt là **lồng tiếng**. DR này xử lý chỗ đó.

**Đã có sẵn trên `main` (`1ce153a`, commit `12c71fe`)**:

| Ý trong yêu cầu | Trên `main` | Còn thiếu |
|-----------------|-------------|-----------|
| Ưu tiên Gemini | Có: `generate_voiceovers` thử `gemini_tts_models(model)` = model chính rồi `GEMINI_TTS_FALLBACK_MODELS` | — |
| Backup khi hết | Có: mặc định `gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts`, cuối cùng edge-tts. Mỗi video một model; `segments[i].tts_model` ghi model đã dùng; `revoice_changed` đọc lại bằng đúng model đó | Chưa ai ghi nhận đã nghe thử hai model phụ với video sản phẩm (R-3) |
| Kiểm tra trước khi tạo | **Không có** | Toàn bộ DR này |

**Vấn đề còn lại (gốc rễ)**:

1. **Không kiểm tra trước.** Mỗi model được gọi lần lượt từng câu cho tới khi lỗi. Model còn 2 lượt, video cần 4 câu: 2 lượt bị dùng rồi bỏ. Chuỗi 3 model có thể phí lượt ở cả 3.
2. **Mọi lỗi 429 đều bị coi như nhau.** `_gemini_tts` bỏ nội dung phản hồi 429, không phân biệt "gọi quá nhanh trong 1 phút" với "hết lượt trong ngày".
3. **Không nhớ là đã hết.** Video kế tiếp trong cùng lần chạy `--sheet` lại thử model đã hết.
4. **Sửa lời đọc trên Studio** khi thiếu lượt: gọi vài câu rồi lỗi, phí các lượt đã gọi (audio cũ vẫn giữ nguyên, đúng C-0001-1).
5. **Người vận hành không biết còn bao nhiêu lượt, video đang dùng giọng nào.** Studio ghi cứng `GEMINI_PER_DAY = 10`. Video rơi sang giọng miễn phí không được nhắc ở đâu, và sau khi duyệt (lên Drive, xoá khỏi máy) thì không đổi giọng được nữa. Studio không có cách đọc lại bằng Gemini.
6. **Tài liệu chưa theo kịp PR #9**: `video-render.md`, `.claude/CLAUDE.md`, hướng dẫn vận hành chưa nhắc chuỗi model phụ.

**Số liệu và nguồn**:

| Số liệu | Giá trị | Nguồn |
|---------|---------|-------|
| Free tier Gemini TTS | 10 lượt/ngày cho **mỗi model** | `.env.example`, `.claude/CLAUDE.md`, thông báo lỗi trong `_gemini_tts`, ghi chú 2026-11-11 (quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`) |
| Lượt cho 1 video sản phẩm | khoảng 4 (1 lượt/câu; kiểu tiểu phẩm nhiều hơn, vd OMNIEAR 5 cảnh) | `.env.example`, `TODO.md` |
| Lượt cho 1 video bài tập | động tác 5–6 · mở đầu 6 · tổng kết Bát Đoạn Cẩm 10 | `exercise.py`, `content/exercise_curriculum.json` |
| Khoảng nghỉ giữa 2 lời gọi | 7 giây | `generate_voiceovers` |
| Model | sản phẩm `gemini-3.8-flash-tts` · động tác `gemini-3.1-flash-tts-preview` · mở đầu/tổng kết `gemini-2.5-flash-preview-tts` | `demo.py`, `exercise.py` |
| Hạn mức 10 lượt/ngày có đúng cho 2 model bài tập | **chưa xác minh** | — |
| Giờ có lại lượt | nửa đêm giờ Pacific, tức **khoảng** 15:00 giờ Việt Nam (14:00 khi Mỹ dùng giờ mùa hè) | Người điều phối nêu; **BA chưa đối chiếu tài liệu Google**. Code tính từ múi giờ, không ghi cứng 15:00 |
| Hạn mức theo phút, tên `quotaId` của nó | **chưa xác minh** | — |
| Lời gọi lỗi (5xx, timeout, 429) có bị tính lượt không | **chưa xác minh** | — |
| Gemini TTS đôi khi đọc sai chữ, đọc bịa thêm câu | đã gặp ("pha" → "sờ và"; trà ô long: thêm "mình mới mua… 120 ngàn") | Hướng dẫn vận hành; `TODO.md` trên `main` |

**Giọng miễn phí (edge-tts) có giữ đúng giới tính và vùng miền không** (đối chiếu `VOICES` và `_tts` trong `demo.py`):

| Trường hợp | edge-tts dùng | Khớp? |
|-----------|---------------|-------|
| Người dẫn nữ Sài Gòn (`nu_nam`) | `vi-VN-HoaiMyNeural` | Đúng giới tính. Giọng vùng nào: **chưa xác minh trong tài liệu dự án**, phải nghe |
| Người dẫn nam Hà Nội (`nam_bac`) | `vi-VN-NamMinhNeural` (code ghi là giọng nam miền Bắc) | Đúng giới tính |
| Có đặt `TTS_VOICE` trong `.env` | Giọng đó cho **mọi** người dẫn, bất kể nam hay nữ | Có thể **sai giới tính**. Ghi vào hướng dẫn phần kỹ thuật |
| Nhân vật tiểu phẩm | Chỉ có 2 giọng gốc, chỉnh cao độ và tốc độ: con trai, bố, ông → giọng nam; con gái, mẹ, bà → giọng nữ | Đúng giới tính; tuổi tác chỉ là mô phỏng |

**Ràng buộc**:
- Chi phí $0 (P02). Không thêm dịch vụ trả phí.
- C-0001-1 (một video một bộ giọng), C-0001-2 (Studio chỉ đọc/ghi JSON, ảnh và chạy `demo.py`), C-0001-3 (API ghi cần `X-Studio: 1`), C-0001-4 (không đổi `app.html`).
- Gemini API không có lời gọi nào trả về "còn bao nhiêu lượt". Muốn kiểm tra trước thì phải tự đếm.
- Tester không được gọi Gemini thật. Không có test suite.

**Lưu ý về cách hiểu yêu cầu**: "hạn chế khi tạo video" cũng có thể chỉ việc **app Gemini hết lượt tạo clip** (`TODO.md` trên `main`: "Gemini Pro hết lượt 2026-11-13" khi làm clip mở đầu). Code không đo và không gọi thay được app Gemini, nên DR này không giải quyết việc đó. Người dùng đã xác nhận: DR này làm cho giọng đọc, clip trong app Gemini là yêu cầu riêng (Q-1).

---

## Quyết định

> **Giữ chuỗi giọng đã có trên `main` (Gemini chính → Gemini phụ → giọng miễn phí). Thêm sổ đếm lượt trên máy (`storage/gemini-tts-usage.json`) để `demo.py` kiểm tra trước: model nào không đủ lượt cho cả video thì bỏ qua, không gọi API. Phản hồi 429 của Gemini là nguồn sự thật cuối và được ghi lại vào sổ. Studio và Terminal nói rõ bằng tiếng Việt: còn bao nhiêu lượt, bao giờ có lại, video đang dùng giọng nào, và cho đọc lại toàn bộ bằng giọng Gemini trước khi duyệt.**

**Cổng V-0, trước khi merge PR (giải quyết góp ý chặn C-1 của MKTG)**: người dùng chọn Q-2 (a), tức nghe thử model phụ rồi mới chốt mặc định. **V-0 chưa diễn ra.**

- Dev **bắt đầu ngay** và **không đổi** `DEFAULT_TTS_FALLBACK_MODELS`: giữ giá trị trên `main`, `gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts`. Thứ tự này cũng là thứ tự người dùng chọn ở Q-3.
- Trước khi merge PR, người dùng nghe thử theo V-0. Model nào không đạt thì bị gỡ khỏi giá trị mặc định (trong `demo.py` và `.env.example`) trước khi merge.
- **Đây là điều chỉnh của người điều phối, người dùng chưa xác nhận riêng điểm này.** Bản 2 của DR đặt cổng V-0 "trước khi Dev bắt đầu". Lý do chuyển: V-0 chỉ quyết định một hằng số, không ảnh hưởng phần code còn lại.

Điểm điều chỉnh so với hướng đã trình người dùng và so với bản 1 của DR:

| Hướng trước | Điều chỉnh | Lý do |
|-------------|-----------|-------|
| DR tự thêm chuỗi model phụ | Dùng lại `gemini_tts_models` và `segments[i].tts_model` của `main`; không thêm tham số cho `generate_voiceovers` | Đã có trên `main`. Ít xung đột, `exercise.py` không phải sửa |
| Bản 1: lỗi không phải hạn mức thì đi thẳng sang edge | Giữ cách của `main`: lỗi gì cũng thử model kế tiếp | Một model preview có thể lỗi riêng. Mạng hỏng hoặc key sai thì lỗi ngay câu đầu, không tốn lượt |
| Bản 1: video bài tập không mượn model khác | Giữ cách của `main` (có mượn) | Người dùng chọn giữ (Q-4) |
| Sổ đếm cộng sau mỗi lời gọi | **Giữ chỗ** N lượt ngay khi kiểm tra, hoàn lại lượt chưa gửi | Hai tiến trình không cùng nghĩ mình còn đủ lượt |
| 429 → "hết lượt hôm nay" | Đọc `quotaId`: theo ngày → khoá đến giờ có lại lượt; theo phút → chờ, thử lại 1 lần; không rõ → khoá 60 phút | 429 do gọi nhanh không làm mất giọng Gemini cả ngày |
| Studio chỉ hiện lượt | Thêm nhãn giọng ở danh sách, lời nhắc trước khi duyệt, nút **Đọc lại toàn bộ bằng giọng Gemini** | Góp ý chặn C-2: video giọng miễn phí phải có đường quay lại Gemini |

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|:---:|-------|
| A | Sổ đếm trên máy + kiểm tra trước, trên nền chuỗi giọng của `main` | Chọn | $0. Không phí lượt khi biết trước là thiếu. Trả lời được "còn bao nhiêu lượt" |
| B | Chỉ phân loại 429 và nhớ trong lần chạy, không có sổ | - | Vẫn phí lượt ở video chạm trần. Không nhớ giữa hai lần chạy. Studio không có số liệu |
| C | Gọi thử Gemini một câu ngắn để dò | - | Mỗi lần dò tốn 1 trong 10 lượt, vẫn không biết còn đủ N lượt hay không |
| D | Giọng dự phòng bằng **Groq** | - | Tài liệu dự án chỉ ghi Groq cho model chữ (`TODO.md` §5, kiểm tra 2026-10-20). Không có tài liệu nào của dự án cho thấy Groq có giọng đọc tiếng Việt. **BA chưa xác minh trên trang Groq** |
| E | Giọng dự phòng bằng **ChatGPT / OpenAI TTS** | - | Trả phí: `FEASIBILITY.md` ghi nạp tối thiểu $5, khoảng $0.015/1K ký tự. ChatGPT bản web không gọi được từ code. Xem Q-5 |
| F | Gộp cả video vào 1 lời gọi Gemini rồi cắt theo khoảng lặng (4 lượt → 1) | Để sau | Lợi lớn nhất về lượt, nhưng đổi cách tạo giọng (chỉ dẫn từng câu, nhiều nhân vật, cắt sai thì lệch hình). Cần DR riêng |
| G | Hết lượt thì dừng, chờ có lại lượt | - | Trái yêu cầu "dùng một trình khác như là backup". Người dùng cũng chọn không dừng cho lô `--sheet` và video bài tập (Q-4, Q-6) |

Chốt cuối của chuỗi là **edge-tts**: miễn phí, đã có trong code. Hạn chế đã biết: phẳng hơn Gemini (người dùng nhận xét 2026-11-11), thỉnh thoảng lỗi "No audio was received" (code thử lại tối đa 6 lần).

---

## Thay đổi cấu trúc

### Dữ liệu

| Đối tượng | Trên `main` | Sau DR | Lý do |
|-----------|-------------|--------|-------|
| `storage/gemini-tts-usage.json` | Không có | Sổ đếm (định dạng bên dưới). Gitignored | Kiểm tra trước, nhớ 429 |
| `storage/gemini-tts-usage.lock` | Không có | File khoá (`fcntl.flock`). Gitignored | Hai tiến trình cùng ghi sổ |
| `script.json` → `segments[i].tts_model` | Có | Giữ nguyên | — |
| `script.json` → `segments[i].tts_fallback` | Không có | `null`: dùng model đầu chuỗi. `"quota"`: model đầu chuỗi thiếu lượt hoặc bị 429. `"error"`: model đầu chuỗi lỗi khác (mạng, key, 5xx). Ghi cùng chỗ với `tts_model` | Studio và Terminal nói đúng lý do (N-7). Đặt trên segment để video bài tập cũng có mà không sửa `exercise.py` |
| `.env` → `GEMINI_TTS_FALLBACK_MODELS` | Có, mặc định `gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts` | Dev giữ nguyên. Sau V-0 (trước khi merge) gỡ model không đạt | C-1, Q-2, Q-3 |
| `.env` → `GEMINI_TTS_DAILY_LIMIT` | Không có | Số lượt/ngày mỗi model, mặc định `10` | Google đổi hạn mức thì sửa một chỗ |
| `GEMINI_TTS_USAGE_FILE` (chỉ để test) | Không có | Đường dẫn sổ đếm thay thế | Tester không đụng sổ thật |
| `GEMINI_TTS_BASE_URL` (chỉ để test) | Không có | Thay cho `https://generativelanguage.googleapis.com/v1beta`. Chỉ nhận `http://127.0.0.1:<cổng>` hoặc `http://localhost:<cổng>` | Tester giả lập 200/429 bằng server local |

**Định dạng sổ đếm**:

```json
{
  "version": 1,
  "day": "2026-11-13",
  "models": {
    "gemini-3.8-flash-tts": {"used": 6, "blocked_until": null, "block_reason": null,
                             "last_call": "2026-11-13T02:12:03+00:00"},
    "gemini-2.5-flash-preview-tts": {"used": 4, "blocked_until": "2026-11-14T08:00:00+00:00",
                                     "block_reason": "daily_429", "last_call": "2026-11-13T03:40:11+00:00"}
  }
}
```

- `day`: ngày theo múi giờ `America/Los_Angeles` (`zoneinfo`, có trong Python 3.9 của `.venv`). Khác ngày hiện tại → coi như sổ trống.
- `used`: số lượt đã giữ chỗ hoặc đã gửi trong ngày.
- `blocked_until` (UTC): không dùng model trước thời điểm này. `block_reason`: `daily_429` (đến giờ có lại lượt) hoặc `unknown_429` (60 phút).
- Lượt còn lại = `0` nếu đang khoá, ngược lại `max(0, GEMINI_TTS_DAILY_LIMIT − used)`.
- File thiếu, rỗng, hỏng JSON, hoặc `version` lạ → coi như sổ trống, in 1 dòng cảnh báo, ghi đè khi cập nhật. **Xoá file luôn an toàn.**

### Quy tắc đếm

| Tình huống | Sổ đếm |
|-----------|--------|
| Kiểm tra trước đạt (model còn ≥ N lượt, không bị khoá) | `used += N` ngay trong lúc giữ khoá (giữ chỗ) |
| Lời gọi trả 200 | Giữ nguyên (đã tính) |
| Lỗi mạng, timeout, HTTP 5xx | Giữ lượt của lời gọi đó (không rõ Google có tính không; đếm dư an toàn hơn đếm thiếu). Hoàn lại các lượt **chưa gửi** |
| HTTP 4xx khác 429 (key sai, model không tồn tại) | Hoàn lại lượt đó và các lượt chưa gửi |
| 429 theo ngày | `blocked_until` = giờ có lại lượt kế tiếp, `block_reason=daily_429`. Hoàn lượt chưa gửi |
| 429 theo phút | Không đổi sổ. Chờ rồi gọi lại đúng lời gọi đó 1 lần |
| 429 không phân loại được, hoặc 429 theo phút lặp lại sau khi chờ | `blocked_until` = bây giờ + 60 phút, `block_reason=unknown_429` |
| Không ghi được sổ (hết quyền ghi, lỗi khoá) | In cảnh báo, **vẫn làm video** như `main` hiện nay |

**Phân loại 429** (`_classify_429`): đọc JSON phản hồi, lấy `error.details[]`:
- có `violations[].quotaId` chứa `PerDay` → `daily` (dạng đã quan sát: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`);
- không có `PerDay`, có `quotaId` chứa `PerMinute` → `minute`; thời gian chờ lấy từ `retryDelay` (vd `"34s"`), không có thì 30 giây, tối đa 65 giây;
- còn lại, hoặc phản hồi không phải JSON → `unknown`.

Tên `quotaId` theo phút **chưa xác minh**. Nếu thực tế khác, lỗi rơi vào `unknown`: khoá 60 phút chứ không khoá cả ngày.

### Luồng hệ thống

```
generate_voiceovers(segments, out_dir, persona, provider=None, model=None)     # chữ ký như main

provider != "gemini"  →  giọng miễn phí (không đụng sổ đếm)

provider == "gemini":
  N     = số câu
  chuỗi = gemini_tts_models(model)                    # như main: model đầu + GEMINI_TTS_FALLBACK_MODELS
  với từng m trong chuỗi:
     quota_reserve(m, N) không đạt → log "skip", sang m kế tiếp            (0 lời gọi API)
     đọc N câu bằng m, nghỉ 7 giây giữa hai câu
        xong                          → dùng m
        GeminiQuotaError daily/unknown → quota_block(m), hoàn lượt chưa gửi, sang m kế tiếp
        lỗi khác                      → hoàn lượt chưa gửi, sang m kế tiếp (như main)
     (đổi model là đọc lại TỪ ĐẦU cả video; file audio_i.mp3 bị ghi đè nên không trộn giọng)
  hết chuỗi → giọng miễn phí cho cả N câu
  ghi segments[i].tts_model (như main) và segments[i].tts_fallback
  in 1 dòng tiếng Việt cho người vận hành (bảng "Thông báo trên Terminal")
```

```
revoice_changed(script, out_dir)          # --render-only, đọc lại k câu đã sửa
  provider == "gemini":
     m = tts_model của video (như main; thư mục cũ → model chính)
     quota_reserve(m, k) không đạt → RevoiceError ngay, KHÔNG gọi API, không đổi audio → exit 3
     đọc k câu bằng m; lỗi bất kỳ → xoá file tạm, hoàn lượt chưa gửi, RevoiceError → exit 3
  KHÔNG có chuỗi dự phòng ở nhánh này (C-0012-1).

render_only(out_dir, revoice_all)
  "edge"    như main.
  "gemini"  trước khi đụng audio: không model nào trong chuỗi còn đủ N lượt
            → RevoiceError, exit 3, 0 lời gọi, audio giữ nguyên.
            Có → generate_voiceovers(provider="gemini") như video mới.
```

### Hàm thêm và sửa trong `demo.py`

Khối mới "Gemini TTS quota ledger", đặt **ngay trước `_gemini_tts`**, không xen vào `_trim_gemini_edges` hay `clean_gemini_audio`:

| Hàm / hằng | Việc |
|-----------|------|
| `QUOTA_TZ = "America/Los_Angeles"`, `UNKNOWN_BLOCK_MINUTES = 60`, `CALLS_PER_VIDEO = 4` | Hằng số. `CALLS_PER_VIDEO` chỉ dùng để ước lượng "đủ cho khoảng mấy video" |
| `_quota_file() -> Path` | `GEMINI_TTS_USAGE_FILE` hoặc `storage/gemini-tts-usage.json` |
| `_quota_day(now=None) -> str`, `_quota_reset_at(now=None) -> datetime` | Ngày Pacific hiện tại; thời điểm có lại lượt kế tiếp (tính bằng `zoneinfo`, không ghi cứng giờ) |
| `_quota_update(fn)` | Khoá `fcntl.flock` trên file `.lock` → đọc sổ (đổi ngày thì làm trống) → `fn(state)` → ghi file tạm rồi `os.replace` → mở khoá |
| `quota_limit() -> int` | `GEMINI_TTS_DAILY_LIMIT`, mặc định 10; không phải số nguyên dương → 10 kèm cảnh báo |
| `quota_left(model) -> int` | Lượt còn lại (0 nếu đang khoá) |
| `quota_reserve(model, n) -> bool` | Trong một lần giữ khoá: đủ thì `used += n`, trả `True`; thiếu hoặc đang khoá thì trả `False`, không đổi sổ |
| `quota_refund(model, n)` | `used = max(0, used − n)` |
| `quota_block(model, reason)` | Ghi `blocked_until`, `block_reason` |
| `quota_status() -> dict` | Dữ liệu cho `--tts-status` |
| `class GeminiQuotaError(RuntimeError)` | `kind` (`daily` / `minute` / `unknown`), `retry_after`. Thông báo vẫn bắt đầu bằng `Gemini TTS quota exceeded` |
| `_classify_429(body: str) -> tuple` | Hàm thuần, trả `(kind, retry_after_seconds)` |
| `voice_summary(segments, provider=None) -> dict` | `{"role": "main" / "backup" / "free" / None, "reason": None / "quota" / "error", "model": …}` suy từ `tts_model`, `tts_fallback`. Thư mục cũ không có khoá `tts_model` → `role` theo `provider`, không có thì `None` |
| `_voice_line_vi(…) -> str` | Câu tiếng Việt cho Terminal |

Sửa:

| Hàm | Thay đổi |
|-----|----------|
| `_gemini_tts` | URL lấy từ `GEMINI_TTS_BASE_URL` (từ chối địa chỉ không phải mặc định hoặc local). 429 → đọc phản hồi, `GeminiQuotaError`. `minute`: chờ `retry_after`, gọi lại 1 lần; vẫn 429 → `kind="unknown"`. Không tự ghi sổ |
| `generate_voiceovers` | Luồng ở trên. **Không đổi chữ ký, không đổi kiểu trả về `str`** |
| `gemini_tts_models`, `DEFAULT_TTS_FALLBACK_MODELS` | **Dev không đổi.** Chỉ gỡ model không đạt V-0, trước khi merge |
| `revoice_changed` | Kiểm tra trước; hoàn lượt khi lỗi |
| `render_only` | Kiểm tra trước cho `revoice_all="gemini"` |
| `approval_step` | In câu "Giọng đọc của video: …" ngay trước câu hỏi `y/n` (dùng chung cho video sản phẩm ở `APPROVAL_MODE=terminal` và video bài tập) |
| `run_one` | Thêm `voice` vào kết quả trả về |
| `run_sheet`, nhánh `--csv` | Trước video đầu tiên in câu ước lượng số video còn đủ lượt |
| `print_summary` | Thêm giọng của từng video |
| `main` | Cờ `--tts-status`: `load_env()`, in **một dòng JSON** rồi thoát 0. Không cần `GROQ_API_KEY`, không gọi mạng, không ghi sổ. **Dành cho Studio và người phụ trách kỹ thuật, không phải thao tác của người vận hành** |

Đầu ra `--tts-status`:

```json
{"provider": "gemini", "limit": 10, "calls_per_video": 4, "videos_left": 3,
 "resets_at": "2026-11-14T08:00:00+00:00",
 "models": [
   {"model": "gemini-3.8-flash-tts", "role": "main", "used": 6, "left": 4,
    "blocked_until": null, "block_reason": null},
   {"model": "gemini-2.5-flash-preview-tts", "role": "backup", "used": 0, "left": 10,
    "blocked_until": null, "block_reason": null}
 ]}
```

`videos_left` = tổng `left // calls_per_video` của các model trong chuỗi. `models` gồm model chính, các model phụ, rồi mọi model khác có trong sổ (`role="other"`).

### Thông báo trên Terminal

Quy ước dự án là log tiếng Anh. Các dòng `TTS plan`, `skip` bên dưới là **log**, giữ tiếng Anh cho Dev và Tester. Các câu tiếng Việt là **thông báo cho người vận hành**, cùng loại với `chưa có clip. Làm clip theo…` đã có trong `exercise.py` và `prompts.txt`; mỗi video in đúng một câu.

```
🎙️  TTS plan: 4 lines → gemini-3.8-flash-tts (4 of 10 left)
   ⏭️  gemini-3.8-flash-tts: 2 left, need 4 → skip (no API call)
   ⏭️  gemini-2.5-flash-preview-tts: blocked until 2026-11-14T08:00Z (daily_429) → skip
```

| Tình huống | Câu tiếng Việt (`{giờ}` = "khoảng 15:00 hôm nay" hoặc "khoảng 15:00 ngày mai", tính theo giờ và ngày trên máy) |
|-----------|-------------|
| Dùng Gemini chính | `Giọng đọc: Gemini (sau video này còn khoảng 2 lượt)` |
| Dùng Gemini phụ | `Giọng Gemini chính không đủ lượt (cần 4, còn 2). Video này dùng giọng Gemini phụ, nghe kỹ trước khi duyệt.` |
| Giọng miễn phí vì thiếu lượt | `Giọng Gemini không đủ lượt (cần 4, còn 2). Video này dùng giọng miễn phí. Có lại lượt lúc {giờ} (giờ Việt Nam).` |
| Giọng miễn phí vì lỗi khác | `Không kết nối được giọng Gemini (không phải do hết lượt). Video này dùng giọng miễn phí.` |
| Đầu lô `--sheet` / `--csv` | `Lượt Gemini còn đủ cho khoảng 2 video. Các video sau sẽ dùng giọng miễn phí.` (không in khi `TTS_PROVIDER=edge`) |
| Trước câu hỏi `y/n` | `Giọng đọc của video: Gemini` / `Gemini phụ` / `giọng miễn phí (lúc tạo, giọng Gemini không đủ lượt)` |
| Bảng tổng kết cuối lần chạy | Thêm cột giọng: `Gemini` / `Gemini phụ` / `giọng miễn phí` |

### `exercise.py`

**Không sửa.** Lời gọi `demo.generate_voiceovers(..., model=model)` và `demo.approval_step(...)` tự nhận kiểm tra trước, `tts_fallback`, và câu "Giọng đọc của video" trước `y/n`.

### `backend/app/api/studio.py`

| Thay đổi | Chi tiết |
|----------|----------|
| `GET /api/studio/voice-quota` (mới, chỉ đọc) | Chạy `demo.py --tts-status` bằng `subprocess.run` (cwd = repo root, timeout 15 giây), trả JSON đó kèm `"available": true`. Lỗi hoặc quá giờ → `{"available": false}`, không trả 500. Chạy được khi đang có job. Không tự đọc file sổ (C-0012-4) |
| `list_videos` | Mỗi video thêm `voice_role` (`main` / `backup` / `free` / `null`) |
| `video_detail` | Thêm `voice_role`, `voice_reason`, `voice_model`, `voice_calls` (số câu của video), **kể cả với thẻ "Chỉ xem"** (video bài tập) |
| `render` | `revoice_all` nhận `"edge"` hoặc `"gemini"`; giá trị khác vẫn 400 |
| Không đổi | `ERROR_KINDS`, `require_studio`, khoá job |

Cách suy `voice_role` trong `studio.py` chỉ là đọc 2 trường JSON của segment đầu (`tts_model`, `tts_fallback`) và `tts_provider`; không có quy tắc hạn mức nào ở đây.

### `backend/app/web/studio.html`

**Từ dùng thống nhất** (N-3, G-4):

| Từ trên giao diện | Nghĩa |
|-------------------|-------|
| giọng Gemini | Model chính |
| Gemini phụ | Model dự phòng |
| giọng miễn phí | edge-tts. Lần đầu xuất hiện trên mỗi màn hình ghi đủ: "giọng miễn phí (không giới hạn lượt, kém tự nhiên hơn Gemini)" |
| có lại lượt | Thay cho "làm mới" |
| `{giờ}` | Giờ máy kèm "hôm nay" hoặc "ngày mai" theo ngày trên máy, có chữ "khoảng": "khoảng 15:00 hôm nay". Không dùng "hôm nay" cho con số lượt, không dùng "để mai" |

Không hiện tên model thô (để trong mục gập "Xem chi tiết kỹ thuật"). Con số lượt luôn kèm "khoảng" ở nơi là ước lượng. Câu chữ dưới đây là bản MKTG đề xuất; MKTG soát lại lần cuối ở V-5.

| Chỗ | Điều kiện | Hiện gì |
|-----|-----------|---------|
| Thanh tiêu đề (luôn thấy, kể cả màn hình 390 px khi danh sách bị ẩn) | Bình thường | "Giọng Gemini: còn 4 lượt chính và 10 lượt phụ · đủ cho khoảng 3 video mới · có lại đủ lượt lúc {giờ}". Không có model phụ thì bỏ phần "phụ" |
| | Hết lượt theo ngày | "Giọng Gemini đã hết lượt. Video mới sẽ dùng giọng miễn phí cho đến {giờ}." |
| | Khoá tạm 60 phút | "Giọng Gemini đang tạm nghỉ đến 10:45. Trong lúc đó video mới sẽ dùng giọng miễn phí." |
| | `provider=edge` | "Đang dùng giọng miễn phí, không giới hạn lượt." |
| | `available=false` | "Chưa xem được số lượt Gemini còn lại. Bạn vẫn dựng lại được; nếu hết lượt, máy sẽ báo và giữ nguyên video cũ." |
| Danh sách bên trái | `voice_role=free` / `backup` | Nhãn nhỏ "Giọng miễn phí" / "Gemini phụ" cạnh nhãn Chờ duyệt |
| Đầu trang chi tiết | `main` | "Giọng của video: Gemini" |
| | `backup` | "Giọng của video: Gemini phụ. Nghe kỹ trước khi duyệt." |
| | `free`, lý do `quota` | "Video này đang dùng giọng miễn phí vì lúc tạo giọng Gemini không đủ lượt. Bạn có thể duyệt luôn, hoặc đợi có lại lượt ({giờ}) rồi bấm Đọc lại toàn bộ bằng giọng Gemini." |
| | `free`, lý do `error` | "Lúc tạo, không kết nối được giọng Gemini (không phải do hết lượt). Nếu lặp lại, báo người phụ trách kỹ thuật." kèm nút đọc lại bằng Gemini |
| | Thẻ "Chỉ xem" | Chỉ dòng "Giọng của video: …", không có nút |
| Nút **Đọc lại toàn bộ bằng giọng Gemini** | Video `free`, đủ lượt | "Đọc lại toàn bộ bằng giọng Gemini (dùng 4 lượt, còn 10)". Hộp xác nhận: "Cả video sẽ được đọc lại bằng giọng Gemini, dùng 4 lượt. Tiếp tục?" |
| | Thiếu lượt | Nút mờ, kèm "Chưa đủ lượt. Có lại lượt lúc {giờ}." |
| Thông báo khi sửa lời đọc (`updateBar`) | Đủ lượt | "Bạn sửa 2 lời đọc. Dựng lại sẽ dùng 2 lượt giọng Gemini của video này. Hiện còn 4, sau khi dựng còn 2." Nếu sau khi dựng còn dưới 4: thêm "Sau đó không đủ lượt Gemini cho một video mới trước {giờ}." |
| | Thiếu lượt (đỏ) | "Bạn sửa 2 lời đọc nhưng giọng Gemini của video này chỉ còn 1 lượt. Chọn một cách: sửa ít câu hơn; đợi đến {giờ}; hoặc đọc lại toàn bộ bằng giọng miễn phí." kèm nút |
| | Video giọng miễn phí | Như hiện nay ("không giới hạn lượt") |
| Nút **Đọc lại toàn bộ bằng giọng miễn phí** | Mọi chỗ có nút | Hộp xác nhận: "Cả video sẽ được đọc lại bằng giọng miễn phí, kém tự nhiên hơn giọng Gemini. Không tốn lượt Gemini. Tiếp tục?" Nút "Đổi sang giọng miễn phí" / "Để sau" |
| Lỗi `error_kind=revoice` | — | "Gemini báo đã hết lượt dù máy đếm còn. Video và giọng cũ vẫn giữ nguyên. Đợi đến {giờ} rồi dựng lại, hoặc đọc lại toàn bộ bằng giọng miễn phí." Bỏ con số cứng "10 lượt" và chữ "để mai" |
| Hộp xác nhận duyệt | `voice_role=free` | Thêm: "Video này dùng giọng miễn phí. Sau khi duyệt không đổi giọng được nữa." |
| | `backup` | Thêm: "Video này dùng giọng Gemini phụ. Bạn đã nghe kỹ chưa?" |

Hộp xác nhận dùng lại `<dialog id="confirm">` đang có (tiêu đề, nội dung, chữ trên 2 nút truyền vào), không dùng `confirm()` của trình duyệt cho các hộp mới. Bỏ hằng `GEMINI_PER_DAY`. Số liệu lấy lại khi mở trang, khi mở một video, khi một job kết thúc.

### Thao tác người dùng

| Thao tác | Trên `main` | Sau DR | Tốn gì |
|----------|-------------|--------|--------|
| Tạo video khi Gemini chính thiếu lượt | Gọi vài câu, lỗi, thử model kế | Biết trước, bỏ qua model thiếu lượt | 0 lượt phí |
| Sửa lời đọc khi thiếu lượt | Bấm dựng lại, chờ, lỗi | Trang báo đỏ ngay; bấm dựng lại cũng dừng ngay | 0 lượt |
| Xem còn bao nhiêu lượt | Không có | Thanh tiêu đề Studio | $0 |
| Biết video dùng giọng nào | Không có | Nhãn ở danh sách, dòng đầu trang chi tiết, hộp duyệt, Terminal | $0 |
| Đổi video giọng miễn phí về giọng Gemini | Chỉ bằng dòng lệnh | Nút trên Studio, trước khi duyệt | N lượt (bằng số câu), hiện trước khi bấm |

---

## Phạm vi

**Làm**: sổ đếm, kiểm tra trước, phân loại 429, `tts_fallback`, `--tts-status`, thông báo tiếng Việt trên Terminal, Studio (lượt còn lại, nhãn giọng, lời nhắc trước khi duyệt, nút đọc lại bằng Gemini, hộp xác nhận), tài liệu (gồm phần PR #9 chưa ghi).

**Không làm**:
- Không đo, không thay thế hạn mức của **app Gemini** (ảnh nhân vật, clip động tác).
- Không thêm dịch vụ trả phí. Không dùng Groq hay ChatGPT làm giọng đọc.
- Không đổi `app.html`, không đổi scope TikTok (C-0001-4).
- Không gộp nhiều câu vào một lời gọi Gemini (phương án F).
- Không thêm dự phòng cho Groq khi viết kịch bản.
- Không sửa `exercise.py`; không đổi cách video bài tập mượn model (Q-4).
- Không xoay vòng nhiều API key. Không tự chờ đến giờ có lại lượt rồi chạy lại.
- Không dừng lô `--sheet` khi hết lượt (Q-6).
- Không tự kiểm lời đọc bằng Whisper (việc đang mở trong `TODO.md`).

**Việc để sau, và góp ý không nhận**:

| Mục | Quyết định | Lý do |
|-----|-----------|-------|
| G-1: dòng gập "Video bài tập: còn N lượt" | Không nhận | Model của video bài tập chính là các model phụ, con số "lượt phụ" đã bao gồm. Thêm một con số nữa dễ lẫn (trái N-4) |
| Nút đổi video "Gemini phụ" về Gemini chính | Để sau | Chưa biết hai giọng khác nhau tới đâu (V-0). `--revoice-all gemini` trên dòng lệnh làm được |
| Dừng lô / dừng video bài tập khi thiếu lượt | Không làm | Người dùng chọn giữ cách hiện nay (Q-4, Q-6) |
| Giọng miễn phí theo vùng miền cho người dẫn nữ | Để sau | edge-tts chỉ có 2 giọng tiếng Việt; chỉ ghi vào danh sách nghe thử |

Mọi mục Chặn (C-1, C-2) và Nên sửa (N-1…N-13) của MKTG đều được nhận. Gợi ý G-2…G-6 được nhận.

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 0 | Đưa `origin/main` (`1ce153a`) vào nhánh; giữ file DR này | Người điều phối | — | Nhánh đã cập nhật | git |
| 0b | **V-0: nghe thử model phụ**, làm song song với Dev, phải xong **trước khi merge PR** | Người dùng | Bảng V-0 | Model nào đạt | `TODO.md` |
| 0c | Sau V-0: gỡ model không đạt khỏi `DEFAULT_TTS_FALLBACK_MODELS` và `.env.example` (không có model nào bị gỡ thì bỏ qua) | Dev | #0b | Code | `demo.py`, `.env.example` |
| 1 | Sổ đếm: `_quota_*`, `quota_*`, khoá file, ghi nguyên tử | Dev | DR | Code | `demo.py` |
| 2 | `_classify_429`, `GeminiQuotaError`, `GEMINI_TTS_BASE_URL`, thử lại 1 lần khi 429 theo phút | Dev | #1 | Code | `demo.py` |
| 3 | Kiểm tra trước trong `generate_voiceovers`; `tts_fallback`. Không đổi `DEFAULT_TTS_FALLBACK_MODELS` | Dev | #1, #2 | Code | `demo.py` |
| 4 | `revoice_changed` và `render_only` (`revoice_all="gemini"`): kiểm tra trước, hoàn lượt | Dev | #1, #2 | Code | `demo.py` |
| 5 | `--tts-status`, `voice_summary`, câu tiếng Việt, `approval_step`, câu đầu lô, `print_summary` | Dev + MKTG | #1, #3 | Code | `demo.py` |
| 6 | `GET /voice-quota`; `voice_*` trong danh sách và chi tiết (cả "Chỉ xem"); `render` nhận `"gemini"` | Dev | #5 | Code | `backend/app/api/studio.py` |
| 7 | Studio: thanh tiêu đề, nhãn, dòng giọng, nút đọc lại bằng Gemini, hộp xác nhận, thông báo sửa lời đọc | Dev + MKTG | #6 | HTML | `backend/app/web/studio.html` |
| 8 | `.gitignore` (2 file sổ), `.env.example` | Dev | — | Config | root |
| 9 | Server giả Gemini cho test, đặt ở thư mục tạm, **không commit** | Tester | #2 | Script tạm | scratchpad |
| 10 | Review: khoá file, hồi quy `exercise.py` và PR #9 (`clean_gemini_audio`), C-0001-1…3, C-0012-1…6, key không gửi ra địa chỉ lạ | Reviewer | #1–8 | Ghi chú | DR §Kết quả |
| 11 | Test theo bảng quyết định, không gọi Gemini thật | Tester | #1–9 | Kết quả D-x, V-x | DR §Kết quả |
| 12 | Soát chữ Studio, câu trên Terminal, hướng dẫn vận hành; ảnh chụp V-5 | MKTG | #5, #7 | Danh sách sửa | DR §Kết quả |
| 13 | Cập nhật tài liệu SSoT | BA | #1–12 | Docs | xem §SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Sổ đếm **thấp hơn** thực tế (máy khác dùng cùng key, file bị xoá, ngày đầu sau khi cài) | Kiểm tra trước đạt nhưng API trả 429 giữa video | 429 theo ngày được ghi vào sổ, video chuyển model kế tiếp và đọc lại từ đầu. Phí tối đa các lượt đã gọi của video đó, một lần. Studio dùng chữ "khoảng"; hướng dẫn có câu về ngày đầu (G-5) |
| R-2 | Rủi ro | Sổ đếm **cao hơn** thực tế (lời gọi lỗi vẫn bị đếm; Google tăng hạn mức) | Bỏ Gemini sớm hơn cần thiết trong ngày đó | Tự hết khi sang ngày. Xoá file sổ là an toàn. Hạn mức đổi thì sửa `GEMINI_TTS_DAILY_LIMIT` (người phụ trách kỹ thuật) |
| R-3 | Rủi ro | Giọng model phụ khác giọng chính tới mức người xem nhận ra; đọc cả phần chỉ dẫn (đã gặp với model `-lite`); đọc sai vùng miền; đọc bịa thêm câu | Video dùng model phụ nghe khác hoặc hỏng | **Chưa xác minh được bằng tài liệu.** Cổng V-0 trước khi merge PR; model không đạt thì bị gỡ khỏi mặc định. Cho tới lúc đó nhánh này giữ mặc định như `main`. Studio ghi "Gemini phụ. Nghe kỹ trước khi duyệt" và nhắc ở hộp duyệt |
| R-4 | Rủi ro (**người dùng đã chọn chấp nhận ở Q-3**) | Model phụ đứng đầu là `gemini-3.1-flash-tts-preview`, model của video động tác **hằng ngày** (5–6 lượt). Video sản phẩm thứ 3 trong ngày mượn 4 lượt của nó: nếu làm trước video bài tập thì model 3.1 còn 6 (vừa đủ cho một video động tác); thêm một video sản phẩm nữa thì còn 2, video bài tập phải sang model 2.5 hoặc giọng miễn phí. Ngày làm video mở đầu hoặc tổng kết (6 hoặc 10 lượt model 2.5) cũng có thể thiếu nếu video sản phẩm đã mượn tới model 2.5 | Video bài tập hôm đó dùng model Gemini khác hoặc giọng miễn phí; chuỗi bài tập đổi giọng một ngày | Giảm nhẹ, không đổi thứ tự: (1) hướng dẫn vận hành: **làm video bài tập trước video sản phẩm trong ngày**, nhất là ngày làm video mở đầu hoặc tổng kết (nhận biết: chuỗi mới bắt đầu, hoặc hôm qua vừa làm động tác cuối; Terminal in tên video ở dòng `🧘`); (2) thanh tiêu đề Studio và câu đầu lô cho biết còn đủ lượt cho khoảng mấy video; (3) giọng thực tế hiện trước câu hỏi `y/n`, gõ `n` nếu không ưng; (4) kiểm tra trước nên không phí lượt khi thiếu. Không yêu cầu người vận hành sửa `.env`. Muốn đổi thứ tự sau này: `GEMINI_TTS_FALLBACK_MODELS` (người phụ trách kỹ thuật) |
| R-5 | Rủi ro | Hai tiến trình cùng ghi sổ | Đếm sai, file hỏng | `fcntl.flock` + giữ chỗ N lượt trong một lần khoá + ghi qua file tạm rồi `os.replace` |
| R-6 | Rủi ro | `quotaId` của 429 theo phút khác dự đoán | Bị xếp vào `unknown` | Khoá 60 phút thay vì cả ngày; Studio có câu riêng "đang tạm nghỉ đến HH:MM" |
| R-7 | Rủi ro | `GEMINI_TTS_BASE_URL` trỏ ra ngoài làm lộ API key | Lộ key | Chỉ nhận địa chỉ Google mặc định hoặc `127.0.0.1` / `localhost` (C-0012-5) |
| R-8 | Rủi ro | **Nhánh cũ hơn `main`**: nhánh tạo từ `22caf14`; `origin/main` là `1ce153a` (PR #9: `demo.py` 125 dòng, `exercise.py` 165 dòng, `.env.example`, `TODO.md`, giáo trình). Lúc BA kiểm lại, thư mục làm việc ở repo gốc **sạch**: các thay đổi này đã commit và merge, không còn "chưa commit" | Dev code trên bản cũ sẽ xung đột ở đúng vùng TTS của `demo.py` | Việc #0: cập nhật nhánh trước khi Dev bắt đầu. DR không sửa `exercise.py`, không đụng `_trim_gemini_edges`, `clean_gemini_audio`. Khối sổ đếm là khối riêng |
| R-9 | Rủi ro | Thư mục video cũ không có `tts_model` / `tts_fallback` | Không biết vai trò giọng | `voice_role` theo `tts_provider`; không có gì thì không hiện dòng giọng. Đọc lại bằng model chính như `main` |
| R-10 | Rủi ro | Người vận hành bấm **Đọc lại toàn bộ bằng giọng Gemini** rồi Gemini báo hết giữa chừng (sổ lệch) | Video trở lại giọng miễn phí, mất vài lượt | Cả video vẫn một giọng. Thông báo lỗi nêu rõ; sổ đã được sửa nên nút mờ đi |
| R-11 | Rủi ro | Đặt `TTS_VOICE` làm người dẫn giọng miễn phí sai giới tính so với persona | Video giọng miễn phí lệch giọng | Ghi vào phần kỹ thuật của hướng dẫn; người vận hành luôn nghe trước khi duyệt |
| A-1 | Giả định | Mỗi model TTS có hạn mức ngày riêng, 10 lượt | Sổ đếm theo từng model | Đúng với quotaId đã quan sát cho model sản phẩm; 2 model còn lại chưa xác minh. Sai thì 429 sửa lại sổ |
| A-2 | Giả định | Có lại lượt lúc nửa đêm giờ Pacific | Giờ hiện trên Studio | Sai thì chỉ lệch giờ hiển thị và giờ mở khoá; lời gọi đầu tiên sau đó nhận 429 và khoá lại. Giao diện ghi "khoảng" |
| A-3 | Giả định | Máy chạy macOS (có `fcntl`) | Khoá file | Không có `fcntl` → áp dụng dòng "không ghi được sổ" |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0012-1 | Một video chỉ dùng **một model** giọng. Đọc lại một phần (`revoice_changed`) phải dùng đúng bộ giọng và model của video; thiếu lượt hoặc lỗi thì không đổi audio nào và **không** tự chuyển model hay bộ giọng. Chuyển model chỉ xảy ra khi đọc lại **toàn bộ** video | Mở rộng C-0001-1 sang mức model | `demo.py` | — |
| C-0012-2 | Sổ đếm chỉ là ước lượng. Phản hồi của Gemini API là nguồn sự thật: 429 luôn được ghi lại vào sổ; sổ hỏng, mất, hoặc không ghi được thì **không được** làm hỏng việc tạo video | Sổ có thể lệch | `demo.py` | — |
| C-0012-3 | Kiểm tra trước, `--tts-status` và Studio **không** gọi Gemini để dò hạn mức | Mỗi lời gọi dò tốn 1 trong 10 lượt | `demo.py`, `studio.py` | Khi Gemini có API xem hạn mức miễn phí |
| C-0012-4 | Mọi lần đọc và ghi sổ đếm đi qua `_quota_update`. Chỉ `demo.py` đọc/ghi sổ; Studio lấy số liệu qua `demo.py --tts-status` | Hai tiến trình chạy cùng lúc; một nguồn logic (C-0001-2) | `demo.py`, `studio.py` | Khi chuyển sang backend đầy đủ |
| C-0012-5 | `GEMINI_TTS_BASE_URL` chỉ nhận địa chỉ Google mặc định hoặc `127.0.0.1` / `localhost`. Chuỗi giọng chỉ gồm dịch vụ $0; thêm dịch vụ trả phí cần DR mới | Không lộ API key; giữ chi phí $0 | `demo.py` | — |
| C-0012-6 | Video không dùng giọng Gemini chính phải được báo cho người vận hành **trước khi duyệt**: trên Terminal lúc tạo và trước `y/n`, trên Studio ở danh sách, trang chi tiết và hộp xác nhận duyệt. Một model chỉ được nằm trong mặc định của `GEMINI_TTS_FALLBACK_MODELS` **ở bản merge vào `main`** sau khi người dùng nghe thử và đồng ý (V-0) | Duyệt xong thư mục bị xoá, không đổi giọng được nữa; giọng chưa nghe không được tự lên sóng | `demo.py`, `studio.py`, `studio.html` | — |

Các ràng buộc C-0001-1…4 giữ nguyên hiệu lực.

supersedes: —

---

## Chi phí

| Hạng mục | Lượt Gemini | USD |
|----------|-------------|-----|
| Kiểm tra trước, `--tts-status`, hiển thị Studio | 0 (chỉ đọc file trên máy) | $0 |
| Dev, Reviewer, Tester, MKTG | 0 (server giả + edge-tts) | $0 |
| Vận hành hằng ngày | Không tăng; giảm số lượt phí khi chạm trần | $0 |
| **V-0, người dùng nghe thử (trước khi merge)** | Khoảng **9 lượt cho mỗi model phụ** (1 video tiểu phẩm khoảng 5 câu + 1 video đơn giản 4 câu), tức khoảng 18 lượt nếu thử cả hai. Vừa trong 10 lượt/ngày của từng model, nhưng **hôm đó video bài tập có thể thiếu lượt Gemini**. Dùng sản phẩm thật thì video không bỏ đi | $0 |
| Nút **Đọc lại toàn bộ bằng giọng Gemini** | Bằng số câu của video, mỗi lần bấm; hiện trước khi bấm | $0 |
| edge-tts, Groq, Drive | Không đổi | $0 |

Không có khoản nào trả phí.

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Xong |
|----------|-------------------|:----:|
| `docs/specs/architecture/capabilities/video-render.md` | § Studio: chuỗi giọng (kể cả phần PR #9), `tts_model`, `tts_fallback`, sổ đếm, quy tắc đếm, C-0012-1…6, endpoint `voice-quota`, `render` nhận `gemini`, biến test | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Xem danh sách chi tiết bên dưới | [ ] |
| `.claude/CLAUDE.md` (`agent/CLAUDE.md`) | Luồng `demo.py` (bước giọng đọc), lệnh `--tts-status`, bảng TTS, mục Studio | [ ] |
| `.env.example` | `GEMINI_TTS_FALLBACK_MODELS`: giữ như `main`, gỡ model không đạt V-0 trước khi merge; `GEMINI_TTS_DAILY_LIMIT`; ghi rõ hai biến này thuộc người phụ trách kỹ thuật | [ ] |
| `TODO.md` | Việc đã xong, kết quả V-0, quyết định ở §5 | [ ] |

**Hướng dẫn vận hành, từng chỗ phải sửa** (N-13). Phần hằng ngày không có tên model và không yêu cầu sửa `.env`.

| Chỗ | Nội dung |
|-----|----------|
| Bước 3. Tạo video | Ý nghĩa câu tiếng Việt về giọng trên Terminal; câu đầu lô; video quan trọng thì làm trước khi hết lượt |
| Bước 5. Duyệt video | Kiểm dòng "Giọng của video" và nhãn ở danh sách; cách làm lại bằng giọng Gemini (nút trên Studio); video "Gemini phụ" nghe kỹ có đọc thừa chữ không; sau khi duyệt không đổi giọng được |
| Đoạn "Lượt giọng Gemini" | Bỏ "10 lượt cho mọi video"; sửa lời đọc và video mới **dùng chung lượt**; đọc thanh tiêu đề Studio thế nào; thay mọi "để mai" bằng "đợi đến khoảng 15:00" kèm giải thích một ngày của Gemini tính từ khoảng 15:00 đến 15:00 hôm sau; giải thích ba tên giọng |
| Mục 4b. Video bài tập | Video bài tập có thể dùng Gemini phụ hoặc giọng miễn phí; nhận biết bằng câu trước `y/n` và dòng giọng ở thẻ "Chỉ xem"; **làm video bài tập trước video sản phẩm trong ngày**, nhất là ngày làm video mở đầu hoặc tổng kết, kèm cách nhận biết ngày đó (R-4) |
| Mục 5. Lịch gợi ý | 1–2 video sản phẩm/ngày = 4–8 lượt, cộng lượt sửa câu; giờ có lại lượt; từ video sản phẩm thứ 3 là mượn lượt của video bài tập (R-4) |
| Mục 6. Gặp lỗi | Sửa dòng Gemini hiện có. Thêm: thông báo đỏ thiếu lượt; "Giọng Gemini đang tạm nghỉ"; "Số lượt trên Studio khác thực tế" (cứ dựng, máy tự sửa số); ngày đầu sau khi cài có thể báo đủ 10 lượt dù đã dùng (G-5) |
| Phần cho người phụ trách kỹ thuật | Xoá file sổ đếm là an toàn; `GEMINI_TTS_FALLBACK_MODELS`, `GEMINI_TTS_DAILY_LIMIT`; `TTS_VOICE` có thể làm sai giới tính người dẫn; `--tts-status`; `--revoice-all gemini` |

## File code thay đổi (việc của Dev theo file)

- [ ] `demo.py`
  - Khối sổ đếm mới trước `_gemini_tts`: hằng số, `_quota_file`, `_quota_day`, `_quota_reset_at`, `_quota_update`, `quota_limit`, `quota_left`, `quota_reserve`, `quota_refund`, `quota_block`, `quota_status`, `GeminiQuotaError`, `_classify_429`
  - `_gemini_tts`: `GEMINI_TTS_BASE_URL` có kiểm địa chỉ; phân loại 429; thử lại 1 lần khi theo phút
  - `generate_voiceovers`: kiểm tra trước từng model, khoá model khi 429, hoàn lượt, `tts_fallback`, câu tiếng Việt. Chữ ký và kiểu trả về giữ nguyên
  - `DEFAULT_TTS_FALLBACK_MODELS`: **không đổi** (giữ như `main`); chỉ gỡ model không đạt V-0, trước khi merge
  - `revoice_changed`: kiểm tra trước, hoàn lượt
  - `render_only`: kiểm tra trước cho `revoice_all="gemini"`
  - `voice_summary`, `_voice_line_vi`; `approval_step` in giọng trước `y/n`; `run_one` trả `voice`; câu đầu lô trong `run_sheet` và nhánh `--csv`; `print_summary` thêm giọng
  - `main`: `--tts-status`
- [ ] `backend/app/api/studio.py`: `GET /voice-quota`; `voice_role` trong `list_videos`; `voice_role`, `voice_reason`, `voice_model`, `voice_calls` trong `video_detail` (cả "Chỉ xem"); `render` nhận `revoice_all="gemini"`
- [ ] `backend/app/web/studio.html`: bỏ `GEMINI_PER_DAY`; thanh tiêu đề lượt; nhãn giọng ở danh sách; dòng giọng ở chi tiết (cả "Chỉ xem"); nút đọc lại bằng Gemini; hộp xác nhận dùng chung cho 3 việc (duyệt, đổi sang giọng miễn phí, đọc lại bằng Gemini); thông báo sửa lời đọc; lỗi revoice; hàm đổi `resets_at` / `blocked_until` thành "khoảng HH:MM hôm nay/ngày mai"
- [ ] `.gitignore`: `storage/gemini-tts-usage.json`, `storage/gemini-tts-usage.lock`
- [ ] `.env.example`: thêm `GEMINI_TTS_DAILY_LIMIT`; dòng `GEMINI_TTS_FALLBACK_MODELS` giữ như `main` (gỡ model không đạt V-0 trước khi merge)
- Không đổi: `exercise.py`, `app.html`, `api/creator.py`, `creator_main.py`, `backend/app/core/config.py`, `drive_upload.py`, `product_sources.py`

---

## Tiêu chí hoàn thành (DoD)

### Cách giả lập cho Tester (không gọi Gemini thật)

- `GEMINI_API_KEY=test`, `GEMINI_TTS_USAGE_FILE=<thư mục tạm>/usage.json`, `GEMINI_TTS_BASE_URL=http://127.0.0.1:<cổng>`, `GEMINI_TTS_FALLBACK_MODELS=gemini-2.5-flash-preview-tts` (đặt rõ để kết quả không phụ thuộc mặc định).
- **Server giả** (script tạm): nhận `POST /models/<model>:generateContent`, ghi lại model và số lần gọi; trả 200 với `inlineData` là 0,5 giây PCM 16-bit 24 kHz base64, hoặc 429/500 theo kịch bản ("lần gọi thứ k của model X trả …").
- **Sổ dựng sẵn**: Tester tự ghi `usage.json` theo định dạng ở trên.
- Thân 429 mẫu. Theo ngày: `{"error":{"code":429,"details":[{"@type":"type.googleapis.com/google.rpc.QuotaFailure","violations":[{"quotaId":"GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}`. Theo phút: đổi `quotaId` thành `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, thêm `{"@type":"type.googleapis.com/google.rpc.RetryInfo","retryDelay":"2s"}`. Không rõ: `{"error":{"code":429}}`.
- Gọi hàm bằng `python -c "import demo; …"` trên **bản sao** thư mục video, hoặc chạy `demo.py --render-only`. Không Drive, không Sheet, không TikTok. Nhánh giọng miễn phí dùng edge-tts thật.
- Trong bảng: "chính" = `gemini-3.8-flash-tts`, "phụ" = `gemini-2.5-flash-preview-tts`, hạn mức 10, video 4 câu, trừ khi ghi khác.

### Bảng quyết định: code

**Bình thường**

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-1 | Sổ trống. `generate_voiceovers` 4 câu, `provider=gemini` | Server giả nhận đúng 4 lời gọi, đều tới chính. Trả `"gemini"`. Mọi segment: `tts_model` = chính, `tts_fallback=None`. Sổ: chính `used=4` | Server giả + sổ |
| D-2 | Sổ: chính `used=8` | **0** lời gọi tới chính, 4 tới phụ. `tts_model` = phụ, `tts_fallback="quota"`. Sổ: chính 8, phụ 4. Log có dòng `skip` | Server giả + sổ + log |
| D-3 | Sổ: chính `used=8`, phụ `used=9` | **0** lời gọi tới server giả. 4 file audio do edge-tts tạo. Trả `"edge"`, `tts_model=None`, `tts_fallback="quota"`. Sổ không đổi | Server giả + sổ |
| D-4 | `voice_summary` trên segment của D-1, D-2, D-3 | `role` lần lượt `main`, `backup`, `free`; `reason` lần lượt `None`, `quota`, `quota` | Gọi hàm |
| D-5 | `demo.py --tts-status` sau D-2 | Thoát 0, stdout đúng **một** dòng JSON: chính `left=2`, phụ `left=6`, `videos_left=1`, có `resets_at`, `limit=10`. 0 lời gọi tới server giả. Sổ không đổi | Chạy lệnh, `json.loads`, so nội dung sổ |
| D-6 | `TTS_PROVIDER=edge`, không có sổ | Dùng edge-tts. Không tạo file sổ. `--tts-status` trả `provider="edge"` | Kiểm file không tồn tại |

**Lỗi**

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-7 | Sổ trống. Lời gọi thứ 3 của chính trả 429 **theo ngày** | Chính bị khoá: `block_reason="daily_429"`, `blocked_until` = nửa đêm Pacific kế tiếp. Cả video đọc lại từ đầu bằng phụ (4 lời gọi), `tts_fallback="quota"`. Chạy lần nữa → 0 lời gọi tới chính | Server giả + sổ |
| D-8 | Sổ trống. Lời gọi thứ 2 của chính trả 429 **theo phút** (`retryDelay` 2s), gọi lại thì 200 | Chờ khoảng 2 giây, gọi lại đúng 1 lần, video xong bằng chính (5 lời gọi tới server, 4 file audio). Chính không bị khoá, `used=4` | Server giả + sổ + thời gian |
| D-9 | Như D-8 nhưng lần gọi lại vẫn 429 theo phút | Chính bị khoá `unknown_429`, `blocked_until` khoảng bây giờ + 60 phút. Video chuyển sang phụ | Sổ |
| D-10 | `_classify_429` với 4 thân: theo ngày, theo phút, `{"error":{"code":429}}`, chuỗi không phải JSON | `daily` / `minute` (2 giây) / `unknown` / `unknown`. Không ném lỗi | Gọi hàm |
| D-11 | Lời gọi thứ 2 của chính trả 500 | Chuyển sang phụ (4 lời gọi), `tts_fallback="error"`. Sổ: chính `used=2` (2 lượt chưa gửi được hoàn), không bị khoá | Server giả + sổ |
| D-12 | Server giả tắt hẳn | Mỗi model thử đúng 1 kết nối rồi bỏ, video dùng giọng miễn phí, `tts_fallback="error"`. Không model nào bị khoá. Câu tiếng Việt là câu "Không kết nối được giọng Gemini" | Sổ + stdout |
| D-13 | File sổ là `{{{`; hoặc `version: 99` | 1 dòng cảnh báo, coi như sổ trống, video vẫn xong, sổ được ghi lại hợp lệ | Chạy D-1 với sổ hỏng |
| D-14 | Thư mục chứa sổ không ghi được (`chmod 555`) | Cảnh báo, video vẫn xong (4 lời gọi), không traceback | Chạy với thư mục chỉ đọc |
| D-15 | `GEMINI_TTS_BASE_URL=http://example.com/v1beta` | Báo lỗi rõ ràng, **không** có kết nối ra ngoài, video dùng giọng miễn phí | Log; server giả nhận 0 |
| D-16 | `--render-only`, video Gemini với `tts_model` = chính, sửa 2 câu. Sổ: chính `used=9` | Exit 3. **0** lời gọi. Mọi `audio_i.mp3` giữ mtime, `video.mp4` không đổi, không còn `_new_audio_*`. Log nêu cần 2, còn 1. Sổ không đổi. **Không** dùng phụ dù phụ còn 10 | Chạy thật + sổ |
| D-17 | Như D-16 nhưng sổ trống; lời gọi thứ 2 trả 429 theo ngày | Exit 3. Không audio nào đổi. Chính bị khoá `daily_429`. 0 lời gọi tới phụ | Chạy thật + sổ |
| D-18 | `--render-only`, video `tts_model` = **phụ**, sửa 1 câu, sổ trống | Đúng 1 lời gọi tới phụ, 0 tới chính. Chỉ `audio_i` của câu đó đổi | Server giả |
| D-19 | Sau D-16: `--render-only --revoice-all edge` | Đọc lại toàn bộ bằng edge, `tts_provider="edge"`, `tts_model=None`, exit 0 | Chạy thật |
| D-20 | Video giọng miễn phí, sổ trống: `--render-only --revoice-all gemini` | 4 lời gọi tới chính, `tts_provider="gemini"`, `tts_model` = chính, `tts_fallback=None`, exit 0 | Server giả |
| D-21 | Như D-20 nhưng sổ: chính `used=8`, phụ `used=9` | Exit 3. **0** lời gọi. Audio và video giữ nguyên, `tts_provider` vẫn `edge` | Chạy thật + sổ |

**Biên**

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-22 | Sổ: chính `used=6` (còn đúng 4), video 4 câu | Dùng chính. Sau đó `used=10`, `left=0` | Sổ |
| D-23 | Sổ: chính `used=7` (còn 3), video 4 câu | Bỏ qua chính, 0 lời gọi tới chính | Server giả |
| D-24 | Sổ có `day` là hôm qua (giờ Pacific), chính `used=10`, `blocked_until` đã qua | Coi như sổ trống: dùng chính. Sổ được ghi với `day` hôm nay | Sổ dựng sẵn |
| D-25 | Sổ hôm nay, chính `unknown_429`, `blocked_until` = 1 phút trước, `used=2` | Hết khoá: chính còn 8, được dùng | Sổ dựng sẵn |
| D-26 | `GEMINI_TTS_FALLBACK_MODELS=` (rỗng), sổ: chính `used=8` | Giọng miễn phí, 0 lời gọi. `--tts-status` không có `role="backup"` | Server giả |
| D-27 | `GEMINI_TTS_DAILY_LIMIT=6` với sổ `used=4`, video 4 câu; rồi `GEMINI_TTS_DAILY_LIMIT=abc` | Với 6: bỏ qua chính. Với `abc`: dùng 10, in cảnh báo | Gọi hàm |
| D-28 | **Hai tiến trình cùng lúc**: sổ chính `used=4`; mỗi tiến trình `quota_reserve(chính, 4)` | Đúng **một** tiến trình nhận `True`. Sổ cuối `used=8`, JSON hợp lệ. Lặp 20 lần | Script tạm, 2 `subprocess` |
| D-29 | 20 tiến trình song song, mỗi tiến trình `quota_reserve(chính, 1)`, sổ trống | Đúng 10 `True`, 10 `False`, `used=10` | Script tạm |
| D-30 | Video 11 câu, hạn mức 10 | Mọi model Gemini bị bỏ qua, giọng miễn phí, 0 lời gọi | Server giả |
| D-31 | `_quota_reset_at` với `now` = 2026-11-13 03:00 UTC và 2026-07-01 03:00 UTC | `2026-11-13T08:00Z` (giờ chuẩn) và `2026-07-01T07:00Z` (giờ mùa hè): không ghi cứng giờ | Gọi hàm |

**Thông báo cho người vận hành**

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-32 | Stdout của D-1, D-2, D-3, D-12 | Mỗi lần có đúng **một** câu tiếng Việt, đúng mẫu ở bảng "Thông báo trên Terminal" (Gemini / Gemini phụ / miễn phí do thiếu lượt, có giờ kèm "hôm nay" hoặc "ngày mai" / miễn phí do không kết nối). Không có tên model trong câu tiếng Việt. Các dòng `TTS plan`, `skip` vẫn tiếng Anh | Đọc stdout |
| D-33 | `approval_step` với script của D-2 và D-3 (stdin đưa `n`) | Câu "Giọng đọc của video: Gemini phụ" / "giọng miễn phí (…)" in **trước** câu hỏi `y/n`. Script không có khoá `tts_model` (thư mục cũ) → không in câu này, không lỗi | Chạy với `echo n \|` (đặt `sys.platform` giả hoặc chấp nhận lệnh `open`) |
| D-34 | Hàm in câu đầu lô với sổ: chính `used=2`, phụ `used=10` | "Lượt Gemini còn đủ cho khoảng 2 video. Các video sau sẽ dùng giọng miễn phí." `TTS_PROVIDER=edge` → không in | Gọi hàm |
| D-35 | `print_summary` với 3 kết quả có `voice` = main / backup / free | Mỗi dòng có tên giọng tiếng Việt. Kết quả không có `voice` (lỗi, `needs_clips`) → không lỗi | Gọi hàm |

**Hồi quy**

| # | Điều kiện | Kết quả mong đợi | Cách kiểm |
|---|-----------|------------------|-----------|
| D-36 | `exercise.py` **không có trong diff**. Gọi `demo.generate_voiceovers(segs, dir, persona, model="gemini-3.1-flash-tts-preview")`, 6 câu, sổ trống | Trả kiểu `str`. 6 lời gọi, đều tới model 3.1. `tts_fallback=None`. Với sổ: model đó `used=8` → 0 lời gọi tới nó, chuyển sang model kế trong chuỗi (như `main`), `tts_fallback="quota"` | `git diff --stat` + server giả |
| D-37 | Không có `GEMINI_API_KEY` | Như `main`: edge-tts, không tạo sổ, không lỗi | Gọi `generate_voiceovers` (hoặc chạy `--product … --style simple --skip-approval --keep-local` nếu có key Groq) |
| D-38 | Thư mục video cũ: segment không có `tts_model`, `tts_provider=gemini`, sửa 1 câu, sổ trống | Đọc lại bằng model chính (1 lời gọi) | Server giả |
| D-39 | `--rerender`, `--approve`, `--render-only` không sửa lời đọc | 0 lời gọi, sổ không đổi. `clean_gemini_audio` vẫn chạy như `main`. Hành vi DR-0001 (D-3, D-9, D-12) giữ nguyên | Chạy thật trên bản sao |
| D-40 | `GET /api/studio/voice-quota` | 200, JSON như `--tts-status` kèm `available=true`, không cần `X-Studio`. Khi `demo.py --tts-status` lỗi (đổi tạm `DEMO` sang file không tồn tại) → 200 `{"available": false}`. Gọi được khi đang có job | TestClient |
| D-41 | `GET /videos` và `GET /videos/{folder}` trên 4 bản sao: Gemini chính, Gemini phụ, giọng miễn phí, bài tập ("Chỉ xem") | `voice_role` đúng ở cả danh sách và chi tiết; chi tiết có `voice_reason`, `voice_calls`. Thẻ "Chỉ xem" có `voice_role`, các API ghi vẫn 409. Thư mục cũ không có trường nào → `voice_role=null`, không lỗi | TestClient |
| D-42 | `POST …/render` với `revoice_all` = `"edge"`, `"gemini"`, `"openai"`; thiếu `X-Studio`; đang có job | 200 / 200 (chạy `--revoice-all gemini --render-only`) / 400 / 403 / 409 | TestClient |
| D-43 | `app.html`, `api/creator.py`, `creator_main.py`, `exercise.py` | Không có trong diff. `/api/creator/videos` vẫn trả danh sách | `git diff --stat` + TestClient |
| D-44 | Đọc diff | Không có lời gọi mạng trong `quota_*`, `--tts-status`, `voice-quota` (C-0012-3). Không chỗ nào đọc/ghi file sổ ngoài `_quota_update` (C-0012-4). `studio.html` không còn `GEMINI_PER_DAY`, "để mai", "10 lượt" ghi cứng, và không có `confirm(` mới | Reviewer + `grep` |

### Bảng quyết định: tài liệu

| # | Đối tượng | Thay đổi | Trạng thái sau | Cách kiểm |
|---|-----------|----------|----------------|-----------|
| DD-1 | `video-render.md` | Sửa | Có chuỗi giọng, sổ đếm, `tts_fallback`, endpoint, C-0012-1…6; tên hàm và biến khớp code | `grep` trong `demo.py`, `studio.py` |
| DD-2 | Hướng dẫn vận hành | Sửa | Đủ 7 chỗ trong bảng "từng chỗ phải sửa". Nhãn trích đúng nguyên văn trên Studio. **Phần hằng ngày không có tên model, không yêu cầu sửa `.env`.** Không còn "10 lượt cho mọi video", không còn "để mai" | Đối chiếu `studio.html`; `grep -n "gemini-\|\.env\|để mai"` trong các mục 3–6 |
| DD-3 | `.claude/CLAUDE.md`, `.env.example`, `TODO.md` | Đồng bộ | `--tts-status`, tên biến, giá trị mặc định khớp code; `TODO.md` có kết quả V-0 | Đối chiếu chéo |

### Kiểm tra E2E

| # | Hạng mục | Cách làm | Mong đợi | Kết quả | Ngày |
|---|----------|----------|----------|---------|------|
| V-0 | **Người dùng nghe thử model phụ, trước khi merge PR** (chưa làm; Dev không chờ). Tốn khoảng 9 lượt Gemini thật cho mỗi model phụ; không thuộc phần Tester | Chạy trên `main` hiện tại, mỗi model phụ 2 video, đặt tạm trên dòng lệnh `GEMINI_TTS_MODEL=<model phụ> GEMINI_TTS_FALLBACK_MODELS=`: (a) 1 video **tiểu phẩm** nhiều nhân vật, người dẫn nữ Sài Gòn; (b) 1 video **đơn giản**, người dẫn nam Hà Nội (sản phẩm điện tử, hoặc thêm `GEMINI_TTS_PERSONA=nam_bac`). Nghe và so với một video dùng model chính | Với từng model, trả lời 5 câu: (1) có đọc phần chỉ dẫn thành tiếng không; (2) đúng vùng miền và giới tính không; (3) có đọc sai số, sai chữ, hoặc **đọc thêm câu không có trong lời** không; (4) các nhân vật tiểu phẩm có phân biệt được không; (5) có khác giọng chính tới mức người xem nhận ra không. Model đạt cả 5 mới được ở lại trong mặc định; model không đạt bị gỡ trước khi merge. Nghe thêm 1 video giọng miễn phí người dẫn nữ để biết giọng vùng nào | | |
| V-1 | Thanh tiêu đề | Sổ dựng sẵn (chính `used=6`), service chạy với biến test, mở `/studio` | Câu "còn 4 lượt chính và 10 lượt phụ…", giờ có chữ "khoảng" và "hôm nay" hoặc "ngày mai" đúng theo ngày trên máy. Không có tên model, không có chữ "hôm nay" gắn với con số lượt | | |
| V-2 | Sửa lời đọc khi thiếu lượt | Bản sao video Gemini chính, sổ chính `used=9`, sửa 2 câu | Thông báo đỏ đúng mẫu, có nút đọc lại bằng giọng miễn phí. Bấm **Dựng lại video** → báo lỗi trong vài giây, video cũ còn nguyên, 0 lời gọi | | |
| V-3 | Đổi sang giọng miễn phí | Tiếp V-2, bấm nút | Hộp xác nhận kiểu của trang (không phải hộp của trình duyệt), nút "Đổi sang giọng miễn phí" / "Để sau". Sau khi dựng: nhãn "Giọng miễn phí" ở danh sách, dòng giọng ở chi tiết | | |
| V-4 | Quay lại giọng Gemini | Tiếp V-3, sổ trống | Nút "Đọc lại toàn bộ bằng giọng Gemini (dùng 4 lượt, còn 10)" bấm được; sau khi dựng: "Giọng của video: Gemini", nhãn ở danh sách mất, server giả nhận 4 lời gọi. Với sổ hết lượt: nút mờ kèm "Chưa đủ lượt. Có lại lượt lúc {giờ}." | | |
| V-5 | MKTG | Ảnh desktop và mobile 390 px: V-1, V-2, hết lượt theo ngày, **khoá tạm 60 phút**, **video giọng miễn phí trước khi duyệt** (danh sách + chi tiết + hộp duyệt), thẻ "Chỉ xem" có dòng giọng, `available=false` | Người không rành kỹ thuật hiểu: còn bao nhiêu lượt, bao giờ có lại, video này giọng gì, hết thì làm gì. Ở 390 px thanh tiêu đề không tràn ngang. Hai con số "còn" trên cùng màn hình không mâu thuẫn | | |
| V-6 | Duyệt video giọng miễn phí | Bấm **Duyệt & lưu** trên video giọng miễn phí (không Drive) | Hộp xác nhận có câu "Video này dùng giọng miễn phí. Sau khi duyệt không đổi giọng được nữa." | | |
| V-7 | Hết lượt cả ngày | Sổ: chính và phụ đều `daily_429`; gọi `generate_voiceovers` | Thanh tiêu đề báo hết lượt đến {giờ}. Giọng miễn phí, 0 lời gọi, Terminal in câu tiếng Việt đúng mẫu | | |
| V-8 | **Người dùng** chạy thật một ngày (sau khi merge) | Tạo video như thường lệ đến khi model chính hết lượt | Terminal có câu tiếng Việt về giọng; video kế tiếp không gọi model đã hết; Studio hiện số lượt khớp | | |

### Cổng chất lượng

- [ ] **Trước khi Dev bắt đầu**: nhánh đã có `origin/main` (`1ce153a`)
- [ ] **Trước khi merge PR**: V-0 có kết quả ghi trong `TODO.md`; model không đạt đã bị gỡ khỏi `DEFAULT_TTS_FALLBACK_MODELS` và `.env.example`
- [ ] Đã kiểm hết D-1…D-44, DD-1…DD-3
- [ ] V-1…V-7 đạt (V-8 do người dùng làm sau khi merge, ghi vào `TODO.md`)
- [ ] Không có hồi quy (D-36…D-43)
- [ ] Không vi phạm C-0001-1…4 và C-0012-1…6
- [ ] Tester xác nhận: 0 lời gọi tới Gemini thật, sổ đếm thật trong `storage/` không bị đụng
- [ ] `exercise.py`, `app.html` không có trong diff
- [ ] Xong mọi việc trong kế hoạch
- [ ] Đã cập nhật tài liệu SSoT

---

## Câu hỏi mở và câu trả lời của người dùng

Người dùng trả lời ngày 2026-11-13, người điều phối chuyển lời. Nguyên văn: "Q1, Q2,Q4,Q5,Q6 nhu BA trả lời. Q3 thì cứ ưu tiên 3.1 trước hết thì 2.5."

| # | Câu hỏi | Khuyến nghị của BA | Người dùng quyết |
|---|---------|--------------------|------------------|
| Q-1 | "Hạn chế khi tạo video" là nói **giọng đọc** (code gọi Gemini API), hay **clip/ảnh trong app Gemini**? | DR này chỉ xử lý giọng đọc; clip trong app Gemini cần yêu cầu riêng | **Theo khuyến nghị.** Làm cho giọng đọc qua API; clip trong app Gemini là yêu cầu riêng |
| Q-2 | `main` đã bật sẵn 2 model Gemini phụ. (a) nghe thử V-0 rồi mới chốt mặc định; (b) để mặc định trống ngay; (c) giữ như `main`, không nghe | (a) | **(a).** V-0 chưa diễn ra. Người điều phối chuyển cổng V-0 sang "trước khi merge PR" (xem §Quyết định); người dùng chưa xác nhận riêng điểm này |
| Q-3 | Thứ tự model phụ: 3.1 (video động tác hằng ngày) trước, hay 2.5 (gần như để không) trước? | 2.5 trước, 3.1 sau | **Không theo khuyến nghị: 3.1 trước, hết thì 2.5** (đúng thứ tự đang có trên `main`). Hệ quả ghi ở R-4 |
| Q-4 | Video bài tập thiếu lượt: giữ cách mượn model khác rồi tới giọng miễn phí, hay dừng lại? | Giữ như hiện nay; có câu báo giọng trước `y/n` | **Theo khuyến nghị** |
| Q-5 | Thêm giọng dự phòng trả phí (OpenAI TTS)? | Không | **Theo khuyến nghị: không** |
| Q-6 | Hết lượt giữa lô `--sheet`: làm tiếp bằng giọng miễn phí, hay dừng? | Làm tiếp bằng giọng miễn phí | **Theo khuyến nghị** |

Còn mở: kết quả V-0; xác nhận của người dùng về việc chuyển cổng V-0 sang trước khi merge.

---

## Kết quả

(BA điền sau khi Dev, Reviewer, Tester, MKTG xong. Kết quả test chép nguyên văn từ báo cáo Tester.)

### Review trước khi Dev (MKTG, 2026-11-13)

| # | Góp ý | Xử lý trong DR |
|---|-------|----------------|
| C-1 | Giọng phụ bật mặc định trước khi ai nghe thử | Cổng V-0 (bản 3: trước khi merge PR, theo điều chỉnh của người điều phối); model không đạt bị gỡ khỏi mặc định; C-0012-6; Q-2. Chi phí V-0 sửa thành khoảng 9 lượt mỗi model |
| C-2 | Video giọng miễn phí không có đường quay lại Gemini, không được nhắc trước khi duyệt | Nhãn ở danh sách, dòng đầu trang chi tiết, câu trong hộp duyệt, nút **Đọc lại toàn bộ bằng giọng Gemini** (đưa vào phạm vi: `demo.py` đã có `--revoice-all gemini`, thêm 1 kiểm tra trước, 1 giá trị ở `render`, 1 nút); D-20, D-21, D-42, V-4, V-6 |
| N-1 | "Hôm nay", giờ làm mới, "để mai" | `{giờ}` = "khoảng HH:MM hôm nay/ngày mai" tính từ múi giờ; bỏ "hôm nay" khỏi con số; D-31, D-44, V-1 |
| N-2 | Câu riêng cho khoá tạm | Bảng Studio; ảnh ở V-5 |
| N-3 | Ba tên giọng | Bảng "Từ dùng thống nhất" |
| N-4 | Hai con số "còn lại" | Câu `updateBar` mới |
| N-5 | Xác nhận khi đổi sang giọng miễn phí | Dùng lại `<dialog id="confirm">`; V-3 |
| N-6 | Câu cho lỗi revoice và `available=false` | Bảng Studio |
| N-7 | Lý do dạng mã | `segments[i].tts_fallback` = `quota` / `error`; D-11, D-12 |
| N-8 | Câu tiếng Việt trên Terminal | Nhận, ghi rõ là thông báo cho người vận hành, log vẫn tiếng Anh; D-32, D-35 |
| N-9 | Hết lượt giữa lô | Câu đầu lô (D-34); Q-6 |
| N-10 | `--tts-status` không phải thao tác người vận hành | Ghi ở bảng hàm và hướng dẫn phần kỹ thuật |
| N-11 | Video bài tập đổi giọng không ai báo | Câu trước `y/n` (D-33), dòng giọng ở thẻ "Chỉ xem" (D-41); Q-4 |
| N-12 | Giọng miễn phí có đúng giới tính, vùng miền | Bảng đối chiếu ở Bối cảnh; R-11; V-0 nghe thêm |
| N-13 | Danh sách tài liệu vận hành | Bảng "từng chỗ phải sửa"; DD-2 |
| G-1 | Dòng gập lượt video bài tập | Không nhận (lý do ở §Phạm vi) |
| G-2…G-6 | Câu "không đủ cho video mới", thanh tiêu đề ở 390 px, "có lại lượt", câu ngày đầu, ảnh V-5 | Nhận |

### Triển khai

| # | Việc | Kết quả | Ghi chú |
|---|------|---------|---------|
| | | | |

### Review

| # | Góp ý | Xử lý |
|---|-------|-------|
| | | |

### Test

| # | Kết quả |
|---|---------|
| | |

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR trước | `docs/decision-records/DR-0001-video-review-studio.md` (C-0001-1…4) |
| Code trên `main` (`1ce153a`) | `demo.py`: `_gemini_tts`, `tts_provider`, `generate_voiceovers`, `gemini_tts_models`, `DEFAULT_TTS_FALLBACK_MODELS`, `clean_gemini_audio`, `revoice_changed`, `approval_step`, `run_one`, `render_only`, `print_summary`; `exercise.py`: `DEFAULT_TTS_MODEL`, `EXTRA_TTS_MODEL`, `run_next`; `backend/app/api/studio.py`: `list_videos`, `video_detail`, `render`; `backend/app/web/studio.html`: `GEMINI_PER_DAY`, `updateBar`, `<dialog id="confirm">` |
| Commit liên quan | `12c71fe` "remove Gemini end-of-clip burst and add backup Gemini TTS models" (PR #9) |
| Tài liệu chi phí | `FEASIBILITY.md` (OpenAI TTS), `.env.example` (Gemini TTS free tier), `TODO.md` §5 (model Groq) |
| Công cụ | `workflow_step.py` không chạy được (thiếu module `automation_engine`), các phase được điều phối thủ công qua `/feature` |
