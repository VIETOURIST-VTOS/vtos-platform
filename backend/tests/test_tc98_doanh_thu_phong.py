"""TC-98 · Doanh thu PKD Lẻ và PKD Đoàn trên màn hình Chủ tịch — anh Tuấn 29/9/2026.

    "nối doanh thu của PKD lẻ và PKD đoàn vào màn hình chủ tịch"

Điều canh: con số theo phòng chia ĐÚNG tập chuyến đã ra `doanh_thu` của `ket_qua_that.thang`,
nên lẻ + đoàn + khác = doanh_thu. Và màn hình chủ tịch phải đọc nó.
"""
import datetime as dt
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
from app.services import ket_qua_that as KQ
from app.services import dashboard as DB_

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _so():
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    db.add(me); db.commit()
    u = User(username="ct", full_name="Chủ tịch", role="chutich", password_hash="x")
    db.add(u); db.commit()

    def them(code, loai, ngay, rev, cost):
        db.add(Tour(code=code, name=code, tour_type=loai, start_date=ngay,
                    end_date=ngay + dt.timedelta(days=2), operator_id=u.id, status="ket_thuc",
                    actual_revenue=rev, actual_cost=cost, company_id=me.id))

    them("LE1", "le_noi_dia", dt.date(2026, 9, 3), 100.0, 60.0)
    them("LE2", "le_nuoc_ngoai", dt.date(2026, 9, 5), 50.0, 30.0)
    them("MICE1", "le_noi_dia", dt.date(2026, 9, 6), 300.0, 200.0)     # mã MICE → Đoàn
    them("D1", "doan_noi_dia", dt.date(2026, 8, 6), 400.0, 300.0)
    them("NP", "package", dt.date(2026, 9, 7), 20.0, 10.0)             # không thuộc phòng nào
    them("THIEU", "le_noi_dia", dt.date(2026, 9, 8), 999.0, None)      # thiếu giá vốn → không cộng
    db.commit()
    return db


def test_theo_mang_cong_lai_bang_doanh_thu():
    db = _so()
    r = KQ.thang(db, "2026-09")
    tm = r["theo_mang"]
    assert tm["le"] == {"doanh_thu": 150.0, "chuyen": 2}
    assert tm["doan"] == {"doanh_thu": 300.0, "chuyen": 1}
    assert tm["khac"] == {"doanh_thu": 20.0, "chuyen": 1}
    assert sum(v["doanh_thu"] for v in tm.values()) == r["doanh_thu"]


def test_doanh_thu_phong_thang_va_luy_ke_nam():
    db = _so()
    d = DB_.doanh_thu_phong(db, dt.date(2026, 9, 29))
    assert d["ky"] == "2026-09" and d["nam"] == 2026
    assert d["le"] == {"thang": 150.0, "chuyen_thang": 2, "nam": 150.0, "chuyen_nam": 2}
    assert d["doan"] == {"thang": 300.0, "chuyen_thang": 1, "nam": 700.0, "chuyen_nam": 2}


def test_man_hinh_chu_tich_doc_doanh_thu_phong():
    trang = open(os.path.join(ROOT, "web", "app", "page.tsx"), encoding="utf-8").read()
    assert trang.count("dt={sec.doanh_thu_phong}") == 2
