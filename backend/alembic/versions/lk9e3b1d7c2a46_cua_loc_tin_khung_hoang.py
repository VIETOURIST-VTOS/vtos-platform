"""Cửa lọc tin khủng hoảng — bảng kết luận của người, và đường đi ngược về tin nguồn

Revision ID: lk9e3b1d7c2a46
Revises: pr4c9a1e7b2d58
Create Date: 2026-09-19

HAI THỨ, VÀ CẢ HAI ĐỀU LÀ THỨ MÁY KHÔNG TỰ BIẾT

1. `mkt_hop_thu_xu_ly` — người của Marketing đã KẾT LUẬN gì về một tin, và ĐIỂM bộ lọc nói ra lúc
   ấy. Chỉ dòng đã xử lý mới nằm đây: ghi cả trăm nghìn tin vào bảng này để lưu chữ "chưa xem" là
   nhân đôi bảng `messages` cho một thông tin suy ra được bằng phép trừ.

   `message_id` UNIQUE. Đó không phải trang trí: hai người cùng mở hàng đợi rồi cùng lập hai dòng
   PR cho một vụ là chuyện xảy ra đúng vào lúc đang có khủng hoảng thật, và bảng quá hạn đếm đôi
   thì con số "bao nhiêu vụ quá hạn" sai ngay ở vụ đầu tiên.

2. `mkt_pr_hoat_dong.nguon_message_id` — đường đi NGƯỢC từ một vụ đã xảy ra về cái tin lẽ ra phải
   báo động. Không có cột này thì không đo được "bộ lọc bỏ sót bao nhiêu", và một bộ lọc không đo
   được là một bộ lọc mòn dần trong im lặng.

   NULLABLE, và rỗng là bình thường: một vụ nổ trên báo thì không có tin nào trong hộp thư.
   `loc_khung_hoang.do_bo_loc()` đếm riêng phần ấy thay vì để nó rơi khỏi mẫu số và làm tỷ lệ đẹp
   lên.

`co_tu_do` dùng server_default=sa.false() — KHÔNG dùng sa.text("0"). Postgres không nhận "0" cho
kiểu boolean và bản di trú sẽ chết ngay lúc khởi động hộp chứa, không phải lúc chạy phép thử.
"""
import sqlalchemy as sa
from alembic import op

revision = "lk9e3b1d7c2a46"
down_revision = "pr4c9a1e7b2d58"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mkt_hop_thu_xu_ly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("diem_luc_do", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ly_do_luc_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("co_tu_do", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ket_luan", sa.String(length=10), nullable=False),
        sa.Column("pr_id", sa.Integer(), sa.ForeignKey("mkt_pr_hoat_dong.id"), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("nguoi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mkt_htxl_message", "mkt_hop_thu_xu_ly", ["message_id"], unique=True)
    op.create_index("ix_mkt_htxl_conv", "mkt_hop_thu_xu_ly", ["conversation_id"])

    op.add_column("mkt_pr_hoat_dong", sa.Column("nguon_message_id", sa.Integer(), nullable=True))
    op.create_index("ix_mkt_pr_nguon_msg", "mkt_pr_hoat_dong", ["nguon_message_id"])


def downgrade():
    op.drop_index("ix_mkt_pr_nguon_msg", table_name="mkt_pr_hoat_dong")
    op.drop_column("mkt_pr_hoat_dong", "nguon_message_id")
    op.drop_index("ix_mkt_htxl_conv", table_name="mkt_hop_thu_xu_ly")
    op.drop_index("ix_mkt_htxl_message", table_name="mkt_hop_thu_xu_ly")
    op.drop_table("mkt_hop_thu_xu_ly")
