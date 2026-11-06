# Sổ giữ chỗ — làn Phân quyền · Đợt KS-20b

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-20b — ĐẶT PHÒNG VTD v1.3, ĐỢT 2: NHIỀU PHÒNG (TỐI ĐA 9), KHAI KHÁCH TỪNG PHÒNG** (bản xem trước D2 / M1 / M2 / D6 đã duyệt 05/11/2026; 06/11 Chủ tịch chọn «Máy nhận đúng cách chia»). Khách khai từng phòng {người lớn, trẻ em, tuổi từng bé}; máy ghép mỗi phòng đã chọn với một nhóm khách hợp sức chứa (phòng rộng cho nhóm đông, ghép cặp khi kẹt), tính phụ thu trẻ em / giường phụ theo đúng người trong từng phòng; khách đổi cách ghép được; số phòng chọn phải bằng số phòng khai. Đơn ghi «Phòng 1 — … · loại phòng · gói» cho Điều hành gửi khách sạn; dòng đơn lưu `khach` (không thêm cột). Giao diện: ô «Phòng và khách» khai từng phòng, khung «Chia phòng» trên trang khách sạn, ô «Số phòng» mỗi gói, giá «/phòng · N đêm», cột «Đã chọn x/y phòng» (điện thoại: thanh dưới). Một phòng thì giữ nút «Đặt ngay» như cũ. | backend/app/services/khach_san_vtd.py, backend/app/services/don_ks_vtd.py, backend/app/api/v1/khach_san_vtd.py, backend/app/api/v1/don_ks_vtd.py, web/components/cong/KhachSanVtd.tsx, backend/tests/test_ks20b_chia_phong.py, docs/dang-lam/phan-quyen/KS-20b.md | 06-11-2026 22:10 | đang làm |
