"""V2 – bảng bản nháp do máy đọc từ ảnh chứng từ

Revision ID: v2d4a8f1c6e2
Revises: v4b1e7a2c9d3
Create Date: 2026-09-08

Bảng RIÊNG chứ không phải một cờ "chờ duyệt" trên bảng đích. Một cờ là lời hứa rằng mọi truy vấn về
sau sẽ nhớ lọc nó ra; chỉ cần một báo cáo quên điều kiện lọc là số máy đọc chưa ai nhìn đã nằm trong
một con số công bố. Bảng riêng thì cái quên đó không xảy ra được.

`dang_cho` là cột phụ trợ cho chỉ mục duy nhất: bằng băm ảnh khi còn chờ, NULL khi đã xử lý. NULL
không đụng chỉ mục duy nhất ở cả SQLite lẫn PostgreSQL, nên một ảnh xử lý xong vẫn đọc lại được, mà
cùng lúc chỉ có đúng một bản đang chờ cho mỗi ảnh.
"""
from alembic import op
import sqlalchemy as sa

revision = "v2d4a8f1c6e2"
down_revision = "v4b1e7a2c9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ban_doc_chung_tu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(length=30), nullable=False, index=True),
        sa.Column("bo_nap", sa.String(length=30), nullable=False),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("checksum_anh", sa.String(length=64), nullable=False, index=True),
        sa.Column("ai_run_id", sa.Integer(), sa.ForeignKey("ai_runs.id"), nullable=True),
        sa.Column("mo_hinh", sa.String(length=60), server_default="", nullable=False),
        sa.Column("so_may_doc", sa.JSON(), nullable=True),
        sa.Column("truong_khong_doc_duoc", sa.JSON(), nullable=True),
        sa.Column("ghi_chu_may", sa.Text(), server_default="", nullable=False),
        sa.Column("trang_thai", sa.String(length=16), server_default="nhap", nullable=False),
        sa.Column("dang_cho", sa.String(length=64), nullable=True),
        sa.Column("so_da_sua", sa.JSON(), nullable=True),
        sa.Column("truong_da_sua", sa.JSON(), nullable=True),
        sa.Column("xac_nhan_boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("xac_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("ket_qua_ghi", sa.String(length=300), server_default="", nullable=False),
        sa.Column("intake_run_id", sa.Integer(), nullable=True),
        sa.Column("ly_do_bo", sa.String(length=300), server_default="", nullable=False),
        sa.Column("boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_ban_doc_dang_cho", "ban_doc_chung_tu",
                    ["loai", "checksum_anh", "dang_cho"], unique=True)
    op.create_index("ix_ban_doc_trang_thai", "ban_doc_chung_tu", ["trang_thai", "loai"])


def downgrade() -> None:
    op.drop_index("ix_ban_doc_trang_thai", table_name="ban_doc_chung_tu")
    op.drop_index("ux_ban_doc_dang_cho", table_name="ban_doc_chung_tu")
    op.drop_table("ban_doc_chung_tu")
