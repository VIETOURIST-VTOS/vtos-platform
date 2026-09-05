"""sửa cột id của vt_records / tour_cost_lines (mất tự tăng do server_default='0' trên PostgreSQL)

Revision ID: 8a1c2f3d4e5f
Revises: 737b5310dd22
"""
from alembic import op

revision = '8a1c2f3d4e5f'
down_revision = '737b5310dd22'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for t in ("vt_records", "tour_cost_lines"):
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {t}_id_seq OWNED BY {t}.id")
        op.execute(f"SELECT setval('{t}_id_seq', COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false)")
        op.execute(f"ALTER TABLE {t} ALTER COLUMN id SET DEFAULT nextval('{t}_id_seq')")


def downgrade():
    pass
