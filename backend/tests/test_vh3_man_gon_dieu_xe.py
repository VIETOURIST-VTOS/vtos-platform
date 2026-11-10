# -*- coding: utf-8 -*-
"""VH-3 · MÀN GỌN cho năm trang điều xe còn lại + ô «Chờ tôi ký» (Chủ tịch duyệt bản xem trước 10/11/2026).

Phép thử giữ bốn điều máy chủ phải đúng để màn gọn không nói sai:
  1. Hồ sơ tài xế có cờ `co_tai_khoan` — cùng luật nối với /xe-hdv/cua-toi.
  2. Lệnh điều xe trả trạng thái nhận của tài xế và hạn nhận (từ `nhan_lenh`, không tính lại).
  3. Xe hôm nay: mỗi xe đúng một nhóm; báo hỏng «phải dừng» xếp trước «đang đi».
  4. «Chờ tôi ký» chỉ mời đúng vai mà cửa ký sẽ nhận (CHO_BUOC × VAI_KY).
"""
import os
import re
import sys
import tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vh3.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

PW = "Vtos@Demo#2026"
TOK: dict = {}
CTX: dict = {}
client: TestClient
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")


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
        from app.core.security import hash_password
        from app.models.core import Tour, User
        from app.models.fleet import Fault, Trip
        from app.models.hr import DispatchOrder, Employee, Vehicle
        db = SessionLocal()
        gd = User(username="vh3.gdxe", full_name="GĐ đội xe VH3", role="gd_doi_xe", department="doi_xe",
                  staff_code="VH3GD", password_hash=hash_password(PW), active=True)
        tx = User(username="vh3.taixe", full_name="Tài xế VH3", role="tai_xe", department="doi_xe",
                  staff_code="VH3TX", password_hash=hash_password(PW), active=True)
        db.add_all([gd, tx]); db.flush()
        e = db.execute(select(Employee).where(Employee.full_name.like("Lý Văn Sơn%"))).scalars().first()
        e.user_id = tx.id
        xe = [v for v in db.execute(select(Vehicle).order_by(Vehicle.id)).scalars() if v.active][:2]
        hom = date.today()
        t = Tour(code="VH3-TOUR", name="Tây Nguyên (VH3)", tour_type="doan_noi_dia", start_date=hom,
                 end_date=hom + timedelta(days=2), status="da_duyet", operator_id=gd.id)
        db.add(t); db.flush()
        # xe[0]: có lệnh phủ hôm nay → đang đi. xe[1]: có lệnh VÀ báo hỏng phải dừng → bị chặn.
        for v in xe:
            db.add(DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=e.id, date_from=hom,
                                 date_to=hom + timedelta(days=2), status="cho_xac_nhan", created_by="vh3"))
        db.add(Fault(vehicle_id=xe[1].id, hien_tuong="Mất phanh khí (VH3)", muc_do="phai_dung_xe",
                     trang_thai="moi"))
        tr = [Trip(vehicle_id=xe[0].id, ngay_di=hom, ngay_ve=hom, ten_tour="VH3 chờ CT", qt_trang_thai="cho_tgd",
                   doanh_thu=15000000),
              Trip(vehicle_id=xe[0].id, ngay_di=hom, ngay_ve=hom, ten_tour="VH3 chờ KT", qt_trang_thai="cho_ke_toan")]
        db.add_all(tr)
        db.commit()
        CTX.update(tai_xe=e.id, xe=[v.plate for v in xe], tr=[x.id for x in tr])
        db.close()
        yield


def test_01_tai_xe_co_co_tai_khoan():
    r = client.get("/api/v1/tai-xe", headers=h("vh3.gdxe"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert "chua_co_tai_khoan" in d
    son = next(x for x in d["rows"] if x["id"] == CTX["tai_xe"])
    assert son["co_tai_khoan"] is True
    assert all("co_tai_khoan" in x for x in d["rows"])


def test_02_lenh_co_trang_thai_nhan():
    r = client.get("/api/v1/fleet/lenh-dieu-xe", headers=h("vh3.gdxe"))
    assert r.status_code == 200, r.text
    x = next(x for x in r.json() if x["tour"] == "VH3-TOUR")
    assert x["trang_thai_nhan"] in ("chua_nhan", "qua_han")      # lệnh đi hôm nay, chưa ai bấm nhận
    assert x["nhan_luc"] is None and x["han_nhan"]


def test_03_xe_hom_nay_moi_xe_mot_nhom():
    r = client.get("/api/v1/fleet/xe-hom-nay-gon", headers=h("vh3.gdxe"))
    assert r.status_code == 200, r.text
    d = r.json()
    di = [x["xe"] for x in d["dang_di"]]
    chan = [x["xe"] for x in d["bi_chan"]]
    bai = [x["xe"] for x in d["o_bai"]]
    assert CTX["xe"][0] in di
    assert CTX["xe"][1] in chan and CTX["xe"][1] not in di      # bị chặn xếp trước đang đi
    tat = di + chan + bai
    assert len(tat) == len(set(tat))


def test_04_cho_toi_ky_dung_vai():
    ct = client.get("/api/v1/fleet/quyet-toan-chuyen/cho-toi-ky", headers=h("chutich"))
    assert ct.status_code == 200, ct.text          # không bị cửa /quyet-toan-chuyen/{tid} nuốt mất
    kt = client.get("/api/v1/fleet/quyet-toan-chuyen/cho-toi-ky", headers=h("ketoan")).json()
    gd = client.get("/api/v1/fleet/quyet-toan-chuyen/cho-toi-ky", headers=h("vh3.gdxe")).json()
    ids_ct = {x["id"] for x in ct.json()["rows"]}
    ids_kt = {x["id"] for x in kt["rows"]}
    assert CTX["tr"][0] in ids_ct and CTX["tr"][1] not in ids_ct
    assert CTX["tr"][1] in ids_kt and CTX["tr"][0] not in ids_kt
    assert gd["rows"] == []                         # GĐ đội xe không giữ bước ký nào


def test_05_man_gon_dang_ky_du_nam_trang():
    src = open(os.path.join(WEB, "app", "xe", "page.tsx"), encoding="utf-8").read()
    for k, f in [("de-nghi", "DeNghiXeGon"), ("lap-lenh", "LapLenhGon"), ("xe-hom-nay", "XeHomNayGon"),
                 ("tai-xe", "TaiXeGon"), ("chu-xe", "ChuXeGon")]:
        assert re.search(rf'"{k}":\s*\(p\)\s*=>\s*<G\.{f}\b', src), k
    gon = open(os.path.join(WEB, "components", "doixe", "TrangGon.tsx"), encoding="utf-8").read()
    bc = gon.split("export function BaoCaoXeGon", 1)[1].split("export function", 1)[0]
    assert "<ChoToiKy" in bc
    assert "/fleet/quyet-toan-chuyen/cho-toi-ky" in gon
    assert "method:" not in gon                     # màn gọn chỉ đọc; từ chối làm ở màn đề nghị đầy đủ
