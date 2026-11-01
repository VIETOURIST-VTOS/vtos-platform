"""KS-16p — «Đặt giữ, trả sau» cho đơn khách sạn VTD (Chủ tịch duyệt bản xem thử 01/11/2026). Chỉ thêm cột.

Revision ID: ks16pe9a1c3e5f7b2
Revises: ks16kd7f9b1c3e5a8
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16pe9a1c3e5f7b2"
down_revision = "ks16kd7f9b1c3e5a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("don_ks_vtd") as b:
        b.add_column(sa.Column("cach_tra", sa.String(6), nullable=False, server_default="ngay"))
        b.add_column(sa.Column("han_tra", sa.Date(), nullable=True))
        b.add_column(sa.Column("nhac_luc", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("don_ks_vtd") as b:
        for c in ("nhac_luc", "han_tra", "cach_tra"):
            b.drop_column(c)
