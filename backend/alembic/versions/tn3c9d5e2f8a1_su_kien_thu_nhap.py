"""Sổ sự kiện thu nhập: bảng su_kien_thu_nhap

Đợt B – chống trùng thu nhập liên phòng, liên kỳ. Một dòng = một khoản thu nhập biến đổi ĐÃ ĐƯỢC KÝ,
kèm căn cứ máy đọc được và danh sách vật thể đã nuôi con số ấy.

KHOÁ DUY NHẤT (ma_nv, loai, can_cu) LÀ PHẦN QUAN TRỌNG NHẤT CỦA BẢN NÂNG CẤP NÀY, không phải bảng.
Phép kiểm ở tầng mã nói ra chỗ trùng trước khi ký, để người xử lý; khoá duy nhất bắt chỗ trùng mà
phép kiểm không thấy. Chỉ cái sau là không vòng qua được, kể cả khi ai đó viết một đường ghi mới.

so_tien để NULL được: rỗng nghĩa là chưa tính ra được, khác hẳn "đã tính, bằng không" (quy tắc K2).

Revision ID: tn3c9d5e2f8a1
Revises: tx6a1b2c3d4e5f

NỐI TIẾP tx6a1b2c3d4e5f, không nối tiếp cl2b8e4f1a7d3 như lúc viết: lúc viết thì cl2b8e4f1a7d3
(Đợt A2) còn là đầu mạch; tới lúc gộp thì làn khác đã đưa tx6a1b2c3d4e5f vào main. Đo đầu mạch
phải làm NGAY TRƯỚC LÚC GỘP, không phải lúc viết — hai đầu mạch nghĩa là `alembic upgrade head`
trong Dockerfile không chạy được và container không khởi động.
"""
from alembic import op
import sqlalchemy as sa

revision = "tn3c9d5e2f8a1"
down_revision = "tx6a1b2c3d4e5f"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2, asdecimal=False)


def upgrade() -> None:
    op.create_table(
        "su_kien_thu_nhap",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("ban_khoa_id", sa.Integer, nullable=True),
        sa.Column("ma_nv", sa.String(20), nullable=False),
        sa.Column("loai", sa.String(30), nullable=False),
        sa.Column("can_cu", sa.String(80), nullable=False),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("nguon", sa.JSON),
        sa.Column("dien_giai", sa.Text, server_default=""),
        sa.Column("ghi_luc", sa.DateTime),
    )
    op.create_index("ux_su_kien_thu_nhap", "su_kien_thu_nhap", ["ma_nv", "loai", "can_cu"], unique=True)
    op.create_index("ix_su_kien_thu_nhap_ky", "su_kien_thu_nhap", ["period"])
    op.create_index("ix_su_kien_thu_nhap_ma_nv", "su_kien_thu_nhap", ["ma_nv"])
    op.create_index("ix_su_kien_thu_nhap_loai", "su_kien_thu_nhap", ["loai"])
    op.create_index("ix_su_kien_thu_nhap_can_cu", "su_kien_thu_nhap", ["can_cu"])


def downgrade() -> None:
    for ten in ("ix_su_kien_thu_nhap_can_cu", "ix_su_kien_thu_nhap_loai", "ix_su_kien_thu_nhap_ma_nv",
                "ix_su_kien_thu_nhap_ky", "ux_su_kien_thu_nhap"):
        op.drop_index(ten, table_name="su_kien_thu_nhap")
    op.drop_table("su_kien_thu_nhap")
