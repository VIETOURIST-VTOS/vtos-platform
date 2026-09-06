"""Hồ sơ nhân sự: ngày sinh và số điện thoại (nạp danh sách tài xế 06/9/2026)

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "f2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("employees", sa.Column("birth_date", sa.Date, nullable=True))
    op.add_column("employees", sa.Column("phone", sa.String(30), nullable=False, server_default=""))


def downgrade():
    op.drop_column("employees", "phone")
    op.drop_column("employees", "birth_date")
