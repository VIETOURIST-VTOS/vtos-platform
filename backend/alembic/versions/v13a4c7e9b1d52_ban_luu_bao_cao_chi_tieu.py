"""Bản lưu báo cáo theo lịch – lưu đúng cấu trúc chỉ tiêu

Revision ID: v13a4c7e9b1d52
Revises: v11d8e4b6a2f79
"""
from alembic import op
import sqlalchemy as sa

revision = "v13a4c7e9b1d52"
down_revision = "v11d8e4b6a2f79"
branch_labels = None
depends_on = None

# Bảng này tồn tại vì trước 10/9/2026 màn hình báo cáo và bản lưu theo lịch là HAI phép tính khác
# nhau cho cùng một câu hỏi. Nay bản lưu được sinh ra từ chính hàm mà màn hình gọi.
#
# Khoá duy nhất (kind, ky, pham_vi) là phần đáng chú ý nhất: nó làm việc CHẠY BÙ an toàn. Lịch lỡ
# một hôm, hôm sau chạy bù, và kết quả là MỘT bản đúng chứ không phải hai bản chờ người ta chọn.


def upgrade() -> None:
    op.create_table(
        "bao_cao_luu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False, index=True),
        sa.Column("ky", sa.String(12), nullable=False, index=True),
        sa.Column("pham_vi", sa.String(30), nullable=False, index=True),
        sa.Column("pham_vi_ten", sa.String(80), server_default=""),
        sa.Column("tu", sa.String(10), server_default=""),
        sa.Column("den", sa.String(10), server_default=""),
        sa.Column("chi_tieu", sa.JSON(), nullable=True),
        sa.Column("markdown", sa.Text(), server_default=""),
        sa.Column("so_viec_do", sa.Integer(), server_default="0"),
        sa.Column("so_can_ra_soat", sa.Integer(), server_default="0"),
        sa.Column("so_chua_co_so", sa.Integer(), server_default="0"),
        sa.Column("tao_boi", sa.String(50), server_default="lich"),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("kind", "ky", "pham_vi", name="uq_bao_cao_luu_ky"),
    )


def downgrade() -> None:
    """Hạ cấp XOÁ toàn bộ bản chụp đã lưu, và KHÔNG dựng lại được.

    Ghi rõ ở đây vì đây không phải thao tác đảo ngược vô hại: bản chụp là ảnh của dữ liệu tại một
    thời điểm đã qua. Nâng cấp lại chỉ dựng lại cái bảng rỗng, còn số của tháng trước thì mất hẳn.
    """
    op.drop_table("bao_cao_luu")
