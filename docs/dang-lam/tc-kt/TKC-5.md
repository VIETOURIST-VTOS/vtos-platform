# Đợt TKC-5 — Nhịp 2c: hoa hồng, khuyến mãi, chi phí trả trước (08/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TKC-5 — hoa hồng, voucher Rewards, CCDC/chi phí trả trước | backend/app/services/tk_chi_tiet.py, backend/app/services/assets.py, backend/app/services/dat_ban.py, backend/app/services/don_ks_vtd.py, backend/app/services/intake_phong_ban_2.py, backend/tests/test_tkc5_hoa_hong_khuyen_mai_tra_truoc.py, backend/tests/test_assets.py, backend/tests/test_tkc4_bon_duong_ghi_tiep_theo.py, backend/tests/test_ks16e_doanh_thu_hoa_hong.py, backend/tests/test_ks16d_dat_ban.py, backend/tests/test_ks16b_voucher_dat_ban.py, backend/tests/test_ks16_rewards_khach_san.py, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/TKC-5.md | 08-11-2026 03:30 | đang làm |

Nắn ba đường còn lại trong nhóm suy ra được từ dữ liệu: doanh thu hoa hồng khách sạn / nhà hàng
(511), voucher VTD Rewards (641), CCDC và chi phí trả trước (242). Đợt này cũng SỬA một lỗi của
Đợt TKC-4 đã lên main: hóa đơn không gắn chuyến ghi vào `51136` — tài khoản bắt buộc mã công
trình — nên hóa đơn ấy không phát hành được.

Còn lại: `1121` (20 tài khoản ngân hàng) · chênh lệch tỷ giá · TK nguyên giá tài sản cố định
(cần một ô chọn trên form) · trích trước `335` (chờ nạp danh mục thật) · rồi mới chặn cứng.
