# Sổ giữ chỗ — làn Phân quyền · Đợt KS-20e

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-20e — EMAIL + PDF SAU THANH TOÁN ĐẶT PHÒNG VTD (THEO MẪU AGODA)** (Chủ tịch duyệt bản xem thử 07/11/2026: email xác nhận, phiếu xác nhận, hóa đơn đặt phòng; song ngữ Việt – Anh; tên «Hóa đơn đặt phòng khách sạn»; hai PDF tự gửi kèm email và tải trong «Đơn của tôi»; logo bộ v2). Email song ngữ đính kèm Phieu-xac-nhan-<mã>.pdf và Hoa-don-<mã>.pdf khi đơn được xác nhận; cổng khách tải lại qua /cong/ks-vtd/don/<mã>/pdf/{phieu,hoa_don}. Không in chữ ký giả (ô «Xác nhận điện tử»); hóa đơn ghi rõ thu hộ, không thay hóa đơn GTGT. Pháp nhân thêm địa chỉ + hotline (màn «Pháp nhân» sửa được); bản nâng cấp ghi giá trị Chủ tịch nhắn cho mã VTD khi ô còn trống. Thêm fpdf2 + fonts-dejavu-core. | backend/app/services/phieu_ks_vtd.py, backend/app/services/don_ks_vtd.py, backend/app/api/v1/don_ks_vtd.py, backend/app/api/v1/companies.py, backend/app/models/core.py, backend/alembic/versions/ks20e1a3c5e7b9d135_dia_chi_hotline_phap_nhan.py, backend/app/static/logo/khoachu-holdings-ngang.svg, backend/requirements.txt, backend/Dockerfile, web/app/companies/page.tsx, web/components/cong/KhachSanVtd.tsx, backend/tests/test_ks20e_phieu_hoa_don.py, backend/tests/test_ks20c_thanh_toan_xac_nhan.py, docs/dang-lam/phan-quyen/KS-20e.md | 07-11-2026 00:30 | xong |
