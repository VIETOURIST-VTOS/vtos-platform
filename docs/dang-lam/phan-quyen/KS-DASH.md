# Sổ giữ chỗ — làn Phân quyền · Đợt KS-DASH

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-DASH — BẢNG ĐIỀU HÀNH CRM KHÔNG BẮT CHỜ 38 GIÂY** (Chủ tịch 07/11/2026 chọn «Cả hai bước»). Đo trên crm thật: dựng lại 37,8 giây, bản nhớ 0,3 giây. Bản nhớ quá 5 phút bị bỏ, robot chỉ dựng lại khi có người ghi → lúc vắng và sau mỗi lần cập nhật máy chủ thì người mở trang phải chờ. Bước 1: còn bản nhớ là trả ngay (kèm `tuoi_giay`) và đánh dấu cũ; robot dựng lại khi có ghi, khi bản quá 4 phút, hoặc khi bản nhớ trống (vừa khởi động → dựng sẵn cho Chủ tịch ngay phút đầu). Bước 2: mỗi lần dựng ghi mili-giây từng khối vào `do_ms` và nhật ký máy chủ để tìm khối chậm. Không đổi phép tính, không đổi màn hình. | backend/app/api/v1/routes.py, backend/app/main.py, backend/app/services/dashboard.py, backend/tests/test_ks_nhanh_dashboard_luon_co_san.py, docs/dang-lam/phan-quyen/KS-DASH.md | 07-11-2026 08:00 | xong |
