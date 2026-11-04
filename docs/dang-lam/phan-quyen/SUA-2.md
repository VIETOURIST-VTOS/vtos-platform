# Sổ giữ chỗ — làn Phân quyền · Đợt SUA-2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **SUA-2 — CỬA `/hach-toan/bang` CHO NÚT ĐÃ CHI** (Chủ tịch «tiếp tục» 02/11/2026; đặt lại sau #618 vì P2-2 đã nối mạch migration và chữa hai bảng chốt). Màn /expenses gọi `/hach-toan/bang` (P2-1 đã khai vào bản đồ) nhưng máy chủ KHÔNG CÓ đường ấy — ô «Hình thức thanh toán» khi bấm ĐÃ CHI luôn rỗng → thêm cửa ĐỌC `GET /hach-toan/bang` trả đúng danh mục tĩnh `HINH_THUC_TT` cho nhóm vai đề nghị chi + thủ quỹ; bảng quy ước đầy đủ vẫn chỉ `XEM`. Khai `api/v1/hach_toan.py: thu_quy` ở test_le2b; test_lg1 lg4 gạch hai món nợ robot_ks (/hach-toan, /ket-so) vì cửa đọc mới. Không đổi quyền ghi nào, không đổi bản đồ màn hình. | backend/app/api/v1/hach_toan.py, backend/tests/test_le2b_ba_vai_ke_toan.py, backend/tests/test_lg1_hai_bang_quyen_khop_nhau.py, docs/dang-lam/phan-quyen/SUA-2.md | 02-11-2026 08:45 | xong |
