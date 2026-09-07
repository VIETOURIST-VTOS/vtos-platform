"""Bảng ghi việc xử lý ngoại lệ (màn hình "Ngoại lệ cần xử lý").

Chỉ một bảng: bản thân ngoại lệ được đọc ra từ nơi nó xảy ra, không chép sang bảng riêng.

Revision ID: e4f5a6b7c8d9
Revises: e0f1a2b3c4d5
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ngoai_le_xu_ly",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ma", sa.String(120), nullable=False),
        sa.Column("trang_thai", sa.String(8), nullable=False, server_default="chua"),
        sa.Column("nguoi_nhan", sa.String(50), nullable=False, server_default=""),
        sa.Column("nhan_luc", sa.DateTime, nullable=True),
        sa.Column("nguoi_chiu_trach_nhiem", sa.String(80), nullable=False, server_default=""),
        sa.Column("giai_trinh", sa.Text, nullable=False, server_default=""),
        sa.Column("da_lam", sa.Text, nullable=False, server_default=""),
        sa.Column("dong_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("dong_luc", sa.DateTime, nullable=True),
        sa.Column("cap_nhat_luc", sa.DateTime, nullable=True),
        sa.Column("so_lan_ghi", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_ngoai_le_xu_ly_ma", "ngoai_le_xu_ly", ["ma"], unique=True)
    op.create_index("ix_ngoai_le_xu_ly_trang_thai", "ngoai_le_xu_ly", ["trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_ngoai_le_xu_ly_trang_thai", table_name="ngoai_le_xu_ly")
    op.drop_index("ix_ngoai_le_xu_ly_ma", table_name="ngoai_le_xu_ly")
    op.drop_table("ngoai_le_xu_ly")
