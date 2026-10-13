"""QT-1: bảy ô của Mẫu 2, tuyến ký bốn bước, và trục "ai bỏ tiền ra tại chỗ".

Mẫu giấy Mẫu 2 (Chủ tịch chọn 13/10/2026) có những ô mà bảng chuyến chưa có chỗ giữ: tạm ứng,
hoàn trả, chi thêm, phụ thu, HDV, hành trình, báo cáo tình trạng xe — cộng tuyến ký Tài xế →
Điều hành → Kế toán → Tổng giám đốc.

`fleet_trip_costs.tra_bang` là trục KHÁC `ben_chiu`: `ben_chiu` hỏi "Vietourist hay chủ xe gánh",
`tra_bang` hỏi "lúc ấy ai móc túi ra". Xem chú thích tại `models/fleet.py::TRA_BANG`.

Revision ID: qt1f3a8c6e2b94
Revises: e4a1b2c3d4e5
"""
from alembic import op
import sqlalchemy as sa

revision = "qt1f3a8c6e2b94"
down_revision = "e4a1b2c3d4e5"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)

CHUYEN = [
    ("tam_ung", TIEN), ("hoan_tra", TIEN), ("chi_them", TIEN), ("phu_thu", TIEN),
    ("hdv", sa.String(80)), ("hanh_trinh", sa.String(200)), ("bc_tinh_trang_xe", sa.Text()),
    ("qt_trang_thai", sa.String(20)), ("qt_nhap_boi", sa.String(50)),
    ("qt_nhap_luc", sa.DateTime()),
    ("qt_dieu_hanh", sa.String(50)), ("qt_dieu_hanh_luc", sa.DateTime()),
    ("qt_ke_toan", sa.String(50)), ("qt_ke_toan_luc", sa.DateTime()),
    ("qt_tgd", sa.String(50)), ("qt_tgd_luc", sa.DateTime()),
    ("qt_tra_lai_ly_do", sa.String(300)),
]
# Cột chữ để "" chứ không NULL: cả kho đọc chúng bằng `or ""`, một cột NULL lẫn vào là một nhánh
# `if x is None` phải thêm ở mọi nơi đọc. Cột TIỀN thì ngược lại – NULL nghĩa là CHƯA KHAI, khác 0.
RONG = {sa.String: "", sa.Text: ""}


def _co_cot(bang: str, cot: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return cot in {c["name"] for c in insp.get_columns(bang)}


def upgrade() -> None:
    for ten, kieu in CHUYEN:
        if not _co_cot("fleet_trips", ten):
            mac_dinh = "nhap" if ten == "qt_trang_thai" else (
                "" if isinstance(kieu, (sa.String, sa.Text)) else None)
            op.add_column("fleet_trips",
                          sa.Column(ten, kieu, nullable=True,
                                    server_default=(mac_dinh if mac_dinh is not None else None)))
    if not _co_cot("fleet_trip_costs", "tra_bang"):
        op.add_column("fleet_trip_costs",
                      sa.Column("tra_bang", sa.String(24), nullable=True, server_default=""))


def downgrade() -> None:
    if _co_cot("fleet_trip_costs", "tra_bang"):
        op.drop_column("fleet_trip_costs", "tra_bang")
    for ten, _ in reversed(CHUYEN):
        if _co_cot("fleet_trips", ten):
            op.drop_column("fleet_trips", ten)
