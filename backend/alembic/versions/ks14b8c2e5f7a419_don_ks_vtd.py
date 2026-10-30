"""KS-14 — Đặt phòng khách sạn VTD có thanh toán: số phòng bán mỗi đêm, đơn đặt phòng, thanh toán (Chủ tịch duyệt 30/10/2026).

Ba bảng mới, bắt đầu RỖNG.

Revision ID: ks14b8c2e5f7a419
Revises: ks13a4d7b9e1c305
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "ks14b8c2e5f7a419"
down_revision = "ks13a4d7b9e1c305"
branch_labels = None
depends_on = None


def _s(n):
    return sa.String(length=n)


def upgrade() -> None:
    op.create_table(
        "phong_trong_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai_phong_id", sa.Integer(), sa.ForeignKey("loai_phong_vtd.id"), nullable=False),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("so_ban", sa.Integer(), nullable=True),
        sa.Column("dong", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sua_boi", _s(50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("loai_phong_id", "ngay", name="uq_phong_trong_vtd"),
    )
    op.create_index("ix_phong_trong_vtd_loai_phong_id", "phong_trong_vtd", ["loai_phong_id"])
    op.create_index("ix_phong_trong_vtd_ngay", "phong_trong_vtd", ["ngay"])

    op.create_table(
        "don_ks_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", _s(16), nullable=False, unique=True),
        sa.Column("khach_san_id", sa.Integer(), sa.ForeignKey("khach_san_vtd.id"), nullable=False),
        sa.Column("tai_khoan_ngoai_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("cong", _s(12), nullable=False, server_default=""),
        sa.Column("ho_ten", _s(120), nullable=False, server_default=""),
        sa.Column("lien_he", _s(120), nullable=False, server_default=""),
        sa.Column("email", _s(160), nullable=False, server_default=""),
        sa.Column("yeu_cau", sa.Text(), nullable=False, server_default=""),
        sa.Column("vao", sa.Date(), nullable=False),
        sa.Column("ra", sa.Date(), nullable=False),
        sa.Column("nguoi_lon", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tre_em", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dong", sa.JSON(), nullable=True),
        sa.Column("so_phong", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tien_phong", TIEN, nullable=False, server_default="0"),
        sa.Column("thue_phi", TIEN, nullable=False, server_default="0"),
        sa.Column("tong", TIEN, nullable=False, server_default="0"),
        sa.Column("trang_thai", _s(12), nullable=False, server_default="cho_tra"),
        sa.Column("giu_den", sa.DateTime(), nullable=True),
        sa.Column("tra_luc", sa.DateTime(), nullable=True),
        sa.Column("han_chot", sa.DateTime(), nullable=True),
        sa.Column("ma_xac_nhan_ks", _s(60), nullable=False, server_default=""),
        sa.Column("xac_nhan_boi", _s(50), nullable=False, server_default=""),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_boi", _s(60), nullable=False, server_default=""),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_huy", _s(300), nullable=False, server_default=""),
        sa.Column("so_hoan", TIEN, nullable=False, server_default="0"),
        sa.Column("hoan_tt", _s(10), nullable=False, server_default=""),
        sa.Column("mien_phat_boi", _s(50), nullable=False, server_default=""),
        sa.Column("da_hoan_tien", TIEN, nullable=False, server_default="0"),
        sa.Column("hoan_boi", _s(50), nullable=False, server_default=""),
        sa.Column("hoan_luc", sa.DateTime(), nullable=True),
        sa.Column("hoan_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("hoa_hong", TIEN, nullable=True),
        sa.Column("phai_tra_ks", TIEN, nullable=True),
        sa.Column("chot_boi", _s(50), nullable=False, server_default=""),
        sa.Column("chot_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
    )
    for c in ("khach_san_id", "tai_khoan_ngoai_id", "vao", "trang_thai", "hoan_tt"):
        op.create_index(f"ix_don_ks_vtd_{c}", "don_ks_vtd", [c])

    op.create_table(
        "thanh_toan_ks_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("don_id", sa.Integer(), sa.ForeignKey("don_ks_vtd.id"), nullable=False),
        sa.Column("kenh", _s(8), nullable=False),
        sa.Column("so_tien", TIEN, nullable=False),
        sa.Column("trang_thai", _s(12), nullable=False, server_default="cho"),
        sa.Column("bank_txn_id", sa.Integer(), sa.ForeignKey("bank_transactions.id"), nullable=True, unique=True),
        sa.Column("ma_gd", _s(40), nullable=False, server_default=""),
        sa.Column("so_gd_cong", _s(40), nullable=False, server_default=""),
        sa.Column("ket_qua", _s(10), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
        sa.Column("xac_nhan_boi", _s(50), nullable=False, server_default=""),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("ghi_chu", _s(300), nullable=False, server_default=""),
        sa.Column("goc", _s(80), nullable=False, server_default=""),
        sa.Column("phi_the", TIEN, nullable=True),
        sa.Column("but_toan", _s(30), nullable=False, server_default=""),
    )
    for c in ("don_id", "trang_thai", "ma_gd"):
        op.create_index(f"ix_thanh_toan_ks_vtd_{c}", "thanh_toan_ks_vtd", [c])


def downgrade() -> None:
    for t in ("thanh_toan_ks_vtd", "don_ks_vtd", "phong_trong_vtd"):
        op.drop_table(t)
