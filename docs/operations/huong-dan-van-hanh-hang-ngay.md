# Hướng dẫn vận hành hằng ngày

Dành cho người đăng video TikTok Shop Affiliate hằng ngày. Không cần biết lập trình: chỉ cần làm theo từng bước, gõ đúng lệnh được cho sẵn.

Áp dụng **sau khi TikTok đã duyệt app** TT Content Publisher.

---

## 1. Ai làm việc gì

Hệ thống hiện tại **không tự đăng video**. Máy lo phần viết kịch bản, đọc giọng và dựng video. Người lo chọn sản phẩm, duyệt và bấm đăng.

| Việc | Ai làm | Ghi chú |
|---|---|---|
| Chọn sản phẩm trên TikTok Shop | **Người** | Mỗi tuần 5–10 sản phẩm |
| Dán link sản phẩm vào Google Sheet | **Người** | Sheet "Tiktok" |
| Điền tên, giá, ảnh, số đã bán, ý chính | Máy | Đọc từ trang sản phẩm TikTok Shop |
| Kiểm tra lại các ý máy điền | **Người** | Bắt buộc |
| Viết kịch bản, caption, hashtag | Máy (AI) | Tự động |
| Đọc giọng | Máy (AI) | Tự động |
| Ảnh nhân vật cho video kiểu tiểu phẩm | **Người**, dùng Gemini | Bỏ qua được nếu chọn video kiểu đơn giản |
| Dựng video | Máy | Tự động |
| Duyệt video trước khi đăng | **Người** | Bắt buộc |
| Gửi video vào điện thoại | Máy | Bấm 1 nút trên trang web |
| Gắn giỏ hàng, bật nhãn AI, bấm Đăng | **Người** | Trên app TikTok |
| Ghi kết quả | **Người** | Sau 48 giờ |

---

## 2. Việc làm một lần, khi TikTok vừa duyệt app

Nhờ người phụ trách kỹ thuật làm phần này, hoặc tự làm theo đúng thứ tự.

