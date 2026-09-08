"""Hạng giấy phép lái xe – cột mới trên giấy tờ xe/tài xế

Revision ID: gp3c8e5b1d47
Revises: v2d4a8f1c6e2
Create Date: 2026-09-08

Trước bản này hệ thống lưu SỐ và HẠN của giấy phép lái xe nhưng không lưu HẠNG. Nghĩa là cổng điều
xe kiểm được "giấy còn hạn không" mà không kiểm được "người này có được lái xe 45 chỗ không" – và đó
mới là câu hỏi mà 45 hành khách trên xe quan tâm.

Cột để RỖNG cho mọi giấy đã có: rỗng nghĩa là CHƯA BIẾT, và cổng điều xe sẽ trả về "chưa đủ dữ liệu"
chứ không trả về "đạt". Không điền đại một hạng mặc định.
"""
from alembic import op
import sqlalchemy as sa

revision = "gp3c8e5b1d47"
down_revision = "v2d4a8f1c6e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicle_documents",
                  sa.Column("hang", sa.String(length=30), server_default="", nullable=False))


def downgrade() -> None:
    op.drop_column("vehicle_documents", "hang")
