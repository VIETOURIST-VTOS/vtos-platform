# Sổ giữ chỗ — làn Phân quyền · Đợt TK-1f

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TK-1f — LỊCH NGÀY LỄ TẾT MÁY TÍNH THEO LUẬT (HDV ×2)** (Chủ tịch 04/11/2026: «áp dụng theo đúng ngày nghỉ»; Tết Âm lịch tính mùng 1, 2, 3, 4; Quốc khánh lấy 1/9). Máy tính mỗi năm: 1/1; mùng 1–4 Tết Nguyên đán; Giỗ Tổ 10/3 âm lịch; 30/4; 1/5; 1/9 và 2/9; 24/11 (Ngày Văn hóa Việt Nam, áp dụng từ 1/7/2026). Đổi âm → dương bằng thuật toán Hồ Ngọc Đức múi giờ +7 (services/am_lich.py), kiểm Tết 2024–2027, Giỗ Tổ 2025/2027. Ngày Điều hành nhập (TK-1e) vẫn cộng thêm — dùng cho ngày hoán đổi. Thẻ «Ngày lễ Tết» ở /tour-doan hiện lịch máy tính năm nay và năm sau. Phép thử test_tk1 (+2). | backend/app/services/am_lich.py, backend/app/services/thiet_ke_doan.py, backend/tests/test_tk1_tu_thiet_ke_tour_doan.py, web/app/tour-doan/page.tsx, docs/dang-lam/phan-quyen/TK-1f.md | 04-11-2026 03:20 | xong |
