# Sổ giữ chỗ — làn Phân quyền · Đợt KS-GT2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-GT2 — HÀNG RÀO GỘP XANH LẠI SAU #712** (Chủ tịch 07/11/2026 chọn «Em tự sửa phép thử»). #712 (GTGT-2) và #713 (CPTT-2) gộp khi `hang-rao-gop` đỏ: hàng rào chạy nhiều tệp trong một tiến trình, `test_gtgt1` chạy trước đặt kỳ kê khai thẳng vào CSDL, nên `test_gtgt2_3` đọc `da_bat = True` và đỏ — chặn mọi PR sau đó (gặp ở #714). Tái hiện đúng khi chạy gtgt1 trước gtgt2. Sửa: `test_gtgt2_3` tự dựng cảnh «chưa đặt» (đặt rỗng rồi trả lại giá trị cũ) thay vì trông vào dữ liệu mẫu; luật «bộ mặc định để trống» vẫn do `test_gtgt1_4` canh. Không đổi mã máy chủ, không đổi màn hình. | backend/tests/test_gtgt2_the_bu_tru_gtgt.py, docs/dang-lam/phan-quyen/KS-GT2.md | 07-11-2026 22:40 | đang làm |
