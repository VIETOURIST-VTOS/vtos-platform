"""AT-2a — Album ảnh nhà hàng: nhiều ảnh, nhóm ảnh, căn cứ quyền dùng, TP Điều hành duyệt.

Ảnh đơn cũ (nha_hang.anh_id) chuyển vào album làm ảnh bìa, trạng thái «Chờ duyệt», căn cứ «Chưa xác minh»
— KHÔNG tự thành «Đã duyệt», nên thôi hiện trên cổng cho tới khi Điều hành ghi căn cứ và TP ĐH duyệt.
Không tắt nhà hàng nào. Cột nha_hang.anh_id giữ nguyên (không xóa) để quay lui được.

Revision ID: at2a7c1e9d4b58
Revises: at1d6f8b0c3e57
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "at2a7c1e9d4b58"
down_revision = "at1d6f8b0c3e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anh_nha_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nha_hang_id", sa.Integer(), sa.ForeignKey("nha_hang.id"), nullable=False),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=False),
        sa.Column("hien_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("nho_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("rong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nhom", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("chu_thich", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("mo_ta_thay_the", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("la_bia", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_cu", sa.String(length=20), nullable=False, server_default="chua_xac_minh"),
        sa.Column("can_cu_ghi_chu", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("credit", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=12), nullable=False, server_default="nhap"),
        sa.Column("ly_do_tra_lai", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("tai_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tai_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_anh_nha_hang_nha_hang_id", "anh_nha_hang", ["nha_hang_id"])
    # Chuyển ảnh đơn cũ: làm ảnh bìa, Chờ duyệt, Chưa xác minh — ghi lại nguồn cũ để Điều hành xem.
    op.execute(
        "INSERT INTO anh_nha_hang (nha_hang_id, attachment_id, hien_id, nho_id, nhom, la_bia, can_cu, can_cu_ghi_chu, "
        "trang_thai, tai_boi, thu_tu) "
        "SELECT id, anh_id, anh_id, anh_id, '', " + ("true" if op.get_bind().dialect.name == "postgresql" else "1")
        + ", 'chua_xac_minh', SUBSTR('Chuyển từ ảnh đơn cũ · nguồn ghi: ' || COALESCE(anh_nguon, ''), 1, 300), "
        "'cho_duyet', 'chuyển dữ liệu', 0 FROM nha_hang WHERE anh_id IS NOT NULL")


def downgrade() -> None:
    op.drop_index("ix_anh_nha_hang_nha_hang_id", table_name="anh_nha_hang")
    op.drop_table("anh_nha_hang")
