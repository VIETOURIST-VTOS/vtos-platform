"""VPM-9 – lịch thanh toán theo tiến độ của hợp đồng khách

Revision ID: z3d7f2a5c9e18
Revises: y2c6e1f4b8d37

Chỉ THÊM một bảng, không đụng `hop_dong_khach`. Cột `han_thanh_toan` cũ vẫn ở nguyên chỗ và vẫn có
nghĩa: từ nay nó là hạn của ĐỢT CUỐI, do dịch vụ đặt lịch ghi vào. Giữ lại chứ không bỏ, vì nhiều
chỗ trong hệ thống đang đọc nó; bỏ đi là đổi hành vi của những chỗ ấy trong cùng một bản vá mà không
ai soát.

`so_tien` để nullable KHÔNG mặc định, theo luật K2: rỗng nghĩa là chưa ai nhập, không phải bằng không.
`ty_le` là TỶ LỆ chứ không phải tiền, nên là Float – không kéo nó vào phạm vi cột tiền.
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "z3d7f2a5c9e18"
down_revision = "y2c6e1f4b8d37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lich_thanh_toan_hd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hop_dong_id", sa.Integer(), sa.ForeignKey("hop_dong_khach.id"), nullable=False, index=True),
        sa.Column("dot", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ten", sa.String(length=120), nullable=True),
        sa.Column("ty_le", sa.Float(), nullable=True),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("moc", sa.String(length=20), nullable=True),
        sa.Column("moc_so_ngay", sa.Integer(), nullable=True),
        sa.Column("han", sa.Date(), nullable=True),
        sa.Column("han_goc", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("boi", sa.String(length=50), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("lich_thanh_toan_hd")
