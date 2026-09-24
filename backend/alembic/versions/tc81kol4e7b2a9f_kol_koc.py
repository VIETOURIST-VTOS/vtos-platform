"""TC-81: KOL / KOC - danh ba nguoi hop tac noi dung va tung lan hop tac

Revision ID: tc81kol4e7b2a9f
Revises: tc77dg9a8b7c6d
Create Date: 2026-09-24

HAI BANG MOI, khong doi bang nao san co - nen ban nay chay lui duoc sach se.

NOI VAO tc77dg9a8b7c6d, la DAU DUY NHAT cua main luc viet (da dem: 110 ban, mot dau). Ngay 23/9
kho nay da mot lan co HAI DAU vi hai lan cung noi vao mot cha, va container khong khoi dong duoc
vi `alembic upgrade head` khong giai duoc - CI cua ca hai PR deu xanh vi khong ban nao thay ban
kia. Truoc khi viet dong nay da dem lai dau tu chinh thu muc versions.
"""
from alembic import op
import sqlalchemy as sa

revision = "tc81kol4e7b2a9f"
down_revision = "tc77dg9a8b7c6d"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "mkt_kol",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ma", sa.String(20), nullable=False),
        sa.Column("ho_ten", sa.String(160), nullable=False),
        sa.Column("biet_danh", sa.String(160), server_default=""),
        sa.Column("kenh", sa.String(16), nullable=False),
        sa.Column("link_kenh", sa.String(400), nullable=False),
        sa.Column("luong_theo_doi", sa.Integer, nullable=True),
        sa.Column("theo_doi_do_ngay", sa.Date, nullable=True),
        sa.Column("gia_tham_khao", TIEN, nullable=True),
        sa.Column("nguoi_lien_he", sa.String(160), server_default=""),
        sa.Column("dien_thoai", sa.String(30), server_default=""),
        sa.Column("email", sa.String(120), server_default=""),
        sa.Column("trang_thai", sa.String(14), server_default="dang_hop_tac"),
        sa.Column("ly_do_ngung", sa.String(300), server_default=""),
        sa.Column("ghi_chu", sa.Text, server_default=""),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("nguoi_tao", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime, server_default=sa.func.now()),
        # Mot KOL la mot KENH - xem ghi chu dau models/kol.py. Chan ban khai lap cua CUNG mot kenh;
        # KHONG chan trung ten, vi hai nguoi that co the trung ten.
        sa.UniqueConstraint("kenh", "link_kenh", name="uq_mkt_kol_kenh_link"),
    )
    op.create_index("ix_mkt_kol_ma", "mkt_kol", ["ma"], unique=True)
    op.create_index("ix_mkt_kol_company_id", "mkt_kol", ["company_id"])

    op.create_table(
        "mkt_kol_hop_tac",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kol_id", sa.Integer, sa.ForeignKey("mkt_kol.id"), nullable=False),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("loai", sa.String(14), server_default="bai_dang"),
        sa.Column("noi_dung", sa.String(300), nullable=False),
        sa.Column("link_bai", sa.String(400), server_default=""),
        sa.Column("ngay_dang", sa.Date, nullable=True),
        # RONG KHAC KHONG - khong server_default, khong NOT NULL. "Chua thoa thuan gia" phai khac
        # duoc "khong mat tien". Xem ghi chu o models/kol.py.
        sa.Column("chi_phi", TIEN, nullable=True),
        sa.Column("payment_request_id", sa.Integer, sa.ForeignKey("payment_requests.id"),
                  nullable=True),
        sa.Column("trang_thai", sa.String(10), server_default="du_kien"),
        sa.Column("ly_do_huy", sa.String(300), server_default=""),
        sa.Column("luot_xem", sa.Integer, nullable=True),
        sa.Column("luot_tuong_tac", sa.Integer, nullable=True),
        sa.Column("so_lead_khai", sa.Integer, nullable=True),
        sa.Column("ghi_chu", sa.Text, server_default=""),
        sa.Column("nguoi_tao", sa.String(50), server_default=""),
        sa.Column("tao_luc", sa.DateTime, server_default=sa.func.now()),
        sa.Column("sua_boi", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_mkt_kol_hop_tac_kol_id", "mkt_kol_hop_tac", ["kol_id"])
    op.create_index("ix_mkt_kol_hop_tac_campaign_id", "mkt_kol_hop_tac", ["campaign_id"])
    op.create_index("ix_mkt_kol_hop_tac_ky", "mkt_kol_hop_tac", ["ky"])
    op.create_index("ix_mkt_kol_hop_tac_pr", "mkt_kol_hop_tac", ["payment_request_id"])


def downgrade() -> None:
    op.drop_table("mkt_kol_hop_tac")
    op.drop_table("mkt_kol")
