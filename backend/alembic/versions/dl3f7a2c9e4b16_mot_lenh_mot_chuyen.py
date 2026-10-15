# -*- coding: utf-8 -*-
"""DL-3 — một lệnh điều xe chỉ được có MỘT chuyến.

HÀNG RÀO THỨ HAI, Ở CƠ SỞ DỮ LIỆU. Lớp dịch vụ đã soát «lệnh này có chuyến chưa» trước khi tạo,
nhưng phép soát ấy ĐỌC RỒI GHI: hai lần bấm «hoàn thành» gần nhau cùng đọc thấy «chưa có» rồi
cùng tạo. Đúng hình với chỗ hỏng của Đợt E7 ở hóa đơn — và ở đây hậu quả là một chuyến có thật
thành hai dòng, doanh thu đội xe cộng hai lần.

ĐIỀU KIỆN `dispatch_id IS NOT NULL` LÀ BẮT BUỘC, không phải tối ưu: 756 chuyến đã nạp bằng Excel
đều để trống cột này, nên một chỉ mục duy nhất KHÔNG điều kiện sẽ đổ ngay ở dòng thứ hai — tức
hàng rào chống trùng lại chặn chính việc nạp sổ.

Khai CẢ `postgresql_where` LẪN `sqlite_where`: máy chủ chạy Postgres, phép thử chạy SQLite, và một
hàng rào chỉ có ở một trong hai nơi là hàng rào không ai đo được.

Revision ID: dl3f7a2c9e4b16
Revises: e16c3d4e5f6a
"""
import sqlalchemy as sa
from alembic import op

revision = "dl3f7a2c9e4b16"
down_revision = "e16c3d4e5f6a"
branch_labels = None
depends_on = None

TEN = "uq_fleet_trips_dispatch_id"


def upgrade() -> None:
    op.create_index(TEN, "fleet_trips", ["dispatch_id"], unique=True,
                    postgresql_where=sa.text("dispatch_id IS NOT NULL"),
                    sqlite_where=sa.text("dispatch_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index(TEN, table_name="fleet_trips")
