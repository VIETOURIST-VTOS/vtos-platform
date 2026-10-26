"""KH-2 — danh mục nhà hàng + thực đơn cho cổng khách; yêu cầu khách mang thông tin đặt bàn.

Revision ID: kh2b8d3f6a1c74
Revises: kh1a4c7e2b9d51
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "kh2b8d3f6a1c74"
down_revision = "kh1a4c7e2b9d51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False, unique=True),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("tinh_thanh", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("khu_vuc", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("am_thuc", sa.String(length=40), nullable=False, server_default="Việt Nam"),
        sa.Column("gio_phuc_vu", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("tien_ich", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("mo_ta", sa.Text(), nullable=False, server_default=""),
        sa.Column("ghi_chu_noi_bo", sa.Text(), nullable=False, server_default=""),
        sa.Column("hien_cong", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hien_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("hien_luc", sa.DateTime(), nullable=True),
        sa.Column("tat_ly_do", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ngung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tao_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "thuc_don_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False, index=True),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("loai", sa.String(length=12), nullable=False, server_default="set"),
        sa.Column("gia_nguoi_lon", sa.Numeric(18, 2), nullable=True),
        sa.Column("gia_tre_em", sa.Numeric(18, 2), nullable=True),
        sa.Column("so_khach_toi_thieu", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mo_ta", sa.Text(), nullable=False, server_default=""),
        sa.Column("dieu_kien", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("dieu_kien_huy", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("tu_ngay", sa.Date(), nullable=True),
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("dang_ban", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.add_column("yeu_cau_khach", sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=True))
    op.add_column("yeu_cau_khach", sa.Column("thuc_don_id", sa.Integer(), sa.ForeignKey("thuc_don_nha_hang.id"), nullable=True))
    op.add_column("yeu_cau_khach", sa.Column("gio_den", sa.String(length=5), nullable=False, server_default=""))
    op.add_column("yeu_cau_khach", sa.Column("tre_em", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("yeu_cau_khach", sa.Column("tam_tinh", sa.Integer(), nullable=True))


def downgrade() -> None:
    for c in ("tam_tinh", "tre_em", "gio_den", "thuc_don_id", "nha_hang_id"):
        op.drop_column("yeu_cau_khach", c)
    op.drop_table("thuc_don_nha_hang")
    op.drop_table("nha_hang")
