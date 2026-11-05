# Sổ giữ chỗ — làn Phân quyền · Đợt TK-1b

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-1b — TẠM TÍNH TOUR ĐOÀN LẤY BẢNG GIÁ XE VÀ BẢNG THÙ LAO HDV CÓ SẴN TRÊN VTOS** (Chủ tịch 04/11/2026: «bảng giá xe đã có trên phần mềm VTOS»; chọn: giá theo tuyến là xe 45 chỗ; lệch tuyến → đơn giá ngày của xe × số ngày; dùng cột xe nhà Vietrip – VTD; nối luôn bảng thù lao HDV). Trong nước: đi xe từ TP HCM, trùng tuyến + số ngày trong bảng giá xe (vehicle_rates, đang hiệu lực, bản mới nhất) → giá trọn chuyến cột xe nhà × số xe 45 chỗ; không trùng (hoặc có chặng bay / tàu) → đơn giá ngày xe nhà nhỏ nhất đủ chỗ (vehicles.internal_rate_per_day) × số ngày; không có nữa → đơn giá đoàn Điều hành nhập. HDV trong nước: bảng thù lao HDV theo tuyến (hdv.tra_don_gia, bản «đoàn» trước, bản chung sau) × số ngày, chưa tính lễ Tết ×2; lệch tuyến → đơn giá đoàn. Nước ngoài giữ đơn giá đoàn. Không đổi bảng, không đổi quyền. Phép thử test_tk1 (+1). | backend/app/services/thiet_ke_doan.py, backend/tests/test_tk1_tu_thiet_ke_tour_doan.py, web/app/tour-doan/page.tsx, docs/dang-lam/phan-quyen/TK-1b.md | 04-11-2026 01:30 | xong |
