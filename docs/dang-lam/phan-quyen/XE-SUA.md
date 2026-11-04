# Sổ giữ chỗ — làn Phân quyền · Đợt XE-SUA

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **XE-SUA — NÚT «SỬA» DÒNG GIÁ XE CHO CHỦ TỊCH** (Chủ tịch 04/11/2026: bảng giá xe có hai dòng Đà Lạt 4 ngày 13tr và 16tr, «Đà Lạt chốt 16tr»; «thay nút ngừng bằng nút sửa»; duyệt bản xem thử). POST /api/v1/vehicle-rates/{id}/sua — chỉ người ký giá xe (Chủ tịch), chỉ dòng đang hiệu lực; sửa tuyến, số ngày, giá xe Vietrip – VTD (> 0), giá xe hợp tác; có hiệu lực ngay, ghi nhật ký trước/sau, ghi chú «Sửa dd/mm». Khung sửa ở màn Đội xe › Bảng giá xe. Phép thử test_hr (+1). | backend/app/api/v1/hr.py, web/components/HrScreens.tsx, backend/tests/test_hr.py, docs/dang-lam/phan-quyen/XE-SUA.md | 04-11-2026 07:50 | đang làm |
