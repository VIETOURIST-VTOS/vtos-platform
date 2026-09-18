"""Sổ hoạt động PR — bảng mới, và lần này bảng mới là đúng

Revision ID: pr4c9a1e7b2d58
Revises: th5b8e2c7a1d94
Create Date: 2026-09-18

Chủ tịch chốt 18/9/2026: người phát ngôn là P.TGĐ Marketing; khủng hoảng truyền thông phải có
phản hồi trong 2 GIỜ kể từ lúc việc được ghi vào sổ.

VÌ SAO BẢNG MỚI Ở ĐÂY, TRONG KHI SỔ TÀI SẢN THƯƠNG HIỆU CÙNG NGÀY LẠI DÙNG CHUNG

Sổ nhận diện dùng chung bảng TSCĐ vì một bộ nhận diện mua ngoài VỐN LÀ một thẻ tài sản — nó đã có
chỗ. Ở đây không có bảng nào đang giữ "một việc truyền thông đã xảy ra": `content_items` giữ BẢN
THẢO trước khi đăng (ô bản thảo, ô người duyệt, ô ngày dự kiến), còn sổ này ghi việc ĐÃ RA NGOÀI
và ai chịu trách nhiệm. Nhét vào `content_items` thì một bảng phải trả lời hai câu hỏi ngược chiều
nhau, và cột nào cũng phải để rỗng một nửa số dòng.

`ghi_nhan_luc` NOT NULL và có CHỈ MỤC: nó là mốc bắt đầu đếm hai giờ, và bộ lọc quá hạn quét theo
đúng cột ấy.
"""
import sqlalchemy as sa
from alembic import op

revision = "pr4c9a1e7b2d58"
down_revision = "th5b8e2c7a1d94"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mkt_pr_hoat_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=20), nullable=False),
        sa.Column("loai", sa.String(length=16), nullable=False),
        sa.Column("tieu_de", sa.String(length=300), nullable=False),
        sa.Column("tom_tat", sa.Text(), nullable=False, server_default=""),
        sa.Column("noi_dang", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("link", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="nhap"),
        sa.Column("nguoi_phat_ngon", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("phat_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_khong_phat", sa.String(length=300), nullable=False, server_default=""),
        # Cột Boolean thêm vào phải dùng sa.false(), KHÔNG phải sa.text("0") – PostgreSQL từ chối
        # DEFAULT 0 cho BOOLEAN và cả lệnh `alembic upgrade head` dừng ở đấy (đã xảy ra 14/9/2026).
        sa.Column("la_khung_hoang", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ghi_nhan_luc", sa.DateTime(), nullable=False),
        sa.Column("phan_hoi_luc", sa.DateTime(), nullable=True),
        sa.Column("phan_hoi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("muc_do", sa.String(length=12), nullable=False, server_default=""),
        sa.Column("nguoi_tao", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_mkt_pr_hoat_dong_ma", "mkt_pr_hoat_dong", ["ma"], unique=True)
    op.create_index("ix_mkt_pr_hoat_dong_ghi_nhan", "mkt_pr_hoat_dong", ["ghi_nhan_luc"])
    op.create_index("ix_mkt_pr_hoat_dong_campaign", "mkt_pr_hoat_dong", ["campaign_id"])


def downgrade():
    op.drop_index("ix_mkt_pr_hoat_dong_campaign", table_name="mkt_pr_hoat_dong")
    op.drop_index("ix_mkt_pr_hoat_dong_ghi_nhan", table_name="mkt_pr_hoat_dong")
    op.drop_index("ix_mkt_pr_hoat_dong_ma", table_name="mkt_pr_hoat_dong")
    op.drop_table("mkt_pr_hoat_dong")
