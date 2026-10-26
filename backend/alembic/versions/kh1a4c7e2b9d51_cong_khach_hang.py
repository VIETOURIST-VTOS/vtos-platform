"""KH-1 — cổng khách hàng: bảng yêu cầu khách gửi từ cổng + sở thích trên tài khoản ngoài.

Revision ID: kh1a4c7e2b9d51
Revises: dh1c5a8e3b7d42
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "kh1a4c7e2b9d51"
down_revision = "dh1c5a8e3b7d42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tai_khoan_ngoai", sa.Column("so_thich", sa.String(length=40), nullable=False, server_default=""))
    op.create_table(
        "yeu_cau_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("loai", sa.String(length=12), nullable=False, server_default="tour"),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("ten_tour", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("so_khach", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ngay_mong_muon", sa.Date(), nullable=True),
        sa.Column("dien_thoai", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("yeu_cau_khach")
    op.drop_column("tai_khoan_ngoai", "so_thich")
