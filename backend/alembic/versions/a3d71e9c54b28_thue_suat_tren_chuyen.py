"""Đ-2c · Hai ô thuế suất trên từng chuyến, cho Điều hành nhập

Revision ID: a3d71e9c54b28
Revises: f2a6c81b93d47
Create Date: 2026-09-14

Chủ tịch chốt 14/9/2026:

    "Thuế GTGT tour châu Âu là tour nước ngoài nên tính 0%, nhưng em cứ viết cấu trúc và thuật
     toán, còn tỷ lệ % để cho Điều hành nhập vào."

Hai cột mới trên `tours`, đều rỗng được – không sửa dữ liệu nào đang có, nên bản này lùi lại sạch.

    thue_suat_ra_pt          thuế suất đầu ra của chuyến này
    thue_suat_ngoai_vn_pt    thuế suất dòng "dịch vụ tiêu dùng ngoài Việt Nam" (tour nước ngoài)

HẬU TỐ `_pt` LÀ PHẦN CỦA TÊN, KHÔNG PHẢI TRANG TRÍ

Đơn vị của hai cột này là PHẦN TRĂM: 8 nghĩa là 8%. Tham số công ty (`thue_suat_dau_ra`,
`thue_suat_ngoai_vn`) thì là SỐ THẬP PHÂN: 0.08 nghĩa là 8%. Hai cách viết cùng một thứ, lệch nhau
đúng 100 lần, và không bao giờ tự lộ ra vì cả hai đều ra một con số tiền trông hợp lý.

Bài học ấy đã phải trả giá một lần: ô % chia tip ngày 12/9 có một "luật ngầm" nhận cả `0.4` lẫn `40`
bằng quy tắc *lớn hơn 1 thì chia 100* — gõ `1` là 100% hay 1%? Luật ấy đã bị gỡ, và từ đó đơn vị
nằm ngay trong tên. Cột này theo đúng quy ước đó.

RỖNG CÓ NGHĨA, KHÔNG PHẢI CHƯA LÀM

Rỗng = chuyến này dùng tham số công ty đang hiệu lực. Máy KHÔNG bao giờ điền sẵn một con số vào đây:
điền sẵn thì sáu tháng sau không ai phân biệt được "Điều hành đã cân nhắc và chọn 8%" với "máy để
mặc định 8% và không ai nhìn".
"""
import sqlalchemy as sa
from alembic import op

revision = "a3d71e9c54b28"
down_revision = "f2a6c81b93d47"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tours", sa.Column("thue_suat_ra_pt", sa.Float(), nullable=True))
    op.add_column("tours", sa.Column("thue_suat_ngoai_vn_pt", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("tours", "thue_suat_ngoai_vn_pt")
    op.drop_column("tours", "thue_suat_ra_pt")
