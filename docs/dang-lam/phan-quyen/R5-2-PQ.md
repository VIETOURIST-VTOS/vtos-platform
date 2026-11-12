# Sổ giữ chỗ — làn Phân quyền · Đợt R5-2-PQ

Một đợt một tệp. Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **R5-2-PQ — quyền của /fit sau khi gộp /kinh-doanh-le** (việc chính ở `../r5/R5-2.md`). MENU_ROLES["/fit"] = BASE_VIEW + SALES (Chủ tịch chốt 13/11/2026: chỉ phòng Kinh doanh lẻ); `/fit` đổi nhóm API sang `/api/v1/kinh-doanh` (tab doanh thu); bỏ `/api/v1/bao-cao` khỏi dòng /fit để nhân viên, trưởng nhóm không đọc được báo cáo phòng (`test_bao_cao_phong` canh) — ai có bảng chỉ tiêu nhận nhóm ấy qua dòng `/bao-cao`. | backend/app/services/access.py, docs/dang-lam/phan-quyen/R5-2-PQ.md | 13-11-2026 04:55 | đang làm |
