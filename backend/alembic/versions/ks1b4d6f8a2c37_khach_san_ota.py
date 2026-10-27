"""KS-1 — khách sạn qua OTA: pháp nhân hợp đồng, đối tác OTA, sổ lượt chuyển.

Gieo sẵn: pháp nhân THE INFINIS PATHWAY INC. (Chủ tịch yêu cầu 28/10/2026) và năm OTA chỉ có TÊN — mọi
OTA «chưa đăng ký», chưa có link, TẮT. Link, trạng thái hợp tác và việc bật do Chủ tịch nhập trên VTOS.

Revision ID: ks1b4d6f8a2c37
Revises: dt1a3c5e7b9d24
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "ks1b4d6f8a2c37"
down_revision = "dt1a3c5e7b9d24"
branch_labels = None
depends_on = None

OTA = (("expedia", "Expedia", 1), ("booking_com", "Booking.com", 2), ("agoda", "Agoda", 3),
       ("traveloka", "Traveloka", 4), ("trip_com", "Trip.com", 5))


def upgrade() -> None:
    pn = op.create_table(
        "phap_nhan_hop_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=30), nullable=False, unique=True),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("quoc_gia", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
    )
    ota = op.create_table(
        "doi_tac_ota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=30), nullable=False, unique=True),
        sa.Column("ten", sa.String(length=80), nullable=False),
        sa.Column("phap_nhan_id", sa.Integer(), sa.ForeignKey("phap_nhan_hop_dong.id"), nullable=True),
        sa.Column("trang_thai", sa.String(length=16), nullable=False, server_default="chua_dang_ky"),
        sa.Column("link", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("ten_mien", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("duong_dan", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("da_kiem_link", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duoc_dung_web", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bang_chung", sa.Text(), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("thu_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sua_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "luot_chuyen_ota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False, index=True),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("doi_tac_ota_id", sa.Integer(), sa.ForeignKey("doi_tac_ota.id"), nullable=False, index=True),
        sa.Column("phien_ban_link", sa.Integer(), nullable=False),
        sa.Column("cong", sa.String(length=12), nullable=False),
        sa.Column("doi_tac_ban_hang_id", sa.Integer(), sa.ForeignKey("doi_tac_ban_hang.id"), nullable=True),
        sa.Column("diem_den", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("nhan_phong", sa.Date(), nullable=True),
        sa.Column("tra_phong", sa.Date(), nullable=True),
        sa.Column("so_phong", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nguoi_lon", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("tre_em", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, index=True),
        sa.UniqueConstraint("tai_khoan_id", "request_id", name="uq_luot_chuyen_ota_req"),
    )
    op.bulk_insert(pn, [{"id": 1, "ma": "INFINIS_CA", "ten": "THE INFINIS PATHWAY INC.", "quoc_gia": "Canada",
                         "ghi_chu": "Pháp nhân ký Affiliate OTA, hưởng hoa hồng (đặc tả Khách sạn v1.1, 28/10/2026)"}])
    op.bulk_insert(ota, [{"ma": m, "ten": t, "phap_nhan_id": 1, "thu_tu": i} for m, t, i in OTA])


def downgrade() -> None:
    op.drop_table("luot_chuyen_ota")
    op.drop_table("doi_tac_ota")
    op.drop_table("phap_nhan_hop_dong")
