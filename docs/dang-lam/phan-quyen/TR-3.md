# Sổ giữ chỗ — làn Phân quyền · Đợt TR-3

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TR-3 — TOUR GHÉP CHƯA CÓ CHUYẾN VẪN HIỆN KHI TÌM (ĐÃ GHÉP WEB)** (Chủ tịch «Ok làm» 02/11/2026, đã duyệt bản xem thử). Trước đây tìm tour ẩn mọi tour ghép chưa có chuyến mở bán → 82 tour mã W… và phần lớn tour web không hiện; bấm vào thì 404. Nay: sản phẩm đang hoạt động đã ghép link web mà chưa có chuyến vẫn hiện — `chua_co_lich`, giá tham khảo lấy từ bảng giá web (`gia_web`) hoặc «Giá liên hệ», xếp sau tour có ngày đi, không khớp khi lọc khoảng ngày; trang chi tiết mở được và dùng ô «Gửi yêu cầu giữ chỗ» (đi vào luồng yêu cầu sẵn có, ghi chú «Tour ghép chưa có lịch»). Chưa ghép web và chưa có chuyến thì vẫn ẩn. Có chuyến thì về như cũ. Không đổi quyền, không đổi thanh toán. Phép thử test_tr3 (4). | backend/app/services/tour_online.py, web/components/cong/ToursAgoda.tsx, backend/tests/test_tr3_tour_chua_co_lich.py, docs/dang-lam/phan-quyen/TR-3.md | 02-11-2026 19:40 | xong |
