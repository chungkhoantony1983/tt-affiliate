# DR-0003: Vùng an toàn cho chữ và khung vẽ trên video (tránh cột nút và thanh tab của TikTok)

| Trạng thái | Ngày | Đề xuất | Duyệt |
|-----------|------|---------|-------|
| 📋 Đề xuất | 2026-11-12 | Claude (BA) | chờ người dùng |

Capability: `video-render` · Nhánh: `fix/cta-safe-zone` · Domain workflow: `spec`

> **Về số DR**: số lớn nhất trên `origin/main` lúc viết là `DR-0001`. Một BA khác đang viết DR cho việc "cắt clip Gemini" (worktree `clip-trim`) và có thể lấy `DR-0002`. Để tránh trùng, DR này dùng số **0003** (= lớn nhất + 2). Nếu DR "cắt clip" không dùng số 0002 thì vẫn giữ số 0003, không đánh lại.

> **Review của MKTG (2026-11-12)**: đã đối chiếu các hằng số với ảnh chụp thật; khớp, nhưng chỉ cho bài không có thẻ giỏ hàng và caption 2 dòng. Các góp ý đã đưa vào §Quyết định, R-2, A-1, D-1, D-3, V-6, việc #5, #8, #8b. MKTG đồng ý phương án A (dịch trái ~60 px), đồng ý lấy ảnh chụp thẻ giỏ hàng làm điều kiện đóng DR ($0), và giữ nguyên các video đã đăng.

Vai trò: **BA** = phân tích, viết DR, cập nhật tài liệu · **Dev** = sửa code · **Reviewer** = review code · **Tester** = chạy bảng quyết định · **MKTG** = xem khung hình và xem thử trên điện thoại dưới góc nhìn người xem.

---

## Bối cảnh

**Vấn đề (gốc rễ)**:

