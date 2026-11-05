# Sổ giữ chỗ — làn Phân quyền · Đợt TR-4

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TR-4 — BỘ LỌC TÌM TOUR: ĐỦ MỨC GIÁ VÀ ĐỦ PHƯƠNG TIỆN** (Chủ tịch 03/11/2026 «bổ sung trên 5 triệu, phương tiện: xe du lịch, máy bay, tàu hỏa, du thuyền», «đẩy TR-4»). Nhóm «Giá mỗi khách» và «Phương tiện» luôn hiện đủ mức (Dưới 2 / 2–5 / Trên 5 triệu; Xe du lịch / Máy bay / Tàu hỏa / Du thuyền), mức chưa có tour thì mờ, số 0, không bấm được; các nhóm khác vẫn ẩn mức trống. Tên «Xe» đổi thành «Xe du lịch» (models/tour_online.PHUONG_TIEN_TOUR). Lọc giá dùng giá chuyến, tour chưa có lịch (TR-3) dùng giá tham khảo trên web. Không đổi quyền, không đổi dữ liệu. Phép thử test_tr4 (3). | web/components/cong/ToursAgoda.tsx, backend/app/models/tour_online.py, backend/tests/test_tr4_loc_gia_phuong_tien.py, docs/dang-lam/phan-quyen/TR-4.md | 03-11-2026 21:05 | xong |
