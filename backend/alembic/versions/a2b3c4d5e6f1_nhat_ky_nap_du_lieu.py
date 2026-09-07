"""Nhật ký nạp dữ liệu

Nạp hàng loạt là lúc dữ liệu vào hệ thống nhanh nhất và ít người nhìn nhất. Bảng này để trả lời
được câu "con số này ở đâu ra" vào đúng lúc khó nhất, kèm mã băm nội dung đã nạp để phân biệt
tệp đã nạp hôm đó với tệp đã sửa sau này.

Revision ID: a2b3c4d5e6f1
Revises: f1e2d3c4b5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f1"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "intake_runs" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "intake_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("loai", sa.String(40), nullable=False),
        sa.Column("ten_tep", sa.String(200), server_default=""),
        sa.Column("nguon", sa.String(40), server_default="nguoi_nhap"),
        sa.Column("tac_nhan", sa.String(80), server_default=""),
        sa.Column("so_dong", sa.Integer, server_default="0"),
        sa.Column("da_nap", sa.Integer, server_default="0"),
        sa.Column("bo_qua_da_co", sa.Integer, server_default="0"),
        sa.Column("dong_loi", sa.Integer, server_default="0"),
        sa.Column("bo_qua_dong_loi", sa.Boolean, server_default=sa.false()),
        sa.Column("dau_vao_hash", sa.String(64), server_default=""),
        sa.Column("ket_qua", sa.Text, server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_intake_runs_loai", "intake_runs", ["loai"])


def downgrade() -> None:
    op.drop_table("intake_runs")
