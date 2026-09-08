"""Bảng quy tắc hạch toán và hàng đợi thiếu giá vốn

Revision ID: c9d8e7f6a5b4
Revises: f2a3b4c5d6e7
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "c9d8e7f6a5b4"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quy_tac_hach_toan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ma", sa.String(length=40), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("nguon", sa.String(length=20), nullable=False),
        sa.Column("dieu_kien", sa.JSON(), nullable=True),
        sa.Column("tk_no", sa.String(length=10), nullable=False),
        sa.Column("tk_co", sa.String(length=10), nullable=False),
        sa.Column("tk_thue", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("ben_thue", sa.String(length=4), nullable=False, server_default=""),
        sa.Column("ty_le_thue", sa.Float(), nullable=False, server_default="0"),
        sa.Column("doi_tuong", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("can_cong_trinh", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dien_giai", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("uu_tien", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("can_cu", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("signed_chutich", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("signed_tgd", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("proposed_by", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quy_tac_hach_toan_ma", "quy_tac_hach_toan", ["ma"])
    op.create_index("ix_quy_tac_hach_toan_nguon", "quy_tac_hach_toan", ["nguon"])

    op.create_table(
        "thieu_gia_von",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ma_don", sa.String(length=60), nullable=False),
        sa.Column("ky", sa.String(length=7), nullable=False, server_default=""),
        sa.Column("ten", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("doanh_thu", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gia_von", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ly_do", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("phong_ban", sa.String(length=40), nullable=False, server_default="dieu_hanh"),
        sa.Column("nguoi_phu_trach", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="cho"),
        sa.Column("giai_trinh", sa.Text(), nullable=False, server_default=""),
        sa.Column("nguoi_xu_ly", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
        sa.Column("phat_hien_luc", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ma_don"),
    )
    op.create_index("ix_thieu_gia_von_ky", "thieu_gia_von", ["ky"])


def downgrade() -> None:
    op.drop_table("thieu_gia_von")
    op.drop_table("quy_tac_hach_toan")
