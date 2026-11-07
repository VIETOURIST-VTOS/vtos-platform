# Sổ giữ chỗ — làn Phân quyền · Đợt KS-KD

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-KD — KHỐI KINH DOANH VÀ DỰ BÁO 13 TUẦN CỦA BẢNG ĐIỀU HÀNH** (Chủ tịch 07/11/2026 chọn «Bảng điều hành: Kinh doanh + Dự báo»). Đo trên crm: `kinh_doanh` 1,4 giây (doanh thu theo phòng gọi `ket_qua_that.thang` cho từng tháng từ tháng 1), `ld_du_bao_13_tuan` 1,0 giây (dự báo cộng lại cả sổ kế toán để lấy số dư đầu kỳ, trong khi bảng vừa có số ấy). Sửa: (1) kết quả `ket_qua_that.thang` của tháng đã đóng nhớ qua lần dựng, cùng chỗ nhớ và cùng cách xoá của KS-XH (ghi sổ là xoá, làm mới là xoá); (2) `forecast_13w` nhận `opening` tuỳ chọn, bảng điều hành truyền `k["tien"]` — cùng `RP.balances`, cùng kỳ. Không đổi con số: phép thử so trùng khớp cách cũ. | backend/app/services/xu_huong.py, backend/app/services/dashboard.py, backend/app/services/finance.py, backend/tests/test_ks_xh_xu_huong_nho_thang_cu.py, docs/dang-lam/phan-quyen/KS-KD.md | 07-11-2026 23:35 | xong |
