"""KS-15 — Đánh giá khách sạn VTD (thang 10, như AT-3) (Chủ tịch duyệt 30/10/2026).

Một bảng mới, bắt đầu RỖNG.

Revision ID: ks15c3d6e8f1a527
Revises: ks14b8c2e5f7a419
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "ks15c3d6e8f1a527"
down_revision = "ks14b8c2e5f7a419"
branch_labels = None
depends_on = None


def _s(n):
    return sa.String(length=n)


def upgrade() -> None:
    op.create_table(
        "danh_gia_ks_vtd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("don_id", sa.Integer(), sa.ForeignKey("don_ks_vtd.id"), nullable=False, unique=True),
        sa.Column("khach_san_id", sa.Integer(), sa.ForeignKey("khach_san_vtd.id"), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("ten_hien", _s(40), nullable=False, server_default=""),
        sa.Column("loai_phong", _s(160), nullable=False, server_default=""),
        sa.Column("so_dem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ngay_tra", sa.Date(), nullable=False),
        sa.Column("di_cung", _s(20), nullable=False, server_default=""),
        sa.Column("diem", sa.Integer(), nullable=False),
        sa.Column("diem_sach", sa.Integer(), nullable=True),
        sa.Column("diem_vi_tri", sa.Integer(), nullable=True),
        sa.Column("diem_phong", sa.Integer(), nullable=True),
        sa.Column("diem_phuc_vu", sa.Integer(), nullable=True),
        sa.Column("diem_gia", sa.Integer(), nullable=True),
        sa.Column("tieu_de", _s(120), nullable=False, server_default=""),
        sa.Column("nhan_xet", sa.Text(), nullable=False, server_default=""),
        sa.Column("anh", sa.JSON(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("an", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("an_ly_do", _s(20), nullable=False, server_default=""),
        sa.Column("an_ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("an_boi", _s(50), nullable=False, server_default=""),
        sa.Column("an_luc", sa.DateTime(), nullable=True),
        sa.Column("xem_lai", _s(6), nullable=False, server_default=""),
        sa.Column("xem_lai_boi", _s(50), nullable=False, server_default=""),
        sa.Column("xem_lai_luc", sa.DateTime(), nullable=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi_boi", _s(60), nullable=False, server_default=""),
        sa.Column("tra_loi_luc", sa.DateTime(), nullable=True),
        sa.Column("tra_loi_an", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tra_loi_an_ly_do", _s(20), nullable=False, server_default=""),
    )
    for c in ("khach_san_id", "tai_khoan_id", "tao_luc", "an"):
        op.create_index(f"ix_danh_gia_ks_vtd_{c}", "danh_gia_ks_vtd", [c])


def downgrade() -> None:
    op.drop_table("danh_gia_ks_vtd")
