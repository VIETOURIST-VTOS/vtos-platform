"""CN-2 · Giữ lương phòng chưa duyệt công và bảng lương bổ sung.

Chủ tịch chốt 21/10/2026. Ba thay đổi:
  · payroll_runs.giu_lai — phòng bị giữ lúc ký bảng chính (JSON, mặc định rỗng = không giữ ai);
  · bang_luong_khoa.bo_sung_so — rỗng = bản khoá bảng chính, có số = bản khoá bảng bổ sung;
  · bảng mới bang_luong_bo_sung.

Revision ID: cn2g4l8b1s30
Revises: cn1x7a3c5k20
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "cn2g4l8b1s30"
down_revision = "cn1x7a3c5k20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payroll_runs") as b:
        b.add_column(sa.Column("giu_lai", sa.JSON(), nullable=True))
    with op.batch_alter_table("bang_luong_khoa") as b:
        b.add_column(sa.Column("bo_sung_so", sa.Integer(), nullable=True))
    op.create_table(
        "bang_luong_bo_sung",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("so", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("phong", sa.JSON(), nullable=True),
        sa.Column("rows", sa.JSON(), nullable=True),
        sa.Column("totals", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="nhap"),
        sa.Column("lap_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
        sa.Column("hcns_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("hcns_at", sa.DateTime(), nullable=True),
        sa.Column("ky_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("ky_vai", sa.String(20), nullable=False, server_default=""),
        sa.Column("ky_luc", sa.DateTime(), nullable=True),
        sa.Column("ban_khoa_id", sa.Integer(), nullable=True),
        sa.Column("entry_ids", sa.JSON(), nullable=True),
    )
    op.create_index("ix_bang_luong_bo_sung_period", "bang_luong_bo_sung", ["period"])
    op.create_index("ix_bang_luong_bo_sung_ky_so", "bang_luong_bo_sung", ["period", "so"], unique=True)


def downgrade():
    op.drop_index("ix_bang_luong_bo_sung_ky_so", table_name="bang_luong_bo_sung")
    op.drop_index("ix_bang_luong_bo_sung_period", table_name="bang_luong_bo_sung")
    op.drop_table("bang_luong_bo_sung")
    with op.batch_alter_table("bang_luong_khoa") as b:
        b.drop_column("bo_sung_so")
    with op.batch_alter_table("payroll_runs") as b:
        b.drop_column("giu_lai")
