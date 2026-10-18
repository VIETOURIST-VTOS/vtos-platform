# -*- coding: utf-8 -*-
"""TL-1 · Chuyến bị Kế toán trả lại quyết toán phải NHẬN RA ĐƯỢC (Chủ tịch duyệt 19/10/2026).

Nút trả lại đưa chuyến về `ket_thuc` — giống hệt chuyến chưa ai đóng số. Máy nhận ra bằng lịch
sử chuyến: sự kiện gần nhất trong cặp (đóng số, Kế toán trả lại) là «trả lại».
"""
import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, TourEvent, User
from app.services import ban_lam_viec as BLV
from app.services import tra_lai_quyet_toan as TLQ

HOM_NAY = dt.date.today()
T0 = dt.datetime(2026, 10, 1, 9, 0)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    s.add(User(username="dh", full_name="dh", role="nv_dh", password_hash="x")); s.commit()
    return s


def _tour(db, ma, trang_thai, buoc):
    u = db.execute(select(User)).scalars().first()
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=HOM_NAY, end_date=HOM_NAY,
             operator_id=u.id, status=trang_thai, planned_pax=1)
    db.add(t); db.flush()
    for i, (b, ghi) in enumerate(buoc):
        db.add(TourEvent(tour_id=t.id, step=b, title=b, note=ghi, actor="kt1",
                         at=T0 + dt.timedelta(hours=i)))
    db.commit()
    return t


def test_tl1_1_nhan_ra_dung_chuyen_bi_tra_lai():
    db = _db()
    a = _tour(db, "A", "ket_thuc", [("dong_so", ""), ("kt_tra_lai", "thiếu hoá đơn")])
    b = _tour(db, "B", "ket_thuc", [("dong_so", ""), ("kt_tra_lai", "x"), ("dong_so", "")])
    c = _tour(db, "C", "da_dong_so", [("dong_so", ""), ("kt_tra_lai", "x"), ("dong_so", "")])
    d = _tour(db, "D", "ket_thuc", [])
    e = _tour(db, "E", "ket_thuc", [("kt_tra_lai", "lần 1"), ("dong_so", ""), ("kt_tra_lai", "lần 2")])
    kq = TLQ.dang_bi_tra_lai(db)
    assert set(kq) == {a.id, e.id}, "chỉ chuyến đang ket_thuc mà bước gần nhất là trả lại"
    assert kq[a.id].note == "thiếu hoá đơn" and kq[e.id].note == "lần 2"
    assert b.id not in kq and c.id not in kq and d.id not in kq


def test_tl1_2_mo_ta_cho_trang_chuyen():
    db = _db()
    a = _tour(db, "A", "ket_thuc", [("dong_so", ""), ("kt_tra_lai", "thiếu hoá đơn")])
    m = TLQ.mo_ta(TLQ.dang_bi_tra_lai(db, [a.id]).get(a.id), 2)
    assert m["ly_do"] == "thiếu hoá đơn" and m["ai"] == "kt1" and m["phien_ban"] == 2
    assert TLQ.mo_ta(None) is None


def test_tl1_3_dong_tren_ban_lam_viec_la_mot_phan_cua_o(monkeypatch):
    from app.services import rules as R
    monkeypatch.setattr(R, "settlement_deadline", lambda db, t: dt.date(2099, 1, 1))
    db = _db()
    _tour(db, "A", "ket_thuc", [("dong_so", ""), ("kt_tra_lai", "x")])
    _tour(db, "B", "ket_thuc", [])
    _tour(db, "C", "da_dong_so", [("dong_so", "")])
    o = BLV._quyet_toan_cho(db)
    assert o["so_luong"] == 2, "con số ô không đổi: dòng trả lại là MỘT PHẦN của nó"
    dong = [x for x in o["dong"] if "trả lại" in x["chinh"].lower()]
    assert len(dong) == 1 and dong[0]["phai"] == "1"


def test_tl1_4_khong_co_chuyen_bi_tra_lai_thi_khong_ve_dong(monkeypatch):
    from app.services import rules as R
    monkeypatch.setattr(R, "settlement_deadline", lambda db, t: dt.date(2099, 1, 1))
    db = _db()
    _tour(db, "B", "ket_thuc", [("dong_so", "")])
    o = BLV._quyet_toan_cho(db)
    assert not [x for x in o["dong"] if "trả lại" in x["chinh"].lower()]
