"""Kế toán theo cấu trúc MISA: TK phân cấp + ánh xạ TT99, 4 chiều đối tượng trên dòng bút toán, danh mục đối tượng & công trình

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("accounts") as b:
        b.add_column(sa.Column("level", sa.Integer(), server_default="1", nullable=False))
        b.add_column(sa.Column("is_detail", sa.Boolean(), server_default=sa.true(), nullable=False))
        b.add_column(sa.Column("bs_debit", sa.String(6), server_default="", nullable=False))
        b.add_column(sa.Column("bs_credit", sa.String(6), server_default="", nullable=False))
        b.add_column(sa.Column("pl_code", sa.String(6), server_default="", nullable=False))
        b.add_column(sa.Column("misa", sa.Boolean(), server_default=sa.false(), nullable=False))
    with op.batch_alter_table("journal_lines") as b:
        b.add_column(sa.Column("partner_code", sa.String(40), server_default="", nullable=False))
        b.add_column(sa.Column("project_code", sa.String(40), server_default="", nullable=False))
        b.add_column(sa.Column("item_code", sa.String(40), server_default="", nullable=False))
        b.add_column(sa.Column("doc_no", sa.String(40), server_default="", nullable=False))
    op.create_index("ix_journal_lines_partner_code", "journal_lines", ["partner_code"])
    op.create_index("ix_journal_lines_project_code", "journal_lines", ["project_code"])
    op.create_table("partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("kind", sa.String(10), server_default="kh", nullable=False),
        sa.Column("is_customer", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_supplier", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("tax_code", sa.String(20), server_default="", nullable=False),
        sa.Column("address", sa.String(300), server_default="", nullable=False),
        sa.Column("phone", sa.String(40), server_default="", nullable=False),
        sa.Column("trade_name", sa.String(200), server_default="", nullable=False),
        sa.Column("internal", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source", sa.String(20), server_default="misa", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True))
    op.create_index("ix_partners_code", "partners", ["code"], unique=True)
    op.create_table("projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="dang_thuc_hien", nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("technical", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("source", sa.String(20), server_default="misa", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True))
    op.create_index("ix_projects_code", "projects", ["code"], unique=True)
    op.create_index("ix_projects_tour_id", "projects", ["tour_id"])


def downgrade():
    op.drop_table("projects"); op.drop_table("partners")
    op.drop_index("ix_journal_lines_project_code", "journal_lines"); op.drop_index("ix_journal_lines_partner_code", "journal_lines")
    with op.batch_alter_table("journal_lines") as b:
        for c in ("doc_no", "item_code", "project_code", "partner_code"): b.drop_column(c)
    with op.batch_alter_table("accounts") as b:
        for c in ("misa", "pl_code", "bs_credit", "bs_debit", "is_detail", "level"): b.drop_column(c)
