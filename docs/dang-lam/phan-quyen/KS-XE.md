# Sổ giữ chỗ — làn Phân quyền · Đợt KS-XE

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-XE — KHỐI HIỆU QUẢ ĐỘI XE + ĐO KHỐI KPI LÃNH ĐẠO** (Chủ tịch 07/11/2026 chọn «Sửa tiếp 2 khối 3 giây»). Số đo `do_ms` trên crm sau #711: một lần dựng 11 giây (trước 28–38), còn `dh_hieu_qua_xe` 3,0 giây và `kpi_lanh_dao` 3,5 giây. Hiệu quả đội xe: tháng đã đóng nhớ tối đa 6 giờ qua các lần dựng, xoá ngay khi có ghi vào bảng đội xe / nhân sự / tài chính / kế toán / booking / tham số (bắt ở `after_flush`) hoặc khi bấm làm mới; chỉ bảng điều hành dùng, màn chi tiết đội xe tính như cũ; số trùng khớp cách cũ. KPI lãnh đạo: thêm đo bốn phần (số dư–nợ vay–phải thu, dự báo 13 tuần, lãi lỗ tháng, kế hoạch) để sửa đúng chỗ. | backend/app/services/hieu_qua_xe.py, backend/app/services/dashboard.py, backend/app/api/v1/routes.py, backend/tests/test_ks_xh_xu_huong_nho_thang_cu.py, docs/dang-lam/phan-quyen/KS-XE.md | 07-11-2026 22:15 | xong |
