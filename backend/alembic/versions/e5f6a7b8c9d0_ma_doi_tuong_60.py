"""Mã đối tượng dài tới 60 ký tự (mã NCC MISA có mã dài 47)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("partners") as b:
        b.alter_column("code", type_=sa.String(60), existing_type=sa.String(40))
    with op.batch_alter_table("journal_lines") as b:
        b.alter_column("partner_code", type_=sa.String(60), existing_type=sa.String(40))


def downgrade():
    with op.batch_alter_table("journal_lines") as b:
        b.alter_column("partner_code", type_=sa.String(40), existing_type=sa.String(60))
    with op.batch_alter_table("partners") as b:
        b.alter_column("code", type_=sa.String(40), existing_type=sa.String(60))
