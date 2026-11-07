# Sổ giữ chỗ — làn Phân quyền · Đợt KS-K2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-K2 — CI ĐẦY ĐỦ TRÊN MAIN XANH LẠI** (Chủ tịch 07/11/2026 chọn «Kiểm CI main»). Lần chạy CI đầy đủ trên main sau #693 đỏ ở hai chỗ: (1) `test_dontckt_dong_hai_dong_oi` vì sổ KS-19p — đã sửa ở #695; (2) `test_k2_doc_an_toan`: phiếu/thư đặt phòng VTD của #692 (KS-20e) đọc cột tiền `tong`, `tien_phong`, `giam_voucher` mà không chặn rỗng (6 chỗ). Sửa theo cách 1 của luật K2: bọc `or 0` tại chỗ đọc. Hàm `_vnd` vốn đã coi rỗng là 0 nên phiếu in ra KHÔNG đổi một chữ; chỉ là nói rõ ở chỗ đọc để phép quét canh cửa nhận ra. | backend/app/services/phieu_ks_vtd.py, docs/dang-lam/phan-quyen/KS-K2.md | 07-11-2026 08:40 | xong |
