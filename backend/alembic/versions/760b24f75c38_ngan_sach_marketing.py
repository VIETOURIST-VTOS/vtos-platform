"""Marketing Đợt 2: ngân sách kỳ theo hạng mục; đề nghị chi marketing ghi hạng mục

Revision ID: 760b24f75c38
Revises: 0ac7b3a3346f
"""
from alembic import op
import sqlalchemy as sa

revision = "760b24f75c38"
down_revision = "0ac7b3a3346f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ins = sa.inspect(op.get_bind())
    if "mkt_budgets" not in ins.get_table_names():
        op.create_table(
            "mkt_budgets",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("period", sa.String(8), nullable=False, index=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True),
            sa.Column("target_leads", sa.Integer, nullable=False, server_default="0"),
            sa.Column("target_revenue", sa.Float, nullable=False, server_default="0"),
            sa.Column("rationale", sa.Text, nullable=False, server_default=""),
            sa.Column("status", sa.String(10), nullable=False, server_default="nhap"),
            sa.Column("nguon_tao", sa.String(6), nullable=False, server_default="nguoi"),
            sa.Column("ai_ghi_chu", sa.Text, nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("approved_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("approved_at", sa.DateTime, nullable=True),
        )
    if "mkt_budget_lines" not in ins.get_table_names():
        op.create_table(
            "mkt_budget_lines",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("budget_id", sa.Integer, sa.ForeignKey("mkt_budgets.id"), nullable=False, index=True),
            sa.Column("hang_muc", sa.String(20), nullable=False),
            sa.Column("amount", sa.Float, nullable=False, server_default="0"),
            sa.Column("note", sa.String(300), nullable=False, server_default=""),
        )
    cols = {c["name"] for c in ins.get_columns("payment_requests")}
    if "marketing_muc" not in cols:
        op.add_column("payment_requests", sa.Column("marketing_muc", sa.String(20), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("payment_requests", "marketing_muc")
    op.drop_table("mkt_budget_lines")
    op.drop_table("mkt_budgets")
