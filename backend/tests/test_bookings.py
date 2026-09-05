"""Vòng đời booking: % cọc & trạng thái thanh toán, deadline hủy chỗ, khóa/mở khóa, hủy booking có phí → bảo lưu, dùng bảo lưu cho booking mới,
đề xuất hoàn tiền bảo lưu → chi → tất toán, hủy bảo lưu ghi 711, robot R4 cảnh báo."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_bookings.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_bookings.db"): os.remove("test_bookings.db")
import pytest
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


def make_booking(name, phone, pax=2):
    t = tour("PT-DL-0912")
    r = client.post("/api/v1/requests", json={"tour_id": t["id"], "customer_name": name, "customer_phone": phone, "source": "Zalo", "care_note": "ok", "pax": pax}, headers=login("kd.hoa")); assert r.status_code == 201, r.text
    b = client.post(f"/api/v1/requests/{r.json()['request']['id']}/booking", headers=login("dh.lan")); assert b.status_code == 201, b.text
    return b.json()["booking"]


def cash(bid, amount):
    r = client.post("/api/v1/receipts/cash", json={"booking_id": bid, "amount": amount, "payer": "khách", "note": "test"}, headers=login("ketoan")); assert r.status_code == 201, r.text


def test_deposit_status_lock_unlock():
    b = make_booking("Trần Thị Hạnh", "0903619785")
    assert b["deposit_pct"] == 30 and b["pmt_status"] == "UNPAID" and b["cancel_deadline"] and b["deposit_due"] == round((b["amount"] - b["discount"]) * 0.3) and b["locked"] is False
    cash(b["id"], b["deposit_due"])
    g = client.get(f"/api/v1/bookings/{b['id']}", headers=login("kd.hoa")).json(); assert g["pmt_status"] == "DEPO" and len(g["receipts"]) == 1
    # sale phụ trách sửa được thông tin khách; người khác không
    assert client.put(f"/api/v1/bookings/{b['id']}", json={"customer_phone": "0903619786"}, headers=login("kd.hoa")).json()["customer_phone"] == "0903619786"
    assert client.put(f"/api/v1/bookings/{b['id']}", json={"customer_phone": "1"}, headers=login("hcns")).status_code == 403
    # thu đủ → robot khóa; sửa bị chặn; TP mở khóa phải có lý do
    cash(b["id"], b["amount"] - b["deposit_due"])
    chk = client.post("/api/v1/bookings/check", headers=login("tp.dieuhanh")).json(); assert chk["locked"] >= 1
    g = client.get(f"/api/v1/bookings/{b['id']}", headers=login("kd.hoa")).json(); assert g["pmt_status"] == "PAID" and g["locked"] is True
    assert client.put(f"/api/v1/bookings/{b['id']}", json={"customer_name": "X"}, headers=login("dh.lan")).json()["detail"]["gate"] == "KHOA_BOOKING"
    assert client.post(f"/api/v1/bookings/{b['id']}/unlock", json={"note": ""}, headers=login("tp.dieuhanh")).status_code == 422
    assert client.post(f"/api/v1/bookings/{b['id']}/unlock", json={"note": "Khách đổi tên trên CMND"}, headers=login("kd.hoa")).status_code == 403
    assert client.post(f"/api/v1/bookings/{b['id']}/unlock", json={"note": "Khách đổi tên trên CMND"}, headers=login("tp.dieuhanh")).status_code == 200
    assert client.put(f"/api/v1/bookings/{b['id']}", json={"customer_name": "TRẦN THỊ HẠNH PHÚC"}, headers=login("dh.lan")).json()["customer_name"] == "TRẦN THỊ HẠNH PHÚC"
    assert len(client.get("/api/v1/bookings?status=paid", headers=login("kd.hoa")).json()) >= 1


def test_cancel_with_charge_creates_retention_then_apply_refund_cancel():
    b = make_booking("Hà Hương", "0903340904")
    cash(b["id"], 3_170_000)
    # chỉ Điều hành hủy; phải có lý do
    assert client.post(f"/api/v1/bookings/{b['id']}/cancel", json={"reason": "x"}, headers=login("kd.hoa")).status_code == 403
    assert client.post(f"/api/v1/bookings/{b['id']}/cancel", json={"reason": ""}, headers=login("dh.lan")).status_code == 422
    r = client.post(f"/api/v1/bookings/{b['id']}/cancel", json={"reason": "KHÁCH BỆNH HỦY TOUR – charge 700K, còn lại bảo lưu", "charge": 700_000}, headers=login("dh.lan")); assert r.status_code == 200, r.text
    out = r.json(); assert out["charge"] == 700_000 and out["retention"] and out["retention"].startswith("BL")
    g = client.get(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan")).json(); assert g["cancelled"] and g["amount"] == 700_000 and g["pmt_status"] == "CANCEL" and g["retentions"][0]["remaining"] == 2_470_000
    # số chỗ không tính booking hủy
    t = client.get(f"/api/v1/tours/{b['tour_id']}/detail", headers=login("dh.lan")).json(); assert all(x["code"] != b["code"] or x["cancelled"] for x in t["bookings"])
    lst = client.get("/api/v1/retentions", headers=login("ketoan")).json(); assert lst["summary"]["hieu_luc"]["remaining"] >= 2_470_000
    rt = next(x for x in lst["rows"] if x["booking_code"] == b["code"])
    # dùng bảo lưu cho booking mới: 1 phần
    nb = make_booking("Hà Hương", "0903340904", pax=1)
    r = client.post(f"/api/v1/retentions/{rt['id']}/apply", json={"booking_id": nb["id"], "amount": 1_000_000}, headers=login("dh.lan")); assert r.status_code == 200, r.text
    g = client.get(f"/api/v1/bookings/{nb['id']}", headers=login("dh.lan")).json(); assert g["paid"] == 1_000_000 and g["receipts"][0]["method"] == "bao_luu"
    rt2 = client.get("/api/v1/retentions?status=hieu_luc", headers=login("ketoan")).json()["rows"]; rt2 = next(x for x in rt2 if x["id"] == rt["id"]); assert rt2["remaining"] == 1_470_000
    # không vượt số còn lại
    assert client.post(f"/api/v1/retentions/{rt['id']}/apply", json={"booking_id": nb["id"], "amount": 5_000_000}, headers=login("dh.lan")).status_code == 422
    # đề xuất hoàn phần còn lại → luồng đề nghị chi hoàn tiền → chi → tất toán
    r = client.post(f"/api/v1/retentions/{rt['id']}/refund", json={"note": "Khách xin hoàn"}, headers=login("dh.lan")); assert r.status_code == 200, r.text
    code = r.json()["request"]
    pr = next(x for x in client.get("/api/v1/payment-requests", headers=login("ketoan")).json() if x["code"] == code); assert pr["amount"] == 1_470_000 and pr["category"] == "hoan_tien"
    for a, w in (("confirm", "tp.dieuhanh"), ("check", "ketoan"), ("approve", "tgd"), ("pay", "ketoan")):
        x = client.post(f"/api/v1/payment-requests/{pr['id']}/step", json={"action": a, "reason": "CK 999" if a == "pay" else ""}, headers=login(w)); assert x.status_code == 200, x.text
    rt3 = next(x for x in client.get("/api/v1/retentions?status=all", headers=login("ketoan")).json()["rows"] if x["id"] == rt["id"]); assert rt3["status"] == "tat_toan" and rt3["remaining"] == 0
    # bảo lưu khác: hủy → ghi 711
    b2 = make_booking("Vũ Văn Nghĩa", "0918273700"); cash(b2["id"], 2_690_000)
    out = client.post(f"/api/v1/bookings/{b2['id']}/cancel", json={"reason": "KHÁCH CÓ VIỆC KHÔNG THAM GIA TOUR, BẢO LƯU", "expires_days": 5}, headers=login("dh.lan")).json()
    rtb = next(x for x in client.get("/api/v1/retentions", headers=login("ketoan")).json()["rows"] if x["code"] == out["retention"])
    assert client.post(f"/api/v1/retentions/{rtb['id']}/cancel", json={"note": ""}, headers=login("tp.dieuhanh")).status_code == 422
    assert "711" not in "" and client.post(f"/api/v1/retentions/{rtb['id']}/cancel", json={"note": "Khách không quay lại sau 90 ngày"}, headers=login("tp.dieuhanh")).status_code == 200
    es = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == f"baoluu:{rtb['code']}"]
    assert es and {(l["account"], l["debit"], l["credit"]) for l in es[0]["lines"]} == {("131", 2_690_000, 0), ("711", 0, 2_690_000)}
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True


def test_robot_alerts_deposit_and_deadline():
    b = make_booking("Khách chưa cọc", "0900000001")
    from app.db.session import SessionLocal
    from app.models.core import Booking
    from datetime import datetime, timedelta
    with SessionLocal() as db:
        x = db.get(Booking, b["id"]); x.created_at = datetime.now() - timedelta(hours=30); x.cancel_deadline = datetime.now() - timedelta(hours=1); db.commit()
    res = client.post("/api/v1/bookings/check", headers=login("ketoan")).json(); assert res["new_alerts"] >= 2
    al = client.get("/api/v1/alerts", headers=login("tp.dieuhanh")).json()
    kinds = {a["kind"] for a in al if a["ref"] == f"booking:{b['code']}"}; assert {"chua_coc", "qua_deadline_thu"} <= kinds
    g = client.get(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan")).json(); assert g["locked"] is True and g["past_deadline"] is True
    # hủy booking → cảnh báo của booking tự đóng
    assert client.post(f"/api/v1/bookings/{b['id']}/cancel", json={"reason": "Không cọc, hủy chỗ"}, headers=login("tp.dieuhanh")).status_code == 200
    assert all(a["resolved"] for a in client.get("/api/v1/alerts", headers=login("tp.dieuhanh")).json() if a["ref"] == f"booking:{b['code']}")
