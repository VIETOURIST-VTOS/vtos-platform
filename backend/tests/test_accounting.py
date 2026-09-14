"""Robot R2 – kế toán TT99: bút toán tự động từ phiếu thu / hóa đơn / quyết toán, sổ cái, cân đối, khóa kỳ, đảo."""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_acc.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_acc.db"):
    os.remove("test_acc.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}
P = f"{date.today():%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def booking(code):
    return next(b for b in client.get("/api/v1/bookings", headers=login("ketoan")).json() if b["code"] == code)


def journal(**q):
    return client.get("/api/v1/journal", params=q, headers=login("ketoan")).json()


def test_accounts_seeded_and_read_roles():
    acc = client.get("/api/v1/accounts", headers=login("bks")).json()
    assert {"111", "112", "131", "154", "331", "3331", "511", "632"} <= {a["code"] for a in acc}
    assert client.get("/api/v1/journal", headers=login("kd.hoa")).status_code == 403


def test_cash_receipt_posts_111_131():
    b = booking("BK26090003")
    r = client.post("/api/v1/receipts/cash", json={"booking_id": b["id"], "amount": 1000000, "payer": "Lê C", "note": "quầy"}, headers=login("ketoan")).json()
    e = next(x for x in journal() if x["source_ref"] == f"receipt:{r['receipt']['code']}")
    assert e["status"] == "da_ghi_so" and e["source_type"] == "thu_tien"
    d = {(l["account"], l["debit"], l["credit"]) for l in e["lines"]}
    assert ("111", 1000000, 0) in d and ("131", 0, 1000000) in d


def test_invoice_flow_and_vat_split():
    b = booking("BK26090001")  # 7.960.000 gồm thuế
    inv = client.post("/api/v1/invoices", json={"booking_id": b["id"], "customer_tax_code": "0301234567", "customer_address": "Q1, TP.HCM"}, headers=login("ketoan")).json()["invoice"]
    assert inv["status"] == "nhap" and inv["vat_rate"] == 0.10 and inv["pre_tax"] + inv["vat"] == inv["total"] == 7960000
    assert client.post("/api/v1/invoices", json={"booking_id": b["id"]}, headers=login("ketoan")).status_code == 422  # trùng
    res = client.post(f"/api/v1/invoices/{inv['id']}/issue", headers=login("ketoan")).json()
    assert res["invoice"]["number"] == 1 and res["invoice"]["provider_ref"].startswith("LOCAL-")
    e = next(x for x in journal() if x["source_ref"].startswith("invoice:"))
    acc = {l["account"]: (l["debit"], l["credit"]) for l in e["lines"]}
    assert acc["131"][0] == 7960000 and acc["511"][1] == inv["pre_tax"] and acc["3331"][1] == inv["vat"]
    # hủy → bút toán đảo, hóa đơn giữ số
    assert client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": ""}, headers=login("ketoan")).status_code == 422
    assert "đảo" in client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "Khách đổi thông tin"}, headers=login("ketoan")).json()["message"]
    rev = next(x for x in journal() if x["source_type"] == "dao")
    assert {l["account"]: (l["debit"], l["credit"]) for l in rev["lines"]}["131"] == (0, 7960000)


def test_settlement_posts_154_331_and_632():
    t = next(x for x in client.get("/api/v1/tours", headers=login("ketoan")).json()["rows"] if x["code"] == "DN-HCM-0820")
    client.post(f"/api/v1/tours/{t['id']}/close", json={"actual_revenue": 189000000, "actual_cost": 158000000}, headers=login("dh.lan"))
    assert client.post(f"/api/v1/tours/{t['id']}/kt-confirm", headers=login("ketoan")).status_code == 200
    es = [x for x in journal() if x["source_ref"] == "tour:DN-HCM-0820"]
    assert len(es) == 2
    pairs = {(l["account"], l["debit"], l["credit"]) for e in es for l in e["lines"]}
    assert {("154", 158000000, 0), ("335", 0, 158000000), ("632", 158000000, 0), ("154", 0, 158000000)} <= pairs   # chưa có đề nghị chi → toàn bộ trích trước 335
    led = client.get("/api/v1/ledger", params={"account": "154", "period": P}, headers=login("tgd")).json()
    assert led["closing"] == 0 and led["total_debit"] == 158000000


def test_manual_entry_balance_gate_draft_post_and_trial_balance():
    bad = client.post("/api/v1/journal", json={"entry_date": str(date.today()), "description": "lệch", "lines": [{"account": "642", "debit": 100}, {"account": "111", "credit": 90}]}, headers=login("ketoan"))
    assert bad.status_code == 422 and "không cân" in bad.json()["detail"]
    ok = client.post("/api/v1/journal", json={"entry_date": str(date.today()), "description": "Chi văn phòng phẩm", "lines": [{"account": "642", "debit": 500000}, {"account": "111", "credit": 500000}]}, headers=login("ketoan")).json()["entry"]
    assert ok["status"] == "nhap"
    tb = client.get("/api/v1/trial-balance", params={"period": P}, headers=login("chutich")).json()
    assert tb["balanced"] and all(r["account"] != "642" for r in tb["rows"])  # nháp chưa lên sổ
    # khóa kỳ bị chặn khi còn nháp
    assert "nháp" in client.post(f"/api/v1/periods/{P}/lock", json={"note": "thử"}, headers=login("ketoan")).json()["detail"]
    assert client.post(f"/api/v1/journal/{ok['id']}/post", headers=login("ketoan")).status_code == 200
    tb = client.get("/api/v1/trial-balance", params={"period": P}, headers=login("chutich")).json()
    assert tb["balanced"] and next(r for r in tb["rows"] if r["account"] == "642")["debit"] == 500000


def test_lock_period_blocks_posting():
    assert client.post(f"/api/v1/periods/{P}/lock", json={"note": "Khóa tháng"}, headers=login("ketoan")).status_code == 200
    r = client.post("/api/v1/journal", json={"entry_date": str(date.today()), "description": "sau khóa", "lines": [{"account": "642", "debit": 1}, {"account": "111", "credit": 1}], "post": True}, headers=login("ketoan"))
    assert r.status_code == 422 and "đã khóa" in r.json()["detail"]
    assert next(p for p in client.get("/api/v1/periods", headers=login("bks")).json() if p["period"] == P)["locked"] is True
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
