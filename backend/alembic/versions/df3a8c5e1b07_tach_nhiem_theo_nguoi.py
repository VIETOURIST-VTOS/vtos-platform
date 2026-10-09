"""Dot E2a: tach bach trach nhiem theo NGUOI - dau chan va cap xung dot

Revision ID: df3a8c5e1b07
Revises: ce4d7b1a9f62
Create Date: 2026-10-09

Hai bang moi, CA HAI BAT DAU RONG.

`cap_tach_nhiem` rong la CO Y: moi dong la mot quy che kiem soat noi bo co nguoi ky. Nap san mot
dong la may tu dat quy che ho nguoi. `muc_do` khong co server_default vi cung ly do - RONG nghia
la CHUA AI DAT, khong phai mot muc nao do (nguyen tac K2).

`buoc_da_lam` khong co rang buoc duy nhat tren (pham_vi, ma_buoc): lam lai mot buoc
phai de lai mot dong nua chu khong ghi de dong cu. Co chi muc tren pham_vi de tra
nhanh dau chan cua mot pham vi (vd `dc:12`, `ky:2026-09`).
"""
import sqlalchemy as sa
from alembic import op

revision = "df3a8c5e1b07"
down_revision = "ce4d7b1a9f62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buoc_da_lam",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pham_vi", sa.String(length=60), nullable=False),
        sa.Column("ma_buoc", sa.String(length=40), nullable=False),
        sa.Column("ma_nguoi", sa.String(length=40), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("vai", sa.String(length=30), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buoc_da_lam_ma_nguoi", "buoc_da_lam", ["ma_nguoi"])
    op.create_index("ix_buoc_da_lam_pham_vi", "buoc_da_lam", ["pham_vi"])
    op.create_index("ix_buoc_da_lam_pham_vi_buoc", "buoc_da_lam", ["pham_vi", "ma_buoc"])

    op.create_table(
        "cap_tach_nhiem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ma_cap", sa.String(length=60), nullable=False),
        sa.Column("buoc_a", sa.String(length=40), nullable=False),
        sa.Column("buoc_b", sa.String(length=40), nullable=False),
        sa.Column("ten", sa.String(length=160), nullable=True),
        sa.Column("mo_ta", sa.Text(), nullable=True),
        sa.Column("muc_do", sa.String(length=20), nullable=True),
        sa.Column("nguoi_ky", sa.String(length=50), nullable=True),
        sa.Column("can_cu", sa.Text(), nullable=True),
        sa.Column("ngay_hieu_luc", sa.DateTime(), nullable=True),
        sa.Column("dang_ap_dung", sa.Boolean(), nullable=True),
        sa.Column("boi", sa.String(length=50), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ux_cap_tach_nhiem_ma", "cap_tach_nhiem", ["ma_cap"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_cap_tach_nhiem_ma", table_name="cap_tach_nhiem")
    op.drop_table("cap_tach_nhiem")
    op.drop_index("ix_buoc_da_lam_pham_vi_buoc", table_name="buoc_da_lam")
    op.drop_index("ix_buoc_da_lam_pham_vi", table_name="buoc_da_lam")
    op.drop_index("ix_buoc_da_lam_ma_nguoi", table_name="buoc_da_lam")
    op.drop_table("buoc_da_lam")
