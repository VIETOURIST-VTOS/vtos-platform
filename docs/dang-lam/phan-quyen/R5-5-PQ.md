# Sổ giữ chỗ — làn Phân quyền · Đợt R5-5-PQ

Một đợt một tệp. Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **R5-5-PQ — bỏ màn `/ban-kd-le` khỏi ma trận quyền** (việc chính ở `../r5/R5-5.md`). Gỡ `/ban-kd-le` khỏi MENU_ROLES và MAN_HINH_API; `MAN_HINH_API["/fit"]` thêm `/api/v1/ban-kd-le` (cửa tự gác vai bằng `ban_kd_le.XEM`). Phạm vi: nv_kd, tn_kd 60 → 61, tp_kd 65 → 66 (chạm nhóm nhưng cửa trả 403); cntt 137 → 136. | backend/app/services/access.py, backend/tests/test_p2_pham_vi_vai_tro.py, docs/dang-lam/phan-quyen/R5-5-PQ.md | 13-11-2026 07:10 | xong |
