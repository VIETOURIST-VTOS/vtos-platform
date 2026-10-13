from app.models.core import *  # noqa
from app.models.de_nghi_xe import *  # noqa
from app.models.chuong_trinh import *  # noqa
from app.models.payments import *  # noqa
from app.models.accounting import *  # noqa
from app.models.assets import *  # noqa
from app.models.banks import *  # noqa
# Phòng HDV Đợt 1 · 06/10/2026. Đặt TRƯỚC hr vì `guide_assignments` mang khoá ngoài sang
# `yeu_cau_hdv`, và sau core vì bảng này mang khoá ngoài sang `tours` và `companies`. Lần thứ MƯỜI BA
# nhắc cùng một điều ở tệp này: bảng khai dưới app/models mà thiếu dòng nhập ở đây thì
# `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate đòi XOÁ bảng.
from app.models.hdv import *  # noqa
from app.models.luong_khoa import *  # noqa
from app.models.chi_luong import *  # noqa
from app.models.su_kien_thu_nhap import *  # noqa
from app.models.lich_su_to_chuc import *  # noqa
from app.models.phap_che import *  # noqa
from app.models.phap_che_viec import *  # noqa
from app.models.nha_dau_tu import *  # noqa
from app.models.hr import *  # noqa
from app.models.hrm import *  # noqa
# Ba bang HCNS mo cung MOT migration 09/10/2026: 5.6 danh gia nhan su, 5.9.2 de nghi mua,
# 5.9.3 cap phat tai san. Dat SAU `assets` va SAU `hr` co ly do: `cap_phat_tai_san` mang khoa
# ngoai sang CA `fixed_assets` (assets) LAN `employees` (hr), nen hai bang ay phai co mat trong
# metadata truoc. Thieu dong nhap nay thi ba bang khong vao Base.metadata: create_all khong tao,
# moi phep thu soi metadata mu dung phan nay ma van bao xanh, va alembic autogenerate doi XOA chung.
from app.models.nhan_su_danh_gia import *  # noqa
from app.models.ops import *  # noqa
from app.models.finance import *  # noqa
from app.models.reports_auto import *  # noqa
from app.models.bao_cao_luu import *  # noqa
# VPM-5. Dòng này đã có từ commit VPM-5 rồi BIẾN MẤT trong cây làm việc ngày 11/9/2026 – một phiên
# khác lưu đè bằng bản mở từ trước khi VPM-5 gộp. Thiếu nó thì `phan_bo_tien` không nằm trong
# Base.metadata: phép thử soi mô hình mù đúng bảng ấy, và alembic autogenerate sẽ đòi XOÁ bảng.
from app.models.phan_bo_tien import *  # noqa
from app.models.giu_cho import *  # noqa
# VPM-11 – sổ nghĩa vụ thanh toán. Thiếu dòng này thì bảng không nằm trong Base.metadata:
# create_all không tạo, phép thử soi mô hình mù đúng bảng ấy, và alembic autogenerate đòi XOÁ nó.
from app.models.nghia_vu import *  # noqa
from app.models.vietrip import *  # noqa
from app.models.crm import *  # noqa
from app.models.visa import *  # noqa
from app.models.suppliers import *  # noqa
from app.models.intake import *  # noqa
from app.models.ghi_mot_lan import *  # noqa
from app.models.ban_hang import *  # noqa
from app.models.attachments import *  # noqa
from app.models.marketing import *  # noqa
from app.models.cskh import *  # noqa
from app.models.ra_soat_tien import *  # noqa
from app.models.ky_thuat import *  # noqa
from app.models.ngoai_le import *  # noqa
from app.models.kiem_soat import *  # noqa
from app.models.hach_toan import *  # noqa
from app.models.quyet_toan import *  # noqa
from app.models.lop3_tour import *  # noqa
from app.models.nap_bo_sung import *  # noqa
from app.models.doc_chung_tu import *  # noqa
# V7 Đợt 3 (10/9/2026). su_co_tour đứng SAU cskh và hr: nó mang khoá ngoài sang complaints và
# incidents, nên hai bảng kia phải có mặt trong metadata trước.
from app.models.su_co_tour import *  # noqa
from app.models.kiem_toan import *  # noqa
# Đội xe thiếu ở đây từ đầu. Ứng dụng vẫn chạy vì các dịch vụ nạp thẳng app.models.fleet, nhưng
# Base.metadata sau `import app.models` thì thiếu 20 bảng – nên mọi phép thử soi metadata đều mù
# đúng phần đội xe. Phát hiện ngày 09/9/2026 khi phép thử canh cột tiền K2 chỉ nhìn thấy 62 trong
# 83 cột và vẫn báo xanh.
from app.models.fleet import *  # noqa
# V11. Thiếu dòng này thì hai bảng lịch tự động hoá không nằm trong Base.metadata: create_all không
# tạo, phép thử soi mô hình mù đúng phần ấy, và alembic autogenerate sẽ đòi XOÁ bảng. Bộ kiểm KS-7
# tìm ra ngày 11/9/2026 – cùng một lỗi đã xảy ra với đội xe (09/9) và VPM-5 (11/9).
from app.models.tu_dong import *  # noqa
# Robot A · DT-2 (11/9/2026). Chốt số dư đã đối soát. Đứng SAU banks và core: nó mang khoá ngoài
# sang bank_accounts_cat và companies. Bốn lần cùng một lỗi đã xảy ra ở tệp này – đội xe (09/9),
# VPM-5, V11 và tu_dong (11/9) – nên thêm bảng mới thì thêm dòng nhập ở đây NGAY, đừng để lần sau.
from app.models.dong_tien import *  # noqa
# Robot A · 13/9/2026. Sổ gán người bán cho kho quyết toán cũ. Đứng SAU core: mang khoá ngoài sang
# users. Lần thứ năm nhắc cùng một điều ở tệp này – thêm bảng thì thêm dòng nhập ở đây NGAY.
from app.models.kho_cu import *  # noqa
# TC-41 (16/9/2026) – kế hoạch tháng. Đứng SAU core: nó mang khoá ngoài sang companies. Lần thứ SÁU
# nhắc cùng một điều ở tệp này – đội xe (09/9), VPM-5, V11, tu_dong (11/9), kho_cu (13/9) – và lần
# này chính bộ kiểm KS-7 bắt được ngay trong vòng đầu: bảng khai dưới app/models mà không có dòng
# nhập ở đây thì `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate
# sẽ đòi XOÁ bảng.
from app.models.ke_hoach import *  # noqa

