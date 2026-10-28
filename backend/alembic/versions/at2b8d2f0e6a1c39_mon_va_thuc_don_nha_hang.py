"""AT-2b — Món ăn và thực đơn nhà hàng (phiên bản), Chủ tịch chốt 29/10/2026.

Revision ID: at2b8d2f0e6a1c39
Revises: at2a7c1e9d4b58
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "at2b8d2f0e6a1c39"
down_revision = "at2a7c1e9d4b58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mon_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("ten_khac", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("nhom", sa.String(length=20), nullable=False, server_default="mon_chinh"),
        sa.Column("mo_ta", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("di_ung", sa.JSON(), nullable=True),
        sa.Column("cay", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("chay", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("anh_id", sa.Integer(), sa.ForeignKey("anh_nha_hang.id"), nullable=True),
        sa.Column("noi_bat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="nhap"),
        sa.Column("ly_do_tra_lai", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mon_nha_hang_nha_hang_id", "mon_nha_hang", ["nha_hang_id"])
    op.create_table(
        "thuc_don_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False),
        sa.Column("loai", sa.String(length=20), nullable=False),
        sa.Column("so", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        sa.Column("can_cu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("so_trang", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="cho_duyet"),
        sa.Column("ly_do_tra_lai", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("tai_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tai_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_thuc_don_ban_nha_hang_id", "thuc_don_ban", ["nha_hang_id"])
    op.create_table(
        "thuc_don_trang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ban_id", sa.Integer(), sa.ForeignKey("thuc_don_ban.id"), nullable=False),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("hien_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("nho_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
    )
    op.create_index("ix_thuc_don_trang_ban_id", "thuc_don_trang", ["ban_id"])


def downgrade() -> None:
    op.drop_index("ix_thuc_don_trang_ban_id", table_name="thuc_don_trang")
    op.drop_table("thuc_don_trang")
    op.drop_index("ix_thuc_don_ban_nha_hang_id", table_name="thuc_don_ban")
    op.drop_table("thuc_don_ban")
    op.drop_index("ix_mon_nha_hang_nha_hang_id", table_name="mon_nha_hang")
    op.drop_table("mon_nha_hang")
