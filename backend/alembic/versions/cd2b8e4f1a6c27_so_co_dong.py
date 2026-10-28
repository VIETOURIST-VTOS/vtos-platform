"""CD-2 — sổ cổ đông: lô danh sách VSD (Chủ tịch duyệt), dòng sổ, nối tài khoản; tệp kèm yêu cầu IR.

Revision ID: cd2b8e4f1a6c27
Revises: vb1d2f4a6c8e13
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "cd2b8e4f1a6c27"
down_revision = "vb1d2f4a6c8e13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lo_so_co_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=12), nullable=False, unique=True, index=True),
        sa.Column("ngay_can_cu", sa.Date(), nullable=False, index=True),
        sa.Column("ten_tep", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("bam_tep", sa.String(length=64), nullable=False, index=True),
        sa.Column("trang_thai", sa.String(length=10), nullable=False, server_default="cho_duyet", index=True),
        sa.Column("so_dong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tong_cp", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("loi", sa.JSON(), nullable=True),
        sa.Column("nap_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nap_luc", sa.DateTime(), nullable=False),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "dong_so_co_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lo_id", sa.Integer(), sa.ForeignKey("lo_so_co_dong.id"), nullable=False, index=True),
        sa.Column("ho_ten", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("giay_to", sa.String(length=40), nullable=False),
        sa.Column("so_cp", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tk_luu_ky", sa.String(length=40), nullable=False, server_default=""),
    )
    op.create_index("ix_dong_so_co_dong_lo_gt", "dong_so_co_dong", ["lo_id", "giay_to"])
    op.create_table(
        "noi_so_co_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("giay_to", sa.String(length=40), nullable=False, index=True),
        sa.Column("noi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("noi_luc", sa.DateTime(), nullable=False),
        sa.Column("go_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("go_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_go", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column("yeu_cau_ir", sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("yeu_cau_ir", "attachment_id")
    op.drop_table("noi_so_co_dong")
    op.drop_index("ix_dong_so_co_dong_lo_gt", table_name="dong_so_co_dong")
    op.drop_table("dong_so_co_dong")
    op.drop_table("lo_so_co_dong")
