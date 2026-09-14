"""Bảng dung lượng dữ liệu: biết chỗ nào đang phình trước khi nghĩ tới nâng cấu hình máy chủ."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_dungluong.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dungluong.db"): os.remove("test_dungluong.db")
import pytest
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


def test_liet_ke_so_dong_tung_bang_va_xep_theo_do_lon():
    d = client.get("/api/v1/he-thong/dung-luong", headers=login("cntt")).json()
    assert d["so_bang"] > 30 and d["tong_so_dong"] > 0
    ten = [b["bang"] for b in d["bang"]]
    assert "tours" in ten and "bookings" in ten and "journal_lines" in ten
    # xếp giảm dần: bảng to đứng trước để nhìn là thấy chỗ cần xử lý
    khoa = [(-b["bytes"], -b["so_dong"]) for b in d["bang"]]
    assert khoa == sorted(khoa)


def test_chi_vai_tro_ky_thuat_va_lanh_dao_xem_duoc():
    assert client.get("/api/v1/he-thong/dung-luong", headers=login("hcns")).status_code == 403
    assert client.get("/api/v1/he-thong/dung-luong", headers=login("chutich")).status_code == 200
