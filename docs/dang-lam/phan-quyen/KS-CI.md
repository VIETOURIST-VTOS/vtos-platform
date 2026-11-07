# Sổ giữ chỗ — làn Phân quyền · Đợt KS-CI

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-CI — CI ĐẦY ĐỦ TRÊN MAIN XANH LẠI SAU TKC-3/4 VÀ CPTT-2** (Chủ tịch 08/11/2026 chọn «Em sửa 3 phép thử»). Lần chạy CI đầy đủ sau #720 và #721 đỏ ba phép thử cũ: `test_nonpackage` và `test_settlement` còn chờ bút toán vào tài khoản cha 632 / 154, nhưng TKC-3/4 (#720, #723) đã cố ý ghi vào tài khoản chi tiết 6321 / 1541; `test_nap_v4` nạp CCDC thiếu cột `tk_chi_phi` mà CPTT-2 (#713) vừa bắt buộc nên dừng ở lỗi khác trước luật đang đo. Chỉ cập nhật phép thử theo luật đã gộp; không đổi mã kế toán. | backend/tests/test_nonpackage.py, backend/tests/test_settlement.py, backend/tests/test_nap_v4.py, docs/dang-lam/phan-quyen/KS-CI.md | 08-11-2026 04:20 | đang làm |
