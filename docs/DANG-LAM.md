# ĐANG LÀM — bảng giữ chỗ của các làn

Bảng này tồn tại vì **ngày 11/9/2026 có hai lần đụng độ trong một buổi chiều**: VPM-11 và Robot A
cùng viết sổ nghĩa vụ thanh toán; làn Phân quyền và Robot A cùng viết DT-1/DT-3. Không làn nào chép
của làn nào — cả hai lần đều là bốn làn cùng đọc một tài liệu rồi viết ra hai bản gần trùng khít.

Mỗi làn ghi **một dòng vào bảng dưới TRƯỚC KHI viết dòng mã đầu tiên**. Làn sau đọc bảng trước khi
viết. Rẻ hơn gỡ một lần đụng độ, và rẻ hơn rất nhiều so với một mạch nâng cấp hai đầu phát hiện sau
khi đã đẩy lên.

## Cách ghi

| Cột | Ghi gì |
|---|---|
| **Làn** | tên làn: `Robot A`, `Phân quyền`, `Vòng`, `VPM`, `Kiểm soát`, `Quyết toán` |
| **Mã việc** | mã trong lệnh giao việc: `DT-2`, `PQ-10`, `TC-4`, `VPM-17`… |
| **Tệp sẽ đụng** | đường dẫn từ gốc kho, phân cách bằng dấu phẩy. Kể cả tệp SẼ TẠO MỚI. |
| **Bắt đầu** | `DD-MM-YYYY HH:MM` |
| **Trạng thái** | `đang làm` · `xong` · `bỏ` |

Chỉ dòng **`đang làm`** mới giữ chỗ. Xong việc thì đổi sang `xong` — **đừng xoá dòng**, vì dòng cũ
là chỗ tra "ai đã đụng tệp này lần trước".

## Phép thử canh bảng này

`backend/tests/test_giu_cho_lan.py` đọc chính tệp này và **ĐỎ** khi hai dòng `đang làm` cùng khai
một đường dẫn. Không có phép thử canh thì một bảng khai đúng ba ngày là không ai điền nữa.

### 23/9/2026 — thêm ba luật, vì hàng rào cũ chưa nổ được lần nào

Đo lại ngày 23/9: trong 40 dòng của bảng dưới, **không có dòng nào ở trạng thái `đang làm`**. Mọi
làn ghi thẳng `xong` ngay lúc đẩy. Luật cũ chỉ so các dòng `đang làm` với nhau — nên một bảng toàn
`xong` là một bảng không giữ chỗ cho ai, và phép thử soi nó thì **luôn xanh**.

Hôm ấy hỏng hai lần trong một ngày: 14:51 làn Vòng đè lên ba tệp của làn Phân quyền; 16:10 làn
TC-77 đè tiếp lên ba tệp nữa, xoá sạch bốn cửa báo động vừa viết xong. **Cả hai lần CI đều xanh** —
xoá phần của làn khác không làm phép thử nào đỏ.

`backend/tests/test_giu_cho_nhanh.py` thêm ba luật, chạy trên **pull request**:

1. Danh sách tệp nhánh đổi phải đọc được (ci.yml tính sẵn) — không đọc được là đỏ.
2. Nhánh đụng **tệp mã** thì chính tệp `docs/DANG-LAM.md` phải nằm trong danh sách ấy: **mỗi vòng
   đẩy lên phải tự ghi một dòng**, không đi nhờ dòng của làn khác.
3. Mọi tệp mã nhánh đụng phải được một dòng **`đang làm`** gọi tên. `xong` không giữ chỗ.

Khép lại với luật cũ: làn A mở dòng `đang làm` cho `marketing.py` → làn B muốn đụng cùng tệp buộc
phải khai → hai dòng `đang làm` trùng tệp → **đỏ trên PR của B**, trước khi gộp, trước khi ai mất
gì.

Đường dẫn khai nhận ba kiểu: đúng tên tệp, thư mục kết bằng `/`, và mẫu sao (`backend/tests/*.py`).

`docs/` ngoài chính quyển sổ này **không** bị canh: hai làn đè một tệp tài liệu thì gỡ bằng mắt
trong một phút, đè một tệp mã thì mất nửa ngày. Hàng rào đặt ở chỗ đắt.

Phép thử **cố ý KHÔNG** đỏ theo thời gian — không có luật "quá N ngày thì đỏ". Một phép thử tự đỏ
mà không ai sửa mã là thứ làm người ta thôi nhìn CI, và chính lệnh giao việc đã cảnh báo điều đó.

