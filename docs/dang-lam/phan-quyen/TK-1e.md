# Sổ giữ chỗ — làn Phân quyền · Đợt TK-1e

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-1e — HDV TOUR ĐOÀN: TUYẾN NHIỀU MỨC LẤY MỨC CAO + NGÀY LỄ TẾT ×2** (Chủ tịch 04/11/2026: «4 mục 600k, 5 có nhân đôi»). Tuyến khớp nhiều bản giá (Đà Lạt 3N2Đ 600k / 3N3Đ 500k) → lấy mức cao. Lịch ngày lễ Tết: bảng mới `ngay_le_tet` (migration tk1e7b9d1f3a5c8e02), Điều hành nhập ở màn /tour-doan › «Ngày lễ Tết» (máy không tự suy lịch âm); ngày đi tour trùng lịch thì thù lao HDV ngày ấy ×2, dòng tạm tính ghi «N ngày lễ Tết ×2». Khai `ngay_le_tet` vào CUA_TAY. Phép thử test_tk1 (+1). | backend/app/models/thiet_ke_doan.py, backend/alembic/versions/tk1e7b9d1f3a5c8e02_ngay_le_tet.py, backend/app/services/thiet_ke_doan.py, backend/app/api/v1/thiet_ke_doan.py, backend/app/services/ks_cua_nhap.py, backend/tests/test_tk1_tu_thiet_ke_tour_doan.py, web/app/tour-doan/page.tsx, docs/dang-lam/phan-quyen/TK-1e.md | 04-11-2026 02:50 | đang làm |
