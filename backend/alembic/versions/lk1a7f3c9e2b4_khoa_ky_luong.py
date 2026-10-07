"""Khóa kỳ lương: bảng bang_luong_khoa

Chuỗi bảng lương đổi theo quyết định Chủ tịch 07/10/2026. Bản nâng cấp này chỉ THÊM một bảng, không
đụng tới `payroll_runs`: ba cột chữ ký cũ (`kt_confirmed_by`, `hcns_by`, `tgd_by`) giữ nguyên vì
chúng là chữ ký của người thật trong những kỳ đã chạy qua chuỗi cũ.

Trạng thái mới (`da_kiem_co_so`, `hcns_kiem`, `da_ky`) là GIÁ TRỊ trong cột `status` đã có, không
phải cột mới — nên không cần đổi lược đồ cho chúng, và những kỳ cũ mang tên trạng thái cũ vẫn đọc
được, đúng như hàm `advance` đã khai.

Revision ID: lk1a7f3c9e2b4
Revises: tc105cdg3b8f1a

NỐI TIẾP tc105cdg3b8f1a, KHÔNG nối tiếp hdv4d9a3c6e1b5 như lúc viết. Lúc viết bản này thì
hdv4d9a3c6e1b5 còn là đầu mạch; tới lúc gộp thì làn khác đã đưa tc105cdg3b8f1a vào main, và
hai đầu mạch nghĩa là `alembic upgrade head` trong Dockerfile không chạy được – container
không khởi động. Sửa bằng cách cho bản viết sau nối tiếp bản viết trước, KHÔNG gộp bằng
merge revision. Nội dung bản nâng cấp không đổi một dòng nào.
"""
from alembic import op
import sqlalchemy as sa

revision = "lk1a7f3c9e2b4"
down_revision = "tc105cdg3b8f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bang_luong_khoa",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("period", sa.String(7), nullable=False, index=True),
        sa.Column("ban_so", sa.Integer, server_default="1"),
        sa.Column("noi_dung", sa.JSON),
        sa.Column("quy_tac", sa.JSON),
        sa.Column("dau_van_tay", sa.String(64), index=True),
        sa.Column("khoa_boi", sa.String(50), server_default=""),
        sa.Column("khoa_vai", sa.String(20), server_default=""),
        sa.Column("khoa_luc", sa.DateTime),
        # RỖNG = bản này đang có hiệu lực. Không dùng cờ true/false: số bản thay cho biết LUÔN bản
        # nào đã thay nó, mà một cờ thì không nói được điều đó.
        sa.Column("bi_thay_boi", sa.Integer, nullable=True),
        sa.Column("ly_do_mo", sa.String(20), server_default=""),
        sa.Column("ghi_chu_mo", sa.Text, server_default=""),
        sa.Column("mo_boi", sa.String(50), server_default=""),
        sa.Column("mo_luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_bang_luong_khoa_ky_ban", "bang_luong_khoa", ["period", "ban_so"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_bang_luong_khoa_ky_ban", table_name="bang_luong_khoa")
    op.drop_table("bang_luong_khoa")
