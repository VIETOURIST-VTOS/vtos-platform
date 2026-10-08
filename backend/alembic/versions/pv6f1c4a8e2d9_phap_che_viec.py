"""Đợt D2 – bàn làm việc Pháp chế: yêu cầu, rà soát hợp đồng, sổ chữ ký, xác nhận chủ số liệu.

Bốn bảng, cả bốn tạo ra RỖNG. Không chèn một dòng dữ liệu nào trong bản nâng cấp này – ranh giới
09/9/2026: phần mềm viết cấu trúc, người dùng khai số liệu.

`down_revision` được ĐO LẠI NGAY TRƯỚC KHI GỘP, không phải lúc viết: main đi tiếp trong lúc đợt này
được viết, và hai đầu mạch làm container không khởi động nổi vì Dockerfile chạy `alembic upgrade
head`. Bài học của Đợt A1 ngày 07/10/2026.

Revision ID: pv6f1c4a8e2d9
Revises: pc5e8b3d1f7a2
"""
import sqlalchemy as sa
from alembic import op

revision = "pv6f1c4a8e2d9"
down_revision = "pc5e8b3d1f7a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "yeu_cau_phap_che",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(30), nullable=False),
        sa.Column("tieu_de", sa.String(300), nullable=False),
        sa.Column("noi_dung", sa.Text(), server_default=""),
        sa.Column("phong_gui", sa.String(80), server_default=""),
        sa.Column("nguoi_gui", sa.String(80), server_default=""),
        sa.Column("muc_do", sa.String(10), server_default="thuong"),
        sa.Column("han_mong_muon", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(16), server_default="moi"),
        sa.Column("nguoi_nhan", sa.String(50), server_default=""),
        sa.Column("nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("ket_qua", sa.Text(), server_default=""),
        sa.Column("dong_luc", sa.DateTime(), nullable=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_yeu_cau_phap_che_loai", "yeu_cau_phap_che", ["loai"])
    op.create_index("ix_yeu_cau_phap_che_trang_thai", "yeu_cau_phap_che", ["trang_thai"])
    op.create_index("ix_yeu_cau_phap_che_tt", "yeu_cau_phap_che", ["trang_thai", "muc_do"])

    op.create_table(
        "ra_soat_hop_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("yeu_cau_id", sa.Integer(), sa.ForeignKey("yeu_cau_phap_che.id"), nullable=False),
        sa.Column("so_hop_dong", sa.String(80), server_default=""),
        sa.Column("doi_tac", sa.String(200), server_default=""),
        sa.Column("loai_hop_dong", sa.String(80), server_default=""),
        # K2: không server_default – rỗng khác 0.
        sa.Column("gia_tri", sa.Numeric(18, 2), nullable=True),
        sa.Column("ngay_nhan", sa.Date(), nullable=True),
        sa.Column("ngay_tra", sa.Date(), nullable=True),
        sa.Column("ket_luan", sa.String(20), server_default=""),
        sa.Column("rui_ro", sa.JSON(), nullable=True),
        sa.Column("dieu_kien", sa.Text(), server_default=""),
        sa.Column("nguoi_ra_soat", sa.String(50), server_default=""),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ra_soat_hop_dong_yc", "ra_soat_hop_dong", ["yeu_cau_id"])

    op.create_table(
        "ban_ghi_chu_ky",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("van_ban_id", sa.Integer(), sa.ForeignKey("van_ban_phap_che.id"), nullable=True),
        sa.Column("mo_ta", sa.String(300), server_default=""),
        sa.Column("nguoi_ky", sa.String(80), nullable=False),
        sa.Column("chuc_danh", sa.String(120), server_default=""),
        sa.Column("ngay_ky", sa.Date(), nullable=False),
        sa.Column("loai_chu_ky", sa.String(20), server_default="tuoi"),
        sa.Column("can_cu_tham_quyen", sa.Text(), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ban_ghi_chu_ky_ngay_ky", "ban_ghi_chu_ky", ["ngay_ky"])
    op.create_index("ix_ban_ghi_chu_ky_ngay", "ban_ghi_chu_ky", ["ngay_ky", "nguoi_ky"])

    op.create_table(
        "xac_nhan_chu_so_lieu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ban_ghi_id", sa.Integer(), sa.ForeignKey("ban_ghi_cong_bo.id"), nullable=False),
        sa.Column("chi_muc", sa.String(160), nullable=False),
        sa.Column("chu_so_lieu", sa.String(80), nullable=False),
        sa.Column("trang_thai", sa.String(16), server_default="cho"),
        sa.Column("y_kien", sa.Text(), server_default=""),
        sa.Column("xac_nhan_boi", sa.String(50), server_default=""),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_xac_nhan_chu_so_lieu_bg", "xac_nhan_chu_so_lieu", ["ban_ghi_id"])
    op.create_index("ix_xac_nhan_chu_so_lieu_tt", "xac_nhan_chu_so_lieu", ["trang_thai"])
    op.create_index("ux_xac_nhan_chu_so_lieu", "xac_nhan_chu_so_lieu",
                    ["ban_ghi_id", "chi_muc"], unique=True)


def downgrade() -> None:
    op.drop_table("xac_nhan_chu_so_lieu")
    op.drop_table("ban_ghi_chu_ky")
    op.drop_table("ra_soat_hop_dong")
    op.drop_table("yeu_cau_phap_che")
