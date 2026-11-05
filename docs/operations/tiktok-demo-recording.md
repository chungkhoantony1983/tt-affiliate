# Quay video demo cho TikTok App Review

Tài liệu này dành cho người vận hành app TT Content Publisher: cấu hình sandbox, chạy app, quay video và nộp review.

TikTok yêu cầu video demo thể hiện toàn bộ luồng, trên đúng domain đã khai, và app chưa từng được duyệt phải demo bằng sandbox.

## 1. Cấu hình sandbox trong portal

Vào app trên developers.tiktok.com, chuyển sang **Sandbox**. Tên mục trong portal có thể khác đôi chút.

1. Tạo sandbox nếu chưa có.
2. Thêm 2 sản phẩm: **Login Kit** và **Content Posting API**. Chỉ bật Upload, không bật Direct Post.
3. Chọn đúng 2 scope: `user.info.basic` và `video.upload`.
4. Trong Login Kit, phần Web, thêm Redirect URI:
   ```
   https://chungkhoantony1983.github.io/tt-affiliate/app.html
   ```
5. Thêm tài khoản TikTok dùng để quay vào danh sách **Target Users**.
6. Nếu sandbox báo URL chưa xác minh, làm lại bước URL properties ở chế độ Sandbox với prefix `https://chungkhoantony1983.github.io/tt-affiliate/`.
7. Sao chép **Client key** và **Client secret** của sandbox vào `.env`. Không gửi 2 giá trị này cho ai và không commit:
   ```
   TIKTOK_CLIENT_KEY=...
   TIKTOK_CLIENT_SECRET=...
   ```

## 2. Chạy app

```bash
.venv/bin/pip install -r requirements-demo.txt
.venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
```

Giữ cửa sổ Terminal đó mở trong lúc quay. Mở trang bằng **Google Chrome**, Safari chặn trang HTTPS gọi tới `localhost`:

```
https://chungkhoantony1983.github.io/tt-affiliate/app.html
```

Nếu Chrome hỏi quyền truy cập mạng cục bộ, chọn **Allow**. Làm việc này trước khi quay.

App liệt kê các video trong `storage/videos/`. Video mới nhất đứng đầu, gồm cả video OMNIEAR.

## 3. Chạy thử trước khi quay

Chạy trọn luồng ở mục 4 một lần với tài khoản sandbox, đảm bảo video về được inbox. Sau đó bấm **Disconnect** để lần quay hiện màn hình xin quyền của TikTok.

Nếu đăng nhập xong app báo lỗi, chép nguyên thông báo gửi lại để xử lý.

## 4. Kịch bản quay

Quay màn hình một mạch bằng `Cmd+Shift+5`, sau đó quay điện thoại cho bước cuối. Kích thước tối đa 50 MB mỗi video, được nộp tối đa 5 video.

| # | Thao tác | Điều cần thấy trong video |
|---|---|---|
| 1 | Mở `https://chungkhoantony1983.github.io/tt-affiliate/` | Thanh địa chỉ, link Terms và Privacy |
| 2 | Bấm **Open the app** | Trang `app.html` |
| 3 | Bấm **Login with TikTok** | Màn hình TikTok hiện 2 quyền được xin |
| 4 | Bấm cho phép | Quay lại app, hiện tên tài khoản (`user.info.basic`) |
| 5 | Chọn video OMNIEAR, phát vài giây | Xem trước video và caption |
| 6 | Bấm **Copy caption**, rồi **Send to TikTok inbox** | Dòng "Sent. Check the notification..." (`video.upload`) |
| 7 | Mở app TikTok trên điện thoại | Thông báo và bản nháp trong inbox |
| 8 | Mở bản nháp, dán caption, chọn quyền xem | Người dùng tự hoàn tất đăng |

Video OMNIEAR có người và giọng đọc do AI tạo, nên bật nhãn **Nội dung do AI tạo** nếu đăng ở bước 8.

## 5. Nộp review

Chuyển về **Production**, tải video lên, bỏ các sản phẩm và scope không dùng, rồi điền phần giải thích:

```
TT Content Publisher helps creators prepare short product-review videos.

Login Kit (user.info.basic): the creator signs in with TikTok, and the app shows
which account is connected.

Content Posting API, Upload (video.upload): the app sends the rendered video to the
creator's TikTok inbox as a draft. The creator opens the draft in the TikTok app,
adds a caption, chooses privacy settings and posts it. The app never posts on the
creator's behalf.

The demo video shows the full flow in the sandbox: sign in, review a video, upload
the draft, then open it in the TikTok app.
```

## Rủi ro cần biết

- **Mục đích sử dụng:** TikTok không duyệt app chỉ dùng riêng. App hiện chạy dịch vụ local trên máy của người vận hành, chưa mở cho creator khác.
- **Giỏ hàng:** Content Posting API không gắn được sản phẩm TikTok Shop, nên được duyệt thì bước gắn sản phẩm vẫn làm tay.
