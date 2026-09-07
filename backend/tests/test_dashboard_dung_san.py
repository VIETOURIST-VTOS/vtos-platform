"""Bảng điều khiển được dựng sẵn ở nền – người mở trang không trả giá cho lần dựng đầu.

Trước đây MỌI thao tác ghi (POST/PUT/DELETE) đều xoá trắng cache. Trên hệ thống thật, nhân viên
tạo booking, ghi phiếu thu, gửi đề nghị chi suốt cả ngày, nên cache gần như luôn trống và gần như
ai mở trang chủ cũng phải chờ dựng lại từ đầu (4 giây trên dữ liệu thật, trước khi tối ưu là sập
máy chủ). Đó chính là "lúc nào cũng chậm".

Nay: thao tác ghi chỉ ĐÁNH DẤU CŨ, robot nền dựng lại, người dùng luôn nhận bản có sẵn.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_dash_warm.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dash_warm.db"): os.remove("test_dash_warm.db")
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


def test_ghi_du_lieu_khong_xoa_trang_cache_ma_chi_danh_dau_cu():
    from app.api.v1 import routes as R_
    kt = login("ketoan")
    assert client.get("/api/v1/dashboard", headers=kt).status_code == 200
    assert client.get("/api/v1/dashboard", headers=kt).json().get("cached") is True
    so_khoa = len(R_._DASH_CACHE)
    assert so_khoa >= 1
    # một thao tác ghi bất kỳ
    client.post("/api/v1/params", json={"key": "nguong_bien", "value": "0.1", "effective_from": "2026-09-01"}, headers=kt)
    assert len(R_._DASH_CACHE) == so_khoa, "thao tác ghi KHÔNG được xoá trắng cache"
    assert R_._DASH_DIRTY is True, "thao tác ghi phải đánh dấu bảng điều khiển đã cũ"
    # người mở trang ngay sau đó vẫn nhận bản có sẵn, không phải chờ dựng lại
    assert client.get("/api/v1/dashboard", headers=kt).json().get("cached") is True


def test_robot_nen_dung_lai_dung_nhung_vai_tro_dang_co_nguoi_dung():
    from app.api.v1 import routes as R_
    from app.db.session import SessionLocal
    client.get("/api/v1/dashboard", headers=login("chutich"))
    khoa_truoc = set(R_._DASH_CACHE.keys())
    assert ("chutich", 0) in khoa_truoc and ("ketoan", 0) in khoa_truoc
    for k in list(R_._DASH_CACHE): R_._DASH_CACHE[k] = (0.0, R_._DASH_CACHE[k][1])   # làm cho cũ
    db = SessionLocal(); n = R_.lam_moi_cache_nen(db); db.close()
    assert n == len(khoa_truoc)
    assert set(R_._DASH_CACHE.keys()) == khoa_truoc, "không tự dựng thêm vai trò chưa ai dùng"
    assert client.get("/api/v1/dashboard", headers=login("chutich")).json().get("cached") is True


def test_refresh_van_dung_lai_that_khi_nguoi_dung_yeu_cau():
    d = client.get("/api/v1/dashboard?refresh=1", headers=login("ketoan")).json()
    assert d.get("cached") is not True
