# Sổ giữ chỗ — làn Phân quyền · Đợt VH-3

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
| Phân quyền | **VH-3 — MÀN GỌN CHO NĂM TRANG ĐIỀU XE CÒN LẠI + Ô «CHỜ TÔI KÝ»** (Chủ tịch duyệt bản xem trước 10/11/2026). Đề nghị xe (đếm + dòng chờ lệnh, nút «Lập lệnh» mở sẵn mẫu, «Không còn xe» kèm lý do), Lập lệnh (đề nghị chờ, lệnh 7 ngày tới kèm tài xế đã nhận chưa), Xe hôm nay (từ lệnh VTOS + báo hỏng phải dừng, không từ sheet), Tài xế (thiếu bằng / bằng sắp hết hạn / chưa có tài khoản), Chủ xe & hợp đồng (kỳ chốt gần nhất). Ô «Chờ tôi ký» ở Báo cáo từng xe chỉ mời đúng vai đang giữ bước (CHO_BUOC × VAI_KY). Máy chủ: `/fleet/lenh-dieu-xe` thêm trạng thái nhận; `/tai-xe` thêm `co_tai_khoan`; cửa mới `/fleet/xe-hom-nay-gon`, `/fleet/quyet-toan-chuyen/cho-toi-ky`. | backend/app/api/v1/fleet.py, backend/app/services/tai_xe.py, backend/tests/test_vh3_man_gon_dieu_xe.py, web/app/xe/page.tsx, web/components/doixe/TrangGon.tsx, docs/dang-lam/phan-quyen/VH-2.md, docs/dang-lam/phan-quyen/VH-3.md | 10-11-2026 11:00 | đang làm |
