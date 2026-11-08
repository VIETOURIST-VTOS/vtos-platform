# Đợt TGIA-1 — Tách chênh lệch tỷ giá về tài khoản chi tiết (08/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TGIA-1 — nắn 413 / 632 / 635 / 515 của bút toán tách tỷ giá | backend/app/services/tk_chi_tiet.py, backend/app/services/chenh_lech_ty_gia.py, backend/tests/test_tgia1_tach_ty_gia_tai_khoan_con.py, backend/tests/test_ky3_chenh_lech_ty_gia.py, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/TGIA-1.md | 08-11-2026 10:10 | xong |

Đo trên sổ thật: mốc tách ĐÃ BẬT (`tach_ty_gia_tu_ngay` = 2026-10-09) nhưng tách được 0 dòng ở
cả ba kỳ — chưa bút toán nào rơi vào tài khoản cha, lúc rẻ nhất để nắn. Lỗ → `6352`, lãi →
`5154`, giá vốn → `6326` (một dòng cho cả kỳ), đánh giá lại → `4131`. Bốn hằng số gốc GIỮ NGUYÊN
cho phép đọc cây. KHÔNG đổi một con số tiền nào, KHÔNG đụng bảng quyền.
