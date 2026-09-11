"""VPM-17 – cửa nhập NGÀY ĐẾN HẠN cho đề nghị chi và đơn đặt dịch vụ

Revision ID: b5f9h4c7e2a31
Revises: a4e8g3b6d1f29

VÌ SAO BẢN VÁ NÀY TỒN TẠI

Sổ nghĩa vụ (VPM-11) xếp mỗi khoản vào một cột của bảng dòng tiền theo NGÀY. `payment_requests` và
`service_orders` không có ngày phải trả nào, nên toàn bộ khoản chi đang chờ rơi vào rổ "Chưa đủ dữ
liệu dự báo": đếm được, nhìn thấy, nhưng không xếp được vào cột nào.

Ranh giới Chủ tịch đặt ngày 09/9/2026: phần mềm viết CẤU TRÚC và CỬA NHẬP, số liệu do nhân viên tự
nhập. Thiếu cột này không phải lý do để hoãn bảng dòng tiền – nó là VIỆC CÒN THIẾU, và bản vá này
dựng cột để người lập đề nghị gõ ngày thật vào.

CHO PHÉP RỖNG, KHÔNG MẶC ĐỊNH, KHÔNG SUY TỪ NGÀY LẬP. Ba việc khác nhau và phải phân biệt được:
  · có hạn ngày 20/9  – người lập đã hẹn nhà cung cấp
  · chưa ai nhập      – RỖNG, và nó phải hiện ra ở danh sách việc còn thiếu
  · không có hạn      – không tồn tại trong nghiệp vụ này; khoản nào cũng phải trả vào một ngày

Suy "7 ngày sau ngày duyệt" thì mọi khoản đều có một ngày trông như thật, xếp gọn vào một cột trên
màn hình lãnh đạo, và không ai còn nhớ đó là số máy đoán. Đó là lý do cột này rỗng cho tới khi có
người gõ.

Ba cột một bộ: ngày, người gõ, lúc gõ. Ngày đến hạn SỬA ĐƯỢC sau khi lập (thương lượng lại với nhà
cung cấp là chuyện thường), nên phải biết ai gõ con số đang nằm đó.
"""
import sqlalchemy as sa
from alembic import op

revision = "b5f9h4c7e2a31"
down_revision = "a4e8g3b6d1f29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for bang in ("payment_requests", "service_orders"):
        op.add_column(bang, sa.Column("ngay_den_han", sa.Date(), nullable=True))
        op.add_column(bang, sa.Column("ngay_den_han_boi", sa.String(length=50), nullable=True))
        op.add_column(bang, sa.Column("ngay_den_han_luc", sa.DateTime(), nullable=True))
        op.create_index(f"ix_{bang}_ngay_den_han", bang, ["ngay_den_han"])


def downgrade() -> None:
    for bang in ("payment_requests", "service_orders"):
        op.drop_index(f"ix_{bang}_ngay_den_han", table_name=bang)
        for cot in ("ngay_den_han_luc", "ngay_den_han_boi", "ngay_den_han"):
            op.drop_column(bang, cot)
