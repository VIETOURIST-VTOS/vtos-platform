"""EM-1 · Cột email công việc trên bảng users.

Chủ tịch duyệt 18/10/2026: tách khỏi email cá nhân của hồ sơ nhân sự; đuôi bắt buộc
@vietourist.com.vn (kiểm ở services/email_cong_viec.py, không ở cơ sở dữ liệu — rỗng hợp lệ).

`server_default=""`: bảng users đang có dữ liệu thật; tài khoản cũ là «chưa có», không phải NULL.

Revision ID: em1u5e2c9v41
Revises: dx5t0u7s9e4a
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa

revision = "em1u5e2c9v41"
down_revision = "dx5t0u7s9e4a"   # head của main b8f42a6, đo 18/10/2026
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_cong_viec", sa.String(120), nullable=False,
                                     server_default=""))


def downgrade():
    op.drop_column("users", "email_cong_viec")
