# Sổ giữ chỗ — làn Phân quyền · Đợt TK-3

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-3 — ĐƠN GIÁ DỊCH VỤ ĐOÀN THEO KHU VỰC; VISA ĐỂ TRỐNG** (Chủ tịch 04/11/2026: giá châu Âu tạm nhập từ quyết toán T6 không áp cho tour Thái, Hàn; «visa em bỏ trống giá vì mỗi nước 1 loại visa và giá khác nhau»; «phần giá để Điều hành sửa và nhập tay»). Cột `khu_vuc` (châu lục / nước, rỗng = mọi nước) cho đơn giá nước ngoài; tạm tính chọn dòng khớp nhất: nước > châu lục > mọi nước, không khớp → Sales báo giá. Danh mục NUOC_NGOAI khớp DD.nn của cổng khách (phép thử). Visa bỏ khỏi loại đơn giá; tạm tính luôn ghi «thiếu giá — Sales báo giá», Điều hành nhập tay trong báo giá từng đoàn. Ô «Khu vực áp dụng» ở /tour-doan (bản xem thử đã duyệt). Migration tk3b4d6f8a0c2e5173. Phép thử test_tk3 (5). | backend/app/models/thiet_ke_doan.py, backend/alembic/versions/tk3b4d6f8a0c2e5173_don_gia_khu_vuc.py, backend/app/services/thiet_ke_doan.py, backend/app/api/v1/thiet_ke_doan.py, backend/tests/test_tk3_don_gia_khu_vuc.py, web/app/tour-doan/page.tsx, docs/dang-lam/phan-quyen/TK-3.md | 04-11-2026 06:00 | đang làm |
