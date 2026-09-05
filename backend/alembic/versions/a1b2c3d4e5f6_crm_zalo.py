"""CRM lead + thống kê kênh + tin Zalo

Revision ID: a1b2c3d4e5f6
Revises: 9b3c4d5e6f70
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '9b3c4d5e6f70'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(20), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False, server_default=""),
        sa.Column("channel", sa.String(40), nullable=False, index=True),
        sa.Column("lead_month", sa.String(7), nullable=False, index=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("campaign", sa.String(80), nullable=False, server_default=""),
        sa.Column("interest", sa.String(200), nullable=False, server_default=""),
        sa.Column("sales_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="moi"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("zalo_uid", sa.String(40), nullable=False, server_default=""),
        sa.Column("zalo_follow", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_contact_at", sa.DateTime(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("phone", "lead_month", "channel", name="uq_lead_phone_month_channel"))
    op.create_table("lead_channel_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lead_month", sa.String(7), nullable=False, index=True),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("lead_month", "channel", name="uq_lead_stat_month_channel"))
    op.create_table("zalo_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(10), nullable=False, server_default="oa"),
        sa.Column("phone", sa.String(20), nullable=False, server_default="", index=True),
        sa.Column("zalo_uid", sa.String(40), nullable=False, server_default=""),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("purpose", sa.String(30), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="cho_gui"),
        sa.Column("response", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_table("zalo_messages"); op.drop_table("lead_channel_stats"); op.drop_table("leads")
