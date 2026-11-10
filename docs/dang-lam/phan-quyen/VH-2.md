# Sổ giữ chỗ — làn Phân quyền · Đợt VH-2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **VH-2 — SỬA SAU KHI BẤM THỬ GIAO DIỆN TRỌN LUỒNG** (Chủ tịch giao 10/11/2026). Bấm bằng trình duyệt đúng từng vai (Điều hành → GĐ đội xe → tài xế trên điện thoại → GĐ báo cáo xe → Chủ tịch → Kế toán) trên bản chạy tại máy. Ba chỗ sửa: (1) cửa bốn bước gửi `lit: null` làm cầu đường / công tác phí / gửi xe bị 422, không vào sổ; (2) Chủ tịch và Kế toán không có đường mở thẳng tờ báo cáo xe đang chờ ký — thêm `/doi-xe?tab=chuyen&chuyen=…` và nút «Mở» ở màn gọn; (3) lệnh trên màn tài xế là bảng bảy cột phải kéo ngang trên điện thoại, nhãn «Đang chờ trả lời» là nhãn của HDV — đổi thành thẻ dọc. | backend/app/api/v1/fleet.py, backend/tests/test_vh1_tron_luong_mot_chuyen.py, web/app/doi-xe/page.tsx, web/app/xe-hdv/page.tsx, web/components/doixe/BonBuocBaoCaoXe.tsx, web/components/doixe/TrangGon.tsx, docs/dang-lam/phan-quyen/VH-1.md, docs/dang-lam/phan-quyen/VH-2.md | 10-11-2026 09:30 | đang làm |
