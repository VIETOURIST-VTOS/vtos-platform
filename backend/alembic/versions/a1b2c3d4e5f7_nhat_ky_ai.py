"""Nhật ký AI thống nhất (chỉ đạo 07/9/2026)

Ba chỗ dùng mô hình ngôn ngữ – trả lời khách trong hộp thư, chấm câu trả lời của tư vấn viên, viết
nhận xét báo cáo cho lãnh đạo – trước bản này không để lại vết nào, trong đó chỗ thứ nhất gửi tin cho
khách hàng thật.

Revision ID: a1b2c3d4e5f7
Revises: 94f4b7de1960
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "94f4b7de1960"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.DateTime, nullable=True),
        sa.Column("tac_vu", sa.String(20), nullable=False, server_default=""),
        sa.Column("muc", sa.Integer, nullable=False, server_default="1"),
        sa.Column("ref", sa.String(60), nullable=False, server_default=""),
        sa.Column("phuc_vu_vai_tro", sa.String(30), nullable=False, server_default=""),
        sa.Column("phuc_vu_nguoi", sa.String(50), nullable=False, server_default=""),
        sa.Column("mo_hinh", sa.String(60), nullable=False, server_default=""),
        sa.Column("nguon", sa.String(12), nullable=False, server_default=""),
        sa.Column("dau_vao_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("so_ban_ghi", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ket_qua", sa.Text, nullable=False, server_default=""),
        sa.Column("tokens_vao", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_ra", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default="khong_can"),
        sa.Column("hau_kiem_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("hau_kiem_luc", sa.DateTime, nullable=True),
        sa.Column("hau_kiem_ghi_chu", sa.String(300), nullable=False, server_default=""),
        sa.Column("loi", sa.String(300), nullable=False, server_default=""),
    )
    op.create_index("ix_ai_runs_ts", "ai_runs", ["ts"])
    op.create_index("ix_ai_runs_tac_vu", "ai_runs", ["tac_vu"])
    op.create_index("ix_ai_runs_trang_thai", "ai_runs", ["trang_thai"])


def downgrade():
    op.drop_table("ai_runs")
