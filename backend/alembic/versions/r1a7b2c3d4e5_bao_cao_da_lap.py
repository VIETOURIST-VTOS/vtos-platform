"""Dot R1 15/10/2026 - ban bao cao da lap: so dong bang theo tung chi tieu.

VI SAO: truoc dot nay man hinh BCTC tinh lai tu so MOI LAN MO, nen con so cua mot ky da qua doi
theo so. Do duoc 15/10/2026 tren so thu: sau khi chot moc kiem toan 30/06/2026 (dap an 10 ty),
nap them moc 31/12/2025 thi chi tieu 111 tai 30/06/2026 tut xuong 9,5 ty - vi cua chot so ghi but
toan theo CHENH LECH va but toan moi de ngay 31/12/2025 chay xuoi vao so du ngay sau.

HAI BANG: `bao_cao_da_lap` (mot BAN cua mot ky) va `bao_cao_da_lap_dong` (tung chi tieu da dong
bang). Khong luu lai ca tep: luu tung chi tieu thi mot cau truy van tra loi duoc "chi tieu 110 ky
nay khac ky truoc bao nhieu".

Revision ID: r1a7b2c3d4e5
Revises: e16c3d4e5f6a
"""
import sqlalchemy as sa
from alembic import op

revision = "r1a7b2c3d4e5"
down_revision = "e16c3d4e5f6a"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2, asdecimal=False)


def upgrade() -> None:
    op.create_table(
        "bao_cao_da_lap",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("loai", sa.String(20), nullable=False, server_default="bctc"),
        sa.Column("loai_ky", sa.String(12), nullable=False, server_default="nam"),
        sa.Column("ky", sa.String(24), nullable=False, server_default=""),
        sa.Column("tu_ngay", sa.Date(), nullable=False),
        sa.Column("den_ngay", sa.Date(), nullable=False),
        # Rong nghia la ban nay KHONG co cot so sanh - khac han "so sanh ra 0".
        sa.Column("so_sanh_den", sa.Date(), nullable=True),
        sa.Column("tham_so", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("nguoi_dai_dien", sa.String(160), nullable=False, server_default=""),
        sa.Column("ngay_lap", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default="nhap"),
        sa.Column("lap_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("lap_vai", sa.String(24), nullable=False, server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
        sa.Column("trinh_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("trinh_luc", sa.DateTime(), nullable=True),
        sa.Column("ky_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("ky_vai", sa.String(24), nullable=False, server_default=""),
        sa.Column("ky_luc", sa.DateTime(), nullable=True),
        sa.Column("tu_choi_ly_do", sa.String(500), nullable=False, server_default=""),
        sa.Column("thay_the_id", sa.Integer(), sa.ForeignKey("bao_cao_da_lap.id"), nullable=True),
    )
    op.create_index("ix_bao_cao_da_lap_company_id", "bao_cao_da_lap", ["company_id"])
    op.create_index("ix_bao_cao_da_lap_loai", "bao_cao_da_lap", ["loai"])
    op.create_index("ix_bao_cao_da_lap_ky", "bao_cao_da_lap", ["ky"])
    op.create_index("ix_bao_cao_da_lap_den_ngay", "bao_cao_da_lap", ["den_ngay"])
    op.create_index("ix_bao_cao_da_lap_trang_thai", "bao_cao_da_lap", ["trang_thai"])
    op.create_index("ix_bao_cao_da_lap_tra", "bao_cao_da_lap",
                    ["loai", "company_id", "ky", "trang_thai"])

    op.create_table(
        "bao_cao_da_lap_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ban_id", sa.Integer(),
                  sa.ForeignKey("bao_cao_da_lap.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bang", sa.String(8), nullable=False),
        sa.Column("ma", sa.String(12), nullable=False),
        sa.Column("ten", sa.String(300), nullable=False, server_default=""),
        # HAI O TIEN KHONG NULLABLE: mot dong co mat nghia la chi tieu ay DA DUOC TINH.
        # "tinh ra 0" khac han "khong tinh" - chi tieu khong tinh thi KHONG co dong.
        sa.Column("gia_tri", TIEN, nullable=False),
        sa.Column("gia_tri_ss", TIEN, nullable=False),
    )
    op.create_index("ix_bao_cao_da_lap_dong_ban_id", "bao_cao_da_lap_dong", ["ban_id"])
    op.create_index("ix_bcdld_ban_bang_ma", "bao_cao_da_lap_dong", ["ban_id", "bang", "ma"])


def downgrade() -> None:
    op.drop_table("bao_cao_da_lap_dong")
    op.drop_table("bao_cao_da_lap")
