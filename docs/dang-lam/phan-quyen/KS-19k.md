# Sổ giữ chỗ — làn Phân quyền · Đợt KS-19k

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-19k — GỘP BÁO GIÁ ĐOÀN VÀO BẢNG BÁO GIÁ CHUNG** (Chủ tịch chọn phương án 1 ngày 06/11/2026: «đầu chung + bảng phụ», «quy về tên trạng thái chung», «màn Bán hàng hiện, chỉ xem»). Phép thử V6 «lẻ và đoàn dùng chung một bảng» đỏ vì TK-2 tách bảng `bao_gia_doan`. Đầu báo giá (mã BGD-…, mảng kd_doan, khách, trạng thái, người lập / duyệt) về `bao_gia` với cột mới `nguon` = thiet_ke; phần riêng (dòng tạm tính + giá vốn, hệ số trẻ em, số NL/TE/EB, hạn 24 giờ, mã băm) sang bảng phụ `bao_gia_thiet_ke`, khóa = id dòng đầu. da_duyet → da_gui, khach_dong_y → khach_chot. Hợp đồng nháp khách đồng ý nối `bao_gia_id`. Màn /bao-gia hiện dòng đoàn kèm giá bán, ẩn nút sửa / gửi / chốt / lập HĐ; máy chủ chặn bốn thao tác ấy. Migration chép dữ liệu cũ rồi bỏ bảng cũ (đã thử lên / xuống trên Postgres). | backend/alembic/versions/ks19k4d6f8a0c2e135_gop_bao_gia_doan.py, backend/app/api/v1/ban_hang.py, backend/app/models/ban_hang.py, backend/app/models/thiet_ke_doan.py, backend/app/services/ban_hang.py, backend/app/services/bao_gia_doan.py, backend/app/services/ks_cua_nhap.py, backend/tests/test_tk2_bao_gia_doan.py, backend/tests/test_ks19k_gop_bao_gia_doan.py, web/app/bao-gia/page.tsx, web/app/tour-doan/page.tsx, web/components/cong/TuThietKeTour.tsx, docs/dang-lam/phan-quyen/KS-19k.md | 06-11-2026 07:00 | đang làm |
