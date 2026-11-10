# Sổ giữ chỗ — làn Phân quyền · Đợt VH-9

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
| Phân quyền | **VH-9 — LỊCH XE 90 NGÀY TỚI** (Chủ tịch duyệt bản xem trước 11/11/2026). Trang con «Lịch xe 90 ngày» trong /xe › Điều xe: bốn thẻ công suất, lưới xe × ngày (lệnh / hỏng / trống / cuối tuần, đề nghị chờ theo ngày), khoảng trống từ 2 ngày liền để bán (nút «Giữ xe cho tour» mở đề nghị xe sẵn ngày), công suất theo tuần (dưới 40% tô vàng). Xe đang hỏng «phải dừng» không tính trống. Tin sáng thứ Hai (robot `/fleet/robot/lich-xe-gui-tuan`, mỗi tuần một tin) gửi Chủ tịch, TGĐ, TP Điều hành, GĐ KD, TP KD, P.TGĐ MKT, P.TGĐ Đoàn. Cửa `/lich-xe-tuong-lai/khoang-trong` cho Kinh doanh — mở vai KD cần access.py (làn R2), đợt sau. | backend/app/services/lich_xe_tuong_lai.py, backend/app/api/v1/fleet.py, backend/app/services/canh_bao_trinh_bay.py, web/app/xe/page.tsx, web/components/doixe/LichXe90.tsx, backend/tests/test_vh9_lich_xe_90_ngay.py, docs/dang-lam/phan-quyen/TT-TBS.md, docs/dang-lam/phan-quyen/VH-8.md, docs/dang-lam/phan-quyen/VH-9.md | 11-11-2026 02:00 | đang làm |
