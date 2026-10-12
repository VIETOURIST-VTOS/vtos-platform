"""Dot E4a: dieu khoan thanh toan va dot thanh toan.

HAI BANG MOI va MOT COT them vao `nghia_vu_thanh_toan`:

  · dieu_khoan_thanh_toan - thoa thuan tra tien, khai mot lan dung cho nhieu hop dong.
    Cac dot cua no la mot KHUON luu dang JSON (ty le, lech ngay, dien giai), khong mang tien.
  · dot_thanh_toan        - dot THAT cua mot nghia vu: mot han, mot so tien, mot phan da tra.
    Chi muc DUY NHAT tren (nghia_vu_id, so_thu_tu): mot lan dung lai dot ma quen xoa dot cu se
    nhan doi tien cua ca nghia vu, va tong van trong hop ly.
  · nghia_vu_thanh_toan.dieu_khoan_id - nghia vu nay dung dieu khoan nao. RONG duoc: so cu khong
    co dieu khoan nao ca, va dat mot dieu khoan mac dinh cho chung la bia ra mot thoa thuan.

KHONG NAP LAI GI CHO SO CU, va day la chu y. Mot nghia vu cu co MOT `ngay_cam_ket` nhap tay; dung
no de dung MOT dot thi tong cac dot bang tong nghia vu that, nhung `can_cu_han` se rong - mot dot
khong biet han cua no tu dau ma ra. Dung hon la de so cu nguyen nhu no dang la: mot nghia vu
khong co dot nao van doc duoc y nhu truoc dot nay, vi `con_lai()` cua nghia vu khong doi.

COT TIEN DUNG Numeric(18, 2) - cung kieu `TIEN` ma `nghia_vu_thanh_toan` dang dung (V9 doi tam cot
tien sang so thap phan 08/9/2026). Khai Float o day la dung lai dung cai da sua.

Revision ID: e4a1b2c3d4e5
Revises: hq1c6f2a8e4b37
"""
from alembic import op
import sqlalchemy as sa

revision = "e4a1b2c3d4e5"
down_revision = "hq1c6f2a8e4b37"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "dieu_khoan_thanh_toan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=40), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("moc", sa.String(length=20), nullable=False),
        sa.Column("dot", sa.JSON(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("nguoi_da_ky", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("proposed_by", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_dieu_khoan_ma", "dieu_khoan_thanh_toan", ["ma"], unique=True)
    op.create_index("ix_dieu_khoan_status", "dieu_khoan_thanh_toan", ["status"])

    op.create_table(
        "dot_thanh_toan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nghia_vu_id", sa.Integer(), sa.ForeignKey("nghia_vu_thanh_toan.id"), nullable=False),
        sa.Column("so_thu_tu", sa.Integer(), nullable=False),
        sa.Column("dien_giai", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("da_tra", TIEN, nullable=True),
        sa.Column("ngay_han", sa.Date(), nullable=True),
        sa.Column("ngay_han_suy", sa.Date(), nullable=True),
        sa.Column("can_cu_han", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dot_nghia_vu", "dot_thanh_toan", ["nghia_vu_id"])
    op.create_index("ux_dot_nghia_vu_stt", "dot_thanh_toan", ["nghia_vu_id", "so_thu_tu"], unique=True)
    op.create_index("ix_dot_han", "dot_thanh_toan", ["ngay_han"])

    with op.batch_alter_table("nghia_vu_thanh_toan") as b:
        b.add_column(sa.Column("dieu_khoan_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nghia_vu_thanh_toan") as b:
        b.drop_column("dieu_khoan_id")
    op.drop_index("ix_dot_han", table_name="dot_thanh_toan")
    op.drop_index("ux_dot_nghia_vu_stt", table_name="dot_thanh_toan")
    op.drop_index("ix_dot_nghia_vu", table_name="dot_thanh_toan")
    op.drop_table("dot_thanh_toan")
    op.drop_index("ix_dieu_khoan_status", table_name="dieu_khoan_thanh_toan")
    op.drop_index("ux_dieu_khoan_ma", table_name="dieu_khoan_thanh_toan")
    op.drop_table("dieu_khoan_thanh_toan")
