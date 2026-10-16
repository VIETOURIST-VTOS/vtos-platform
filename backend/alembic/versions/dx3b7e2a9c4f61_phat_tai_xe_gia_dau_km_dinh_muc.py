"""DX-3 - phat tai xe, gia dau theo ngay, va km dinh muc cua danh muc tour

Ba viec cuoi cua danh sach bay viec lap trinh doi xe (chot 11/10/2026), Chu tich duyet 16/10/2026.

PHAT TAI XE NAM O BANG RIENG, KHONG PHAI MOT DONG CHI PHI KY. Chu tich chot 16/10/2026: khoan phat
di vao LUONG cua nguoi lai, khong vao gia von cua chiec xe. Nhet no vao `fleet_period_costs` thi
chiec xe ganh loi cua nguoi, va bao cao lai lo tung xe sai - dung hinh da ghi trong chinh tep
`models/fleet.py` khi tach `fleet_faults` khoi `fleet_maintenance`.

GIA DAU THEO NGAY de QUY TIEN RA SO LIT. So ke the dau cho tien, khong phai lit; khong co gia ngay
thi khong tinh duoc tieu hao, va o "Tieu hao" tren man hinh doi xe doc ra mot con so khong ai kiem
duoc. Khoa theo (ngay, loai) chu khong chi theo ngay: dau DO va xang khac gia.

KM DINH MUC NAM TREN DANH MUC TOUR (`products`), khong nam tren tung chuyen. Mot tuyen co quang
duong co dinh; khai theo tung chuyen la bat nguoi dieu hanh go lai cung mot con so moi lan mo tour.

Revision ID: dx3b7e2a9c4f61
Revises: dl3f7a2c9e4b16
"""
import sqlalchemy as sa
from alembic import op

revision = "dx3b7e2a9c4f61"
down_revision = "dl3f7a2c9e4b16"
branch_labels = None
depends_on = None


def _co_bang(ten: str) -> bool:
    return ten in sa.inspect(op.get_bind()).get_table_names()


def _co_cot(bang: str, cot: str) -> bool:
    return cot in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(bang)}


def upgrade() -> None:
    if not _co_bang("fleet_driver_penalties"):
        op.create_table(
            "fleet_driver_penalties",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("driver_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False),
            sa.Column("ky", sa.String(7), nullable=False),          # YYYY-MM, ky luong se tru
            sa.Column("ngay", sa.Date, nullable=False),
            sa.Column("so_tien", sa.Numeric(18, 2), nullable=False),
            sa.Column("ly_do", sa.String(300), nullable=False),
            sa.Column("trip_id", sa.Integer, sa.ForeignKey("fleet_trips.id"), nullable=True),
            sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=True),
            sa.Column("hcns_doi_chieu_luc", sa.DateTime, nullable=True),
            sa.Column("hcns_doi_chieu_boi", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )
        op.create_index("ix_fleet_driver_penalties_ky", "fleet_driver_penalties", ["ky"])
        op.create_index("ix_fleet_driver_penalties_driver", "fleet_driver_penalties", ["driver_id"])

    if not _co_bang("fleet_fuel_prices"):
        op.create_table(
            "fleet_fuel_prices",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("ngay", sa.Date, nullable=False),
            sa.Column("loai", sa.String(20), nullable=False, server_default="do"),
            sa.Column("gia_lit", sa.Numeric(18, 2), nullable=False),
            sa.Column("nguon", sa.String(120), nullable=False, server_default=""),
            sa.Column("boi", sa.String(50), nullable=False, server_default=""),
            sa.Column("luc", sa.DateTime, nullable=True),
        )
        # MOT GIA cho mot (ngay, loai). Hai dong cung ngay cung loai thi phep quy lit ra hai ket
        # qua khac nhau tuy dong nao doc truoc - va khong ai biet con so tieu hao dua tren gia nao.
        op.create_index("uq_fleet_fuel_prices_ngay_loai", "fleet_fuel_prices",
                        ["ngay", "loai"], unique=True)

    if not _co_cot("products", "km_dinh_muc"):
        op.add_column("products", sa.Column("km_dinh_muc", sa.Integer, nullable=True))


def downgrade() -> None:
    if _co_cot("products", "km_dinh_muc"):
        op.drop_column("products", "km_dinh_muc")
    if _co_bang("fleet_fuel_prices"):
        op.drop_index("uq_fleet_fuel_prices_ngay_loai", table_name="fleet_fuel_prices")
        op.drop_table("fleet_fuel_prices")
    if _co_bang("fleet_driver_penalties"):
        op.drop_index("ix_fleet_driver_penalties_driver", table_name="fleet_driver_penalties")
        op.drop_index("ix_fleet_driver_penalties_ky", table_name="fleet_driver_penalties")
        op.drop_table("fleet_driver_penalties")
