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

    # xem trước: phải nói rõ sẽ khóa những tài khoản nào, và KHÔNG được thay đổi gì
    xt = client.post("/api/v1/employees/import-master?dry_run=true", headers=login("hcns")).json()
    assert xt["xem_truoc"] is True and xt["created"] + xt["updated"] >= 110
    assert any("kd.hoa" in x for x in xt["users_closed"]), "tài khoản không có trong bảng lương phải nằm trong danh sách sẽ khóa"
    assert client.post("/api/v1/auth/login", data={"username": "kd.hoa", "password": "123456"}).status_code == 200, "xem trước không được đổi gì"

    # đặt lại mật khẩu lẻ vẫn chạy trước khi nạp
    hoa_id = client.get("/api/v1/auth/me", headers=login("kd.hoa")).json()["id"]
    assert client.post(f"/api/v1/users/{hoa_id}/reset-password", json={"new_password": "abc123"}, headers=login("hcns")).status_code == 200
    assert client.post("/api/v1/auth/login", data={"username": "kd.hoa", "password": "abc123"}).status_code == 200

    r = client.post("/api/v1/employees/import-master", headers=login("hcns")).json()
    assert r["created"] + r["updated"] >= 110 and r["users_created"] > 40
    # tài khoản hcns demo cũng không có trong bảng lương nên đã bị khóa – từ đây dùng HCNS thật
    assert client.get("/api/v1/staff", headers=login("hcns")).status_code == 401
    hcns = lambda: login("phanngocduy", "290")
    d = client.get("/api/v1/staff", headers=hcns()).json()
    rows = {x["code"]: x for x in d["rows"]}
    assert rows["114"]["full_name"] == "Nguyễn Ngọc Thạnh" and rows["114"]["sales_group"] == "KD1" and rows["114"]["department"] == "kd_le"
    assert rows["37"]["title"] == "TPKD" and rows["26"]["department"] == "dieu_hanh" and rows["290"]["department"] == "hcns"
    assert d["groups"]["KD5"] == "Nhóm KD 5"

    # chỉ đạo 07/9/2026: ba trường hợp chuyển phòng
    assert rows["285"]["department"] == "hcns", "Trần Thị Thùy Trang về HCNS"
    assert rows["267"]["department"] == "marketing", "CSKH về Marketing"
    assert rows["303"]["department"] == "marketing", "Bùi Phúc Bửu Lâm về Marketing"

    # tài xế đứng tên lái xe và HDV được cấp tài khoản, vai trò xe_hdv
    tx = client.get("/api/v1/auth/me", headers=login("tranvinh", "297")).json()
    assert tx["role"] == "xe_hdv"
    assert client.get("/api/v1/tours", headers=login("tranvinh", "297")).status_code == 403

    # tài khoản tạo mới: username không dấu, mật khẩu = mã NV; vai trò trưởng nhóm
    me = client.get("/api/v1/auth/me", headers=login("nguyenngocthanh", "114")).json()
    assert me["role"] == "tn_kd" and me["username"] == "nguyenngocthanh"
    tp = client.get("/api/v1/auth/me", headers=login("truonghaidang", "37")).json(); assert tp["role"] == "tp_kd"
    gd = client.get("/api/v1/auth/me", headers=login("lethinh", "8")).json(); assert gd["role"] == "gd_kd"

    # bảng lương là danh sách người đang làm việc: ai không có trong đó thì không đăng nhập được nữa
    assert any("kd.hoa" in x for x in r["users_closed"])
    assert client.post("/api/v1/auth/login", data={"username": "kd.hoa", "password": "abc123"}).status_code == 401
    # nhưng tài khoản hệ thống thì không bị khóa theo bảng lương
    for tk in ("chutich", "tgd", "cntt"):
        assert client.post("/api/v1/auth/login", data={"username": tk, "password": "123456"}).status_code == 200

    # trưởng nhóm KD1 chỉ thấy booking của sale nhóm KD1, không thấy booking của người khác
    b = client.get("/api/v1/bookings?limit=500", headers=login("nguyenngocthanh", "114")).json()
    assert all(x["sales_id"] != hoa_id for x in b)
    assert len(client.get("/api/v1/bookings?limit=500", headers=login("truonghaidang", "37")).json()) > 0

    r3 = client.post("/api/v1/employees/import-master?reset_passwords=true", headers=hcns()).json(); assert r3["passwords_reset"] > 40
    # nạp lần 2 không tạo trùng, không khóa thêm ai
    r2 = client.post("/api/v1/employees/import-master", headers=login("cntt")).json()
    assert r2["created"] == 0 and r2["users_created"] == 0 and r2["users_closed"] == []
