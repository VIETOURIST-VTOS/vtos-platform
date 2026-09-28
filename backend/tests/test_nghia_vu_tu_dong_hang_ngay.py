"""28/9/2026 · Sổ nghĩa vụ tự dựng hằng ngày để hai khối Phải thu · Phải trả có số.

    "em vào vtos để sửa và update lên đây hằng ngày cho anh" — anh Tuấn, 28/9/2026

Ba điều canh:
  1. Robot (ROBOT_TOKEN) gọi được cửa dựng sổ; sai hoặc thiếu token thì 401.
  2. Chủ tịch bấm tay được cửa /dong-tien/nghia-vu/dong-bo; vai kinh doanh vẫn bị chặn.
  3. robots.yml gọi cửa robot ngay trong lượt kéo Vietrip.
"""
import os, sys
from pathlib import Path
os.environ["DATABASE_URL"] = "sqlite:///./test_nv_hang_ngay.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "rt"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nv_hang_ngay.db"): os.remove("test_nv_hang_ngay.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.ROBOT_TOKEN = "rt"

client = TestClient(app); TOK = {}
CUA = "/api/v1/dong-tien/robot/nghia-vu/dong-bo"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_robot_dung_so_can_token():
    assert client.post(CUA).status_code == 401
    assert client.post(CUA, headers={"X-Robot-Token": "sai"}).status_code == 401
    r = client.post(CUA, headers={"X-Robot-Token": "rt"})
    assert r.status_code == 200, r.text
    assert "tong_dong" in r.json()


def test_chu_tich_bam_tay_duoc_kinh_doanh_thi_khong():
    assert client.post("/api/v1/dong-tien/nghia-vu/dong-bo", headers=login("chutich")).status_code == 200
    assert client.post("/api/v1/dong-tien/nghia-vu/dong-bo", headers=login("kd.hoa")).status_code == 403


def test_lich_robot_goi_dung_so_sau_luot_vietrip():
    yml = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "robots.yml").read_text(encoding="utf-8")
    khoi = yml.split("vietrip)", 1)[1].split(";;", 1)[0]
    assert "/dong-tien/robot/nghia-vu/dong-bo" in khoi
