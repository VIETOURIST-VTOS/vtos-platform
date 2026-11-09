"""Đội xe v3.3 · đề xuất chi của Giám đốc đội xe đi vào Đề nghị chi 05-TT

Revision ID: dx5c2a8e4f1b7d93
Revises: p103a7c2e9d4b6f1
Create Date: 2026-11-10

Chủ tịch chốt 10/11/2026: không dựng luồng duyệt riêng cho đội xe (tài liệu v3.3 mục 3 — «không tạo
thêm một luồng duyệt song song»). Phiếu đội xe là một đề nghị chi loại `chi_doi_xe`; MỘT cột JSON
giữ phần riêng của đội xe (phạm vi, xe, loại, nhóm khoản, tài khoản, căn cứ, khoản gốc, hẹn chứng từ).
Không đụng cột nào đang có.
"""
import sqlalchemy as sa
from alembic import op

revision = "dx5c2a8e4f1b7d93"
down_revision = "p103a7c2e9d4b6f1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_requests", sa.Column("doi_xe", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("payment_requests", "doi_xe")
