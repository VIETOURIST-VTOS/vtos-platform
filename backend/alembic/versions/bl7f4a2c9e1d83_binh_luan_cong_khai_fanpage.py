"""Bình luận công khai Fanpage — bảng riêng, và hàng đợi nhận hai nguồn

Revision ID: bl7f4a2c9e1d83
Revises: lk9e3b1d7c2a46
Create Date: 2026-09-19

BA THAY ĐỔI

1. `mkt_fb_binh_luan` — bình luận dưới bài đăng Fanpage. Bảng RIÊNG, không đổ vào `messages`:
   `inbox.get_or_create` tạo một Lead cho mỗi hội thoại mới, nên đổ vào đó thì mỗi người bình luận
   thành một lead giả và tỷ lệ chốt lead của Sales bị pha loãng bằng thứ không phải lead. Xem đầy
   đủ ở app/models/marketing.py.

   `comment_id` UNIQUE: webhook của Facebook có thể gửi lại cùng một sự kiện, và không có khoá này
   thì một bình luận thành ba dòng.

2. `mkt_hop_thu_xu_ly` nhận HAI NGUỒN. `message_id` chuyển sang NULLABLE và thêm `binh_luan_id`,
   mỗi cột một khoá ngoại thật, cộng một cột `nguon` nói cột nào đang mang giá trị.

   ĐÃ CÂN NHẮC một cặp (loại, mã) chung cho gọn và BỎ: cặp chung vứt mất ràng buộc khoá ngoại, nên
   một mã trỏ vào hư không thì cơ sở dữ liệu không kêu, và ba tháng sau hàng đợi có những dòng
   không mở ra được.

   Bảng này mới dựng hôm qua và gần như chưa có dòng nào, nên đổi bây giờ rẻ. Để sang tháng sau
   thì phải chuyển dữ liệu.

   Ở Postgres, chỉ mục UNIQUE trên cột nullable cho phép NHIỀU dòng NULL — đúng thứ cần: mọi dòng
   nguồn "bình luận" đều có `message_id` rỗng.

3. `mkt_pr_hoat_dong.nguon_binh_luan_id` — đường đi ngược từ một vụ về bình luận đã sinh ra nó,
   cùng vai trò với `nguon_message_id`. Không có nó thì phép đo "bộ lọc bỏ sót bao nhiêu" mù đúng
   ở nửa nguy hiểm hơn.
"""
import sqlalchemy as sa
from alembic import op

revision = "bl7f4a2c9e1d83"
down_revision = "lk9e3b1d7c2a46"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mkt_fb_binh_luan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.String(length=64), nullable=False),
        sa.Column("post_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("parent_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("page_id", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("tac_gia_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tac_gia_ten", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("link", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("la_cua_page", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("da_sua", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("da_xoa", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("nhan_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mkt_bl_comment", "mkt_fb_binh_luan", ["comment_id"], unique=True)
    op.create_index("ix_mkt_bl_post", "mkt_fb_binh_luan", ["post_id"])
    op.create_index("ix_mkt_bl_tao_luc", "mkt_fb_binh_luan", ["tao_luc"])

    op.add_column("mkt_hop_thu_xu_ly",
                  sa.Column("nguon", sa.String(length=10), nullable=False, server_default="tin"))
    op.add_column("mkt_hop_thu_xu_ly", sa.Column("binh_luan_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_htxl_binh_luan", "mkt_hop_thu_xu_ly", "mkt_fb_binh_luan",
                          ["binh_luan_id"], ["id"])
    op.create_index("ix_mkt_htxl_binh_luan", "mkt_hop_thu_xu_ly", ["binh_luan_id"], unique=True)
    op.alter_column("mkt_hop_thu_xu_ly", "message_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("mkt_hop_thu_xu_ly", "conversation_id", existing_type=sa.Integer(),
                    nullable=True)

    op.add_column("mkt_pr_hoat_dong", sa.Column("nguon_binh_luan_id", sa.Integer(), nullable=True))
    op.create_index("ix_mkt_pr_nguon_bl", "mkt_pr_hoat_dong", ["nguon_binh_luan_id"])


def downgrade():
    op.drop_index("ix_mkt_pr_nguon_bl", table_name="mkt_pr_hoat_dong")
    op.drop_column("mkt_pr_hoat_dong", "nguon_binh_luan_id")
    op.alter_column("mkt_hop_thu_xu_ly", "conversation_id", existing_type=sa.Integer(),
                    nullable=False)
    op.alter_column("mkt_hop_thu_xu_ly", "message_id", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_mkt_htxl_binh_luan", table_name="mkt_hop_thu_xu_ly")
    op.drop_constraint("fk_htxl_binh_luan", "mkt_hop_thu_xu_ly", type_="foreignkey")
    op.drop_column("mkt_hop_thu_xu_ly", "binh_luan_id")
    op.drop_column("mkt_hop_thu_xu_ly", "nguon")
    op.drop_index("ix_mkt_bl_tao_luc", table_name="mkt_fb_binh_luan")
    op.drop_index("ix_mkt_bl_post", table_name="mkt_fb_binh_luan")
    op.drop_index("ix_mkt_bl_comment", table_name="mkt_fb_binh_luan")
    op.drop_table("mkt_fb_binh_luan")
