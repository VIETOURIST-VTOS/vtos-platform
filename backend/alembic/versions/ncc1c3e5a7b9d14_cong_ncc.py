"""NCC-1 — cổng nhà cung cấp: nối tài khoản, phản hồi đơn, giá / đề xuất, bản kê, đề nghị, học liệu; nhà hàng nhận bàn.

Revision ID: ncc1c3e5a7b9d14
Revises: cd2b8e4f1a6c27
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "ncc1c3e5a7b9d14"
down_revision = "cd2b8e4f1a6c27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tai_khoan_ngoai", sa.Column("ncc_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True))
    op.create_index("ix_tai_khoan_ngoai_ncc_id", "tai_khoan_ngoai", ["ncc_id"])
    op.add_column("nha_hang", sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True))
    op.create_index("ix_nha_hang_supplier_id", "nha_hang", ["supplier_id"])
    op.add_column("yeu_cau_khach", sa.Column("nha_hang_tt", sa.String(length=10), nullable=False, server_default="cho"))
    op.add_column("yeu_cau_khach", sa.Column("nha_hang_ghi_chu", sa.Text(), nullable=False, server_default=""))
    op.add_column("yeu_cau_khach", sa.Column("nha_hang_luc", sa.DateTime(), nullable=True))
    op.create_table(
        "phan_hoi_don_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("hanh_dong", sa.String(length=10), nullable=False),
        sa.Column("ma_xac_nhan", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("xu_ly_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "gia_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False, index=True),
        sa.Column("dich_vu", sa.String(length=200), nullable=False),
        sa.Column("don_vi", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("gia", TIEN, nullable=False),
        sa.Column("so_luong_mo", sa.Integer(), nullable=True),
        sa.Column("tu_ngay", sa.Date(), nullable=True),
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("ngay_khong_phuc_vu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("thay_cho_id", sa.Integer(), nullable=True),
        sa.Column("het_hieu_luc", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("de_xuat_id", sa.Integer(), nullable=True),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "de_xuat_gia_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("loai", sa.String(length=10), nullable=False, server_default="gia"),
        sa.Column("gia_ncc_id", sa.Integer(), nullable=True),
        sa.Column("thuc_don_id", sa.Integer(), nullable=True),
        sa.Column("nha_hang_id", sa.Integer(), nullable=True),
        sa.Column("dich_vu", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("don_vi", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("gia", TIEN, nullable=False),
        sa.Column("gia_tre_em", TIEN, nullable=True),
        sa.Column("so_luong_mo", sa.Integer(), nullable=True),
        sa.Column("tu_ngay", sa.Date(), nullable=True),
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("ngay_khong_phuc_vu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="cho", index=True),
        sa.Column("xu_ly_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "ban_ke_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=30), nullable=False, unique=True, index=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False, index=True),
        sa.Column("ky", sa.String(length=7), nullable=False),
        sa.Column("trang_thai", sa.String(length=14), nullable=False, server_default="cho_ncc", index=True),
        sa.Column("tong", TIEN, nullable=False, server_default="0"),
        sa.Column("lap_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=False),
        sa.Column("xac_nhan_tk_id", sa.Integer(), nullable=True),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "dong_ban_ke_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ban_ke_id", sa.Integer(), sa.ForeignKey("ban_ke_ncc.id"), nullable=False, index=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False, index=True),
        sa.Column("ma_don", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("noi_dung", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("ngay", sa.Date(), nullable=True),
        sa.Column("gia_tri", TIEN, nullable=False, server_default="0"),
        sa.Column("ncc_gia_tri", TIEN, nullable=True),
        sa.Column("ncc_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "de_nghi_ncc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False, unique=True, index=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("loai", sa.String(length=12), nullable=False),
        sa.Column("bo_phan", sa.String(length=12), nullable=False, server_default="ketoan"),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="moi", index=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("xu_ly_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "hoc_lieu_doi_tac",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tieu_de", sa.String(length=200), nullable=False),
        sa.Column("nhom", sa.String(length=12), nullable=False, server_default="quy_trinh"),
        sa.Column("danh_cho", sa.JSON(), nullable=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("hien", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dang_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
        sa.Column("go_boi", sa.String(length=50), nullable=False, server_default=""),
    )


def downgrade() -> None:
    for t in ("hoc_lieu_doi_tac", "de_nghi_ncc", "dong_ban_ke_ncc", "ban_ke_ncc", "de_xuat_gia_ncc", "gia_ncc", "phan_hoi_don_ncc"):
        op.drop_table(t)
    for c in ("nha_hang_luc", "nha_hang_ghi_chu", "nha_hang_tt"):
        op.drop_column("yeu_cau_khach", c)
    op.drop_index("ix_nha_hang_supplier_id", table_name="nha_hang")
    op.drop_column("nha_hang", "supplier_id")
    op.drop_index("ix_tai_khoan_ngoai_ncc_id", table_name="tai_khoan_ngoai")
    op.drop_column("tai_khoan_ngoai", "ncc_id")