1. Vào [developers.tiktok.com](https://developers.tiktok.com), mở app, chọn **Production**.
2. Chép **Client key** và **Client secret** của Production.
3. Mở file `.env` trong thư mục dự án, thay 2 dòng sau bằng giá trị vừa chép, rồi lưu:
   ```
   TIKTOK_CLIENT_KEY=...
   TIKTOK_CLIENT_SECRET=...
   ```
4. Trong Production → **Login Kit** → tab **Web**, kiểm tra Redirect URI là:
   ```
   https://chungkhoantony1983.github.io/tt-affiliate/app.html
   ```

> **Không** gửi Client secret cho ai, không chụp màn hình file `.env`.

Key Sandbox chỉ dùng được với tài khoản thử. Sau bước này, app dùng được với tài khoản thật.

### Kết nối Google Drive (làm một lần)

Video đã duyệt được tải lên Google Drive, mỗi sản phẩm một thư mục con, rồi xoá khỏi máy cho nhẹ. Chương trình đăng nhập Drive bằng **tài khoản Google của bạn**, vì tài khoản bot đọc Google Sheet không có dung lượng Drive.

1. Vào [console.cloud.google.com](https://console.cloud.google.com), chọn project **omni-affiliate**.
2. **APIs & Services → Library**, tìm **Google Drive API**, bấm **Enable**.
3. **APIs & Services → OAuth consent screen**: thêm email của bạn vào **Test users**, rồi bấm **Publish app** để chuyển sang **In production**. Nếu để ở Testing, cứ 7 ngày lại phải đăng nhập lại.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**, loại **Desktop app**. Bấm **Download JSON**, đổi tên thành `google-oauth-client.json`, bỏ vào thư mục dự án.
5. Mở file `.env`, thêm dòng:
   ```
   DRIVE_FOLDER_ID=18PdyjmrQD7MTqkhiR66pfYsIMAYZLEdz
   ```
6. Lần đầu duyệt video, trình duyệt sẽ mở trang đăng nhập Google. Chọn tài khoản, bấm **Continue** ở cảnh báo "Google hasn't verified this app" (app của chính bạn), cho phép. Từ lần sau không phải đăng nhập nữa.

> Không gửi `google-oauth-client.json`, `google-drive-token.json` cho ai.

---

## 3. Mỗi buổi làm việc: bật máy chủ

Làm một lần ở đầu buổi.

1. Mở ứng dụng **Terminal** (bấm `Cmd + Space`, gõ `Terminal`, Enter).
2. Dán lệnh sau, Enter:
   ```bash
   cd ~/Documents/project/tiktok_affiliate
   ```
3. Dán lệnh sau, Enter:
   ```bash
   .venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
   ```
4. Thấy dòng `Uvicorn running on http://127.0.0.1:8000` là xong. **Để nguyên cửa sổ này**, không tắt trong suốt buổi.

Để chạy các lệnh khác ở mục 4, mở thêm một cửa sổ Terminal mới (`Cmd + N`) và gõ lại lệnh `cd` ở bước 2.

Hết buổi: bấm vào cửa sổ máy chủ, nhấn `Ctrl + C`.

---

## 4. Quy trình mỗi video

### Bước 1. Chọn sản phẩm

1. Mở app TikTok → **TikTok Shop** → **Sàn tiếp thị liên kết** (Affiliate Center).
2. Chọn sản phẩm:
   - Giá 100.000–500.000 ₫.
   - Hoa hồng từ 10% trở lên.
   - Đã có người mua, càng nhiều càng tốt.
   - Hợp với kênh: nhà cửa, công nghệ, đồ bếp, phụ kiện ô tô.
3. Bấm **Thêm vào showcase**. Không có bước này thì lúc đăng sẽ không gắn được giỏ hàng.
4. Trên trang sản phẩm, bấm **Chia sẻ → Sao chép liên kết**.

### Bước 2. Dán link vào Google Sheet

Mở Google Sheet **Shopee_Tiktok_Affiliate_Management**, sheet **Tiktok**. Mỗi dòng là một sản phẩm. Chỉ cần điền 2 ô:

| Cột | Ghi gì | Ví dụ |
|---|---|---|
| `name` | Tên ngắn gọn để dễ nhận ra | `Trà oolong` |
| `product_url` | Link vừa sao chép | `https://vt.tiktok.com/...` |

Các ô khác để trống, máy sẽ tự điền. Ô nào bạn đã điền thì máy giữ nguyên.

Muốn máy điền ngay để xem trước, trong cửa sổ Terminal thứ hai chạy:
```bash
.venv/bin/python demo.py --sheet --fill-only
```

Máy điền: `price` (giá thấp nhất lúc đọc), `images` (3 ảnh), `sold_count`, `category`, `selling_points`, `notes`.

**Bắt buộc đọc lại `selling_points` và `notes`.** Máy chỉ lấy từ mô tả của người bán, nhưng người bán có thể quảng cáo quá lời, ví dụ "không gây mất ngủ". Ý nào không chắc chắn thì xoá đi.

Lưu ý:
- `commission_pct` (% hoa hồng) máy **không** đọc được vì chỉ hiện trong Affiliate Center. Tự điền nếu muốn theo dõi.
- Giá trên TikTok Shop thay đổi theo ngày. Không muốn video nhắc giá thì ghi `0` vào ô `price`. Đừng xoá trống, vì máy sẽ tự điền lại.
- Sản phẩm sức khoẻ, thực phẩm, làm đẹp: kiểm tra ô `notes` có ghi những điều không được nói, ví dụ "không chữa bệnh".
- Muốn bỏ qua một sản phẩm: ghi `skip` vào ô `status`.

### Bước 3. Tạo video

Trong cửa sổ Terminal thứ hai, chọn một trong hai kiểu.

**Kiểu đơn giản** (chỉ dùng ảnh sản phẩm):
```bash
.venv/bin/python demo.py --sheet --style simple
```

**Kiểu tiểu phẩm** (có nhân vật, phải tự tạo ảnh bằng Gemini ở bước 4):
```bash
.venv/bin/python demo.py --sheet
```

Máy làm lần lượt từng dòng có `status` trống, và tự điền các ô còn trống trước khi làm.

Giọng đọc được chọn tự động theo cột `category` và tên sản phẩm:

| Sản phẩm | Giọng |
|---|---|
| Điện tử, công nghệ, máy móc, dụng cụ, ô tô/xe, thể thao, tập luyện | Nam Hà Nội |
| Sức khỏe, gia đình, mẹ và bé, người già, quà tặng, tình cảm, và mọi loại khác | Nữ Sài Gòn |

Muốn đổi giọng cho một sản phẩm thì sửa ô `category`, ví dụ ghi `Điện tử` để dùng giọng nam. Video nằm trong thư mục `storage/videos/<ngày giờ>_<tên sản phẩm>/`.

Máy tự ghi vào cột `status`:

| Giá trị | Nghĩa |
|---|---|
| `done` | Đã duyệt video, chờ đăng |
| `needs_images` | Kiểu tiểu phẩm, đang chờ ảnh nhân vật: làm bước 4 |
| `skip` | Bạn tự ghi, máy bỏ qua |

### Bước 4. Ảnh nhân vật (chỉ với kiểu tiểu phẩm)

Nếu Terminal báo `Cần ảnh nhân vật cho cảnh ...`:

1. Mở file `prompts.txt` trong thư mục video vừa tạo.
2. Mở [gemini.google.com](https://gemini.google.com), tạo **một** cuộc trò chuyện mới.
3. Dán lần lượt từng đoạn prompt. Từ đoạn thứ 2, thêm câu: *"Giữ nguyên các nhân vật giống hệt ảnh trước."*
4. Tải từng ảnh về, đổi tên đúng như dòng **Lưu thành** (ví dụ `canh_1.png`), bỏ vào thư mục video đó.
5. Chạy lệnh có sẵn ở cuối hướng dẫn trong `prompts.txt`, dạng:
   ```bash
   .venv/bin/python demo.py --rerender storage/videos/<tên thư mục>
   ```

Không dùng hình người nổi tiếng hay nhân vật phim: TikTok có thể gỡ video hoặc khoá tính năng tiếp thị liên kết.

### Bước 5. Duyệt video

Máy tự mở video và hiện kịch bản trên Terminal. Kiểm tra:
- Lời nói đúng sự thật, không hứa quá mức, không bịa thông số.
- Không sai chính tả trên màn hình.
- Giá đúng, nếu có hiện giá.

Gõ `y` rồi Enter để đồng ý, `n` để bỏ. Đồng ý thì máy:
- tạo file `post.txt` cạnh video, có caption để dán;
- tự ghi `done` vào Google Sheet;
- tải cả thư mục lên Google Drive vào `<tên sản phẩm>/<ngày giờ>_<tên>/`, kiểm tra từng file đã lên đủ, rồi **xoá bản trên máy**. Terminal in ra link thư mục Drive.

Muốn giữ bản trên máy thì thêm `--keep-local` vào lệnh. Nếu tải lên lỗi (mất mạng, chưa kết nối Drive), máy giữ nguyên thư mục và báo lỗi, không mất gì.

Lưu ý: nghe kỹ giọng đọc. Giọng Gemini đôi khi đọc sai chữ, ví dụ "pha" thành "sờ và". Câu nào sai thì gõ `n` và chạy lại.

Gõ `n` thì `status` vẫn trống, lần chạy sau máy làm lại video mới cho sản phẩm đó. Không muốn làm lại thì ghi `skip`.

### Bước 6. Gửi video vào điện thoại

1. Mở bằng **Google Chrome**: [chungkhoantony1983.github.io/tt-affiliate/app.html](https://chungkhoantony1983.github.io/tt-affiliate/app.html)
2. Nếu Chrome hỏi quyền truy cập mạng cục bộ, chọn **Allow**.
3. Bấm **Login with TikTok**, cho phép. Mỗi lần bật lại máy chủ phải đăng nhập lại.
4. Chọn video trong danh sách, bấm phát thử.
5. Bấm **Copy caption**, rồi **Send to TikTok inbox**.
6. Chờ dòng chữ xanh **"Sent. Check the notification…"**.

> TikTok chỉ cho **tối đa 5 video đang chờ đăng trong 24 giờ**. Gửi xong thì đăng luôn, đừng gửi dồn.

### Bước 7. Đăng trên điện thoại

1. Mở app TikTok → **Hộp thư** → thông báo *"Video của bạn từ TT Content Publisher đã sẵn sàng"*.
2. Bấm vào, bấm **Tiếp**.
3. Dán caption, lấy từ `post.txt` hoặc đã copy ở bước 6. TikTok cho tối đa 5 hashtag.
4. **Thêm liên kết → Sản phẩm** → chọn đúng sản phẩm trong showcase.
5. **Cài đặt khác** → **bật nhãn "Nội dung do AI tạo"**. Bắt buộc, vì giọng đọc và hình nhân vật do AI tạo.
6. Chọn **Mọi người** được xem, bấm **Đăng**.

### Bước 8. Ghi kết quả

Sau 48 giờ, mở `TODO.md`, mục **4. Nhật ký video đã đăng**, thêm một dòng: ngày, sản phẩm, hoa hồng, kiểu hook, thời lượng, lượt xem, lượt bấm giỏ hàng, số đơn.

---

## 4b. Video bài tập hằng ngày (không bán hàng)

Mỗi ngày 1 video dạy 1 động tác, đi lần lượt theo giáo trình `content/exercise_curriculum.json`: Bát Đoạn Cẩm 8 bài, rồi Thái Cực Quyền 24 thức. Lời đọc và chữ trên màn hình lấy nguyên văn từ giáo trình, không cho AI viết lại. Giọng nam Hà Nội.

**1. Chạy lệnh:**
```bash
.venv/bin/python demo.py --exercise
```

**2. Nếu Terminal báo `chưa có clip`:** mở file prompt nó chỉ ra, ví dụ `storage/clips/bdc/prompts_01.txt`.
- Mở [gemini.google.com](https://gemini.google.com), chọn tạo video, dán từng prompt. Làm trong **cùng một cuộc trò chuyện** để nhân vật giống nhau.
- Xem kỹ từng clip: tay, chân, hướng nhìn có đúng như dòng tiếng Việt ghi bên trên prompt không. Sai thì tạo lại.
- Tải về, đổi tên đúng như dòng **Lưu thành** (`00.mp4`, `01_1.mp4`…), bỏ vào thư mục `storage/clips/bdc/`.
- `00.mp4` là tư thế chuẩn bị, chỉ làm một lần, dùng cho mọi bài.
- Hết lượt tạo video trong ngày: làm trước bước 1 và 3. Bước thiếu clip sẽ mượn clip bước liền trước.
- Chạy lại lệnh ở mục 1.

Máy dừng trước khi đọc giọng nếu chưa có clip, nên không tốn lượt Gemini.

**3. Duyệt:** như bước 5 của video sản phẩm. Gõ `y` thì máy đánh dấu bài đó đã làm và tải lên Drive vào `video_output/Bài tập - Bát Đoạn Cẩm/`. Gõ `n` thì sửa xong chạy lại không tốn lượt đọc giọng:
```bash
.venv/bin/python demo.py --exercise-rerender storage/videos/<thư mục vừa tạo>
```

**4. Đăng:** như video sản phẩm, nhưng **không gắn sản phẩm**. Vẫn bật nhãn **"Nội dung do AI tạo"**.

Clip bài tập đã làm được giữ trong `storage/clips/`, không bị xoá sau khi đăng.

---

## 5. Lịch gợi ý

| Khi nào | Việc |
|---|---|
| Mỗi ngày | 1–2 video sản phẩm: bước 3 → 7 |
| Mỗi ngày | 1 video bài tập (mục 4b); làm sẵn clip Gemini cho bài hôm sau |
| Mỗi ngày | Ghi kết quả các video đăng 2 ngày trước (bước 8) |
| Đầu tuần | Chọn 5–10 sản phẩm mới (bước 1–2) |
| Cuối tuần | Xem nhật ký: sản phẩm, kiểu hook nào nhiều đơn thì làm thêm |

---

## 6. Gặp lỗi thì làm gì

| Hiện tượng | Cách xử lý |
|---|---|
| Trang web báo *"local … service is not running"* | Máy chủ chưa bật hoặc đã tắt: làm lại mục 3. Nếu máy chủ vẫn chạy: bấm biểu tượng bên trái thanh địa chỉ Chrome, cho phép truy cập mạng cục bộ, tải lại trang |
| Danh sách video trống | Chưa có video nào được tạo: làm bước 3 |
| Bấm Send báo *Connect your TikTok account first* | Đăng nhập lại (bước 6.3) |
| Báo lỗi có chữ `spam_risk_too_many_pending_share` | Đã có 5 video chờ đăng: đăng hết trên điện thoại, hoặc chờ sang ngày hôm sau |
| Terminal báo `TikTok returned no product data` | TikTok tạm chặn việc đọc tự động. Chờ một lúc rồi chạy lại, hoặc tự điền các ô còn trống |
| Terminal báo `row 1 is missing columns` | Dòng 1 của sheet Tiktok bị sửa tên cột: đặt lại đúng 10 tên cột tiếng Anh |
| Terminal báo `PERMISSION_DENIED` hoặc `403` khi đọc sheet | Sheet chưa chia sẻ quyền Editor cho `sheet-bot@omni-affiliate.iam.gserviceaccount.com` |
| Terminal báo `GROQ_API_KEY not set` | File `.env` thiếu key: nhờ người phụ trách kỹ thuật |
| Không thấy thông báo trên điện thoại | Kiểm tra đúng tài khoản TikTok, vuốt xuống tải lại Hộp thư, chờ vài phút |
| Không thấy mục **Sản phẩm** khi đăng | Sản phẩm chưa có trong showcase, hoặc người bán chưa mở hoa hồng: làm lại bước 1.3 hoặc chọn sản phẩm khác |
| Lỗi khác | Chụp màn hình Terminal và trang web, gửi người phụ trách kỹ thuật |

---

## 7. Những điều không được làm

- Không đăng video thiếu nhãn **"Nội dung do AI tạo"**.
- Không dùng hình người nổi tiếng, nhân vật phim, nhạc có bản quyền.
- Không nói sản phẩm chữa bệnh, hay hứa kết quả không có thật.
- Không chia sẻ file `.env`, Client secret, mật khẩu TikTok.
- Không gửi quá 5 video chờ đăng trong 24 giờ.
