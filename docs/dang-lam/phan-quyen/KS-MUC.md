# Sổ giữ chỗ — làn Phân quyền · Đợt KS-MUC

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-MUC — BA MỨC ĐỘ BA MÀU TRÊN CRM** (Chủ tịch 07/11/2026: «phần cảnh báo màu hồng, vàng, xanh theo từng mức độ đã bị thay thành một màu xanh navy là sai»; duyệt «Trả lại hồng + sửa vàng»). KS-NAVY (#704) đổi `--vtos-danger` sang xanh — nền tối trùng đúng `--vtos-info` — nên mọi chỗ nghiêm trọng / quá hạn / từ chối / lỗ / số âm / báo lỗi (khoảng 75 chỗ trong 18 tệp, cộng các trang dùng bí danh `--red`) thành xanh. Sửa: trả `--vtos-danger` và nền của nó về giá trị cũ (tối #FF6B90 / #3B1B27, sáng #A8145C / #FBE9F0); khối Vận hành: thanh và nhãn mức «Cảnh báo» lấy `--vtos-warning` (lỗi cũ từ TQ-1 lấy nhầm `--vtos-info`), «Theo dõi» xanh, «Chưa phân loại» xám. Navy giữ cho thương hiệu và nút; cổng kh/dt/ir không đổi. | web/app/tokens.css, web/components/KhoiVanHanh.css, web/components/KhoiVanHanh.tsx, backend/tests/test_bo_nhan_dien.py, backend/tests/test_tc64_toc_do_va_chu_sang.py, backend/tests/test_ks_muc_ba_mau_muc_do.py, docs/dang-lam/phan-quyen/KS-MUC.md | 07-11-2026 23:55 | đang làm |
