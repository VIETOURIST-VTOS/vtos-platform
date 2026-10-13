"""HQ-2c - dinh muc tieu hao dau theo so cho

Chu tich quyet 13/10/2026: nguong do DOI XE khai, khong de may tu doan tu trung binh cua chinh
chiec xe ay - mot chiec hao nhieu suot sau thang thi may coi do la binh thuong, va chiec hao nhat
doi tro thanh chiec khong bao gio bi canh bao.

Khoa theo `seats` chu khong theo tung xe: so cho la thuoc tinh da co trong danh muc va chinh no
quyet dinh muc hao. Khai theo tung xe thi moi lan mua xe moi lai them mot o trong nua.

Revision ID: hq2d4b7e1a9c53
Revises: gop1a5c9e3b7d24
"""
import sqlalchemy as sa
from alembic import op

revision = "hq2d4b7e1a9c53"
down_revision = "gop1a5c9e3b7d24"
branch_labels = None
depends_on = None


def _co_bang(ten: str) -> bool:
    return ten in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    # Guard: ban va co the chay lai tren mot co so du lieu da co bang - khong duoc no.
    if _co_bang("fleet_fuel_norms"):
        return
    op.create_table(
        "fleet_fuel_norms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("seats", sa.Integer, nullable=False, unique=True),
        sa.Column("l_100km", sa.Float, nullable=False),
        sa.Column("ghi_chu", sa.String(200), nullable=False, server_default=""),
        sa.Column("boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime, nullable=True),
    )
    op.create_index("ix_fleet_fuel_norms_seats", "fleet_fuel_norms", ["seats"])


def downgrade() -> None:
    if _co_bang("fleet_fuel_norms"):
        op.drop_index("ix_fleet_fuel_norms_seats", table_name="fleet_fuel_norms")
        op.drop_table("fleet_fuel_norms")
