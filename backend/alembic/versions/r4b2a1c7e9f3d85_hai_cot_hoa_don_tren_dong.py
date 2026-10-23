"""Đợt R4b-2a — hai cột hóa đơn trên dòng bút toán, và bốn cột vết ghi.

Revision ID: r4b2a1c7e9f3d85
Revises: cn1x7a3c5k20
Create Date: 2026-10-22

KHÔNG đụng cột số chứng từ gốc đã có. Cột ấy mang SỐ CHỨNG TỪ (đo 22/10/2026: chỗ duy nhất
ghi vào nó là `services/hach_toan.py`, và nó ghi `so_chung_tu`), nên dùng lại nó làm số hóa
đơn là để bộ quy tắc đè mất số hóa đơn mỗi lần tự ghi sổ — sổ vẫn cân và không phép thử nào đỏ.

Mọi cột đều CHO RỖNG và không có giá trị mặc định ở tầng máy chủ: sổ cũ không bị viết lại,
và một dòng cũ đọc ra đúng cái nó vốn là — "chưa nhận được hóa đơn".
"""
import sqlalchemy as sa
from alembic import op

revision = "r4b2a1c7e9f3d85"
down_revision = "cn1x7a3c5k20"
branch_labels = None
depends_on = None

COT = (
    ("ngay_hoa_don", sa.Date(), True),
    ("so_hoa_don", sa.String(length=40), True),
    ("hoa_don_trang_thai", sa.String(length=20), True),
    ("hoa_don_ly_do", sa.String(length=200), True),
    ("hoa_don_nguoi_ghi", sa.String(length=50), True),
    ("hoa_don_ghi_luc", sa.DateTime(), True),
)


def upgrade() -> None:
    for ten, kieu, rong in COT:
        op.add_column("journal_lines", sa.Column(ten, kieu, nullable=rong))
    op.create_index("ix_journal_lines_hoa_don_trang_thai", "journal_lines", ["hoa_don_trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_journal_lines_hoa_don_trang_thai", table_name="journal_lines")
    for ten, _, _ in reversed(COT):
        op.drop_column("journal_lines", ten)
