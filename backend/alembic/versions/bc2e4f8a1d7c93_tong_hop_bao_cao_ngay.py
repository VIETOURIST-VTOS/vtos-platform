"""BC-2 — tổng hợp báo cáo ngày cho người xem xét: trục xem xét, sổ xem xét, việc phát sinh.

Revision ID: bc2e4f8a1d7c93
Revises: bc1a7d3e9f2c61
Create Date: 2026-10-26

Hai cột thêm vào `daily_reports` có mặc định rỗng. Báo cáo cũ đã chấm (`reviewed_by` có tên) vẫn
đọc ra là «đã xem» mà không cần điền cột mới — chỗ đọc suy từ `reviewed_by` khi cột trống.
"""
import sqlalchemy as sa
from alembic import op

revision = "bc2e4f8a1d7c93"
down_revision = "bc1a7d3e9f2c61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("daily_reports") as b:
        b.add_column(sa.Column("xem_trang_thai", sa.String(length=20), nullable=False, server_default=""))
        b.add_column(sa.Column("bo_sung_ly_do", sa.String(length=300), nullable=False, server_default=""))
    op.create_table(
        "daily_report_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id"), nullable=False, index=True),
        sa.Column("hanh_dong", sa.String(length=20), nullable=False),
        sa.Column("ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("diem", sa.Float(), nullable=True),
        sa.Column("lan_nop", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "daily_report_follow_ups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id"), nullable=False, index=True),
        sa.Column("loai", sa.String(length=20), nullable=False),
        sa.Column("tu_phong", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("den_phong", sa.String(length=20), nullable=False, server_default="", index=True),
        sa.Column("nguoi_nhan_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("han", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="mo"),
        sa.Column("ghi_chu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("cap_nhat_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("cap_nhat_luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("daily_report_follow_ups")
    op.drop_table("daily_report_reviews")
    with op.batch_alter_table("daily_reports") as b:
        b.drop_column("bo_sung_ly_do")
        b.drop_column("xem_trang_thai")
