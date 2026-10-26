"""KH-4 — đánh giá trên cổng, góp ý riêng lãnh đạo, yêu cầu hỗ trợ.

Revision ID: kh4e7a1c3d5f28
Revises: kh3c2e9b5d7f13
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "kh4e7a1c3d5f28"
down_revision = "kh3c2e9b5d7f13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phieu_danh_gia_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("care_id", sa.Integer(), sa.ForeignKey("care_tickets.id"), nullable=False, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("gui_luc", sa.DateTime(), nullable=True),
        sa.Column("han_sua", sa.Date(), nullable=False),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("so_lan_sua", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cong_khai", sa.String(length=6), nullable=False, server_default=""),
        sa.Column("gop_y", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "gop_y_lanh_dao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=12), nullable=False, unique=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("tieu_de", sa.String(length=200), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("muc", sa.String(length=8), nullable=False, server_default="thuong"),
        sa.Column("lien_he_qua", sa.String(length=8), nullable=False, server_default="email"),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="moi", index=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("ghi_chu_noi_bo", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tra_loi_luc", sa.DateTime(), nullable=True),
        sa.Column("cap_nhat_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("cap_nhat_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True, index=True),
    )
    op.create_table(
        "ho_tro_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=12), nullable=False, unique=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True, index=True),
        sa.Column("loai", sa.String(length=8), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("hoa_don", sa.JSON(), nullable=True),
        sa.Column("bo_phan", sa.String(length=12), nullable=False, index=True),
        sa.Column("giao_cho_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="moi", index=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tra_loi_luc", sa.DateTime(), nullable=True),
        sa.Column("nhan_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("cap_nhat_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table("ho_tro_khach")
    op.drop_table("gop_y_lanh_dao")
    op.drop_table("phieu_danh_gia_khach")
