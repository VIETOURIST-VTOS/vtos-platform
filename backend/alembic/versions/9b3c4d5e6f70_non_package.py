"""dịch vụ lẻ non-package: trường dịch vụ trên booking; tour KLE → loại non_package

Revision ID: 9b3c4d5e6f70
Revises: 8a2b3c4d5e6f
"""
from alembic import op
import sqlalchemy as sa

revision = '9b3c4d5e6f70'
down_revision = '8a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bookings") as b:
        b.add_column(sa.Column("service_type", sa.String(20), nullable=False, server_default=""))
        b.add_column(sa.Column("country", sa.String(60), nullable=False, server_default=""))
        b.add_column(sa.Column("customer_email", sa.String(120), nullable=False, server_default=""))
        b.add_column(sa.Column("service_date", sa.Date(), nullable=True))
        b.add_column(sa.Column("cost_amount", sa.Float(), nullable=False, server_default="0"))
        b.add_column(sa.Column("supplier_name", sa.String(160), nullable=False, server_default=""))
    op.execute("UPDATE tours SET tour_type='non_package' WHERE code LIKE 'KLE%'")


def downgrade():
    op.execute("UPDATE tours SET tour_type='le_noi_dia' WHERE tour_type='non_package'")
    with op.batch_alter_table("bookings") as b:
        for c in ("service_type", "country", "customer_email", "service_date", "cost_amount", "supplier_name"): b.drop_column(c)
