# Sổ giữ chỗ — làn Phân quyền · Đợt KS-NUT

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-NUT — MÀU NÚT VTOS DO NGƯỜI DÙNG CHỌN** (Chủ tịch 07/11/2026, bản xem thử «Navy bên trong VTOS»: "chọn cả A và B cho người dùng tự bấm điều khiển vào nút giao diện"). Bảng «Giao diện» thêm mục «Màu nút»: Navy đậm (A, mặc định — nút/chip/nhãn đang chọn #14538D viền #5A9BD4) · Xanh sáng (B — giữ #1E63C8). Chỉ áp ở nền tối. Cả hai: gạch tab đang chọn #5A9BD4 thay vàng. Cất theo tài khoản: cột users.gd_mau_nut ("" = chưa chọn), PUT/DELETE /auth/giao-dien nhận mau_nut, /auth/me trả mau_nut + mặc định "navy"; kịch bản chống loé trong <head> đặt data-mau-nut trước khi vẽ. | backend/app/models/core.py, backend/app/api/v1/routes.py, backend/alembic/versions/mn3b7d9f1a2c4e57_mau_nut_theo_tai_khoan.py, backend/tests/test_ks_nut_mau_nut_tu_chon.py, web/lib/api.ts, web/app/layout.tsx, web/components/ChonGiaoDien.tsx, web/app/tokens.css, web/app/globals.css, docs/dang-lam/phan-quyen/KS-NUT.md | 07-11-2026 03:40 | xong |
