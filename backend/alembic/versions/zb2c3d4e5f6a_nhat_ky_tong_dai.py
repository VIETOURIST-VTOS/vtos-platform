"""Nhật ký nguyên văn sự kiện tổng đài (nghe trước, hiểu sau)

Revision ID: zb2c3d4e5f6a
Revises: za1b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa

revision = "zb2c3d4e5f6a"
down_revision = "za1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tong_dai_su_kien",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nguon", sa.String(20), server_default="", nullable=False),
        sa.Column("phuong_thuc", sa.String(10), server_default="", nullable=False),
        sa.Column("duong_dan", sa.String(300), server_default="", nullable=False),
        sa.Column("chuoi_truy_van", sa.Text(), server_default="", nullable=False),
        sa.Column("than", sa.Text(), server_default="", nullable=False),
        sa.Column("dau_muc", sa.JSON(), nullable=True),
        sa.Column("ip_goi", sa.String(60), server_default="", nullable=False),
        sa.Column("da_doc", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("nhan_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tong_dai_su_kien_nguon", "tong_dai_su_kien", ["nguon"])
    op.create_index("ix_tong_dai_su_kien_ip_goi", "tong_dai_su_kien", ["ip_goi"])
    op.create_index("ix_tong_dai_su_kien_nhan_luc", "tong_dai_su_kien", ["nhan_luc"])


def downgrade():
    op.drop_table("tong_dai_su_kien")
