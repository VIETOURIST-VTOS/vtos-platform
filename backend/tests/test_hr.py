"""Robot R6 – nhân sự & lương: thang f, thang giảm, quỹ visa, HDV (cổng 13), tài xế, luồng bảng lương 3 bước, bút toán lương."""
# Từ 07/9/2026 bảng lương tách khỏi hồ sơ nhân sự và theo VAI TRÒ chỉ còn HCNS (cùng Chủ tịch, TGĐ,
# Ban Kiểm soát). CNTT và Kế toán không còn mở được – nên các phép thử về lương đăng nhập bằng HCNS.
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
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
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


def test_f_rate_official_table():
    T = H.parse_f_table("65:0,70:0,90:0,100:0,110:0.5,130:0.8,160:1.1,200:1.4,250:1.7,300:2,350:2.3,400:2.6,450:2.9,500:3.2,550:3.5,600:3.8,700:4.1,800:4.4,900:4.7,1000:5")
    assert len(T) == 20
    assert H.f_rate(120_000_000, 200_000_000, T) == (0, 0.0)          # < 65% → f0
    assert H.f_rate(200_000_000, 200_000_000, T) == (4, 0.0)          # 100% → f4, hệ số 0
    assert H.f_rate(650_000_000, 200_000_000, T) == (10, 0.02)        # 325% → f10 = 2,0% (ví dụ chính sách: 2% × 450tr = 9tr)
    assert round(0.02 * (650_000_000 - 200_000_000)) == 9_000_000
    assert H.f_rate(1_999_999_999, 200_000_000, T) == (19, 0.047)     # 900–<1000% → f19
    assert H.f_rate(2_000_000_000, 200_000_000, T) == (20, 0.05)      # ≥ 1000% → trần 5%
    assert H.f_rate(156_000_000, 120_000_000, T) == (6, 0.008)        # Cần Thơ mốc 120tr: 130% → f6 (B.2 = 60% cột HCM)
    class E: pass
    e = E(); e.office = "binhduong"; assert H.moc_of(e, 200e6, 120e6) == 200e6
    e.office = "hanoi"; assert H.moc_of(e, 200e6, 120e6) == 120e6
    assert H.base_salary_le(type("X", (), {"base_salary": 7_000_000})(), 150_000_000, 200_000_000, 20_000_000, 700_000) == 7_000_000 - 3 * 700_000
    assert str(H.add_working_days(date(2026, 9, 5), 3)) == "2026-09-09"   # T7 5/9 → T2 7, T3 8, T4 9 (bỏ CN)


def test_draft_from_seed():
    r = run(refresh=True)
    assert r["status"] == "nhap" and r["totals"]["so_chuyen"] >= 1
    hoa = row(r, "NS0002")                          # sale lẻ: DT Đà Lạt 73,82 triệu < 200 triệu → thang giảm
    # Từ 01/9/2026 phần chênh là KẾT QUẢ XÁC ĐỊNH MỨC LƯƠNG của kỳ, không phải khoản trừ (Điều 127.2 BLLĐ)
    assert hoa["luong_cb"] < 7_000_000 and "Phụ lục C" in hoa["ghi_chu"]
    assert hoa["xac_dinh_luong"]["che_do"] == "thang_doanh_thu" and hoa["xac_dinh_luong"]["cap"] > 0
    assert hoa["xac_dinh_luong"]["muc_ky"] == hoa["luong_cb"]
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
    tours = client.get("/api/v1/tours", headers=login("tp.dieuhanh")).json()["rows"]
    t = next(x for x in tours if x["code"] == "PT-DL-0912")
    emps = {e["code"]: e for e in client.get("/api/v1/employees", headers=login("hcns")).json()}
    bad = client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": emps["NS0012"]["id"], "days": 2, "rate_per_day": 400000}, headers=login("dh.lan"))
    assert bad.status_code == 422 and bad.json()["detail"]["gate"] == "CONG_13"
    ok = client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": emps["NS0011"]["id"], "days": 2, "rate_per_day": 400000}, headers=login("dh.lan"))
    assert ok.status_code == 201