# Robot A · 16/9/2026. Sổ tỷ giá – Chủ tịch chốt "nhân viên tự nhập tại từng thời điểm". Không mang
# khoá ngoài sang bảng nào nên đứng đâu cũng được, nhưng vẫn phải CÓ MẶT ở đây: lần thứ sáu nhắc
# cùng một điều ở tệp này – thiếu dòng nhập thì create_all không tạo bảng, phép thử soi mô hình mù
# đúng phần ấy, và alembic autogenerate sẽ đòi XOÁ bảng.
from app.models.ty_gia import *  # noqa  # k2-doc-an-toan: dòng NHẬP MODULE, không đọc cột tiền nào — bộ dò thấy dấu sao của `import *` và tưởng là phép nhân

# TC-73 · 19/9/2026. Cơ cấu tổ chức khối Kinh doanh (don_vi_kd, phan_cong_kd). Lần thứ bảy nhắc cùng một điều ở tệp này – thiếu dòng nhập thì create_all không
# tạo bảng, phép thử soi mô hình mù đúng phần ấy, và alembic autogenerate sẽ đòi XOÁ bảng.
from app.models.to_chuc_kd import *  # noqa

# 19/9/2026 · Nối tài khoản VTOS với Zalo, để cảnh báo khủng hoảng tới được NGƯỜI chứ không chỉ tới
# màn hình. Mang khoá ngoài sang `users` nên đứng SAU core. Và lần thứ TÁM nhắc cùng một điều ở tệp
# này: bảng khai dưới app/models mà thiếu dòng nhập ở đây thì `import app.models` không thấy nó,
# create_all không tạo, và alembic autogenerate sẽ đòi XOÁ bảng.
from app.models.zalo_noi import *  # noqa

