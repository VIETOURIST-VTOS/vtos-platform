# Đợt NH-1 — Bộ đọc Sổ tiền gửi hỏi tên cột, không đếm cột (09/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | NH-1 — bộ đọc Sổ tiền gửi MISA đọc cột theo TÊN và xử lý hậu tố mã chứng từ | backend/app/services/banks.py, backend/tests/test_nh1_bo_doc_so_tien_gui.py, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/NH-1.md | 09-11-2026 00:20 | xong |

Đo trên sổ thật 08/11/2026 sau khi nạp bản đồ chứng từ hai năm: gán được 10/27 dòng còn nằm
trên `1121`, và CẢ MƯỜI khớp bằng lớp «chứng từ chỉ thuộc 1 ngân hàng» — không một dòng nào
khớp bằng lớp có số tiền, vì mọi số tiền trong bản đồ là MÃ TÀI KHOẢN (`3388`, `1121`). Nguyên
nhân: MISA in cùng báo cáo ra hai bố cục (8 cột và 13 cột), bộ đọc gõ cứng `row[5]`/`row[6]`.
Lỗi thứ hai cùng bản chất: mã `MISA-FT26167686276948-0617` trượt vì sổ MISA ghi
`FT26167686276948`, trong khi 7.860 chứng từ khác mang hậu tố `-NNNN` THẬT nên không được cắt
bừa. Đợt này KHÔNG ghi một dòng sổ nào, KHÔNG đụng bảng quyền, KHÔNG đụng giao diện.
