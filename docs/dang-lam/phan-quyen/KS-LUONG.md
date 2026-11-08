# Sổ giữ chỗ — làn Phân quyền · Đợt KS-LUONG

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-LUONG — BẢNG LƯƠNG KỲ KHÔNG SẬP VÌ MỘT NGƯỜI CHƯA KHAI LƯƠNG** (Chủ tịch 08/11/2026 cho kiểm 75 màn hình trên crm thật, duyệt xem nhật ký Render). Trang Nhân sự mọi thẻ trả 500 ở `/payroll-runs/2026-10` và `2026-09`. Nhật ký: `luong.py:111 xac_dinh_theo_cong` định dạng `e.base_salary:,.0f` khi `base_salary` rỗng → TypeError. Sửa: rỗng thì nói «chưa khai mức lương hợp đồng», không in 0 và không nổ. Phép thử dựng đúng ca ấy qua cửa API. | backend/app/services/luong.py, backend/tests/test_ks_luong_muc_rong.py, docs/dang-lam/phan-quyen/KS-LUONG.md | 08-11-2026 22:25 | đang làm |
