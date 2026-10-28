"""DT-2 — đặt bàn nhà hàng có thanh toán (QR / OnePay), chính sách hủy, doanh số D06.

Revision ID: dt2b4d6f8a1c35
Revises: ncc1c3e5a7b9d14
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "dt2b4d6f8a1c35"
down_revision = "ncc1c3e5a7b9d14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "don_dat_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False, unique=True, index=True),
        sa.Column("yeu_cau_id", sa.Integer(), sa.ForeignKey("yeu_cau_khach.id"), nullable=False, unique=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("nguon", sa.String(length=12), nullable=False, server_default="khach_hang"),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=True, index=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False, index=True),
        sa.Column("thuc_don_id", sa.Integer(), sa.ForeignKey("thuc_don_nha_hang.id"), nullable=False),
        sa.Column("ngay", sa.Date(), nullable=False, index=True),
        sa.Column("gio", sa.String(length=5), nullable=False),
        sa.Column("nguoi_lon", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tre_em", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ten_khach", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("dien_thoai", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("la_doan", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cach_tt", sa.String(length=4), nullable=False, server_default="coc"),
        sa.Column("ty_le_coc", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("tam_tinh", TIEN, nullable=False, server_default="0"),
        sa.Column("phai_tra_truoc", TIEN, nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="cho_nhan", index=True),
        sa.Column("nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("han_tra", sa.DateTime(), nullable=True),
        sa.Column("bill_thuc_te", TIEN, nullable=True),
        sa.Column("thu_tai_ban", TIEN, nullable=True),
        sa.Column("bill_attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("dung_luc", sa.DateTime(), nullable=True),
        sa.Column("dung_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("doanh_so", TIEN, nullable=True),
        sa.Column("chot_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("chot_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_boi", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("huy_ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("mien_phat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("so_giu", TIEN, nullable=True),
        sa.Column("so_hoan", TIEN, nullable=True),
        sa.Column("hoan_tt", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("hoan_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("hoan_luc", sa.DateTime(), nullable=True),
        sa.Column("hoan_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "thanh_toan_dat_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("don_id", sa.Integer(), sa.ForeignKey("don_dat_ban.id"), nullable=False, index=True),
        sa.Column("kenh", sa.String(length=8), nullable=False),
        sa.Column("so_tien", TIEN, nullable=False),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="cho", index=True),
        sa.Column("bank_txn_id", sa.Integer(), sa.ForeignKey("bank_transactions.id"), nullable=True, unique=True),
        sa.Column("ma_gd", sa.String(length=40), nullable=False, server_default="", index=True),
        sa.Column("so_gd_cong", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("ket_qua", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
        sa.Column("xac_nhan_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("goc", sa.String(length=80), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("thanh_toan_dat_ban")
    op.drop_table("don_dat_ban")
