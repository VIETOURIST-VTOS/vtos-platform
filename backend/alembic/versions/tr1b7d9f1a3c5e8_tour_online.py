"""TR-1 — Tour kiểu Agoda trên cổng khách + nối nội dung web + đặt tour online (Chủ tịch duyệt 01–02/11/2026).
Thêm cột cho products, hai bảng mới don_tour_online / thanh_toan_tour_online. Không sửa dữ liệu cũ.

Revision ID: tr1b7d9f1a3c5e8
Revises: at2a6c8e0b2d4f6a1
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "tr1b7d9f1a3c5e8"
down_revision = "at2a6c8e0b2d4f6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products") as b:
        b.add_column(sa.Column("diem_den", sa.String(120), nullable=False, server_default=""))
        b.add_column(sa.Column("noi_bat", sa.JSON(), nullable=True))
        b.add_column(sa.Column("wellness", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("phuong_tien_ds", sa.JSON(), nullable=True))
        b.add_column(sa.Column("mo_thanh_toan", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("link_web", sa.String(300), nullable=False, server_default=""))
        b.add_column(sa.Column("noi_dung_web", sa.JSON(), nullable=True))
    op.create_table(
        "don_tour_online",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("tai_khoan_ngoai_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("nguoi_lon", sa.Integer(), nullable=False),
        sa.Column("tre_em", sa.Integer(), nullable=False),
        sa.Column("em_be", sa.Integer(), nullable=False),
        sa.Column("khach", sa.JSON(), nullable=False),
        sa.Column("email", sa.String(160), nullable=False),
        sa.Column("cach_tra", sa.String(4), nullable=False),
        sa.Column("tong", sa.Numeric(18, 2), nullable=False),
        sa.Column("phai_tra", sa.Numeric(18, 2), nullable=False),
        sa.Column("han_tra_con_lai", sa.DateTime(), nullable=True),
        sa.Column("hoa_don_cong_ty", sa.JSON(), nullable=True),
        sa.Column("hoa_don_da_xuat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hoa_don_xuat_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("hoa_don_xuat_luc", sa.DateTime(), nullable=True),
        sa.Column("email_gui_luc", sa.DateTime(), nullable=True),
        sa.Column("email_moc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_loi", sa.String(300), nullable=False, server_default=""),
        sa.Column("yeu_cau", sa.Text(), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_don_tour_online_booking_id", "don_tour_online", ["booking_id"], unique=True)
    op.create_index("ix_don_tour_online_ma", "don_tour_online", ["ma"])
    op.create_index("ix_don_tour_online_tour_id", "don_tour_online", ["tour_id"])
    op.create_index("ix_don_tour_online_product_id", "don_tour_online", ["product_id"])
    op.create_index("ix_don_tour_online_tai_khoan_ngoai_id", "don_tour_online", ["tai_khoan_ngoai_id"])
    op.create_table(
        "thanh_toan_tour_online",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("don_id", sa.Integer(), sa.ForeignKey("don_tour_online.id"), nullable=False),
        sa.Column("kenh", sa.String(8), nullable=False),
        sa.Column("ma_gd", sa.String(40), nullable=False),
        sa.Column("so_tien", sa.Numeric(18, 2), nullable=False),
        sa.Column("trang_thai", sa.String(12), nullable=False),
        sa.Column("so_gd_cong", sa.String(60), nullable=False, server_default=""),
        sa.Column("ket_qua", sa.String(40), nullable=False, server_default=""),
        sa.Column("receipt_id", sa.Integer(), nullable=True),
        sa.Column("ghi_chu", sa.String(300), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_thanh_toan_tour_online_don_id", "thanh_toan_tour_online", ["don_id"])
    op.create_index("ix_thanh_toan_tour_online_ma_gd", "thanh_toan_tour_online", ["ma_gd"])


def downgrade() -> None:
    op.drop_table("thanh_toan_tour_online")
    op.drop_table("don_tour_online")
    with op.batch_alter_table("products") as b:
        for c in ("noi_dung_web", "link_web", "mo_thanh_toan", "phuong_tien_ds", "wellness", "noi_bat", "diem_den"):
            b.drop_column(c)
