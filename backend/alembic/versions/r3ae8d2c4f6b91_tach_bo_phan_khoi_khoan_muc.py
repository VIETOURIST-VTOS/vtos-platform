"""Dot R3a: tach bo phan ra khoi item_code, va hai chi muc cho hai chieu

Revision ID: r3ae8d2c4f6b91
Revises: dl3f7a2c9e4b16
Create Date: 2026-10-16

CHUYEN DU LIEU CU — CHO DUY NHAT CAN DOC KY TRONG BAN NAY.

Truoc dot nay, `services/assets.py` ghi MA BO PHAN vao cot `item_code` cho hai loai but toan:
khau hao TSCD (`source_type = 'khau_hao'`) va phan bo chi phi tra truoc (`source_type = 'phan_bo'`).
Do lai tren main 16/10/2026: DUNG HAI nguon ay, khong con nguon nao khac. Nen cau UPDATE duoi day
chon duoc CHINH XAC nhung dong phai chuyen, khong doan mot dong nao.

Dieu kien `item_code <> ''` la bat buoc: bo phan de trong thi khong co gi de chuyen, va khong co
dieu kien ay thi cau lenh van chay nhung dem ra mot con so dong "da chuyen" lon hon su that.

Chieu nguoc (downgrade) tra lai dung nhung dong ay, de ban nay lui duoc. Khong lui duoc thi mot
loi phat hien luc trien khai se phai sua bang tay tren co so du lieu that.
"""
from alembic import op
import sqlalchemy as sa

revision = "r3ae8d2c4f6b91"
down_revision = "dx3b7e2a9c4f61"
branch_labels = None
depends_on = None

NGUON_GHI_BO_PHAN = ("khau_hao", "phan_bo")


def upgrade() -> None:
    op.add_column("journal_lines", sa.Column("bo_phan", sa.String(length=20), nullable=False, server_default=""))
    op.create_index("ix_journal_lines_bo_phan", "journal_lines", ["bo_phan"])
    op.create_index("ix_journal_lines_item_code", "journal_lines", ["item_code"])
    op.execute(
        "UPDATE journal_lines SET bo_phan = item_code, item_code = '' "
        "WHERE item_code <> '' AND entry_id IN ("
        "  SELECT id FROM journal_entries WHERE source_type IN ('khau_hao', 'phan_bo'))"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE journal_lines SET item_code = bo_phan, bo_phan = '' "
        "WHERE bo_phan <> '' AND entry_id IN ("
        "  SELECT id FROM journal_entries WHERE source_type IN ('khau_hao', 'phan_bo'))"
    )
    op.drop_index("ix_journal_lines_item_code", table_name="journal_lines")
    op.drop_index("ix_journal_lines_bo_phan", table_name="journal_lines")
    op.drop_column("journal_lines", "bo_phan")
