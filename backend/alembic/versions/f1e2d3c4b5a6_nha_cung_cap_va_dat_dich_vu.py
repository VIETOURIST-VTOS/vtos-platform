"""Nhà cung cấp, đổi số tài khoản có hai người, và đơn đặt dịch vụ

Đầu chi lớn nhất của công ty đến nay chưa có sổ: chi phí tour đi ra bằng đề nghị chi, nhưng
không có nơi nào trả lời được "đã đặt những gì, của ai, cho tour nào, đã dùng chưa".

Bảng supplier_bank_changes tồn tại vì một lý do duy nhất: đổi số tài khoản của một nhà cung
cấp có thật rồi để hệ thống tự chuyển tiền vào đó là cách gian lận thanh toán phổ biến nhất.
Số tài khoản đang hiệu lực nằm ở suppliers và chỉ đổi khi có người THỨ HAI xác nhận.

Revision ID: f1e2d3c4b5a6
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "f1e2d3c4b5a6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ten = set(sa.inspect(op.get_bind()).get_table_names())
    if "suppliers" not in ten:
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String(30), nullable=False, unique=True),
            sa.Column("ten", sa.String(200), nullable=False),
            sa.Column("loai", sa.String(20), server_default="khac"),
            sa.Column("ma_so_thue", sa.String(20), server_default=""),
            sa.Column("dia_chi", sa.String(300), server_default=""),
            sa.Column("nguoi_lien_he", sa.String(120), server_default=""),
            sa.Column("dien_thoai", sa.String(40), server_default=""),
            sa.Column("email", sa.String(120), server_default=""),
            sa.Column("so_tai_khoan", sa.String(40), server_default=""),
            sa.Column("ngan_hang", sa.String(120), server_default=""),
            sa.Column("chu_tai_khoan", sa.String(160), server_default=""),
            sa.Column("dieu_khoan_tt", sa.String(200), server_default=""),
            sa.Column("note", sa.String(300), server_default=""),
            sa.Column("active", sa.Boolean, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("created_by", sa.String(50), server_default=""),
        )
    if "supplier_bank_changes" not in ten:
        op.create_table(
            "supplier_bank_changes",
            sa.Column("id", sa.Integer, primary_key=True),
            # Không đặt khóa ngoại ở tầng CSDL: SQLite (máy lập trình) không thêm được ràng buộc vào bảng
            # đã tạo, nên khai ở đây sẽ làm hai môi trường chạy hai lược đồ khác nhau.
            sa.Column("supplier_id", sa.Integer, nullable=False),
            sa.Column("so_tk_cu", sa.String(40), server_default=""),
            sa.Column("ngan_hang_cu", sa.String(120), server_default=""),
            sa.Column("chu_tk_cu", sa.String(160), server_default=""),
            sa.Column("so_tk_moi", sa.String(40), nullable=False),
            sa.Column("ngan_hang_moi", sa.String(120), server_default=""),
            sa.Column("chu_tk_moi", sa.String(160), server_default=""),
            sa.Column("ly_do", sa.String(300), server_default=""),
            sa.Column("chung_tu", sa.String(200), server_default=""),
            sa.Column("status", sa.String(20), server_default="cho_xac_nhan"),
            sa.Column("de_nghi_boi", sa.String(50), server_default=""),
            sa.Column("de_nghi_luc", sa.DateTime, nullable=True),
            sa.Column("xac_nhan_boi", sa.String(50), server_default=""),
            sa.Column("xac_nhan_luc", sa.DateTime, nullable=True),
            sa.Column("ghi_chu", sa.String(300), server_default=""),
        )
        op.create_index("ix_supplier_bank_changes_supplier", "supplier_bank_changes", ["supplier_id"])
    if "service_orders" not in ten:
        op.create_table(
            "service_orders",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String(30), nullable=False, unique=True),
            sa.Column("supplier_id", sa.Integer, nullable=False),
            sa.Column("tour_id", sa.Integer, nullable=False),
            sa.Column("loai", sa.String(20), server_default="khac"),
            sa.Column("noi_dung", sa.String(300), nullable=False),
            sa.Column("ngay_su_dung", sa.Date, nullable=True),
            sa.Column("so_luong", sa.Float, server_default="1"),
            sa.Column("don_vi", sa.String(30), server_default=""),
            sa.Column("don_gia", sa.Float, server_default="0"),
            sa.Column("thanh_tien", sa.Float, server_default="0"),
            sa.Column("status", sa.String(20), server_default="nhap"),
            sa.Column("xac_nhan_ncc", sa.String(200), server_default=""),
            sa.Column("payment_request_id", sa.Integer, nullable=True),
            sa.Column("note", sa.String(300), server_default=""),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("created_by", sa.String(50), server_default=""),
        )
        op.create_index("ix_service_orders_tour", "service_orders", ["tour_id"])
        op.create_index("ix_service_orders_supplier", "service_orders", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("service_orders")
    op.drop_table("supplier_bank_changes")
    op.drop_table("suppliers")
