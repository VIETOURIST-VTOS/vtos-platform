"""CG-1 — cổng kết nối VTD: tài khoản bên ngoài và mã xác thực một lần.

Revision ID: cg1b7e2d4a9f15
Revises: bc2e4f8a1d7c93
Create Date: 2026-10-26

Hai bảng MỚI, không đụng `users`. Tài khoản khách hàng / đối tác / cổ đông tách hẳn khỏi tài khoản
nhân viên — xem docstring của app/models/cong_ngoai.py.
"""
import sqlalchemy as sa
from alembic import op

revision = "cg1b7e2d4a9f15"
down_revision = "bc2e4f8a1d7c93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tai_khoan_ngoai",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(length=20), nullable=False),
        sa.Column("ho_ten", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("dien_thoai", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="ho_so"),
        sa.Column("loai_doi_tac", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("ten_don_vi", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ma_so_thue", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("giay_to", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("tk_luu_ky", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("ghi_chu_ho_so", sa.Text(), nullable=False, server_default=""),
        sa.Column("gui_ho_so_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("dong_y_dieu_khoan_luc", sa.DateTime(), nullable=True),
        sa.Column("nhan_tin_quang_cao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("kenh_ua_thich", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("phien", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("dang_nhap_cuoi", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tkn_loai_dt", "tai_khoan_ngoai", ["loai", "dien_thoai"])
    op.create_index("ix_tkn_loai_email", "tai_khoan_ngoai", ["loai", "email"])
    op.create_table(
        "ma_xac_thuc_ngoai",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khoa", sa.String(length=48), nullable=False),
        sa.Column("loai", sa.String(length=20), nullable=False),
        sa.Column("kenh", sa.String(length=10), nullable=False),
        sa.Column("lien_he", sa.String(length=160), nullable=False),
        sa.Column("ma_bam", sa.String(length=64), nullable=False),
        sa.Column("het_han", sa.DateTime(), nullable=False),
        sa.Column("so_lan_sai", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("da_dung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ma_xac_thuc_ngoai_khoa", "ma_xac_thuc_ngoai", ["khoa"], unique=True)
    op.create_index("ix_ma_xac_thuc_ngoai_lien_he", "ma_xac_thuc_ngoai", ["lien_he"])


def downgrade() -> None:
    op.drop_index("ix_ma_xac_thuc_ngoai_lien_he", table_name="ma_xac_thuc_ngoai")
    op.drop_index("ix_ma_xac_thuc_ngoai_khoa", table_name="ma_xac_thuc_ngoai")
    op.drop_table("ma_xac_thuc_ngoai")
    op.drop_index("ix_tkn_loai_email", table_name="tai_khoan_ngoai")
    op.drop_index("ix_tkn_loai_dt", table_name="tai_khoan_ngoai")
    op.drop_table("tai_khoan_ngoai")
