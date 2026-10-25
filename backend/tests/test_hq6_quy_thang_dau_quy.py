"""HQ-6 · Tháng đầu quý thì nút «Quý» mở QUÝ LIỀN TRƯỚC đã đủ ba tháng (Chủ tịch chốt 24/10/2026).

Đo trên hệ thật 24/10/2026: quý 4 mới có tháng 10 nên Tháng và Quý in đúng một bộ số (527,5 tr —
240,6 tr — 133 ngày). Phép tính đúng, nhưng người đọc kết luận màn hình hỏng.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.services import hieu_qua_xe as HQ  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    v = Vehicle(plate="50F-HQ6", seats=45, ngay_vao_doi=date(2025, 1, 1))
    s.add(v); s.flush()
    for ma, di, dt in (("JUL", date(2026, 7, 5), 100.0), ("AUG", date(2026, 8, 5), 200.0),
                       ("SEP", date(2026, 9, 5), 300.0), ("OCT", date(2026, 10, 5), 400.0),
                       ("NOV", date(2026, 11, 5), 500.0)):
        s.add(Trip(ma_phieu=ma, vehicle_id=v.id, ngay_di=di, ngay_ve=di, km_dau=1000, km_cuoi=1100,
                   doanh_thu=dt, ten_tour="thử"))
    s.commit()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def test_thang_dau_quy_thi_quy_la_quy_truoc_du_ba_thang(db):
    tk = HQ.theo_ky(db, date(2026, 10, 24), hom_nay=date(2026, 10, 24))
    assert tk["thang"]["doanh_thu"] == 400
    assert tk["quy"]["nhan"] == "Quý 3/2026"
    assert tk["quy"]["doanh_thu"] == 600, "quý 3 = T7 + T8 + T9, không phải tháng 10"
    assert tk["quy"]["doanh_thu"] != tk["thang"]["doanh_thu"]
    assert tk["nam"]["doanh_thu"] == 1000, "năm vẫn tính đến mốc (T1–T10)"


def test_quy_truoc_da_het_nen_co_so_sanh_voi_quy_truoc_nua(db):
    q = HQ.theo_ky(db, date(2026, 10, 24), hom_nay=date(2026, 10, 24))["quy"]
    assert q["so_sanh"] is not None, "quý 3 đã hết thì phải có so sánh"
    assert "2026-04" in q["so_sanh"]["nhan"] and "2026-06" in q["so_sanh"]["nhan"]


def test_thang_thu_hai_cua_quy_thi_giu_quy_dang_chay(db):
    q = HQ.theo_ky(db, date(2026, 11, 20), hom_nay=date(2026, 11, 20))["quy"]
    assert q["nhan"].startswith("Quý 4/2026") and q["doanh_thu"] == 900


def test_thang_mot_thi_lui_ve_quy_4_nam_truoc():
    from app.services.hieu_qua_xe import _nhom_ky
    from datetime import timedelta
    mq = date(2027, 1, 1) - timedelta(days=1)
    assert _nhom_ky(mq)["quy"] == ["2026-10", "2026-11", "2026-12"]
