"""Quyền AI theo vị trí và nút tắt khẩn AI đối ngoại

Trước bản này, việc AI có tự gửi tin cho khách hay không phụ thuộc MỘT tham số nằm lẫn trong bảng
chính sách, không hạn mức, không ai hậu kiểm. Nay là bảng theo vị trí × nhóm việc, và robot hộp thư
đọc thẳng bảng đó trước mỗi lần định gửi.

Revision ID: c2d3e4f5a6b7
Revises: a2b3c4d5e6f1
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "a2b3c4d5e6f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vai_tro", sa.String(30), nullable=False, server_default=""),
        sa.Column("tac_vu", sa.String(20), nullable=False, server_default=""),
        sa.Column("muc", sa.Integer, nullable=False, server_default="0"),
        sa.Column("han_muc", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("updated_by", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index("ix_ai_positions_vai_tro", "ai_positions", ["vai_tro"])
    op.create_index("ix_ai_positions_tac_vu", "ai_positions", ["tac_vu"])
    op.create_table(
        "ai_pause",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tam_dung", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("ly_do", sa.String(300), nullable=False, server_default=""),
        sa.Column("boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table("ai_pause")
    op.drop_table("ai_positions")
