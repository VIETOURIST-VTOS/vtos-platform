"""CT-1 · 4.4.2 Chương trình của TỪNG CHUYẾN: hai bảng, cả hai tạo ra RỖNG.

Trước bản này tab Thông tin in nguyên văn `products.program` — chương trình của SẢN PHẨM, dùng
chung cho mọi chuyến cùng mã. Sửa nó là sửa chương trình của mọi chuyến, kể cả chuyến đã đi xong.

KHÔNG CHÉP SẴN DỮ LIỆU KHI CHẠY MIGRATION. Không một dòng `INSERT ... SELECT program FROM products`
nào ở đây, dù nó rất dễ viết và trông rất tiện: chép hàng loạt là ghi vào sổ của hàng trăm chuyến
một nội dung mà không người điều hành nào đọc qua. Việc chép xảy ra khi người điều hành MỞ tab
chương trình của chuyến ấy, và màn hình nói rõ nó vừa chép từ đâu.

Revision ID: ct1f6b2d8a4e93
Revises: vb1e7c3a9d5f24
"""
import sqlalchemy as sa
from alembic import op

revision = "ct1f6b2d8a4e93"
down_revision = "lg3b2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chuong_trinh_tour",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("nguon", sa.String(20), server_default="chua_soan", nullable=False),
        sa.Column("product_id_goc", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("ban_san_pham_goc", sa.Text(), server_default=""),
        sa.Column("chep_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_boi", sa.String(50), server_default=""),
        sa.Column("sua_cuoi_boi", sa.String(50), server_default=""),
        sa.Column("sua_cuoi_luc", sa.DateTime(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_chuong_trinh_tour", "chuong_trinh_tour", ["tour_id"])
    op.create_index("ix_chuong_trinh_tour_tour_id", "chuong_trinh_tour", ["tour_id"])

    op.create_table(
        "chuong_trinh_ngay",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("ngay_thu", sa.Integer(), nullable=False),
        sa.Column("ngay", sa.Date(), nullable=True),
        sa.Column("tieu_de", sa.String(200), server_default=""),
        sa.Column("noi_dung", sa.Text(), server_default=""),
        sa.Column("bua_sang", sa.Boolean(), server_default=sa.false()),
        sa.Column("bua_trua", sa.Boolean(), server_default=sa.false()),
        sa.Column("bua_toi", sa.Boolean(), server_default=sa.false()),
        sa.Column("khach_san", sa.String(200), server_default=""),
        sa.Column("phuong_tien", sa.String(120), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("lan_sua_sau_khoi_hanh", sa.Integer(), server_default="0"),
        sa.Column("ly_do_sua_gan_nhat", sa.Text(), server_default=""),
        sa.Column("sua_boi", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    # Một chuyến, một ngày thứ N, đúng MỘT dòng. Không có ràng buộc này thì hai lần bấm "dựng khung"
    # đẻ ra hai bộ ngày chồng nhau, và màn hình in ra một lịch trình có hai ngày 1.
    op.create_unique_constraint("uq_chuong_trinh_tour_ngay", "chuong_trinh_ngay",
                                ["tour_id", "ngay_thu"])
    op.create_index("ix_chuong_trinh_ngay_tour_id", "chuong_trinh_ngay", ["tour_id"])


def downgrade() -> None:
    op.drop_table("chuong_trinh_ngay")
    op.drop_table("chuong_trinh_tour")
