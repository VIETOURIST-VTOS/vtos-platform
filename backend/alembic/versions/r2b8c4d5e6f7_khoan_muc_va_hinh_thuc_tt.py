# -*- coding: utf-8 -*-
"""Đợt R2 15/10/2026 — danh mục khoản mục chi phí + hình thức thanh toán vào khóa quy tắc.

Revision ID: r2b8c4d5e6f7
Revises: r1a7b2c3d4e5
"""
from alembic import op
import sqlalchemy as sa

revision = "r2b8c4d5e6f7"
down_revision = "r1a7b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "khoan_muc_chi_phi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("nhom", sa.String(length=20), server_default="gia_von", nullable=False),
        sa.Column("thu_tu", sa.Integer(), server_default="100", nullable=False),
        sa.Column("dung", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("ghi_chu", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_khoan_muc_chi_phi_ma", "khoan_muc_chi_phi", ["ma"], unique=True)
    op.create_index("ix_khoan_muc_chi_phi_nhom", "khoan_muc_chi_phi", ["nhom"])
    op.create_index("ix_khoan_muc_chi_phi_dung", "khoan_muc_chi_phi", ["dung"])

    op.add_column("quy_tac_hach_toan",
                  sa.Column("hinh_thuc_tt", sa.String(length=20), server_default="", nullable=False))
    op.add_column("quy_tac_hach_toan",
                  sa.Column("can_khoan_muc", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_quy_tac_hach_toan_hinh_thuc_tt", "quy_tac_hach_toan", ["hinh_thuc_tt"])

    # BỐN DÒNG CŨ ĐƯỢC BẬT CHIỀU KHOẢN MỤC NGAY TRONG BẢN DI TRÚ, và phải làm ở đây chứ không ở
    # `nap_mac_dinh`: hàm ấy BỎ QUA mã đã có (đúng — để không đè lên bản Kế toán đã sửa), nên trên
    # kho dữ liệu thật, nơi bốn mã này đã nằm sẵn từ 08/9/2026, nó sẽ không bao giờ chạm tới chúng
    # và cột mới sẽ mãi mãi là `false`. Khi ấy đợt này chỉ đúng trên máy, nơi kho dữ liệu dựng mới.
    op.execute(
        "UPDATE quy_tac_hach_toan SET can_khoan_muc = true "
        "WHERE ma IN ('MUA_CO_HD', 'MUA_KHONG_HD', 'TRICH_TRUOC', 'HOAN_UNG')")


def downgrade() -> None:
    op.drop_index("ix_quy_tac_hach_toan_hinh_thuc_tt", table_name="quy_tac_hach_toan")
    op.drop_column("quy_tac_hach_toan", "can_khoan_muc")
    op.drop_column("quy_tac_hach_toan", "hinh_thuc_tt")
    op.drop_index("ix_khoan_muc_chi_phi_dung", table_name="khoan_muc_chi_phi")
    op.drop_index("ix_khoan_muc_chi_phi_nhom", table_name="khoan_muc_chi_phi")
    op.drop_index("ux_khoan_muc_chi_phi_ma", table_name="khoan_muc_chi_phi")
    op.drop_table("khoan_muc_chi_phi")
