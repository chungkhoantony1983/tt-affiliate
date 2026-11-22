# capcut-mcp — Claude tạo dự án CapCut

MCP server cho phép Claude (Claude Desktop, Claude Code) dựng **dự án nháp (draft) CapCut desktop**:
ghép clip/ảnh, chữ trên màn hình, phụ đề SRT, giọng đọc, nhạc nền, mờ dần, zoom chậm, hiệu ứng
chuyển cảnh. Bạn mở dự án trong CapCut, xem lại, chỉnh nếu cần rồi bấm **Xuất**.

- Ngôn ngữ / SDK: Python ≥ 3.10, **MCP Python SDK chính thức v2** (`mcp>=2.3`, API `MCPServer`), transport stdio.
- Không phụ thuộc gì khác. `imageio-ffmpeg` (tuỳ chọn, đã có trong `requirements-demo.txt`) giúp đọc độ dài / kích thước video.
- Không gọi mạng, không cần API key.

## Tính khả thi (đọc trước)

| Câu hỏi | Trả lời |
|---|---|
| CapCut có API chính thức để tạo video? | **Không.** Chỉ có cách ghi file draft vào thư mục dự án của CapCut desktop. |
| Định dạng draft có công bố? | Không. Tool này dựa theo các dự án mã nguồn mở đã giải mã định dạng (xem *Nguồn*). |
| CapCut bản quốc tế có mã hoá draft? | Không. Chỉ **Jianying (剪映, Trung Quốc) ≥ 6.0** mã hoá → tool từ chối và báo lỗi rõ. |
| Tự xuất .mp4? | **Không.** Người dùng mở CapCut và bấm Xuất. (Pipeline `demo.py` / `travel.py` của repo vẫn tự xuất bằng FFmpeg.) |
| CapCut mới (8.7+, 9.x, 10.x)? | Có báo cáo app từ chối draft do công cụ tạo từ đầu. Cách an toàn: **ghi vào một dự án trống do CapCut tạo** (`into_existing`, xem dưới). |
| Hiệu ứng chuyển cảnh thư viện CapCut | Cần `effect_id` / `resource_id` thật. Tool **không tự bịa id**: lấy từ một dự án bạn đã áp hiệu ứng bằng tay (`inspect_capcut_draft`). Mờ dần (`fade_in`/`fade_out`) và zoom chạy bằng keyframe, không cần tài nguyên. |

Chưa kiểm được: mở draft trong CapCut thật (máy cloud không có CapCut). Test tự động chỉ kiểm cấu
trúc JSON, thời gian, tham chiếu, cách ghi vào thư mục. **Lần đầu hãy thử 1 draft ngắn trên máy bạn.**

## Cài đặt

```bash
cd tools/capcut_mcp
python3 -m venv .venv
.venv/bin/pip install -e '.[probe]'        # Windows: .venv\Scripts\pip install -e ".[probe]"
```

Thư mục draft CapCut tự nhận:

- Windows: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`
- macOS: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`

Khác chỗ (hoặc đổi trong CapCut → Cài đặt → Vị trí lưu nháp) thì đặt biến môi trường `CAPCUT_DRAFTS_DIR`.

### Claude Desktop

Sửa `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "capcut": {
      "command": "/ĐƯỜNG/DẪN/tt-affiliate/tools/capcut_mcp/.venv/bin/capcut-mcp",
      "env": { "CAPCUT_DRAFTS_DIR": "/Users/<bạn>/Movies/CapCut/User Data/Projects/com.lveditor.draft" }
    }
  }
}
```

Windows: `"command": "C:\\...\\tools\\capcut_mcp\\.venv\\Scripts\\capcut-mcp.exe"`. `env` bỏ được nếu dùng thư mục mặc định. Khởi động lại Claude Desktop.

### Claude Code

