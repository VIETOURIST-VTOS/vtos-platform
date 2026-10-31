"""KS-16h — Nguồn đơn CTV, D06 theo v3, đối soát đối tác (Chủ tịch duyệt bản xem thử 31/10/2026). Chỉ thêm cột / bảng.

Revision ID: ks16hb3e5a7c9d1f4
Revises: ks16gd2f4a6c8e0b3
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16hb3e5a7c9d1f4"
down_revision = "ks16gd2f4a6c8e0b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nguon_don",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khach_sdt", sa.String(20), nullable=False),
        sa.Column("khach_ten", sa.String(120), nullable=False, server_default=""),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=False),
        sa.Column("loai", sa.String(12), nullable=False),
        sa.Column("tu", sa.DateTime(), nullable=False),
        sa.Column("den", sa.DateTime(), nullable=False),
        sa.Column("trang_thai", sa.String(10), nullable=False, server_default="giu"),
        sa.Column("ly_do", sa.String(300), nullable=False, server_default=""),
        sa.Column("yeu_cau_id", sa.Integer(), nullable=True),
        sa.Column("chinh_sach", sa.String(20), nullable=False, server_default="v3-31/10/2026"),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_nguon_don_khach_sdt", "nguon_don", ["khach_sdt"])
    op.create_index("ix_nguon_don_doi_tac_id", "nguon_don", ["doi_tac_id"])
    op.create_table(
        "bang_doi_soat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=False),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("gui_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("gui_luc", sa.DateTime(), nullable=False),
        sa.Column("han_phan_hoi", sa.Date(), nullable=False),
        sa.Column("han_tra", sa.Date(), nullable=False),
        sa.Column("phan_hoi_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("doi_tac_id", "ky", name="uq_bang_doi_soat"),
    )
    op.create_index("ix_bang_doi_soat_doi_tac_id", "bang_doi_soat", ["doi_tac_id"])
    op.create_index("ix_bang_doi_soat_ky", "bang_doi_soat", ["ky"])
    op.create_table(
        "dong_doi_soat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bang_id", sa.Integer(), sa.ForeignKey("bang_doi_soat.id"), nullable=False),
        sa.Column("ma_don", sa.String(30), nullable=False),
        sa.Column("ten", sa.String(200), nullable=False, server_default=""),
        sa.Column("doanh_so", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("hoa_hong", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("y_kien", sa.String(12), nullable=False, server_default=""),
        sa.Column("y_kien_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dong_doi_soat_bang_id", "dong_doi_soat", ["bang_id"])
    op.create_table(
        "vu_viec_doi_tac",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(20), nullable=False, unique=True),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=False),
        sa.Column("loai", sa.String(12), nullable=False),
        sa.Column("booking_ma", sa.String(30), nullable=False, server_default=""),
        sa.Column("khach_sdt", sa.String(20), nullable=False, server_default=""),
        sa.Column("dong_doi_soat_id", sa.Integer(), sa.ForeignKey("dong_doi_soat.id"), nullable=True),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(10), nullable=False, server_default="mo"),
        sa.Column("han", sa.Date(), nullable=False),
        sa.Column("ket_qua", sa.String(500), nullable=False, server_default=""),
        sa.Column("xu_ly_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_vu_viec_doi_tac_doi_tac_id", "vu_viec_doi_tac", ["doi_tac_id"])
    op.create_index("ix_vu_viec_doi_tac_trang_thai", "vu_viec_doi_tac", ["trang_thai"])
    with op.batch_alter_table("tours") as b:
        b.add_column(sa.Column("d06_phu_luc", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("vat_pct", sa.Float(), nullable=False, server_default="8"))
    with op.batch_alter_table("bookings") as b:
        b.add_column(sa.Column("nguon_don_id", sa.Integer(), nullable=True))
        b.create_foreign_key("fk_bookings_nguon_don", "nguon_don", ["nguon_don_id"], ["id"])
        b.create_index("ix_bookings_nguon_don_id", ["nguon_don_id"])


def downgrade() -> None:
    with op.batch_alter_table("bookings") as b:
        b.drop_index("ix_bookings_nguon_don_id")
        b.drop_constraint("fk_bookings_nguon_don", type_="foreignkey")
        b.drop_column("nguon_don_id")
    with op.batch_alter_table("tours") as b:
        b.drop_column("vat_pct")
        b.drop_column("d06_phu_luc")
    for t in ("vu_viec_doi_tac", "dong_doi_soat", "bang_doi_soat", "nguon_don"):
        op.drop_table(t)
