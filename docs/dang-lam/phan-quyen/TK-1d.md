# Sổ giữ chỗ — làn Phân quyền · Đợt TK-1d

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-1d — XE TOUR ĐOÀN LỆCH SỐ NGÀY: CỬA NHẬP ĐƠN GIÁ NGÀY XE NHÀ + QUY GIÁ TUYẾN THEO NGÀY** (Chủ tịch 04/11/2026 «làm cả 2»: thử Đà Lạt 3 ngày không ra giá xe vì bảng giá xe chỉ có Đà Lạt 4 ngày và 14 xe 45 chỗ chưa có đơn giá ngày). (1) Cửa nhập: màn /doi-xe › Hồ sơ xe có ô «Đơn giá ngày (xe nhà)» — Đội xe / Điều hành / HCNS / CNTT nhập, ghi qua PUT /fleet/xe/{id} (thêm trường internal_rate_per_day, kiểm phiên bản như mọi lần sửa hồ sơ). Claude không nhập số. (2) Phép tính: trùng tuyến + số ngày → giá trọn chuyến; không thì đơn giá ngày xe nhà × số ngày; chưa có thì giá tuyến (số ngày gần nhất) ÷ số ngày tuyến × số ngày đi; không có nữa → đơn giá đoàn. Phép thử test_tk1 (+2). | backend/app/services/thiet_ke_doan.py, backend/app/api/v1/fleet.py, web/app/doi-xe/page.tsx, backend/tests/test_tk1_tu_thiet_ke_tour_doan.py, docs/dang-lam/phan-quyen/TK-1d.md | 04-11-2026 02:35 | xong |
