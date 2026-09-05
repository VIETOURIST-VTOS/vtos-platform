"""Dịch vụ lẻ Non-package: tạo (mã KLEddmmyy[_n], tour non_package + booking + dòng chi phí), thu tiền, in phiếu, sửa, hủy có phí → bảo lưu, tổng hợp theo loại, chốt tháng."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_nonpackage.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nonpackage.db"): os.remove("test_nonpackage.db")
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


def test_create_pay_print_edit_cancel_summary():
    h = login("kd.hoa")
    assert client.post("/api/v1/non-package", json={"service_type": "VISA", "customer_name": "Hoàng Văn Nam", "customer_phone": "", "source": "Zalo", "amount": 7000000}, headers=h).json()["detail"]["gate"] == "CONG_4"
    r = client.post("/api/v1/non-package", json={"service_type": "VISA", "description": "Visa Mỹ B1/B2", "country": "MỸ", "customer_name": "Hoàng Văn Nam", "customer_phone": "0765090170", "source": "Facebook", "amount": 7000000, "cost_amount": 4500000, "supplier_name": "Đại lý visa ABC", "service_date": str(date.today() + timedelta(days=10))}, headers=h)
    assert r.status_code == 201, r.text
    row = r.json()["row"]; assert row["tour_code"] == f"KLE{date.today():%d%m%y}" and row["pmt_status"] == "UNPAID" and row["profit"] == 2500000 and row["deposit_pct"] if "deposit_pct" in row else True
    r2 = client.post("/api/v1/non-package", json={"service_type": "FLIGHT", "description": "Vé SGN–BKK", "country": "THÁI LAN", "customer_name": "Trần Mai Linh", "customer_phone": "0969662280", "source": "Zalo", "amount": 4448000, "cost_amount": 4000000}, headers=login("dh.lan")).json()["row"]
    assert r2["tour_code"] == f"KLE{date.today():%d%m%y}_2"
    # dòng chi phí sinh trên tour KLE; tour loại non_package
    st = client.get(f"/api/v1/tours/{row['tour_id']}/settlement", headers=h).json(); assert st["lines"][0]["actual"] == 4500000 and st["lines"][0]["supplier_name"] == "Đại lý visa ABC"
    t = client.get(f"/api/v1/tours/{row['tour_id']}/detail", headers=h).json(); assert t["tour_type"] == "non_package"
    # thu tiền → PAID; in phiếu
    assert client.post("/api/v1/receipts/cash", json={"booking_id": row["id"], "amount": 7000000, "payer": "Nam", "note": "TM"}, headers=login("ketoan")).status_code == 201
    lst = client.get("/api/v1/non-package?paid=paid", headers=h).json(); assert any(x["id"] == row["id"] and x["pmt_status"] == "PAID" for x in lst["rows"])
    p = client.get(f"/api/v1/non-package/{row['id']}/print", headers=h); assert p.status_code == 200 and "PHIẾU XÁC NHẬN DỊCH VỤ" in p.text and "7,000,000" in p.text
    # sửa giá vốn → dòng chi phí cập nhật; đổi giá khi đã khóa bị chặn
    e = client.put(f"/api/v1/non-package/{row['id']}", json={"cost_amount": 4800000}, headers=h).json(); assert e["cost_amount"] == 4800000 and e["profit"] == 2200000
    assert client.get(f"/api/v1/tours/{row['tour_id']}/settlement", headers=h).json()["summary"]["actual"] == 4800000
    client.post("/api/v1/bookings/check", headers=login("tp.dieuhanh"))
    assert client.put(f"/api/v1/non-package/{row['id']}", json={"amount": 7500000}, headers=h).json()["detail"]["gate"] == "KHOA_BOOKING"
    # tổng hợp theo loại
    s = client.get(f"/api/v1/non-package?month={date.today():%Y-%m}", headers=login("tgd")).json()["summary"]
    assert s["total"]["n"] == 2 and s["total"]["revenue"] == 11448000 and s["by_type"][0]["service_type"] == "VISA"
    # hủy dịch vụ vé (đã thu 1tr) có phí 300k → bảo lưu 700k
    client.post("/api/v1/receipts/cash", json={"booking_id": r2["id"], "amount": 1000000, "payer": "Linh", "note": "TM"}, headers=login("ketoan"))
    c = client.post(f"/api/v1/bookings/{r2['id']}/cancel", json={"reason": "Khách đổi lịch bay", "charge": 300000}, headers=login("dh.lan")).json(); assert c["retention"]
    s = client.get(f"/api/v1/non-package?month={date.today():%Y-%m}", headers=login("tgd")).json()["summary"]; assert s["total"]["n"] == 1 and s["total"]["cancelled"] == 1
    # chốt tháng: chỉ tháng đã kết thúc
    assert client.post("/api/v1/non-package/close-month", json={"month": f"{date.today():%Y-%m}"}, headers=login("ketoan")).status_code == 422
    assert client.post("/api/v1/non-package/close-month", json={"month": "2026-08"}, headers=login("kd.hoa")).status_code == 403
    assert client.post("/api/v1/non-package/close-month", json={"month": "2026-08"}, headers=login("ketoan")).json()["closed"] == []


def test_close_month_posts_accounting():
    h = login("dh.lan")
    row = client.post("/api/v1/non-package", json={"service_type": "HOTEL", "description": "KS Đà Lạt 2 đêm", "customer_name": "Lê Văn Cường", "customer_phone": "0912345678", "source": "Web", "amount": 3000000, "cost_amount": 2400000, "supplier_name": "KS Sammy", "service_date": "2026-07-20"}, headers=h).json()["row"]
    client.post("/api/v1/receipts/cash", json={"booking_id": row["id"], "amount": 3000000, "payer": "Cường", "note": "TM"}, headers=login("ketoan"))
    from app.db.session import SessionLocal
    from app.models.core import Tour
    with SessionLocal() as db:
        t = db.get(Tour, row["tour_id"]); t.start_date = t.end_date = date(2026, 7, 20); db.commit()
    res = client.post("/api/v1/non-package/close-month", json={"month": "2026-07"}, headers=login("ketoan")).json(); assert row["tour_code"] in res["closed"], res
    d = client.get(f"/api/v1/tours/{row['tour_id']}/detail", headers=h).json(); assert d["status"] == "kt_xac_nhan" and d["actual_revenue"] == 3000000 and d["actual_cost"] == 2400000
    es = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == f"tour:{row['tour_code']}"]
    pairs = {(l["account"], l["debit"], l["credit"]) for e in es for l in e["lines"]}; assert ("632", 2400000, 0) in pairs and ("335", 0, 2400000) in pairs
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
