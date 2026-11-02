"""TR-1d — Link thanh toán tour đoàn riêng (Chủ tịch duyệt 02/11/2026). Một bảng mới; không sửa dữ liệu cũ.

Revision ID: tr1d4b6c8e0a2f13
Revises: dk1a7c3e5b9d2f41
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "tr1d4b6c8e0a2f13"
down_revision = "dk1a7c3e5b9d2f41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "link_thanh_toan_doan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(20), nullable=False, server_default=""),
        sa.Column("hop_dong_id", sa.Integer(), sa.ForeignKey("hop_dong_khach.id"), nullable=False),
        sa.Column("lich_id", sa.Integer(), sa.ForeignKey("lich_thanh_toan_hd.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("so_tien", sa.Numeric(18, 2), nullable=False),
        sa.Column("han", sa.Date(), nullable=False),
        sa.Column("trang_thai", sa.String(10), nullable=False, server_default="mo"),
        sa.Column("email", sa.String(120), nullable=False, server_default=""),
        sa.Column("dien_thoai", sa.String(30), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_huy", sa.String(300), nullable=False, server_default=""),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("tra_luc", sa.DateTime(), nullable=True),
        sa.Column("email_link_luc", sa.DateTime(), nullable=True),
        sa.Column("email_hd_luc", sa.DateTime(), nullable=True),
        sa.Column("email_loi", sa.String(300), nullable=False, server_default=""),
    )
    op.create_index("ix_link_thanh_toan_doan_ma", "link_thanh_toan_doan", ["ma"], unique=True)
    op.create_index("ix_link_thanh_toan_doan_hop_dong_id", "link_thanh_toan_doan", ["hop_dong_id"])
    op.create_index("ix_link_thanh_toan_doan_lich_id", "link_thanh_toan_doan", ["lich_id"])
    op.create_index("ix_link_thanh_toan_doan_booking_id", "link_thanh_toan_doan", ["booking_id"])
    op.create_index("ix_link_thanh_toan_doan_trang_thai", "link_thanh_toan_doan", ["trang_thai"])


def downgrade() -> None:
    op.drop_table("link_thanh_toan_doan")
