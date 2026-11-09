# Sổ giữ chỗ — làn Phân quyền · Đợt VH-1

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **VH-1 — ĐỘI XE VÀO VẬN HÀNH** (Chủ tịch duyệt bản xem trước 10/11/2026). (1) Chạy thử trọn luồng một chuyến bằng đúng vai qua cửa HTTP thật; lập lệnh trả mã lệnh. (2) Báo cáo xe bước 1 chọn lệnh điều xe → gắn tour, tài xế, ngày; một lệnh một phiếu; mở đúng phiếu tài xế đã gửi. (3) Bảng sẵn sàng vận hành đầu /xe (xe · người · tham số · chi phí kỳ · việc treo). (4) Tài xế ghi chuyến trên điện thoại ở «Xe & lệnh của tôi» (km, dầu, cầu đường, gửi xe, ảnh hoá đơn, gửi GĐ); gỡ phần HDV khỏi màn này theo lệnh Chủ tịch. | backend/app/api/v1/hr.py, backend/app/api/v1/fleet.py, backend/app/services/tai_xe_ghi_chuyen.py, backend/app/services/san_sang_doi_xe.py, backend/tests/test_vh1_tron_luong_mot_chuyen.py, web/app/xe-hdv/page.tsx, web/app/xe/page.tsx, web/components/doixe/BonBuocBaoCaoXe.tsx, web/components/doixe/TaiXeGhiChuyen.tsx, web/components/doixe/SanSangVanHanh.tsx, docs/dang-lam/phan-quyen/VH-1.md | 10-11-2026 03:45 | đang làm |

Mục menu của vai HDV vẫn trỏ /xe-hdv vì bảng quyền + menu (access.py, Shell.tsx) do làn R2 giữ — màn này nay chỉ hiện một dòng chuyển HDV sang màn phòng Hướng dẫn. Cửa máy chủ `/api/v1/xe-hdv/...` của HDV giữ nguyên.
