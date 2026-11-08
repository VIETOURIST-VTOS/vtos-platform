# Sổ giữ chỗ — làn Phân quyền · Đợt KS-AN

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-AN — BÀN LÀM VIỆC KHÔNG BÀY KHỐI VAI TRÒ KHÔNG ĐƯỢC XEM** (Chủ tịch 08/11/2026 chọn «Kiểm các bàn làm việc khác», duyệt «Ẩn hẳn khối» theo bản xem thử khung 4). Rà 13 chức danh: trên bàn PTGĐ, TP Điều hành, GĐ KD, HCNS, CNTT, nhân viên Điều hành / Kinh doanh, khối «Doanh thu và lợi nhuận» hiện «Chưa kết nối» kèm đường dẫn /api/… (máy chủ trả 403); khối «Báo cáo ngày» báo «máy chủ chưa trả tỉ lệ» với mọi vai trừ Chủ tịch, TGĐ, HCNS (máy chủ không gửi trường). Sửa: 403 → không bày khối; vắng trường `bao_cao_ngay` → không bày khối; lỗi thật vẫn báo «Chưa kết nối». Không đổi quyền, không đổi số. | web/components/KhoiKetQuaKinhDoanh.tsx, web/app/page.tsx, backend/tests/test_ks_an_khoi_khong_quyen.py, docs/dang-lam/phan-quyen/KS-AN.md | 08-11-2026 04:45 | xong |
