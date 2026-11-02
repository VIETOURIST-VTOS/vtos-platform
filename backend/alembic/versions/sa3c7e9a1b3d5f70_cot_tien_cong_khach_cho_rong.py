"""SUA-3 — 13 cột tiền của cổng khách (đặt bàn, khách sạn VTD / OTA, tour online, bảng kê NCC) cho phép RỖNG.

Đợt K2 (09/9/2026): cột tiền không được vừa mặc định 0 vừa NOT NULL — «chưa nhập» lặng lẽ thành «0 đồng».
Các đợt cổng khách 29/10–02/11 thêm 13 cột đúng kiểu ấy, nên test_ks_cot_tien_ky_thuat đỏ trên main. Bản này
CHỈ bỏ NOT NULL; máy vẫn ghi 0 khi tạo dòng (mặc định phía Python giữ nguyên), không sửa dữ liệu cũ.

Revision ID: sa3c7e9a1b3d5f70
Revises: dk2b5e8c1f3a7d49
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "sa3c7e9a1b3d5f70"
down_revision = "dk2b5e8c1f3a7d49"
branch_labels = None
depends_on = None

COT = (
    ("ban_ke_ncc", "tong"),
    ("don_dat_ban", "da_hoan_tien"), ("don_dat_ban", "giam_voucher"),
    ("don_khach_san_ota", "gia_gom_thue"), ("don_khach_san_ota", "hoan_gom_thue"),
    ("don_ks_vtd", "da_hoan_tien"), ("don_ks_vtd", "giam_voucher"), ("don_ks_vtd", "thue_phi"),
    ("don_ks_vtd", "tien_phong"), ("don_ks_vtd", "tong"),
    ("don_tour_online", "tong"), ("thanh_toan_tour_online", "so_tien"),
    ("khach_san_vtd", "thue_phi_pt"),
)


def upgrade() -> None:
    bang = {}
    for b, c in COT:
        bang.setdefault(b, []).append(c)
    for b, cs in bang.items():
        with op.batch_alter_table(b) as t:
            for c in cs:
                t.alter_column(c, existing_type=(sa.Float() if c == "thue_phi_pt" else sa.Numeric(14, 2) if b == "don_khach_san_ota" else sa.Numeric(18, 2)), nullable=True)


def downgrade() -> None:
    bang = {}
    for b, c in COT:
        bang.setdefault(b, []).append(c)
    for b, cs in bang.items():
        with op.batch_alter_table(b) as t:
            for c in cs:
                t.alter_column(c, existing_type=(sa.Float() if c == "thue_phi_pt" else sa.Numeric(14, 2) if b == "don_khach_san_ota" else sa.Numeric(18, 2)), nullable=False)
