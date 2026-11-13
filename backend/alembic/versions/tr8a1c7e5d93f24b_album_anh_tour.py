"""TR-8 · album ảnh tour trên cổng khách

Revision ID: tr8a1c7e5d93f24b
Revises: vx27a1c3e5f7b9d2
Create Date: 2026-11-13

Chủ tịch duyệt 13/11/2026. Đo được cùng ngày trên kh.vietourist.vn/tours: 13 trong 85 tour
KHÔNG có một tấm ảnh nào, và trong 33 tour đang có chuyến mở bán thì 22 tour thiếu ảnh. Nội
dung tour đọc từ vietourist.com.vn nên chất lượng ảnh bị chặn trần bởi web cũ — chỉ sửa được
bằng một cửa để phòng sản phẩm tải ảnh lên.

Bảng MỚI, không đụng cột nào đang có. Ảnh đọc từ web vẫn nằm nguyên trong products.noi_dung_web;
ảnh tải lên chỉ ĐỨNG TRƯỚC khi ghép danh sách cho cổng khách.

Ba khoá ngoại đều trỏ vào attachments: bản gốc (chỉ nội bộ), bản hiển thị ≤1600px, ảnh nhỏ
≤480px. Hai bản sau do máy tạo, đã xoá EXIF nên không rò toạ độ GPS của người chụp ra internet.
"""
import sqlalchemy as sa
from alembic import op

revision = "tr8a1c7e5d93f24b"
down_revision = "vx27a1c3e5f7b9d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "anh_tour",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("hien_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("nho_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("rong", sa.Integer(), server_default="0"),
        sa.Column("cao", sa.Integer(), server_default="0"),
        sa.Column("nhom", sa.String(20), server_default=""),
        sa.Column("chu_thich", sa.String(200), server_default=""),
        sa.Column("mo_ta_thay_the", sa.String(200), server_default=""),
        sa.Column("thu_tu", sa.Integer(), server_default="0"),
        sa.Column("la_bia", sa.Boolean(), server_default=sa.false()),
        sa.Column("can_cu", sa.String(20), server_default="chua_xac_minh"),
        sa.Column("can_cu_ghi_chu", sa.String(300), server_default=""),
        sa.Column("credit", sa.String(160), server_default=""),
        # KS-16c (31/10/2026) nhắc lại cho tour 13/11/2026: tải là hiện, không có bước duyệt.
        # Cột này còn để GỠ NHANH một tấm ảnh sai sang «an» mà không phải xoá hẳn.
        sa.Column("trang_thai", sa.String(12), server_default="da_duyet"),
        sa.Column("tai_boi", sa.String(50), server_default=""),
        sa.Column("tai_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_boi", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("anh_tour")
