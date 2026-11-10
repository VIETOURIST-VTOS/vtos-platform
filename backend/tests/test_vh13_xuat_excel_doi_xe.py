# -*- coding: utf-8 -*-
"""VH-13 · Xuất Excel ba bảng đội xe (Chủ tịch duyệt 11/11/2026): Xếp hạng xe & tài xế, Lãi lỗ, Báo cáo từng xe.
Tệp đọc đúng hàm của màn hình; cùng nhóm vai với màn; trang Xếp hạng/Lãi lỗ nhúng trong /xe dùng tháng ở đầu /xe."""
import io
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vh13.db")
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
from openpyxl import load_workbook  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

PW = "Vtos@Demo#2026"
TOK: dict = {}
KY = date.today().strftime("%Y-%m")
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        from app.models.core import User
        from app.models.fleet import Trip
        from app.models.hr import Vehicle
        db = SessionLocal()
        db.add(User(username="vh13.nvkd", full_name="NV KD VH13", role="nv_kd", password_hash=hash_password(PW), active=True))
        v = Vehicle(plate="VH13-01", seats=29, active=True, code="VH13X")
        db.add(v); db.flush()
        d = date.today().replace(day=1)
        db.add(Trip(vehicle_id=v.id, ten_tour="Tour VH13", ngay_di=d, ngay_ve=d, km_dau=1000, km_cuoi=1250,
                    doanh_thu=5_000_000, status="da_gui", ma_phieu="VH13-P1"))
        db.commit(); db.close()
        yield


def _wb(r):
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "attachment" in r.headers["content-disposition"]
    return load_workbook(io.BytesIO(r.content))


def _cot(ws, hang=3):
    return [c.value for c in ws[hang]]


def test_1_xep_hang_hai_trang_tinh():
    wb = _wb(client.get(f"/api/v1/fleet/hieu-qua.xlsx?ky={KY}", headers=h("chutich")))
    assert wb.sheetnames == ["Xe", "Tài xế"]
    assert _cot(wb["Xe"])[:3] == ["Hạng", "Mã xe", "Biển số"] and "LN/ngày" in _cot(wb["Xe"])
    assert any(r[2] == "VH13-01" for r in wb["Xe"].iter_rows(min_row=4, values_only=True))


def test_2_lai_lo_ba_trang_tinh_cung_so_man_hinh():
    wb = _wb(client.get(f"/api/v1/fleet/lai-lo.xlsx?ky={KY}", headers=h("chutich")))
    assert wb.sheetnames == ["Tổng kỳ", "Theo xe", "Theo chuyến"]
    man = client.get(f"/api/v1/fleet/lai-lo?ky={KY}", headers=h("chutich")).json()["tong"]
    tong = {r[0]: r[1] for r in wb["Tổng kỳ"].iter_rows(min_row=4, values_only=True)}
    assert tong["Lợi nhuận"] == man["loi_nhuan"] and tong["Giá vốn vận tải (ba tầng)"] == man["gia_von"]
    chuyen = list(wb["Theo chuyến"].iter_rows(min_row=4, values_only=True))
    assert any(r[0] == "VH13-P1" for r in chuyen)


def test_3_bao_cao_tung_xe_theo_ky():
    wb = _wb(client.get(f"/api/v1/fleet/chuyen.xlsx?ky={KY}", headers=h("chutich")))
    ws = wb["Báo cáo từng xe"]
    dong = [r for r in ws.iter_rows(min_row=4, values_only=True) if r[0] == "VH13-P1"]
    assert dong and dong[0][9] == 250       # km chạy
    assert _cot(ws)[-2:] == ["Trạng thái quyết toán", "Ghi chú"]


def test_4_quyen_va_ky_sai():
    for duong in ("hieu-qua.xlsx", "lai-lo.xlsx", "chuyen.xlsx"):
        assert client.get(f"/api/v1/fleet/{duong}?ky={KY}", headers=h("vh13.nvkd")).status_code == 403
        assert client.get(f"/api/v1/fleet/{duong}?ky=11-2026", headers=h("chutich")).status_code == 422


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_5_mot_nut_moi_bang_va_mot_o_ky():
    assert _w("app", "hieu-qua-doi-xe", "page.tsx").count("<NutExcel ") == 1
    assert _w("app", "lai-lo-doi-xe", "page.tsx").count("<NutExcel ") == 1
    g = _w("components", "doixe", "TrangGon.tsx")
    assert g.count("<NutExcel ") == 1 and "/fleet/chuyen.xlsx?ky=${kyChon}" in g
    hq = _w("app", "hieu-qua-doi-xe", "page.tsx")
    assert '{!chiXepHang && <div className="panel"><h2>Kỳ đánh giá</h2>' in hq
    assert "{!kyTuXe && <label>Kỳ" in _w("app", "lai-lo-doi-xe", "page.tsx")
    xe = _w("app", "xe", "page.tsx")
    assert 'const TRANG_THEO_KY = ["hieu-qua", "lai-lo"];' in xe and "`ky=${ky}`" in xe
