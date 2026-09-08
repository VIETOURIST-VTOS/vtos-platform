"""Kho token Zalo OA – token sống trong cơ sở dữ liệu, không phải biến môi trường

Revision ID: za1b2c3d4e5f
Revises: v9b2e7c3a91d5
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "za1b2c3d4e5f"
down_revision = "v9b2e7c3a91d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zalo_oa_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("oa_id", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("access_token", sa.Text(), nullable=False, server_default=""),
        sa.Column("refresh_token", sa.Text(), nullable=False, server_default=""),
        sa.Column("het_han_luc", sa.DateTime(), nullable=True),
        sa.Column("lan_lam_moi", sa.DateTime(), nullable=True),
        sa.Column("so_lan_lam_moi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ma_chong_gia", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("loi_cuoi", sa.Text(), nullable=False, server_default=""),
        sa.Column("cap_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_zalo_oa_tokens_oa_id", "zalo_oa_tokens", ["oa_id"])


def downgrade() -> None:
    op.drop_index("ix_zalo_oa_tokens_oa_id", table_name="zalo_oa_tokens")
    op.drop_table("zalo_oa_tokens")
