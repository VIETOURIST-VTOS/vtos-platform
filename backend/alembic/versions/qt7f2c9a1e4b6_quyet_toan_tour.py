"""Quyết toán tour theo điều hành: bảng riêng để giá vốn có thể RỖNG

495 chuyến hai tháng 7–8/2026 với 48.042.594.678 đ hiện vào VTOS bằng đồng bộ Vietrip hoặc gõ tay.

Vì sao không ghi thẳng vào bảng tours: cột giá vốn ở đó là Float mặc định 0, không có cách nào nói
"chưa có số". Mà đúng chỗ đó là chỗ hỏng — trong hai tệp thật có 76 dòng doanh thu 2.654.940.111 đ để
giá vốn bằng 0. Một cột không phân biệt được "0 đồng" với "chưa ai điền" là sổ báo lãi 100% trên 2,65
tỷ, và bảng vẫn cân nên không ai nhìn ra.

Cột phan_loai tách 60 dòng khách lẻ (bảo lưu do hủy tour, gia hạn visa, vé) khỏi 16 dòng tour thật sự
thiếu giá vốn. Gộp làm một thì hàng đợi lúc nào cũng đầy dòng không ai sửa được, và người ta thôi mở nó.

Mã bản này KHÔNG đặt theo dãy chữ cái như các bản trước: dãy đó đã dùng hết và bản đầu tiên tôi chọn
(a3b4c5d6e7f8) trùng đúng mã của phân hệ Visa. Alembic không báo trùng — nó âm thầm nhận một bản và
sinh ra CHU TRÌNH trong mạch, làm hỏng cả bộ. Kèm bản này là một phép thử canh mã trùng.

Revision ID: qt7f2c9a1e4b6
Revises: b5e2c7a913d0
"""
from alembic import op
import sqlalchemy as sa

revision = "qt7f2c9a1e4b6"
down_revision = "b5e2c7a913d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "tour_settlements" in insp.get_table_names():
        return
    op.create_table(
        "tour_settlements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("ma_tour", sa.String(60), nullable=False),
        sa.Column("ten_tour", sa.String(300), server_default=""),
        sa.Column("loai", sa.String(20), server_default="tour"),
        sa.Column("dieu_hanh", sa.String(120), server_default=""),
        sa.Column("operator_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sale", sa.String(120), server_default=""),
        sa.Column("ngay_kh", sa.Date, nullable=True),
        sa.Column("ngay_kt", sa.Date, nullable=True),
        sa.Column("doanh_thu", sa.Float, server_default="0"),
        # NULL = chưa có số. Đây là lý do tồn tại của cả bảng này.
        sa.Column("gia_von", sa.Float, nullable=True),
        sa.Column("trang_thai_qt", sa.String(20), server_default="du_toan"),
        sa.Column("phan_loai", sa.String(30), server_default=""),
        sa.Column("phan_loai_boi", sa.String(50), server_default=""),
        sa.Column("phan_loai_luc", sa.DateTime, nullable=True),
        sa.Column("han_bao_luu", sa.Date, nullable=True),
        sa.Column("ghi_chu", sa.Text, server_default=""),
        sa.Column("nguon", sa.String(30), server_default="nap_tep"),
        sa.Column("ten_tep", sa.String(200), server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ux_tour_settlements_ma", "tour_settlements", ["ma_tour"], unique=True)
    op.create_index("ix_tour_settlements_ky", "tour_settlements", ["ky"])


def downgrade() -> None:
    op.drop_table("tour_settlements")
