# -*- coding: utf-8 -*-
"""Dòng chi phí chuyến: thêm khóa nối `maintenance_id` tới phiếu bảo dưỡng.

VÌ SAO: cùng một hóa đơn garage hôm nay có thể nằm ở hai bảng – một dòng `fleet_trip_costs` loại
`sua_chua` (do người nhập ghi vào chuyến) và một phiếu `fleet_maintenance` (do đội xe mở phiếu). Không
khóa nào nối chúng, nên mọi báo cáo cộng CẢ HAI. Chú thích trong `fleet_ai.hieu_qua_ky` viết "bảo dưỡng
NGOÀI chuyến", nhưng truy vấn không loại trừ gì – cái tên nói một đằng, câu lệnh làm một nẻo.

VÌ SAO KHÔNG ĐOÁN BẰNG NGÀY VÀ SỐ TIỀN: hai lần sửa cùng ngày cùng giá là chuyện có thật (hai xe cùng
thay một loại lốp). Đoán sẽ gộp nhầm hai khoản có thật thành một, và mất tiền khỏi báo cáo mà không ai
biết. Khóa nối thì người nhập nói rõ "dòng này chính là phiếu kia", hoặc không nói gì – và khi không
nói gì, hệ thống cộng cả hai rồi CẢNH BÁO, chứ không tự trừ.

RỖNG VẪN LÀ RỖNG: cột cho phép NULL và không có mặc định. Mọi dòng chi phí cũ giữ nguyên trống, nghĩa
là "chưa ai nối", không phải "đã xác nhận là hai khoản khác nhau".

ĐỔI NGƯỢC ĐƯỢC: `downgrade` xoá cột. Mất các mối nối đã khai, không mất tiền.

Revision ID: qt2c8f3a1e7b94
Revises: qt1b9e4f2a7c35
"""
import sqlalchemy as sa
from alembic import op

revision = "qt2c8f3a1e7b94"
down_revision = "qt1b9e4f2a7c35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fleet_trip_costs") as b:
        b.add_column(sa.Column("maintenance_id", sa.Integer(), nullable=True))
    op.create_index("ix_fleet_trip_costs_maintenance_id", "fleet_trip_costs", ["maintenance_id"])


def downgrade() -> None:
    op.drop_index("ix_fleet_trip_costs_maintenance_id", table_name="fleet_trip_costs")
    with op.batch_alter_table("fleet_trip_costs") as b:
        b.drop_column("maintenance_id")
