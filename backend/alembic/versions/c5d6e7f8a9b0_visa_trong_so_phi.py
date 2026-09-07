"""Visa Đợt 4: trọng số phân bổ phí gia đình trên hồ sơ

Cả nhà nộp một khoản trên MỘT booking. Muốn báo cáo lãi lỗ theo từng đương đơn thì phải chia, và trọng số
cho phép chia không đều (người lớn 1, trẻ em 0,5). Để trống là chia đều. Đây là số quản trị, không phải
chứng từ – chứng từ vẫn là phiếu thu của booking.

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
    op.add_column("visa_cases", sa.Column("fee_weight", sa.Float, nullable=True))


def downgrade():
    op.drop_column("visa_cases", "fee_weight")