# TC-74 · 19/9/2026. Đối tác bán hàng của khối Kinh doanh. Lần thứ CHÍN nhắc cùng một điều ở
# tệp này: bảng khai dưới app/models mà thiếu dòng nhập ở đây thì create_all không tạo, phép
# thử soi mô hình mù đúng phần ấy, và alembic autogenerate sẽ đòi XOÁ bảng.
from app.models.doi_tac_ban_hang import *  # noqa
from app.models.chi_tieu_kd import *  # noqa

# 19/9/2026 · Sổ gửi báo động khủng hoảng. Mang khoá ngoài sang `alerts` và `users` nên đứng SAU
# core. Và lần thứ CHÍN nhắc cùng một điều ở tệp này: bảng khai dưới app/models mà thiếu dòng nhập
# ở đây thì `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate sẽ
# đòi XOÁ bảng.
from app.models.bao_dong import *  # noqa

# TC-81 · 24/9/2026. KOL / KOC — danh bạ người hợp tác nội dung và từng lần hợp tác có tiền. Mang
# khoá ngoài sang `campaigns`, `companies` và `payment_requests` nên đứng SAU core và marketing.
# Lần thứ MƯỜI nhắc cùng một điều ở tệp này: bảng khai dưới app/models mà thiếu dòng nhập ở đây
# thì `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate đòi XOÁ bảng.
from app.models.kol import *  # noqa

# TC-83 · 24/9/2026. Bia mộ tài khoản đã xoá. KHÔNG mang khoá ngoài sang `users` — cố ý, vì hàng ở
# users đã biến mất đúng lúc hàng này được ghi, khoá ngoài sẽ chặn chính việc ghi. Lần thứ MƯỜI MỘT
# nhắc cùng một điều ở tệp này: bảng khai dưới app/models mà thiếu dòng nhập ở đây thì
# `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate đòi XOÁ bảng.
from app.models.tai_khoan_da_xoa import *  # noqa

# CSKH tự động · 25/9/2026. Đánh giá sau tour do KHÁCH tự chấm, và mã khảo sát dùng một lần cho
# cửa công khai. Mang khoá ngoài sang `care_tickets`, `bookings`, `tours` nên đứng SAU cskh và
# core. Lần thứ MƯỜI HAI nhắc cùng một điều ở tệp này: bảng khai dưới app/models mà thiếu dòng
# nhập ở đây thì `import app.models` không thấy nó, create_all không tạo, và alembic autogenerate
# đòi XOÁ bảng.
from app.models.danh_gia import *  # noqa

# 28/9/2026 · Công nợ khách theo Vietrip – ảnh chụp mỗi ngày (báo cáo 8h sáng). Không mang khoá
# ngoài sang bảng nào ngoài hai bảng của chính nó.
from app.models.cong_no_vietrip import *  # noqa  # k2-doc-an-toan: dòng NHẬP MODULE, không đọc cột tiền nào

# 08/10/2026 · Dấu nguồn quảng cáo + hàng đợi chuyển đổi gửi đi (TC-103, TC-105). Thiếu dòng
# này thì hai bảng ấy KHÔNG vào Base.metadata khi nạp app.models, và mọi bộ kiểm soi metadata
# mù đúng phần đó mà vẫn báo xanh – đúng chuyện đã xảy ra với Đội xe ngày 09/9/2026.
from app.models.quang_cao import *  # noqa

# 09/10/2026 · Đợt E1 – bảng mức độ chặn của từng phép kiểm. Thiếu dòng này thì bảng không vào
# Base.metadata, create_all không tạo, và alembic autogenerate đòi XOÁ nó.
from app.models.muc_do_chan import *  # noqa
from app.models.tach_nhiem import *  # noqa
from app.models.mo_lai_ky import *  # noqa  # Đợt E6 13/10/2026 — hồ sơ mở lại kỳ kế toán
from app.models.so_hoa_don import *  # noqa  # Đợt E7 13/10/2026 — sổ số nhảy hóa đơn
