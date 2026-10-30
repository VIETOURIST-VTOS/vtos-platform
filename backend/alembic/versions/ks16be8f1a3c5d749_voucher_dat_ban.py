"""KS-16b — Voucher VTD Rewards khi trả trước đặt bàn nhà hàng (Chủ tịch duyệt 30/10/2026).

Chỉ THÊM cột, đều rỗng / 0 cho dữ liệu cũ.

Revision ID: ks16be8f1a3c5d749
Revises: ks16d4e7f9a2b638
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16be8f1a3c5d749"
down_revision = "ks16d4e7f9a2b638"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("don_dat_ban") as b:
        b.add_column(sa.Column("voucher_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("giam_voucher", sa.Numeric(18, 2), nullable=False, server_default="0"))
        b.add_column(sa.Column("km_vtd", sa.Numeric(18, 2), nullable=False, server_default="0"))
        b.add_column(sa.Column("km_but_toan", sa.String(length=30), nullable=False, server_default=""))
    with op.batch_alter_table("voucher_rewards") as b:
        b.add_column(sa.Column("dat_ban_id", sa.Integer(), sa.ForeignKey("don_dat_ban.id", name="fk_voucher_dat_ban"), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("voucher_rewards") as b:
        b.drop_column("dat_ban_id")
    with op.batch_alter_table("don_dat_ban") as b:
        b.drop_column("km_but_toan")
        b.drop_column("km_vtd")
        b.drop_column("giam_voucher")
        b.drop_column("voucher_id")
