# Hướng dẫn vận hành hằng ngày

Dành cho người đăng video TikTok Shop Affiliate hằng ngày. Không cần biết lập trình: chỉ cần làm theo từng bước, gõ đúng lệnh được cho sẵn.

Áp dụng **sau khi TikTok đã duyệt app** TT Content Publisher.

---

## 1. Ai làm việc gì

Hệ thống hiện tại **không tự đăng video**. Máy lo phần viết kịch bản, đọc giọng và dựng video. Người lo chọn sản phẩm, duyệt và bấm đăng.

| Việc | Ai làm | Ghi chú |
|---|---|---|
| Chọn sản phẩm trên TikTok Shop | **Người** | Mỗi tuần 5–10 sản phẩm |
| Ghi sản phẩm vào danh sách | **Người** | File `products.csv` |
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
4. Lưu lại: tên sản phẩm, giá, link sản phẩm, 2–3 ảnh, vài ý chính về công dụng.

### Bước 2. Ghi vào danh sách sản phẩm

Mở file `products.csv` trong thư mục dự án bằng VS Code. Mỗi dòng là một sản phẩm, các ô cách nhau bằng dấu phẩy:

| Cột | Ghi gì | Ví dụ |
|---|---|---|
| `name` | Tên sản phẩm | `Máy hút bụi mini cầm tay` |
| `price` | Giá, chỉ số, để trống nếu chưa rõ | `189000` |
| `category` | Ngành hàng | `Nhà cửa` |
| `images` | Link hoặc đường dẫn ảnh, cách nhau bằng `\|` | `https://.../a.jpg\|https://.../b.jpg` |
| `selling_points` | Ý chính, cách nhau bằng `\|` | `Lực hút mạnh\|Sạc USB\|Nặng 500g` |
| `product_url` | Link sản phẩm TikTok Shop | `https://shop.tiktok.com/...` |
| `commission_pct` | % hoa hồng | `12` |
| `sold_count` | Số đã bán | `3500` |
| `notes` | Điều cần tránh khi viết | `Không phải thiết bị y tế` |
| `status` | Để trống. Làm xong ghi `done`, muốn bỏ qua ghi `skip` | |

Lưu ý:
- Tên hoặc ý chính có dấu phẩy thì bỏ dấu phẩy đi, tránh lệch cột.
- Sản phẩm sức khoẻ, làm đẹp: **luôn** ghi vào `notes` những điều không được nói, ví dụ "không chữa bệnh".

### Bước 3. Tạo video

Trong cửa sổ Terminal thứ hai, chọn một trong hai kiểu.

**Kiểu đơn giản** (nhanh, chỉ dùng ảnh sản phẩm):
```bash
.venv/bin/python demo.py --csv products.csv --style simple
```

**Kiểu tiểu phẩm** (có nhân vật, phải tự tạo ảnh bằng Gemini ở bước 4):
```bash
.venv/bin/python demo.py --csv products.csv
```

Máy làm lần lượt từng sản phẩm có `status` trống. Video nằm trong thư mục `storage/videos/<ngày giờ>_<tên sản phẩm>/`.

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

Gõ `y` rồi Enter để đồng ý, `n` để bỏ. Đồng ý thì máy tạo file `post.txt` cạnh video, có caption để dán.

Sau đó mở `products.csv`, ghi `done` vào cột `status` của sản phẩm vừa làm, để lần sau máy không làm lại.

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

## 5. Lịch gợi ý

| Khi nào | Việc |
|---|---|
| Mỗi ngày | 1–2 video: bước 3 → 7 |
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
