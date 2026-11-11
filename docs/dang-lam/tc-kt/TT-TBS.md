# Đợt TT-TBS — trả bổ sung + chi một phần trong sổ Đề nghị chi 05-TT (10/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TT-TBS — bước `tra_bo_sung` + `gui_lai` (giữ mã, xoá chữ ký, lưu bản trước); bước `pay` nhận số tiền từng lần, mỗi lần một UNC và một bút toán (mã nguồn `dc:<mã>/lanN` từ lần 2). Kèm `khoan_goc` / `de_nghi_theo_khoan_goc` / `chung_tu_trung` (chống ghi chi phí hai lần). Khai ở sổ làn TC-KT theo cho phép của Chủ tịch 10/11/2026. Phần còn lại ở [../phan-quyen/TT-TBS.md](../phan-quyen/TT-TBS.md). | backend/app/services/ops.py, backend/app/api/v1/ops.py, docs/dang-lam/tc-kt/TT-TBS.md | 10-11-2026 02:30 | xong |
