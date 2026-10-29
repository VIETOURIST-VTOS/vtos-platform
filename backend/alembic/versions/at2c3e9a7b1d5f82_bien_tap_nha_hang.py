"""AT-2c — Biên tập và mức hoàn thiện nhà hàng: Chủ tịch giao người biên tập + hạn (Chủ tịch chốt 29/10/2026).

Revision ID: at2c3e9a7b1d5f82
Revises: at2b8d2f0e6a1c39
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "at2c3e9a7b1d5f82"
down_revision = "at2b8d2f0e6a1c39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bien_tap_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False, unique=True),
        sa.Column("nguoi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("han", sa.Date(), nullable=True),
        sa.Column("giao_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("giao_luc", sa.DateTime(), nullable=True),
        sa.Column("da_xin_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("da_xin_luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("bien_tap_nha_hang")
