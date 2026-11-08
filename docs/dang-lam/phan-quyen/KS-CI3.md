# Sổ giữ chỗ — làn Phân quyền · Đợt KS-CI3

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-CI3 — 5 PHÉP ĐỎ CỦA LẦN CHẠY 4 MÁY ĐẦU TIÊN** (Chủ tịch 08/11/2026 chọn «Đẩy PR sửa cả hai»). CI đầy đủ trên main sau #735 (chia 4 máy, phần lâu nhất 36 phút) đỏ 5 phép: `test_nap_v4` (4) — TSCD-1 (#735) bắt buộc cột «TK nguyên giá» chi tiết (2113) mà dữ liệu mẫu chưa khai; `test_r4c4_ve_tien_cap_chi_tiet` (1) — KS-TC (#729) chuyển số dư đầu kỳ dự báo sang đọc qua `dashboard._so_du_no_vay_phai_thu` (vẫn cộng ("111","112") cấp cha), phép thử đếm hụt một chỗ. Mã đúng, chỉ phép thử cũ. Không đổi mã. | backend/tests/test_nap_v4.py, backend/tests/test_r4c4_ve_tien_cap_chi_tiet.py, docs/dang-lam/phan-quyen/KS-CI3.md | 08-11-2026 11:20 | đang làm |
