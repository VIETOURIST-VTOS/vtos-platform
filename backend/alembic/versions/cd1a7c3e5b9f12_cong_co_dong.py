"""CD-1 — cổng cổ đông đợt 1: tài liệu trên cổng, sự kiện, quan tâm sự kiện, yêu cầu IR.

Revision ID: cd1a7c3e5b9f12
Revises: ks2c6e8a1b3d49
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "cd1a7c3e5b9f12"
down_revision = "ks2c6e8a1b3d49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tai_lieu_cong_co_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ban_ghi_id", sa.Integer(), sa.ForeignKey("ban_ghi_cong_bo.id"), nullable=False, index=True),
        sa.Column("tieu_de", sa.String(length=300), nullable=False),
        sa.Column("nhom", sa.String(length=20), nullable=False, server_default="khac"),
        sa.Column("pham_vi", sa.String(length=12), nullable=False, server_default="co_dong"),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("thay_cho_id", sa.Integer(), nullable=True, index=True),
        sa.Column("ly_do_thay", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="hien"),
        sa.Column("dang_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("dang_luc", sa.DateTime(), nullable=False),
        sa.Column("go_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("go_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_go", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_tai_lieu_cong_co_dong_tt_pv", "tai_lieu_cong_co_dong", ["trang_thai", "pham_vi"])
    op.create_table(
        "su_kien_co_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("loai", sa.String(length=20), nullable=False, server_default="gap_go"),
        sa.Column("bat_dau", sa.DateTime(), nullable=False, index=True),
        sa.Column("dia_diem", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ngay_chot_ds", sa.Date(), nullable=True),
        sa.Column("mo_ta", sa.Text(), nullable=False, server_default=""),
        sa.Column("tai_lieu_ids", sa.JSON(), nullable=True),
        sa.Column("nhan_quan_tam", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="nhap", index=True),
        sa.Column("ly_do_huy", sa.Text(), nullable=False, server_default=""),
        sa.Column("tao_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "quan_tam_su_kien",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("su_kien_id", sa.Integer(), sa.ForeignKey("su_kien_co_dong.id"), nullable=False, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("luc", sa.DateTime(), nullable=False),
        sa.Column("bo_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("su_kien_id", "tai_khoan_id", name="uq_quan_tam_su_kien"),
    )
    op.create_table(
        "yeu_cau_ir",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=12), nullable=False, unique=True, index=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("chu_de", sa.String(length=12), nullable=False, server_default="khac"),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="cho", index=True),
        sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("xac_nhan_da_cong_bo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tra_loi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tra_loi_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_dong", sa.Text(), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("yeu_cau_ir")
    op.drop_table("quan_tam_su_kien")
    op.drop_table("su_kien_co_dong")
    op.drop_index("ix_tai_lieu_cong_co_dong_tt_pv", table_name="tai_lieu_cong_co_dong")
    op.drop_table("tai_lieu_cong_co_dong")
