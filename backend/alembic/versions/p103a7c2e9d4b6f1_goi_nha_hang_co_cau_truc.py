"""P1-03 · gói nhà hàng có điều kiện cấu trúc + luồng đặt bàn 4 bước

Revision ID: p103a7c2e9d4b6f1
Revises: mn3b7d9f1a2c4e57
Create Date: 2026-11-09

Chủ tịch duyệt bản xem trước 09/11/2026. Thêm vào `thuc_don_nha_hang`: khung giờ, số khách tối đa,
tuổi tính giá trẻ em, phụ thu có số, hạn nhà hàng trả lời, cọc mỗi khách (gói gọi món).
Thêm vào `don_dat_ban`: phụ thu đã tính, tuổi từng trẻ, hạn nhà hàng trả lời.
Mọi cột mới để trống được: gói / đơn cũ giữ nguyên cách bán như trước.
"""
import sqlalchemy as sa
from alembic import op

revision = "p103a7c2e9d4b6f1"
down_revision = "mn3b7d9f1a2c4e57"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("thuc_don_nha_hang", sa.Column("gio_tu", sa.String(length=5), nullable=False, server_default=""))
    op.add_column("thuc_don_nha_hang", sa.Column("gio_den", sa.String(length=5), nullable=False, server_default=""))
    op.add_column("thuc_don_nha_hang", sa.Column("so_khach_toi_da", sa.Integer(), nullable=True))
    op.add_column("thuc_don_nha_hang", sa.Column("tuoi_te_tu", sa.Integer(), nullable=True))
    op.add_column("thuc_don_nha_hang", sa.Column("tuoi_te_den", sa.Integer(), nullable=True))
    op.add_column("thuc_don_nha_hang", sa.Column("phu_thu", sa.JSON(), nullable=True))
    op.add_column("thuc_don_nha_hang", sa.Column("han_phan_hoi_gio", sa.Integer(), nullable=True))
    op.add_column("thuc_don_nha_hang", sa.Column("coc_moi_khach", sa.Numeric(18, 2), nullable=True))
    op.add_column("don_dat_ban", sa.Column("phu_thu", sa.JSON(), nullable=True))
    op.add_column("don_dat_ban", sa.Column("tuoi_tre", sa.JSON(), nullable=True))
    op.add_column("don_dat_ban", sa.Column("han_phan_hoi", sa.DateTime(), nullable=True))


def downgrade():
    for c in ("han_phan_hoi", "tuoi_tre", "phu_thu"):
        op.drop_column("don_dat_ban", c)
    for c in ("coc_moi_khach", "han_phan_hoi_gio", "phu_thu", "tuoi_te_den", "tuoi_te_tu", "so_khach_toi_da", "gio_den", "gio_tu"):
        op.drop_column("thuc_don_nha_hang", c)
