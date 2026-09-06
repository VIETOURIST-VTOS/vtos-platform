"""Công ty chủ quản cho tour, booking, phiếu thu, đề nghị chi và chứng từ ghi sổ (Đợt 2 mục 2)

Cột để RỖNG cho hồ sơ cũ – rỗng nghĩa là "chưa xác định pháp nhân", đưa vào danh sách đối chiếu.
Tuyệt đối không đặt mặc định về công ty mẹ: gán sai pháp nhân sẽ làm sai báo cáo từng đơn vị và
làm sai cả phần loại trừ giao dịch nội bộ khi hợp nhất.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
"""
from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None

BANG = ["tours", "bookings", "receipts", "payment_requests", "journal_entries"]


def upgrade():
    for t in BANG:
        op.add_column(t, sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True))
        op.create_index(f"ix_{t}_company_id", t, ["company_id"])


def downgrade():
    for t in BANG:
        op.drop_index(f"ix_{t}_company_id", table_name=t)
        op.drop_column(t, "company_id")
