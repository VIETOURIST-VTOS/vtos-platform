"""DL-2 - so khach song den ngay di: o lan sua cuoi + so ghi tung lan doi

Chu tich 13/10/2026: "so khach se do nhan vien dieu hanh nhap tay va dieu chinh den ngay di".
Cua De nghi xe truoc ban nay chi co TAO / TU CHOI / HUY - khong duong nao sua. Nen con so ma Giam
doc doi xe dung de quyet dieu may chiec la con so cua NGAY LAP DE NGHI.

Giu lich su chu khong ghi de: khi mot doan thieu cho o bai xe luc 5 gio sang, cau hoi dau tien la
"luc lap lenh thi de nghi ghi bao nhieu khach". Ghi de thi cau ay khong co cau tra loi.

Revision ID: dl2k8m4p6r2w51
Revises: hq2d4b7e1a9c53
"""
import sqlalchemy as sa
from alembic import op

revision = "dl2k8m4p6r2w51"
down_revision = "hq2d4b7e1a9c53"
branch_labels = None
depends_on = None


def _co_cot(bang: str, cot: str) -> bool:
    ins = sa.inspect(op.get_bind())
    if bang not in ins.get_table_names():
        return False
    return cot in {c["name"] for c in ins.get_columns(bang)}


def _co_bang(ten: str) -> bool:
    return ten in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _co_cot("fleet_vehicle_requests", "so_khach_sua_luc"):
        op.add_column("fleet_vehicle_requests",
                      sa.Column("so_khach_sua_luc", sa.DateTime, nullable=True))
    if not _co_cot("fleet_vehicle_requests", "so_khach_sua_boi"):
        op.add_column("fleet_vehicle_requests",
                      sa.Column("so_khach_sua_boi", sa.String(50), nullable=False,
                                server_default=""))
    if not _co_bang("fleet_vehicle_request_pax_log"):
        op.create_table(
            "fleet_vehicle_request_pax_log",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("de_nghi_id", sa.Integer,
                      sa.ForeignKey("fleet_vehicle_requests.id"), nullable=False),
            sa.Column("so_khach_cu", sa.Integer, nullable=False),
            sa.Column("so_khach_moi", sa.Integer, nullable=False),
            sa.Column("so_xe_can_cu", sa.Integer, nullable=False),
            sa.Column("so_xe_can_moi", sa.Integer, nullable=False),
            sa.Column("ly_do", sa.String(300), nullable=False, server_default=""),
            sa.Column("boi", sa.String(50), nullable=False, server_default=""),
            sa.Column("luc", sa.DateTime, nullable=True),
        )
        op.create_index("ix_pax_log_de_nghi", "fleet_vehicle_request_pax_log", ["de_nghi_id"])


def downgrade() -> None:
    if _co_bang("fleet_vehicle_request_pax_log"):
        op.drop_index("ix_pax_log_de_nghi", table_name="fleet_vehicle_request_pax_log")
        op.drop_table("fleet_vehicle_request_pax_log")
    for c in ("so_khach_sua_boi", "so_khach_sua_luc"):
        if _co_cot("fleet_vehicle_requests", c):
            op.drop_column("fleet_vehicle_requests", c)
