# -*- coding: utf-8 -*-
"""R5-21 · Bàn Trưởng phòng KD chờ 43 giây trên crm (Chủ tịch 14/11/2026 «load rất chậm»).

Nguyên nhân: ô đối chiếu số màn Chủ tịch gọi cả `dashboard.doanh_thu_phong` (tính thêm luỹ kế năm =
`ket_qua_that.thang` cho từng tháng từ đầu năm) và bàn TP gọi hai lần. Nay một lượt tính tháng này cho
mỗi bàn, số không đổi."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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


def _dem(monkeypatch):
    from app.services import ket_qua_that as KQT
    n = {"c": 0}
    goc = KQT.thang

    def boc(*a, **k):
        n["c"] += 1
        return goc(*a, **k)
    monkeypatch.setattr(KQT, "thang", boc)
    return n


def test_doi_chieu_bang_o_thang_cua_man_chu_tich(db):
    from app.services import ban_kd_le as GD, dashboard as DB
    d = date(2026, 11, 14)
    a, b = GD.doi_chieu_chu_tich(db, d), DB.doanh_thu_phong(db, d)["le"]
    assert (a["thang"], a["chuyen_thang"]) == (b["thang"], b["chuyen_thang"])


@pytest.mark.parametrize("vai", ["tp_kd", "tn_kd"])
def test_ban_tp_tn_tinh_thang_mot_lan(db, monkeypatch, vai):
    from app.models.core import User
    from app.services import ban_kd_vai as KV
    u = User(username="x." + vai, full_name="X", role=vai, password_hash="x", active=True, sales_group="KD1")
    db.add(u); db.commit()
    n = _dem(monkeypatch)
    KV.tong_quan(db, u, date(2026, 11, 14))
    assert n["c"] <= 1, n


def test_ban_gd_tinh_thang_mot_lan(db, monkeypatch):
    from app.services import ban_kd_le as GD
    n = _dem(monkeypatch)
    GD.tong_quan(db, date(2026, 11, 14))
    assert n["c"] <= 1, n
