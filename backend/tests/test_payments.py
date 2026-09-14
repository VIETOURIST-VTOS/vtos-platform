"""Robot R1 – thu tiền SePay: khớp tuyệt đối, chờ Kế toán, idempotent, tiền mặt."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_pay.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
os.environ["SEPAY_WEBHOOK_KEY"] = "test-key"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_pay.db"):
    os.remove("test_pay.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.SEPAY_WEBHOOK_KEY = "test-key"

client = TestClient(app)
TOK = {}
H = {"Authorization": "Apikey test-key"}


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


def test_webhook_requires_key():
    assert client.post("/api/v1/sepay/webhook", json={"id": 1}).status_code == 401


def test_exact_match_creates_receipt_and_is_idempotent():
    b = booking("BK26090001")   # 4 khách × 1.990.000 = 7.960.000
    p = {"id": 9001, "gateway": "TPBank", "transactionDate": "2026-09-05 09:00:00", "accountNumber": "0001", "transferType": "in",
         "transferAmount": 7960000, "content": "NGUYEN VAN A CK BK26090001 tour phan thiet", "referenceCode": "FT1"}
    r = client.post("/api/v1/sepay/webhook", json=p, headers=H).json()
    assert r["new"] is True and r["match_status"] == "da_khop"
    r2 = client.post("/api/v1/sepay/webhook", json=p, headers=H).json()
    assert r2["new"] is False
    rc = [x for x in client.get("/api/v1/receipts", headers=login("ketoan")).json() if x["booking_code"] == "BK26090001"]
    assert len(rc) == 1 and rc[0]["status"] == "tu_dong" and rc[0]["amount"] == 7960000
    assert booking("BK26090001")["paid"] == 7960000


def test_partial_amount_goes_to_accountant_then_assign():
    p = {"id": 9002, "transactionDate": "2026-09-05 10:00:00", "transferType": "in", "transferAmount": 3000000, "content": "CK BK26090002 coc"}
    r = client.post("/api/v1/sepay/webhook", json=p, headers=H).json()
    assert r["match_status"] == "cho_ke_toan" and "≠" in r["note"]
    t = next(x for x in client.get("/api/v1/bank-transactions?status=cho_ke_toan", headers=login("ketoan")).json() if x["sepay_id"] == "9002")
    assert client.post(f"/api/v1/bank-transactions/{t['id']}/assign", json={"booking_id": booking("BK26090002")["id"], "note": "Đặt cọc đợt 1"}, headers=login("kd.hoa")).status_code == 403
    res = client.post(f"/api/v1/bank-transactions/{t['id']}/assign", json={"booking_id": booking("BK26090002")["id"], "note": "Đặt cọc đợt 1"}, headers=login("ketoan")).json()
    assert res["receipt"]["status"] == "ke_toan_xac_nhan"
    assert booking("BK26090002")["paid"] == 3000000
    # phần còn lại 2.970.000 chuyển sau → khớp tuyệt đối phần còn phải thu
    p2 = {"id": 9003, "transactionDate": "2026-09-06 10:00:00", "transferType": "in", "transferAmount": 2970000, "content": "BK 26090002 thanh toan"}
    assert client.post("/api/v1/sepay/webhook", json=p2, headers=H).json()["match_status"] == "da_khop"
    assert booking("BK26090002")["paid"] == 5970000


def test_no_code_and_outgoing():
    r = client.post("/api/v1/sepay/webhook", json={"id": 9004, "transferType": "in", "transferAmount": 500000, "content": "chuyen tien"}, headers=H).json()
    assert r["match_status"] == "cho_ke_toan"
    r = client.post("/api/v1/sepay/webhook", json={"id": 9005, "transferType": "out", "transferAmount": 500000, "content": "tra NCC"}, headers=H).json()
    assert r["match_status"] == "bo_qua"


def test_confirm_and_cash_and_summary():
    rc = next(x for x in client.get("/api/v1/receipts", headers=login("ketoan")).json() if x["status"] == "tu_dong")
    assert client.post(f"/api/v1/receipts/{rc['id']}/confirm", headers=login("ketoan")).status_code == 200
    b = booking("BK26090003")
    res = client.post("/api/v1/receipts/cash", json={"booking_id": b["id"], "amount": 1000000, "payer": "Lê C", "note": "Thu tại quầy"}, headers=login("ketoan")).json()
    assert res["receipt"]["method"] == "tien_mat"
    s = client.get("/api/v1/collections/summary", headers=login("tgd")).json()
    row = next(x for x in s["bookings"] if x["code"] == "BK26090003")
    assert row["due"] == row["total"] - 1000000
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
