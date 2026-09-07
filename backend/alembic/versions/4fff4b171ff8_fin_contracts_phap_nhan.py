"""fin_contracts: pháp nhân vay (company_id)

Khế ước vay đã có cột `entity` dạng chữ, giữ nguyên văn hồ sơ ngân hàng. Cột này trỏ về
danh mục pháp nhân để dư nợ và lãi vay cộng đúng theo từng công ty khi lập báo cáo hợp nhất.

Revision ID: 4fff4b171ff8
Revises: eb8aee29bc5d
"""
from alembic import op
import sqlalchemy as sa

revision = "4fff4b171ff8"
down_revision = "eb8aee29bc5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("fin_contracts")}
    if "company_id" not in cols:
        op.add_column("fin_contracts", sa.Column("company_id", sa.Integer(), nullable=True))
        op.create_index("ix_fin_contracts_company", "fin_contracts", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_fin_contracts_company", table_name="fin_contracts")
    op.drop_column("fin_contracts", "company_id")
