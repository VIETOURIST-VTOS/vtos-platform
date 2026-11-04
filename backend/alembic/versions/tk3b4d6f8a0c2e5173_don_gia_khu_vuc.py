"""TK-3 · đơn giá dịch vụ đoàn gắn khu vực (châu lục / nước) cho tour nước ngoài

Revision ID: tk3b4d6f8a0c2e5173
Revises: tk2a3c5e7f9b1d4062
"""
import sqlalchemy as sa
from alembic import op

revision = "tk3b4d6f8a0c2e5173"
down_revision = "tk2a3c5e7f9b1d4062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("don_gia_doan", sa.Column("khu_vuc", sa.String(60), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("don_gia_doan", "khu_vuc")
