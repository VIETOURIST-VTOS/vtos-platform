"""TC-77: noi dong chi ngan sach Marketing vao chien dich

Revision ID: tc77dg9a8b7c6d
Revises: tc76ct5a6b7c8d
"""
import sqlalchemy as sa
from alembic import op

revision = "tc77dg9a8b7c6d"
down_revision = "tc76ct5a6b7c8d"   # noi SAU ban chi tieu kinh doanh cua TC-76
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
