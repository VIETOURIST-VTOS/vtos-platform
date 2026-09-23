"""TC-77: noi dong chi ngan sach Marketing vao chien dich

Revision ID: tc77dg9a8b7c6d
Revises: bd5a2f8c1e94
"""
import sqlalchemy as sa
from alembic import op

revision = "tc77dg9a8b7c6d"
# 23/9/2026 - SUA MOT DONG, doi gia tri chu khong doi y dinh cua TC-77.
#
# Ban nay va bd5a2f8c1e94 (bao dong khung hoang, PR #128) CUNG noi vao tc76ct5a6b7c8d. Moi
# nhanh rieng le chi co MOT dau nen ca hai PR deu xanh; gop lai thanh HAI DAU, va alembic tu
# choi chay khi co hon mot dau - hop chua API se khong khoi dong duoc o lan trien khai toi.
#
# Noi sau bd5a2f8c1e94 vi ban ay vao kho truoc (PR #128 gop luc 17:06, PR #127 sau do). Thu tu
# nay khong anh huong gi ve mat du lieu: mot ban them cot cho dong chi ngan sach Marketing,
# mot ban tao bang canh bao gui - hai ban khong dung chung bang nao.
down_revision = "bd5a2f8c1e94"   # noi SAU ban bao dong khung hoang - giu MOT dau duy nhat
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
