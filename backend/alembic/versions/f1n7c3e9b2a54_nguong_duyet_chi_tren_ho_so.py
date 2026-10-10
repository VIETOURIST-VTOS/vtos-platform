# -*- coding: utf-8 -*-
"""Dot F1: nguong duyet chi da ap cho tung ho so.

Them `nguong_duyet_ap_dung` vao `payment_requests`.

Vi sao: xem chu thich dai trong `app/models/ops.py` tai cot nay. Ngan gon - moc tien phan cap duyet
nam o tham so va tham so DOI DUOC, nen cap duyet cua mot ho so phai duoc ghi xuong chinh ho so ay
luc trinh; doc tham so luc duyet thi mot ho so tu tut cap khi ai do nang moc.

NULLABLE, KHONG MAC DINH SO. Moi dong da co trong bang deu lap TRUOC khi co luat nay - khong cach
nao biet chung duoc trinh theo moc nao, nen khong duoc dien mot con so vao do. RONG doc ra la CHUA
CHOT, va `services/ops.py` CHAN buoc duyet khi gap no chu khong coi la "khong co moc".

Revision ID: f1n7c3e9b2a54
Revises: df3a8c5e1b07
Create Date: 2026-10-10
"""
import sqlalchemy as sa
from alembic import op

revision = "f1n7c3e9b2a54"
down_revision = "df3a8c5e1b07"
branch_labels = None
depends_on = None

# Cung kieu voi mo hinh (app/models/kieu_tien.py), khai lai dung con so de ban nang cap va mo hinh
# khong bao gio lech nhau.
TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.add_column(sa.Column("nguong_duyet_ap_dung", TIEN, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payment_requests") as b:
        b.drop_column("nguong_duyet_ap_dung")
