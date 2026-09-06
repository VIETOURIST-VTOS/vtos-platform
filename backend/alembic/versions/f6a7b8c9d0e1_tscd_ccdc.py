"""Tài sản cố định & Công cụ dụng cụ – chi phí trả trước (phân hệ TSCĐ/CCDC theo MISA)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fixed_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="huu_hinh"),
        sa.Column("group", sa.String(60), nullable=False, server_default=""),
        sa.Column("asset_account", sa.String(10), nullable=False, server_default="211"),
        sa.Column("depr_account", sa.String(10), nullable=False, server_default="2141"),
        sa.Column("expense_account", sa.String(10), nullable=False, server_default="6424"),
        sa.Column("partner_code", sa.String(60), nullable=False, server_default=""),
        sa.Column("project_code", sa.String(40), nullable=False, server_default=""),
        sa.Column("department", sa.String(20), nullable=False, server_default=""),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("depr_months", sa.Integer, nullable=False, server_default="0"),
        sa.Column("salvage", sa.Float, nullable=False, server_default="0"),
        sa.Column("opening_accumulated", sa.Float, nullable=False, server_default="0"),
        sa.Column("opening_period", sa.String(7), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="dang_dung"),
        sa.Column("disposed_date", sa.Date, nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("source", sa.String(20), nullable=False, server_default="vtos"),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "asset_depreciations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("fixed_assets.id"), nullable=False, index=True),
        sa.Column("period", sa.String(7), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("accumulated", sa.Float, nullable=False, server_default="0"),
        sa.Column("remaining", sa.Float, nullable=False, server_default="0"),
        sa.Column("entry_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "prepaid_expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="ccdc"),
        sa.Column("asset_account", sa.String(10), nullable=False, server_default="242"),
        sa.Column("expense_account", sa.String(10), nullable=False, server_default="6423"),
        sa.Column("partner_code", sa.String(60), nullable=False, server_default=""),
        sa.Column("project_code", sa.String(40), nullable=False, server_default=""),
        sa.Column("department", sa.String(20), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("months", sa.Integer, nullable=False, server_default="1"),
        sa.Column("opening_allocated", sa.Float, nullable=False, server_default="0"),
        sa.Column("opening_period", sa.String(7), nullable=False, server_default=""),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="dang_pb"),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("source", sa.String(20), nullable=False, server_default="vtos"),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "prepaid_allocations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("prepaid_id", sa.Integer, sa.ForeignKey("prepaid_expenses.id"), nullable=False, index=True),
        sa.Column("period", sa.String(7), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("allocated", sa.Float, nullable=False, server_default="0"),
        sa.Column("remaining", sa.Float, nullable=False, server_default="0"),
        sa.Column("entry_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table("prepaid_allocations")
    op.drop_table("prepaid_expenses")
    op.drop_table("asset_depreciations")
    op.drop_table("fixed_assets")
