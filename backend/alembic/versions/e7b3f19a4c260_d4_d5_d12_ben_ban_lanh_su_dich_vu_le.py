"""Đ-4 nhiều bên bán ghép land · Đ-12 đề nghị chi phí lãnh sự

Revision ID: e7b3f19a4c260
Revises: d4a9c72e1b085
Create Date: 2026-09-13

Bốn bảng mới, không sửa bảng nào đang có – nên bản này lùi lại được sạch.

    tour_ben_ban           một bên bán cùng ngồi trên chuyến (đại lý ghép land, hoặc Vietourist)
    tour_ben_ban_dong      dòng phân bổ / hoàn tip / thanh toán của từng bên
    de_nghi_lanh_su        tờ đề nghị chi phí lãnh sự
    de_nghi_lanh_su_dong   một khách trên tờ ấy

KHÔNG có bảng nào cho Đ-5 (dịch vụ lẻ theo tháng) ở đây, dù bản đề xuất 12/9 có nêu. Đo lại ngày
13/9: VTOS đã có màn hình /non-package làm đúng sổ ấy theo tháng, đã có bốn mã khoản mục vs_phi_lsq,
vs_phi_dich_vu_visa, vs_dich_thuat, hd_phi_dieu_hanh cho bốn cột chi của tệp, và tour_cost_lines đã
mang được tien_te / so_tien_goc / ty_gia / ngay_ty_gia. Dựng thêm bảng là tạo SỔ THỨ BA cho cùng một
việc — và sổ ấy sẽ không sinh bút toán, nên số kế toán tách làm hai. Đ-5 làm bằng một bảng tổng hợp
ĐỌC từ dữ liệu đang có, không phải bằng bảng mới.

KHÔNG có bảng biểu phí lãnh sự ở đây: biểu phí dùng lại `bang_gia` / `bang_gia_dong` đã có sẵn, và
do nhân viên team Visa khai – mốc tuổi giảm phí là quy định của từng lãnh sự quán, không phải hằng
số của phần mềm.
"""
import sqlalchemy as sa
from alembic import op

revision = "e7b3f19a4c260"
down_revision = "d4a9c72e1b085"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)
TY_GIA = sa.Numeric(18, 4)


def upgrade():
    op.create_table(
        "tour_ben_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ten_ben", sa.String(length=200), nullable=False),
        sa.Column("la_vietourist", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("mst", sa.String(length=20), nullable=True),
        sa.Column("so_khach_nguoi_lon", sa.Integer(), nullable=True),
        sa.Column("so_khach_tre_em", sa.Integer(), nullable=True),
        sa.Column("so_khach_em_be", sa.Integer(), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tbb_tour", "tour_ben_ban", ["tour_id"])

    op.create_table(
        "tour_ben_ban_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ben_ban_id", sa.Integer(), sa.ForeignKey("tour_ben_ban.id"), nullable=False),
        sa.Column("stt", sa.Integer(), nullable=True),
        sa.Column("noi_dung", sa.String(length=300), nullable=True),
        sa.Column("loai", sa.String(length=20), nullable=False, server_default="phan_bo"),
        sa.Column("cach_chia", sa.String(length=20), nullable=True),
        sa.Column("don_gia", TIEN, nullable=True),
        sa.Column("so_luong", sa.Float(), nullable=True),
        sa.Column("thanh_tien", TIEN, nullable=True),
        sa.Column("ngay", sa.Date(), nullable=True),
        sa.Column("so_chung_tu", sa.String(length=100), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tbbd_ben", "tour_ben_ban_dong", ["ben_ban_id"])
    op.create_index("ix_tbbd_tour", "tour_ben_ban_dong", ["tour_id"])

    op.create_table(
        "de_nghi_lanh_su",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=40), nullable=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("thi_truong", sa.String(length=20), nullable=True),
        sa.Column("ngay", sa.Date(), nullable=True),
        sa.Column("don_vi_thu", sa.String(length=200), nullable=True),
        sa.Column("mst_don_vi_thu", sa.String(length=30), nullable=True),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="nhap"),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
        sa.Column("nguoi_nhap", sa.String(length=60), nullable=True),
        sa.Column("nhap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dnls_tour", "de_nghi_lanh_su", ["tour_id"])
    op.create_index("ix_dnls_ngay", "de_nghi_lanh_su", ["ngay"])

    op.create_table(
        "de_nghi_lanh_su_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("de_nghi_id", sa.Integer(), sa.ForeignKey("de_nghi_lanh_su.id"), nullable=False),
        sa.Column("stt", sa.Integer(), nullable=True),
        sa.Column("ho_ten", sa.String(length=200), nullable=True),
        sa.Column("gioi_tinh", sa.String(length=10), nullable=True),
        sa.Column("ngay_sinh", sa.Date(), nullable=True),
        sa.Column("sale", sa.String(length=100), nullable=True),
        sa.Column("ben_ban_id", sa.Integer(), sa.ForeignKey("tour_ben_ban.id"), nullable=True),
        sa.Column("khach_id", sa.Integer(), sa.ForeignKey("booking_khach.id"), nullable=True),
        sa.Column("phi_tls_cao_cap", TIEN, nullable=True),
        sa.Column("phi_tls_co_ban", TIEN, nullable=True),
        sa.Column("phi_lsq", TIEN, nullable=True),
        sa.Column("thanh_tien", TIEN, nullable=True),
        sa.Column("mst", sa.String(length=30), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=True),
    )
    op.create_index("ix_dnlsd_to", "de_nghi_lanh_su_dong", ["de_nghi_id"])


def downgrade():
    op.drop_table("de_nghi_lanh_su_dong")
    op.drop_table("de_nghi_lanh_su")
    op.drop_table("tour_ben_ban_dong")
    op.drop_table("tour_ben_ban")