def test_incident_workflow_and_penalty():
    emps = {e["code"]: e for e in client.get("/api/v1/employees", headers=login("hcns")).json()}
    lv = client.get("/api/v1/incident-levels", headers=login("kd.hoa")).json(); assert set(lv["levels"]) == {"1", "2", "3"} or set(lv["levels"]) == {1, 2, 3}
    # Trưởng phòng lập biên bản mức 2 → HCNS xác nhận → GĐ KD duyệt → chờ khiếu nại (chưa hiệu lực, chưa trừ)
    r = client.post("/api/v1/incidents", json={"employee_id": emps["NS0002"]["id"], "level": 2, "description": "Báo giá sai phải bù chi phí", "occurred_on": f"{P}-03"}, headers=login("tp.dieuhanh"))
    assert r.status_code == 201
    iid = client.get("/api/v1/incidents", headers=login("hcns")).json()[0]["id"]
    assert client.post(f"/api/v1/incidents/{iid}/approve", headers=login("gd.kd")).status_code == 404     # chưa HCNS xác nhận
    assert client.post(f"/api/v1/incidents/{iid}/confirm", headers=login("hcns")).status_code == 200
    assert client.post(f"/api/v1/incidents/{iid}/approve", headers=login("tp.dieuhanh")).status_code == 403   # không đúng thẩm quyền
    assert client.post(f"/api/v1/incidents/{iid}/approve", headers=login("gd.kd")).status_code == 200
    i = next(x for x in client.get("/api/v1/incidents", headers=login("hcns")).json() if x["id"] == iid); assert i["status"] == "cho_khieu_nai"
    before = row(run(refresh=True), "NS0002")
    assert not any("sự vụ" in k["ten"] for k in before["khoan"])       # đang trong hạn khiếu nại → chưa trừ
    # nhân viên khiếu nại → treo; cấp trên bác → hiệu lực → trừ 1 triệu chỉ vào hoa hồng
    me = client.post(f"/api/v1/incidents/{iid}/opinion", json={"opinion": "Tôi không đồng ý", "appeal": "Khách tự đổi ngày"}, headers=login("kd.hoa"))
    assert me.status_code == 200
    assert client.post(f"/api/v1/incidents/{iid}/opinion", json={"appeal": "x"}, headers=login("kd.tuan")).status_code == 403
    assert client.post(f"/api/v1/incidents/{iid}/resolve", json={"accept": False, "result": "Giữ nguyên"}, headers=login("gd.kd")).status_code == 200
    after = row(run(refresh=True), "NS0002")
    assert "Sự vụ ≥ mức 2: 1 vụ" in str(after["ghi_chu"]) or any("sự vụ" in k["ten"] and k["tien"] < 0 for k in after["khoan"])
    assert after["luong_cb"] > 0 and after["bien_doi"] >= 0            # chỉ trừ hoa hồng, không trừ lương cơ bản
    # mức 3 cần 2 chữ ký Chủ tịch + TGĐ; mức 1 hiệu lực ngay, không chế tài
    r3 = client.post("/api/v1/incidents", json={"employee_id": emps["NS0002"]["id"], "level": 3, "description": "Thu tiền ngoài hệ thống", "occurred_on": str(date.today())}, headers=login("hcns"))
    i3 = client.get("/api/v1/incidents", headers=login("hcns")).json()[0]["id"]
    assert client.post(f"/api/v1/incidents/{i3}/approve", headers=login("tgd")).json()["message"].startswith("Đã ký")
    assert client.post(f"/api/v1/incidents/{i3}/approve", headers=login("chutich")).status_code == 200
    assert next(x for x in client.get("/api/v1/incidents", headers=login("hcns")).json() if x["id"] == i3)["status"] == "cho_khieu_nai"
    client.post("/api/v1/incidents", json={"employee_id": emps["NS0002"]["id"], "level": 1, "description": "Thiếu báo cáo 1 ngày", "occurred_on": str(date.today())}, headers=login("hcns"))
    assert client.get("/api/v1/incidents", headers=login("hcns")).json()[0]["status"] == "hieu_luc"
    assert client.post("/api/v1/incidents", json={"employee_id": emps["NS0002"]["id"], "level": 4, "description": "x", "occurred_on": str(date.today())}, headers=login("hcns")).status_code == 422


