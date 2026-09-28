# -*- coding: utf-8 -*-
"""Nới cột `params.value` từ 200 lên 500 ký tự — 27/9/2026.

VÌ SAO: làn CSKH thêm tham số `khao_sat_mau_tin` (mẫu tin nhắn Zalo gửi khách) dài **210 ký tự**,
và bản ấy được gộp vào main đúng lúc CI chết vì hạn mức chi tiêu GitHub Actions — nên hàng rào K11
(`tests/test_ks_do_dai.py`, so độ dài chuỗi với độ dài cột) không kêu được. CI sống lại thì main
đỏ, và mọi nhánh của mọi làn đỏ theo.

VÌ SAO NỚI CỘT CHỨ KHÔNG CẮT CÂU CHỮ: bảng `params` sinh ra để câu chữ gửi khách và các con số vận
hành nằm NGOÀI mã — sửa một dấu phẩy không phải đẩy một vòng mã. Cắt mẫu tin cho vừa con số 200 là
lấy cột làm chủ và bắt Marketing viết theo giới hạn kỹ thuật. Và đây mới là tham số mẫu tin ĐẦU
TIÊN; còn mẫu ZNS, mẫu nhắc, mẫu xin lỗi sự cố phía sau.

VÌ SAO 500 CHỨ KHÔNG PHẢI 2000: cột này vẫn là THAM SỐ, không phải chỗ chứa văn bản dài. Một giá
trị quá 500 ký tự là dấu hiệu thứ đang cất vào đây đáng lẽ phải là một bảng riêng — và giữ trần ở
500 là để dấu hiệu ấy còn kêu được.

CHỈ NỚI, KHÔNG THU HẸP: mọi giá trị đang có đều ≤ 200 nên không dòng nào bị cắt. `downgrade` thu
về 200 sẽ CẮT CỤT giá trị dài hơn — PostgreSQL từ chối, SQLite cắt im lặng — nên bản hạ cấp nói
thẳng điều đó ở chú thích thay vì để người chạy nó tưởng là một bước lùi vô hại.

Revision ID: pv2d8e1a6c4b
Revises: nt1c4f7b2e8a
"""
import sqlalchemy as sa
from alembic import op

revision = "pv2d8e1a6c4b"
down_revision = "nt1c4f7b2e8a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("params") as b:
        b.alter_column("value", existing_type=sa.String(200), type_=sa.String(500),
                       existing_nullable=False, existing_server_default="")


def downgrade() -> None:
    # CẢNH BÁO: bước này CẮT CỤT mọi giá trị dài hơn 200 ký tự. Chạy nó trên cơ sở dữ liệu thật đã
    # có mẫu tin CSKH là mất một phần câu chữ gửi khách, và mất im lặng trên SQLite.
    with op.batch_alter_table("params") as b:
        b.alter_column("value", existing_type=sa.String(500), type_=sa.String(200),
                       existing_nullable=False, existing_server_default="")
