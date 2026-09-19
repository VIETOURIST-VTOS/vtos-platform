"""Nối tài khoản VTOS với Zalo — để cảnh báo tới được NGƯỜI, không chỉ tới màn hình

Revision ID: zn8c3e1f7a4d26
Revises: tc73kd0a1b2c3d
Create Date: 2026-09-19

HAI BẢNG

`zalo_noi_tai_khoan` — một tài khoản VTOS ↔ một UID Zalo. HAI ràng buộc DUY NHẤT, và cái thứ hai
mới là cái quan trọng: thiếu ràng buộc duy nhất trên `zalo_uid` thì một chiếc điện thoại nối được
vào hai tài khoản, và cảnh báo dành riêng cho Chủ tịch tới một máy mà người khác cũng đang cầm.
Cơ sở dữ liệu chặn được chuyện ấy; một phép kiểm trong mã thì không, vì nó chỉ chạy khi có ai gọi.

`zalo_ma_noi` — mã dùng một lần, sống 10 phút. `het_han` có chỉ mục vì mọi lần tra đều lọc theo nó.

VÌ SAO KHÔNG THÊM CỘT VÀO `users`: bảng ấy là bảng nóng nhất kho, mọi làn đều đọc; thêm một cột
vào đó là thêm một chỗ đụng nhau. Quan hệ này lại rời rạc và một-một — nối được, gỡ được, phần lớn
tài khoản không có — nên nó đúng hình một bảng nối hơn là một cột.

`da_dung` dùng server_default=sa.false(), KHÔNG dùng sa.text("0"): Postgres không nhận "0" cho kiểu
boolean và bản di trú sẽ chết lúc khởi động hộp chứa, không phải lúc chạy phép thử.
"""
import sqlalchemy as sa
from alembic import op

revision = "zn8c3e1f7a4d26"
down_revision = "tc73kd0a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "zalo_noi_tai_khoan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("zalo_uid", sa.String(length=40), nullable=False),
        sa.Column("gan_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("gan_boi", sa.String(length=50), nullable=False, server_default=""),
    )
    op.create_index("ix_zalo_noi_user", "zalo_noi_tai_khoan", ["user_id"], unique=True)
    op.create_index("ix_zalo_noi_uid", "zalo_noi_tai_khoan", ["zalo_uid"], unique=True)

    op.create_table(
        "zalo_ma_noi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ma", sa.String(length=12), nullable=False),
        sa.Column("het_han", sa.DateTime(), nullable=False),
        sa.Column("da_dung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("lan_sai", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_zalo_ma_user", "zalo_ma_noi", ["user_id"])
    op.create_index("ix_zalo_ma_ma", "zalo_ma_noi", ["ma"])
    op.create_index("ix_zalo_ma_het_han", "zalo_ma_noi", ["het_han"])


def downgrade():
    op.drop_index("ix_zalo_ma_het_han", table_name="zalo_ma_noi")
    op.drop_index("ix_zalo_ma_ma", table_name="zalo_ma_noi")
    op.drop_index("ix_zalo_ma_user", table_name="zalo_ma_noi")
    op.drop_table("zalo_ma_noi")
    op.drop_index("ix_zalo_noi_uid", table_name="zalo_noi_tai_khoan")
    op.drop_index("ix_zalo_noi_user", table_name="zalo_noi_tai_khoan")
    op.drop_table("zalo_noi_tai_khoan")
