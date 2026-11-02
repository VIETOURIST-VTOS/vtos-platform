# Sổ giữ chỗ — làn Phân quyền · Đợt SUA-2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **SUA-2 — CHỮA HAI CHỖ CÒN ĐỎ / CÒN HỎNG SAU P2-1** (Chủ tịch «tiếp tục» 02/11/2026). (1) Màn /expenses gọi `/hach-toan/bang` (P2-1 đã khai vào bản đồ) nhưng máy chủ KHÔNG CÓ đường ấy — ô «Hình thức thanh toán» khi bấm ĐÃ CHI luôn rỗng → thêm cửa ĐỌC `GET /hach-toan/bang` trả đúng danh mục tĩnh `HINH_THUC_TT` cho nhóm vai đề nghị chi + thủ quỹ; bảng quy ước đầy đủ vẫn chỉ `XEM`. (2) test_le2b đỏ: R4c-4 mở `POST /receipts/cash` cho `thu_quy` mà quên khai → khai, kèm cửa đọc mới. (3) test_lg1 lg9 đỏ: P2-1 đổi PHAM_VI_DA_CHOT ketoan_tt 31→32, thu_quy 27→28 nhưng quên theo ở lg9 → theo; lg4 gạch hai món nợ robot_ks (/hach-toan, /ket-so) vì cửa đọc mới. (4) KHẨN: mạch migration có HAI ĐẦU (`dk2b5e8c1f3a7d49` DK-2 và `tr1d4b6c8e0a2f13` TR-1d cùng nối sau dk1a7…) → `alembic upgrade head` dừng, máy chủ không lên bản mới. TR-1d gộp trước nên máy thật đã ở tr1d4…; nối dk2b… SAU tr1d4… (đổi down_revision, không merge revision — đúng luật test_mach_migration). Không đổi quyền ghi nào, không đổi bản đồ màn hình. | backend/app/api/v1/hach_toan.py, backend/tests/test_le2b_ba_vai_ke_toan.py, backend/tests/test_lg1_hai_bang_quyen_khop_nhau.py, backend/alembic/versions/dk2b5e8c1f3a7d49_dang_nhap_va_may_da_nho.py, docs/dang-lam/phan-quyen/SUA-2.md | 02-11-2026 08:20 | đang làm |
