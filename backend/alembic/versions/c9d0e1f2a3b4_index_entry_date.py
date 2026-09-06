"""Chỉ mục ngày hạch toán cho chứng từ – mọi sổ kế toán đều lọc theo khoảng ngày

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    # journal_entries.entry_date chưa có chỉ mục trong khi Sổ cái, Nhật ký chung, Bảng cân đối tài khoản,
    # sổ công nợ và bảng gợi ý ngân hàng đều lọc theo khoảng ngày ⇒ mỗi lần mở sổ là một lần quét toàn bảng.
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])


def downgrade():
    op.drop_index("ix_journal_entries_entry_date", table_name="journal_entries")
