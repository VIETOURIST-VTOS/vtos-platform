"""AT-3 — Đánh giá sao nhà hàng: chỉ người đặt đơn «khách đã dùng» (Chủ tịch duyệt 29/10/2026).

Revision ID: at3a5d8c2e7f4b19
Revises: at2c3e9a7b1d5f82
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "at3a5d8c2e7f4b19"
down_revision = "at2c3e9a7b1d5f82"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "danh_gia_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("don_id", sa.Integer(), sa.ForeignKey("don_dat_ban.id"), nullable=False, unique=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("ten_hien", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("ngay_an", sa.Date(), nullable=False),
        sa.Column("so_khach", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("la_doan", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("diem", sa.Integer(), nullable=False),
        sa.Column("diem_mon", sa.Integer(), nullable=True),
        sa.Column("diem_phuc_vu", sa.Integer(), nullable=True),
        sa.Column("diem_khong_gian", sa.Integer(), nullable=True),
        sa.Column("diem_gia", sa.Integer(), nullable=True),
        sa.Column("nhan_xet", sa.Text(), nullable=False, server_default=""),
        sa.Column("anh", sa.JSON(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("an", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("an_ly_do", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("an_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("an_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("an_luc", sa.DateTime(), nullable=True),
        sa.Column("xem_lai", sa.String(length=6), nullable=False, server_default=""),
        sa.Column("xem_lai_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xem_lai_luc", sa.DateTime(), nullable=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi_boi", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("tra_loi_luc", sa.DateTime(), nullable=True),
        sa.Column("tra_loi_an", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tra_loi_an_ly_do", sa.String(length=20), nullable=False, server_default=""),
    )
    op.create_index("ix_danh_gia_nha_hang_nha_hang_id", "danh_gia_nha_hang", ["nha_hang_id"])
    op.create_index("ix_danh_gia_nha_hang_tai_khoan_id", "danh_gia_nha_hang", ["tai_khoan_id"])
    op.create_index("ix_danh_gia_nha_hang_tao_luc", "danh_gia_nha_hang", ["tao_luc"])
    op.create_index("ix_danh_gia_nha_hang_an", "danh_gia_nha_hang", ["an"])


def downgrade() -> None:
    op.drop_index("ix_danh_gia_nha_hang_an", "danh_gia_nha_hang")
    op.drop_index("ix_danh_gia_nha_hang_tao_luc", "danh_gia_nha_hang")
    op.drop_index("ix_danh_gia_nha_hang_tai_khoan_id", "danh_gia_nha_hang")
    op.drop_index("ix_danh_gia_nha_hang_nha_hang_id", "danh_gia_nha_hang")
    op.drop_table("danh_gia_nha_hang")
