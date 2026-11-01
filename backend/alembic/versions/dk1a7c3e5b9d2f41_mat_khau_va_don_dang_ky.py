"""DK-1: mat khau tai khoan ngoai + bang don_dang_ky

Chu tich chot 01/11/2026: mat khau bat buoc khi tao tai khoan, ma mot lan xuong buoc cuoi.
Ba buoc truoc do phai co cho dung ma chua co tai khoan -> bang `don_dang_ky`, het han 24 gio.

Revision ID: dk1a7c3e5b9d2f41
"""
from alembic import op
import sqlalchemy as sa

revision = "dk1a7c3e5b9d2f41"
down_revision = "tr1b7d9f1a3c5e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tai_khoan_ngoai",
                  sa.Column("mat_khau_bam", sa.String(255), nullable=False, server_default=""))
    op.create_table(
        "don_dang_ky",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("khoa", sa.String(64), nullable=False),
        sa.Column("loai", sa.String(20), nullable=False),
        sa.Column("ho_ten", sa.String(160), nullable=False, server_default=""),
        sa.Column("dien_thoai", sa.String(20), nullable=False, server_default=""),
        sa.Column("email", sa.String(160), nullable=False, server_default=""),
        sa.Column("mat_khau_bam", sa.String(255), nullable=False, server_default=""),
        sa.Column("ma_khoa", sa.String(64), nullable=False, server_default=""),
        sa.Column("dong_y_dieu_khoan_luc", sa.DateTime, nullable=True),
        sa.Column("nhan_tin_quang_cao", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("het_han", sa.DateTime, nullable=False),
        sa.Column("tao_luc", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_don_dang_ky_khoa", "don_dang_ky", ["khoa"], unique=True)
    op.create_index("ix_don_dang_ky_het_han", "don_dang_ky", ["het_han"])


def downgrade():
    op.drop_index("ix_don_dang_ky_het_han", table_name="don_dang_ky")
    op.drop_index("ix_don_dang_ky_khoa", table_name="don_dang_ky")
    op.drop_table("don_dang_ky")
    op.drop_column("tai_khoan_ngoai", "mat_khau_bam")
