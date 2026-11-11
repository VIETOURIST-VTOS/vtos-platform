"""VH-27 · hai nút «Công việc» / «Chờ duyệt»: nhớ dòng nào người dùng đã bấm xem

Revision ID: vx27a1c3e5f7b9d2
Revises: tb6d1e3a9c5f2b84
Create Date: 2026-11-12

Chủ tịch duyệt 12/11/2026: bấm một dòng trong danh sách xổ thì số trên nút giảm, nhớ TRÊN MÁY CHỦ (đổi máy vẫn
giữ). MỘT cột JSON thêm vào `users`, rỗng = chưa xem dòng nào.
"""
import sqlalchemy as sa
from alembic import op

revision = "vx27a1c3e5f7b9d2"
down_revision = "tb6d1e3a9c5f2b84"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("viec_da_xem", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("users", "viec_da_xem")
