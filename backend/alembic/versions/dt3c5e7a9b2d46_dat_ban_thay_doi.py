"""DT-3 — đặt bàn: đổi lịch / số khách sau khi đặt, hoàn nhiều lần, ghi sổ thu hộ (phí thẻ, mã chứng từ).

Revision ID: dt3c5e7a9b2d46
Revises: dt2b4d6f8a1c35
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "dt3c5e7a9b2d46"
down_revision = "dt2b4d6f8a1c35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("don_dat_ban", sa.Column("so_lan_doi", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("don_dat_ban", sa.Column("thay_doi", sa.JSON(), nullable=True))
    op.add_column("don_dat_ban", sa.Column("thay_doi_luc", sa.DateTime(), nullable=True))
    op.add_column("don_dat_ban", sa.Column("thay_doi_ghi_chu", sa.Text(), nullable=False, server_default=""))
    op.add_column("don_dat_ban", sa.Column("huy_mien_phi", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("don_dat_ban", sa.Column("da_hoan_tien", TIEN, nullable=False, server_default="0"))
    op.add_column("thanh_toan_dat_ban", sa.Column("phi_the", TIEN, nullable=True))
    op.add_column("thanh_toan_dat_ban", sa.Column("but_toan", sa.String(length=30), nullable=False, server_default=""))


def downgrade() -> None:
    for c in ("but_toan", "phi_the"):
        op.drop_column("thanh_toan_dat_ban", c)
    for c in ("da_hoan_tien", "huy_mien_phi", "thay_doi_ghi_chu", "thay_doi_luc", "thay_doi", "so_lan_doi"):
        op.drop_column("don_dat_ban", c)
