from app.models.core import *  # noqa
from app.models.payments import *  # noqa
from app.models.accounting import *  # noqa
from app.models.assets import *  # noqa
from app.models.banks import *  # noqa
from app.models.hr import *  # noqa
from app.models.hrm import *  # noqa
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
