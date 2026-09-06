"""Bản đồ chứng từ → tài khoản ngân hàng (nạp từ Sổ tiền gửi MISA)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_doc_map",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bank_code", sa.String(20), nullable=False, index=True),
        sa.Column("doc_no", sa.String(60), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("side", sa.String(4), nullable=False, server_default="thu"),
        sa.Column("source_file", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table("bank_doc_map")