```bash
claude mcp add capcut -- /ĐƯỜNG/DẪN/tt-affiliate/tools/capcut_mcp/.venv/bin/capcut-mcp
# có thư mục riêng:
claude mcp add capcut -e CAPCUT_DRAFTS_DIR="/đường/dẫn/com.lveditor.draft" -- /ĐƯỜNG/DẪN/.venv/bin/capcut-mcp
```

MCP server phải chạy **trên cùng máy với CapCut** (đường dẫn file media phải tồn tại ở máy mở CapCut).

## Quy trình khuyên dùng

1. Mở CapCut → **Tạo dự án mới** (để trống) → thoát hẳn CapCut. Nhớ tên dự án (vd `1122`).
2. Nhờ Claude dựng video, cuối cùng lưu với `into_existing: "1122"`.
3. Mở lại CapCut → dự án `1122` có sẵn timeline → xem, chỉnh, **Xuất**.

Bản gốc của dự án được sao lưu thành `*.bak-<giờ>` trong cùng thư mục, nên lỡ hỏng thì đổi tên lại.
Bản CapCut cũ hơn (≤ 8.x) có thể lưu thẳng thành dự án mới (bỏ `into_existing`), rồi khởi động lại CapCut.

## Công cụ (tools)

Thời gian tính bằng **giây**. Vị trí `x`, `y` trong `[-1, 1]`, `(0,0)` = giữa khung, `y = -1` = mép dưới.
Video dọc 1080×1920 cho TikTok: giữ chữ trong khoảng `y` từ `-0.65` đến `0.55` để tránh nút của app.

| Tool | Việc |
|---|---|
| `capcut_info` | Thư mục draft của máy, các draft đang mở trong bộ nhớ |
| `create_draft(name, width=1080, height=1920, fps=30)` | Tạo dự án trong bộ nhớ → `draft_id` |
| `add_media(draft_id, path, start?, duration?, source_start, track="main", volume, speed, scale, x, y, fade_in, fade_out, zoom_from, zoom_to)` | Thêm clip video hoặc ảnh. Bỏ `start` = nối tiếp cuối track. Track khác (vd `overlay`) = lồng hình |
| `add_text(draft_id, text, start, duration, track="text", font_size=8, color, bold, align, x, y, stroke_color, background_color, max_width, fade_in, fade_out)` | Chữ trên màn hình (hook, tiêu đề). Chữ chồng thời gian → khác `track` |
| `add_subtitles(draft_id, srt, track="subtitles", offset, font_size=6, color, y=-0.62, …)` | Phụ đề từ nội dung SRT hoặc đường dẫn `.srt` |
| `add_audio(draft_id, path, start=0, duration?, source_start, track="audio", volume, fade_in, fade_out)` | Giọng đọc / nhạc nền (mỗi loại một track, vd `voiceover`, `music`) |
| `add_transition(draft_id, track, after_segment, name, effect_id, resource_id, duration=0.5)` | Hiệu ứng chuyển cảnh thư viện CapCut, id lấy từ `inspect_capcut_draft` |
| `remove_segment(draft_id, segment_id)` | Xoá một đoạn |
| `get_timeline(draft_id)` | Xem các track/đoạn + lỗi kiểm tra |
| `save_draft_to_capcut(draft_id, into_existing?, drafts_dir?, overwrite, copy_media, allow_missing_media)` | Ghi vào thư mục CapCut (CapCut phải đang tắt). `copy_media` chép file vào `materials/` của dự án |
| `list_capcut_drafts(drafts_dir?)` | Liệt kê dự án CapCut trên máy |
| `inspect_capcut_draft(project)` | Đọc một dự án có sẵn: track, phiên bản app, id hiệu ứng chuyển cảnh/hiệu ứng để dùng lại |
| `build_video(name, scenes, voiceover?, music?, music_volume=0.2, subtitles_srt?, save, into_existing?, …)` | Dựng cả video trong một lần gọi |

Lỗi dự đoán trước (file không có, đoạn chồng nhau, clip dài hơn file gốc, draft Jianying mã hoá…)
trả về cho Claude bằng lời rõ ràng để Claude tự sửa.

## Ví dụ

Nói với Claude:

