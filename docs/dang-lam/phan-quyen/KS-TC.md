# Sổ giữ chỗ — làn Phân quyền · Đợt KS-TC

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-TC — TRANG TÀI CHÍNH NHANH LÊN** (Chủ tịch 08/11/2026 chọn «Kiểm tốc độ các trang crm», duyệt «Sửa cả 4 trang», trang Tài chính trước). Đo crm thật hai lượt: Tài chính 6–8 s — `/bank-transactions` 6–7,6 s vì mỗi dòng hỏi riêng mã booking và số dòng phân bổ (1 + 2×200 câu hỏi), `/fin/forecast` 4–5 s vì cộng lại cả sổ cái lấy số dư tiền. Sửa: nạp hai bảng tra một lần cho cả danh sách, không kéo gói tin gốc `raw`; dự báo đọc số dư qua bộ nhớ KS-SD của bảng điều hành (xoá khi ghi sổ). Không đổi số, không đổi khuôn trả về. | backend/app/api/v1/payments.py, backend/app/services/finance.py, backend/tests/test_ks_tc_tai_chinh_nhanh.py, docs/dang-lam/phan-quyen/KS-TC.md | 08-11-2026 05:40 | xong |
