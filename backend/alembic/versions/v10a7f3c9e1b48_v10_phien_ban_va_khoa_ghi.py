"""V10 – cột phiên bản cho 12 bảng nhiều người cùng sửa, và bảng khóa chống ghi trùng

Revision ID: v10a7f3c9e1b48
Revises: v9b2e7c3a91d5
Create Date: 2026-09-08

Hai thay đổi, cùng một gốc: quyết định "nhập là dùng luôn" bỏ khâu duyệt từng dòng, nên mọi va chạm
giữa hai người bây giờ xảy ra thẳng trên dữ liệu thật.

VÌ SAO server_default="1" CHỨ KHÔNG PHẢI CHỈ default=1: bản ghi đang có trong cơ sở dữ liệu không đi
qua mã Python lúc nâng cấp. Không có server_default thì mọi dòng cũ mang giá trị RỖNG, và lần sửa đầu
tiên sau nâng cấp sẽ so một số với một chỗ trống – tức là cột kiểm phiên bản không kiểm gì trong đúng
khoảng thời gian nó cần thiết nhất.

Cột này KHÔNG nặng như V9: thêm cột có mặc định là thao tác nhanh trên PostgreSQL 11 trở lên (không
viết lại bảng). Nhưng vẫn nên chạy cùng cửa sổ với V9 đợt 2 vì hai bản đi liền nhau.
"""
from alembic import op
import sqlalchemy as sa

revision = "v10a7f3c9e1b48"
down_revision = "v9b2e7c3a91d5"
branch_labels = None
depends_on = None

# Viết thẳng ra từng bảng. Giữ ĐÚNG thứ tự và đúng danh sách với BANG_CO_PHIEN_BAN ở
# app/services/ghi_mot_lan.py – có phép thử canh hai chỗ không lệch nhau.
BANG = [
    "tours", "bookings", "tour_settlements", "tour_cost_lines", "employees", "vehicles",
    "fleet_trips", "dispatch_orders", "products", "suppliers", "visa_cases", "leads",
]


def upgrade() -> None:
    for b in BANG:
        op.add_column(b, sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "khoa_ghi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khoa", sa.String(80), nullable=False),
        sa.Column("duong_dan", sa.String(200), server_default=""),
        sa.Column("phuong_thuc", sa.String(10), server_default="POST"),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("trang_thai", sa.Integer(), server_default="200"),
        sa.Column("tra_ve", sa.Text(), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_khoa_ghi_khoa", "khoa_ghi", ["khoa"], unique=True)
    op.create_index("ix_khoa_ghi_luc", "khoa_ghi", ["luc"])
    op.create_index("ix_khoa_ghi_duong_dan_luc", "khoa_ghi", ["duong_dan", "luc"])


def downgrade() -> None:
    op.drop_index("ix_khoa_ghi_duong_dan_luc", table_name="khoa_ghi")
    op.drop_index("ix_khoa_ghi_luc", table_name="khoa_ghi")
    op.drop_index("ix_khoa_ghi_khoa", table_name="khoa_ghi")
    op.drop_table("khoa_ghi")
    for b in reversed(BANG):
        op.drop_column(b, "phien_ban")
