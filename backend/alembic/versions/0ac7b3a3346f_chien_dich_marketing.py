"""Marketing Đợt 1: bảng chiến dịch; lead và đề nghị chi trỏ về chiến dịch

Revision ID: 0ac7b3a3346f
Revises: 94f4b7de1960
"""
from alembic import op
import sqlalchemy as sa

revision = "0ac7b3a3346f"
down_revision = "c8d9e0f1a2b3"   # nối sau bản vá của phiên song song – mạch migration phải luôn có MỘT đầu
branch_labels = None
depends_on = None


def upgrade() -> None:
    ins = sa.inspect(op.get_bind())
    if "campaigns" not in ins.get_table_names():
        op.create_table(
            "campaigns",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("objective", sa.String(20), nullable=False),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=True),
            sa.Column("mang", sa.String(6), nullable=False, server_default="le"),
            sa.Column("channels", sa.JSON, nullable=True),
            sa.Column("from_date", sa.Date, nullable=False),
            sa.Column("to_date", sa.Date, nullable=True),
            sa.Column("budget", sa.Float, nullable=False, server_default="0"),
            sa.Column("target_leads", sa.Integer, nullable=False, server_default="0"),
            sa.Column("target_bookings", sa.Integer, nullable=False, server_default="0"),
            sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True),
            sa.Column("status", sa.String(12), nullable=False, server_default="nhap"),
            sa.Column("evaluation", sa.Text, nullable=False, server_default=""),
            sa.Column("note", sa.Text, nullable=False, server_default=""),
            sa.Column("nguon_tao", sa.String(6), nullable=False, server_default="nguoi"),
            sa.Column("ai_ghi_chu", sa.Text, nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("approved_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("approved_at", sa.DateTime, nullable=True),
        )
    for bang in ("leads", "payment_requests"):
        cols = {c["name"] for c in ins.get_columns(bang)}
        if "campaign_id" not in cols:
            op.add_column(bang, sa.Column("campaign_id", sa.Integer, nullable=True))
            op.create_index(f"ix_{bang}_campaign", bang, ["campaign_id"])


def downgrade() -> None:
    for bang in ("leads", "payment_requests"):
        op.drop_index(f"ix_{bang}_campaign", table_name=bang)
        op.drop_column(bang, "campaign_id")
    op.drop_table("campaigns")
