"""TC-105: hang doi chuyen doi gui di

Revision ID: tc105cdg3b8f1a
Revises: tc103dqc7f2a9e
Create Date: 2026-10-07

MOT BANG MOI, khong doi bang nao san co - chay lui duoc sach se.

Dau mach dem tren `git archive origin/main`, KHONG dem tren cay lam viec - bai hoc cua TC-103,
noi lan dau noi nham vao mot cha da bi PR khac chiem, suyt thanh hai dau mach va may chu khong
khoi dong duoc.

RANG BUOC DUY NHAT tren `khoa_chong_trung` = nen tang + ma booking + dau. Chay lai luot sinh
khong nhan doi; mot booking cham hai mau quang cao CUNG nen tang van la hai dong, vi hai mau ay
can hai loi bao rieng.
"""
from alembic import op
import sqlalchemy as sa

revision = "tc105cdg3b8f1a"
down_revision = "tc103dqc7f2a9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chuyen_doi_gui_di",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dau_id", sa.Integer, sa.ForeignKey("dau_quang_cao.id"), nullable=False),
        sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("nen_tang", sa.String(24), nullable=False),
        sa.Column("loai_ma", sa.String(24), nullable=False),
        sa.Column("ma", sa.String(200), nullable=False, server_default=""),
        sa.Column("ma_booking", sa.String(40), nullable=False),
        # RONG khac KHONG: chua doc duoc doanh thu thi de trong, tuyet doi khong ghi 0.
        sa.Column("doanh_thu", sa.Numeric(18, 2), nullable=True),
        sa.Column("tien_te", sa.String(3), nullable=False, server_default="VND"),
        sa.Column("chot_luc", sa.DateTime, nullable=True),
        sa.Column("trang_thai", sa.String(20), nullable=False, server_default="cho_gui"),
        sa.Column("lan_thu", sa.Integer, nullable=False, server_default="0"),
        sa.Column("loi_cuoi", sa.Text, nullable=False, server_default=""),
        sa.Column("gui_luc", sa.DateTime, nullable=True),
        sa.Column("tra_loi", sa.Text, nullable=False, server_default=""),
        sa.Column("khoa_chong_trung", sa.String(300), nullable=False),
        sa.Column("tao_luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_cdg_khoa", "chuyen_doi_gui_di", ["khoa_chong_trung"], unique=True)
    for cot in ("dau_id", "lead_id", "nen_tang", "ma_booking", "chot_luc", "trang_thai", "tao_luc"):
        op.create_index(f"ix_cdg_{cot}", "chuyen_doi_gui_di", [cot])


def downgrade() -> None:
    op.drop_table("chuyen_doi_gui_di")
