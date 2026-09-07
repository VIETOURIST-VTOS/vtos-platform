"""Công nợ đội xe: bảng ghi nhận đã trả / đã thu

Sổ công nợ nói được "phải trả bao nhiêu" nhưng không nói được "đã trả chưa" nếu không có bảng
này – và một sổ công nợ không phân biệt được hai điều đó là sổ dẫn tới trả tiền hai lần.

`idem_key` duy nhất ở CƠ SỞ DỮ LIỆU chứ không chỉ kiểm trong mã: hai tiến trình chạy song song
có thể cùng đọc thấy "chưa có" rồi cùng ghi, và chỉ ràng buộc ở tầng dữ liệu mới chặn được.

Revision ID: c1d2e3f4a5b6
Revises: 0fa7043cb785
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "0fa7043cb785"   # nối sau bản vá bán xe của phiên song song – giữ MỘT đầu duy nhất
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "fleet_debt_payments" in insp.get_table_names():
        return
    op.create_table(
        "fleet_debt_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idem_key", sa.String(120), nullable=False, unique=True),
        sa.Column("huong", sa.String(16), nullable=False),
        # Không đặt khóa ngoại ở tầng CSDL cho các cột tham chiếu: SQLite (máy lập trình) không sửa được
        # ràng buộc sau khi tạo bảng, nên khai báo khóa ngoại ở đây sẽ làm hai môi trường chạy hai lược đồ
        # khác nhau. Quan hệ vẫn được giữ ở tầng mô hình và kiểm ở tầng dịch vụ.
        sa.Column("partner_id", sa.Integer(), nullable=True),
        sa.Column("settlement_id", sa.Integer(), nullable=True),
        sa.Column("sale_case_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("so_tien", sa.Float(), server_default="0"),
        sa.Column("chung_tu", sa.String(120), server_default=""),
        sa.Column("note", sa.String(300), server_default=""),
        sa.Column("created_by", sa.String(50), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fleet_debt_payments_settlement", "fleet_debt_payments", ["settlement_id"])
    op.create_index("ix_fleet_debt_payments_partner", "fleet_debt_payments", ["partner_id"])


def downgrade() -> None:
    op.drop_table("fleet_debt_payments")
