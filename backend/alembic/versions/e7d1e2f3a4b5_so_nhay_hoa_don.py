"""Đợt E7 13/10/2026 — sổ số nhảy hóa đơn, mã việc phát hành, và chỉ mục duy nhất trên số.

Revision ID: e7d1e2f3a4b5
Revises: e6c1d2e3f4a5
Create Date: 2026-10-13

BA VIỆC, VÀ VIỆC THỨ BA LÀ VIỆC CẨN THẬN NHẤT.

1. Bảng `so_nhay_hoa_don` — số cuối đã cấp của từng ký hiệu. NẠP SẴN từ sổ hiện có: số cuối của
   mỗi ký hiệu lấy bằng `max(number)` trên chính bảng `invoices`, vì những số ấy ĐÃ TIÊU rồi.
   Không nạp thì bộ cấp số bắt đầu lại từ 1 và cấp lại đúng những số đã in ra giấy.

2. Hai cột trên `invoices`: `issue_request_id` (mã việc của một lần bấm) và `issue_sent_at`.

3. CHỈ MỤC DUY NHẤT (series, number) — CÓ ĐIỀU KIỆN `number > 0`. Điều kiện ấy là bắt buộc, không
   phải tối ưu: mọi hóa đơn NHÁP đều mang `number = 0` theo giá trị mặc định của cột, nên một chỉ
   mục duy nhất không điều kiện sẽ đổ ngay ở tờ nháp thứ hai. Postgres và SQLite đều nhận chỉ mục
   có điều kiện; khai cả hai phương ngữ vì máy chủ chạy Postgres còn phép thử chạy SQLite, và một
   hàng rào chỉ có ở một trong hai nơi là hàng rào không ai đo được.
"""
import sqlalchemy as sa
from alembic import op

revision = "e7d1e2f3a4b5"
down_revision = "e6c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "so_nhay_hoa_don",
        sa.Column("series", sa.String(length=20), primary_key=True),
        sa.Column("so_cuoi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cap_nhat_luc", sa.DateTime(), nullable=True),
        sa.Column("cap_nhat_boi", sa.String(length=50), nullable=False, server_default=""),
    )
    # NẠP SẴN: số cuối đã tiêu của từng ký hiệu, lấy từ chính sổ hóa đơn. Tính CẢ tờ đã hủy —
    # số của một tờ đã hủy vẫn là số đã tiêu, và cấp lại nó là làm ra hai tờ một số.
    op.execute("""
        INSERT INTO so_nhay_hoa_don (series, so_cuoi, cap_nhat_boi)
        SELECT series, MAX(number), 'di_tru_e7' FROM invoices WHERE number > 0 GROUP BY series
    """)
    op.add_column("invoices", sa.Column("issue_request_id", sa.String(length=64), nullable=True))
    op.add_column("invoices", sa.Column("issue_sent_at", sa.DateTime(), nullable=True))
    op.create_index("ux_invoices_issue_request_id", "invoices", ["issue_request_id"], unique=True)
    op.create_index("ux_invoices_series_number", "invoices", ["series", "number"], unique=True,
                    postgresql_where=sa.text("number > 0"), sqlite_where=sa.text("number > 0"))


def downgrade() -> None:
    op.drop_index("ux_invoices_series_number", table_name="invoices")
    op.drop_index("ux_invoices_issue_request_id", table_name="invoices")
    op.drop_column("invoices", "issue_sent_at")
    op.drop_column("invoices", "issue_request_id")
    op.drop_table("so_nhay_hoa_don")
