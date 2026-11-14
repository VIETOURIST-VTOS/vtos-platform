# -*- coding: utf-8 -*-
"""R5-24 · Bàn KD nhớ 2 phút (Chủ tịch 14/11/2026 chọn «1»: lưu sẵn 1–2 phút, số có thể chậm tối đa 2 phút)."""
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[1]


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def test_phan_chung_tinh_mot_lan_trong_hai_phut(db, monkeypatch):
    from app.services import ban_kd_le as GD, ket_qua_that as KQT, ban_tour_le as BTL
    GD.KHO_CHUNG.xoa()
    n = {"kqt": 0, "sap": 0}
    g1, g2 = KQT.thang, BTL.dong_sap_di
    monkeypatch.setattr(KQT, "thang", lambda *a, **k: (n.__setitem__("kqt", n["kqt"] + 1), g1(*a, **k))[1])
    monkeypatch.setattr(BTL, "dong_sap_di", lambda *a, **k: (n.__setitem__("sap", n["sap"] + 1), g2(*a, **k))[1])
    d = date.today()
    for _ in range(3):
        GD.doi_chieu_chu_tich(db, d); GD.thuc_ban(db)
    assert n == {"kqt": 1, "sap": 1}
    assert GD.KHO_CHUNG.song_giay == 120


def test_khoa_cua_moi_cua_mang_vai_va_nguoi():
    s = (GOC / "app/api/v1/ban_kd_le.py").read_text(encoding="utf-8")
    assert 'KHO_BAN = NHO.Kho("ban_kd_le", 120)' in s
    assert 'NHO.khoa_vai(u.role, u.id, "vai_tong_quan")' in s           # bàn của ai là của người ấy
    assert 'NHO.khoa_vai(u.role, u.id, "nhip", pham_vi, ky)' in s
    assert s.count("refresh: bool = False") == 4                        # cửa làm mới (luật 2)


def test_khong_nho_loi(db):
    from app.api.v1 import ban_kd_le as A
    A.KHO_BAN.xoa()
    def hong():
        raise ValueError("thử")
    with pytest.raises(ValueError):
        A._nho(("x",), False, hong, db)
    assert len(A.KHO_BAN) == 0
    assert A._nho(("x",), False, lambda: {"a": 1}, db) == {"a": 1}
    assert A._nho(("x",), False, lambda: {"a": 2}, db) == {"a": 1, "nho_tam": True}
    assert A._nho(("x",), True, lambda: {"a": 3}, db) == {"a": 3}
