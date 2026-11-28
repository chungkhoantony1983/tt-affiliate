# CapCut MCP: Claude tạo video quảng cáo sản phẩm affiliate

MCP server này cho phép Claude (Claude Desktop hoặc Claude Code) nhận thông tin sản phẩm
và tự dựng video quảng cáo:

- **Dự án nháp CapCut**: tạo sẵn trong thư mục CapCut, gồm ảnh/video sản phẩm, hiệu ứng zoom/pan,
  chuyển cảnh, chữ có animation, giá + % giảm, lời kêu gọi mua, nhạc nền, giọng đọc.
  Bạn mở CapCut, chỉnh thêm nếu muốn rồi bấm Export.
- **File MP4 xuất thẳng** bằng ffmpeg (không cần CapCut), lưu ở `~/Movies/CapCut-MCP/`.
  Dùng để xem nhanh hoặc đăng luôn.
- **Caption gợi ý** kèm link affiliate và hashtag.

> CapCut không có API chính thức. MCP này tạo file dự án (draft) mà CapCut đọc được,
> dựa trên thư viện mã nguồn mở [pyCapCut](https://github.com/GuanYixuan/pyCapCut)
> (đã kiểm chứng tới CapCut 9.5, chủ yếu trên Windows; trên macOS cần thử thực tế).

## 1. Cài đặt trên macOS

1. Cài **CapCut desktop từ capcut.com** (không dùng bản Mac App Store). Mở CapCut, đăng nhập,
   tạo thử 1 dự án trống rồi đóng lại, để CapCut tạo thư mục dự án.
2. Cài [Homebrew](https://brew.sh) nếu chưa có.
3. Mở Terminal ở thư mục repo `tiktok_affiliate` và chạy (cài editable từ chính `tools/capcut-mcp`, sửa code ở đây là server nhận luôn):

   ```bash
   cd tools/capcut-mcp
   bash install_mac.sh
   ```

   Script sẽ cài Python 3.12, ffmpeg, thư viện cần thiết, và tự đăng ký MCP với Claude Desktop
   (và Claude Code nếu có).
4. Thoát hẳn Claude Desktop (Cmd+Q) rồi mở lại.
5. Trong Claude, gõ: *"Kiểm tra trạng thái capcut"*. Nếu `drafts_folder` là `null`, hãy tìm thư mục
   dự án trong CapCut (Settings → Projects/Drafts location) và nói Claude:
   *"đặt thư mục draft CapCut là /đường/dẫn/..."*.

## 2. Cách dùng

Ví dụ câu lệnh cho Claude:

> Tạo video quảng cáo TikTok cho sản phẩm **Máy xay sinh tố mini**. Ảnh: ~/Downloads/may-xay/1.jpg,
> 2.jpg, 3.jpg. Điểm nổi bật: xay đá 30 giây, sạc USB, dễ vệ sinh. Giá 199.000đ, giá gốc 350.000đ,
> mã giảm GIAM20, link affiliate https://s.shopee.vn/xxxx. Nhạc nền ~/Music/beat.mp3. Phong cách sôi động.

Claude sẽ gọi `create_product_video`, rồi bạn:

1. Mở CapCut (hoặc bảo Claude "mở CapCut"). Nếu CapCut đang mở, cần **khởi động lại** để thấy dự án mới
   tên `QC - <tên sản phẩm>`.
2. Xem lại, chỉnh, rồi Export.
3. Đăng kèm caption Claude gợi ý.

Muốn chỉnh chi tiết (đổi thời lượng cảnh, chữ, hiệu ứng), cứ nói với Claude. Claude sẽ sửa `spec`
và gọi `build_video` để dựng lại.

## 3. Các công cụ (tools)

| Tool | Tác dụng |
|---|---|
| `capcut_status` | Kiểm tra thư mục CapCut, ffmpeg, font |
| `set_drafts_folder` | Đặt thủ công thư mục draft CapCut |
| `create_product_video` | Thông tin sản phẩm → draft CapCut + MP4 + caption |
| `build_video` | Dựng video từ spec tuỳ biến (từng cảnh, từng dòng chữ) |
| `list_effects` | Tra tên chuyển cảnh, animation chữ, font, filter của CapCut |
| `list_drafts` | Liệt kê dự án trong CapCut |
| `open_capcut` | Mở/khởi động lại CapCut |

**Phong cách có sẵn:** `energetic` (TikTok Shop, nhanh, chuyển cảnh mạnh), `elegant` (mỹ phẩm, thời
trang), `minimal` (gia dụng, công nghệ). **Khung hình:** `9:16`, `1:1`, `4:5`, `16:9`.

**Font hỗ trợ tiếng Việt tốt trong CapCut:** `Montserrat`, `Nunito`, `Rubik_Bold`, `Poppins_Bold`
(để trống thì dùng font hệ thống).

## 4. Lưu ý

- Ảnh/video có thể là file trên máy hoặc URL. Ảnh được chép vào thư mục dự án nên không bị mất.
- Nên dùng ảnh sản phẩm mà bạn có quyền sử dụng (ảnh do nhà bán cung cấp cho affiliate, hoặc tự chụp),
  và nhạc nền bản quyền miễn phí.
- Nếu CapCut báo lỗi hoặc không mở được dự án, file MP4 vẫn được tạo để bạn dùng. Gửi lại thông báo lỗi
  để điều chỉnh cho đúng phiên bản CapCut của bạn.
