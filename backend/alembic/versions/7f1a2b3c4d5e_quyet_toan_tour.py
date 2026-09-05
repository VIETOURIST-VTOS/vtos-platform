"""quyết toán tour soạn trên VTOS: dòng chi phí có dự toán/trạng thái/phiên bản/chứng từ; tour có phiên bản quyết toán; tạm ứng

Revision ID: 7f1a2b3c4d5e
Revises: 6d29554fe3aa
"""
from alembic import op
import sqlalchemy as sa

revision = '7f1a2b3c4d5e'
down_revision = '6d29554fe3aa'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tour_cost_lines") as b:
        b.add_column(sa.Column("budget", sa.Float(), nullable=False, server_default="0"))
        b.add_column(sa.Column("status", sa.String(10), nullable=False, server_default="hd"))
        b.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("doc_name", sa.String(160), nullable=False, server_default=""))
        b.add_column(sa.Column("doc_data", sa.Text(), nullable=False, server_default=""))
        b.add_column(sa.Column("updated_by", sa.String(50), nullable=False, server_default=""))
    with op.batch_alter_table("tours") as b:
        b.add_column(sa.Column("settlement_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    with op.batch_alter_table("tours") as b:
        b.drop_column("settlement_version")
    with op.batch_alter_table("tour_cost_lines") as b:
        for c in ("budget", "status", "version", "doc_name", "doc_data", "updated_by"): b.drop_column(c)
