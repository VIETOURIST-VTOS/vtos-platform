# -*- coding: utf-8 -*-
"""Chuyến: thêm cột `quyet_toan` — đã quyết toán xong hay còn đang chạy.

VÌ SAO CẦN CỘT MỚI: màn Hiệu quả đội xe cộng MỌI chuyến có ngày khởi hành trong kỳ vào ô tiền. Chuyến
đang chạy thì doanh thu có thể đã biết (hợp đồng chốt trước) mà chứng từ dầu, cầu đường, công tác phí
chưa về. Cộng chung thì biên lợi nhuận của tháng đang chạy vọt lên gần 100% rồi tụt dần suốt tháng —
con số nhảy múa đó làm người đọc mất lòng tin vào cả màn hình, và không ai nhìn ra vì sao.

VÌ SAO KHÔNG SUY RA TỪ "ĐÃ CÓ DÒNG CHI PHÍ CHƯA": hai việc khác nhau. Một chuyến quyết toán xong mà
thật sự không tốn đồng nào (xe đi việc công ty, không qua trạm, không đổ dầu giữa đường) vẫn phải được
tính tiền; suy đoán sẽ xếp nhầm nó thành "đang chạy" và giấu doanh thu của nó khỏi báo cáo. Ngược lại
một chuyến đang chạy đã kịp ghi tạm ứng công tác phí sẽ bị suy đoán thành "đã xong". Đoán sai theo cả
hai chiều, mà không chiều nào kêu lên. Người nạp biết chuyến đã quyết toán chưa — hỏi thẳng rẻ hơn đoán.

VÌ SAO KHÔNG DÙNG CỜ `co`: cờ đỏ/vàng bật vì lệch km GPS hay thiếu chứng từ. Những chuyến ấy đã quyết
toán xong và phải được tính tiền. Và không dùng `status`: chuyến nạp từ báo cáo ngoài vào thẳng
`da_xac_nhan` ngay lúc tạo (services/fleet.py), nên `status` không phân biệt được hai việc này.

MẶC ĐỊNH TRUE, CÓ CHỦ Ý: mọi chuyến đã nằm trong sổ trước bản này đều là chuyến đã quyết toán xong.
Đặt mặc định FALSE sẽ làm toàn bộ doanh thu lịch sử biến mất khỏi ô tiền ngay khi nâng cấp — một bản
nâng cấp không được phép đổi một đồng nào của quá khứ.

ĐỔI NGƯỢC ĐƯỢC: `downgrade` xoá cột. Mất thông tin chuyến nào đang chạy, nhưng không mất tiền: mọi
chuyến quay về được tính như đã quyết toán, đúng hành vi trước bản này.

Revision ID: qt1b9e4f2a7c35
Revises: tk2a3c5e7f9b1d4062
"""
import sqlalchemy as sa
from alembic import op

revision = "qt1b9e4f2a7c35"
down_revision = "tk2a3c5e7f9b1d4062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default="1" để bản ghi cũ nhận TRUE ngay trong câu ALTER, không cần một câu UPDATE riêng
    # chạy sau — máy chủ nâng cấp xong là sổ đã đúng, không có khoảng giữa nào mà báo cáo trả số sai.
    with op.batch_alter_table("fleet_trips") as b:
        b.add_column(sa.Column("quyet_toan", sa.Boolean(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("fleet_trips") as b:
        b.drop_column("quyet_toan")
