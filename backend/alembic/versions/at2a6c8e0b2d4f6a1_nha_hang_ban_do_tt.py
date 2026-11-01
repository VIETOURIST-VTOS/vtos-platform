"""AT-2 — nhà hàng kiểu Agoda: tọa độ (bản đồ) + công tắc mở thanh toán từng nhà hàng (Chủ tịch duyệt bản xem thử
01/11/2026). Công tắc chung dùng bảng cai_dat_ks_vtd sẵn có (khóa mo_thanh_toan_nha_hang). Chỉ thêm cột.

Revision ID: at2a6c8e0b2d4f6a1
Revises: ks16sf1b3d5a7c9e2
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "at2a6c8e0b2d4f6a1"
down_revision = "ks16sf1b3d5a7c9e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nha_hang") as b:
        b.add_column(sa.Column("vi_do", sa.Float(), nullable=True))
        b.add_column(sa.Column("kinh_do", sa.Float(), nullable=True))
        b.add_column(sa.Column("toa_do_nguon", sa.String(12), nullable=False, server_default=""))
        b.add_column(sa.Column("mo_thanh_toan", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("nha_hang") as b:
        for c in ("mo_thanh_toan", "toa_do_nguon", "kinh_do", "vi_do"):
            b.drop_column(c)
