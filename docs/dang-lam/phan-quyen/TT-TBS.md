# Sổ giữ chỗ — làn Phân quyền · Đợt TT-TBS

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TT-TBS — TRẢ BỔ SUNG + CHI MỘT PHẦN cho MỌI đề nghị chi 05-TT** (Chủ tịch duyệt bản xem trước 10/11/2026). Người giữ bước trả hồ sơ về người lập kèm lý do; người lập sửa và gửi lại cùng mã, đi lại tuyến từ đầu, bản trước lưu lại. Kế toán chi nhiều lần, tổng không vượt số duyệt, mỗi lần một UNC và một bút toán; bảng nợ phải trả và dòng tiền chỉ tính phần còn phải chi. **Kèm phần D — chống ghi chi phí hai lần (đội xe):** khoản gốc chọn từ sổ của xe (dòng chi phí chuyến / phiếu bảo dưỡng), một khoản gốc một đề nghị chi, cảnh báo trùng số chứng từ, dòng chi phí chuyến hiện mã DC đã gắn. | backend/alembic/versions/tb6d1e3a9c5f2b84_tra_bo_sung_chi_mot_phan.py, backend/app/models/ops.py, backend/app/services/debts.py, backend/app/services/dong_tien.py, backend/app/services/finance.py, backend/app/services/nghia_vu.py, backend/app/api/v1/fleet.py, backend/tests/test_tb6_tra_bo_sung_chi_mot_phan.py, web/app/expenses/page.tsx, web/components/doixe/DeXuatChiTaiCho.tsx, backend/app/services/chu_ky.py, backend/app/services/quyet_toan_chuyen.py, backend/tests/test_cg1_chong_ghi_hai_lan.py, web/components/doixe/BonBuocDeXuatChi.tsx, web/components/QuyetToanChuyen.tsx, docs/dang-lam/phan-quyen/TT-TBS.md | 10-11-2026 02:30 | xong |

`backend/app/services/ops.py` và `backend/app/api/v1/ops.py` khai ở sổ làn TC-KT ([../tc-kt/TT-TBS.md](../tc-kt/TT-TBS.md)) — Chủ tịch cho phép 10/11/2026.
