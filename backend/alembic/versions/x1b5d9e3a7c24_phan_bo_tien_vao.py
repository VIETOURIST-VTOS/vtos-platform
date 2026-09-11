"""VPM-5: phân bổ một khoản tiền vào cho nhiều booking

Revision ID: x1b5d9e3a7c24
Revises: w1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa
from app.models.kieu_tien import TIEN

revision = "x1b5d9e3a7c24"
down_revision = "w1a2b3c4d5e6"
branch_labels = None
depends_on = None

# Trước bản này `receipts.booking_id` và `bank_transactions.booking_id` đều là khoá ĐƠN: một khoản
# tiền chỉ gắn được đúng một booking. Khách chuyển một lần cho hai tour thì kế toán không có chỗ để
# nói điều đó. Bảng `phan_bo_tien` là chỗ ấy.
#
# `chua_phan_bo` cố ý CHO PHÉP RỖNG và không có mặc định, theo quy ước K2: rỗng nghĩa là chưa từng
# phân bổ dòng nào, khác hẳn 0 nghĩa là đã phân bổ hết. Mọi giao dịch có trước 11/9/2026 đều rỗng —
# và rỗng là câu trả lời ĐÚNG cho chúng, không phải một chỗ dữ liệu còn thiếu.


def upgrade() -> None:
    op.create_table(
        "phan_bo_tien",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_txn_id", sa.Integer(), sa.ForeignKey("bank_transactions.id"), nullable=False, index=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False, index=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("so_tien", TIEN, nullable=False),
        sa.Column("ghi_chu", sa.String(300), server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("huy", sa.Boolean(), server_default=sa.false()),
        sa.Column("huy_boi", sa.String(50), server_default=""),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_ly_do", sa.String(300), server_default=""),
    )
    op.create_index("ix_phan_bo_tien_txn_huy", "phan_bo_tien", ["bank_txn_id", "huy"])
    op.add_column("bank_transactions", sa.Column("chua_phan_bo", TIEN, nullable=True))


def downgrade() -> None:
    """Hạ cấp XOÁ mọi dòng phân bổ, kể cả các dòng đã huỷ kèm lý do.

    Phiếu thu do chúng sinh ra thì KHÔNG mất – chúng là bảng riêng. Nghĩa là sau khi hạ cấp, hệ thống
    còn phiếu thu nhưng không còn biết chúng đến từ khoản tiền nào và vì sao chia như thế. Ghi rõ ở
    đây để người chạy biết mình đang đánh đổi cái gì.
    """
    op.drop_column("bank_transactions", "chua_phan_bo")
    op.drop_index("ix_phan_bo_tien_txn_huy", table_name="phan_bo_tien")
    op.drop_table("phan_bo_tien")
