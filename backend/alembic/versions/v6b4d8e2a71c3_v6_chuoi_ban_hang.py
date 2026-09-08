"""V6 – sáu bảng của chuỗi bán hàng: bảng giá, báo giá, bản đã gửi, hợp đồng khách

Revision ID: v6b4d8e2a71c3
Revises: v10a7f3c9e1b48
Create Date: 2026-09-08

Sáu bảng MỚI, không đụng bảng nào đang có – nên bản nâng cấp này không khóa bảng lớn và chạy được
giữa giờ làm việc, khác V9.

Ba bảng có người sửa (bang_gia, bao_gia, hop_dong_khach) mang sẵn cột `phien_ban` của V10 từ lúc
sinh ra. Chúng KHÔNG nằm trong BANG_CO_PHIEN_BAN – danh sách ấy là danh sách bảng được V10 THÊM cột,
và trộn hai thứ vào một chỗ thì phép thử canh V10 không còn nói lên điều gì.

bao_gia_ban cố ý KHÔNG có phien_ban: bản đã gửi khách không sửa, nên không có gì để va chạm.
"""
from alembic import op
import sqlalchemy as sa

revision = "v6b4d8e2a71c3"
down_revision = "v10a7f3c9e1b48"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "bang_gia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("ten", sa.String(200), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("mang", sa.String(20), server_default="kd_le"),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        sa.Column("hieu_luc_den", sa.Date(), nullable=True),
        sa.Column("tien_te", sa.String(3), server_default="VND"),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("trang_thai", sa.String(20), server_default="hieu_luc"),
        sa.Column("tao_boi", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bang_gia_ma", "bang_gia", ["ma"], unique=True)
    op.create_index("ix_bang_gia_product_id", "bang_gia", ["product_id"])
    op.create_index("ix_bang_gia_mang", "bang_gia", ["mang"])
    op.create_index("ix_bang_gia_hieu_luc_tu", "bang_gia", ["hieu_luc_tu"])

    op.create_table(
        "bang_gia_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bang_gia_id", sa.Integer(), sa.ForeignKey("bang_gia.id"), nullable=False),
        sa.Column("hang_khach", sa.String(20), server_default="nguoi_lon"),
        sa.Column("mo_ta", sa.String(200), server_default=""),
        sa.Column("gia_ban", TIEN, server_default="0"),
        sa.Column("gia_von", TIEN, nullable=True),
        sa.Column("chiet_khau_toi_da", sa.Float(), server_default="0"),
        sa.Column("thu_tu", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_bang_gia_dong_bang_gia_id", "bang_gia_dong", ["bang_gia_id"])

    op.create_table(
        "bao_gia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("mang", sa.String(20), server_default="kd_le"),
        sa.Column("khach_ten", sa.String(200), nullable=False),
        sa.Column("khach_dien_thoai", sa.String(30), server_default=""),
        sa.Column("khach_email", sa.String(120), server_default=""),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("bang_gia_id", sa.Integer(), sa.ForeignKey("bang_gia.id"), nullable=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("sales_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("ngay_khoi_hanh", sa.Date(), nullable=True),
        sa.Column("so_khach", sa.Integer(), server_default="1"),
        sa.Column("han_hieu_luc", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(20), server_default="nhap"),
        sa.Column("bien_luc_gui", sa.Float(), nullable=True),
        sa.Column("nguong_luc_gui", sa.Float(), nullable=True),
        sa.Column("duoi_bien", sa.Boolean(), server_default=sa.false()),
        sa.Column("giai_trinh", sa.Text(), server_default=""),
        sa.Column("duyet_boi", sa.String(50), server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), server_default=""),
        sa.Column("tao_boi", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bao_gia_ma", "bao_gia", ["ma"], unique=True)
    for c in ("mang", "lead_id", "product_id", "tour_id", "sales_id", "company_id", "trang_thai"):
        op.create_index(f"ix_bao_gia_{c}", "bao_gia", [c])

    op.create_table(
        "bao_gia_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bao_gia_id", sa.Integer(), sa.ForeignKey("bao_gia.id"), nullable=False),
        sa.Column("hang_khach", sa.String(20), server_default="nguoi_lon"),
        sa.Column("mo_ta", sa.String(200), server_default=""),
        sa.Column("so_luong", sa.Integer(), server_default="1"),
        sa.Column("don_gia", TIEN, server_default="0"),
        sa.Column("gia_von_don_vi", TIEN, nullable=True),
        sa.Column("chiet_khau", TIEN, server_default="0"),
        sa.Column("thu_tu", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_bao_gia_dong_bao_gia_id", "bao_gia_dong", ["bao_gia_id"])

    op.create_table(
        "bao_gia_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bao_gia_id", sa.Integer(), sa.ForeignKey("bao_gia.id"), nullable=False),
        sa.Column("lan", sa.Integer(), server_default="1"),
        sa.Column("tong_ban", TIEN, server_default="0"),
        sa.Column("tong_von", TIEN, nullable=True),
        sa.Column("bien", sa.Float(), nullable=True),
        sa.Column("nguong", sa.Float(), nullable=True),
        sa.Column("du_co_so", sa.Boolean(), server_default=sa.false()),
        sa.Column("noi_dung", sa.JSON(), nullable=True),
        sa.Column("gui_boi", sa.String(50), server_default=""),
        sa.Column("gui_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bao_gia_ban_bao_gia_id", "bao_gia_ban", ["bao_gia_id"])

    op.create_table(
        "hop_dong_khach",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("so_hop_dong", sa.String(50), nullable=False),
        sa.Column("bao_gia_id", sa.Integer(), sa.ForeignKey("bao_gia.id"), nullable=True),
        sa.Column("bao_gia_ban_id", sa.Integer(), sa.ForeignKey("bao_gia_ban.id"), nullable=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("khach_ten", sa.String(200), nullable=False),
        sa.Column("khach_dai_dien", sa.String(120), server_default=""),
        sa.Column("khach_ma_so_thue", sa.String(20), server_default=""),
        sa.Column("khach_dia_chi", sa.String(300), server_default=""),
        sa.Column("ngay_ky", sa.Date(), nullable=True),
        sa.Column("gia_tri", TIEN, server_default="0"),
        sa.Column("dat_coc", TIEN, server_default="0"),
        sa.Column("han_thanh_toan", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(20), server_default="nhap"),
        sa.Column("tep_dinh_kem", sa.String(300), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("tao_boi", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_hop_dong_khach_so_hop_dong", "hop_dong_khach", ["so_hop_dong"], unique=True)
    for c in ("bao_gia_id", "booking_id", "company_id", "trang_thai"):
        op.create_index(f"ix_hop_dong_khach_{c}", "hop_dong_khach", [c])


def downgrade() -> None:
    op.drop_table("hop_dong_khach")
    op.drop_table("bao_gia_ban")
    op.drop_table("bao_gia_dong")
    op.drop_table("bao_gia")
    op.drop_table("bang_gia_dong")
    op.drop_table("bang_gia")
