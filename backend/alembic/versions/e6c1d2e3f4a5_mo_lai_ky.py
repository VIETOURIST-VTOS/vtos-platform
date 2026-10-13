"""Đợt E6 13/10/2026 — bảng hồ sơ mở lại kỳ kế toán.

Revision ID: e6c1d2e3f4a5
Revises: e5b1c2d3e4f5
Create Date: 2026-10-13

Chỉ THÊM một bảng, không đụng dòng dữ liệu nào đang có. `period_locks` giữ nguyên.
"""
import sqlalchemy as sa
from alembic import op

revision = "e6c1d2e3f4a5"
down_revision = "e5b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mo_lai_ky",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.String(length=7), nullable=False, index=True),
        sa.Column("ly_do", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=16), nullable=False, server_default="cho_ky"),
        sa.Column("trinh_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("trinh_vai", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("trinh_luc", sa.DateTime(), nullable=True),
        sa.Column("ky_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ky_vai", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("ky_luc", sa.DateTime(), nullable=True),
        sa.Column("tu_choi_ly_do", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("khoa_cu_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("khoa_cu_luc", sa.DateTime(), nullable=True),
        sa.Column("khoa_cu_ghi_chu", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("khoa_lai_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("khoa_lai_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mo_lai_ky_tt_ky", "mo_lai_ky", ["trang_thai", "period"])


def downgrade() -> None:
    op.drop_index("ix_mo_lai_ky_tt_ky", table_name="mo_lai_ky")
    op.drop_table("mo_lai_ky")
