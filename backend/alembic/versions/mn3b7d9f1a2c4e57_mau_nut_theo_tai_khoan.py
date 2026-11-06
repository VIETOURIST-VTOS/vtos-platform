"""KS-NUT · màu nút riêng theo tài khoản – navy đậm (A) hoặc xanh sáng (B)

Revision ID: mn3b7d9f1a2c4e57
Revises: ks20e1a3c5e7b9d135
Create Date: 2026-11-07

Anh Tuấn duyệt cả hai phương án của bản xem thử «Navy bên trong VTOS» (07/11/2026) và cho người
dùng tự bấm chọn trong bảng «Giao diện». MỘT cột thêm vào `users`, không đụng cột nào khác.

Cùng quy ước RỖNG KHÁC MẶC ĐỊNH như gd_nen: "" = người này chưa chọn (đi theo mặc định hệ thống,
hiện là "navy"); KHÔNG điền sẵn "navy" cho các tài khoản đang có.
"""
import sqlalchemy as sa
from alembic import op

revision = "mn3b7d9f1a2c4e57"
down_revision = "ks20e1a3c5e7b9d135"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("gd_mau_nut", sa.String(length=8),
                                     nullable=False, server_default=""))


def downgrade():
    op.drop_column("users", "gd_mau_nut")
