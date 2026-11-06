# Sổ giữ chỗ — làn Phân quyền · Đợt KS-19o

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-19o — BỐN PHÉP THỬ ĐỎ TRÊN MAIN SAU KS-19k** (Chủ tịch «sửa cả A, B, C»; CI main 3af8ca5). (1) KS-7 C2 coi bảng đã bỏ là bảng không có mô hình: chỉ đọc upgrade() và trừ bảng op.drop_table. (2) V9 không đọc được cột tiền của bảng phụ bao_gia_thiet_ke viết qua hàm: bản nâng cấp KS-19k viết thẳng cột (cùng cột, cùng kiểu, không đổi hành vi). (3) TR-1d bom hẹn giờ: «hết hạn» của link đoàn xét theo ngày tiền về, không theo lúc robot chạy. (4) Q2-A bom hẹn giờ: hạn liên hệ của phiếu chăm sóc thử tính từ hôm nay. | backend/alembic/versions/ks19k4d6f8a0c2e135_gop_bao_gia_doan.py, backend/app/services/thanh_toan_doan.py, backend/tests/test_ks7_bang_khong_co_cua_mo_rong.py, backend/tests/test_q2a_dem_luot_doc.py, backend/tests/test_ks19o_bom_hen_gio_main.py, docs/dang-lam/phan-quyen/KS-19o.md | 06-11-2026 10:40 | xong |
