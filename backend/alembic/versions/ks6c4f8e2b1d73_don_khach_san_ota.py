"""KS-6 — hai bảng đơn khách sạn theo đúng các bước của Agoda Demand API.

`don_khach_san_ota` mang đủ chuỗi mã của sáu bước (searchId → blockId → tag → bookingId →
reference), `buoc_don_ota` ghi lại từng lần gọi kể cả lần quá hạn.

Không có cột nào nhận số thẻ: mô hình đã chọn là Fulfill Assisted, Agoda thu tiền khách.
Không có cột nào chép `totalPayment`: tài liệu Book API cấm dùng con số ấy để đặt.

Mọi mã của Agoda là BigInteger — trang Content API nói mọi định danh phải lưu bằng số 64 bit,
và `searchId` mẫu (633141408144250000) vượt 32 bit.

Revision ID: ks6c4f8e2b1d73
"""
import sqlalchemy as sa
from alembic import op

revision = "ks6c4f8e2b1d73"
down_revision = "ks5b3e7d1a9c42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "don_khach_san_ota",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("the_tham_chieu", sa.String(length=50), nullable=False),
        sa.Column("ota_id", sa.Integer(), sa.ForeignKey("doi_tac_ota.id"), nullable=False),
        sa.Column("moi_truong", sa.String(length=8), nullable=False, server_default="tat"),
        sa.Column("trang_thai", sa.String(length=16), nullable=False, server_default="moi"),
        sa.Column("trang_thai_nguon", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("ma_tim", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tim_luc", sa.DateTime(), nullable=True),
        sa.Column("ma_khoi", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("the_chao", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("ma_khach_san", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("ma_phong", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("ma_goi_gia", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("kieu_thanh_toan", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("ngay_nhan", sa.Date(), nullable=True),
        sa.Column("ngay_tra", sa.Date(), nullable=True),
        sa.Column("so_phong", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nguoi_lon", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tre_em", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tuoi_tre_em", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("nuoc_khach", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("ngon_ngu", sa.String(length=10), nullable=False, server_default="vi-vn"),
        sa.Column("tien_te", sa.String(length=3), nullable=False, server_default="VND"),
        sa.Column("gia_gom_thue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("phu_thu", sa.Text(), nullable=False, server_default=""),
        sa.Column("ma_don_nguon", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("ma_hanh_trinh", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("dang_xu_ly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dat_luc", sa.DateTime(), nullable=True),
        sa.Column("so_xac_nhan_ks", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tham_chieu_nguon", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tham_chieu_huy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ly_do_huy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hoan_gom_thue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("sua_boi", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    # Thẻ tham chiếu phải DUY NHẤT. Hai đơn cùng thẻ thì lúc tra Booking List không biết đơn nào
    # là đơn nào — đúng lúc cần biết nhất.
    op.create_unique_constraint("uq_don_ks_ota_the", "don_khach_san_ota", ["the_tham_chieu"])
    op.create_index("ix_don_ks_ota_trang_thai", "don_khach_san_ota", ["trang_thai"])
    op.create_index("ix_don_ks_ota_ota", "don_khach_san_ota", ["ota_id"])

    op.create_table(
        "buoc_don_ota",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("don_id", sa.BigInteger(), sa.ForeignKey("don_khach_san_ota.id"), nullable=False),
        sa.Column("buoc", sa.String(length=16), nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("ma_tra_ve", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qua_han", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tom_tat", sa.Text(), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=80), nullable=False, server_default=""),
    )
    op.create_index("ix_buoc_don_ota_don", "buoc_don_ota", ["don_id"])


def downgrade() -> None:
    op.drop_index("ix_buoc_don_ota_don", table_name="buoc_don_ota")
    op.drop_table("buoc_don_ota")
    op.drop_index("ix_don_ks_ota_ota", table_name="don_khach_san_ota")
    op.drop_index("ix_don_ks_ota_trang_thai", table_name="don_khach_san_ota")
    op.drop_constraint("uq_don_ks_ota_the", "don_khach_san_ota", type_="unique")
    op.drop_table("don_khach_san_ota")