def test_guide_rate_table_and_assignment():
    rates = client.get("/api/v1/guide-rates", headers=login("hcns")).json()
    assert len([r for r in rates if r["status"] == "active"]) == 23
    dl = next(r for r in rates if r["route"] == "Đà Lạt 3N2Đ"); assert dl["rate_per_day"] == 600000 and dl["old_rate_per_day"] == 350000 and str(dl["effective_from"]) == "2026-09-01"
    emps = client.get("/api/v1/employees", headers=login("hcns")).json()
    g = next(e for e in emps if e["department"] == "huong_dan" and e["guide_ok"])
    t = client.get("/api/v1/tours", headers=login("hcns")).json()["rows"][0]
    r = client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": g["id"], "days": 0, "rate_per_day": 0, "rate_id": dl["id"], "holiday": True}, headers=login("tp.dieuhanh"))
    assert r.status_code == 201, r.text
    a = client.get("/api/v1/guide-assignments", headers=login("hcns")).json()[0]
    assert a["rate_per_day"] == 600000 and a["days"] == 3 and a["amount"] == 600000 * 3 * 2
    assert client.post("/api/v1/guide-assignments", json={"tour_id": t["id"], "guide_id": g["id"], "days": 2, "rate_per_day": 0, "holiday": False}, headers=login("tp.dieuhanh")).status_code == 422
    # đề xuất giá mới 2 chữ ký thay giá cũ cùng tuyến
    r = client.post("/api/v1/guide-rates", json={"route": "Đà Lạt 3N2Đ", "days": 3, "rate_per_day": 650000, "old_rate_per_day": 600000, "effective_from": "2026-12-01"}, headers=login("hcns")); assert r.status_code == 201
    nid = [x for x in client.get("/api/v1/guide-rates", headers=login("hcns")).json() if x["status"] == "pending"][0]["id"]
    client.post(f"/api/v1/guide-rates/{nid}/sign", headers=login("chutich")); client.post(f"/api/v1/guide-rates/{nid}/sign", headers=login("tgd"))
    st = {x["id"]: x["status"] for x in client.get("/api/v1/guide-rates", headers=login("hcns")).json()}
    assert st[nid] == "active" and st[dl["id"]] == "rejected"


def test_payroll_flow_roles_and_journal():
    # Mức đóng BHXH là dữ liệu riêng, không suy từ lương hợp đồng – nạp trước rồi mới tính lương.
    ds = client.get("/api/v1/employees?limit=1000", headers=login("cntt")).json()
    rows = [{"ma": e["code"], "muc": 5_310_000} for e in ds if e["active"] and e["contract_type"] == "hdld"]
    assert client.post("/api/v1/bhxh/nap", json={"rows": rows, "ky": "2026-08"}, headers=login("hcns")).status_code == 200
    client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns"))
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns")).status_code == 422   # chưa qua Kế toán
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("ketoan")).json()["run"]["status"] == "kt_xac_nhan"
    assert client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns")).status_code == 422  # khóa tính lại
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns")).json()["run"]["status"] == "hcns_lap"
    res = client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("tgd")).json()
    assert res["run"]["status"] == "tgd_ky" and len(res["run"]["entry_ids"]) >= 3
    # Từ 07/9/2026 bút toán lương lập RIÊNG theo từng pháp nhân trả lương, và có thêm hai dòng khoản trừ
    # của người lao động (BHXH 3383, đoàn phí 3382), nên số chứng từ nhiều hơn ba.
    js = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"].startswith(f"payroll:{P}")]
    acc = {(l["account"]) for e in js for l in e["lines"]}
    assert {"642", "334", "632", "338", "3335"} <= acc
    assert "3383" in acc, "BHXH phần người lao động phải được ghi sổ"
    phap_nhan = {e["source_ref"].split(":")[-1] for e in js}
    assert phap_nhan, "mỗi pháp nhân một bộ chứng từ, ghi rõ ở source_ref"
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True


def test_fleet_summary():
    s = client.get("/api/v1/fleet/summary", params={"period": P}, headers=login("cntt")).json()
    assert s["total_revenue"] >= 10_500_000 and next(r for r in s["rows"] if r["vehicle"] == "50F-009.60")["driver_allowance"] == 600_000


def test_vehicle_rate_table_and_dispatch_pricing():
    rates = client.get("/api/v1/vehicle-rates", headers=login("dh.lan")).json()
    pt = next(r for r in rates if r["route"] == "Phan Thiết 2 ngày")
    assert pt["internal_price"] == 9_000_000 and pt["partner_price"] == 10_000_000 and pt["status"] == "active" and len(rates) >= 29
    veh = {v["plate"]: v for v in client.get("/api/v1/vehicles", headers=login("dh.lan")).json()}
    t = next(x for x in client.get("/api/v1/tours", headers=login("dh.lan")).json()["rows"] if x["code"] == "PT-DL-0912")
    base = {"tour_id": t["id"], "date_from": t["start_date"], "date_to": t["end_date"], "rate_id": pt["id"]}
    # Đợt 4 đội xe: xe này đã có lệnh trước đó nên tài xế của nó đang nhiều ngày công nhất, và bộ gợi ý xếp
    # nó dưới nhóm đề xuất theo tiêu chí cân bằng ngày công. Chọn phương án hệ thống đánh giá thấp hơn thì
    # phải ghi lý do – ghi vết bắt buộc của đặc tả A1, không phải rào chặn: một câu là qua.
    assert client.post("/api/v1/dispatch", json={**base, "vehicle_id": veh["50F-009.60"]["id"],
                                                 "ly_do_khac_goi_y": "Kiểm thử bảng giá – chọn đúng xe này"},
                       headers=login("dh.lan")).status_code == 201
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
