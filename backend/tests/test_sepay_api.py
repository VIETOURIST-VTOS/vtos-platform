"""Kết nối API SePay (kéo giao dịch): chuẩn hóa payload, idempotent, khớp booking, trạng thái kết nối."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_sepay_api.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["SEPAY_API_TOKEN"] = "tok-test"; os.environ["ROBOT_TOKEN"] = "rb"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_sepay_api.db"): os.remove("test_sepay_api.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import sepay as SP

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def fake_get(path, params=None, token=None):
    if path == "/bankaccounts/list":
        return {"status": 200, "bankaccounts": [{"id": 1, "bank_short_name": "TPBank", "account_number": "01811267101", "account_holder_name": "CTCP DU LICH VIETOURIST", "active": 1, "last_transaction": "2026-09-05 10:00:00"}]}
    assert params["transaction_date_min"].startswith("2026-09-01")
    return {"status": 200, "transactions": [
        {"id": "7001", "bank_brand_name": "TPBank", "account_number": "01811267101", "transaction_date": "2026-09-02 09:15:00", "amount_out": "0", "amount_in": "5000000", "transaction_content": "KHONG CO MA", "reference_number": "FT1"},
        {"id": "7002", "bank_brand_name": "TPBank", "account_number": "01811267101", "transaction_date": "2026-09-03 09:15:00", "amount_out": "1200000", "amount_in": "0", "transaction_content": "CHI KHAC", "reference_number": "FT2"}]}


def test_pull_and_status(monkeypatch):
    monkeypatch.setattr(SP, "_get", fake_get)
    h = login("ketoan")
    st = client.get("/api/v1/sepay/status", headers=h).json()
    assert st["api_token_set"] and st["accounts"][0]["account_number"] == "01811267101"
    r = client.post("/api/v1/sepay/pull", json={"from_date": "2026-09-01", "to_date": "2026-09-05"}, headers=h); assert r.status_code == 200, r.text
    assert r.json()["new"] == 2 and r.json()["pending"] == 1
    r2 = client.post("/api/v1/sepay/pull", json={"from_date": "2026-09-01", "to_date": "2026-09-05"}, headers=h).json(); assert r2["new"] == 0
    txns = client.get("/api/v1/bank-transactions", headers=h).json()
    t = next(x for x in txns if x["sepay_id"] == "7001"); assert t["match_status"] == "cho_ke_toan" and t["amount"] == 5000000 and t["gateway"] == "TPBank"
    assert client.post("/api/v1/robot/sepay/pull", json={"from_date": "2026-09-01"}, headers={"X-Robot-Token": "rb"}).status_code == 200
    assert client.post("/api/v1/robot/sepay/pull", json={}, headers={"X-Robot-Token": "sai"}).status_code == 401
    assert client.post("/api/v1/sepay/pull", json={}, headers=login("kd.hoa")).status_code == 403


def test_pull_without_token(monkeypatch):
    monkeypatch.setattr(SP.settings, "SEPAY_API_TOKEN", "")
    r = client.post("/api/v1/sepay/pull", json={"from_date": "2026-09-01"}, headers=login("cntt")); assert r.status_code == 502 and "SEPAY_API_TOKEN" in r.json()["detail"]


def test_webhook_ping_without_id(monkeypatch):
    monkeypatch.setattr(SP.settings, "SEPAY_WEBHOOK_KEY", "k1")
    r = client.post("/api/v1/sepay/webhook", json={"gateway": "TPBank", "content": "test"}, headers={"Authorization": "Apikey k1"})
    assert r.status_code == 201 and r.json()["test"] is True
    assert client.post("/api/v1/sepay/webhook", json={"id": 1}, headers={"Authorization": "Apikey sai"}).status_code == 401
