"""fleet_sale_cases: người mua và hạn thu đủ tiền

Xe bán cho người ngoài (không phải đối tác hợp tác) cần tên người mua, và khoản còn phải thu
cần một mốc cam kết để theo dõi được như một khoản nợ có hạn.

Revision ID: 0fa7043cb785
Revises: 4fff4b171ff8
"""
from alembic import op
import sqlalchemy as sa

revision = "0fa7043cb785"
down_revision = "4fff4b171ff8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("fleet_sale_cases")}
    if "nguoi_mua" not in cols:
        op.add_column("fleet_sale_cases", sa.Column("nguoi_mua", sa.String(160), nullable=False, server_default=""))
    if "han_thu_du" not in cols:
        op.add_column("fleet_sale_cases", sa.Column("han_thu_du", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("fleet_sale_cases", "han_thu_du")
    op.drop_column("fleet_sale_cases", "nguoi_mua")
