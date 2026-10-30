"""KS-16e — Bút toán doanh thu hoa hồng khách sạn / nhà hàng (Chủ tịch chốt 31/10/2026). Chỉ thêm cột.

Revision ID: ks16ea3c5e7f9b104
Revises: ks16dc8e2b4f7a903
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16ea3c5e7f9b104"
down_revision = "ks16dc8e2b4f7a903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for bang in ("don_ks_vtd", "don_dat_ban"):
        with op.batch_alter_table(bang) as b:
            b.add_column(sa.Column("dt_but_toan", sa.String(30), nullable=False, server_default=""))


def downgrade() -> None:
    for bang in ("don_dat_ban", "don_ks_vtd"):
        with op.batch_alter_table(bang) as b:
            b.drop_column("dt_but_toan")
