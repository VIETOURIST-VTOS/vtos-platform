# Sổ giữ chỗ — làn Phân quyền · Đợt SUA-4

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **SUA-4 — VPM-8: BỐN BẢNG CÓ CỘT `phien_ban` CHƯA XẾP CHỖ** (Chủ tịch «em làm luôn» 02/11/2026, sau #621). test_vpm8 a1 đỏ sẵn trên main: doi_tac_ota, dat_phong_ota, so_hoa_hong_ota, hop_dong_nha_hang mang cột `phien_ban` nhưng chưa khai ở ghi_mot_lan.py. Ở bốn bảng này cột ấy là SỐ BẢN nội dung (link OTA, dòng đặt phòng sau đối soát, sổ hoa hồng chép bản, hợp đồng nhà hàng ký lại), không phải khoá ghi một lần — gắn kiem_phien_ban sẽ trả 409 sai. Thêm danh mục thứ tư `PHIEN_BAN_NGHIA_KHAC` kèm lý do từng bảng; vpm8 a1/a4 đọc thêm danh mục ấy. Không đổi mã nghiệp vụ OTA / nhà hàng, không đổi quyền. | backend/app/services/ghi_mot_lan.py, backend/tests/test_vpm8_khoa_phien_ban.py, docs/dang-lam/phan-quyen/SUA-4.md | 02-11-2026 22:30 | đang làm |
