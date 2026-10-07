"""Lịch sử tổ chức: bảng lich_su_to_chuc

Đợt C. `employees.department` là một giá trị HIỆN TẠI; đổi phòng cho một người hôm nay thì mọi báo
cáo quá khứ đọc theo phòng mới — lịch sử bị viết lại mà không ai bấm nút nào gọi là sửa lịch sử.
Bảng này mở mẫu `phan_cong_kd` (đã có cho khối Kinh doanh) ra toàn bộ nhân sự.

BẢN NÂNG CẤP NÀY KHÔNG NẠP DỮ LIỆU CŨ, và đó là chủ ý. Lịch sử của những năm trước không nằm trong
hệ thống; dựng nó ra từ phòng hiện tại là viết vào sổ một điều không ai biết có đúng không. Bảng
bắt đầu rỗng, và chặng đầu của mỗi người được dựng tại lần điều chuyển đầu tiên, có cờ `suy_ra`
đánh dấu rằng nó là một suy ra chứ không phải bản ghi.

Revision ID: ls4d7e2a9c3b6
Revises: tn3c9d5e2f8a1
"""
from alembic import op
import sqlalchemy as sa

revision = "ls4d7e2a9c3b6"
down_revision = "tn3c9d5e2f8a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lich_su_to_chuc",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ma_nv", sa.String(20), nullable=False),
        sa.Column("phong", sa.String(20), nullable=False),
        sa.Column("chuc_vu", sa.String(20), server_default="nv"),
        sa.Column("van_phong", sa.String(20), server_default=""),
        sa.Column("company_id", sa.Integer, nullable=True),
        sa.Column("tu_ngay", sa.Date, nullable=False),
        # RỖNG = chặng đang mở. Xem chú thích ở models/lich_su_to_chuc.py.
        sa.Column("den_ngay", sa.Date, nullable=True),
        sa.Column("ly_do", sa.Text, server_default=""),
        sa.Column("suy_ra", sa.Boolean, server_default=sa.false()),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime),
    )
    op.create_index("ix_lich_su_to_chuc_nguoi_ngay", "lich_su_to_chuc", ["ma_nv", "tu_ngay", "den_ngay"])
    op.create_index("ix_lich_su_to_chuc_ma_nv", "lich_su_to_chuc", ["ma_nv"])
    op.create_index("ix_lich_su_to_chuc_tu_ngay", "lich_su_to_chuc", ["tu_ngay"])


def downgrade() -> None:
    for ten in ("ix_lich_su_to_chuc_tu_ngay", "ix_lich_su_to_chuc_ma_nv", "ix_lich_su_to_chuc_nguoi_ngay"):
        op.drop_index(ten, table_name="lich_su_to_chuc")
    op.drop_table("lich_su_to_chuc")
