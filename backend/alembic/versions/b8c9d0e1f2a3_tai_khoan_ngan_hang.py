"""Danh mục tài khoản ngân hàng (tiểu khoản 112 theo từng ngân hàng)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_accounts_cat",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("bank_name", sa.String(120), nullable=False),
        sa.Column("account_number", sa.String(40), nullable=False, server_default=""),
        sa.Column("account_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("branch", sa.String(120), nullable=False, server_default=""),
        sa.Column("currency", sa.String(5), nullable=False, server_default="VND"),
        sa.Column("account_code", sa.String(10), nullable=False, server_default="", index=True),
        sa.Column("parent_account", sa.String(10), nullable=False, server_default="1121"),
        sa.Column("match_prefixes", sa.JSON, nullable=True),
        sa.Column("match_keywords", sa.JSON, nullable=True),
        sa.Column("sepay_account_number", sa.String(40), nullable=False, server_default=""),
        sa.Column("opening_balance", sa.Float, nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table("bank_accounts_cat")
