"""Đầu vào do HCNS nhập cho kỳ lương (công chuẩn, công thực tế) – Phụ lục đối chiếu 27/8/2026

Chỉ Kế toán và Nhân sự Hành chính còn chấm công theo ngày; công thực tế của họ là đầu vào của kỳ chứ
không suy ra được từ dữ liệu nghiệp vụ. Lưu cùng kỳ lương để bảng lương giải thích lại được về sau.

Mã bản ghi sinh ngẫu nhiên chứ không đặt tay: hôm nay đã hai lần hai phiên làm việc song song đặt trùng
mã migration và làm hỏng toàn bộ việc triển khai.

Revision ID: 27eb4f9b2c06
Revises: e7f8a9b0c1d2
"""
from alembic import op
import sqlalchemy as sa

revision = "27eb4f9b2c06"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payroll_runs", sa.Column("inputs", sa.JSON, nullable=True))


def downgrade():
    op.drop_column("payroll_runs", "inputs")
