"""KS-13 — Danh mục khách sạn hợp tác VTD: khách sạn, ảnh, loại phòng, gói giá, mùa giá (Chủ tịch duyệt 30/10/2026).

Năm bảng mới, bắt đầu RỖNG.

Revision ID: ks13a4d7b9e1c305
Revises: pl1b7e4c9a2d6f03
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "ks13a4d7b9e1c305"
down_revision = "pl1b7e4c9a2d6f03"
branch_labels = None
depends_on = None



def _s(n):
    return sa.String(length=n)


def upgrade() -> None:
    op.create_table(
        "khach_san_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", _s(20), nullable=False, unique=True),
        sa.Column("ten", _s(160), nullable=False),
        sa.Column("tinh_thanh", _s(80), nullable=False, server_default=""),
        sa.Column("khu_vuc", _s(120), nullable=False, server_default=""),
        sa.Column("dia_chi", _s(300), nullable=False, server_default=""),
        sa.Column("sao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loai", _s(12), nullable=False, server_default="khach_san"),
        sa.Column("km_trung_tam", sa.Float(), nullable=True),
        sa.Column("gan", _s(300), nullable=False, server_default=""),
        sa.Column("noi_bat", _s(300), nullable=False, server_default=""),
        sa.Column("mo_ta", sa.Text(), nullable=False, server_default=""),
        sa.Column("tien_ich", sa.JSON(), nullable=True),
        sa.Column("gio_nhan", _s(5), nullable=False, server_default="14:00"),
        sa.Column("gio_tra", _s(5), nullable=False, server_default="12:00"),
        sa.Column("cs_tre_em", _s(300), nullable=False, server_default=""),
        sa.Column("cs_giuong_phu", _s(300), nullable=False, server_default=""),
        sa.Column("cs_vat_nuoi", _s(300), nullable=False, server_default=""),
        sa.Column("cs_khac", sa.Text(), nullable=False, server_default=""),
        sa.Column("thue_phi_pt", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lien_he_noi_bo", _s(300), nullable=False, server_default=""),
        sa.Column("ghi_chu_noi_bo", sa.Text(), nullable=False, server_default=""),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("hien_cong", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hien_boi", _s(50), nullable=False, server_default=""),
        sa.Column("hien_luc", sa.DateTime(), nullable=True),
        sa.Column("tat_ly_do", _s(200), nullable=False, server_default=""),
        sa.Column("ngung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tao_boi", _s(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sua_boi", _s(50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_khach_san_vtd_tinh_thanh", "khach_san_vtd", ["tinh_thanh"])
    op.create_index("ix_khach_san_vtd_supplier_id", "khach_san_vtd", ["supplier_id"])
    op.create_table(
        "loai_phong_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khach_san_id", sa.Integer(), sa.ForeignKey("khach_san_vtd.id"), nullable=False),
        sa.Column("ten", _s(120), nullable=False),
        sa.Column("dien_tich", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("giuong", _s(120), nullable=False, server_default=""),
        sa.Column("mo_ta", _s(300), nullable=False, server_default=""),
        sa.Column("toi_da_nguoi_lon", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("toi_da_tre_em", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_phong", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dang_ban", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sua_boi", _s(50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_loai_phong_vtd_khach_san_id", "loai_phong_vtd", ["khach_san_id"])
    op.create_table(
        "anh_khach_san_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khach_san_id", sa.Integer(), sa.ForeignKey("khach_san_vtd.id"), nullable=False),
        sa.Column("loai_phong_id", sa.Integer(), sa.ForeignKey("loai_phong_vtd.id"), nullable=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("hien_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("nho_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("rong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nhom", _s(12), nullable=False, server_default="khac"),
        sa.Column("chu_thich", _s(200), nullable=False, server_default=""),
        sa.Column("nguon", _s(200), nullable=False, server_default=""),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("la_bia", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trang_thai", _s(10), nullable=False, server_default="nhap"),
        sa.Column("ly_do_tra_lai", _s(300), nullable=False, server_default=""),
        sa.Column("tai_boi", _s(50), nullable=False, server_default=""),
        sa.Column("tai_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("duyet_boi", _s(50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_anh_khach_san_vtd_khach_san_id", "anh_khach_san_vtd", ["khach_san_id"])
    op.create_index("ix_anh_khach_san_vtd_loai_phong_id", "anh_khach_san_vtd", ["loai_phong_id"])
    op.create_index("ix_anh_khach_san_vtd_trang_thai", "anh_khach_san_vtd", ["trang_thai"])
    op.create_table(
        "goi_gia_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai_phong_id", sa.Integer(), sa.ForeignKey("loai_phong_vtd.id"), nullable=False),
        sa.Column("ten", _s(80), nullable=False, server_default="Chỉ phòng"),
        sa.Column("bua_sang", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("huy_truoc_ngay", sa.Integer(), nullable=True),
        sa.Column("dang_ban", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trang_thai", _s(10), nullable=False, server_default="nhap"),
        sa.Column("ly_do_tra_lai", _s(300), nullable=False, server_default=""),
        sa.Column("sua_boi", _s(50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("gui_boi", _s(50), nullable=False, server_default=""),
        sa.Column("duyet_boi", _s(50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_goi_gia_vtd_loai_phong_id", "goi_gia_vtd", ["loai_phong_id"])
    op.create_index("ix_goi_gia_vtd_trang_thai", "goi_gia_vtd", ["trang_thai"])
    op.create_table(
        "mua_gia_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goi_id", sa.Integer(), sa.ForeignKey("goi_gia_vtd.id"), nullable=False),
        sa.Column("tu_ngay", sa.Date(), nullable=False),
        sa.Column("den_ngay", sa.Date(), nullable=False),
        sa.Column("gia_thuong", TIEN, nullable=False),
        sa.Column("gia_cuoi_tuan", TIEN, nullable=True),
        sa.Column("gia_niem_yet", TIEN, nullable=True),
        sa.Column("ghi_chu", _s(200), nullable=False, server_default=""),
    )
    op.create_index("ix_mua_gia_vtd_goi_id", "mua_gia_vtd", ["goi_id"])


def downgrade() -> None:
    for t in ("mua_gia_vtd", "goi_gia_vtd", "anh_khach_san_vtd", "loai_phong_vtd", "khach_san_vtd"):
        op.drop_table(t)
