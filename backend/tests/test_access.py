"""Rà phân quyền tuần 3: ma trận nhìn thấy dữ liệu theo vai trò, Ban Kiểm soát chỉ đọc, NV kinh doanh chỉ thấy phần mình phụ trách, robot token."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_access.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_access.db"): os.remove("test_access.db")
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


def _tour_id():
    return client.get("/api/v1/tours?limit=1", headers=login("tgd")).json()["rows"][0]["id"]


def test_read_matrix_cost_finance_audit():
    tid = _tour_id()
    # Kinh doanh / HCNS: không xem chi phí NCC, quyết toán, dòng tiền tour, ngân hàng, nhật ký kiểm toán
    for who in ("kd.hoa", "gd.kd", "hcns"):
        h = login(who)
        for path in (f"/api/v1/tours/{tid}/settlement", f"/api/v1/tours/{tid}/cost-lines", f"/api/v1/tours/{tid}/cashflow", "/api/v1/bank-transactions", "/api/v1/audit"):
            assert client.get(path, headers=h).status_code == 403, (who, path)
        v = client.get(f"/api/v1/tours/{tid}", headers=h).json()
        assert v["fixed_cost"] is None and v["calc"] is None and v["settlement"] is None and "audit" not in v and v["price_per_pax"]   # giá bán vẫn thấy
    # Điều hành xem chi phí nhưng không xem ngân hàng / nhật ký
    h = login("dh.lan")
    assert client.get(f"/api/v1/tours/{tid}/settlement", headers=h).status_code == 200
    assert client.get("/api/v1/bank-transactions", headers=h).status_code == 403 and client.get("/api/v1/audit", headers=h).status_code == 403
    # Chủ tịch, TGĐ, Kế toán, Ban Kiểm soát: xem cả giao dịch ngân hàng
    for who in ("chutich", "tgd", "ketoan", "bks"):
        h = login(who)
        for path in (f"/api/v1/tours/{tid}/settlement", "/api/v1/bank-transactions", "/api/v1/audit", "/api/v1/params"):
            assert client.get(path, headers=h).status_code == 200, (who, path)
    # CNTT (chỉ đạo 07/9/2026): vẫn đối chiếu được quyết toán, nhật ký và tham số, nhưng KHÔNG còn xem
    # giao dịch ngân hàng – vận hành hệ thống không cần nhìn sổ tiền gửi của công ty.
    h = login("cntt")
    for path in (f"/api/v1/tours/{tid}/settlement", "/api/v1/audit", "/api/v1/params"):
        assert client.get(path, headers=h).status_code == 200, ("cntt", path)
    assert client.get("/api/v1/bank-transactions", headers=h).status_code == 403
    # HCNS không xem booking; vẫn xem tham số
    assert client.get("/api/v1/bookings", headers=login("hcns")).status_code == 403
    assert client.get("/api/v1/params", headers=login("hcns")).status_code == 200


def test_sales_sees_only_own():
    hoa, tuan = login("kd.hoa"), login("kd.tuan")
    me = client.get("/api/v1/auth/me", headers=hoa).json()["id"]
    rows = client.get("/api/v1/bookings?limit=500", headers=hoa).json()
    assert rows and all(r["sales_id"] == me for r in rows)
    all_rows = client.get("/api/v1/bookings?limit=500", headers=login("gd.kd")).json()
    assert len(all_rows) > len(rows)   # GĐ KD thấy toàn bộ
    other = next(r for r in all_rows if r["sales_id"] != me)
    assert client.get(f"/api/v1/bookings/{other['id']}", headers=hoa).status_code == 403
    assert client.get(f"/api/v1/bookings/{rows[0]['id']}", headers=hoa).status_code == 200
    # phiếu thu, yêu cầu, bảo lưu, dịch vụ lẻ cũng chỉ của mình
    for path in ("/api/v1/receipts", "/api/v1/requests", "/api/v1/retentions?status=all"):
        assert client.get(path, headers=hoa).status_code == 200
    # cảnh báo: sale chỉ thấy cảnh báo gửi tới vai trò nv_kd
    for a in client.get("/api/v1/alerts", headers=hoa).json()["rows"]: assert "nv_kd" in a["to_roles"].split(",")


def test_bks_read_only_and_robot_token():
    h = login("bks")
    tid = _tour_id()
    assert client.get(f"/api/v1/tours/{tid}", headers=h).status_code == 200
    for m, path in (("post", "/api/v1/tours"), ("post", f"/api/v1/tours/{tid}/approve"), ("post", "/api/v1/daily-reports"), ("put", f"/api/v1/tours/{tid}"), ("post", "/api/v1/params")):
        r = getattr(client, m)(path, json={}, headers=h); assert r.status_code == 403 and "chỉ có quyền đọc" in r.text, (m, path, r.text)
    assert client.post("/api/v1/auth/password", json={"old_password": "123456", "new_password": "123456"}, headers=h).status_code in (200, 422)
    # robot: token rỗng trên máy chủ → mọi lời gọi robot bị chặn, kể cả header rỗng
    assert client.post("/api/v1/robot/run", headers={"X-Robot-Token": ""}).status_code == 401
    assert client.post("/api/v1/robot/run").status_code == 401
    assert client.post("/api/v1/robot/vietrip/sync", json={}, headers={"X-Robot-Token": ""}).status_code == 401
