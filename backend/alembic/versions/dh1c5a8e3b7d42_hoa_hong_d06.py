"""DH-1 — hoa hồng đối tác bán hàng theo D06: hình thức, kỳ, sổ chỉ ghi thêm, chi.

Revision ID: dh1c5a8e3b7d42
Revises: cg1b7e2d4a9f15
Create Date: 2026-10-26

Bốn bảng MỚI. Không đụng `bookings` hay `doi_tac_ban_hang`: nguồn doanh số đọc thẳng từ booking,
hình thức hưởng nằm ở bảng riêng có hiệu lực theo tháng.
"""
import sqlalchemy as sa
from alembic import op

revision = "dh1c5a8e3b7d42"
down_revision = "cg1b7e2d4a9f15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hinh_thuc_hoa_hong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=False, index=True),
        sa.Column("hinh_thuc", sa.String(length=20), nullable=False),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "ky_hoa_hong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi_tac_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=False, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("company_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ky", sa.String(length=7), nullable=False, index=True),
        sa.Column("chuong_trinh", sa.String(length=20), nullable=False),
        sa.Column("doanh_so", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("co_ban", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("thuong", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="mo"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thu", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("chot_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("chot_luc", sa.DateTime(), nullable=True),
        sa.Column("tinh_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("doi_tac_id", "company_key", "ky", "chuong_trinh", name="uq_ky_hoa_hong"),
    )
    op.create_table(
        "so_hoa_hong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky_id", sa.Integer(), sa.ForeignKey("ky_hoa_hong.id"), nullable=False, index=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("thanh_phan", sa.String(length=10), nullable=False),
        sa.Column("so_tien", sa.BigInteger(), nullable=False),
        sa.Column("doanh_so", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sau_chot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nguon", sa.Text(), nullable=False, server_default=""),
        sa.Column("ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "chi_hoa_hong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky_id", sa.Integer(), sa.ForeignKey("ky_hoa_hong.id"), nullable=False, index=True),
        sa.Column("payment_request_id", sa.Integer(), sa.ForeignKey("payment_requests.id"), nullable=False, unique=True),
        sa.Column("so_tien", sa.BigInteger(), nullable=False),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chi_hoa_hong")
    op.drop_table("so_hoa_hong")
    op.drop_table("ky_hoa_hong")
    op.drop_table("hinh_thuc_hoa_hong")
