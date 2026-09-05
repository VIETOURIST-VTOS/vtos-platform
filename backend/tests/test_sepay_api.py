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


def test_match_by_vietrip_tour_code(monkeypatch):
    """Khách CK ghi mã tour Vietrip (không dấu chấm) → khớp booking của tour còn phải thu đúng số tiền."""
    monkeypatch.setattr(SP.settings, "SEPAY_WEBHOOK_KEY", "k1")
    h = login("cntt")
    tour = {"recID": 5001, "tourcode": "NT001.03110926", "ngayKhoiHanh": "2026-09-11T00:00:00", "ngayKetThuc": "2026-09-13T00:00:00", "soChoMoBan": 40, "loaiTour": "TOURLE", "nuoc": "", "fstUser": "A", "adl": 3990000, "tenSanPham": "NHA TRANG", "soNgay": 3}
    bks = [{"recID": 140001, "tourcode": "NT001.03110926", "tenNguoiBook": "KH A", "phone": "0901", "adl": 2, "chd": 0, "inf": 0, "totalDue": 7980000, "pmtStatus": "UNPAID", "fstUser": "B", "fstUpdate": "2026-09-01T10:00:00", "status": "OK", "tourID": 5001},
           {"recID": 140002, "tourcode": "NT001.03110926", "tenNguoiBook": "KH B", "phone": "0902", "adl": 1, "chd": 0, "inf": 0, "totalDue": 3990000, "pmtStatus": "UNPAID", "fstUser": "B", "fstUpdate": "2026-09-01T10:00:00", "status": "OK", "tourID": 5001}]
    client.post("/api/v1/import/vietrip/tour", json={"rows": [tour]}, headers=h); client.post("/api/v1/import/vietrip/booking", json={"rows": bks}, headers=h)
    client.post("/api/v1/import/vietrip/apply?limit=50", headers=h)
    wh = lambda pl: client.post("/api/v1/sepay/webhook", json=pl, headers={"Authorization": "Apikey k1"}).json()
    r = wh({"id": 9101, "gateway": "TPBank", "transactionDate": "2026-09-05 18:05:40", "transferType": "in", "transferAmount": 7980000, "content": "NT00103110926 KH A", "referenceCode": "FT9"})
    assert r["match_status"] == "da_khop", r
    r2 = wh({"id": 9102, "gateway": "TPBank", "transactionDate": "2026-09-05 18:06:00", "transferType": "in", "transferAmount": 1000000, "content": "QR - NT00103110926", "referenceCode": "FT10"})
    assert r2["match_status"] == "cho_ke_toan" and "không booking nào" in r2["note"]
    bk = next(b for b in client.get("/api/v1/bookings", headers=h).json() if b["code"] == "VT140001"); assert bk["paid"] == 7980000


def test_rematch_endpoint():
    r = client.post("/api/v1/bank-transactions/rematch", headers=login("ketoan")); assert r.status_code == 200 and "checked" in r.json()
