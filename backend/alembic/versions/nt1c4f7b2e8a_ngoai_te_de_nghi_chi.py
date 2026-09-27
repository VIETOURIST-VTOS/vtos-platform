# -*- coding: utf-8 -*-
"""Bốn ô ngoại tệ cho đề nghị chi — Chủ tịch chốt 27/9/2026.

Thêm `tien_te`, `so_tien_ngoai_te`, `ty_gia`, `ngay_ty_gia` vào `payment_requests`.

Vì sao: xem chú thích dài trong `app/models/ops.py` tại `class PaymentRequest`. Ngắn gọn – trước
hôm nay đề nghị chi chỉ có một ô tiền VND, nên chênh lệch tỷ giá chui vào cột "còn phải trả NCC".

MỌI CỘT NULLABLE, KHÔNG CÓ MẶC ĐỊNH SỐ. Hàng nghìn đề nghị chi đã có trong bảng đều là khoản đồng
Việt Nam hoặc khoản ngoại tệ đã bị gõ tay thành VND – không cách nào phân biệt được, nên không được
điền một con số vào chỗ ấy. `tien_te` mặc định rỗng: rỗng nghĩa là khoản đồng Việt Nam, và với dòng
cũ nó cũng là điều duy nhất nói được mà không bịa.

Revision ID: nt1c4f7b2e8a
Revises: ch1f5a8d3e6b
"""
import sqlalchemy as sa
from alembic import op

revision = "nt1c4f7b2e8a"
down_revision = "ch1f5a8d3e6b"
branch_labels = None
depends_on = None

# Cùng kiểu với mô hình, khai lại đúng con số để bản nâng cấp và mô hình không bao giờ lệch nhau.
TIEN = sa.Numeric(18, 2)
TY_GIA = sa.Numeric(18, 6)


def upgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.add_column(sa.Column("tien_te", sa.String(3), nullable=False, server_default=""))
        b.add_column(sa.Column("so_tien_ngoai_te", TIEN, nullable=True))
        b.add_column(sa.Column("ty_gia", TY_GIA, nullable=True))
        b.add_column(sa.Column("ngay_ty_gia", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.drop_column("ngay_ty_gia")
        b.drop_column("ty_gia")
        b.drop_column("so_tien_ngoai_te")
        b.drop_column("tien_te")
