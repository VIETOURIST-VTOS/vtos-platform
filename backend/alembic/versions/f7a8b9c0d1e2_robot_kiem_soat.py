"""Robot Kiểm soát: bảng phát hiện, chấm điểm phòng ban, báo cáo gửi Chủ tịch.

Revision ID: f7a8b9c0d1e2
Revises: a7c3e91d5b42
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "a7c3e91d5b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ks_phat_hien",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ma", sa.String(160), nullable=False),
        sa.Column("loai", sa.String(24), nullable=False),
        sa.Column("muc", sa.String(6), nullable=False, server_default="vang"),
        sa.Column("phong_ban", sa.String(60), nullable=False, server_default=""),
        sa.Column("vai_tro", sa.String(30), nullable=False, server_default=""),
        sa.Column("doi_tuong", sa.String(120), nullable=False, server_default=""),
        sa.Column("tom_tat", sa.Text, nullable=False, server_default=""),
        sa.Column("chi_tiet", sa.JSON, nullable=True),
        sa.Column("lan_dau", sa.DateTime, nullable=True),
        sa.Column("lan_cuoi", sa.DateTime, nullable=True),
        sa.Column("so_lan", sa.Integer, nullable=False, server_default="1"),
        sa.Column("con", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("da_bao_cao", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_ks_phat_hien_ma", "ks_phat_hien", ["ma"], unique=True)
    op.create_index("ix_ks_phat_hien_loai", "ks_phat_hien", ["loai"])
    op.create_index("ix_ks_phat_hien_con", "ks_phat_hien", ["con"])

    op.create_table(
        "ks_diem",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("phong_ban", sa.String(60), nullable=False),
        sa.Column("diem", sa.Float, nullable=True),
        sa.Column("can_cu", sa.JSON, nullable=True),
        sa.Column("nhan_xet", sa.Text, nullable=False, server_default=""),
        sa.Column("du_co_so", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default="cho_hau_kiem"),
        sa.Column("hau_kiem_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("hau_kiem_luc", sa.DateTime, nullable=True),
        sa.Column("hau_kiem_ghi_chu", sa.String(400), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_ks_diem_ky", "ks_diem", ["ky"])
    op.create_index("ix_ks_diem_phong_ban", "ks_diem", ["phong_ban"])
    op.create_index("ix_ks_diem_trang_thai", "ks_diem", ["trang_thai"])

    op.create_table(
        "ks_bao_cao",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("luc", sa.DateTime, nullable=True),
        sa.Column("ly_do", sa.String(200), nullable=False, server_default=""),
        sa.Column("so_do", sa.Integer, nullable=False, server_default="0"),
        sa.Column("so_vang", sa.Integer, nullable=False, server_default="0"),
        sa.Column("noi_dung", sa.Text, nullable=False, server_default=""),
        sa.Column("ma_phat_hien", sa.JSON, nullable=True),
        sa.Column("da_xem", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("xem_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("xem_luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_ks_bao_cao_luc", "ks_bao_cao", ["luc"])


def downgrade() -> None:
    op.drop_index("ix_ks_bao_cao_luc", table_name="ks_bao_cao")
    op.drop_table("ks_bao_cao")
    for i in ("ix_ks_diem_trang_thai", "ix_ks_diem_phong_ban", "ix_ks_diem_ky"):
        op.drop_index(i, table_name="ks_diem")
    op.drop_table("ks_diem")
    for i in ("ix_ks_phat_hien_con", "ix_ks_phat_hien_loai", "ix_ks_phat_hien_ma"):
        op.drop_index(i, table_name="ks_phat_hien")
    op.drop_table("ks_phat_hien")
