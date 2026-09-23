"""TC-77: noi dong chi ngan sach Marketing vao chien dich

Revision ID: tc77dg9a8b7c6d
Revises: tc76ct5a6b7c8d
"""
import sqlalchemy as sa
from alembic import op

revision = "tc77dg9a8b7c6d"
# SUA 24/9/2026 - NOI LAI MACH, ban nay tung lam main co HAI DAU.
#
# TC-77 va lan bao dong khung hoang (bd5a2f8c1e94) cung noi vao tc76ct5a6b7c8d, moi ban dung
# tren goc cua rieng minh nen CI cua tung PR deu xanh. Gop ca hai vao main thi mach co hai
# dau, va `alembic upgrade head` trong Dockerfile khong chay duoc - container khong khoi dong.
#
# PR #128 (bao dong) gop TRUOC PR #127 (TC-77), nen ban viet sau la ban nay, va ban nay phai
# noi tiep. Doi down_revision cua CHINH TEP MINH, khong dung tep cua lan kia.
#
# BAI HOC DA GHI MOT LAN NGAY 19/9 va lap lai hom nay: hai lan gop lien nhau trong mot ngay
# thi cua hep `hang-rao-gop` tren main la cho duy nhat bat duoc, vi CI cua tung PR khong the
# thay ban nang cap cua lan kia.
down_revision = "bd5a2f8c1e94"
branch_labels = None
depends_on = None

# MOT COT MOI, RONG. Khong dong mot dong du lieu nao.
#
# Anh Tuan chot 23/9/2026: noi chi vao chien dich de tra loi duoc "chien dich nay tieu that bao
# nhieu, thu ve bao nhieu". Truoc do chi chi chia theo thang x hang muc, nen hieu qua tung chien
# dich chi so duoc voi ngan sach DU KIEN chu khong voi tien DA tieu.
#
# KHONG SUY NGUOC CHO CAC DONG CU, va day khong phai chuyen luoi. Doan "hang muc Facebook thang 9
# chac la cua chien dich CD2609-01" la bia so lieu - ranh gioi 09/9/2026. Cot nay rong cho moi
# dong da nhap truoc hom nay; Marketing gan tay dan, va phan chua gan hien rieng o `chi_chua_gan`
# chu khong bi chia deu cho cac chien dich de bang trong can.


def upgrade() -> None:
    op.add_column("mkt_budget_lines",
                  sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=True))
    op.create_index("ix_mkt_budget_lines_campaign_id", "mkt_budget_lines", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_mkt_budget_lines_campaign_id", table_name="mkt_budget_lines")
    op.drop_column("mkt_budget_lines", "campaign_id")
