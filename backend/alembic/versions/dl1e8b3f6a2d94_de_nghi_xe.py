"""DL-1: bang de nghi xe va cot de_nghi_id tren lenh dieu xe

Revision ID: dl1e8b3f6a2d94
Revises: hx1d4e7a2c9b58
Create Date: 2026-10-11

Mat dau cua chuoi dieu xe Chu tich dac ta 11/10/2026:

    Dieu hanh DE NGHI xe  ->  Giam doc doi xe LAP LENH  ->  Tai xe NHAN

Truoc ban nay chuoi chi co mat giua: POST /dispatch cho ca Dieu hanh lan Giam doc doi xe tu chon xe
va phat lenh. Nguoi CAN xe va nguoi CO xe la hai vai, gop lai thi khong ai tra loi duoc cau "ai
quyet chiec xe nay di chuyen nay".

`dispatch_orders.de_nghi_id` de RONG DUOC - co y: bat buoc ngay thi muoi tep phep kiem cua cac lan
khac do, va Dieu hanh chua kip chuyen sang dung cua de nghi. Cho ho ay DEM DUOC bang
de_nghi_xe.lenh_khong_qua_de_nghi(), cung khuon voi misa.thieu_tai_khoan().
"""
from alembic import op
import sqlalchemy as sa

revision = "dl1e8b3f6a2d94"
down_revision = "hx1d4e7a2c9b58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_vehicle_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False, index=True),
        sa.Column("ngay_di", sa.Date(), nullable=False),
        sa.Column("ngay_ve", sa.Date(), nullable=False),
        sa.Column("so_khach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("km_du_kien", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_xe_can", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("yeu_cau", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=20), nullable=False,
                  server_default="cho_lap_lenh", index=True),
        sa.Column("ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("nguoi_de_nghi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("xu_ly_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("xu_ly_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_de_nghi_xe_tour_trang_thai", "fleet_vehicle_requests",
                    ["tour_id", "trang_thai"])
    op.add_column("dispatch_orders", sa.Column("de_nghi_id", sa.Integer(), nullable=True))
    op.create_index("ix_dispatch_orders_de_nghi_id", "dispatch_orders", ["de_nghi_id"])


def downgrade() -> None:
    op.drop_index("ix_dispatch_orders_de_nghi_id", table_name="dispatch_orders")
    op.drop_column("dispatch_orders", "de_nghi_id")
    op.drop_index("ix_de_nghi_xe_tour_trang_thai", table_name="fleet_vehicle_requests")
    op.drop_table("fleet_vehicle_requests")
