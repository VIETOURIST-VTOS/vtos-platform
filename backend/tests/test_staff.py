"""Danh sách nhân viên chính thức từ bảng lương HCNS: mã NV, phòng, nhóm KD, tài khoản; trưởng nhóm KD thấy booking nhóm mình."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_staff.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_staff.db"): os.remove("test_staff.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u, pw="123456"):
    k = (u, pw)
    if k not in TOK: TOK[k] = client.post("/api/v1/auth/login", data={"username": u, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[k]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_import_master_and_group_scope():
    assert client.post("/api/v1/employees/import-master", headers=login("kd.hoa")).status_code == 403
    r = client.post("/api/v1/employees/import-master", headers=login("hcns")).json()
    assert r["created"] + r["updated"] >= 120 and r["users_created"] > 50
    d = client.get("/api/v1/staff", headers=login("kd.hoa")).json()
    rows = {x["code"]: x for x in d["rows"]}
    assert rows["114"]["full_name"] == "Nguyễn Ngọc Thạnh" and rows["114"]["sales_group"] == "KD1" and rows["114"]["department"] == "kd_le"
    assert rows["37"]["title"] == "TPKD" and rows["26"]["department"] == "dieu_hanh" and rows["290"]["department"] == "hcns"
    assert d["groups"]["KD5"] == "Nhóm KD 5"
    # tài khoản tạo mới: username không dấu, mật khẩu = mã NV; vai trò trưởng nhóm
    me = client.get("/api/v1/auth/me", headers=login("nguyenngocthanh", "114")).json()
    assert me["role"] == "tn_kd" and me["username"] == "nguyenngocthanh"
    tp = client.get("/api/v1/auth/me", headers=login("truonghaidang", "37")).json(); assert tp["role"] == "tp_kd"
    gd = client.get("/api/v1/auth/me", headers=login("lethinh", "8")).json(); assert gd["role"] == "gd_kd"
    # trưởng nhóm KD1 chỉ thấy booking của sale nhóm KD1 (chưa có → rỗng), không thấy booking của kd.hoa
    b = client.get("/api/v1/bookings?limit=500", headers=login("nguyenngocthanh", "114")).json()
    hoa_id = client.get("/api/v1/auth/me", headers=login("kd.hoa")).json()["id"]
    assert all(x["sales_id"] != hoa_id for x in b)
    # trưởng phòng KD thấy tất cả
    assert len(client.get("/api/v1/bookings?limit=500", headers=login("truonghaidang", "37")).json()) > 0
    # nạp lần 2 không tạo trùng
    r2 = client.post("/api/v1/employees/import-master", headers=login("cntt")).json()
    assert r2["created"] == 0 and r2["users_created"] == 0
