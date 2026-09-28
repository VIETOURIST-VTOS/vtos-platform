"""Công nợ khách theo Vietrip – ảnh chụp mỗi ngày, 4 nhóm

Revision ID: cv3a8d1e6f42
Revises: nt1c4f7b2e8a
Create Date: 2026-09-28

HAI bảng mới, KHÔNG sửa bảng nào đang có – lùi lại sạch. Cột boolean dùng sa.false() (PostgreSQL
từ chối DEFAULT 0 cho BOOLEAN – sự cố 14/9/2026).
"""
import sqlalchemy as sa
from alembic import op

revision = "cv3a8d1e6f42"
down_revision = "nt1c4f7b2e8a"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade():
    op.create_table(
        "cong_no_vietrip_anh",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("so_booking", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tong_con_thieu", TIEN, nullable=True),
        sa.Column("so_lan_nap", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tep_key", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("tep_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tep_ben_vung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("nguoi_nap", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_cong_no_vietrip_anh_ngay", "cong_no_vietrip_anh", ["ngay"], unique=True)
    op.create_table(
        "cong_no_vietrip_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anh_id", sa.Integer(), sa.ForeignKey("cong_no_vietrip_anh.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("booking_id", sa.String(length=30), nullable=False),
        sa.Column("ma_tour", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("ten_tour", sa.Text(), nullable=False, server_default=""),
        sa.Column("khach", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("sdt_khach", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("sales", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("sdt_sales", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("tong", TIEN, nullable=True),
        sa.Column("da_thu", TIEN, nullable=True),
        sa.Column("con_thieu", TIEN, nullable=True),
        sa.Column("khoi_hanh", sa.Date(), nullable=True),
        sa.Column("nhom", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bao_luu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_cong_no_vietrip_dong_anh", "cong_no_vietrip_dong", ["anh_id", "nhom"])


def downgrade():
    op.drop_index("ix_cong_no_vietrip_dong_anh", table_name="cong_no_vietrip_dong")
    op.drop_table("cong_no_vietrip_dong")
    op.drop_index("ux_cong_no_vietrip_anh_ngay", table_name="cong_no_vietrip_anh")
    op.drop_table("cong_no_vietrip_anh")
