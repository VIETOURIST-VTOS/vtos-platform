# Sổ giữ chỗ — làn Phân quyền · Đợt KS-SD

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-SD — SỐ DƯ TIỀN · NỢ VAY · PHẢI THU NHỚ GIỮA CÁC LẦN DỰNG** (Chủ tịch 07/11/2026 chọn «Nhớ số dư, ghi sổ là tính lại»). Số đo `do_ms` trên crm sau #714: một lần dựng 5,7 giây, trong đó `ld_so_du_no_vay_phai_thu` 1,2 giây — `RP.balances` cộng lại toàn bộ sổ (hơn 25 nghìn chứng từ) mỗi vài phút. Sửa: ba con số nhớ theo kỳ, XOÁ NGAY khi có ghi vào sổ kế toán, hợp đồng tài chính hoặc booking (bắt ở `after_flush`) hoặc khi bấm làm mới. Phép tính chuyển nguyên vào `_so_du_no_vay_phai_thu`, không đổi một con số. | backend/app/services/dashboard.py, backend/app/api/v1/routes.py, backend/tests/test_ks_xh_xu_huong_nho_thang_cu.py, docs/dang-lam/phan-quyen/KS-SD.md | 07-11-2026 22:55 | xong |
