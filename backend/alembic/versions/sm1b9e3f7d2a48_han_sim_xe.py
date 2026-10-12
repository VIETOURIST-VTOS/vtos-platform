"""SM-1: han sim va cong GPS cua sim

Revision ID: sm1b9e3f7d2a48
Revises: dl2a7c4e9b1f36
Create Date: 2026-10-12

MOT COT tren `vehicle_documents`: `cong_gps` — cong GPS ma chiec sim nay nuoi.

Khong them bang moi: sim la mot GIAY TO CO HAN cua xe, dung khuon voi dang kiem va bao hiem —
`kind="sim"`, `number` la so thue bao, `expires_on` la han goi cuoc. Dung bang rieng cho sim la
dung chuoi thu hai de tra loi cung mot cau hoi "giay nay het han ngay nao", va hai chuoi thi co
ngay hai cho noi khac nhau.

VI SAO `cong_gps` LA MOT COT CHU KHONG PHAI MOT CAU TRONG O GHI CHU: sim chet thi cong ay TAT, va
cau hoi ngay sau do luon la "cong nao, mat may xe". Chu tu do trong o ghi chu thi ba nguoi go ba
kieu va khong loc duoc — dung cho `km_nguon` da hong mot lan va phai sua.
"""
from alembic import op
import sqlalchemy as sa

revision = "sm1b9e3f7d2a48"
down_revision = "e3c4d5e6f7a8"
branch_labels = None
depends_on = None


def _co_cot(bang: str, cot: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return cot in {c["name"] for c in insp.get_columns(bang)}


def upgrade() -> None:
    if not _co_cot("vehicle_documents", "cong_gps"):
        op.add_column("vehicle_documents",
                      sa.Column("cong_gps", sa.String(20), nullable=False, server_default=""))


def downgrade() -> None:
    if _co_cot("vehicle_documents", "cong_gps"):
        op.drop_column("vehicle_documents", "cong_gps")
