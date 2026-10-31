"""KS-16k — Chính sách trẻ em theo cách Agoda YCS (Chủ tịch duyệt bản xem thử 01/11/2026): số trẻ miễn phí, giá giường
phụ cố định / %, sức chứa cơ bản + khách thêm, ghi đè giá trẻ em theo loại phòng và gói giá. Chỉ thêm cột.

Revision ID: ks16kd7f9b1c3e5a8
Revises: ks16jc5e7a9b1d3f6
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16kd7f9b1c3e5a8"
down_revision = "ks16jc5e7a9b1d3f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("khach_san_vtd") as b:
        b.add_column(sa.Column("cs_so_tre_mien_phi", sa.Integer(), nullable=True))
        b.add_column(sa.Column("cs_tre_mp_tinh_suc_chua", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("cs_giuong_phu_kieu", sa.String(10), nullable=False, server_default="co_dinh"))
    with op.batch_alter_table("loai_phong_vtd") as b:
        b.add_column(sa.Column("suc_chua", sa.Integer(), nullable=True))
        b.add_column(sa.Column("khach_them_toi_da", sa.Integer(), nullable=True))
        b.add_column(sa.Column("so_tre_mien_phi", sa.Integer(), nullable=True))
        b.add_column(sa.Column("phi_giuong_phu", sa.Numeric(18, 2), nullable=True))
        b.add_column(sa.Column("giuong_phu_kieu", sa.String(10), nullable=False, server_default=""))
        b.add_column(sa.Column("giuong_phu_xac_nhan", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("gia_tre_rieng", sa.JSON(), nullable=True))
    with op.batch_alter_table("goi_gia_vtd") as b:
        b.add_column(sa.Column("tre_em_che_do", sa.String(14), nullable=False, server_default=""))
        b.add_column(sa.Column("gia_tre", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("goi_gia_vtd") as b:
        b.drop_column("gia_tre")
        b.drop_column("tre_em_che_do")
    with op.batch_alter_table("loai_phong_vtd") as b:
        for c in ("gia_tre_rieng", "giuong_phu_xac_nhan", "giuong_phu_kieu", "phi_giuong_phu", "so_tre_mien_phi",
                  "khach_them_toi_da", "suc_chua"):
            b.drop_column(c)
    with op.batch_alter_table("khach_san_vtd") as b:
        for c in ("cs_giuong_phu_kieu", "cs_tre_mp_tinh_suc_chua", "cs_so_tre_mien_phi"):
            b.drop_column(c)
