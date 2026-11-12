"""VH-37 · Nhật trình chuyến bản 2 (Chủ tịch duyệt bản xem trước 12/11/2026 08:06).

Mã tour thay Phiếu (nối tour Kinh doanh / lệnh Điều hành), Chi phí + Lãi cạnh Doanh thu, Cờ → Ghi chú,
nút trạng thái 4 màu ở cuối (Sửa / Mở lại nằm trong chi tiết), chuyến huỷ không hiện."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vh37.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh37.db"): os.remove("test_vh37.db")
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.core import Tour
from app.models.fleet import Trip

TOK: dict = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


client = None


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        yield
GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _w():
    return open(os.path.join(GOC, "web", "app", "doi-xe", "page.tsx"), encoding="utf-8").read()


def test_1_api_tra_ma_tour_va_tong_chi():
    h = login("cntt")
    vid = client.get("/api/v1/fleet/xe", headers=h).json()[0]["id"]
    d = date.today() + timedelta(days=200)
    t = client.post("/api/v1/fleet/chuyen", headers=h, json={"vehicle_id": vid, "ten_tour": "VH37 thử",
                    "ngay_di": str(d), "ngay_ve": str(d + timedelta(days=1)), "doanh_thu": 5_000_000})
    assert t.status_code == 201, t.text
    tid = t.json()["id"]
    for amt, bc in ((1_200_000, "vietourist_tam_ung"), (300_000, "chu_xe")):
        r = client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=h,
                        json={"kind": "cau_duong", "amount": amt, "ben_chiu": bc})
        assert r.status_code in (200, 201), r.text
    db = SessionLocal()
    try:
        tour = db.query(Tour).first()
        if tour:
            db.get(Trip, tid).tour_id = tour.id
            db.commit()
            ma = tour.code
        else:
            ma = ""
    finally:
        db.close()
    row = next(x for x in client.get(f"/api/v1/fleet/chuyen?vehicle_id={vid}", headers=h).json() if x["id"] == tid)
    assert row["tong_chi"] == 1_500_000
    assert row["ma_tour"] == ma


def test_2_man_bo_phieu_vts_ung_co_them_chi_phi_lai_ghi_chu():
    s = _w()
    dau = s[s.index("<thead><tr><th aria-hidden=\"true\"></th><th>Mã tour</th>"):]
    dau = dau[:dau.index("</tr></thead>")]
    for c in ("Mã tour", "Tên tour", "Xe", "Đi → về", "Km chạy", "Doanh thu", "Chi phí", "Lãi", "Ghi chú", "T.thái"):
        assert f">{c}</th>" in dau, c
    assert "Phiếu</th>" not in dau and "VTS ứng" not in dau and ">Cờ</th>" not in dau


def test_3_nut_trang_thai_va_sua_trong_chi_tiet_huy_an():
    s = _w()
    assert 'const chuyenHien = chuyen.filter((t) => t.status !== "huy");' in s
    assert 't.status === "da_xac_nhan" ? ["xam", "Xám"' in s
    dong = s[s.index('<tr className={"nt-dong"'):s.index('{mo && <tr className="nt-ct">')]
    assert "Sửa</button>" not in dong and "Mở lại để sửa" not in dong   # một nút một chỗ
    ct = s[s.index('{mo && <tr className="nt-ct">'):]
    assert 'className="nt-nut"' in ct and "Mở lại để sửa" in ct
