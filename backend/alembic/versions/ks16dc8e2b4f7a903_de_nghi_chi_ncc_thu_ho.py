"""KS-16d — Tự lập đề nghị chi trả khách sạn / nhà hàng tiền thu hộ (Chủ tịch chốt 31/10/2026).

Chỉ THÊM cột, rỗng cho dữ liệu cũ.

Revision ID: ks16dc8e2b4f7a903
Revises: ks16cf2a9c4e6b815
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16dc8e2b4f7a903"
down_revision = "ks16cf2a9c4e6b815"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("don_ks_vtd") as b:
        b.add_column(sa.Column("payment_request_id", sa.Integer(), sa.ForeignKey("payment_requests.id", name="fk_don_ks_vtd_pr"), nullable=True))
    with op.batch_alter_table("don_dat_ban") as b:
        b.add_column(sa.Column("hoa_hong", sa.Numeric(18, 2), nullable=True))
        b.add_column(sa.Column("phai_tra_nh", sa.Numeric(18, 2), nullable=True))
        b.add_column(sa.Column("payment_request_id", sa.Integer(), sa.ForeignKey("payment_requests.id", name="fk_don_dat_ban_pr"), nullable=True))
    with op.batch_alter_table("payment_requests") as b:
        b.add_column(sa.Column("robot_ghi_chu", sa.String(300), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.drop_column("robot_ghi_chu")
    with op.batch_alter_table("don_dat_ban") as b:
        b.drop_column("payment_request_id")
        b.drop_column("phai_tra_nh")
        b.drop_column("hoa_hong")
    with op.batch_alter_table("don_ks_vtd") as b:
        b.drop_column("payment_request_id")
