# Sổ giữ chỗ — làn Phân quyền · Đợt TR-2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TR-2 — MÀN GHÉP TOUR WEB ĐỌC ĐỦ CÁC KHU «XEM THÊM»** (Chủ tịch «làm từ 1 đến 4» 03/11/2026). Hai trang danh sách `tour-trong-nuoc` / `tour-nuoc-ngoai` chỉ in vài tour mỗi miền rồi để nút «Xem thêm» → `/vn/tour/area/?area=N` (mỗi khu chia trang `&page=K`); bộ đọc cũ chỉ lấy hai trang đầu nên màn «Tour online → tour trên web» thấy 57/105 tour đang bán. Nay `doc_ds_web()` đọc thêm mọi khu ghi trên hai trang ấy, lần lượt từng trang tới khi không còn tour mới (trần 40 trang/khu, 6 khu song song); số khu chỉ nhận chữ số và link tự dựng trên tên miền Vietourist. Khu hỏng thì giữ phần đã đọc và ghi lỗi. Phép thử test_tr2 (4, hai chiều). Không đổi quyền, không đổi giao diện. | backend/app/services/tour_online.py, backend/tests/test_tr2_doc_du_khu_web.py, docs/dang-lam/phan-quyen/TR-2.md | 03-11-2026 01:40 | xong |
