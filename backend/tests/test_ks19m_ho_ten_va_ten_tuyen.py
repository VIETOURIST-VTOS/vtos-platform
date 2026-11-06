# -*- coding: utf-8 -*-
"""KS-19m · sau vòng thử tour đoàn 06/11/2026 (Chủ tịch duyệt bản xem thử):

  1. Hồ sơ khách chưa có tên → gửi thiết kế phải ghi họ tên / tên công ty; tên lưu vào hồ sơ và lên báo giá.
  2. Hồ sơ đã có tên → không bắt buộc, tên hồ sơ giữ nguyên.
  3. Dòng xe quy theo ngày không ghi lặp số ngày khi tên tuyến đã có («Đà Lạt 4 ngày 4 ngày»).
  4. Giao diện có ô «Họ tên / Tên công ty» và gửi kèm ho_ten.
"""
from pathlib import Path

import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_tk1_tu_thiet_ke_tour_doan import NOW, _bang_gia, _thiet_ke, _tk, nen  # noqa: F401


def _gui(db, nen, **d):
    from app.services import thiet_ke_doan as S
    return S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen), "dien_thoai": "0901000001", "dong_y": True, **d}, NOW)


def test_ks19m_1_ho_so_trong_ten_thi_bat_buoc(db, nen):
    from app.models.ban_hang import BaoGia
    from app.models.thiet_ke_doan import ThietKeDoan
    from app.services import bao_gia_doan as B
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    k = _tk(db)
    k.ho_ten = ""
    db.commit()
    with pytest.raises(S.LoiThietKe, match="họ tên"):
        _gui(db, nen)
    r = _gui(db, nen, ho_ten="  Công ty TNHH ABC  ")
    assert _tk(db).ho_ten == "Công ty TNHH ABC"
    tk = db.query(ThietKeDoan).filter(ThietKeDoan.ma == r["ma"]).one()
    bg = B.lap(db, _u(db, "dh"), tk.id, NOW)
    assert db.get(BaoGia, bg["id"]).khach_ten == "Công ty TNHH ABC"


def test_ks19m_2_ho_so_co_ten_thi_giu_nguyen(db, nen):
    _bang_gia(db)
    k = _tk(db)
    k.ho_ten = "Nguyễn Văn Hồ Sơ"
    db.commit()
    _gui(db, nen)
    _gui(db, nen, ho_ten="Tên khác")
    assert _tk(db).ho_ten == "Nguyễn Văn Hồ Sơ"


def test_ks19m_3_ten_tuyen_khong_lap_so_ngay():
    goc = Path(__file__).resolve().parents[1] / "app" / "services" / "thiet_ke_doan.py"
    s = goc.read_text(encoding="utf-8")
    assert 'f"{int(r.days)} ngày" in (r.route or "")' in s
    assert 'theo tuyến {r.route} {int(r.days)} ngày, quy theo ngày' not in s


def test_ks19m_4_giao_dien():
    c = (Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "TuThietKeTour.tsx").read_text(encoding="utf-8")
    assert "Họ tên / Tên công ty" in c and "ho_ten: gui.ho_ten" in c
