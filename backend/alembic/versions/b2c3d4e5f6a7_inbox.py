"""hộp thư đa kênh: conversations, messages

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel", sa.String(20), nullable=False, index=True),
        sa.Column("external_id", sa.String(80), nullable=False),
        sa.Column("page_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("customer_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("phone", sa.String(20), nullable=False, server_default="", index=True),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("sales_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="mo"),
        sa.Column("last_in_at", sa.DateTime(), nullable=True), sa.Column("last_out_at", sa.DateTime(), nullable=True), sa.Column("sla_due_at", sa.DateTime(), nullable=True),
        sa.Column("unanswered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_replies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_off", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True), sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("channel", "external_id", name="uq_conv_channel_ext"))
    op.create_table("messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False, index=True),
        sa.Column("direction", sa.String(3), nullable=False),
        sa.Column("sender", sa.String(20), nullable=False, server_default="khach"),
        sa.Column("sender_name", sa.String(80), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("external_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="da_nhan"),
        sa.Column("response", sa.Text(), nullable=False, server_default=""),
        sa.Column("ai_review", sa.JSON(), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=True, index=True))


def downgrade():
    op.drop_table("messages"); op.drop_table("conversations")
