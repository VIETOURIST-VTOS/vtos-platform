\"\"\"Dot LG3: them o ghi TEN nguoi ky tren bang tours.

Chuyen duoi bien 10% nay ky theo MANG (Doan -> ptgd_doan, Le -> gd_kd), nen so vai co the ky
khong con co dinh. De moi vai mot cot boolean thi sau vai lan doi luat, bang co nam cot chu ky ma
ba cot luon rong. O nay ghi "vai:ten", doc bang `chu_ky.doc_nguoi_da_ky`.

Ba cot cu O LAI va van la su that cho chuyen da ky truoc day; phep tinh "du chu ky chua" doc CA
HAI nguon nen chuyen dang ky do giua hai dot khong mat chu ky da co.

Revision ID: lg3b2c3d4e5f6a
Revises: lg2a1b2c3d4e5f
\"\"\"
from alembic import op
import sqlalchemy as sa

revision = "lg3b2c3d4e5f6a"
down_revision = "lg2a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tours") as b:
        b.add_column(sa.Column("nguoi_da_ky", sa.String(length=200), nullable=False,
                               server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("tours") as b:
        b.drop_column("nguoi_da_ky")
