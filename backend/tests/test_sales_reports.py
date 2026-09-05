"""Báo cáo bán hàng (bán tour lẻ, nhắc thu, hủy chỗ, kinh doanh, tour lẻ) + Excel; robot R9 giám sát bất thường."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_sales_reports.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_sales_reports.db"): os.remove("test_sales_reports.db")
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def tour(code):
    return next(t for t in client.get("/api/v1/tours", headers=login("cntt")).json() if t["code"] == code)


def booking(name, phone, pax=2, discount=0):
    t = tour("PT-DL-0912")
    r = client.post("/api/v1/requests", json={"tour_id": t["id"], "customer_name": name, "customer_phone": phone, "source": "Zalo", "care_note": "ok", "pax": pax, "discount": discount}, headers=login("kd.hoa"))
    return client.post(f"/api/v1/requests/{r.json()['request']['id']}/booking", headers=login("dh.lan")).json()["booking"]


def test_reports_and_excel():
    b1 = booking("Khách A", "0901"); b2 = booking("Khách B", "0902", pax=3)
    client.post("/api/v1/receipts/cash", json={"booking_id": b1["id"], "amount": b1["amount"], "payer": "A", "note": "TM"}, headers=login("ketoan"))
    client.post(f"/api/v1/bookings/{b2['id']}/cancel", json={"reason": "Khách bận", "charge": 0}, headers=login("dh.lan"))
    lst = client.get("/api/v1/sales-reports", headers=login("kd.hoa")).json(); assert {x["key"] for x in lst} >= {"ban_tour_le", "nhac_thu", "huy_cho", "kinh_doanh", "tour_le"}
    today = str(date.today())
    r = client.get(f"/api/v1/sales-reports/ban_tour_le?from={today}&to={today}", headers=login("gd_kd" if False else "tgd")).json()
    hoa = next(s for s in r["summary"] if "Hoa" in s["sale"] or s["sale"]); assert r["total"]["cancelled"] >= 1 and r["total"]["bookings"] >= 1
    n = client.get("/api/v1/sales-reports/nhac_thu", headers=login("tp.dieuhanh")).json(); assert n["total"]["bookings"] >= 0 and all(d["due"] > 0 for d in n["detail"])
    h = client.get(f"/api/v1/sales-reports/huy_cho?from={today}&to={today}", headers=login("gd.kd") if False else login("tgd")).json(); assert h["total"]["cancelled"] >= 1 and h["detail"][0]["reason"] == "Khách bận"
    k = client.get(f"/api/v1/sales-reports/kinh_doanh?month={date.today():%Y-%m}", headers=login("tgd")).json(); assert k["summary"] and "f" in k["summary"][0] and k["summary"][0]["moc"] > 0
    t = client.get(f"/api/v1/sales-reports/tour_le?from={today}&to={str(date.today() + timedelta(days=40))}", headers=login("tgd")).json(); assert any(x["tour_code"] == "PT-DL-0912" for x in t["summary"])
    # sale chỉ thấy dòng của mình
    mine = client.get(f"/api/v1/sales-reports/ban_tour_le?from={today}&to={today}", headers=login("kd.hoa")).json(); assert all(s["sale"] == mine["summary"][0]["sale"] for s in mine["summary"])
    x = client.get(f"/api/v1/sales-reports/ban_tour_le/xlsx?from={today}&to={today}", headers=login("tgd")); assert x.status_code == 200 and x.headers["content-type"].startswith("application/vnd.openxmlformats") and len(x.content) > 3000
    from openpyxl import load_workbook
    from io import BytesIO
    wb = load_workbook(BytesIO(x.content)); assert wb.sheetnames == ["Tổng hợp", "Chi tiết"] and wb["Tổng hợp"]["A1"].value == "Báo cáo bán tour lẻ"
    assert client.get("/api/v1/sales-reports/nope", headers=login("tgd")).status_code == 404


def test_r9_anomalies():
    b = booking("Khách giảm lớn", "0903", pax=2, discount=0)
    # giảm giá lớn: sửa trực tiếp discount 20%
    from app.db.session import SessionLocal
    from app.models.core import Booking
    with SessionLocal() as db:
        x = db.get(Booking, b["id"]); x.discount = x.amount * 0.2; db.commit()
    client.post("/api/v1/receipts/cash", json={"booking_id": b["id"], "amount": 35_000_000, "payer": "X", "note": "TM"}, headers=login("ketoan"))
    r = client.post("/api/v1/robot/r9", headers=login("bks")).json(); kinds = {i["kind"] for i in r["items"]}
    assert {"r9_giam_gia_lon", "r9_tien_mat_lon"} <= kinds and r["new_alerts"] >= 2
    assert client.post("/api/v1/robot/r9", headers=login("kd.hoa")).status_code == 403
    al = client.get("/api/v1/alerts", headers=login("chutich")).json(); assert any(a["kind"] == "r9_giam_gia_lon" and a["ref"] == f"booking:{b['code']}" for a in al)
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
