"""KS-16c — Bỏ khâu duyệt ảnh khách sạn VTD và nhà hàng (Chủ tịch chốt 31/10/2026).

Ảnh tải lên là hiện ngay. Ảnh đang Nháp / Chờ duyệt / Trả lại chuyển sang Đã duyệt (ghi `duyet_boi = tu_dong`);
ảnh đang Ẩn giữ nguyên. Không đổi cấu trúc bảng.

Revision ID: ks16cf2a9c4e6b815
Revises: ks16be8f1a3c5d749
Create Date: 2026-10-31
"""
from alembic import op

revision = "ks16cf2a9c4e6b815"
down_revision = "ks16be8f1a3c5d749"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for bang in ("anh_khach_san_vtd", "anh_nha_hang"):
        op.execute(f"UPDATE {bang} SET trang_thai = 'da_duyet', duyet_boi = 'tu_dong', duyet_luc = CURRENT_TIMESTAMP "
                   f"WHERE trang_thai IN ('nhap', 'cho_duyet', 'tra_lai')")


def downgrade() -> None:
    # Trả ảnh do máy tự duyệt (dấu `tu_dong`) về Nháp; ảnh TP Điều hành đã duyệt tay giữ nguyên.
    for bang in ("anh_khach_san_vtd", "anh_nha_hang"):
        op.execute(f"UPDATE {bang} SET trang_thai = 'nhap', duyet_boi = '', duyet_luc = NULL "
                   f"WHERE duyet_boi = 'tu_dong' AND trang_thai = 'da_duyet'")
