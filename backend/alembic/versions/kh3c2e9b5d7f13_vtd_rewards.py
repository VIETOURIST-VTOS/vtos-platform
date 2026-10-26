"""KH-3 — VTD Rewards: sổ điểm chỉ ghi thêm, voucher, yêu thích.

Revision ID: kh3c2e9b5d7f13
Revises: kh2b8d3f6a1c74
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "kh3c2e9b5d7f13"
down_revision = "kh2b8d3f6a1c74"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voucher_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False, unique=True),
        sa.Column("chu", sa.String(length=80), nullable=False, index=True),
        sa.Column("so_diem", sa.Integer(), nullable=False),
        sa.Column("gia_tri", sa.BigInteger(), nullable=False),
        sa.Column("han_dung", sa.Date(), nullable=False),
        sa.Column("han_diem_goc", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="cho_dung"),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("ap_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ap_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "so_diem_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chu", sa.String(length=80), nullable=False, index=True),
        sa.Column("loai", sa.String(length=10), nullable=False),
        sa.Column("so_diem", sa.BigInteger(), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True, index=True),
        sa.Column("voucher_id", sa.Integer(), sa.ForeignKey("voucher_rewards.id"), nullable=True),
        sa.Column("het_han", sa.Date(), nullable=True),
        sa.Column("co_so", sa.BigInteger(), nullable=True),
        sa.Column("he_so", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("hang", sa.String(length=12), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "yeu_thich_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("gia_luc_luu", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tai_khoan_id", "tour_id", name="uq_yeu_thich"),
    )


def downgrade() -> None:
    op.drop_table("yeu_thich_khach")
    op.drop_table("so_diem_rewards")
    op.drop_table("voucher_rewards")
