"""PQ-9: mỗi cảnh báo một người phụ trách

Đo bản đang chạy 11/9/2026: 1.703 cảnh báo, 1.557 chưa xử lý, chỉ 146 từng được xử lý. Chỗ hỏng
nằm ở cột người nhận – to_roles là một DANH SÁCH VAI TRÒ. Một cảnh báo đỏ quá hạn thu tiền gửi cho
"nv_kd,gd_kd,tp_dh,ketoan": gửi cho bốn vai trò là không gửi cho ai.

Thêm hai cột, không đụng tới to_roles: hai cột trả lời hai câu khác nhau – ai được BÁO TIN, và ai
phải TRẢ LỜI. Gộp lại là mất đúng cái khác biệt vừa làm ra.

Cả hai cột đều CHO PHÉP TRỐNG, có chủ ý: có loại cảnh báo không suy ra được một người (cảnh báo
dòng tiền gửi Ban lãnh đạo). Chỗ nguy hiểm không phải ô trống, mà là ô trống không ai đếm – nên
dịch vụ chu_canh_bao trả về số "chưa có chủ" tách theo loại.

KHÔNG đóng dấu người phụ trách cho 1.557 dòng đang có trong chính migration này. Việc suy chủ đọc
qua bốn bảng khác nhau và có loại suy không ra; làm trong migration thì lỗi ở dòng thứ 900 sẽ cuộn
ngược cả lần triển khai, và không ai xem được kết quả trước khi nó ghi. Giao hàng loạt đi qua
chu_canh_bao.giao_het() – chạy được, xem trước được, chạy lại được.

Revision ID: y2c6e0f4b8d3
Revises: x1b5d9e3a7c24
Create Date: 2026-09-11
"""
import sqlalchemy as sa
from alembic import op

# Nối vào ĐÚNG đầu đang có của nhánh (x1b5d9e3a7c24 – VPM-5 phân bổ tiền vào), không nối vào một
# revision cũ hơn. Nối vào cha cũ là tạo thêm một đầu thứ hai, và container khởi động sẽ dừng ở
# "Multiple head revisions are present" – đúng kiểu hỏng đã làm chết lần triển khai ngày 10/9.
revision = "y2c6e0f4b8d3"
down_revision = "x1b5d9e3a7c24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alerts") as b:
        b.add_column(sa.Column("nguoi_phu_trach", sa.Integer(), nullable=True))
        b.add_column(sa.Column("giao_luc", sa.DateTime(), nullable=True))
        b.create_foreign_key("fk_alerts_nguoi_phu_trach", "users", ["nguoi_phu_trach"], ["id"])
    # Màn hình chính của mỗi người là "cảnh báo của tôi, chưa xử lý" – lọc đúng hai cột này, nên
    # chỉ mục đi theo cặp. Không đặt thì mỗi lần mở trang là một lần quét toàn bảng 1.703 dòng, và
    # bảng này chỉ có mỗi ngày một to thêm.
    op.create_index("ix_alerts_nguoi_chua_xu_ly", "alerts", ["nguoi_phu_trach", "resolved"])


def downgrade() -> None:
    op.drop_index("ix_alerts_nguoi_chua_xu_ly", table_name="alerts")
    with op.batch_alter_table("alerts") as b:
        b.drop_constraint("fk_alerts_nguoi_phu_trach", type_="foreignkey")
        b.drop_column("giao_luc")
        b.drop_column("nguoi_phu_trach")
