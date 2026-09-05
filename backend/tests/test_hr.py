"""Robot R6 – nhân sự & lương: thang f, thang giảm, quỹ visa, HDV (cổng 13), tài xế, luồng bảng lương 3 bước, bút toán lương."""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_hr.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hr.db"):
    os.remove("test_hr.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import hr as H

client = TestClient(app)
TOK = {}
P = f"{date.today() - timedelta(days=14):%Y-%m}"   # tháng Kế toán xác nhận tour Đà Lạt mẫu


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def run(refresh=False):
    return client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": refresh}, headers=login("hcns")).json()


def row(r, code):
    return next(x for x in r["rows"] if x["ma"] == code)


def test_f_rate_and_salary_scale_units():
    assert H.f_rate(150_000_000, 200_000_000) == (0, 0.0)          # dưới mốc: không hoa hồng
    assert H.f_rate(200_000_000, 200_000_000)[1] == 0.0             # f0
    assert H.f_rate(650_000_000, 200_000_000) == (5, 0.005)         # 325% mốc → f5
    assert H.f_rate(2_000_000_000, 200_000_000) == (20, 0.05)       # ≥ 1000% → trần 5%
    class E: base_salary = 7_000_000
    assert H.base_salary_le(E(), 200_000_000, 200_000_000, 20_000_000, 700_000) == 7_000_000
    assert H.base_salary_le(E(), 150_000_000, 200_000_000, 20_000_000, 700_000) == 7_000_000 - 3 * 700_000
    assert H.base_salary_le(E(), 0, 200_000_000, 20_000_000, 700_000) == 0


def test_draft_from_seed():
    r = run(refresh=True)
    assert r["status"] == "nhap" and r["totals"]["so_chuyen"] >= 1
    hoa = row(r, "NS0002")                          # sale lẻ: DT Đà Lạt 73,82 triệu < 200 triệu → thang giảm
    assert hoa["luong_cb"] < 7_000_000 and "Thang giảm" in hoa["ghi_chu"]
    lan = row(r, "NS0006")                          # điều hành: thưởng chuyến 70%
    assert any("70%" in k["ten"] for k in lan["khoan"])
    hdv = row(r, "NS0011")                          # HDV CTV: 3 ngày × 450k, TNCN 10%
    assert hdv["bien_doi"] == 1_350_000 and hdv["tncn"] == 135_000 and hdv["thuc_nhan"] == 1_215_000 and hdv["luong_cb"] == 0
    tx = row(r, "NS0013")                           # tài xế: 3 ngày × 200k
    assert any(k["tien"] == 600_000 for k in tx["khoan"])
    vy, nam, lananh = row(r, "NS0008"), row(r, "NS0009"), row(r, "NS0010")
    # HCM: 200k + 50k + (200k+300k) = 750k chia đều 2 người; Hà Nội riêng 200k
    assert vy["bien_doi"] == nam["bien_doi"] == 375_000 and lananh["bien_doi"] == 200_000


def test_gate13_guide_conditions_and_pending_hold():
    tours = client.get("/api/v1/tours", headers=login("tp.dieuhanh")).json()
    t = next(x for x in tours if x["code"] == "PT-DL-0912")
    emps = {e["code"]: e for e in client.get("/api/v1/employees", headers=login("hcns")).json()}
    bad = client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": emps["NS0012"]["id"], "days": 2, "rate_per_day": 400000}, headers=login("dh.lan"))
    assert bad.status_code == 422 and bad.json()["detail"]["gate"] == "CONG_13"
    ok = client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": emps["NS0011"]["id"], "days": 2, "rate_per_day": 400000}, headers=login("dh.lan"))
    assert ok.status_code == 201


def test_incident_penalty_only_hits_commission():
    emps = {e["code"]: e for e in client.get("/api/v1/employees", headers=login("hcns")).json()}
    client.post("/api/v1/incidents", json={"employee_id": emps["NS0002"]["id"], "level": 2, "description": "Khách khiếu nại", "occurred_on": str(date.today())}, headers=login("hcns"))
    r = run(refresh=True)
    hoa = row(r, "NS0002")
    assert hoa["bien_doi"] >= 0 and hoa["luong_cb"] > 0      # không trừ lương cơ bản (Điều 127.2 BLLĐ)


def test_payroll_flow_roles_and_journal():
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns")).status_code == 422   # chưa qua Kế toán
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("ketoan")).json()["run"]["status"] == "kt_xac_nhan"
    assert client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns")).status_code == 422  # khóa tính lại
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns")).json()["run"]["status"] == "hcns_lap"
    res = client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("tgd")).json()
    assert res["run"]["status"] == "tgd_ky" and len(res["run"]["entry_ids"]) == 3
    js = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == f"payroll:{P}"]
    acc = {(l["account"]) for e in js for l in e["lines"]}
    assert {"642", "334", "632", "338", "3335"} <= acc
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True


def test_fleet_summary():
    s = client.get("/api/v1/fleet/summary", params={"period": P}, headers=login("cntt")).json()
    assert s["total_revenue"] >= 10_500_000 and next(r for r in s["rows"] if r["vehicle"] == "50F-009.60")["driver_allowance"] == 600_000


def test_vehicle_rate_table_and_dispatch_pricing():
    rates = client.get("/api/v1/vehicle-rates", headers=login("dh.lan")).json()
    pt = next(r for r in rates if r["route"] == "Phan Thiết 2 ngày")
    assert pt["internal_price"] == 9_000_000 and pt["partner_price"] == 10_000_000 and pt["status"] == "active" and len(rates) >= 29
    veh = {v["plate"]: v for v in client.get("/api/v1/vehicles", headers=login("dh.lan")).json()}
    t = next(x for x in client.get("/api/v1/tours", headers=login("dh.lan")).json() if x["code"] == "PT-DL-0912")
    base = {"tour_id": t["id"], "date_from": t["start_date"], "date_to": t["end_date"], "rate_id": pt["id"]}
    assert client.post("/api/v1/dispatch", json={**base, "vehicle_id": veh["50F-009.60"]["id"]}, headers=login("dh.lan")).status_code == 201
    assert client.post("/api/v1/dispatch", json={**base, "vehicle_id": veh["50E-955.31"]["id"]}, headers=login("dh.lan")).status_code == 201
    ds = {d["vehicle"]: d for d in client.get("/api/v1/dispatch", headers=login("dh.lan")).json() if d["tour_code"] == "PT-DL-0912"}
    assert ds["50F-009.60"]["internal_price"] == 9_000_000 and ds["50E-955.31"]["internal_price"] == 10_000_000 and ds["50F-009.60"]["route"] == "Phan Thiết 2 ngày"
    # đề xuất giá mới cần 2 chữ ký
    r = client.post("/api/v1/vehicle-rates", json={"route": "Phan Thiết 2 ngày", "days": 2, "internal_price": 9_500_000, "partner_price": 10_500_000, "effective_from": "2026-10-01"}, headers=login("cntt"))
    assert r.status_code == 201
    new = [x for x in client.get("/api/v1/vehicle-rates", headers=login("cntt")).json() if x["status"] == "pending"][0]
    assert client.post("/api/v1/dispatch", json={**base, "vehicle_id": veh["50F-009.60"]["id"], "rate_id": new["id"]}, headers=login("dh.lan")).status_code == 422
    client.post(f"/api/v1/vehicle-rates/{new['id']}/sign", headers=login("tgd"))
    assert "hiệu lực" in client.post(f"/api/v1/vehicle-rates/{new['id']}/sign", headers=login("chutich")).json()["message"]
