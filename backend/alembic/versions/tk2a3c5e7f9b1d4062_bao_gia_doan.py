"""TK-2 — báo giá chính thức tour đoàn khách tự thiết kế (giai đoạn 2).

Chủ tịch 04/11/2026: hạn báo giá 24 giờ; giá trẻ em 75% (tour xe) / 80% (có chặng bay); khách đồng ý → hợp đồng nháp.

Revision ID: tk2a3c5e7f9b1d4062
Revises: tk1e7b9d1f3a5c8e02
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op

revision = "tk2a3c5e7f9b1d4062"
down_revision = "tk1e7b9d1f3a5c8e02"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "bao_gia_doan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(24), nullable=False),
        sa.Column("thiet_ke_id", sa.Integer(), sa.ForeignKey("thiet_ke_doan.id"), nullable=False),
        sa.Column("thiet_ke_ma", sa.String(20), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("dong", sa.JSON(), nullable=False),
        sa.Column("bien_pt", TIEN, nullable=False, server_default="10"),
        sa.Column("he_so_te", TIEN, nullable=False, server_default="0.75"),
        sa.Column("so_nl", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_te", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_eb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tong_von", TIEN, nullable=True),
        sa.Column("tong_ban", TIEN, nullable=True),
        sa.Column("gia_nl", TIEN, nullable=True),
        sa.Column("gia_te", TIEN, nullable=True),
        sa.Column("bao_gom", sa.JSON(), nullable=False),
        sa.Column("khong_bao_gom", sa.JSON(), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(14), nullable=False, server_default="nhap"),
        sa.Column("cap_duyet", sa.String(10), nullable=False, server_default=""),
        sa.Column("ly_do_bien", sa.String(300), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("gui_duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_tra", sa.String(300), nullable=False, server_default=""),
        sa.Column("han_luc", sa.DateTime(), nullable=True),
        sa.Column("ma_bam", sa.String(64), nullable=False, server_default=""),
        sa.Column("khach_dong_y_luc", sa.DateTime(), nullable=True),
        sa.Column("hop_dong_id", sa.Integer(), sa.ForeignKey("hop_dong_khach.id"), nullable=True),
    )
    op.create_index("ix_bao_gia_doan_ma", "bao_gia_doan", ["ma"], unique=True)
    op.create_index("ix_bao_gia_doan_thiet_ke_id", "bao_gia_doan", ["thiet_ke_id"])
    op.create_index("ix_bao_gia_doan_thiet_ke_ma", "bao_gia_doan", ["thiet_ke_ma"])
    op.create_index("ix_bao_gia_doan_tai_khoan_id", "bao_gia_doan", ["tai_khoan_id"])
    op.create_index("ix_bao_gia_doan_trang_thai", "bao_gia_doan", ["trang_thai"])


def downgrade() -> None:
    op.drop_table("bao_gia_doan")
