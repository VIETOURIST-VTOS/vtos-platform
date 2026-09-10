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
# GỘP 08/9/2026 – nối SAU bản kho token Zalo OA thay vì song song với nó.
#
# Hai nhánh cùng rẽ từ v9b2e7c3a91d5 nên mạch có hai đầu, và Dockerfile chạy "alembic upgrade head":
# nhiều hơn một đầu là container KHÔNG khởi động được. Chuỗi V10 → V6 → V12 nối sau bản Zalo chứ
# không ngược lại, vì bản Zalo đã nằm trên main và có thể đã chạy trên hệ thống thật – đổi cha của
# một bản đã chạy là đổi thứ tự đã xảy ra rồi.
#
# NỐI LẠI 09/9/2026 – cùng một lỗi, lần thứ hai. Trong lúc nhánh này chạy, main nhận thêm
# zb2c3d4e5f6a (nhật ký tổng đài), cũng rẽ từ za1b2c3d4e5f. Đếm đầu mạch trên NHÁNH NÀY vẫn ra một
# đầu và vẫn xanh – mạch chỉ tách làm hai vào ĐÚNG lúc gộp, tức là lúc không ai còn nhìn nữa và
# container thì đã dừng. Nên phép đếm đúng là đếm trên origin, không phải trên thư mục đang mở.
#
# NỐI LẠI LẦN BA – lúc GỘP THẬT 09/9/2026. Trong lúc nhánh này chạy, main lại nhận thêm
# zc3d4e5f6a7b (bốn số tiền cho lô nạp), cũng rẽ từ zb2c3d4e5f6a. Gộp xong đếm ra HAI đầu mạch, đúng
# như dự đoán khi nối lần hai – và lần này bắt được vì đã đếm NGAY SAU KHI GỘP, trước khi đẩy lên.
#
# Ba lần cùng một lỗi trên cùng một mạch, không lần nào do viết sai. Lỗi nằm ở chỗ ĐẾM: đếm trên
# nhánh của mình thì hai phiên làm song song không bao giờ thấy nhau, và mạch chỉ tách vào đúng lúc
# gộp. Phép đếm đúng là đếm SAU KHI ĐÃ GỘP, và phải làm trước khi đẩy lên.
down_revision = "8de308e27b31"
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
