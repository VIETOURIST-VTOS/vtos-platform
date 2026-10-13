"""Đợt E14 13/10/2026 — hai mốc thời gian của bút toán điều chỉnh.

Revision ID: e14a2b3c4d5e
Revises: e7d1e2f3a4b5
Create Date: 2026-10-14

Hai cột, cả hai NULLABLE, và nullable là CÓ CHỦ Ý chứ không phải cho dễ:

  · `ky_goc`         — kỳ GỐC mà bút toán này đi sửa
  · `ngay_phat_hien` — ngày NGƯỜI nhận ra sai sót

Hai mốc này chỉ có nghĩa với bút toán ĐIỀU CHỈNH. Mọi bút toán khác để RỖNG, và rỗng ở đây đọc
đúng là "không phải bút toán điều chỉnh" — khác hẳn 0 hay một ngày mặc định. Nạp sẵn một giá trị
cho các bút toán cũ là bịa ra một câu chuyện chưa từng xảy ra, nên bản di trú này KHÔNG nạp gì.

Chỉ mục trên `ky_goc`: thuyết minh BCTC hỏi "kỳ 09 bị sửa bởi những bút toán nào", và câu ấy hỏi
mỗi lần lập báo cáo.
"""
import sqlalchemy as sa
from alembic import op

revision = "e14a2b3c4d5e"
down_revision = "e7d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("ky_goc", sa.String(length=7), nullable=True))
    op.add_column("journal_entries", sa.Column("ngay_phat_hien", sa.Date(), nullable=True))
    op.create_index("ix_journal_entries_ky_goc", "journal_entries", ["ky_goc"])


def downgrade() -> None:
    op.drop_index("ix_journal_entries_ky_goc", table_name="journal_entries")
    op.drop_column("journal_entries", "ngay_phat_hien")
    op.drop_column("journal_entries", "ky_goc")
