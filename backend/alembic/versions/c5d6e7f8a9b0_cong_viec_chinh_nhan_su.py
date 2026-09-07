"""Công việc chính của nhân sự (tuyến / thị trường phụ trách) – bảng phân công Điều hành & Visa 07/9/2026

Điều hành nội địa và outbound mỗi người phụ trách một nhóm tuyến, chuyên viên visa phụ trách thị trường.
Trước đây thông tin này chỉ nằm trong file của HCNS nên không dùng được để giao việc hay soát tải.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""
from alembic import op
import sqlalchemy as sa

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("employees", sa.Column("duties", sa.Text, nullable=False, server_default=""))


def downgrade():
    op.drop_column("employees", "duties")
