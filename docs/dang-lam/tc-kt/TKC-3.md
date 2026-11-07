# Đợt TKC-3 — Nhịp 2a: nắn đường ghi về tài khoản chi tiết (07/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TKC-3 — một bảng khai «đường ghi → tài khoản chi tiết» | backend/app/services/tk_chi_tiet.py, backend/app/services/rules.py, backend/app/services/ops.py, backend/app/services/accounting.py, backend/app/services/misa.py, backend/app/services/reports.py, backend/tests/test_tkc3_nan_duong_ghi_ve_tai_khoan_con.py, backend/tests/test_accounting.py, backend/tests/test_ops.py, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/TKC-3.md | 07-11-2026 23:45 | đang làm |

Nhịp 1 (Đợt TKC-2) đo trên sổ thật: 187 dòng vào 13 tài khoản cha. Đọc mã đếm được 14 chỗ gõ
cứng tài khoản cha. Đợt này nắn BA đường (đề nghị chi, quyết toán tour, kết chuyển lãi/lỗ) qua
MỘT bảng khai có chữ ký. Không bật chặn (nhịp 3), không đụng bảng quyền, không mở cửa nào.

Còn lại cho Đợt TKC-4: hóa đơn (511, 3331), lương (334, 338, 642, 632), vay (341, 3411, 635),
trích trước (335 — con `3351` chưa có trong danh mục mẫu), hoa hồng và khuyến mãi (511, 641),
chênh lệch tỷ giá (413, 515, 632, 635), mặc định của mô hình tài sản (211, 242), tiền mặt và
tiền gửi (111, 112 — `1121` có 20 con là 20 tài khoản ngân hàng, phải chọn theo giao dịch).
