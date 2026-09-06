"""Sửa hồ sơ nhân sự: chỉ ghi đè trường được gửi, và ngưng hồ sơ trùng (Ý kiến thẩm định 06/9/2026).

Nạp danh sách tài xế tháng 9/2026 sinh ra hai hồ sơ cùng tên "Trần Vinh" (mã 296 và 297). HCNS phải
ngưng được hồ sơ thừa ngay trên màn hình, nhưng không được ngưng người đang đứng tên lái một xe còn
khai thác – nếu không, lệnh điều xe sẽ trỏ vào hồ sơ đã nghỉ.

Trước đây PUT /employees/{id} ghi đè toàn bộ EmployeeIn: màn hình cũ gửi thiếu trường mới (ngày sinh,
điện thoại, chức danh) là xóa trắng dữ liệu vừa nạp. Nay dùng exclude_unset.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ho_so_nhan_su.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ho_so_nhan_su.db"): os.remove("test_ho_so_nhan_su.db")
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


def tao(ten="Trần Vinh kiểm thử"):
    r = client.post("/api/v1/employees", json={"full_name": ten, "department": "doi_xe", "position": "tai_xe",
                                               "base_salary": 9_000_000, "phone": "0901234567", "birth_date": "1985-04-12",
                                               "title": "Tài xế Vietrip"}, headers=login("hcns"))
    assert r.status_code == 201, r.text
    return r.json()["employee"]


def test_tao_ho_so_nhan_ngay_sinh_dien_thoai_chuc_danh():
    e = tao()
    assert e["phone"] == "0901234567" and e["birth_date"] == "1985-04-12" and e["title"] == "Tài xế Vietrip"


def test_sua_ho_so_khong_xoa_truong_khong_gui():
    """Màn hình cũ chỉ gửi họ tên + phòng; ngày sinh, điện thoại, lương phải còn nguyên."""
    e = tao("Trần Vinh kiểm thử 2")
    r = client.put(f"/api/v1/employees/{e['id']}", json={"full_name": "Trần Vinh kiểm thử 2", "department": "doi_xe"}, headers=login("hcns"))
    assert r.status_code == 200, r.text
    sau = r.json()["employee"]
    assert sau["phone"] == "0901234567" and sau["birth_date"] == "1985-04-12"
    assert sau["base_salary"] == 9_000_000 and sau["title"] == "Tài xế Vietrip"
    assert sau["active"] is True


def test_ngung_ho_so_trung_va_mo_lai():
    e = tao("Trần Vinh kiểm thử 3")
    r = client.put(f"/api/v1/employees/{e['id']}", json={"full_name": e["full_name"], "department": "doi_xe", "active": False}, headers=login("hcns"))
    assert r.status_code == 200, r.text
    assert r.json()["employee"]["active"] is False
    assert "Ngưng làm việc" in r.json()["message"]
    ds = client.get("/api/v1/employees", headers=login("hcns")).json()
    assert any(x["id"] == e["id"] and x["active"] is False for x in ds), "ngưng chứ không xóa – vẫn tra cứu được"
    r = client.put(f"/api/v1/employees/{e['id']}", json={"full_name": e["full_name"], "department": "doi_xe", "active": True}, headers=login("hcns"))
    assert r.json()["employee"]["active"] is True


def test_khong_ngung_duoc_tai_xe_dang_dung_ten_xe():
    e = tao("Trần Vinh kiểm thử 4")
    xe = client.get("/api/v1/vehicles", headers=login("hcns")).json()
    x = next(v for v in xe if v["active"])
    assert client.put(f"/api/v1/vehicles/{x['id']}", json={"driver_id": e["id"]}, headers=login("hcns")).status_code == 200
    r = client.put(f"/api/v1/employees/{e['id']}", json={"full_name": e["full_name"], "department": "doi_xe", "active": False}, headers=login("hcns"))
    assert r.status_code == 422, r.text
    assert x["plate"] in r.json()["detail"]
    client.put(f"/api/v1/vehicles/{x['id']}", json={"driver_id": None}, headers=login("hcns"))
    assert client.put(f"/api/v1/employees/{e['id']}", json={"full_name": e["full_name"], "department": "doi_xe", "active": False}, headers=login("hcns")).status_code == 200
