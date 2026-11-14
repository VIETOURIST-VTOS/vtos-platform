# -*- coding: utf-8 -*-
"""R5-26 · Lập lệnh điều xe (Chủ tịch duyệt bản xem trước 14/11/2026 21:01)."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"


def test_xo_ra_moi_xe_du_dieu_kien():
    s = (WEB / "app/lenh-dieu-xe/lap-lenh/page.tsx").read_text(encoding="utf-8")
    assert "(xoHet ? (gy.tat_ca || gy.phuong_an) : gy.phuong_an).map(" in s
    assert "Xem tất cả" in s and "Thu gọn về nhóm đề xuất" in s
    assert "onClick={() => chot(p, \"\")}" in s       # cùng nút chốt; máy chủ hỏi lý do khi xe điểm thấp hơn


def test_nut_mo_lich_va_lap_lenh_navy_sang():
    s = (WEB / "components/doixe/TrangGon.tsx").read_text(encoding="utf-8")
    assert "Mở lịch và lập lệnh →" in s and 'background: "var(--vtos-sky)"' in s
    assert "Mở lịch & lệnh đầy đủ" not in s


def test_may_chu_tra_du_danh_sach():
    import inspect
    from app.services import fleet_ai as AI
    assert '"tat_ca": pa' in inspect.getsource(AI.goi_y_dieu_xe)
