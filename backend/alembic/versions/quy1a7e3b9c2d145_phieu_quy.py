"""Đợt QUY-1 04/11/2026 — bảng phiếu quỹ tiền mặt.

`booking_id` RỖNG ĐƯỢC, và đó chính là lý do bảng này tồn tại: `receipts.booking_id` là NOT NULL
nên một khoản nộp quỹ / hoàn ký quỹ / thu khác không có chỗ nào để ghi.

Cột tiền dùng `Numeric(18, 2)` — đúng `models/kieu_tien.TIEN`, không phải `Float`. Lý do ở tệp ấy.
"""
from alembic import op
import sqlalchemy as sa

revision = "quy1a7e3b9c2d145"
down_revision = "qt2c8f3a1e7b94"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "phieu_quy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False, unique=True),
        sa.Column("chieu", sa.String(length=4), nullable=False, index=True),
        sa.Column("ngay", sa.Date(), nullable=False, index=True),
        sa.Column("so_tien", sa.Numeric(18, 2), nullable=False),
        sa.Column("ly_do", sa.String(length=40), nullable=False, index=True),
        sa.Column("noi_dung", sa.String(length=200), server_default=""),
        sa.Column("ten_doi_tuong", sa.String(length=160), server_default=""),
        sa.Column("ma_doi_tuong", sa.String(length=60), server_default=""),
        sa.Column("khoan_muc", sa.String(length=40), server_default=""),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("quy_tac", sa.String(length=40), server_default=""),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=50), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True, index=True),
    )


def downgrade():
    op.drop_table("phieu_quy")
