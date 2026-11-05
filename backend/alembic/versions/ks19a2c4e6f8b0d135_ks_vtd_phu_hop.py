"""KS-19 · khách sạn VTD: «Phù hợp cho» (bộ lọc cổng). Giá đã gồm 8% VAT — không đổi cột, chỉ đổi phép tính.

Revision ID: ks19a2c4e6f8b0d135
Revises: quy2b8d1f3a5c7e9
"""
import sqlalchemy as sa
from alembic import op

revision = "ks19a2c4e6f8b0d135"
down_revision = "quy2b8d1f3a5c7e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("khach_san_vtd", sa.Column("phu_hop", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("khach_san_vtd", "phu_hop")
