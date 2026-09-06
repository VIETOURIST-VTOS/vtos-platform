"""Danh mục pháp nhân; gắn công ty chủ quản cho xe và hướng dẫn viên

Ý kiến thẩm định 06/9/2026 mục C1: đội xe thuộc Công ty TNHH Vận tải Vietrip – pháp nhân riêng trong
phạm vi hợp nhất – nên xe và HDV phải ghi rõ công ty chủ quản để nhận diện giao dịch nội bộ.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tax_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("kind", sa.String(12), nullable=False, server_default="con"),
        sa.Column("ownership_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
    )
    op.add_column("vehicles", sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True))
    op.add_column("employees", sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True))


def downgrade():
    op.drop_column("employees", "company_id")
    op.drop_column("vehicles", "company_id")
    op.drop_table("companies")
