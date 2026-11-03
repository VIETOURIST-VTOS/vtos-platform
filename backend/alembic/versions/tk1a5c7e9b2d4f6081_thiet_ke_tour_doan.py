"""TK-1 — khách tự thiết kế tour đoàn (giai đoạn 1): đơn giá dịch vụ đoàn + phiên bản thiết kế.

Chủ tịch 04/11/2026: khách thấy giá tạm tính (khách sạn, nhà hàng từ hệ thống; xe và chi phí khác Điều hành nhập),
biên tạm tính 10%, «làm luôn giai đoạn 1». Vé máy bay: Điều hành nhập giá theo chặng, nối API vé sau.

Revision ID: tk1a5c7e9b2d4f6081
Revises: ks17c4e6a8b0d2f135
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op

revision = "tk1a5c7e9b2d4f6081"
down_revision = "ks17c4e6a8b0d2f135"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "don_gia_doan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(20), nullable=False),
        sa.Column("ten", sa.String(160), nullable=False),
        sa.Column("pham_vi", sa.String(8), nullable=False, server_default="ca_hai"),
        sa.Column("tu_cho", sa.Integer(), nullable=True),
        sa.Column("gia", TIEN, nullable=False),
        sa.Column("tu_diem", sa.String(80), nullable=False, server_default=""),
        sa.Column("den_diem", sa.String(80), nullable=False, server_default=""),
        sa.Column("hang_ve", sa.String(20), nullable=False, server_default=""),
        sa.Column("gia_tre_em", TIEN, nullable=True),
        sa.Column("gia_em_be", TIEN, nullable=True),
        sa.Column("tu_ngay", sa.Date(), nullable=True),
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.String(300), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(10), nullable=False, server_default="cho_duyet"),
        sa.Column("tao_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("duyet_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do", sa.String(300), nullable=False, server_default=""),
    )
    op.create_index("ix_don_gia_doan_loai", "don_gia_doan", ["loai"])
    op.create_index("ix_don_gia_doan_trang_thai", "don_gia_doan", ["trang_thai"])
    op.create_table(
        "thiet_ke_doan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(20), nullable=False),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("yeu_cau_id", sa.Integer(), sa.ForeignKey("yeu_cau_khach.id"), nullable=True),
        sa.Column("thiet_ke", sa.JSON(), nullable=False),
        sa.Column("du_toan", sa.JSON(), nullable=False),
        sa.Column("tong_ban", TIEN, nullable=True),
        sa.Column("tong_von", TIEN, nullable=True),
        sa.Column("ngay_di", sa.Date(), nullable=True),
        sa.Column("so_khach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tom_tat", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(12), nullable=False, server_default="da_gui"),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("ma", "phien_ban", name="uq_thiet_ke_doan_ma_pb"),
    )
    op.create_index("ix_thiet_ke_doan_ma", "thiet_ke_doan", ["ma"])
    op.create_index("ix_thiet_ke_doan_tai_khoan_id", "thiet_ke_doan", ["tai_khoan_id"])
    op.create_index("ix_thiet_ke_doan_yeu_cau_id", "thiet_ke_doan", ["yeu_cau_id"])


def downgrade() -> None:
    op.drop_table("thiet_ke_doan")
    op.drop_table("don_gia_doan")
