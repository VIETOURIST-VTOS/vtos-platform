"""DT-1 — cổng đối tác: nối tài khoản ngoài với đối tác bán hàng; tên khách CTV giới thiệu.

Revision ID: dt1a3c5e7b9d24
Revises: kh4e7a1c3d5f28
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "dt1a3c5e7b9d24"
down_revision = "kh4e7a1c3d5f28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tai_khoan_ngoai", sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=True))
    op.create_index("ix_tai_khoan_ngoai_doi_tac_id", "tai_khoan_ngoai", ["doi_tac_id"])
    op.add_column("yeu_cau_khach", sa.Column("ten_khach", sa.String(length=120), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("yeu_cau_khach", "ten_khach")
    op.drop_index("ix_tai_khoan_ngoai_doi_tac_id", table_name="tai_khoan_ngoai")
    op.drop_column("tai_khoan_ngoai", "doi_tac_id")
