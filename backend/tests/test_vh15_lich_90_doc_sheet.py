# -*- coding: utf-8 -*-
"""VH-15 · Lịch xe 90 ngày đọc thêm Sheet xe (Chủ tịch 11/11/2026: đội xe ghi trước chuyến sắp chạy vào sheet).

Đo trên bản thật 11/11/2026: VTOS chưa có lệnh điều xe nào → lịch báo cả 11 xe trống 100%, và tin sáng thứ Hai
sẽ bảo Kinh doanh bán những ngày xe đã có khách. Nay: ngày có chuyến trên sheet là BẬN (lệnh VTOS thắng sheet),
sheet đọc hỏng thì nói ra và robot KHÔNG gửi tin «xe trống»; «Giữ xe cho tour» chỉ hiện với vai gửi được đề nghị."""
import os
import sys
import tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vh15.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
os.environ["ROBOT_TOKEN"] = "rt-vh15"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services import xe_theo_sheet as XS  # noqa: E402

settings.ROBOT_TOKEN = "rt-vh15"
PW = "Vtos@Demo#2026"
TOK: dict = {}
HOM = date.today()
LINK = "https://docs.google.com/spreadsheets/d/e/2PACX-vh15/pub?gid=0&single=true&output=csv"
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client: TestClient


def _csv():
    a, b = HOM + timedelta(days=3), HOM + timedelta(days=5)
    return ("XE SỐ,SỐ,Lái xe,Tên tour,Ngày đi,Ngày về,Số ngày,CTP\n"
            "XE 1,15001,Tú\n"
            f",50F15001,TÚ,Đà Lạt VH15,{a:%d/%m/%Y},{b:%d/%m/%Y},3,600.000\n")


def h(u: str) -> dict:
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": PW})
        assert r.status_code == 200, f"{u}: {r.text}"
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    global client
    with TestClient(app) as c:
        client = c
        from app.models.core import Param
        from app.models.hr import Vehicle
        from app.services import rules as R
        db = SessionLocal()
        db.add(Vehicle(plate="50F15001", seats=29, active=True, code="VH15X"))
        p = db.execute(select(Param).where(Param.key == XS.KHOA_LINK)).scalars().all()
        if p:
            for x in p:
                x.value = LINK
        else:
            db.add(Param(key=XS.KHOA_LINK, value=LINK, label="x", effective_from=date(2026, 1, 1), status="active"))
        db.commit(); db.close(); R.clear_param_cache()
        yield


@pytest.fixture()
def sheet(monkeypatch):
    noi_dung = {"v": _csv()}

    def doc(url, doc_lai=False, tai=None):
        if noi_dung["v"] is None:
            return {"noi_dung": None, "doc_luc": None, "loi_tai": "Không tải được sheet: 404", "ban_cu": False}
        return {"noi_dung": noi_dung["v"], "doc_luc": "05:30 11/11/2026", "loi_tai": None, "ban_cu": False}
    monkeypatch.setattr(XS, "doc", doc)
    return noi_dung


def _hang(d, bien):
    return next(x for x in d["xe"] if x["xe"] == bien)


def test_1_ngay_co_chuyen_tren_sheet_la_ban(sheet):
    d = client.get("/api/v1/fleet/lich-xe-tuong-lai?so_ngay=30", headers=h("chutich")).json()
    x = _hang(d, "50F15001")
    assert x["o"][3:6] == ["sheet"] * 3 and x["o"][2] == "" and x["o"][6] == ""
    assert x["tour_sheet"]["4"] == "Đà Lạt VH15" and x["cong_suat"] == round(3 * 100 / 30)
    assert d["sheet"]["loi"] is None and d["sheet"]["so_chuyen"] == 1
    kt = [k for k in d["khoang_trong"] if k["xe"] == "50F15001"]
    assert kt[0]["den"] == str(HOM + timedelta(days=2)) and kt[1]["tu"] == str(HOM + timedelta(days=6))


def test_2_sheet_hong_thi_noi_ra_va_khong_gui_tin(sheet):
    sheet["v"] = None
    d = client.get("/api/v1/fleet/lich-xe-tuong-lai?so_ngay=30", headers=h("chutich")).json()
    assert "Không tải được sheet" in d["sheet"]["loi"]
    r = client.post("/api/v1/fleet/robot/lich-xe-gui-tuan", headers={"X-Robot-Token": "rt-vh15"})
    assert r.status_code == 200 and r.json()["da_gui"] is False and "Sheet xe" in r.json()["ly_do"]
    from app.models.core import Alert
    db = SessionLocal()
    assert not db.execute(select(Alert).where(Alert.kind == "xe_trong_tuan")).scalars().first()
    db.close()


def test_3_sheet_doc_duoc_thi_gui(sheet):
    r = client.post("/api/v1/fleet/robot/lich-xe-gui-tuan", headers={"X-Robot-Token": "rt-vh15"})
    assert r.json()["da_gui"] is True, r.text


def test_4_giu_xe_chi_cho_vai_gui_duoc_de_nghi():
    s = open(os.path.join(GOC, "web", "components", "doixe", "LichXe90.tsx"), encoding="utf-8").read()
    assert 'api("/de-nghi-xe/meta").then((m: any) => setDuocGiu(!!m?.toi_duoc_de_nghi))' in s
    assert "{duocGiu && <button" in s and "Chuyến ghi trước trên Sheet xe" in s
    assert client.get("/api/v1/de-nghi-xe/meta", headers=h("chutich")).status_code == 200
