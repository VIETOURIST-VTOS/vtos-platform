"""ĐỢT R3b 17/10/2026 — bảng danh mục bộ phận.

Chỉ TẠO BẢNG. Không một câu nào chạm vào `journal_lines`: chữ cũ đã nằm trong sổ được nhận về làm
BÚT DANH của bộ phận chứ không viết đè, vì "cntt → BP_CNTT" là quyết định của người HÔM NAY áp lên
những dòng ĐÃ GHI, mà kỳ đã khoá thì không ai được sửa.

Cha đọc từ chính cây lúc dựng bản vá (q2a3d5f7b9c1e), không ghim cứng — bài học 15/10/2026.

Revision ID: r3b7c1e4a9d52
Revises: q2a3d5f7b9c1e
"""
from alembic import op
import sqlalchemy as sa

revision = "r3b7c1e4a9d52"
down_revision = "dg3c8f2a6e4b17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bo_phan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("thu_tu", sa.Integer(), server_default="100"),
        sa.Column("dung", sa.Boolean(), server_default=sa.true()),
        sa.Column("but_danh", sa.Text(), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_bo_phan_ma", "bo_phan", ["ma"], unique=True)
    op.create_index("ix_bo_phan_dung", "bo_phan", ["dung"])


def downgrade() -> None:
    op.drop_index("ix_bo_phan_dung", table_name="bo_phan")
    op.drop_index("ix_bo_phan_ma", table_name="bo_phan")
    op.drop_table("bo_phan")
