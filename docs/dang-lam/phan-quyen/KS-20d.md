# Sổ giữ chỗ — làn Phân quyền · Đợt KS-20d

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-20d — TÌM NHIỀU PHÒNG GHÉP ĐƯỢC NHIỀU LOẠI PHÒNG** (thử thật 06/11/2026 trên kh.vietourist.vn: tìm 3 phòng ở Đà Lạt ra 0 khách sạn vì máy bắt MỘT loại phòng còn đủ 3 phòng, mà mỗi loại chỉ còn 2; Chủ tịch chọn «Cộng các loại phòng»). Nhiều phòng: mỗi loại phòng có gói hợp người chỉ cần còn ≥ 1 phòng; khách sạn hiện khi TỔNG số phòng còn của các loại ấy ≥ số phòng khách cần. Một phòng giữ như cũ. Không đổi giá, ghép phòng, đặt. | backend/app/services/khach_san_vtd.py, backend/tests/test_ks20d_tim_nhieu_loai_phong.py, docs/dang-lam/phan-quyen/KS-20d.md | 06-11-2026 23:40 | xong |