Người dùng báo (2026-11-12): *"Khung "BẤM GIỎ HÀNG VÀNG" bị lấn sang cột nút bên phải của TikTok vẫn chưa được sửa."* Lỗi đã được MKTG ghi ở `storage/videos/20261111_114841_bot-me-den/marketing-review.md` (hạng mục F, đề xuất #8) và trong `TODO.md` §5 (mục "Đội vai trò AI").

Đọc code (`demo.py` dòng 594–822, `exercise.py` dòng 353–457) thấy nguyên nhân gốc không riêng gì CTA:

1. **Không có khái niệm "vùng an toàn" trong code.** Mọi chữ được canh giữa theo cả khung `W=1080` (`_text_block`: `max_w = W - 140`; `_pill`: không giới hạn bề rộng, không xuống dòng). Chỉ có một chú thích ở `_scene_story` nhắc "~350px" cho phần dưới, không thành hằng số, không áp cho cảnh khác.
2. **`_pill()` không bao giờ xuống dòng.** Chữ dài thì khung dài theo, có thể vượt cả mép ảnh. CTA "BẤM GIỎ HÀNG VÀNG BÊN DƯỚI" cỡ 56 rộng 1003 px.
3. **Hiệu ứng zoom làm chữ phình ra.** `render_video` dùng `zoompan` 1,00 → 1,06 quanh tâm khung. Chữ vẽ trên ảnh tĩnh nên cũng bị phóng to 6 %: một điểm ở x = 1010 lúc vẽ sẽ ra x = 1038 ở khung cuối. Mọi số đo phải tính trên khung cuối, không phải trên ảnh lúc vẽ.
4. **Phía trên cũng bị che.** Thanh tab của TikTok ("Bạn bè / Đã follow / Đề xuất") nằm ngay chỗ đặt hook cảnh sản phẩm (y = 120), nhãn cảnh sản phẩm (y = 170), tên chuỗi và hook của video bài tập (y = 120, 180).

**Lý do làm bây giờ**: người dùng yêu cầu. Cột nút che CTA đúng lúc người xem cần bấm giỏ hàng, ảnh hưởng trực tiếp tới đơn.

**Người được lợi**: người xem (đọc được trọn chữ), người vận hành (không phải tự canh chữ, không phải sửa tay), kênh (CTA rõ hơn ở cảnh quyết định mua).

**Đã có sẵn**: Studio "Dựng lại video" (`demo.py --render-only`), `--rerender`, `--exercise-rerender` dựng lại không gọi AI. `scripts/review_frames.py` trích khung hình để kiểm.

**Còn thiếu**: hằng số vùng an toàn dùng chung; hàm vẽ chữ biết tôn trọng vùng đó; cách kiểm tự động.

**Ràng buộc**:
- Chi phí $0 (P02). Không gọi Gemini, Groq. Dựng lại video cũ không được tốn lượt TTS.
- Không đổi `app.html` (C-0001-4, app TikTok đang xét duyệt).
- Giữ ý nghĩa CTA: "giỏ hàng vàng", hướng xuống dưới, mũi tên chỉ xuống, dòng "Video có gắn link tiếp thị liên kết".
- Không có test suite (`.claude/CLAUDE.md`). Kiểm bằng script và khung hình.

### Số đo vùng UI của TikTok (nguồn và giả định)

Trong repo **không có tài liệu chính thức** của TikTok về kích thước cột nút hay thanh tab. Các con số dưới đây **đo từ một ảnh chụp màn hình thật**, không lấy từ tài liệu TikTok:

- Nguồn: `storage/videos/20261020_145409_omniear-tai-nghe-thu-va-khuech-dai-am-th/Ảnh màn hình 2026-10-20 lúc 15.25.14.png` (video OMNIEAR đã đăng, chụp trên iPhone, 1290×2796, chưa gắn giỏ hàng).
- Cách quy đổi: thanh điều hướng đáy (đen) bắt đầu ở y = 2548. TikTok phủ video kín chiều cao 0–2548, nên hệ số = 2548 / 1920 = **1,327** và **mỗi bên bị cắt mất khoảng 54 px video** (1080 × 1,327 = 1433 > 1290). Kiểm chéo: phụ đề "Giờ mẹ nghe rõ tiếng con rồi, vui quá." rộng 920 px trong video (đo bằng font của `demo.py`), trên ảnh chụp rộng 1227 px (x 23–1250) → 1,334 ≈ 1,327 × zoom 1,005. Khớp.
- Công thức: `x_video = 540 + (x_màn_hình − 645) / 1,327`, `y_video = y_màn_hình / 1,327`.

| Vùng UI (trên ảnh chụp) | Toạ độ màn hình | Quy đổi ra khung video 1080×1920 |
|---|---|---|
| Phần video nhìn thấy theo chiều ngang | 0–1290 | x ≈ 54–1026 |
| Thanh tab (chữ "Bạn bè", gạch chân) | y 224–302 | y ≈ 169–228 |
| Đồng hồ trạng thái | y 68–107 | y ≈ 51–81 |
| Cột nút phải: mép trái (ảnh đại diện, tim, bình luận) | x ≈ 1132 (tim 1158, bình luận 1138) | x ≈ 907 |
| Cột nút phải: từ ảnh đại diện tới đĩa nhạc | y ≈ 1398–2540 | y ≈ 1053–1914 |
| Khối caption (tên kênh "SDC…" trở xuống) | y ≥ 2111 | y ≥ 1591 |

**Giả định (chưa có số đo)**:
- Chỉ có **một** máy (iPhone, tỉ lệ 19,5:9). Máy Android hoặc máy 16:9 có thể khác.
- Ảnh chụp **chưa có thẻ giỏ hàng vàng** (video OMNIEAR chưa gắn sản phẩm). Thẻ giỏ hàng nằm trên khối caption nên có thể đẩy vùng che dưới lên cao hơn y = 1591. Chưa đo được.
- Ảnh chụp màn hình iOS không hiện "Dynamic Island" (đảo đen giữa mép trên), nên chưa đo được nó che tới đâu. Mép trên an toàn bên dưới đã nằm dưới thanh tab nên cũng tránh được vùng này.

MKTG đề xuất "chừa khoảng 120–140 px bên phải". Số đo ở trên cho thấy cột nút bắt đầu ở x ≈ 907, tức là cách mép phải 173 px (vì TikTok cắt 54 px mỗi bên trên máy dài). DR này dùng số đo, không dùng con số ước lượng.

---

## Quyết định

> **Định nghĩa một bộ hằng số vùng an toàn duy nhất trong `demo.py`, tính theo khung video cuối cùng (sau zoom). Mọi hàm vẽ chữ/khung (`_text_block`, `_pill`, mũi tên CTA, và lớp chữ của `exercise.py`) lấy bề rộng, vị trí từ vùng này. Ở phần dưới (ngang cột nút), khối chữ được canh giữa trong khoảng an toàn nên tâm dịch sang trái. Khung CTA ngắt thành 2 dòng "BẤM GIỎ HÀNG VÀNG" / "BÊN DƯỚI", mũi tên đặt dưới tâm khung. Thêm script kiểm `scripts/check_safe_zone.py` ($0). Video cũ sửa bằng "Dựng lại video", không tốn lượt giọng.**

### Hằng số (khung cuối 1080×1920)

| Tên (gợi ý cho Dev) | Giá trị | Cơ sở |
|---|---|---|
| `SAFE_TOP` | 240 | Thanh tab kết thúc ở y ≈ 228, chừa 12 px |
| `SAFE_BOTTOM` | 1570 | Khối caption bắt đầu ở y ≈ 1591, chừa 21 px. Trùng con số "~350 px" đã ghi trong `_scene_story`. Chưa tính thẻ giỏ hàng (xem giả định) |
| `SAFE_SIDE` | 60 | Máy dài cắt 54 px mỗi bên, chừa 6 px. Áp cho cả trái và phải |
| `BUTTON_COL_X` | 890 | Mép trái cột nút ở x ≈ 907, chừa 17 px |
| `BUTTON_COL_TOP` | 1000 | Ảnh đại diện bắt đầu ở y ≈ 1053, chừa 53 px vì máy khác có thể cao hơn |
| `ZOOM_MAX` | 1,06 | Hệ số đang dùng trong `zoompan`. Filter phải đọc từ hằng số này, không ghi số cứng |

Quy tắc: một chữ/khung có phần nào nằm trong dải y ≥ `BUTTON_COL_TOP` thì mép phải ≤ `BUTTON_COL_X`. Ở trên dải đó, mép phải ≤ `1080 − SAFE_SIDE` = 1020.

Khoảng vẽ tương ứng **trên ảnh tĩnh** của `demo.py` (đã bù zoom 1,06 quanh tâm 540, 960): trái ≥ 88, phải ≤ 992 (phần trên) hoặc ≤ 870 (ngang cột nút), trên ≥ 281, dưới ≤ 1535. `exercise.py` không zoom lớp chữ nên dùng thẳng số khung cuối. Dev viết một hàm tính khoảng này từ hằng số (vd `safe_box(y0, y1, zoom)`), không ghi tay các số 88/870/281/1535.

### Cách vẽ chữ

- **Canh giữa trong khoảng an toàn** của dải y mà chữ chiếm: phần trên tâm vẫn là 540; ngang cột nút tâm là (88 + 870) / 2 ≈ 479 trên ảnh tĩnh, tức dịch trái khoảng 60 px. Mũi tên CTA theo tâm của khung CTA.
- **`_pill` được xuống dòng** theo bề rộng an toàn (tối đa 2 dòng). Vẫn không vừa thì giảm cỡ chữ từng bước tới mức tối thiểu Dev chọn. **Sàn cỡ chữ**: DR không đặt con số (chưa có nguồn); `check_safe_zone.py` in cỡ chữ thực tế của từng phần tử để MKTG duyệt ở việc #8. **Khung CTA không được giảm cỡ** (2 dòng ở cỡ 56 đã vừa). Vẫn không vừa (vd một từ quá dài) thì vẫn vẽ ở cỡ tối thiểu và in cảnh báo `⚠️` ra log (Studio thấy trong log job), **không dừng dựng**.
- **Khối chữ phía dưới neo đáy**: phụ đề, giá, CTA, mũi tên không được vượt `SAFE_BOTTOM`. Nhiều dòng hơn thì đẩy lên trên, không tràn xuống.
- **Khối chữ phía trên** (hook, nhãn cảnh, dòng minh bạch, tên chuỗi bài tập) bắt đầu từ `SAFE_TOP`. Dev được dời khung ảnh sản phẩm / khung clip (`_paste_fit` box, `VIDEO_BOX`) để đủ chỗ, miễn không còn chữ nằm ngoài vùng. Ở cảnh sản phẩm, **ưu tiên dời ảnh xuống** (dải y 1440–1570 đang trống) hơn là thu nhỏ ảnh; hook/nhãn không được đè lên nhãn in trên sản phẩm và phải đọc được trong 3 giây đầu.
- **Ảnh sản phẩm và cột nút (gợi ý MKTG, không bắt buộc)**: ở cảnh sản phẩm, ảnh hiện trải tới x ≈ 964 trong dải y 1053–1440, nên ảnh đại diện/nút tim che góc dưới phải của sản phẩm. Dev có thể giữ khung ảnh ngoài cột nút nếu không làm ảnh nhỏ đi nhiều. Đây không phải lỗi hạng mục F (chỉ áp cho chữ/khung vẽ).
- **CTA**: giữ nguyên chữ "BẤM GIỎ HÀNG VÀNG" + "BÊN DƯỚI" (C-0003-3), 2 dòng trong cùng một khung vàng `#FFC300`, cỡ 56 như cũ (dòng dài nhất rộng 704 px, vừa khoảng 88–870). Bề rộng khung vàng theo dòng 1, dòng 2 canh giữa trong khung, mũi tên vàng chỉ xuống sát ngay dưới khung. Giá đỏ phía trên khung vàng. Ảnh sản phẩm ở cảnh CTA **dời xuống** để nhường chỗ cho dòng minh bạch, không thu nhỏ; nên đặt ảnh cùng tâm với khối chữ dưới (≈ x 479 trên ảnh tĩnh) để ảnh, giá, khung vàng, mũi tên thẳng một trục (MKTG xác nhận bằng khung hình V-1).
- **Dòng minh bạch** "Video có gắn link tiếp thị liên kết": dời xuống y ≥ `SAFE_TOP`, có nền tối hoặc viền đậm để đọc được trên nền mờ (hiện chỉ cao khoảng 13 px trên khung 540, chữ trắng trên nền mờ). Cỡ chữ **không nhỏ hơn hiện tại** (30).
- **Mũi tên CTA và thẻ giỏ hàng**: thẻ giỏ hàng của TikTok nằm ngay trên tên kênh, đúng chỗ đáy khối CTA/mũi tên đang neo (≤ `SAFE_BOTTOM`). Vị trí thật của thẻ chưa đo (R-2). Khi có ảnh chụp (V-6): đầu mũi tên phải nằm ngay trên mép trên của thẻ, không bị thẻ che, và theo chiều ngang nằm trong khoảng mép trái–mép phải của thẻ. Nếu lệch thì chỉ đổi hằng số (`SAFE_BOTTOM`, tâm khối dưới), không đổi cấu trúc.

---

## Các phương án

| # | Phương án | Chọn | Lý do |
|---|-----------|------|-------|
| A | Hằng số vùng an toàn dùng chung + hàm vẽ canh giữa trong khoảng an toàn (dịch trái ở phần dưới) + `_pill` tự xuống dòng + bù zoom | ⭐ | Sửa tận gốc cho mọi chữ (GP-002), một chỗ định nghĩa. Giữ cỡ chữ CTA 56. Không đổi cách dựng (vẫn zoom ảnh tĩnh), ít rủi ro hồi quy |
| B | Chỉ sửa khung CTA (ngắt dòng hoặc thu nhỏ) | - | Số đo cho thấy phụ đề cảnh story (đến x ≈ 1030), giá, hook, nhãn cảnh sản phẩm, chữ video bài tập cũng ra ngoài vùng. Sửa một chỗ thì lỗi lặp lại ở chỗ khác (GP-002) |
| C | Canh giữa đối xứng: chừa cả hai bên bằng bề rộng cột nút (khoảng an toàn 190–890 ở phần dưới) | - | Mất thêm 130 px bên trái. Phụ đề 13–15 từ thành 3–4 dòng, che nhiều ảnh hơn, chữ phải nhỏ lại |
| D | Tách chữ ra lớp riêng không zoom (overlay sau `zoompan`, như `exercise.py` đang làm) | - | Gọn về hình học (không cần bù 6 %) nhưng phải tách mỗi hàm cảnh thành 2 ảnh và đổi filter của `render_video`; chữ đứng yên trên nền chuyển động là đổi "cảm giác" mọi video. Thay đổi lớn hơn mức cần cho lỗi này. Có thể xem lại sau nếu MKTG muốn chữ đứng yên |

---

## Chi phí (P02)

| Việc | Tốn quota / tiền? | Nguồn |
|---|---|---|
| Sửa code vẽ chữ, dựng video mới | $0 (Pillow + FFmpeg local) | `video-render.md` §Cost |
| Dựng lại video cũ (Studio "Dựng lại video" khi không sửa lời đọc, `--rerender`, `--exercise-rerender`) | $0, **0 lượt Gemini TTS**: `revoice_changed` chỉ đọc lại câu có `line != audio_line` | `demo.py` `render_only`, `revoice_changed`; `exercise.py` `rerender` |
| `scripts/check_safe_zone.py` | $0, không gọi mạng | — |
| Groq, Gemini | Không dùng | — |
| Ảnh chụp video đã đăng có thẻ giỏ hàng (V-6) | $0, không đăng bài mới: chụp video Bột mè đen đã đăng | — |

---

## Thay đổi cấu trúc

### Dữ liệu

| Đối tượng | Trước | Sau | Lý do |
|-----------|-------|-----|-------|
| Hằng số trong `demo.py` | Không có; số cứng rải rác (`W - 140`, y = 110/120/170/230/1170/1330/1460, `0.06` trong `zoompan`) | `SAFE_TOP`, `SAFE_BOTTOM`, `SAFE_SIDE`, `BUTTON_COL_X`, `BUTTON_COL_TOP`, `ZOOM_MAX` + hàm tính khoảng vẽ | Một nguồn duy nhất (C-0003-2) |
| `exercise.py` | Số cứng y = 120/180/300/1310/1330, `VIDEO_BOX = (360, 920)` | Dùng hằng số của `demo` (đã `import demo`); `VIDEO_BOX` có thể đổi để đủ chỗ | Cùng quy tắc cho mọi video |
| `script.json`, `product.json`, Sheet | — | **Không đổi** | Dựng lại video cũ không cần chuyển đổi dữ liệu |
| `.env` | — | **Không thêm biến** | Vùng an toàn là quy tắc cố định, không cho người vận hành chỉnh |

### Luồng hệ thống

Không đổi luồng. Chỉ đổi bên trong bước `render_video` (và `exercise.render`): vị trí, bề rộng, số dòng của chữ.

### Luồng dữ liệu

Không đổi.

### Thao tác người dùng

| Thao tác | Trước | Sau |
|---|---|---|
| Video sản phẩm đang chờ duyệt trên Studio (nhãn **Chờ duyệt** / **Cần ảnh**) | Chữ CTA lấn cột nút | Bấm **Dựng lại video** (không cần sửa gì). 1–2 phút, $0, không tốn lượt giọng. Xem lại rồi mới **Duyệt & lưu** |
| Video bài tập đang chờ duyệt (Studio hiện **Chỉ xem**) | — | `.venv/bin/python demo.py --exercise-rerender storage/videos/<thư mục>` ($0) |
| Video **đã đăng** (OMNIEAR 2026-10-20, Bột mè đen 2026-11-11) | — | Không sửa được trên TikTok. Khuyến nghị giữ nguyên (xem câu hỏi mở 3) |
| Video đã duyệt và đã chuyển lên Drive (thư mục local đã xoá) | — | Không dựng lại được bằng Studio. Muốn sửa phải tạo lại video (tốn lượt giọng nếu dùng Gemini) |

---

## Kế hoạch công việc

| # | Việc | Vai trò | Input | Output | Vị trí |
|---|------|---------|-------|--------|--------|
| 1 | Thêm hằng số vùng an toàn + hàm tính khoảng vẽ (có tham số zoom); `zoompan` đọc `ZOOM_MAX` | Dev | DR này | Code | `demo.py` |
| 2 | `_text_block`, `_pill` nhận khoảng an toàn: canh giữa trong khoảng, `_pill` xuống dòng tối đa 2 dòng, giảm cỡ, cảnh báo `⚠️` khi vẫn tràn; hỗ trợ neo đáy | Dev | #1 | Code | `demo.py` |
| 3 | Sắp lại `_scene_story`, `_scene_product`, `_scene_cta` (CTA 2 dòng, mũi tên theo tâm khung, dòng minh bạch dưới `SAFE_TOP`, dời khung ảnh nếu cần) | Dev | #2 | Code | `demo.py` |
| 4 | Sắp lại `_overlay` và `VIDEO_BOX` của video bài tập theo cùng hằng số (không zoom) | Dev | #2 | Code | `exercise.py` |
| 5 | Script kiểm: dựng từng loại cảnh với chữ thường và chữ dài nhất (bảng D-n), đo khung chữ thực vẽ, quy ra khung cuối (×`ZOOM_MAX`), in từng phần tử + toạ độ + giới hạn + **cỡ chữ thực tế** + PASS/FAIL, exit 1 nếu có FAIL. Thêm chế độ `--frames <thư mục review-frames>` vẽ đường biên vùng an toàn lên khung hình để người xem bằng mắt | Dev | #1–4 | Script | `scripts/check_safe_zone.py` |
| 6 | Review: không còn toạ độ chữ ghi cứng ngoài hằng số; `zoompan` dùng `ZOOM_MAX`; không gọi TTS/LLM trong đường dựng lại; không đụng `app.html`, `studio.py` | Reviewer | #1–5 | Ghi chú review | DR §Kết quả |
| 7 | Chạy bảng D-n bằng script #5; chạy V-n trên **bản sao** thư mục video (tắt Drive: không đặt `DRIVE_FOLDER_ID` hoặc dùng `--keep-local`; không đụng Sheet) | Tester | #1–5 | Kết quả D-n, V-n nguyên văn | DR §Kết quả |
| 8 | Xem khung hình có vẽ đường biên (V-1…V-3), đánh giá: chữ dịch trái có lệch mắt không, CTA 2 dòng có rõ không, ảnh/giá/khung vàng/mũi tên cảnh CTA có thẳng trục không, dòng minh bạch có đọc được không, ảnh sản phẩm có bị thu nhỏ quá không, cỡ chữ thực tế (in từ script #5) có chấp nhận được không | MKTG | #7 | Nhận xét | DR §Kết quả |
| 8b | Đo ảnh chụp thẻ giỏ hàng (V-6): mép trên, mép trái, mép phải của thẻ, quy đổi ra khung video; đối chiếu với đầu mũi tên CTA. Lệch thì đề xuất hằng số mới cho Dev | MKTG + BA | Ảnh chụp của người dùng | Số đo + đề xuất | DR §Kết quả |
| 9 | Cập nhật tài liệu SSoT (bảng dưới), đối chiếu tên hằng số, tên script, nhãn nút với code | BA | #1–8 | Docs | xem §SSoT |

---

## Rủi ro và giả định

| # | Loại | Nội dung | Ảnh hưởng | Cách xử lý |
|---|------|----------|-----------|------------|
| R-1 | Rủi ro | Số đo chỉ từ 1 máy iPhone | Máy khác có cột nút cao/thấp hơn, cắt mép khác | Đã chừa lề (12–53 px). V-6 xem thử trên máy người vận hành. Hằng số ở một chỗ, đổi một lần là áp cho mọi video |
| R-2 | Rủi ro | Thẻ giỏ hàng nằm ngay trên tên kênh, đúng chỗ đáy khối CTA/mũi tên đang neo | Đầu mũi tên, giá, phụ đề có thể bị thẻ che, hoặc mũi tên chỉ lệch khỏi thẻ | **Điều kiện đóng DR** (không chặn Dev): V-6 đo thẻ từ ảnh chụp video Bột mè đen đã đăng. Có số đo mới thì chỉ đổi hằng số |
| R-3 | Rủi ro | Phần dưới dịch trái ~60 px | Nhìn hơi lệch so với ảnh | MKTG đã chấp nhận phương án A. Cảnh CTA nên dời ảnh về cùng tâm ≈ x 479; MKTG xác nhận bằng khung hình V-1 ở #8 |
| R-4 | Rủi ro | Khoảng hẹp hơn → phụ đề nhiều dòng hơn, chữ trên cùng thấp hơn | Chữ che ảnh nhiều hơn, ảnh sản phẩm nhỏ đi | Neo đáy, giảm cỡ có giới hạn; MKTG xem ở #8 |
| R-5 | Rủi ro | Thay đổi bố cục làm hỏng `--rerender` của thư mục cũ | Không dựng lại được video đang chờ | D-10, D-11, V-4 chạy trên bản sao thư mục cũ |
| A-1 | Giả định | TikTok giữ bố cục giao diện như ảnh chụp 2026-10-20. Số đo chỉ đúng với bài **không có thẻ giỏ hàng** và caption **2 dòng** (1–2 câu, quy tắc J của MKTG). Caption dài hơn đẩy khối caption lên cao hơn y ≈ 1591 | Hằng số lỗi thời hoặc thiếu lề dưới | V-6 chụp thêm video có caption dài nhất kênh đang dùng. Đo lại khi thấy chữ bị che; chỉ đổi hằng số |
| A-2 | Giả định | Không có chữ nào khác ngoài các hàm đã liệt kê vẽ lên video (đã đọc toàn bộ `demo.py` 594–822 và `exercise.py` 353–457) | Bỏ sót | Reviewer `grep` `draw.` / `_text_block` / `_pill` / `polygon` trong repo |

---

## Ràng buộc mới

| ID | Ràng buộc | Lý do | Phạm vi | Điều kiện gỡ |
|----|-----------|-------|---------|--------------|
| C-0003-1 | Mọi chữ, khung, mũi tên vẽ lên video phải nằm trong vùng an toàn **tính trên khung cuối** (sau zoom): y trong [`SAFE_TOP`, `SAFE_BOTTOM`], x trong [`SAFE_SIDE`, 1080 − `SAFE_SIDE`], và x ≤ `BUTTON_COL_X` với phần nằm ở y ≥ `BUTTON_COL_TOP` | Chữ bị che thì người xem không đọc được, CTA mất tác dụng | `demo.py`, `exercise.py`, mọi cảnh mới sau này | Khi TikTok đổi giao diện: đo lại, viết DR mới đổi số |
| C-0003-2 | Hằng số vùng an toàn và `ZOOM_MAX` chỉ định nghĩa một lần trong `demo.py`. Hàm vẽ và `zoompan` đọc từ đó, không ghi số cứng | Tránh lệch giữa các chỗ (nguyên nhân của lỗi này) | `demo.py`, `exercise.py` | — |
| C-0003-3 | Cảnh CTA luôn có: chữ "BẤM GIỎ HÀNG VÀNG" và "BÊN DƯỚI", mũi tên vàng chỉ xuống, dòng "Video có gắn link tiếp thị liên kết" | Ý nghĩa CTA và nghĩa vụ minh bạch tiếp thị liên kết | `_scene_cta` | DR mới |
| C-0003-4 | Sửa bố cục chữ không được làm đường dựng lại (`--render-only` không sửa lời đọc, `--rerender`, `--exercise-rerender`) gọi TTS hay LLM | Sửa video cũ phải $0 | `demo.py`, `exercise.py` | — |

supersedes: — (không gỡ ràng buộc cũ; C-0001-1…4 vẫn giữ)

---

## Tài liệu SSoT bị ảnh hưởng

| Tài liệu | Nội dung cập nhật | Đã cập nhật |
|---|---|:-:|
| `docs/specs/architecture/capabilities/video-render.md` | Thay bảng "Text Overlay Rules" (y = 100/1300/1420, đã lỗi thời) bằng mục "Vùng an toàn" (hằng số, nguồn số đo, quy tắc canh giữa/neo đáy, CTA 2 dòng, cách kiểm) | [ ] |
| `.claude/CLAUDE.md` | §Luồng `demo.py`: nhắc hằng số vùng an toàn và `scripts/check_safe_zone.py`; §Lệnh thường dùng: thêm lệnh kiểm | [ ] |
| `docs/operations/huong-dan-van-hanh-hang-ngay.md` | Bước 5 / mục 6: "Chữ bị nút TikTok che → bấm **Dựng lại video**, không tốn lượt giọng"; mục 4b: lệnh `--exercise-rerender` để cập nhật chữ video bài tập | [ ] |
| `TODO.md` | §5: đánh dấu lỗi CTA đã xử lý (DR-0003); §1 bước 4 "chữ tránh vùng UI TikTok" ghi rõ theo DR-0003 | [ ] |
| `.env.example` | Không đổi (không thêm biến) | — |

---

## Hoàn thành khi (DoD)

### Bảng quyết định cho code

Mọi toạ độ là **khung cuối 1080×1920 sau zoom 1,06** (với `demo.py`) hoặc khung cuối không zoom (với `exercise.py`). Giới hạn: trên ≥ 240, dưới ≤ 1570, trái ≥ 60, phải ≤ 1020; phần ở y ≥ 1000 thì phải ≤ 890.
Cách kiểm chung "script": `.venv/bin/python scripts/check_safe_zone.py` in dòng của phần tử tương ứng là PASS, kèm toạ độ khung chữ.

| # | Loại | Điều kiện đầu vào | Kết quả mong đợi | Cách kiểm |
|---|------|-------------------|------------------|-----------|
| D-1 | Bình thường | Cảnh CTA có giá `86.247đ` | Khung vàng 2 dòng "BẤM GIỎ HÀNG VÀNG" / "BÊN DƯỚI", **cỡ chữ 56** (script in ra); bề rộng khung theo dòng 1, dòng 2 canh giữa; mép phải ≤ 890, mép trái ≥ 60; mũi tên chỉ xuống, sát dưới khung, tâm mũi tên trùng tâm khung vàng (±2 px), đáy mũi tên ≤ 1570; khung giá đỏ nằm trên khung vàng | script + xem `_scene` PNG |
| D-2 | Bình thường | Cảnh CTA không có giá (`price` trống) | Như D-1, không có khung đỏ, không có khoảng trống lạ | script |
| D-3 | Bình thường | Dòng "Video có gắn link tiếp thị liên kết" ở cảnh CTA | Đỉnh chữ ≥ 240; cỡ chữ ≥ 30 (script in ra); có nền tối hoặc viền đậm; ảnh sản phẩm CTA được dời xuống, không nhỏ hơn hiện tại (so kích thước khung ảnh trước/sau) | script + xem PNG |
| D-4 | Bình thường | Cảnh sản phẩm đầu có hook "Chán vị nhạt nhẽo?"; cảnh sản phẩm có nhãn "Mè đen + Đậu đen"; cảnh sản phẩm có giá | Hook, nhãn: đỉnh ≥ 240, hai mép trong [60, 1020]. Khung giá: đáy ≤ 1570, mép phải ≤ 890 | script |
| D-5 | Bình thường | Cảnh story có hook "Mẹ nghe chưa rõ?" + phụ đề "Giờ mẹ nghe rõ tiếng con rồi, vui quá." | Hook đỉnh ≥ 240; phụ đề mép phải ≤ 890, đáy ≤ 1570 | script |
| D-6 | Biên | Nhãn cảnh sản phẩm dài: "Khuếch đại âm thanh môi trường rõ ràng" (hiện rộng 33–1046 sau zoom) | Khung xuống 2 dòng hoặc nhỏ chữ; hai mép trong [60, 1020] | script |
| D-7 | Biên | Giá dài `12.990.000đ` ở cảnh sản phẩm và cảnh CTA | Mép phải ≤ 890, đáy ≤ 1570 | script |
| D-8 | Biên | Phụ đề story 16 từ: "Bột mè đen kết hợp đậu đen xanh lòng, nguyên liệu thật sự rất chỉn chu." | Nhiều dòng hơn nhưng đáy ≤ 1570 (neo đáy), mép phải ≤ 890 | script |
| D-9 | Biên | Hook 12 từ: "Chán vị nhạt nhẽo khi ăn sáng mỗi ngày mà không biết đổi món gì?" ở cảnh sản phẩm và cảnh story | Đỉnh ≥ 240, hai mép trong [60, 1020], không đè lên phụ đề | script + xem PNG |
| D-10 | Lỗi | Nhãn là 1 từ dài không ngắt được: "Siêuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu" | Vẽ ở cỡ tối thiểu, log có dòng `⚠️` nêu phần tử bị tràn; quá trình dựng **không dừng** (exit 0) | Chạy script với chuỗi này, đọc log + exit code |
| D-11 | Bình thường | Video bài tập: cảnh động tác (`ex_move`/khác `ex_end`) và cảnh kết (`ex_end` có `careful`) của Bát Đoạn Cẩm | Tên chuỗi, hook, "Hình minh hoạ", khung vàng, chữ màn hình, dòng "Bài vận động nhẹ…": đỉnh ≥ 240, đáy ≤ 1570, mép phải ≤ 890 với phần ở y ≥ 1000 | script (lớp chữ RGBA, đo vùng alpha > 0) |
| D-12 | Hồi quy | `zoompan` sau khi sửa | Biểu thức zoom dùng `ZOOM_MAX`; đổi `ZOOM_MAX` thì cả zoom và khoảng vẽ cùng đổi | Reviewer đọc code; Tester đặt tạm `ZOOM_MAX=1.10` trong bản sao, chạy script → vẫn PASS |
| D-13 | Hồi quy | Bản sao `20261111_114841_bot-me-den`, chạy `demo.py --render-only <bản sao>` không sửa gì | Không gọi TTS: md5 của `audio_0..3.mp3` trước = sau; log không có dòng gọi Gemini/edge; `video.mp4` mới, thời lượng lệch ≤ 0,1 s so với bản cũ (18,0 s); thư mục có nhãn **Chờ duyệt** | So md5, đọc log, `review_frames.py` → `facts.json` |
| D-14 | Hồi quy | Bản sao thư mục OMNIEAR (story, có `canh_1/2/5.png`), `demo.py --rerender <bản sao> --skip-approval --keep-local` (không đặt `DRIVE_FOLDER_ID`) | Dựng xong, không gọi TTS/Groq, md5 audio không đổi | So md5, đọc log |
| D-15 | Hồi quy | Bản sao `20261112_143304_baitap_bdc_00_gioithieu`, `demo.py --exercise-rerender <bản sao>`, trả lời `n` ở bước duyệt | Dựng xong, không gọi TTS, md5 audio không đổi | So md5, đọc log |
| D-16 | Hồi quy | `app.html`, `backend/app/api/studio.py` | Không đổi | `git diff --stat origin/main` không có hai file này |

### Bảng quyết định cho tài liệu

| # | Tài liệu | Kiểu thay đổi | Kết quả mong đợi | Cách kiểm |
|---|---|---|---|---|
| DD-1 | `video-render.md` | Sửa | Có mục "Vùng an toàn" với đúng tên + giá trị hằng số trong code, nguồn số đo (ảnh chụp 2026-10-20), giả định chưa đo thẻ giỏ hàng; bỏ bảng Text Overlay Rules cũ | So với `grep -n "SAFE_\|ZOOM_MAX" demo.py` |
| DD-2 | `huong-dan-van-hanh-hang-ngay.md` | Thêm | Người không code đọc được: thấy chữ bị nút che → bấm **Dựng lại video** (đúng nhãn trên Studio), không tốn lượt giọng; video bài tập dùng lệnh `--exercise-rerender` | Đối chiếu nhãn với `backend/app/web/studio.html` |
| DD-3 | `.claude/CLAUDE.md` | Sửa | Có lệnh `scripts/check_safe_zone.py` đúng tên và cờ | Chạy thử lệnh ghi trong tài liệu |
| DD-4 | `TODO.md` | Sửa | §5 ghi lỗi CTA đã xử lý theo DR-0003, kèm câu hỏi mở còn lại (đo thẻ giỏ hàng) nếu chưa trả lời | Đọc lại |

### Kiểm tra đầu-cuối (E2E)

Khung hình từ `scripts/review_frames.py` rộng 540 px (một nửa), nên giới hạn trên khung hình là: trên ≥ 120, dưới ≤ 785, trái ≥ 30, phải ≤ 510; phần ở y ≥ 500 thì phải ≤ 445. Chạy `scripts/check_safe_zone.py --frames storage/review-frames/<thư mục>` để vẽ đường biên rồi xem bằng mắt.

| # | Việc kiểm | Cách làm | Mong đợi | Kết quả | Ngày |
|---|---|---|---|---|---|
| V-1 | CTA video Bột mè đen | Chép `storage/videos/20261111_114841_bot-me-den` thành bản sao; mở Studio, chọn bản sao, bấm **Dựng lại video** (không sửa gì); `review_frames.py <bản sao>`; vẽ đường biên | `scene_4_start`, `scene_4_mid`: khung vàng 2 dòng, mép phải ≤ 445, mũi tên đáy ≤ 785, dòng minh bạch đỉnh ≥ 120; trước khi sửa là x≈5–535 (marketing-review F) | — | — |
| V-2 | Cảnh sản phẩm Bột mè đen | Như V-1, xem `scene_1..3` | Hook/nhãn đỉnh ≥ 120; giá đáy ≤ 785, mép phải ≤ 445 | — | — |
| V-3 | Phụ đề story OMNIEAR | Bản sao thư mục OMNIEAR, `--rerender --skip-approval --keep-local`, trích khung | `scene_5_*` ("Giờ mẹ nghe rõ…"): mép phải ≤ 445, đáy ≤ 785 | — | — |
| V-4 | Video bài tập mở đầu | Bản sao thư mục `..._baitap_bdc_00_gioithieu`, `--exercise-rerender`, trích khung (`review_frames.py` dựa vào `segments`; nếu không chạy được với video bài tập thì dùng ffmpeg trích 1 khung/cảnh) | Mọi chữ trong vùng | — | — |
| V-5 | Không tốn quota | Trong V-1, V-3, V-4 | md5 `audio_*.mp3` không đổi; Studio không hiện thông báo dùng lượt Gemini | — | — |
| V-6 | **Điều kiện đóng DR** (không chặn Dev): đo thẻ giỏ hàng | Người dùng mở video Bột mè đen **đã đăng** (có thẻ giỏ hàng) trên điện thoại, chụp màn hình lúc cảnh CTA; chụp thêm một video có caption dài nhất kênh đang dùng. MKTG + BA đo mép trên, mép trái, mép phải của thẻ, quy đổi ra khung video (công thức ở §Bối cảnh) và đặt lên khung V-1 | Đầu mũi tên CTA (bản mới) nằm ngay trên mép trên của thẻ, không bị thẻ che, và theo chiều ngang nằm trong khoảng mép trái–mép phải của thẻ; giá, phụ đề không bị thẻ hay caption dài che. Không đạt → chỉ đổi hằng số, chạy lại D-n và V-1 | — | — |

### Cổng chất lượng

- [ ] Mọi dòng D-n, DD-n, V-1…V-5 đã kiểm, kết quả ghi nguyên văn từ Tester
- [ ] V-6 (thẻ giỏ hàng) đã đo và đạt: bắt buộc để đóng DR, không chặn Dev bắt đầu
- [ ] `scripts/check_safe_zone.py` exit 0 với bộ chuỗi chuẩn
- [ ] Không hồi quy dựng lại (D-13…D-15), không tốn lượt TTS
- [ ] Không vi phạm C-0001-1…4
- [ ] Tài liệu SSoT đã cập nhật và khớp code

---

## Kết quả

### Phase 2: Dev

| # | Việc | Kết quả | Ghi chú |
|---|------|---------|---------|
| 1–5 | — | — | — |

### Phase 3: Review

| # | Góp ý | Cách xử lý |
|---|-------|-----------|
| — | — | — |

### Phase 4: Test

(chép nguyên văn từ báo cáo Tester)

---

## Liên quan

| Loại | Liên kết |
|------|----------|
| DR liên quan | DR-0001 (Studio "Dựng lại video", C-0001-4 không đổi `app.html`) |
| Review marketing | `storage/videos/20261111_114841_bot-me-den/marketing-review.md` (F, đề xuất #8) |
| Nguồn số đo | `storage/videos/20261020_145409_omniear-tai-nghe-thu-va-khuech-dai-am-th/Ảnh màn hình 2026-10-20 lúc 15.25.14.png` |
| Code | `demo.py` (`_text_block`, `_pill`, `_scene_story`, `_scene_product`, `_scene_cta`, `render_video`/`zoompan`), `exercise.py` (`_overlay`, `VIDEO_BOX`, `render`) |
