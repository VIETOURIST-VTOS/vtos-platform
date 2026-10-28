"""KS-2 — đối soát OTA: lô nạp báo cáo, đặt phòng OTA, sổ hoa hồng (USD); SubID trên link.

Revision ID: ks2c6e8a1b3d49
Revises: ks1b4d6f8a2c37
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "ks2c6e8a1b3d49"
down_revision = "ks1b4d6f8a2c37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doi_tac_ota", sa.Column("subid_cho_phep", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("doi_tac_ota", sa.Column("subid_tham_so", sa.String(length=30), nullable=False, server_default=""))
    op.add_column("luot_chuyen_ota", sa.Column("ma_luot", sa.String(length=16), nullable=True))
    op.create_index("ix_luot_chuyen_ota_ma_luot", "luot_chuyen_ota", ["ma_luot"], unique=True)
    op.create_table(
        "lo_nap_ota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=30), nullable=False, unique=True),
        sa.Column("doi_tac_ota_id", sa.Integer(), sa.ForeignKey("doi_tac_ota.id"), nullable=False, index=True),
        sa.Column("ky", sa.String(length=7), nullable=False, server_default=""),
        sa.Column("ten_tep", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("bam_tep", sa.String(length=64), nullable=False, index=True),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="cho_duyet", index=True),
        sa.Column("dong", sa.JSON(), nullable=False),
        sa.Column("so_dong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_loi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loi", sa.JSON(), nullable=False),
        sa.Column("nap_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nap_luc", sa.DateTime(), nullable=False),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("ket_qua", sa.JSON(), nullable=False),
    )
    op.create_table(
        "dat_phong_ota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi_tac_ota_id", sa.Integer(), sa.ForeignKey("doi_tac_ota.id"), nullable=False, index=True),
        sa.Column("khoa", sa.String(length=300), nullable=False),
        sa.Column("co_ma_rieng", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ky", sa.String(length=7), nullable=False, server_default="", index=True),
        sa.Column("ngay_dat", sa.Date(), nullable=True),
        sa.Column("san_pham", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("thanh_pho", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("quoc_gia", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("link", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("ngay_den", sa.Date(), nullable=True),
        sa.Column("ngay_di", sa.Date(), nullable=True),
        sa.Column("so_khach", sa.Integer(), nullable=True),
        sa.Column("tien_te", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("gia_tri_cent", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("hoa_hong_cent", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("trang_thai_chuyen", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("trang_thai_tt", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("ma_luot", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("luot_id", sa.Integer(), sa.ForeignKey("luot_chuyen_ota.id"), nullable=True, index=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lo_id", sa.Integer(), sa.ForeignKey("lo_nap_ota.id"), nullable=False),
        sa.Column("cap_nhat_luc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("doi_tac_ota_id", "khoa", name="uq_dat_phong_ota_khoa"),
    )
    op.create_table(
        "so_hoa_hong_ota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dat_phong_id", sa.Integer(), sa.ForeignKey("dat_phong_ota.id"), nullable=False, index=True),
        sa.Column("lo_id", sa.Integer(), sa.ForeignKey("lo_nap_ota.id"), nullable=False, index=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False),
        sa.Column("tien_te", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("chenh_cent", sa.BigInteger(), nullable=False),
        sa.Column("ly_do", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("so_hoa_hong_ota")
    op.drop_table("dat_phong_ota")
    op.drop_table("lo_nap_ota")
    op.drop_index("ix_luot_chuyen_ota_ma_luot", table_name="luot_chuyen_ota")
    op.drop_column("luot_chuyen_ota", "ma_luot")
    op.drop_column("doi_tac_ota", "subid_tham_so")
    op.drop_column("doi_tac_ota", "subid_cho_phep")
