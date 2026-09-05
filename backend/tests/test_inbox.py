"""Hộp thư đa kênh: webhook Facebook (verify + tin khách), hội thoại/lead tự tạo, SLA, sale trả lời (+AI chấm), AI trả lời thay khi trễ (quy tắc khi chưa có khóa), tắt AI."""
import os, sys, json
os.environ["DATABASE_URL"] = "sqlite:///./test_inbox.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["FB_VERIFY_TOKEN"] = "vtos-test"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_inbox.db"): os.remove("test_inbox.db")
import pytest
from datetime import datetime, timedelta
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


def test_facebook_webhook_and_ai_fallback():
    r = client.get("/api/v1/facebook/webhook?hub.mode=subscribe&hub.verify_token=vtos-test&hub.challenge=12345"); assert r.status_code == 200 and r.text == "12345"
    assert client.get("/api/v1/facebook/webhook?hub.mode=subscribe&hub.verify_token=sai&hub.challenge=1").status_code == 403
    ev = {"object": "page", "entry": [{"id": "PAGE1", "messaging": [{"sender": {"id": "PSID001"}, "recipient": {"id": "PAGE1"}, "message": {"mid": "m1", "text": "Cho em hỏi tour Phan Thiết cuối tuần còn chỗ không?"}}]}]}
    assert client.post("/api/v1/facebook/webhook", json=ev).json()["received"] == 1
    assert client.post("/api/v1/facebook/webhook", json=ev).json()["received"] == 0   # trùng mid → bỏ qua
    h = login("gd.kd")
    lst = client.get("/api/v1/inbox", headers=h).json(); c = next(x for x in lst if x["external_id"] == "PSID001")
    assert c["channel"] == "facebook" and c["unanswered"] and c["sla_due_at"] and c["lead_id"]
    st = client.get("/api/v1/inbox/status", headers=h).json(); assert st["overdue"] >= 1 and st["ai"] is False
    # sale trả lời → AI chấm (quy tắc) cờ giảm giá
    r = client.post(f"/api/v1/inbox/{c['id']}/reply", json={"text": "Dạ còn chỗ, em giảm giá thêm 500k cho anh nhé"}, headers=login("kd.hoa")).json()
    assert r["msg"]["sender"] == "sale" and r["msg"]["status"] == "loi" and any("giảm giá" in f for f in r["msg"]["ai_review"]["flags"])   # chưa có token FB → gửi lỗi nhưng ghi nhận
    d = client.get(f"/api/v1/inbox/{c['id']}", headers=h).json(); assert len(d["messages"]) == 2 and d["unanswered"] is False and d["sales_name"]
    # khách nhắn tiếp, sale không trả lời → robot: quá SLA → AI trả lời thay
    ev2 = {"object": "page", "entry": [{"id": "PAGE1", "messaging": [{"sender": {"id": "PSID001"}, "recipient": {"id": "PAGE1"}, "message": {"mid": "m2", "text": "Giá bao nhiêu 1 người? SĐT em 0903123456"}}]}]}
    client.post("/api/v1/facebook/webhook", json=ev2)
    assert client.post("/api/v1/inbox/check", headers=login("cntt")).json()["ai_replied"] == 0   # chưa quá hạn
    from app.db.session import SessionLocal
    from app.models.crm import Conversation
    with SessionLocal() as db:
        x = db.get(Conversation, c["id"]); x.sla_due_at = datetime.now() - timedelta(minutes=1); db.commit()
    res = client.post("/api/v1/inbox/check", headers=login("cntt")).json(); assert res["ai_replied"] == 1 and res["new_alerts"] == 1
    d = client.get(f"/api/v1/inbox/{c['id']}", headers=h).json()
    assert d["messages"][-1]["sender"] == "ai" and "Vietourist" in d["messages"][-1]["text"] and d["ai_replies"] == 1 and d["phone"] == "0903123456" and d["status"] == "ai_da_tra_loi"
    al = client.get("/api/v1/alerts", headers=login("tp.dieuhanh")).json(); assert any(a["kind"] == "sale_tra_loi_cham" for a in al)
    # AI gợi ý trả lời cho sale
    dr = client.post(f"/api/v1/inbox/{c['id']}/ai-draft", headers=login("kd.hoa")).json(); assert dr["source"] == "quy_tac" and dr["text"]
    # tắt AI cho hội thoại → quá hạn chỉ cảnh báo, không trả lời
    client.post(f"/api/v1/inbox/{c['id']}/assign", json={"ai_off": True}, headers=h)
    ev3 = {"object": "page", "entry": [{"id": "PAGE1", "messaging": [{"sender": {"id": "PSID001"}, "recipient": {"id": "PAGE1"}, "message": {"mid": "m3", "text": "Alo?"}}]}]}
    client.post("/api/v1/facebook/webhook", json=ev3)
    with SessionLocal() as db:
        x = db.get(Conversation, c["id"]); x.sla_due_at = datetime.now() - timedelta(minutes=1); db.commit()
    assert client.post("/api/v1/inbox/check", headers=login("cntt")).json()["ai_replied"] == 0
    # lead tạo từ inbox có SĐT khách chia sẻ
    ld = client.get("/api/v1/leads?q=0903123456", headers=h).json()["rows"]; assert ld and ld[0]["channel"] == "Facebook"
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True


def test_simulate_web_and_zalo_route():
    h = login("cntt")
    r = client.post("/api/v1/inbox/simulate", json={"channel": "web", "external_id": "web-abc", "name": "Khách web", "text": "Tour Đà Lạt 3 ngày giá sao?"}, headers=h); assert r.status_code == 201
    z = {"event_name": "user_send_text", "sender": {"id": "9000000000000000001"}, "message": {"text": "Tư vấn tour Nha Trang", "msg_id": "z1"}, "timestamp": "1"}
    assert client.post("/api/v1/zalo/webhook", json=z).status_code == 200
    lst = client.get("/api/v1/inbox?channel=zalo", headers=h).json(); assert any(x["external_id"] == "9000000000000000001" for x in lst)
