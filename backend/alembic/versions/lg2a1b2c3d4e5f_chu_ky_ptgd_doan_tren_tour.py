"""Dot LG2: them cot chu ky P.TGD tour doan tren bang tours.

Chu tich chot 11/10/2026 - chuyen duoi bien 10% doi nguoi ky: Chu tich RA KHOI LUAT, P.TGD tour
doan VAO. Cot `signed_chutich` O LAI va khong bi doi ten: chuyen da ky TRUOC ngay ay mang chu ky
Chu tich THAT, va ban nang cap nay KHONG doi du lieu cu sang cot moi. Doi la viet lai lich su.

Revision ID: lg2a1b2c3d4e5f
Revises: f1n7c3e9b2a54
"""
from alembic import op
import sqlalchemy as sa

revision = "lg2a1b2c3d4e5f"
down_revision = "f1n7c3e9b2a54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tours") as b:
        # `sa.false()` chu KHONG `sa.text("0")`: PostgreSQL tu choi so tho cho cot boolean
        # ("is of type boolean but default expression is of type integer") va `alembic upgrade
        # head` dung ngay do - container khong khoi dong duoc. Hang rao `test_mach_migration`
        # bat dung loi nay cua em o lan chay dau.
        b.add_column(sa.Column("signed_ptgd_doan", sa.Boolean(), nullable=False,
                               server_default=sa.false()))
    # Cot ghi TEN nguoi da ky tren de nghi chi. Dang "vai:ten,vai:ten"; doc bang
    # `chu_ky.doc_nguoi_da_ky`. RONG voi moi ho so lap truoc dot nay, va rong nghia la KHONG
    # BIET ai da ky chu khong phai chua ai ky - khong suy nguoc tu `approved_by` de dien vao,
    # vi `approved_by` chi ghi nguoi bam CUOI CUNG.
    with op.batch_alter_table("payment_requests") as b:
        b.add_column(sa.Column("nguoi_da_ky", sa.String(length=200), nullable=False,
                               server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.drop_column("nguoi_da_ky")
    with op.batch_alter_table("tours") as b:
        b.drop_column("signed_ptgd_doan")
