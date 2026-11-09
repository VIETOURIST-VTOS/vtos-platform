# Sổ giữ chỗ — làn Phân quyền · Đợt XE-V33B

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **XE-V33B — ĐỘI XE HOÀN THIỆN (Chủ tịch duyệt bản xem trước 10/11/2026)**. (1) Tuyến duyệt mới: Giám đốc đội xe gửi → **Chủ tịch duyệt** → Kế toán kiểm chứng từ và chi, áp cho cả đề xuất chi đội xe (`chi_doi_xe`, mọi số tiền) và tờ báo cáo xe (chuyến vào lợi nhuận khi Chủ tịch duyệt; báo cáo nhập qua cửa bốn bước chưa vào lợi nhuận). (2) Màn gọn từng trang con của /xe thay khung nhúng nguyên màn; «Mở…» mới mở màn chi tiết tại chỗ. | backend/app/api/v1/fleet.py, backend/app/models/fleet.py, backend/app/services/quyet_toan_chuyen.py, backend/tests/test_dx5_de_nghi_chi_doi_xe.py, backend/tests/test_qt1_quyet_toan_chuyen.py, backend/tests/test_xg1_man_gon_doi_xe.py, web/app/doi-xe/page.tsx, web/app/xe/page.tsx, web/components/QuyetToanChuyen.tsx, web/components/doixe/BonBuocBaoCaoXe.tsx, web/components/doixe/BonBuocDeXuatChi.tsx, web/components/doixe/DeXuatChiTaiCho.tsx, web/components/doixe/TrangGon.tsx, docs/dang-lam/phan-quyen/XE-V33B.md | 10-11-2026 02:00 | đang làm |

`backend/app/services/ops.py` khai ở sổ làn TC-KT ([../tc-kt/XE-V33B.md](../tc-kt/XE-V33B.md)) — Chủ tịch cho phép 10/11/2026.
