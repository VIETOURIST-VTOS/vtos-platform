"""AT-1 — Khám phá ẩm thực: nguồn danh sách, xác minh, hợp đồng nhà hàng, nội dung + ảnh, điểm thưởng đặt bàn.

Revision ID: at1d6f8b0c3e57
Revises: dt3c5e7a9b2d46
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "at1d6f8b0c3e57"
down_revision = "dt3c5e7a9b2d46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nha_hang", sa.Column("nguon", sa.String(length=60), nullable=False, server_default=""))
    op.add_column("nha_hang", sa.Column("nguon_ref", sa.String(length=300), nullable=False, server_default=""))
    op.add_column("nha_hang", sa.Column("dia_danh_nguon", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("nha_hang", sa.Column("mon_noi_bat", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("nha_hang", sa.Column("lien_he_xac_minh", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("nha_hang", sa.Column("xac_minh_boi", sa.String(length=50), nullable=False, server_default=""))
    op.add_column("nha_hang", sa.Column("xac_minh_luc", sa.DateTime(), nullable=True))
    op.add_column("nha_hang", sa.Column("anh_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True))
    op.add_column("nha_hang", sa.Column("anh_nguon", sa.String(length=200), nullable=False, server_default=""))
    op.create_table(
        "hop_dong_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("so_hd", sa.String(length=80), nullable=False),
        sa.Column("ngay_ky", sa.Date(), nullable=False),
        sa.Column("tu_ngay", sa.Date(), nullable=False),
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("hoa_hong_bps", sa.Integer(), nullable=True),
        sa.Column("hoa_hong_co_dinh", sa.Integer(), nullable=True),
        sa.Column("co_so_hoa_hong", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("thay_cho_id", sa.Integer(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("con_dung", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ghi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ghi_luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_hop_dong_nha_hang_nha_hang_id", "hop_dong_nha_hang", ["nha_hang_id"])
    op.create_table(
        "noi_dung_am_thuc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(length=12), nullable=False),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("ten_khac", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("nhom", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("tinh_thanh", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("tom_tat", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("vung", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("nen_an", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("thanh_phan", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("cach_goi", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("nha_hang_ids", sa.JSON(), nullable=True),
        sa.Column("anh_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("anh_nguon", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hien", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )


    op.add_column("so_diem_rewards", sa.Column("dat_ban_id", sa.Integer(), sa.ForeignKey("don_dat_ban.id"), nullable=True))
    op.create_index("ix_so_diem_rewards_dat_ban_id", "so_diem_rewards", ["dat_ban_id"])


def downgrade() -> None:
    op.drop_index("ix_so_diem_rewards_dat_ban_id", table_name="so_diem_rewards")
    op.drop_column("so_diem_rewards", "dat_ban_id")
    op.drop_table("noi_dung_am_thuc")
    op.drop_index("ix_hop_dong_nha_hang_nha_hang_id", table_name="hop_dong_nha_hang")
    op.drop_table("hop_dong_nha_hang")
    for c in ("anh_nguon", "anh_id", "xac_minh_luc", "xac_minh_boi", "lien_he_xac_minh", "mon_noi_bat", "dia_danh_nguon", "nguon_ref", "nguon"):
        op.drop_column("nha_hang", c)
