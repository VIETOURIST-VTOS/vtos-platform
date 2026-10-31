"""KS-16f — Video khách sạn VTD và nhà hàng (Chủ tịch duyệt 31/10/2026). Bảng mới, rỗng.

Revision ID: ks16fb7c9d1e3a5f2
Revises: ks16ea3c5e7f9b104
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16fb7c9d1e3a5f2"
down_revision = "ks16ea3c5e7f9b104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_dich_vu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi_tuong", sa.String(20), nullable=False),
        sa.Column("doi_tuong_id", sa.Integer(), nullable=False),
        sa.Column("loai", sa.String(16), nullable=False, server_default="khac"),
        sa.Column("loai_phong_id", sa.Integer(), sa.ForeignKey("loai_phong_vtd.id"), nullable=True),
        sa.Column("mon_id", sa.Integer(), sa.ForeignKey("mon_nha_hang.id"), nullable=True),
        sa.Column("thuc_don_id", sa.Integer(), sa.ForeignKey("thuc_don_nha_hang.id"), nullable=True),
        sa.Column("tieu_de", sa.String(160), nullable=False, server_default=""),
        sa.Column("nguon", sa.String(200), nullable=False, server_default=""),
        sa.Column("xac_nhan_quyen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ten_tep", sa.String(200), nullable=False, server_default=""),
        sa.Column("kieu", sa.String(40), nullable=False, server_default="video/mp4"),
        sa.Column("kich_thuoc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thoi_luong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("khoa_luu", sa.String(200), nullable=False, server_default=""),
        sa.Column("ma_tai", sa.String(300), nullable=False, server_default=""),
        sa.Column("phan", sa.JSON(), nullable=True),
        sa.Column("anh_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("la_gioi_thieu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trang_thai", sa.String(10), nullable=False, server_default="dang_tai"),
        sa.Column("tai_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tai_luc", sa.DateTime(), nullable=True),
        sa.Column("xong_luc", sa.DateTime(), nullable=True),
        sa.Column("an_boi", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index("ix_video_dich_vu_doi_tuong", "video_dich_vu", ["doi_tuong"])
    op.create_index("ix_video_dich_vu_doi_tuong_id", "video_dich_vu", ["doi_tuong_id"])
    op.create_index("ix_video_dich_vu_trang_thai", "video_dich_vu", ["trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_video_dich_vu_trang_thai", "video_dich_vu")
    op.drop_index("ix_video_dich_vu_doi_tuong_id", "video_dich_vu")
    op.drop_index("ix_video_dich_vu_doi_tuong", "video_dich_vu")
    op.drop_table("video_dich_vu")
