"""Kho tệp & hình ảnh đính kèm dùng chung cho mọi phòng ban

Trước bản này chỉ phân hệ Visa có chỗ cất tài liệu; chứng từ của các phòng khác nằm trong Zalo, trong
email, trong máy của người giữ hồ sơ. Bảng này cho mọi phân hệ một chỗ cất chung, kèm mã băm nội dung để
đối chiếu và cờ thu hồi thay cho việc xóa cứng.

Chỉ mục duy nhất (đối tượng, mã bản ghi, mã băm) là thứ làm cho việc tải lại đúng tấm ảnh cũ không sinh
ra bản thứ hai – không phải để tiết kiệm chỗ, mà để người đọc hồ sơ không phải đoán hai bản giống nhau
khác nhau ở đâu.

Revision ID: b7c8d9e0f1a2
Revises: c2d3e4f5a6b7
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "attachments" in insp.get_table_names():
        return
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doi_tuong", sa.String(30), nullable=False),
        sa.Column("doi_tuong_id", sa.String(60), nullable=False),
        sa.Column("phong_ban", sa.String(20), server_default=""),
        sa.Column("loai", sa.String(20), server_default="chung_tu"),
        sa.Column("ten_tep", sa.String(200), nullable=False),
        sa.Column("kieu_noi_dung", sa.String(80), server_default=""),
        sa.Column("kich_thuoc", sa.Integer, server_default="0"),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("khoa_luu", sa.String(200), nullable=False),
        sa.Column("la_anh", sa.Boolean, server_default=sa.false()),
        sa.Column("mo_ta", sa.Text, server_default=""),
        sa.Column("nguon", sa.String(20), server_default="nguoi_nhap"),
        sa.Column("tac_nhan", sa.String(80), server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime, server_default=sa.func.now()),
        sa.Column("thu_hoi", sa.Boolean, server_default=sa.false()),
        sa.Column("thu_hoi_boi", sa.String(50), server_default=""),
        sa.Column("thu_hoi_luc", sa.DateTime, nullable=True),
        sa.Column("ly_do_thu_hoi", sa.String(200), server_default=""),
    )
    op.create_index("ix_attachments_doi_tuong", "attachments", ["doi_tuong", "doi_tuong_id"])
    op.create_index("ix_attachments_checksum", "attachments", ["checksum"])
    op.create_index("ux_attachments_noi_dung", "attachments",
                    ["doi_tuong", "doi_tuong_id", "checksum"], unique=True)


def downgrade() -> None:
    op.drop_table("attachments")
