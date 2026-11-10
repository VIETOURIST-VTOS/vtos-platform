# -*- coding: utf-8 -*-
"""VH-9 · Lịch xe 90 ngày tới (Chủ tịch duyệt 11/11/2026): công suất, khoảng trống để bán, tin sáng thứ Hai."""
import os
import sys
import tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vh9.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
os.environ["ROBOT_TOKEN"] = "rt-vh9"
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

settings.ROBOT_TOKEN = "rt-vh9"
PW = "Vtos@Demo#2026"
TOK: dict = {}
CTX: dict = {}
client: TestClient


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
        from app.models.fleet import Fault
        from app.models.hr import DispatchOrder, Employee, Vehicle
        db = SessionLocal()
        kd = User(username="vh9.gdkd", full_name="GĐ kinh doanh VH9", role="gd_kd", password_hash=hash_password(PW), active=True)
        nv = User(username="vh9.nvkd", full_name="NV kinh doanh VH9", role="nv_kd", password_hash=hash_password(PW), active=True)
        db.add_all([kd, nv]); db.flush()
        hom = date.today()
        xe = [Vehicle(plate=f"VH9-{i}", seats=29, active=True, code=f"VH9X{i}") for i in range(3)]
        db.add_all(xe); db.flush()
        e = db.execute(select(Employee)).scalars().first()
        t = Tour(code="VH9-T", name="Tour VH9", tour_type="doan_noi_dia", start_date=hom, end_date=hom + timedelta(days=4),
                 status="da_duyet", operator_id=kd.id)
        db.add(t); db.flush()
        # xe 0: có lệnh 5 ngày đầu; xe 1: trống hết; xe 2: báo hỏng phải dừng
        db.add(DispatchOrder(tour_id=t.id, vehicle_id=xe[0].id, driver_id=e.id, date_from=hom,
                             date_to=hom + timedelta(days=4), status="cho_xac_nhan", created_by="vh9"))
        db.add(Fault(vehicle_id=xe[2].id, hien_tuong="Gãy nhíp (VH9)", muc_do="phai_dung_xe", trang_thai="moi"))
        db.commit()
        CTX.update(xe=[v.plate for v in xe], hom=hom)
        db.close()
        yield


def _hang(d, bien):
    return next(x for x in d["xe"] if x["xe"] == bien)


def test_1_luoi_va_cong_suat():
    r = client.get("/api/v1/fleet/lich-xe-tuong-lai?so_ngay=30", headers=h("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    x0, x1, x2 = (_hang(d, b) for b in CTX["xe"])
    assert x0["o"][:5] == ["lenh"] * 5 and x0["o"][5] == ""
    assert x0["cong_suat"] == round(5 * 100 / 30)
    assert x1["cong_suat"] == 0
    assert x2["bi_chan"] and x2["cong_suat"] is None and set(x2["o"]) == {"chan"}


def test_2_xe_hong_khong_bao_gio_la_khoang_trong():
    d = client.get("/api/v1/fleet/lich-xe-tuong-lai", headers=h("chutich")).json()
    xe_trong = {k["xe"] for k in d["khoang_trong"]}
    assert CTX["xe"][1] in xe_trong and CTX["xe"][2] not in xe_trong
    k0 = [k for k in d["khoang_trong"] if k["xe"] == CTX["xe"][0]]
    assert k0 and k0[0]["tu"] == str(CTX["hom"] + timedelta(days=5))


def test_3_phan_kinh_doanh_chi_co_khoang_trong():
    # Cửa riêng cho phòng Kinh doanh: chỉ khoảng trống + công suất theo tuần, không lưới, không tên tour.
    # Vai gd_kd / tp_kd vào được cửa này cần khai màn hình trong access.py (làn R2 giữ) — đợt sau; hôm nay
    # Kinh doanh nhận danh sách qua tin sáng thứ Hai (test_4).
    r = client.get("/api/v1/fleet/lich-xe-tuong-lai/khoang-trong", headers=h("chutich"))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"tu", "den", "khoang_trong", "tuan", "nguong_thap", "cong_suat_30", "sheet"}


def test_4_tin_sang_thu_hai_mot_tuan_mot_tin(monkeypatch):
    # VH-15: lịch đọc thêm Sheet xe; sheet đọc hỏng thì robot không gửi. Ở đây cho sheet đọc được, không chuyến.
    from app.services import xe_theo_sheet as XS
    monkeypatch.setattr(XS, "doc", lambda url, doc_lai=False, tai=None: {
        "noi_dung": "XE SỐ,SỐ,Lái xe,Tên tour,Ngày đi,Ngày về\n", "doc_luc": "x", "loi_tai": None, "ban_cu": False})
    assert client.post("/api/v1/fleet/robot/lich-xe-gui-tuan").status_code == 401
    r = client.post("/api/v1/fleet/robot/lich-xe-gui-tuan", headers={"X-Robot-Token": "rt-vh9"})
    assert r.status_code == 200 and r.json()["da_gui"], r.text
    assert set(r.json()["nguoi_nhan"]) == {"chutich", "tgd", "tp_dh", "gd_kd", "tp_kd", "ptgd_mkt", "ptgd_doan"}
    r2 = client.post("/api/v1/fleet/robot/lich-xe-gui-tuan", headers={"X-Robot-Token": "rt-vh9"})
    assert r2.json()["da_gui"] is False
    from app.models.core import Alert
    db = SessionLocal()
    a = db.execute(select(Alert).where(Alert.kind == "xe_trong_tuan")).scalars().all()
    db.close()
    assert len(a) == 1 and CTX["xe"][1] in a[0].message and CTX["xe"][2] not in a[0].message


def test_5_man_hinh_dang_ky_trang_con():
    web = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")
    s = open(os.path.join(web, "app", "xe", "page.tsx"), encoding="utf-8").read()
    assert '{ ma: "lich-90", ten: "Lịch xe 90 ngày"' in s and '"lich-90": (p) => <LichXe90 mo={p.mo} />' in s
    g = open(os.path.join(web, "components", "doixe", "LichXe90.tsx"), encoding="utf-8").read()
    assert "/lenh-dieu-xe/de-nghi/moi?tu=${k.tu}&den=${k.den}" in g    # giữ xe đi qua đề nghị xe như luồng cũ
