"""CRM: nhập lead từ file Marketing (Excel), thống kê kênh × tháng, đối chiếu lead ↔ booking, báo cáo lead & chuyển đổi + Excel, Zalo (hàng chờ, webhook)."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_crm.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_crm.db"): os.remove("test_crm.db")
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
FX = os.path.join(os.path.dirname(__file__), "fixtures_lead_t8.xlsx")


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_import_marketing_file_and_conversion_report():
    h = login("ptgd.mkt") if client.post("/api/v1/auth/login", data={"username": "ptgd.mkt", "password": "123456"}).status_code == 200 else login("gd.kd")
    with open(FX, "rb") as f:
        r = client.post("/api/v1/leads/import", files={"file": ("lead_t8.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=h)
    assert r.status_code == 200, r.text
    out = r.json(); assert out["rows"] == 303 and out["new"] + out["updated"] == 303 and out["n_errors"] == 0 and out["stats"] == 21, out
    st = client.get("/api/v1/leads/stats?month=2026-08", headers=h).json(); assert sum(s["leads"] for s in st) == 2785 and any(s["channel"] == "VCHAT" and s["leads"] == 1062 for s in st)
    lst = client.get("/api/v1/leads?month=2026-08&channel=Hotline%201", headers=h).json(); assert len(lst["rows"]) == 55 and all(len(x["phone"]) == 7 for x in lst["rows"])   # file nguồn chỉ có 7 số cuối cho Hotline 1 T8
    # booking cho 1 lead T8 (khách mới) và 1 lead T6 (đã đi 1 lần trước) → đối chiếu
    t = next(x for x in client.get("/api/v1/tours", headers=login("cntt")).json()["rows"] if x["code"] == "PT-DL-0912")
    lead8 = next(x for x in client.get("/api/v1/leads?month=2026-08&channel=VCHAT", headers=h).json()["rows"] if len(x["phone"]) == 10); lead6 = next(x for x in client.get("/api/v1/leads?month=2026-06&channel=Hotline%201", headers=h).json()["rows"] if len(x["phone"]) == 10)
    for ld in (lead8, lead6):
        rq = client.post("/api/v1/requests", json={"tour_id": t["id"], "customer_name": ld["name"], "customer_phone": ld["phone"], "source": ld["channel"], "care_note": "lead", "pax": 2}, headers=login("kd.hoa")).json()["request"]
        assert client.post(f"/api/v1/requests/{rq['id']}/booking", headers=login("dh.lan")).status_code == 201
    m = client.post("/api/v1/leads/match", headers=h).json(); assert m["matched"] >= 2
    l8 = client.get(f"/api/v1/leads?month=2026-08&channel=VCHAT&q={lead8['phone']}", headers=h).json()["rows"][0]; assert l8["status"] == "chot" and l8["booking_code"]
    tm = f"{t['start_date'][:7]}"
    rep = client.get(f"/api/v1/leads/conversion?month={tm}&lead_months=2026-06,2026-07,2026-08", headers=h).json()
    m8 = next(x for x in rep["by_month"] if x["lead_month"] == "2026-08"); assert m8["leads"] == 2785 and m8["converted"] >= 1 and any(d["phone"] == lead8["phone"] and d["kind"] == "Khách mới" for d in rep["detail"])
    assert any(r["lead_month"] == "2026-06" and r["converted"] >= 1 for r in rep["by_month"])
    x = client.get(f"/api/v1/leads/conversion/xlsx?month={tm}&lead_months=2026-06,2026-07,2026-08", headers=h); assert x.status_code == 200 and len(x.content) > 5000
    # sale chỉ thấy lead của mình
    assert client.get("/api/v1/leads?month=2026-08", headers=login("kd.hoa")).json()["rows"] == []
    assert client.put(f"/api/v1/leads/{l8['id']}", json={"status": "dang_cham_soc", "note": "gọi lại 15h"}, headers=h).json()["status"] == "dang_cham_soc"


def test_zalo_queue_and_webhook():
    h = login("gd.kd")
    st = client.get("/api/v1/zalo/status", headers=h).json(); assert st["oa"] is False
    lead = client.get("/api/v1/leads?month=2026-08&channel=VCHAT", headers=h).json()["rows"][0]
    r = client.post("/api/v1/zalo/send", json={"lead_id": lead["id"], "text": "Vietourist cảm ơn anh/chị đã quan tâm tour…", "purpose": "cham_soc"}, headers=h); assert r.status_code == 201, r.text
    assert r.json()["status"] == "cho_cau_hinh" and r.json()["kind"] == "zns"
    assert client.post("/api/v1/zalo/send", json={"phone": "", "text": "x"}, headers=h).status_code == 422
    # webhook: follow → lead Zalo OA; gửi text có SĐT → gắn SĐT và uid sang lead cũ
    ev = {"event_name": "follow", "follower": {"id": "8123456789012345678"}, "timestamp": "1"}
    assert client.post("/api/v1/zalo/webhook", json=ev).json()["lead"] == "new"
    ev2 = {"event_name": "user_send_text", "sender": {"id": "8123456789012345678"}, "message": {"text": f"SĐT của tôi là {lead['phone']} nhé"}, "timestamp": "2"}
    assert client.post("/api/v1/zalo/webhook", json=ev2).status_code == 200
    l2 = client.get(f"/api/v1/leads?month=2026-08&q={lead['phone']}", headers=h).json()["rows"]; assert any(x["zalo_uid"] == "8123456789012345678" for x in l2)
    # có uid → tin kế tiếp đi OA
    r = client.post("/api/v1/zalo/send", json={"lead_id": lead["id"], "text": "Chào anh/chị", "purpose": "cham_soc"}, headers=h).json(); assert r["kind"] == "oa" and r["status"] == "cho_cau_hinh"
    msgs = client.get("/api/v1/zalo/messages", headers=h).json(); assert len(msgs) >= 2
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
