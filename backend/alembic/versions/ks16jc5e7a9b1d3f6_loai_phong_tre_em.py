"""KS-16j — Loại phòng: mô tả dài, tiện nghi, trẻ em «chưa xác nhận», giường phụ, nguồn & đối chiếu;
chính sách trẻ em kiểu Agoda ở khách sạn (Chủ tịch duyệt bản xem thử 01/11/2026).

toi_da_tre_em cho phép NULL. Số 0 cũ không phân biệt được «không nhận» với «để trống» (máy cũ đổi trống thành 0),
nên mọi số 0 cũ chuyển thành NULL = chưa xác nhận; Điều hành xác nhận lại.

Revision ID: ks16jc5e7a9b1d3f6
Revises: ks16hb3e5a7c9d1f4
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16jc5e7a9b1d3f6"
down_revision = "ks16hb3e5a7c9d1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("loai_phong_vtd") as b:
        b.add_column(sa.Column("mo_ta_dai", sa.Text(), nullable=False, server_default=""))
        b.add_column(sa.Column("tien_nghi", sa.JSON(), nullable=True))
        b.add_column(sa.Column("giuong_phu_toi_da", sa.Integer(), nullable=True))
        b.add_column(sa.Column("noi_cui", sa.Boolean(), nullable=True))
        b.add_column(sa.Column("nguon", sa.String(12), nullable=False, server_default=""))
        b.add_column(sa.Column("ky_doi_chieu", sa.String(120), nullable=False, server_default=""))
        b.add_column(sa.Column("ma_hang", sa.String(80), nullable=False, server_default=""))
        b.add_column(sa.Column("ten_tuong_duong", sa.String(160), nullable=False, server_default=""))
        b.add_column(sa.Column("can_xac_nhan", sa.JSON(), nullable=True))
        b.add_column(sa.Column("ghi_chu_doi_chieu", sa.String(500), nullable=False, server_default=""))
        b.add_column(sa.Column("trang_thai_dc", sa.String(14), nullable=False, server_default=""))
        b.alter_column("toi_da_tre_em", existing_type=sa.Integer(), nullable=True, server_default=None)
    op.execute("UPDATE loai_phong_vtd SET toi_da_tre_em = NULL WHERE toi_da_tre_em = 0")
    with op.batch_alter_table("khach_san_vtd") as b:
        b.add_column(sa.Column("cs_nhan_tre_em", sa.String(14), nullable=False, server_default="chua_xac_nhan"))
        b.add_column(sa.Column("cs_tre_tu_tuoi", sa.Integer(), nullable=True))
        b.add_column(sa.Column("cs_moc_tuoi", sa.JSON(), nullable=True))
        b.add_column(sa.Column("cs_phi_giuong_phu", sa.Numeric(18, 2), nullable=True))
        b.add_column(sa.Column("cs_giuong_phu_an_sang", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("cs_noi", sa.String(120), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("khach_san_vtd") as b:
        for c in ("cs_noi", "cs_giuong_phu_an_sang", "cs_phi_giuong_phu", "cs_moc_tuoi", "cs_tre_tu_tuoi", "cs_nhan_tre_em"):
            b.drop_column(c)
    op.execute("UPDATE loai_phong_vtd SET toi_da_tre_em = 0 WHERE toi_da_tre_em IS NULL")
    with op.batch_alter_table("loai_phong_vtd") as b:
        b.alter_column("toi_da_tre_em", existing_type=sa.Integer(), nullable=False)
        for c in ("trang_thai_dc", "ghi_chu_doi_chieu", "can_xac_nhan", "ten_tuong_duong", "ma_hang", "ky_doi_chieu",
                  "nguon", "noi_cui", "giuong_phu_toi_da", "tien_nghi", "mo_ta_dai"):
            b.drop_column(c)
