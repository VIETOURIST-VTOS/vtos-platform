"""BCTC rút gọn (B01/B02/B03), kết chuyển 911 nháp, tờ khai GTGT/TNCN + XML."""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_rep.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_rep.db"): os.remove("test_rep.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; P = f"{date.today():%Y-%m}"


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_statements_balance_and_tax_forms():
    kt = login("ketoan")
    b = next(x for x in client.get("/api/v1/bookings", headers=kt).json() if x["code"] == "BK26090001")
    client.post("/api/v1/receipts/cash", json={"booking_id": b["id"], "amount": 7960000, "payer": "A"}, headers=kt)
    inv = client.post("/api/v1/invoices", json={"booking_id": b["id"], "customer_tax_code": "0301"}, headers=kt).json()["invoice"]
    client.post(f"/api/v1/invoices/{inv['id']}/issue", headers=kt)
    client.post("/api/v1/journal", json={"entry_date": str(date.today()), "description": "Chi VPP", "post": True, "lines": [{"account": "642", "debit": 500000}, {"account": "111", "credit": 500000}]}, headers=kt)
    bs = client.get("/api/v1/reports/balance-sheet", params={"period": P}, headers=login("chutich")).json()
    assert bs["balanced"] and bs["total_assets"] == 7960000 - 500000
    pl = client.get("/api/v1/reports/income-statement", params={"period": P}, headers=login("tgd")).json()
    rows = dict((r[0], r[2]) for r in pl["rows"])
    assert round(rows["01"]) == inv["pre_tax"] and rows["26"] == 500000 and round(rows["60"]) == round(inv["pre_tax"] - 500000)
    cf = client.get("/api/v1/reports/cash-flow", params={"period": P}, headers=login("bks")).json()
    r = dict((x[0], x[2]) for x in cf["rows"])
    assert cf["reconciled"] and r["01"] == 7960000 and r["07"] == -500000 and r["70"] == 7460000
    vat = client.get("/api/v1/tax/vat", params={"period": P}, headers=kt).json()
    v = dict((x[0], x[2]) for x in vat["rows"])
    assert v["[33]"] == inv["vat"] and v["[40]"] == inv["vat"]
    xml = client.get("/api/v1/tax/vat/xml", params={"period": P}, headers=kt)
    assert xml.status_code == 200 and "01/GTGT" in xml.text and 'ma="33"' in xml.text
    res = client.post(f"/api/v1/reports/closing-entries/{P}", headers=kt).json()
    assert len(res["entries"]) == 3 and all(e["status"] == "nhap" for e in res["entries"])
    assert client.post(f"/api/v1/reports/closing-entries/{P}", headers=kt).status_code == 422
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
