# Đợt TKC-4 — Nhịp 2b: bốn đường ghi tiếp theo (07/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TKC-4 — hóa đơn, lương, vay, kết chuyển chi phí đội xe | backend/app/services/tk_chi_tiet.py, backend/app/services/accounting.py, backend/app/services/hr.py, backend/app/services/finance.py, backend/app/services/ket_so.py, backend/tests/test_tkc4_bon_duong_ghi_tiep_theo.py, backend/tests/test_accounting.py, backend/tests/test_ky2_tk627_va_ten_tt99.py, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/TKC-4.md | 08-11-2026 00:40 | xong |

Đợt TKC-3 dựng bảng khai chung và nắn ba đường. Đợt này nắn bốn đường nữa qua CÙNG bảng ấy:
hóa đơn (511, 3331) · lương (642, 334, 632, 338) · vay (341, 635) · kết chuyển chi phí đội xe
627 → 154 → 632. Không bật chặn, không đụng bảng quyền, không mở cửa nào.

Còn lại: hoa hồng và khuyến mãi (511, 641) · CCDC/chi phí trả trước (242) · chênh lệch tỷ giá
(632, 635, 515 — bút toán gộp mọi chuyến, nắn đúng thì phải tách theo loại tour, đổi cả thẻ) ·
TK nguyên giá tài sản cố định (211 — cần một ô chọn trên form, giống Đợt CPTT-1) · tiền mặt và
tiền gửi (111, 112 — 1121 có 20 con là 20 tài khoản ngân hàng) · trích trước (335) · chặn cứng.
