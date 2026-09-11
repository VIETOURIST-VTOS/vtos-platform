"""VPM-7 – giữ chỗ có thời hạn: bảng nhật ký + bốn cột trên bookings

Revision ID: y2c6e1f4b8d37
Revises: x1b5d9e3a7c24

`giu_cho_den` cố ý để RỖNG cho toàn bộ booking đã có. Rỗng ở đây nghĩa là CHƯA ĐẶT HẠN, không phải
"hết hạn từ lâu": robot đặt hạn cho chúng ở lượt chạy đầu tiên rồi mới tính đến chuyện hết hạn ở lượt
sau. Nếu bản vá này tự điền hạn cho vài nghìn booking cũ thì ngay sáng hôm sau một loạt chỗ bị trả về
mà không ai kịp nhìn — và không cách nào biết chỗ nào bị trả oan.

`giu_cho_het` và `gia_han_lan` thì có server_default: chúng là CỜ và SỐ ĐẾM, không phải cột tiền, nên
luật K2 (NULL ≠ 0) không áp vào đây. "Chưa từng gia hạn" đúng là 0 lần, không phải "chưa ai nhập".
"""
import sqlalchemy as sa
from alembic import op

revision = "y2c6e1f4b8d37"
down_revision = "x1b5d9e3a7c24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nhat_ky_giu_cho",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False, index=True),
        sa.Column("viec", sa.String(length=20), nullable=False),
        sa.Column("han_cu", sa.DateTime(), nullable=True),
        sa.Column("han_moi", sa.DateTime(), nullable=True),
        sa.Column("so_cho", sa.Integer(), nullable=True),
        sa.Column("ly_do", sa.String(length=300), nullable=True),
        sa.Column("boi", sa.String(length=50), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_nhat_ky_giu_cho_booking_luc", "nhat_ky_giu_cho", ["booking_id", "luc"])

    op.add_column("bookings", sa.Column("giu_cho_den", sa.DateTime(), nullable=True))
    op.add_column("bookings", sa.Column("giu_cho_het", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("bookings", sa.Column("giu_cho_het_luc", sa.DateTime(), nullable=True))
    op.add_column("bookings", sa.Column("gia_han_lan", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("bookings", "gia_han_lan")
    op.drop_column("bookings", "giu_cho_het_luc")
    op.drop_column("bookings", "giu_cho_het")
    op.drop_column("bookings", "giu_cho_den")
    op.drop_index("ix_nhat_ky_giu_cho_booking_luc", table_name="nhat_ky_giu_cho")
    op.drop_table("nhat_ky_giu_cho")
