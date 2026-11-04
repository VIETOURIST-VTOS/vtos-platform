# Sổ giữ chỗ — làn Phân quyền · Đợt KS-ANH

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-ANH — PHÒNG CHƯA CÓ ẢNH RIÊNG LẤY ẢNH ĐẠI DIỆN KHÁCH SẠN** (Chủ tịch 05/11/2026: «khách sạn nào chưa có ảnh phòng em lấy ảnh đại diện khách sạn»). Cổng khách `chi_tiet_cong`: loại phòng không có ảnh gắn `loai_phong_id` thì hiện ảnh bìa của khách sạn (`_anh_duyet` xếp bìa lên đầu), cờ `anh_dai_dien` = true; có ảnh riêng thì chỉ ảnh riêng. Không đổi dữ liệu ảnh, không nhân bản tệp. Phép thử test_ks_anh_dai_dien_phong (1). | backend/app/services/khach_san_vtd.py, backend/tests/test_ks_anh_dai_dien_phong.py, docs/dang-lam/phan-quyen/KS-ANH.md | 05-11-2026 04:00 | đang làm |
