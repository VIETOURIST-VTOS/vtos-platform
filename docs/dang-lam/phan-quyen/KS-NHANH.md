# Sổ giữ chỗ — làn Phân quyền · Đợt KS-NHANH

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-NHANH — BA TRANG CHẬM CÒN LẠI: CÔNG NỢ, BÁO CÁO NGÀY, KẾT SỔ** (Chủ tịch 08/11/2026 duyệt «Sửa cả 4 trang»; Tài chính ở KS-TC). Đo crm thật hai lượt: `/cong-no` 4,0–5,3 s (nạp nguyên mọi booking và mọi tour để giữ dòng còn chênh); `/daily-reports/tong-hop` 4,3–4,8 s (mỗi nhân viên hỏi riêng ngày nghỉ, báo cáo, hạn nộp, số tệp, lịch sử xem); `/ket-so/tach-ty-gia/xem-truoc` và `/ket-so/bu-tru-gtgt/xem-truoc` 4,3–4,8 s (nạp toàn bộ bảy bảng ngoại tệ; quét sổ cái năm lần). Sửa: lọc trong SQL và chỉ kéo cột cần; nạp sẵn một lần cho cả bảng; một lần quét sổ cái thay năm. Cách cũ giữ làm thước, phép thử so bằng nhau. Không đổi số. | backend/app/services/debts.py, backend/app/services/ops.py, backend/app/services/bao_cao_ngay_xem.py, backend/app/services/ket_so.py, backend/app/services/chenh_lech_ty_gia.py, backend/tests/test_ks_cn_bc_nhanh.py, backend/tests/test_ks_kso_ket_so_nhanh.py, docs/dang-lam/phan-quyen/KS-NHANH.md | 08-11-2026 06:40 | đang làm |
