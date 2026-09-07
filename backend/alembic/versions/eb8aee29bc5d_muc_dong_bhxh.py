"""Tiền lương làm căn cứ đóng BHXH bắt buộc – khác mức lương hợp đồng

Danh sách đóng BHXH tháng 08/2026 của VTD: 86 người, mức tham gia 5.310.000 (2 người 4.730.000), trong khi
lương hợp đồng của họ từ 7.000.000 tới 25.000.000. Lấy lương hợp đồng làm căn cứ đóng là trừ của người lao
động gấp nhiều lần số phải trừ. Đoàn phí công đoàn cũng tính trên chính mức này theo thỏa thuận khấu trừ.

Revision ID: eb8aee29bc5d
Revises: b0c1d2e3f4a5
"""
from alembic import op
import sqlalchemy as sa

revision = "eb8aee29bc5d"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("employees", sa.Column("bhxh_base", sa.Float, nullable=False, server_default="0"))


def downgrade():
    op.drop_column("employees", "bhxh_base")
