"""VB-1 — vé máy bay qua OTA: sản phẩm + loại link trên đối tác OTA; trường vé trên lượt chuyển; 4 OTA vé (TẮT).

Revision ID: vb1d2f4a6c8e13
Revises: cd1a7c3e5b9f12
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "vb1d2f4a6c8e13"
down_revision = "cd1a7c3e5b9f12"
branch_labels = None
depends_on = None

# Danh sách OTA Chủ tịch chọn 28/10/2026 — chỉ tên, KHÔNG link, KHÔNG bật. Chủ tịch nhập link và bật.
VE = (("traveloka_ve", "Traveloka", 11), ("trip_com_ve", "Trip.com", 12), ("agoda_ve", "Agoda", 13), ("expedia_ve", "Expedia", 14))


def upgrade() -> None:
    op.add_column("doi_tac_ota", sa.Column("san_pham", sa.String(length=12), nullable=False, server_default="khach_san"))
    op.add_column("doi_tac_ota", sa.Column("loai_link", sa.String(length=10), nullable=False, server_default="hoa_hong"))
    op.create_index("ix_doi_tac_ota_san_pham", "doi_tac_ota", ["san_pham"])
    for c in (sa.Column("san_pham", sa.String(length=12), nullable=False, server_default="khach_san"),
              sa.Column("diem_di", sa.String(length=120), nullable=False, server_default=""),
              sa.Column("em_be", sa.Integer(), nullable=False, server_default="0"),
              sa.Column("hang_ve", sa.String(length=20), nullable=False, server_default=""),
              sa.Column("loai_link", sa.String(length=10), nullable=False, server_default="hoa_hong")):
        op.add_column("luot_chuyen_ota", c)
    ota = sa.table("doi_tac_ota", sa.column("ma", sa.String), sa.column("ten", sa.String), sa.column("san_pham", sa.String),
                   sa.column("loai_link", sa.String), sa.column("thu_tu", sa.Integer), sa.column("trang_thai", sa.String),
                   sa.column("link", sa.String), sa.column("ten_mien", sa.String), sa.column("duong_dan", sa.String),
                   sa.column("da_kiem_link", sa.Boolean), sa.column("duoc_dung_web", sa.Boolean), sa.column("bat", sa.Boolean),
                   sa.column("phien_ban", sa.Integer), sa.column("bang_chung", sa.String), sa.column("ghi_chu", sa.String),
                   sa.column("subid_cho_phep", sa.Boolean), sa.column("subid_tham_so", sa.String), sa.column("sua_boi", sa.String))
    op.bulk_insert(ota, [{"ma": m, "ten": t, "san_pham": "ve_may_bay", "loai_link": "cong_khai", "thu_tu": i,
                          "trang_thai": "chua_dang_ky", "link": "", "ten_mien": "", "duong_dan": "", "da_kiem_link": False,
                          "duoc_dung_web": False, "bat": False, "phien_ban": 1, "bang_chung": "", "ghi_chu": "",
                          "subid_cho_phep": False, "subid_tham_so": "", "sua_boi": ""} for m, t, i in VE])


def downgrade() -> None:
    op.execute("DELETE FROM doi_tac_ota WHERE san_pham = 've_may_bay'")
    for c in ("loai_link", "hang_ve", "em_be", "diem_di", "san_pham"):
        op.drop_column("luot_chuyen_ota", c)
    op.drop_index("ix_doi_tac_ota_san_pham", table_name="doi_tac_ota")
    op.drop_column("doi_tac_ota", "loai_link")
    op.drop_column("doi_tac_ota", "san_pham")
