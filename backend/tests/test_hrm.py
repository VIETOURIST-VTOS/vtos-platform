"""Phân hệ Nhân sự kiểu MISA: hồ sơ, hợp đồng lao động, người phụ thuộc, đơn từ – phép năm, bảng chấm công."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_hrm.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hrm.db"): os.remove("test_hrm.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def an_employee(h):
    return client.get("/api/v1/employees", headers=h).json()[0]


def test_ho_so_va_hop_dong():
    h = login("hcns")
    e = an_employee(h)
    eid = e["id"]

    # Hồ sơ trống → liệt kê đúng trường còn thiếu
    r = client.get(f"/api/v1/employees/{eid}/profile", headers=h).json()
    assert r["profile"] is None and r["completeness"]["percent"] == 0
    assert "id_number" in r["completeness"]["missing"]

    up = client.put(f"/api/v1/employees/{eid}/profile", headers=h, json={
        "dob": "1990-05-12", "gender": "nam", "id_number": "079090001234", "permanent_address": "12 Lê Lợi, Q.1, TP.HCM",
        "phone": "0903000111", "tax_code": "8123456789", "bank_account": "01811267101", "bank_name": "TPBank"})
    assert up.status_code == 200, up.text
    r2 = client.get(f"/api/v1/employees/{eid}/profile", headers=h).json()
    assert r2["completeness"]["percent"] == 100 and r2["completeness"]["missing"] == []

    # Hợp đồng lao động: ký, xem hợp đồng đang hiệu lực, số HĐ không trùng
    c = client.post("/api/v1/labor-contracts", headers=h, json={
        "employee_id": eid, "code": "HDLD-2026-001", "kind": "xac_dinh_12", "signed_on": "2026-01-02",
        "effective_from": "2026-01-05", "effective_to": "2027-01-04", "salary": 15_000_000, "si_salary": 10_000_000})
    assert c.status_code == 201, c.text
    assert c.json()["bhxh"] is True and c.json()["status"] == "hieu_luc"
    dup = client.post("/api/v1/labor-contracts", headers=h, json={
        "employee_id": eid, "code": "HDLD-2026-001", "effective_from": "2026-02-01"})
    assert dup.status_code == 422 and "đã tồn tại" in dup.json()["detail"]

    r3 = client.get(f"/api/v1/employees/{eid}/profile", headers=h).json()
    assert r3["contract"]["code"] == "HDLD-2026-001"

    # Cảnh báo hợp đồng: nhân sự chưa có hợp đồng phải hiện ra
    al = client.get("/api/v1/labor-contracts/alerts?within_days=45", headers=h).json()
    assert al["counts"]["no_contract"] >= 1
    assert eid not in [x["employee_id"] for x in al["no_contract"]]

    # Chấm dứt hợp đồng
    cid = c.json()["id"]
    t = client.post(f"/api/v1/labor-contracts/{cid}/terminate", headers=h, json={"on": "2026-06-30", "reason": "Nghỉ việc"})
    assert t.status_code == 200 and t.json()["status"] == "cham_dut"


def test_nguoi_phu_thuoc_va_giam_tru():
    h = login("hcns")
    eid = an_employee(h)["id"]
    base = client.get(f"/api/v1/employees/{eid}/pit-deduction?period=2026-09", headers=h).json()
    assert base["dependents"] == 0 and base["total"] == base["self"]

    d = client.post("/api/v1/dependents", headers=h, json={
        "employee_id": eid, "full_name": "Nguyễn Minh Anh", "relation": "con", "dob": "2018-03-01",
        "from_period": "2026-01"})
    assert d.status_code == 201, d.text
    after = client.get(f"/api/v1/employees/{eid}/pit-deduction?period=2026-09", headers=h).json()
    assert after["dependents"] == 1
    assert after["total"] == after["self"] + after["dependent_rate"]

    # Người phụ thuộc đăng ký từ 2026-01 thì kỳ 2025-12 chưa được giảm trừ
    before = client.get(f"/api/v1/employees/{eid}/pit-deduction?period=2025-12", headers=h).json()
    assert before["dependents"] == 0

    rm = client.delete(f"/api/v1/dependents/{d.json()['id']}", headers=h)
    assert rm.status_code == 200
    assert client.get(f"/api/v1/employees/{eid}/pit-deduction?period=2026-09", headers=h).json()["dependents"] == 0


def test_phep_nam_va_don_tu():
    h = login("hcns")
    emps = client.get("/api/v1/employees", headers=h).json()
    e = emps[1] if len(emps) > 1 else emps[0]
    eid = e["id"]
    client.post("/api/v1/labor-contracts", headers=h, json={
        "employee_id": eid, "code": "HDLD-2026-PN1", "kind": "khong_xac_dinh",
        "effective_from": "2020-01-01", "salary": 12_000_000, "annual_leave_days": 12})

    bal = [x for x in client.get("/api/v1/leave-balance?year=2026", headers=h).json() if x["employee_id"] == eid][0]
    assert bal["entitlement"] >= 12 and bal["used"] == 0

    # Gửi đơn 3 ngày phép rồi duyệt → trừ đúng quỹ phép và ghi vào bảng chấm công
    r = client.post("/api/v1/leaves", headers=h, json={
        "employee_id": eid, "kind": "phep_nam", "date_from": "2026-09-07", "date_to": "2026-09-09", "reason": "Việc gia đình"})
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    assert r.json()["days"] == 3 and r.json()["status"] == "cho_duyet"

    pend = [x for x in client.get("/api/v1/leave-balance?year=2026", headers=h).json() if x["employee_id"] == eid][0]
    assert pend["pending"] == 3 and pend["used"] == 0

    ok = client.post(f"/api/v1/leaves/{lid}/decide", headers=h, json={"approve": True, "note": "Đồng ý"})
    assert ok.status_code == 200 and ok.json()["status"] == "duyet"
    after = [x for x in client.get("/api/v1/leave-balance?year=2026", headers=h).json() if x["employee_id"] == eid][0]
    assert after["used"] == 3 and after["remaining"] == after["entitlement"] - 3

    sheet = client.get("/api/v1/attendance?period=2026-09", headers=h).json()
    row = [x for x in sheet["rows"] if x["employee_id"] == eid][0]
    marked = [c for c in row["cells"] if c["day"] in (7, 8, 9)]
    assert all(c["kind"] == "phep_nam" and c["work"] == 0 for c in marked), marked
    assert row["leave_days"] == 3

    # Xin vượt quỹ phép phải bị chặn ngay khi gửi đơn
    over = client.post("/api/v1/leaves", headers=h, json={
        "employee_id": eid, "kind": "phep_nam", "date_from": "2026-10-01", "date_to": "2026-11-30"})
    assert over.status_code == 422 and "quỹ phép" in over.json()["detail"]

    # Nghỉ không lương không trừ phép năm
    ul = client.post("/api/v1/leaves", headers=h, json={
        "employee_id": eid, "kind": "khong_luong", "date_from": "2026-09-14", "date_to": "2026-09-14"})
    assert ul.status_code == 201
    client.post(f"/api/v1/leaves/{ul.json()['id']}/decide", headers=h, json={"approve": True})
    b2 = [x for x in client.get("/api/v1/leave-balance?year=2026", headers=h).json() if x["employee_id"] == eid][0]
    assert b2["used"] == 3


def test_bang_cham_cong_sua_tay():
    h = login("hcns")
    eid = an_employee(h)["id"]
    sheet = client.get("/api/v1/attendance?period=2026-09", headers=h).json()
    assert sheet["standard_days"] == 22                       # tháng 9/2026 có 22 ngày làm việc (T2–T6)
    row = [x for x in sheet["rows"] if x["employee_id"] == eid][0]
    assert row["work_days"] == 22

    # Chấm công cuối tuần đi trực + nửa ngày nghỉ
    assert client.post("/api/v1/attendance", headers=h, json={
        "employee_id": eid, "day": "2026-09-05", "kind": "lam_viec", "work": 1, "ot_hours": 4, "note": "Trực page"}).status_code == 200
    assert client.post("/api/v1/attendance", headers=h, json={
        "employee_id": eid, "day": "2026-09-10", "kind": "khong_luong", "work": 0.5}).status_code == 200

    s2 = client.get("/api/v1/attendance?period=2026-09", headers=h).json()
    r2 = [x for x in s2["rows"] if x["employee_id"] == eid][0]
    assert r2["work_days"] == 22 + 1 - 0.5
    assert r2["ot_hours"] == 4 and r2["unpaid_days"] == 1

    bad = client.post("/api/v1/attendance", headers=h, json={"employee_id": eid, "day": "2026-09-11", "kind": "sai_loai"})
    assert bad.status_code == 422
