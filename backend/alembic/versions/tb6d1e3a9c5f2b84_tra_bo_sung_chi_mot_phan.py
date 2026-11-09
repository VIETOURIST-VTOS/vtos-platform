"""05-TT · trả bổ sung + chi một phần (mọi đề nghị chi)

Revision ID: tb6d1e3a9c5f2b84
Revises: dx5c2a8e4f1b7d93
Create Date: 2026-11-10

Chủ tịch duyệt bản xem trước 10/11/2026, áp cho MỌI đề nghị chi 05-TT:
  · «Trả bổ sung» kèm lý do: hồ sơ về người lập, sửa rồi gửi lại; chữ ký cũ xoá, bản trước giữ lại.
  · Chi một phần: nhiều lần chi, tổng không vượt số được duyệt, mỗi lần ghi sổ riêng.
Ba cột mới, không đụng cột nào đang có. `da_chi_tien` rỗng cho mọi hồ sơ cũ (chưa chi lần nào).
"""
import sqlalchemy as sa
from alembic import op

revision = "tb6d1e3a9c5f2b84"
down_revision = "dx5c2a8e4f1b7d93"
branch_labels = None
depends_on = None


def upgrade():
    # Rỗng = chưa chi lần nào (luật cột tiền KT-12: cột tiền không mặc định 0).
    op.add_column("payment_requests", sa.Column("da_chi_tien", sa.Numeric(18, 2), nullable=True))
    op.add_column("payment_requests", sa.Column("lan_chi", sa.JSON(), nullable=True))
    op.add_column("payment_requests", sa.Column("lan_tra", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("payment_requests", "lan_tra")
    op.drop_column("payment_requests", "lan_chi")
    op.drop_column("payment_requests", "da_chi_tien")
