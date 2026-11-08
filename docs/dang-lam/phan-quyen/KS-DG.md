# Sổ giữ chỗ — làn Phân quyền · Đợt KS-DG

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-DG — THẺ «ĐÁNH GIÁ & SỰ VỤ» TẢI ĐƯỢC BẢNG ĐÁNH GIÁ** (Chủ tịch 08/11/2026 hỏi «các phân hệ Marketing, Điều hành, Kinh doanh, HCNS đã xong hết chưa», chọn «Sửa rồi kiểm lại trên crm thật»). Rà 75 màn hình của bốn phân hệ: chỉ một lỗi — `DanhGiaNhanSu.tsx` gọi `api("/api/v1/danh-gia-ns…")`, `api()` tự ghép `/api/v1` nên thành `/api/v1/api/v1/…` → 404. Sửa một dòng; phép thử quét cả giao diện chặn kiểu lỗi này. | web/components/DanhGiaNhanSu.tsx, backend/tests/test_ks_dg_api_khong_lap_tien_to.py, docs/dang-lam/phan-quyen/KS-DG.md | 08-11-2026 10:45 | xong |