> Dùng capcut, làm video dọc "Hoi An at night" từ `~/clips/hoian_1.mp4` (lấy từ giây 3, 4 giây),
> `~/clips/hoian_2.jpg` (3 giây, zoom 1.0→1.12), `~/clips/hoian_3.mp4` (4 giây, mờ dần cuối 0.5s).
> Hook "Is Hoi An worth it at night?" 0–2.5s ở trên. Giọng đọc `~/vo/hoian.mp3`, nhạc `~/music/pixabay_lofi.mp3`
> nhỏ 15%, phụ đề `~/vo/hoian.vi.srt`. Lưu vào dự án trống "1122".

Claude sẽ gọi `build_video`:

```json
{
  "name": "Hoi An at night",
  "scenes": [
    {"media": "~/clips/hoian_1.mp4", "source_start": 3, "duration": 4,
     "text": "Is Hoi An worth it at night?", "text_y": 0.35},
    {"media": "~/clips/hoian_2.jpg", "duration": 3, "zoom_from": 1.0, "zoom_to": 1.12},
    {"media": "~/clips/hoian_3.mp4", "duration": 4, "fade_out": 0.5}
  ],
  "voiceover": "~/vo/hoian.mp3",
  "music": "~/music/pixabay_lofi.mp3", "music_volume": 0.15,
  "subtitles_srt": "~/vo/hoian.vi.srt",
  "save": true, "into_existing": "1122"
}
```

Lưu ý `text` trong một scene kéo dài bằng scene đó. Hook ngắn hơn (0–2.5s) thì gọi `add_text` riêng.
Giọng đọc dài hơn hình thì video kéo dài theo giọng: kiểm `get_timeline` trước khi lưu.

### Dùng với video du lịch của repo

Thư mục `storage/videos/<…>/` của `travel.py` đã có clip có giấy phép, `audio_N.mp3`, `credits.txt`.
Có thể nhờ Claude "dựng draft CapCut từ thư mục này" để chỉnh tay trong CapCut thay vì dựng bằng FFmpeg.
Bản quyền vẫn theo `credits.txt` và DR-0002: chỉ dùng clip Pixabay/Pexels/Wikimedia đã ghi nguồn.

## Test

```bash
cd tools/capcut_mcp
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q
```

Test kiểm: đơn vị micro giây, nối tiếp đoạn, mọi `material_id` / `extra_material_refs` trỏ đúng,
chữ (JSON trong `content`, range UTF-16 cho emoji), keyframe mờ/zoom, SRT, chặn đoạn chồng nhau, ghi
thư mục mới, ghi vào dự án có sẵn (giữ id/phiên bản/trường lạ của app, ghi cả bản `Timelines/`, sao lưu),
từ chối draft mã hoá, chép media, gọi tool qua MCP, và đọc video thật bằng ffmpeg (nếu có `imageio-ffmpeg`).

## Giới hạn

- Không tự xuất .mp4, không gắn sản phẩm TikTok Shop, không đăng TikTok.
- Font chữ: font mặc định của CapCut (chọn font khác trong app).
- Không có hiệu ứng/animation chữ, bộ lọc, sticker từ thư viện (cần id tài nguyên thật). Có thể thêm sau theo cách `add_transition`.
- Draft giữ trong bộ nhớ của server: khởi động lại MCP server là mất draft chưa lưu.
- Cấu trúc draft có thể đổi theo bản CapCut mới. Gặp lỗi mở dự án: gửi `inspect_capcut_draft` của một dự án CapCut tự tạo để so.

## Nguồn

- pyJianYingDraft (GuanYixuan): https://github.com/GuanYixuan/pyJianYingDraft
- pyCapCut: https://github.com/GuanYixuan/pyCapCut · https://pypi.org/project/pycapcut/
- capcut-cli, ghi chú phiên bản & mã hoá: https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md · https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md
- VectCutAPI (CapCutAPI): https://docsearch.algolia.com/mcp/docs/repo/sun-guannan/vectcutapi
