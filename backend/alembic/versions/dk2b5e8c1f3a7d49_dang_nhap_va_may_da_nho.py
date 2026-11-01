"""DK-2: dang nhap bang mat khau + bang may_da_nho

Ve sau cua dieu 6 (Chu tich chot 01/11/2026): mat khau ngan thi may phai quen.
Them phanh dang nhap THEO TAI KHOAN, va bang `may_da_nho` giu danh sach may da xac minh.

Revision ID: dk2b5e8c1f3a7d49
"""
from alembic import op
import sqlalchemy as sa

revision = "dk2b5e8c1f3a7d49"
down_revision = "dk1a7c3e5b9d2f41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tai_khoan_ngoai",
                  sa.Column("dn_sai", sa.Integer, nullable=False, server_default="0"))
    op.add_column("tai_khoan_ngoai", sa.Column("dn_khoa_den", sa.DateTime, nullable=True))
    op.create_table(
        "may_da_nho",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tai_khoan_id", sa.Integer,
                  sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("dau_bam", sa.String(64), nullable=False),
        sa.Column("ten_may", sa.String(80), nullable=False, server_default=""),
        sa.Column("ip_cuoi", sa.String(64), nullable=False, server_default=""),
        sa.Column("dung_cuoi", sa.DateTime, nullable=True),
        sa.Column("het_han", sa.DateTime, nullable=False),
        sa.Column("tao_luc", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_may_da_nho_tai_khoan_id", "may_da_nho", ["tai_khoan_id"])
    op.create_index("ix_may_da_nho_dau_bam", "may_da_nho", ["dau_bam"])
    op.create_index("ix_may_da_nho_het_han", "may_da_nho", ["het_han"])


def downgrade():
    op.drop_index("ix_may_da_nho_het_han", table_name="may_da_nho")
    op.drop_index("ix_may_da_nho_dau_bam", table_name="may_da_nho")
    op.drop_index("ix_may_da_nho_tai_khoan_id", table_name="may_da_nho")
    op.drop_table("may_da_nho")
    op.drop_column("tai_khoan_ngoai", "dn_khoa_den")
    op.drop_column("tai_khoan_ngoai", "dn_sai")
