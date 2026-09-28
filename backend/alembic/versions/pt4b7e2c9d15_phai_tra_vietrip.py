"""Phải trả NCC theo dự toán tour trên Vietrip – ảnh chụp mỗi ngày

Revision ID: pt4b7e2c9d15
Revises: cv3a8d1e6f42
Create Date: 2026-09-29

HAI bảng mới, KHÔNG sửa bảng nào đang có – lùi lại sạch.
"""
import sqlalchemy as sa
from alembic import op

revision = "pt4b7e2c9d15"
down_revision = "cv3a8d1e6f42"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade():
    op.create_table(
        "phai_tra_vietrip_anh",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("so_tour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tong_con_phai_chi", TIEN, nullable=True),
        sa.Column("so_lan_nap", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("nguoi_nap", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_phai_tra_vietrip_anh_ngay", "phai_tra_vietrip_anh", ["ngay"], unique=True)
    op.create_table(
        "phai_tra_vietrip_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anh_id", sa.Integer(), sa.ForeignKey("phai_tra_vietrip_anh.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tour_id", sa.Integer(), nullable=False),
        sa.Column("ma_tour", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("ten_tour", sa.Text(), nullable=False, server_default=""),
        sa.Column("khoi_hanh", sa.Date(), nullable=True),
        sa.Column("ket_thuc", sa.Date(), nullable=True),
        sa.Column("tong_chi", TIEN, nullable=True),
        sa.Column("da_chi", TIEN, nullable=True),
        sa.Column("con_phai_chi", TIEN, nullable=True),
    )
    op.create_index("ix_phai_tra_vietrip_dong_anh", "phai_tra_vietrip_dong", ["anh_id"])


def downgrade():
    op.drop_index("ix_phai_tra_vietrip_dong_anh", table_name="phai_tra_vietrip_dong")
    op.drop_table("phai_tra_vietrip_dong")
    op.drop_index("ux_phai_tra_vietrip_anh_ngay", table_name="phai_tra_vietrip_anh")
    op.drop_table("phai_tra_vietrip_anh")
