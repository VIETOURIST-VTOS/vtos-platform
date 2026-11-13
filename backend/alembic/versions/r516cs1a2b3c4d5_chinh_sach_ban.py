"""R5-16 · Chính sách bán của Phòng Kinh doanh Lẻ

Revision ID: r516cs1a2b3c4d5
Revises: tr8a1c7e5d93f24b
Create Date: 2026-11-14

Chủ tịch duyệt 14/11/2026: «Giá & chính sách bán» thành «Chính sách bán» — chiết khấu tối đa theo vai,
giá trẻ em / em bé / phụ thu, khuyến mãi; mỗi lần ban hành một bản có hiệu lực từ–đến. Bảng MỚI, không đụng
cột nào đang có.
"""
import sqlalchemy as sa
from alembic import op

revision = "r516cs1a2b3c4d5"
down_revision = "tr8a1c7e5d93f24b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chinh_sach_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("mang", sa.String(20), server_default="kd_le"),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        sa.Column("hieu_luc_den", sa.Date(), nullable=True),
        sa.Column("noi_dung", sa.Text(), server_default="{}"),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("tao_boi", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chinh_sach_ban_ma", "chinh_sach_ban", ["ma"], unique=True)
    op.create_index("ix_chinh_sach_ban_mang", "chinh_sach_ban", ["mang"])
    op.create_index("ix_chinh_sach_ban_hieu_luc_tu", "chinh_sach_ban", ["hieu_luc_tu"])


def downgrade():
    op.drop_table("chinh_sach_ban")
