"""TK-1e — lịch ngày lễ Tết cho tạm tính tour đoàn (thù lao HDV ngày lễ ×2).

Chủ tịch 04/11/2026: «có nhân đôi». Điều hành nhập ngày ở màn /tour-doan.

Revision ID: tk1e7b9d1f3a5c8e02
Revises: tk1a5c7e9b2d4f6081
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op

revision = "tk1e7b9d1f3a5c8e02"
down_revision = "tk1a5c7e9b2d4f6081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ngay_le_tet",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("ten", sa.String(120), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ngay_le_tet_ngay", "ngay_le_tet", ["ngay"], unique=True)


def downgrade() -> None:
    op.drop_table("ngay_le_tet")
