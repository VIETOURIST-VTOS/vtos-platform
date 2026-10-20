"""CN-1 · Bảng xác nhận công tháng theo phòng.

Chủ tịch chốt 21/10/2026: HCNS lập và xác nhận, TGĐ duyệt; phòng chưa duyệt công thì bảng lương
chặn. Một dòng cho mỗi (kỳ, phòng); hiệu lực tính lại khi đọc bằng dấu ảnh chụp số liệu.

Revision ID: cn1x7a3c5k20
Revises: em1u5e2c9v41
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "cn1x7a3c5k20"
down_revision = "em1u5e2c9v41"   # head của main d7aaebf, đo 21/10/2026
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "xac_nhan_cong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("phong", sa.String(20), nullable=False),
        sa.Column("so_lieu", sa.JSON(), nullable=True),
        sa.Column("van_tay", sa.String(64), nullable=False, server_default=""),
        sa.Column("hcns_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("hcns_at", sa.DateTime(), nullable=True),
        sa.Column("tgd_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("tgd_vai", sa.String(20), nullable=False, server_default=""),
        sa.Column("tgd_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("period", "phong", name="uq_xac_nhan_cong_ky_phong"),
    )
    op.create_index("ix_xac_nhan_cong_period", "xac_nhan_cong", ["period"])


def downgrade():
    op.drop_index("ix_xac_nhan_cong_period", table_name="xac_nhan_cong")
    op.drop_table("xac_nhan_cong")
