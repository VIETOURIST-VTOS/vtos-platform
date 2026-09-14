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
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
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
    # Từ 07/9/2026 việc AI có tự gửi hay không do bảng quyền AI theo vị trí quyết định. Đặt khung giờ cả
    # ngày để phép thử không phụ thuộc vào giờ chạy – nếu không, cùng một bộ mã sẽ xanh ban ngày và đỏ
    # lúc chạy đêm, và người đọc sẽ tưởng mã hỏng.
    from app.services import ai_quyen as AQ
    assert client.put("/api/v1/ai/positions", headers=login("chutich"), json={
        "vai_tro": AQ.CHU_QUAN_HOP_THU, "tac_vu": "tin_khach", "muc": 3,
        "han_muc": {"khung_gio": "00:00-23:59", "so_luot_ngay": 50,
                    "loai_noi_dung": "lịch khởi hành, giá công bố", "nguoi_hau_kiem": "ptgd_mkt"}}).status_code == 200
    # 11/9/2026: cửa thứ hai. Máy chạy phép thử KHÔNG có khoá mô hình, nên draft_reply rơi về câu
    # dựng sẵn theo quy tắc (nguồn "quy_tac"). Mức 3 cấp cho câu của mô hình có ràng buộc
    # loai_noi_dung, không cấp cho câu cứng trong mã – nên AI SOẠN NHÁP chứ không tự gửi.
    # Bản trước của phép thử này đòi ai_replied == 1, tức là đòi đúng cái hỏng: càng hỏng càng gửi.
    res = client.post("/api/v1/inbox/check", headers=login("cntt")).json()
    assert res["ai_replied"] == 0 and res["ai_soan_nhap"] == 1 and res["new_alerts"] == 1
    d = client.get(f"/api/v1/inbox/{c['id']}", headers=h).json()
    # Không có tin nào của "ai" đi ra ngoài công ty, và số lượt AI trả lời vẫn là 0. Số điện thoại
    # khách tự nhắn thì vẫn phải bắt được – phần đọc tin không đổi, chỉ phần GỬI bị chặn.
    assert d["messages"][-1]["sender"] != "ai" and d["ai_replies"] == 0 and d["phone"] == "0903123456"
    al = client.get("/api/v1/alerts", headers=login("tp.dieuhanh")).json()["rows"]; assert any(a["kind"] == "sale_tra_loi_cham" for a in al)
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


def test_standby_and_echo_when_other_app_is_primary():
    """VTOS là Người nhận phụ: tin khách đến qua entry.standby; chatbot/app khác trả lời → echo → ghi nhận đã trả lời, SLA tắt."""
    ev = {"object": "page", "entry": [{"id": "PAGE1", "standby": [{"sender": {"id": "PSID777"}, "recipient": {"id": "PAGE1"}, "message": {"mid": "s1", "text": "Tour Đà Lạt tháng 10 3n2d giá bao nhiêu?"}}]}]}
    assert client.post("/api/v1/facebook/webhook", json=ev).json()["received"] == 1
    h = login("gd.kd")
    c = next(x for x in client.get("/api/v1/inbox", headers=h).json() if x["external_id"] == "PSID777"); assert c["unanswered"]
    echo = {"object": "page", "entry": [{"id": "PAGE1", "standby": [{"sender": {"id": "PAGE1"}, "recipient": {"id": "PSID777"}, "message": {"mid": "e1", "is_echo": True, "app_id": 999, "text": "Dạ. Em chào Anh/Chị, em là Thu Tuyết…"}}]}]}
    r = client.post("/api/v1/facebook/webhook", json=echo).json(); assert r["received"] == 0 and r["echoes"] == 1
    d = client.get(f"/api/v1/inbox/{c['id']}", headers=h).json()
    assert d["unanswered"] is False and d["messages"][-1]["direction"] == "out" and "chatbot" in d["messages"][-1]["sender_name"]
    assert client.post("/api/v1/facebook/webhook", json=echo).json()["echoes"] == 0   # trùng mid


def test_fb_poll_fallback(monkeypatch):
    """Kéo hội thoại qua Graph khi webhook không tới: tin khách → hộp thư, tin Page → đã trả lời, trùng mid bỏ qua."""
    from app.services import inbox as IB
    from app.core.config import settings
    monkeypatch.setattr(settings, "FB_PAGE_ACCESS_TOKEN", "x"); monkeypatch.setattr(settings, "FB_PAGE_ID", "PAGE1")
    data = {"data": [{"updated_time": "2026-09-06T13:00:00+0000", "participants": {"data": [{"id": "PSID900", "name": "Tuấn Trần"}, {"id": "PAGE1", "name": "Vietourist"}]},
             "messages": {"data": [{"id": "mid.2", "message": "Dạ em gửi chương trình tour ạ", "from": {"id": "PAGE1"}, "created_time": "2026-09-06T12:59:00+0000"},
                                   {"id": "mid.1", "message": "test 2 - tour Đà Lạt", "from": {"id": "PSID900", "name": "Tuấn Trần"}, "created_time": "2026-09-06T12:58:00+0000"}]}}]}
    monkeypatch.setattr(IB, "_graph", lambda method, path, body=None: data)
    r = client.post("/api/v1/facebook/poll", headers=login("cntt")).json(); assert r["new_in"] == 1 and r["new_out"] == 1
    h = login("gd.kd"); c = next(x for x in client.get("/api/v1/inbox", headers=h).json() if x["external_id"] == "PSID900")
    assert c["customer_name"] == "Tuấn Trần" and c["unanswered"] is False
    # tin cũ (nạp bù) khách nhắn sau cùng → không tính SLA, AI không trả lời; tin mới (vừa xong) → tính SLA
    from datetime import datetime, timedelta
    old = (datetime.now() - timedelta(hours=5, minutes=0)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    data["data"].append({"participants": {"data": [{"id": "PSID901", "name": "Khách Cũ"}, {"id": "PAGE1"}]}, "messages": {"data": [{"id": "mid.9", "message": "hỏi tour cũ", "from": {"id": "PSID901"}, "created_time": old}]}})
    fresh = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    data["data"].append({"participants": {"data": [{"id": "PSID902", "name": "Khách Mới"}, {"id": "PAGE1"}]}, "messages": {"data": [{"id": "mid.10", "message": "hỏi tour mới", "from": {"id": "PSID902"}, "created_time": fresh}]}})
    client.post("/api/v1/facebook/poll", headers=login("cntt"))
    rows = {x["external_id"]: x for x in client.get("/api/v1/inbox", headers=h).json()}
    assert rows["PSID901"]["unanswered"] is False and rows["PSID901"]["sla_due_at"] is None
    assert rows["PSID902"]["unanswered"] is True and rows["PSID902"]["sla_due_at"]
    assert client.post("/api/v1/facebook/poll", headers=login("cntt")).json()["new_in"] == 0
