"""TC-103: dau nguon quang cao

Revision ID: tc103dqc7f2a9e
Revises: hdv4d9a3c6e1b5
Create Date: 2026-10-07

MOT BANG MOI, khong doi bang nao san co - chay lui duoc sach se.

NOI VAO hdv4d9a3c6e1b5, la DAU DUY NHAT cua origin/main ngay 07/10/2026 (125 ban, mot dau).

BAN DAU TEP NAY NOI VAO tc83bm6d1a4f9c VA DO LA SAI - chep lai de lan sau khong ai di lai.
Con so ay dem duoc tren CAY LAM VIEC cua lan 1, thu da tut lai sau origin/main 13 ban: PR #210
(HDV dot 4) trong khoang ay da them hdv4d9a3c6e1b5 noi vao DUNG tc83bm6d1a4f9c. Hai ban cung mot
cha la HAI DAU, va `alembic upgrade head` dung lai voi "Multiple head revisions" - may chu khong
khoi dong duoc, trong khi CI cua ca hai PR deu xanh vi khong ban nao thay ban kia. Kho nay da
dinh dung loi ay mot lan ngay 23/9.

BAI HOC, mot cau: dem dau mach tren `git archive origin/main`, KHONG dem tren cay lam viec.

RANG BUOC DUY NHAT dat tren `khoa_chong_trung`, KHONG tren (nen_tang, loai_ma, ma). Ma rong la
hop le - mot cuoc goi vao hotline thuong khong co ma nao - va rang buoc kia se cho dung MOT dong
khong ma cho moi nen tang, tuc la chan chinh cuoc goi thu hai. Xem giai thich day du o
app/models/quang_cao.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "tc103dqc7f2a9e"
down_revision = "hdv4d9a3c6e1b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dau_quang_cao",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nen_tang", sa.String(24), nullable=False),
        sa.Column("loai_ma", sa.String(24), nullable=False),
        sa.Column("ma", sa.String(200), nullable=False, server_default=""),
        sa.Column("khoa_chong_trung", sa.String(160), nullable=False),
        sa.Column("ma_chien_dich", sa.String(64), nullable=True),
        sa.Column("ma_nhom_qc", sa.String(64), nullable=True),
        sa.Column("ma_mau_qc", sa.String(64), nullable=True),
        sa.Column("ten_chien_dich", sa.String(200), nullable=False, server_default=""),
        sa.Column("sdt", sa.String(20), nullable=False, server_default=""),
        sa.Column("zalo_uid", sa.String(40), nullable=False, server_default=""),
        sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("utm", sa.JSON, nullable=True),
        sa.Column("trang_dich", sa.String(500), nullable=False, server_default=""),
        sa.Column("trang_gioi_thieu", sa.String(500), nullable=False, server_default=""),
        sa.Column("cham_luc", sa.DateTime, nullable=True),
        sa.Column("nhan_luc", sa.DateTime, nullable=True),
        sa.Column("nguon_ghi", sa.String(24), nullable=False, server_default="khac"),
        sa.Column("than_nguyen_van", sa.Text, nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.String(300), nullable=False, server_default=""),
        sa.Column("boi", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index("ix_dqc_khoa", "dau_quang_cao", ["khoa_chong_trung"], unique=True)
    for cot in ("nen_tang", "loai_ma", "ma", "ma_chien_dich", "sdt", "zalo_uid", "lead_id",
                "cham_luc", "nhan_luc", "nguon_ghi"):
        op.create_index(f"ix_dqc_{cot}", "dau_quang_cao", [cot])


def downgrade() -> None:
    op.drop_table("dau_quang_cao")
