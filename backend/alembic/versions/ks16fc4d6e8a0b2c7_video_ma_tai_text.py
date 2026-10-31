"""KS-16f2 — sửa tải video lên kho R2: cột ma_tai (UploadId multipart) đổi sang TEXT. R2 trả UploadId dài hơn
300 ký tự nên bước «bắt đầu tải» lỗi 500 trên CRM (31/10/2026).

Revision ID: ks16fc4d6e8a0b2c7
Revises: ks16fb7c9d1e3a5f2
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16fc4d6e8a0b2c7"
down_revision = "ks16fb7c9d1e3a5f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("video_dich_vu") as b:
        b.alter_column("ma_tai", type_=sa.Text(), existing_type=sa.String(300), existing_nullable=False,
                       existing_server_default="")


def downgrade() -> None:
    with op.batch_alter_table("video_dich_vu") as b:
        b.alter_column("ma_tai", type_=sa.String(300), existing_type=sa.Text(), existing_nullable=False,
                       existing_server_default="")
