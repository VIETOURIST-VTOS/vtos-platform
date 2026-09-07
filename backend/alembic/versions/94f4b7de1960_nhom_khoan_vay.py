"""fin_contracts: nhóm khoản vay

Sao kê ngân hàng gộp chung vay mua xe, vay bất động sản và vay vốn lưu động. Màn hình theo dõi
vay xe chỉ được lấy đúng nhóm của mình.

Revision ID: 94f4b7de1960
Revises: 0fa7043cb785
"""
from alembic import op
import sqlalchemy as sa

revision = "94f4b7de1960"
down_revision = "0fa7043cb785"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("fin_contracts")}
    if "loan_group" not in cols:
        op.add_column("fin_contracts", sa.Column("loan_group", sa.String(24), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("fin_contracts", "loan_group")
