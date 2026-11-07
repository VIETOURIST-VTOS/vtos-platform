# Sổ giữ chỗ — làn Phân quyền · Đợt KS-XH

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-XH — KHỐI XU HƯỚNG VÀ ĐIỀU HÀNH CỦA BẢNG ĐIỀU HÀNH** (Chủ tịch 07/11/2026 chọn «Sửa Xu hướng + Điều hành»). Số đo `do_ms` trên crm sau #708: dựng 28 giây, xu hướng 14 giây, điều hành 6 giây; dựng chồng nhau (robot + làm mới) thì 80 giây. Sửa: (1) một hàm đọc dùng chung cho cả lần dựng, không hỏi trùng tháng; (2) tháng đã đóng nhớ tối đa 6 giờ, xoá ngay khi có ghi vào bảng mà xu hướng đọc (bắt ở tầng cơ sở dữ liệu) hoặc khi bấm làm mới; (3) một lần dựng một lúc, lần đến sau dùng luôn kết quả; (4) đo từng khối con của Điều hành để sửa vòng sau. Số trên màn hình không đổi — phép thử so trùng khớp với cách cũ. | backend/app/services/xu_huong.py, backend/app/services/dashboard.py, backend/app/api/v1/routes.py, backend/tests/test_ks_xh_xu_huong_nho_thang_cu.py, docs/dang-lam/phan-quyen/KS-XH.md | 07-11-2026 09:10 | đang làm |
