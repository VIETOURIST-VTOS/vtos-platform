"""tiền bảo lưu, khóa booking, % cọc, hủy booking có phí

Revision ID: 8a2b3c4d5e6f
Revises: 7f1a2b3c4d5e
"""
from alembic import op
import sqlalchemy as sa

revision = '8a2b3c4d5e6f'
down_revision = '7f1a2b3c4d5e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bookings") as b:
        b.add_column(sa.Column("deposit_pct", sa.Float(), nullable=False, server_default="30"))
        b.add_column(sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("lock_reason", sa.String(120), nullable=False, server_default=""))
        b.add_column(sa.Column("cancel_reason", sa.String(200), nullable=False, server_default=""))
        b.add_column(sa.Column("cancelled_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("cancel_charge", sa.Float(), nullable=False, server_default="0"))
    op.create_table("retentions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False, index=True),
        sa.Column("tour_code", sa.String(30), nullable=False, server_default=""),
        sa.Column("customer_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("customer_phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("remaining", sa.Float(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="hieu_luc"),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("refund_request_id", sa.Integer(), nullable=True),
        sa.Column("applied_booking_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolve_note", sa.String(300), nullable=False, server_default=""),
    )


def downgrade():
    op.drop_table("retentions")
    with op.batch_alter_table("bookings") as b:
        for c in ("deposit_pct", "locked", "lock_reason", "cancel_reason", "cancelled_at", "cancel_charge"): b.drop_column(c)
