"""KS-16 — VTD Rewards cho khách sạn VTD: tích điểm như tour, khách tự nhập voucher (Chủ tịch duyệt 30/10/2026).

Chỉ THÊM cột, đều rỗng / 0 cho dữ liệu cũ.

Revision ID: ks16d4e7f9a2b638
Revises: ks15c3d6e8f1a527
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16d4e7f9a2b638"
down_revision = "ks15c3d6e8f1a527"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("don_ks_vtd") as b:
        b.add_column(sa.Column("voucher_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("giam_voucher", sa.Numeric(18, 2), nullable=False, server_default="0"))
        b.add_column(sa.Column("km_but_toan", sa.String(length=30), nullable=False, server_default=""))
    with op.batch_alter_table("so_diem_rewards") as b:
        b.add_column(sa.Column("don_ks_id", sa.Integer(), sa.ForeignKey("don_ks_vtd.id", name="fk_so_diem_don_ks"), nullable=True))
        b.create_index("ix_so_diem_rewards_don_ks_id", ["don_ks_id"])
    with op.batch_alter_table("voucher_rewards") as b:
        b.add_column(sa.Column("don_ks_id", sa.Integer(), sa.ForeignKey("don_ks_vtd.id", name="fk_voucher_don_ks"), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("voucher_rewards") as b:
        b.drop_column("don_ks_id")
    with op.batch_alter_table("so_diem_rewards") as b:
        b.drop_index("ix_so_diem_rewards_don_ks_id")
        b.drop_column("don_ks_id")
    with op.batch_alter_table("don_ks_vtd") as b:
        b.drop_column("km_but_toan")
        b.drop_column("giam_voucher")
        b.drop_column("voucher_id")
