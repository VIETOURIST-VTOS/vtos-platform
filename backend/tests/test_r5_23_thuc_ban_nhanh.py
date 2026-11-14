# -*- coding: utf-8 -*-
"""R5-23 · Khối «Chuyến cần thúc bán» trên bàn TP / Trưởng nhóm / Chuyên viên không dựng cả bàn bán tour lẻ
(Chủ tịch 14/11/2026 «load rất chậm»; đo trên crm `ban_lam_viec` ≈ 3,8 giây). Cùng kết quả, ít việc hơn."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

HOM_NAY = date.today()


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


def _tour(db, code, cach, trang_thai="da_duyet", loai="le_noi_dia"):
    from app.models.core import Tour, User
    op = db.query(User).filter_by(username="dh.thu").first()
    if op is None:
        op = User(username="dh.thu", full_name="DH", role="nv_dh", password_hash="x", active=True)
        db.add(op); db.flush()
    t = Tour(operator_id=op.id, code=code, name="Thử " + code, tour_type=loai, start_date=HOM_NAY + timedelta(days=cach),
             end_date=HOM_NAY + timedelta(days=cach + 2), price_per_pax=2_000_000, fixed_cost=10_000_000,
             var_cost_per_pax=1_000_000, planned_pax=30, status=trang_thai)
    db.add(t); db.flush()
    return t


def test_duong_nhanh_cung_ket_qua_duong_day_du(db):
    from app.services import ban_kd_le as GD, ban_tour_le as BTL
    _tour(db, "PT-LE-01", 2); _tour(db, "PT-LE-02", 6); _tour(db, "PT-LE-03", 7)
    _tour(db, "PT-LE-04", 8); _tour(db, "PT-LE-05", 30); _tour(db, "PT-LE-06", 3, "nhap")
    db.commit()
    nhanh = GD.thuc_ban(db)
    assert nhanh == GD.thuc_ban(db, BTL.ban_lam_viec(db)["rows"])
    assert {x["code"] for x in nhanh} == {"PT-LE-01", "PT-LE-02", "PT-LE-03"}


def test_ban_vai_dung_duong_nhanh():
    s = (Path(__file__).resolve().parents[1] / "app/services/ban_kd_le.py").read_text(encoding="utf-8")
    assert "rows = BTL.dong_sap_di(db, 7)" in s
