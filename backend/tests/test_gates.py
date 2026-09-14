"""Kiểm thử các cổng chặn qua API (SQLite trong bộ nhớ, dữ liệu mẫu)."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vtos.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vtos.db"):
    os.remove("test_vtos.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


def post(u, path, json=None):
    return client.post(path, json=json, headers=login(u))


def tour_by_code(code):
    return next(t for t in client.get("/api/v1/tours", headers=login("cntt")).json()["rows"] if t["code"] == code)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def test_health_and_chain():
    r = client.get("/api/v1/health"); assert r.json()["audit_chain_ok"] is True


def test_gate5_three_numbers_required():
    t = tour_by_code("SG-CT-1020")
    r = post("dh.lan", f"/api/v1/tours/{t['id']}/submit")
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "CONG_5"


def test_gate1_2_below_margin_needs_justification_then_two_signatures():
    t = tour_by_code("SG-CT-1020")
    client.put(f"/api/v1/tours/{t['id']}", json={"price_per_pax": 1650000, "fixed_cost": 9500000, "var_cost_per_pax": 1300000,
               "planned_pax": 20, "rest_stops": "Trạm dừng Mỹ Thuận", "justification": ""}, headers=login("dh.lan"))
    r = post("dh.lan", f"/api/v1/tours/{t['id']}/submit")
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "CONG_1_2"
    client.put(f"/api/v1/tours/{t['id']}", json={"price_per_pax": 1650000, "fixed_cost": 9500000, "var_cost_per_pax": 1300000,
               "planned_pax": 20, "rest_stops": "Trạm dừng Mỹ Thuận",
               "justification": "Lý do giá xe tăng. Khoản làm mỏng biên: xe. Phương án bù: bán thêm dịch vụ. Lỗ tối đa 2 triệu."}, headers=login("dh.lan"))
    assert post("dh.lan", f"/api/v1/tours/{t['id']}/submit").status_code == 200
    assert post("tgd", f"/api/v1/tours/{t['id']}/approve").status_code == 422          # chưa TP xác nhận
    assert post("tp.dieuhanh", f"/api/v1/tours/{t['id']}/confirm").status_code == 200
    assert post("ptgd.doan", f"/api/v1/tours/{t['id']}/approve").json()["detail"]["gate"] == "CONG_1"
    assert "Chờ chữ ký" in post("tgd", f"/api/v1/tours/{t['id']}/approve").json()["message"]
    assert "Đủ 2 chữ ký" in post("chutich", f"/api/v1/tours/{t['id']}/approve").json()["message"]
    assert tour_by_code("SG-CT-1020")["below_margin"] is True


def test_gate4_required_fields_and_gate3_promo():
    t = tour_by_code("PT-DL-0912")
    r = post("kd.hoa", "/api/v1/requests", {"tour_id": t["id"], "customer_name": "A", "customer_phone": "", "source": "Zalo", "care_note": "x", "pax": 2})
    assert r.json()["detail"]["gate"] == "CONG_4"
    r = post("kd.hoa", "/api/v1/requests", {"tour_id": t["id"], "customer_name": "KM lớn", "customer_phone": "0909", "source": "Zalo", "care_note": "vip", "pax": 2, "discount": 25000000, "promo_code": "KM90"})
    rid = r.json()["request"]["id"]
    assert post("kd.hoa", f"/api/v1/requests/{rid}/booking").json()["detail"]["gate"] == "CONG_12"
    assert post("dh.lan", f"/api/v1/requests/{rid}/booking").json()["detail"]["gate"] == "CONG_3"


def test_gate12_booking_sla_flag():
    r = next(x for x in client.get("/api/v1/requests?open_only=1", headers=login("dh.lan")).json() if x["customer_name"] == "Võ Thị D")
    res = post("dh.lan", f"/api/v1/requests/{r['id']}/booking").json()
    assert res["booking"]["sla_ok"] is False and "QUÁ 2 GIỜ" in res["message"]


def test_gate8_d7_only_chairman_can_run():
    t = tour_by_code("PT-DL-0912")
    assert post("tp.dieuhanh", f"/api/v1/tours/{t['id']}/d7", {"decision": "chay"}).json()["detail"]["gate"] == "CONG_8"
    assert post("chutich", f"/api/v1/tours/{t['id']}/d7", {"decision": "chay"}).status_code == 200


def test_gate6_settlement_one_door_and_flow():
    t = tour_by_code("DN-HCM-0820")
    assert post("dh.minh", f"/api/v1/tours/{t['id']}/close", {"actual_revenue": 189000000, "actual_cost": 158000000}).json()["detail"]["gate"] == "CONG_6"
    assert "QUÁ HẠN" in post("dh.lan", f"/api/v1/tours/{t['id']}/close", {"actual_revenue": 189000000, "actual_cost": 158000000}).json()["message"]
    assert post("cntt", f"/api/v1/tours/{t['id']}/kt-confirm").status_code == 403
    assert post("ketoan", f"/api/v1/tours/{t['id']}/kt-confirm").status_code == 200
    assert post("cntt", f"/api/v1/tours/{t['id']}/cntt-check").status_code == 200
    v = client.get(f"/api/v1/tours/{t['id']}", headers=login("cntt")).json()
    assert v["status"] == "khoa" and v["settlement"]["eligible"] is False   # quá hạn → không quỹ


def test_params_two_signatures():
    r = post("tp.dieuhanh", "/api/v1/params", {"key": "han_qt_le", "value": "4", "effective_from": "2026-10-01"})
    pid = r.json()["param"]["id"]
    assert post("ketoan", f"/api/v1/params/{pid}/sign").status_code == 403
    assert "chờ" in post("tgd", f"/api/v1/params/{pid}/sign").json()["message"]
    assert "hiệu lực" in post("chutich", f"/api/v1/params/{pid}/sign").json()["message"]


def test_audit_chain_intact_and_robot_api():
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
    assert client.post("/api/v1/robot/run", headers={"X-Robot-Token": "wrong"}).status_code == 401
    assert client.post("/api/v1/robot/run", headers={"X-Robot-Token": "doi-robot-token"}).status_code == 200
    assert client.get("/api/v1/payroll", headers=login("hcns")).status_code == 200


def test_chu_tich_toan_quyen_moi_phan_he():
    """Chủ tịch HĐQT có toàn quyền (quyết định 06/9/2026) – nhưng các chốt an toàn khác KHÔNG nới theo:
    kỳ đã khóa vẫn không ghi được, và vai trò khác vẫn bị chặn như cũ."""
    ct = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"})
    assert ct.status_code == 200, ct.text
    h = {"Authorization": f"Bearer {ct.json()['access_token']}"}

    # Thao tác vốn chỉ dành cho kế toán: lập và ghi sổ chứng từ
    r = client.post("/api/v1/journal", headers=h, json={
        "entry_date": "2029-04-05", "description": "Chu tich lap chung tu", "post": True,
        "lines": [{"account": "1111", "debit": 1_000_000}, {"account": "1121", "credit": 1_000_000}]})
    assert r.status_code == 201, r.text
    # Thao tác vốn chỉ dành cho HCNS
    assert client.get("/api/v1/hrm/profile-gaps", headers=h).status_code == 200

    # Kỳ đã khóa thì Chủ tịch cũng không ghi được – toàn quyền không phá chốt an toàn kế toán
    assert client.post("/api/v1/periods/2029-05/lock", headers=h, json={"note": "test"}).status_code == 200
    r2 = client.post("/api/v1/journal", headers=h, json={
        "entry_date": "2029-05-05", "description": "Ghi vao ky da khoa", "post": True,
        "lines": [{"account": "1111", "debit": 1_000}, {"account": "1121", "credit": 1_000}]})
    assert r2.status_code == 422 and "khóa" in str(r2.json()["detail"])

    # Vai trò khác vẫn bị chặn như cũ
    kd = client.post("/api/v1/auth/login", data={"username": "kd.hoa", "password": "Vtos@Demo#2026"})
    if kd.status_code == 200:
        hk = {"Authorization": f"Bearer {kd.json()['access_token']}"}
        assert client.get("/api/v1/hrm/profile-gaps", headers=hk).status_code == 403
