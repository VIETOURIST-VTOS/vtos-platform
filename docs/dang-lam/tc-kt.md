# Sổ giữ chỗ — làn TC-KT (Tài chính – Kế toán)

Luật và lý do tách tệp: [README.md](README.md). Cột giữ nguyên như quyển sổ cũ.
Mọi dòng trong tệp này PHẢI có cột `Làn` là `TC-KT` — hàng rào `test_giu_cho_lan.py` canh.

Làn này mở ngày 02/11/2026. Trước đó mọi đợt của phân hệ Tài chính – Kế toán ghi vào
`phan-quyen.md`, và bốn nhánh R4c liên tiếp không gộp được vì cùng nối vào cuối một tệp.
**Dòng cũ nằm lại bên ấy** — xem phần bổ sung 02/11 trong README.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | **LAN-TCKT — MỞ LÀN RIÊNG CHO TÀI CHÍNH – KẾ TOÁN** (Chủ tịch chốt 02/11/2026 sau khi bốn nhánh R4c lần lượt không gộp được). Việc tách ngày 06/10 chạy đúng — làn `at2-nha-hang-agoda` gộp hôm nay mà không đụng `phan-quyen.md`. Nhưng bốn đợt R4c đều khai làn «Phân quyền» nên cùng nối vào cuối một tệp; đo được `phan-quyen.md` **444 KB · 187 dòng · 16 dòng «đang làm»** trong khi `vpm.md` là 334 byte. Cùng một hỏng hóc của 06/10, ở một tầng sâu hơn. Đợt này khai `"TC-KT": "tc-kt"` trong `LAN_TEP`, tạo tệp này, và thêm một dòng vào bảng của README. KHÔNG dời một dòng nào của ai (luật 5 canh: số dòng «đang làm» của `phan-quyen.md` không được giảm). Đo trước khi vá rằng hàng rào N2 nhận tệp sổ theo KHUÔN ĐƯỜNG DẪN chứ không theo danh sách làn — nếu nó cũng có danh sách gõ tay thì đợt này mới thiếu một nửa. Sáu luật ở `test_lantckt_lan_rieng.py`. | backend/tests/test_giu_cho_lan.py, backend/tests/test_lantckt_lan_rieng.py, docs/dang-lam/README.md, docs/dang-lam/tc-kt.md | 02-11-2026 06:40 | xong |
