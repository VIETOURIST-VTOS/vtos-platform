"""PL-1 — Phân loại nhà hàng: «Đặc sản địa phương» + bậc sang trọng (Chủ tịch duyệt 30/10/2026).

Revision ID: pl1b7e4c9a2d6f03
Revises: at3a5d8c2e7f4b19
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "pl1b7e4c9a2d6f03"
down_revision = "at3a5d8c2e7f4b19"
branch_labels = None
depends_on = None

_COT = [
    ("dac_san_tay", sa.String(length=4)), ("dac_san_ly_do", sa.String(length=200)),
    ("dac_san_de_xuat", sa.String(length=4)), ("dac_san_de_xuat_ly_do", sa.String(length=200)),
    ("dac_san_de_xuat_boi", sa.String(length=50)),
    ("michelin_hang", sa.String(length=10)), ("michelin_boi", sa.String(length=50)),
    ("bac", sa.String(length=12)), ("bac_chot_boi", sa.String(length=50)),
    ("bac_de_xuat", sa.String(length=12)), ("bac_de_xuat_boi", sa.String(length=50)),
]
_LUC = ["dac_san_de_xuat_luc", "michelin_luc", "bac_chot_luc", "bac_de_xuat_luc"]


def upgrade() -> None:
    with op.batch_alter_table("nha_hang") as b:
        for ten, kieu in _COT:
            b.add_column(sa.Column(ten, kieu, nullable=False, server_default=""))
        b.add_column(sa.Column("michelin_gia", sa.Integer(), nullable=False, server_default="0"))
        for ten in _LUC:
            b.add_column(sa.Column(ten, sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nha_hang") as b:
        for ten in reversed(_LUC):
            b.drop_column(ten)
        b.drop_column("michelin_gia")
        for ten, _k in reversed(_COT):
            b.drop_column(ten)
