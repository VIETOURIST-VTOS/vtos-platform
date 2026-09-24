"""TC-83: bia mo tai khoan da xoa

Revision ID: tc83bm6d1a4f9c
Revises: tc81kol4e7b2a9f
Create Date: 2026-09-24

MOT BANG MOI, khong doi bang nao san co - chay lui duoc sach se.

NOI VAO tc81kol4e7b2a9f, la DAU DUY NHAT cua main luc viet. Ngay 23/9 kho nay da mot lan co HAI
DAU vi hai lan cung noi vao mot cha, va container khong khoi dong duoc vi `alembic upgrade head`
khong giai duoc - CI cua ca hai PR deu xanh vi khong ban nao thay ban kia. Truoc khi viet dong
nay da dem lai dau tu chinh thu muc versions.

TEN DANG NHAP KHONG DAT DUY NHAT, co y. Mot ten dang nhap co the duoc cap lai cho nguoi khac sau
nay; rang buoc duy nhat se chan dung lan xoa thu hai, tuc la chan viec ghi lai su that.
"""
from alembic import op
import sqlalchemy as sa

revision = "tc83bm6d1a4f9c"
down_revision = "tc81kol4e7b2a9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tai_khoan_da_xoa",
        sa.Column("id", sa.Integer, primary_key=True),
        # KHONG phai khoa ngoai toi users.id: hang da bien mat, khoa ngoai se chan chinh viec ghi.
        sa.Column("user_id_cu", sa.Integer, nullable=False),
        sa.Column("tai_khoan", sa.String(50), nullable=False),
        sa.Column("ho_ten", sa.String(160), nullable=False),
        sa.Column("ma_nv", sa.String(30), server_default=""),
        sa.Column("vai", sa.String(30), server_default=""),
        sa.Column("da_gop_vao", sa.String(50), server_default=""),
        sa.Column("ly_do", sa.Text, server_default=""),
        sa.Column("xoa_boi", sa.String(50), nullable=False),
        sa.Column("xoa_luc", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tai_khoan_da_xoa_user_id_cu", "tai_khoan_da_xoa", ["user_id_cu"])
    op.create_index("ix_tai_khoan_da_xoa_tai_khoan", "tai_khoan_da_xoa", ["tai_khoan"])
    op.create_index("ix_tai_khoan_da_xoa_xoa_luc", "tai_khoan_da_xoa", ["xoa_luc"])


def downgrade() -> None:
    op.drop_table("tai_khoan_da_xoa")