Bảng này KHÔNG thay cho việc đọc kho mã trước khi viết. Nó chỉ bắt được chuyện hai làn khai cùng một
tệp; hai làn viết cùng một KHÁI NIỆM vào hai tệp khác tên thì bảng không thấy — đó vẫn là việc phải
đọc lệnh giao việc của làn khác.

---

## Bảng

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Robot A | GD-1 khối Dòng tiền DT-1…DT-4 | backend/app/models/dong_tien.py, backend/app/services/dong_tien.py, backend/app/api/v1/dong_tien.py, web/app/dong-tien/page.tsx | 11-09-2026 13:40 | xong |
| VPM | VPM-11 sổ nghĩa vụ thanh toán | backend/app/models/nghia_vu.py, backend/app/services/nghia_vu.py | 11-09-2026 14:30 | xong |
| VPM | VPM-17 cửa nhập ngày đến hạn | backend/app/api/v1/ops.py, backend/app/api/v1/suppliers.py, backend/app/services/ops.py, backend/app/services/suppliers.py | 11-09-2026 16:00 | xong |
| Phân quyền | PQ-10 · SEC-02 · CF-07 · DT-1 · DT-3 · GD-1 | backend/app/services/pham_vi_dang_xem.py, backend/app/services/lam_tron_tien.py, backend/app/services/dong_tien_ky.py, backend/app/services/dong_tien_pham_vi.py, backend/app/services/canh_bao_trinh_bay.py | 11-09-2026 15:30 | xong |
| Vòng | TC-2 · TC-1 · TC-1b · TC-4 | web/components/Shell.tsx, web/components/ChonDonVi.tsx, web/components/dienthoai.tsx, web/lib/phamvi.ts, web/app/globals.css | 11-09-2026 15:00 | xong |
| Kiểm soát | hàng rào phạm vi · visa sales | backend/app/services/access.py | 11-09-2026 09:00 | xong |
| Robot A | Ba cửa kho quyết toán cũ T1–T6/2026 | backend/app/services/intake_kho_cu.py, backend/app/services/intake.py, backend/tests/test_kho_cu_ba_cua.py | 12-09-2026 01:30 | xong |
| Robot A | Đ-2 thuế GTGT ở mức chuyến | backend/app/services/thue_gtgt_chuyen.py, backend/app/services/lai_lo_tour.py, backend/tests/test_thue_gtgt_chuyen.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-3 ba phép kiểm hai tổng phải bằng nhau | backend/app/services/soat_can_doi_quyet_toan.py, backend/tests/test_soat_can_doi_quyet_toan.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-6 tiền tip hai chiều + tham số tỷ lệ chia | backend/app/services/tip_tour.py, backend/app/models/lop3_tour.py, backend/app/services/rules.py, backend/tests/test_tip_tour.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-1 mở cửa quyết toán lớp 3 | web/app/tours/[id]/page.tsx, backend/tests/test_cua_quyet_toan_lop3.py | 12-09-2026 21:00 | xong |
| Robot A | Đ-2b thuế tour nước ngoài hai dòng hoá đơn | backend/app/services/thue_gtgt_chuyen.py, backend/app/services/lai_lo_tour.py, backend/app/services/rules.py | 12-09-2026 22:30 | xong |
| Robot A | Đ-6b ô % chia tip cho Điều hành nhập | backend/app/services/tip_tour.py, backend/app/api/v1/quyet_toan_lop3.py, web/components/QuyetToanForm.tsx | 12-09-2026 22:30 | xong |
| Robot A | Đ-10 dự chi ↔ thực chi sang lớp 3, thêm chiều ngược | backend/app/services/soat_du_chi.py, backend/app/api/v1/quyet_toan_lop3.py, backend/tests/test_dot1_quyet_toan.py | 13-09-2026 06:00 | xong |
| Robot A | Đ-11 chứng từ gắn vào từng dòng chi | backend/app/models/attachments.py, backend/app/api/v1/quyet_toan_lop3.py, backend/tests/test_dot1_quyet_toan.py | 13-09-2026 06:00 | xong |
| Robot A | Đ-7 thu hộ – chi hộ, số dư có chủ và có hạn | backend/app/services/thu_ho_chi_ho.py, backend/app/models/lop3_tour.py, backend/app/api/v1/quyet_toan_lop3.py, backend/alembic/versions/c1f5a8d3e7b62_d7_thu_ho_chu_tien_va_han_xu_ly.py, backend/tests/test_dot1_quyet_toan.py | 13-09-2026 06:00 | xong |
| Robot A | Đ-8 vé máy bay theo mã đặt chỗ, dòng khách là số chốt | backend/app/services/ve_may_bay.py, backend/app/models/lop3_tour.py, backend/app/api/v1/quyet_toan_lop3.py, backend/alembic/versions/d4a9c72e1b085_d8_d9_ve_may_bay_va_cong_no_truong_doan.py, web/components/QuyetToanForm.tsx, backend/tests/test_dot2_quyet_toan.py | 13-09-2026 09:00 | xong |
| Robot A | Đ-9 công nợ trưởng đoàn, nhiều đồng tiền song song, quy ước dấu | backend/app/services/cong_no_truong_doan.py, backend/app/models/lop3_tour.py, backend/app/api/v1/quyet_toan_lop3.py, web/components/QuyetToanForm.tsx, backend/tests/test_dot2_quyet_toan.py | 13-09-2026 09:00 | xong |
| Robot A | Đ-4 nhiều bên bán ghép land + Đ-6b hoàn tip cho bên bán | backend/app/services/ben_ban_tour.py, backend/app/models/lop3_tour.py, backend/app/api/v1/quyet_toan_lop3.py, backend/alembic/versions/e7b3f19a4c260_d4_d5_d12_ben_ban_lanh_su_dich_vu_le.py, web/components/QuyetToanForm.tsx, backend/tests/test_dot3_quyet_toan.py | 13-09-2026 14:00 | xong |
| Robot A | Đ-12 đề nghị chi phí lãnh sự theo từng khách | backend/app/services/de_nghi_lanh_su.py, backend/app/models/lop3_tour.py, backend/app/api/v1/quyet_toan_lop3.py, web/components/QuyetToanForm.tsx, backend/tests/test_dot3_quyet_toan.py | 13-09-2026 14:00 | xong |
| Robot A | Đ-5 dịch vụ lẻ theo tháng — KHÔNG bảng mới, đọc từ /non-package | backend/app/services/dich_vu_le_thang.py, backend/app/services/access.py, backend/app/api/v1/quyet_toan_lop3.py, web/app/non-package/page.tsx, web/app/tours/[id]/page.tsx, backend/tests/test_dot3_quyet_toan.py | 13-09-2026 14:00 | xong |
| Robot A | Chủ tịch toàn quyền — một luật, 25 chỗ tự kiểm bằng tay | backend/app/api/deps.py, backend/app/services/ks_toan_quyen.py, backend/tests/test_ks_toan_quyen.py, backend/app/api/v1/quyet_toan_lop3.py, backend/app/api/v1/settlement.py, backend/app/api/v1/routes.py, backend/app/services/access.py, backend/app/services/bookings.py, backend/app/services/giu_cho.py, backend/app/services/nonpackage.py, backend/app/services/ops.py, backend/app/services/products.py, backend/app/services/settlement.py, backend/app/services/tours.py, backend/app/services/rules.py | 13-09-2026 17:30 | xong |
| Robot A | Mở cửa tách bạch trách nhiệm cho Chủ tịch theo công tắc (chạy thử) | backend/app/api/deps.py, backend/app/services/rules.py, backend/app/services/ks_toan_quyen.py, backend/app/services/ks_robot.py, backend/app/models/kiem_soat.py, backend/app/services/ops.py, backend/app/services/tours.py, backend/app/services/settlement.py, backend/app/services/marketing.py, backend/app/api/v1/access.py, backend/app/api/v1/hr.py, backend/tests/test_ks_toan_quyen.py | 13-09-2026 19:00 | xong |
| Robot A | Nạp kho quyết toán cũ T1–T6/2026 — sửa bộ đọc + cửa tạo chuyến | backend/app/services/nap_kho_cu.py, backend/app/services/tao_chuyen_kho_cu.py, backend/app/services/intake_tao_chuyen.py, backend/app/services/intake.py, backend/tests/test_tao_chuyen_kho_cu.py, backend/tests/test_intake_tao_chuyen.py, backend/tests/test_kho_cu_bang_khach_khong_phai_bang_chi.py | 13-09-2026 21:00 | xong |
| Robot A | Nút GỠ CẢ LÔ kho quyết toán cũ — đường đi ngược của hai cửa nạp | backend/app/services/go_lo_kho_cu.py, backend/app/api/v1/quyet_toan_lop3.py, backend/tests/test_go_lo_kho_cu.py, web/components/KhoCuLo.tsx, web/app/tours/page.tsx | 13-09-2026 23:00 | xong |
| Robot A | Kho cũ CHẠY VỀ BÁO CÁO — khớp người bán, phiếu đặt theo sale, bản đối chiếu H1 | backend/app/models/kho_cu.py, backend/app/services/khop_nguoi_ban.py, backend/app/services/phieu_dat_kho_cu.py, backend/app/services/intake_doi_chieu_h1.py, backend/app/services/intake_kho_cu.py, backend/app/services/intake_tao_chuyen.py, backend/app/services/tao_chuyen_kho_cu.py, backend/app/services/go_lo_kho_cu.py, backend/app/services/thue_gtgt_chuyen.py, backend/app/services/intake.py, backend/app/api/v1/quyet_toan_lop3.py, backend/alembic/versions/f2a6c81b93d47_kho_cu_gan_nguoi_ban.py, web/components/KhoCuNguoiBan.tsx, web/app/tours/page.tsx | 14-09-2026 01:00 | xong |
| Robot A | Đ-2c thuế suất GTGT là Ô TRÊN CHUYẾN cho Điều hành nhập, không viết cứng | backend/app/models/core.py, backend/app/services/thue_gtgt_chuyen.py, backend/app/services/rules.py, backend/app/services/lai_lo_tour.py, backend/app/api/v1/quyet_toan_lop3.py, backend/alembic/versions/a3d71e9c54b28_thue_suat_tren_chuyen.py, backend/tests/test_thue_gtgt_chuyen.py, web/components/ThueSuatChuyen.tsx, web/components/QuyetToanForm.tsx | 14-09-2026 02:00 | xong |
| Robot A | Mật khẩu đã công khai — soát, buộc đổi, siết luật đặt; bỏ mật khẩu khỏi trang đăng nhập | backend/app/services/mat_khau_yeu.py, backend/app/api/v1/routes.py, backend/app/api/v1/access.py, backend/tests/test_mat_khau_cong_khai.py, web/app/login/page.tsx, web/app/access/page.tsx, web/components/MatKhauCongKhai.tsx | 14-09-2026 21:30 | xong |
| Robot A | Mật khẩu đã công khai (vá lần 2) — bỏ phép quét bcrypt làm treo màn hình Tài khoản, bắt ngay ở cửa đăng nhập; gỡ "123456" khỏi seed và 95 tệp phép thử | backend/app/services/mat_khau_yeu.py, backend/app/services/seed.py, backend/app/api/v1/routes.py, backend/app/api/v1/access.py, backend/tests/*.py (đổi mật khẩu mẫu), web/components/MatKhauCongKhai.tsx | 14-09-2026 23:10 | xong |
| Robot A | Cửa NẠP CẢ LÔ nhiều tệp ở màn hình Nạp dữ liệu — mỗi tệp một lần nạp, giữ riêng tên tệp cho nhật ký | web/app/nap-du-lieu/page.tsx, backend/tests/test_cua_nap_ca_lo.py | 15-09-2026 01:30 | xong |
| Robot A | Chiết tính: dòng CỘNG bị đếm thành dòng CHI nên giá vốn vào hệ thống gấp đôi — sửa bộ đọc, tách nhóm viết liền, để số lượng 0 yên | backend/app/services/quyet_toan_chi_tiet.py, backend/tests/test_ctt_dong_cong.py | 15-09-2026 02:40 | xong |
| Phân quyền | Gói R3 Marketing — cửa nhập khách tiềm năng, mã lead, lịch sử giao–nhận Sales; và hai kiểu ô mới cho khuôn ba cửa | backend/alembic/versions/mkt1a9c4e7b2d63_marketing_ma_lead_va_ban_giao.py, backend/app/models/crm.py, backend/app/services/intake.py, backend/app/services/intake_marketing.py, backend/app/services/leads.py, backend/app/services/nhap_lieu.py, backend/tests/test_mkt2_cua_nhap.py, backend/tests/test_mkt5_ty_le_chot_leads.py, backend/tests/test_mkt7_han_xu_ly_lead.py, web/app/nap-du-lieu/page.tsx | 18-09-2026 13:30 | xong |
| Phân quyền | Sổ tài sản thương hiệu — dùng chung bảng TSCĐ, hai chữ ký cho một bộ nhận diện mới | backend/alembic/versions/th5b8e2c7a1d94_so_tai_san_thuong_hieu.py, backend/app/models/assets.py, backend/app/services/tai_san_thuong_hieu.py, backend/app/services/intake_thuong_hieu.py, backend/app/services/intake.py, backend/app/services/assets.py, backend/app/services/rules.py, backend/app/api/v1/assets.py, backend/app/api/v1/marketing.py, backend/tests/test_th1_tai_san_thuong_hieu.py, backend/tests/test_mkt6_man_hinh_marketing.py, web/app/marketing/page.tsx | 18-09-2026 19:00 | xong |
| Phân quyền | Sổ hoạt động PR — người phát ngôn P.TGĐ Marketing, và đồng hồ 2 giờ của khủng hoảng truyền thông | backend/alembic/versions/pr4c9a1e7b2d58_so_hoat_dong_pr.py, backend/app/models/marketing.py, backend/app/services/pr_hoat_dong.py, backend/app/services/intake_pr.py, backend/app/services/intake.py, backend/app/services/rules.py, backend/app/services/pham_vi_phap_nhan.py, backend/app/api/v1/marketing.py, backend/tests/test_pr1_hoat_dong_pr.py, backend/tests/test_mkt6_man_hinh_marketing.py, web/app/marketing/page.tsx | 18-09-2026 21:00 | xong |
| Phân quyền | Cửa lọc tin khủng hoảng — xếp hàng tin đáng đọc trước cho Marketing; bộ lọc KHÔNG tự đánh dấu khủng hoảng, và có phép đo chính nó (bắt đúng / báo nhầm / bỏ sót) | backend/alembic/versions/lk9e3b1d7c2a46_cua_loc_tin_khung_hoang.py, backend/app/models/marketing.py, backend/app/services/loc_khung_hoang.py, backend/app/services/rules.py, backend/app/services/ks_cua_nhap.py, backend/app/api/v1/marketing.py, backend/tests/test_lk1_loc_khung_hoang.py, backend/tests/test_mkt6_man_hinh_marketing.py, web/app/marketing/page.tsx | 19-09-2026 02:00 | xong |
| Phân quyền | Bình luận công khai Fanpage — đăng ký trường webhook `feed`, bảng riêng (không đổ vào hộp thư vì sẽ sinh lead giả), và điểm CÔNG KHAI +1 trong hàng đợi cảnh báo | backend/alembic/versions/bl7f4a2c9e1d83_binh_luan_cong_khai_fanpage.py, backend/app/models/marketing.py, backend/app/services/fb_binh_luan.py, backend/app/services/loc_khung_hoang.py, backend/app/services/inbox.py, backend/app/services/ks_cua_nhap.py, backend/app/api/v1/marketing.py, backend/tests/test_bl1_binh_luan_cong_khai.py, web/app/marketing/page.tsx | 19-09-2026 04:00 | xong |
| Phân quyền | Nối tài khoản VTOS với Zalo bằng mã dùng một lần — để cảnh báo tới được NGƯỜI; và chốt chặn người của công ty biến thành lead giả trong sổ khách hàng | backend/alembic/versions/zn8c3e1f7a4d26_noi_tai_khoan_zalo.py, backend/app/models/zalo_noi.py, backend/app/models/__init__.py, backend/app/services/zalo_nguoi_dung.py, backend/app/services/zalo.py, backend/app/services/ks_cua_nhap.py, backend/app/api/v1/crm.py, backend/tools/ks2_khai_quyen.py, backend/app/services/access.py, backend/tests/test_zn1_noi_tai_khoan_zalo.py, backend/tests/test_p2_pham_vi_vai_tro.py, web/app/doi-mat-khau/page.tsx | 19-09-2026 15:00 | xong |
| Phân quyền | CI chạy hai hình — bộ đủ 24 phút chỉ trên PR (cửa chặn), main còn cửa hẹp 12 giây soi đúng chuyện hai làn đụng nhau (cửa báo). Trần chi tiêu Actions chạm đáy 19/9 làm bốn làn cùng đứng | .github/workflows/ci.yml, backend/tests/test_ci_hang_rao_main.py | 19-09-2026 17:30 | xong |
| Phân quyền | Báo động khủng hoảng — ngưỡng ĐỎ tự reo chuông phút 0 cho Chủ tịch, phút 15 chưa ai bấm nhận thì đánh thức TGĐ và P.TGĐ Marketing; sổ gửi ghi CẢ lần không gửi được kèm lý do | backend/alembic/versions/bd5a2f8c1e94_bao_dong_khung_hoang.py, backend/app/models/bao_dong.py, backend/app/models/__init__.py, backend/app/services/bao_dong_khung_hoang.py, backend/app/services/rules.py, backend/app/services/ks_cua_nhap.py, backend/app/api/v1/marketing.py, backend/tools/ks2_khai_quyen.py, backend/tests/test_bd1_bao_dong_khung_hoang.py, web/components/Shell.tsx, web/app/marketing/page.tsx | 19-09-2026 22:30 | xong |
| Phân quyền | Hàng rào giữ chỗ làn — đẩy mã lên mà không có dòng `đang làm` thì ĐỎ | .github/workflows/ci.yml, backend/tests/test_giu_cho_nhanh.py, backend/tests/test_ci_hang_rao_main.py | 23-09-2026 17:00 | đang làm |
