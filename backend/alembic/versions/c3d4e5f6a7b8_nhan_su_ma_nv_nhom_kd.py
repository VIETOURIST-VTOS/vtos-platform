"""Nhân sự: mã NV HCNS, nhóm kinh doanh, chức vụ; user.sales_group/staff_code

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("sales_group", sa.String(20), server_default="", nullable=False))
        b.add_column(sa.Column("staff_code", sa.String(20), server_default="", nullable=False))
    with op.batch_alter_table("employees") as b:
        b.add_column(sa.Column("title", sa.String(60), server_default="", nullable=False))
        b.add_column(sa.Column("sales_group", sa.String(20), server_default="", nullable=False))


def downgrade():
    with op.batch_alter_table("employees") as b:
        b.drop_column("sales_group"); b.drop_column("title")
    with op.batch_alter_table("users") as b:
        b.drop_column("staff_code"); b.drop_column("sales_group")
