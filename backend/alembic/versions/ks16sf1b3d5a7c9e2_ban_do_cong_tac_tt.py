"""KS-16s — tọa độ khách sạn (bản đồ), công tắc mở thanh toán (chung + từng khách sạn), giờ đến dự kiến
(Chủ tịch duyệt bản xem thử 01/11/2026). Chỉ thêm cột / thêm bảng.

Revision ID: ks16sf1b3d5a7c9e2
Revises: ks16pe9a1c3e5f7b2
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16sf1b3d5a7c9e2"
down_revision = "ks16pe9a1c3e5f7b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("khach_san_vtd") as b:
        b.add_column(sa.Column("vi_do", sa.Float(), nullable=True))
        b.add_column(sa.Column("kinh_do", sa.Float(), nullable=True))
        b.add_column(sa.Column("toa_do_nguon", sa.String(12), nullable=False, server_default=""))
        b.add_column(sa.Column("mo_thanh_toan", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("don_ks_vtd") as b:
        b.add_column(sa.Column("gio_den", sa.String(20), nullable=False, server_default=""))
    op.create_table("cai_dat_ks_vtd",
                    sa.Column("khoa", sa.String(40), primary_key=True),
                    sa.Column("gia_tri", sa.String(200), nullable=False, server_default=""),
                    sa.Column("sua_boi", sa.String(50), nullable=False, server_default=""),
                    sa.Column("sua_luc", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_table("cai_dat_ks_vtd")
    with op.batch_alter_table("don_ks_vtd") as b:
        b.drop_column("gio_den")
    with op.batch_alter_table("khach_san_vtd") as b:
        for c in ("mo_thanh_toan", "toa_do_nguon", "kinh_do", "vi_do"):
            b.drop_column(c)
