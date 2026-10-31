"""KS-16g — VTD Rewards theo đề xuất v3 (Chủ tịch duyệt 31/10/2026): loại voucher, ngày sinh, mã giới thiệu,
bảng giới thiệu khách. Chỉ thêm cột / bảng.

Revision ID: ks16gd2f4a6c8e0b3
Revises: ks16fc4d6e8a0b2c7
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "ks16gd2f4a6c8e0b3"
down_revision = "ks16fc4d6e8a0b2c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("voucher_rewards") as b:
        b.add_column(sa.Column("loai", sa.String(12), nullable=False, server_default="doi_diem"))
        b.add_column(sa.Column("pham_vi", sa.String(10), nullable=False, server_default="tat_ca"))
        b.add_column(sa.Column("don_toi_thieu", sa.BigInteger(), nullable=False, server_default="0"))
    with op.batch_alter_table("tai_khoan_ngoai") as b:
        b.add_column(sa.Column("ngay_sinh", sa.Date(), nullable=True))
        b.add_column(sa.Column("ngay_sinh_luc", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("ma_gioi_thieu", sa.String(12), nullable=True))
        b.create_unique_constraint("uq_tkn_ma_gioi_thieu", ["ma_gioi_thieu"])
    op.create_table(
        "gioi_thieu_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chu_gioi_thieu", sa.String(80), nullable=False),
        sa.Column("tai_khoan_gioi_thieu_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, unique=True),
        sa.Column("chu_duoc", sa.String(80), nullable=False),
        sa.Column("ma", sa.String(12), nullable=False),
        sa.Column("trang_thai", sa.String(12), nullable=False, server_default="cho"),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("ghi_chu", sa.String(200), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_gioi_thieu_rewards_chu_gioi_thieu", "gioi_thieu_rewards", ["chu_gioi_thieu"])
    op.create_index("ix_gioi_thieu_rewards_chu_duoc", "gioi_thieu_rewards", ["chu_duoc"])


def downgrade() -> None:
    op.drop_index("ix_gioi_thieu_rewards_chu_duoc", "gioi_thieu_rewards")
    op.drop_index("ix_gioi_thieu_rewards_chu_gioi_thieu", "gioi_thieu_rewards")
    op.drop_table("gioi_thieu_rewards")
    with op.batch_alter_table("tai_khoan_ngoai") as b:
        b.drop_constraint("uq_tkn_ma_gioi_thieu", type_="unique")
        b.drop_column("ma_gioi_thieu")
        b.drop_column("ngay_sinh_luc")
        b.drop_column("ngay_sinh")
    with op.batch_alter_table("voucher_rewards") as b:
        b.drop_column("don_toi_thieu")
        b.drop_column("pham_vi")
        b.drop_column("loai")
