"""KS-20e · địa chỉ + hotline của pháp nhân (in trên phiếu xác nhận / hóa đơn đặt phòng VTD và chân email).

Chủ tịch 07/11/2026 nhắn trực tiếp địa chỉ và số điện thoại của công ty mẹ: «242 Trần Hưng Đạo, TP HCM, 08 62616365».
Bản nâng cấp ghi đúng hai giá trị ấy cho pháp nhân công ty mẹ (mã VTD) KHI ô còn trống — số điện thoại ghi theo mã
vùng hiện hành 028 (mã 08 của TP.HCM đã đổi từ 2017). Kế toán sửa lại được ở màn «Pháp nhân».

Revision ID: ks20e1a3c5e7b9d135
Revises: ks19k4d6f8a0c2e135
"""
import sqlalchemy as sa
from alembic import op

revision = "ks20e1a3c5e7b9d135"
down_revision = "ks19k4d6f8a0c2e135"
branch_labels = None
depends_on = None

DIA_CHI = "242 Trần Hưng Đạo, TP. Hồ Chí Minh"
HOTLINE = "028 6261 6365"


def upgrade() -> None:
    op.add_column("companies", sa.Column("address", sa.String(300), nullable=False, server_default=""))
    op.add_column("companies", sa.Column("phone", sa.String(40), nullable=False, server_default=""))
    op.execute(sa.text("UPDATE companies SET address = :a WHERE code = 'VTD' AND address = ''").bindparams(a=DIA_CHI))
    op.execute(sa.text("UPDATE companies SET phone = :p WHERE code = 'VTD' AND phone = ''").bindparams(p=HOTLINE))


def downgrade() -> None:
    op.drop_column("companies", "phone")
    op.drop_column("companies", "address")
