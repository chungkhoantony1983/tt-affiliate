---
description: 'Quy tắc giọng đọc (TTS) của dự án để làm và soát code: một video một engine/model, chuỗi model dự phòng, đọc lại câu sửa theo script.json, quota Gemini, model -lite, tiếng nổ ở mép, Gemini đọc bịa, chọn giọng'
---

Mã nạp: voice-rules/1

Skill này là **sổ tay dùng chung của `dev`, `reviewer`, `techlead`, `tester`**. Dùng khi làm, soát hay test bất cứ thứ gì chạm tới giọng đọc, hoặc khi soát chỗ có thể gọi Gemini ngoài ý muốn. Không có script, không nhận đối số. Nguồn của mỗi quy tắc nằm trong ngoặc: khi code đổi thì đọc lại nguồn, đừng tin skill hơn code.

## Quy tắc

1. **Một video, một engine, một model** (C-0001-1). `generate_voiceovers` thử lần lượt `gemini_tts_models()` = `GEMINI_TTS_MODEL` → `GEMINI_TTS_FALLBACK_MODELS` → edge-tts. Model nào lỗi thì **đọc lại cả video** bằng model kế tiếp, không ghép câu của hai model hay hai engine (`demo.py`: `generate_voiceovers`, `gemini_tts_models`).
2. **Ghi lại model đã dùng**: `seg["tts_model"]`. `revoice_changed()` đọc lại câu sửa (`line != audio_line`) bằng đúng `tts_provider` và model đó. Lỗi thì không đổi file nào (exit 3), Studio đưa lựa chọn `--revoice-all edge` (`demo.py`: `revoice_changed`, `render_only`; `api/studio.py`).
3. **Engine lấy từ `script.json`, không từ biến môi trường**: `revoice_changed()` dùng `script.json → tts_provider`, **không** theo `TTS_PROVIDER`. Đặt `TTS_PROVIDER=edge` không đủ để chặn Gemini khi dựng lại video Gemini có câu đã sửa. Khi kiểm: luôn để trống `GEMINI_API_KEY`, hoặc dùng skill `sandbox-render`.
4. **Quota**: mỗi model Gemini TTS free 10 lượt/ngày (`.env.example`, thông báo lỗi trong `_gemini_tts`).
   - Video sản phẩm: `gemini-3.8-flash-tts` (`GEMINI_TTS_MODEL`).
   - Video bài tập: `gemini-3.1-flash-tts-preview` cho động tác (`exercise.DEFAULT_TTS_MODEL`), `gemini-2.5-flash-preview-tts` cho mở đầu, tổng kết (`exercise.EXTRA_TTS_MODEL`).
   - Hai model dự phòng của video sản phẩm (`DEFAULT_TTS_FALLBACK_MODELS`) chính là hai model của video bài tập, nên **dùng chung lượt**.
   - **Không gọi Gemini khi kiểm.** Mỗi lần gọi là 1 lượt của người vận hành.
5. **Không dùng model `-lite`**: nó đọc to cả phần chỉ dẫn đạo diễn (`exercise.py`, ghi chú trên `DEFAULT_TTS_MODEL`, 2026-11-12). Prompt phải giữ khung `AUDIO PROFILE / DIRECTOR'S NOTES / TRANSCRIPT` (`_gemini_tts_prompt`).
6. **Tiếng nổ ở mép clip**: `_trim_gemini_edges` cắt tiếng click đầu clip và tiếng nổ cuối clip. `clean_gemini_audio` làm sạch lại audio cũ khi dựng lại mà không gọi TTS. `render_video` thêm fade 15 ms ở đầu và 30 ms ở cuối mỗi câu. Sửa phần này thì kiểm bằng skill `audio-check` Bước 2.
7. **Gemini có thể đọc thêm câu không có trong lời** (vụ trà ô long, 2026-11-13: tự thêm "… bán có 120 ngàn một túi"). Sửa prompt TTS thì kiểm bằng `audio-check` Bước 3 trên audio **đã có**, không tạo audio mới.
8. **Chọn giọng**: `choose_persona` — điện tử, máy móc, ô tô, thể thao → `nam_bac`; còn lại → `nu_nam`. Ép một giọng cho mọi video bằng `GEMINI_TTS_PERSONA`. Giọng đã chọn lưu ở `script.json → voice_persona`.

## Chỗ có thể gọi Gemini (soát chi phí)

| Đường gọi | Khi nào gọi Gemini | Cách chặn khi kiểm |
|-----------|--------------------|--------------------|
| `demo.py` tạo video mới (`--product`, `--csv`, `--sheet`) | Có `GEMINI_API_KEY` và `TTS_PROVIDER` khác `edge` | `TTS_PROVIDER=edge GEMINI_API_KEY=` |
| `demo.py --render-only` (Studio "Dựng lại") | Có câu sửa và `script.json → tts_provider=gemini` (quy tắc 3) | `GEMINI_API_KEY=`, hoặc `--revoice-all edge`, hoặc `sandbox-render` |
| `exercise.py` tạo bài mới (qua `demo.generate_voiceovers`, model `EXERCISE_TTS_MODEL` / `EXERCISE_EXTRA_TTS_MODEL`) | Mỗi động tác, mở đầu, tổng kết | `TTS_PROVIDER=edge GEMINI_API_KEY=` |
| `IMAGE_PROVIDER=gemini` | Tạo ảnh nhân vật (cần billing) | Giữ `IMAGE_PROVIDER=manual` |

Soát diff: có lời gọi `_gemini_tts` mới, vòng lặp gọi lại, hay thử lại khi lỗi mà không giới hạn thì báo (mỗi lượt thừa là 1/10 quota trong ngày).

## Câu hỏi soát nhanh

- Có đường nào ghép audio của hai model / hai engine trong cùng một video không?
- Đổi `tts_provider`, `tts_model`, `audio_line` trong `script.json` thì nơi ghi (`demo.py`), nơi đọc (`api/studio.py`) và nơi hiện (`studio.html`) đã khớp chưa?
- Thư mục cũ thiếu `tts_provider` / `tts_model` thì chạy ra sao (hiện coi là `gemini` và model chính)?
- Ca test có thể chạm Gemini không? Nếu có: đã để trống `GEMINI_API_KEY` hay dùng `sandbox-render` chưa?
