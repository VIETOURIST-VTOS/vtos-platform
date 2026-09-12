VTOS — BỘ FILE GIAO DIỆN CHO ĐỘI IT
Phiên bản 1.0 · 09/2026

────────────────────────────────────────────────────────────
1. LOGO  (thư mục logo/)
   vtos-logo.svg           Bản chính — dùng trên nền sáng
   vtos-logo-nen-toi.svg   Dùng trên nền navy/đen
   vtos-logo-trang.svg     Toàn trắng — đặt trong ô navy, trên ảnh
   vtos-logo-don-sac.svg   Một màu #0B2545
   (kèm .png 1600px nền trong suốt cho chỗ nào không nhận SVG)

   Nhúng trong web: dán thẳng nội dung SVG vào HTML (inline) để
   đổi màu bằng CSS, hoặc dùng <img src="vtos-logo.svg">.

2. FAVICON / APP ICON  (thư mục favicon/)
   favicon.ico             16/32/48 — đặt ở thư mục gốc website
   icon-16/32/48/64.png    favicon các cỡ
   icon-180.png            apple-touch-icon
   icon-192/256/512.png    PWA manifest, Android
   app-icon.svg            bản vector của ô bo góc

   <link rel="icon" href="/favicon.ico" sizes="any">
   <link rel="icon" type="image/svg+xml" href="/favicon/app-icon.svg">
   <link rel="apple-touch-icon" href="/favicon/icon-180.png">

3. MÀU VÀ PHÔNG
   tokens.css              biến CSS — import một lần ở file gốc
   tokens.json             cùng giá trị, cho Tailwind/JS/Figma

   Phông lấy từ Google Fonts:
   <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Be+Vietnam+Pro:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap">

────────────────────────────────────────────────────────────
QUY TẮC BẮT BUỘC KHI DỰNG GIAO DIỆN

  1. Thanh điều hướng trái luôn nền #14538D đặc.
     Mục đang chọn làm sáng bằng lớp phủ trắng 14%
     (background: rgba(255,255,255,0.14)), không đổi sang màu khác.

  2. Mỗi màn hình chỉ MỘT nút chính màu navy.
     Mọi thao tác còn lại dùng nút viền hoặc nút chữ.

  3. Trạng thái dùng đúng ba màu, không thêm màu thứ tư:
        xanh lá  #3B8C43  đã duyệt / thành công
        hồng     #FC4D7A  từ chối / cảnh báo
        navy sáng #2E7FB8 chờ xử lý
     Nền chip trạng thái dùng biến --vtos-*-bg tương ứng.

  4. Số tiền, mã chứng từ, mã nhân viên đặt bằng JetBrains Mono
     để các cột dóng thẳng hàng.

  5. Chữ trên nền navy tối thiểu 13px, độ đậm từ 400 trở lên.

  6. Logo trong giao diện không nhỏ hơn 22px.
     Favicon và icon ứng dụng dùng ô bo góc (app-icon),
     KHÔNG dùng ký hiệu trần.

  7. Bo góc ô icon = 23,5% cạnh. Không bo tròn hoàn toàn.

  8. KHÔNG dùng lại màu xanh ngọc #01A381 và xanh dương #01B1F0
     của bản nhận diện cũ ở bất kỳ đâu.

────────────────────────────────────────────────────────────
NGUYÊN TẮC DỮ LIỆU (áp dụng cho mọi màn hình)

  Mỗi con số hiển thị trên màn hình phải có một ô nhập tay
  hoặc một cửa tải file tương ứng cho người dùng.
  Màn hình nào có số mà không có cửa nhập — đó là phần còn
  thiếu của hệ thống, cần bổ sung.
────────────────────────────────────────────────────────────
