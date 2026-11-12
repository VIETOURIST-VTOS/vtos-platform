# Sổ giữ chỗ — làn Phân quyền · Đợt R5-1-PQ

Một đợt một tệp. Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **R5-1-PQ — phần quyền của bàn GĐ Kinh doanh lẻ `/ban-kd-le`** (việc chính ở sổ làn R5, `../r5/R5-1.md`). Thêm dòng `/ban-kd-le` vào MENU_ROLES (BASE_VIEW + gd_kd + cntt, Chủ tịch chốt 13/11/2026) và nhóm `/api/v1/ban-kd-le`; bảng phạm vi đã chốt +1 cho sáu vai. Khai ở làn này vì `access.py` là tệp nóng chỉ làn Phân quyền hoặc TC-KT được giữ (`test_donpq_5`). | backend/app/services/access.py, backend/tests/test_p2_pham_vi_vai_tro.py, docs/dang-lam/phan-quyen/R5-1-PQ.md | 13-11-2026 04:10 | đang làm |
