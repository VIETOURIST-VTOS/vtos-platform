"""Đ-8 vé máy bay theo mã đặt chỗ · Đ-9 công nợ trưởng đoàn nhiều đồng tiền

Revision ID: d4a9c72e1b085
Revises: c1f5a8d3e7b62
Create Date: 2026-09-13

Bốn bảng mới, không sửa bảng nào đang có – nên bản này lùi lại được sạch.

    tour_ve_ma          khối chỗ giữ ở hãng: mã, hành trình, số chỗ, HẠN XUẤT VÉ
    tour_ve_khach       một dòng một khách – ĐÂY LÀ SỐ CHỐT của khối vé
    tour_ve_thanh_toan  các đợt trả tiền cho đại lý vé (chỉ TRỪ DẦN vào nợ)
    tour_tl_cong_no     từng dòng trên tờ quyết toán trưởng đoàn, mỗi dòng một đồng tiền

Cột tiền dùng Numeric(18, 2) và tỷ giá Numeric(18, 4), đúng quy ước V9.
"""
import sqlalchemy as sa
from alembic import op

revision = "d4a9c72e1b085"
down_revision = "c1f5a8d3e7b62"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)
TY_GIA = sa.Numeric(18, 4)


def upgrade():
    op.create_table(
        "tour_ve_ma",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ma_dat_cho", sa.String(length=40), nullable=False),
        sa.Column("hang_bay", sa.String(length=60), nullable=True),
        sa.Column("hanh_trinh", sa.String(length=200), nullable=True),
        sa.Column("so_cho_giu", sa.Integer(), nullable=True),
        sa.Column("han_xuat_ve", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="giu_cho"),
        sa.Column("nha_cung_cap", sa.String(length=200), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tvm_tour", "tour_ve_ma", ["tour_id"])
    op.create_index("ix_tvm_ma", "tour_ve_ma", ["ma_dat_cho"])

    op.create_table(
        "tour_ve_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ve_ma_id", sa.Integer(), sa.ForeignKey("tour_ve_ma.id"), nullable=True),
        sa.Column("khach_id", sa.Integer(), sa.ForeignKey("booking_khach.id"), nullable=True),
        sa.Column("ho_ten_ve", sa.String(length=200), nullable=True),
        sa.Column("loai", sa.String(length=20), nullable=False, server_default="ve"),
        sa.Column("gia_ve", TIEN, nullable=True),
        sa.Column("gia_ve_noi_dia", TIEN, nullable=True),
        sa.Column("phi_khac", TIEN, nullable=True),
        sa.Column("phi_nang_hang", TIEN, nullable=True),
        sa.Column("thanh_tien", TIEN, nullable=True),
        sa.Column("tien_te", sa.String(length=3), nullable=True),
        sa.Column("ty_gia", TY_GIA, nullable=True),
        sa.Column("so_hoa_don", sa.String(length=100), nullable=True),
        sa.Column("ly_do", sa.String(length=300), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tvk_tour", "tour_ve_khach", ["tour_id"])
    op.create_index("ix_tvk_ma", "tour_ve_khach", ["ve_ma_id"])

    op.create_table(
        "tour_ve_thanh_toan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ve_ma_id", sa.Integer(), sa.ForeignKey("tour_ve_ma.id"), nullable=True),
        sa.Column("ngay", sa.Date(), nullable=True),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("tien_te", sa.String(length=3), nullable=True),
        sa.Column("ty_gia", TY_GIA, nullable=True),
        sa.Column("hinh_thuc", sa.String(length=40), nullable=True),
        sa.Column("so_chung_tu", sa.String(length=100), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tvtt_tour", "tour_ve_thanh_toan", ["tour_id"])

    op.create_table(
        "tour_tl_cong_no",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("phan_cong_id", sa.Integer(), sa.ForeignKey("guide_assignments.id"), nullable=True),
        sa.Column("ten_truong_doan", sa.String(length=200), nullable=True),
        sa.Column("stt", sa.Integer(), nullable=True),
        sa.Column("noi_dung", sa.String(length=300), nullable=True),
        sa.Column("loai", sa.String(length=30), nullable=False),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("tien_te", sa.String(length=3), nullable=True),
        sa.Column("ty_gia", TY_GIA, nullable=True),
        sa.Column("ngay_ty_gia", sa.Date(), nullable=True),
        sa.Column("hdv_chi_id", sa.Integer(), sa.ForeignKey("tour_hdv_chi.id"), nullable=True),
        sa.Column("da_thanh_toan", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("ngay_thanh_toan", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ttcn_tour", "tour_tl_cong_no", ["tour_id"])
    op.create_index("ix_ttcn_pc", "tour_tl_cong_no", ["phan_cong_id"])


def downgrade():
    op.drop_table("tour_tl_cong_no")
    op.drop_table("tour_ve_thanh_toan")
    op.drop_table("tour_ve_khach")
    op.drop_table("tour_ve_ma")
