"""DL-1b: tai xe nhan lenh dieu xe

Revision ID: dl2a7c4e9b1f36
Revises: dl1e8b3f6a2d94
Create Date: 2026-10-12

Ba cot tren `dispatch_orders` — mat thu ba cua chuoi dieu xe:

    nhan_luc            luc tai xe bam nhan; RONG la chua nhan
    nhan_boi            ai bam (tai xe, hoac nguoi bam ho)
    tu_choi_nhan_ly_do  ly do khong nhan duoc; BAT BUOC khi tu choi

KHONG muon lai cot `status`. Cot ay dang mang nghia "GIAM DOC DOI XE da chot lenh"
(`da_xac_nhan` chi dat duoc boi nguoi duy nhat duoc lap lenh). Nhet them nghia "tai xe da nhan"
vao cung mot o la dung cai bay `two_signatures` da ghi trong so: mot o mang hai ly do thi ve sau
khong ai tach lai duoc ai da bam.

KHONG co cot "qua han". Qua han doi theo dong ho chu khong theo mot lan bam nao, nen mot cot luu
san se sai ngay phut sau khi ghi, tru phi co nguoi chay nen cap nhat — va cho ay la cho se quen
chay. Tinh tai cho bang `nhan_lenh.trang_thai_nhan()`, cung khuon voi `su_co_tour.qua_han()`.
"""
from alembic import op
import sqlalchemy as sa

revision = "dl2a7c4e9b1f36"
down_revision = "dl1e8b3f6a2d94"
branch_labels = None
depends_on = None


def _co_cot(bang: str, cot: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return cot in {c["name"] for c in insp.get_columns(bang)}


def upgrade() -> None:
    # Kiem truoc khi them: ban vá nay có thể chạy lại trên một kho đã có cột (sửa tay, hoặc một
    # lần deploy hỏng giữa chừng). Them de len thi alembic do va container khong len duoc.
    if not _co_cot("dispatch_orders", "nhan_luc"):
        op.add_column("dispatch_orders", sa.Column("nhan_luc", sa.DateTime(), nullable=True))
    if not _co_cot("dispatch_orders", "nhan_boi"):
        op.add_column("dispatch_orders",
                      sa.Column("nhan_boi", sa.String(50), nullable=False, server_default=""))
    if not _co_cot("dispatch_orders", "tu_choi_nhan_ly_do"):
        op.add_column("dispatch_orders",
                      sa.Column("tu_choi_nhan_ly_do", sa.String(300), nullable=False,
                                server_default=""))


def downgrade() -> None:
    for c in ("tu_choi_nhan_ly_do", "nhan_boi", "nhan_luc"):
        if _co_cot("dispatch_orders", c):
            op.drop_column("dispatch_orders", c)
