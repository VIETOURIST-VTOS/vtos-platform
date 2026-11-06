# Sổ giữ chỗ — làn Phân quyền · Đợt KS-20c

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-20c — ĐẶT PHÒNG VTD v1.3, ĐỢT 3: THANH TOÁN (D3), XÁC NHẬN (D4 / M3), ĐƠN CỦA TÔI + HỦY (M4)** (bản xem trước đã duyệt 05/11/2026; 06/11 Chủ tịch «làm tiếp», chọn giữ «Đặt giữ, trả sau» — ô voucher đã bỏ từ KS-19). Thanh tiến trình bốn bước Chọn phòng → Thông tin → Thanh toán → Xác nhận; trang thanh toán thêm ô «Tích điểm VTD» và «Thanh toán thành công = phòng được xác nhận ngay» (đơn có giường phụ chờ khách sạn thì báo rõ); trang xác nhận: số đã nhận, «Xem trong Đơn của tôi», «In / lưu phiếu xác nhận (PDF)», «Chỉ đường Google Maps», ngày giờ nhận / trả, hạn hủy miễn phí từng phòng; cột tóm tắt theo P1, P2…; Đơn của tôi chia tab Sắp tới / Đã qua / Đã hủy, nút «Hủy đơn»; hỏi hủy hiện từng phòng hoàn bao nhiêu, lý do (không bắt buộc), điện thoại là tấm trượt từ dưới. Máy chủ chỉ thêm `hoan_dong` (từng gói hoàn bao nhiêu, cùng luật số hoàn); không đổi luật hoàn, giá, thanh toán. | backend/app/services/don_ks_vtd.py, web/components/cong/KhachSanVtd.tsx, backend/tests/test_ks20c_thanh_toan_xac_nhan.py, docs/dang-lam/phan-quyen/KS-20c.md | 06-11-2026 22:55 | xong |
