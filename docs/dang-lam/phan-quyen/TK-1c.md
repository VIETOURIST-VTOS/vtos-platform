# Sổ giữ chỗ — làn Phân quyền · Đợt TK-1c

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-1c — THÙ LAO HDV CHO TUYẾN CHƯA CÓ: SUY THEO VÙNG CỦA BẢNG GIÁ MỚI** (Chủ tịch 04/11/2026: «tuyến nào chưa có phí hướng dẫn em lấy tương tự theo vùng của bảng giá mới để bổ sung cho đủ»). Máy TÍNH, không ghi thêm dòng nào vào bảng thù lao HDV: (1) trùng tuyến — so đúng tập địa danh, «Đà Lạt Phan Thiết» không khớp chuyến chỉ đi Đà Lạt; nhiều bản lấy số ngày gần nhất; (2) có tuyến chung địa danh → trung vị các tuyến ấy; (3) không có → theo 5 vùng (Miền Bắc · Bắc & Trung Trung Bộ · Nam Trung Bộ · Tây Nguyên · Nam Bộ), giá vùng = trung vị các tuyến nằm trọn trong vùng, đi nhiều vùng lấy vùng cao nhất. Dòng tạm tính ghi rõ «tương tự tuyến…» / «vùng…». Cách đọc địa danh mới cũng dùng cho bảng giá xe. Màn /tour-doan hiện giá vùng cho người xem được giá vốn. Phòng Hướng dẫn thêm tuyến thì giá tuyến được dùng trước. Phép thử test_tk1 (+1). | backend/app/services/thiet_ke_doan.py, backend/tests/test_tk1_tu_thiet_ke_tour_doan.py, web/app/tour-doan/page.tsx, docs/dang-lam/phan-quyen/TK-1c.md | 04-11-2026 02:10 | đang làm |
