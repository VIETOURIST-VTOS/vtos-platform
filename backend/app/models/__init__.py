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
