"""HX-1: so may va ai xac nhan so ghe

Revision ID: hx1d4e7a2c9b58
Revises: ct1f6b2d8a4e93
Create Date: 2026-10-11

Ba cot tren bang `vehicles`:

  engine_no          so may. Sheet `THEO DOI CP` cua Vietrip co du cho 23 xe ma VTOS khong co cho giu.
  seats_xac_nhan_boi ai da xac nhan so ghe
  seats_xac_nhan_luc luc nao

VI SAO HAI COT XAC NHAN CHU KHONG SUA COT `seats`:

  `seats` mac dinh 45 va khong cho rong, nen mot chiec xe chua ai nhap ghe doc ra DUNG Y mot chiec
  45 cho that. Phuong an "canh bao khi dung bang 45" thi gan nhan oan cho ca xe 45 cho THAT, va nhan
  ay se khong bao gio tat. Ghi RIENG ai xac nhan thi con so co nguoi chiu trach nhiem, va mot chiec
  45 cho da xac nhan khong con bi hoi lai.

  Chu tich chon phuong an nay ngay 11/10/2026, khac phuong an Claude de xuat (cho cot rong).

KHONG them cot the dau vao day, du sheet nguon xep the theo tung DONG XE: Dot 2 doi xe da quyet
nguoc lai va ghi ly do tai `Employee.fuel_card_last4` - the gan voi TAI XE, vi doi tai xe ma the gan
vao xe thi moi giao dich the sau ngay ban giao gan nham chi phi sang nguoi khac. Chu tich xac nhan
giu nguyen quyet dinh ay ngay 11/10/2026.
"""
from alembic import op
import sqlalchemy as sa

revision = "hx1d4e7a2c9b58"
down_revision = "ct1f6b2d8a4e93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("engine_no", sa.String(length=40),
                                        nullable=False, server_default=""))
    op.add_column("vehicles", sa.Column("seats_xac_nhan_boi", sa.String(length=50),
                                        nullable=False, server_default=""))
    op.add_column("vehicles", sa.Column("seats_xac_nhan_luc", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicles", "seats_xac_nhan_luc")
    op.drop_column("vehicles", "seats_xac_nhan_boi")
    op.drop_column("vehicles", "engine_no")
