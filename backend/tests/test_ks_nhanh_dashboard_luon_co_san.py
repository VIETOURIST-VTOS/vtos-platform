"""KS-NHANH (07/11/2026) — bảng điều hành crm không bao giờ bắt người mở trang chờ dựng lại.

Đo trên crm thật: dựng lại từ đầu 38 giây, lấy bản nhớ 0,3 giây. Trước đây bản nhớ quá 5 phút là
bỏ, và robot nền chỉ dựng lại khi CÓ ai ghi → lúc vắng, hoặc ngay sau mỗi lần cập nhật máy chủ,
Chủ tịch mở trang là chờ nửa phút. Ba điều phép thử này canh:
  1. bản nhớ cũ vẫn được trả NGAY (kèm tuổi), và bị đánh dấu cũ để robot dựng lại;
  2. robot dựng lại cả khi không ai ghi, nếu bản nhớ đã quá 4 phút;
  3. bản nhớ trống (vừa khởi động) → robot dựng sẵn cho Chủ tịch, không thêm vai trò khác;
và bước 2: mỗi lần dựng ghi số mili-giây từng khối vào `do_ms` để tìm khối chậm.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ks_nhanh.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks_nhanh.db"): os.remove("test_ks_nhanh.db")
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


def test_ban_nho_cu_van_tra_ngay_va_danh_dau_cu():
    from app.api.v1 import routes as R_
    h = login("ketoan")
    client.get("/api/v1/dashboard", headers=h)
    k = ("ketoan", 0)
    R_._DASH_CACHE[k] = (R_._DASH_CACHE[k][0] - 3600, R_._DASH_CACHE[k][1])   # cũ 1 giờ
    R_._DASH_DIRTY = False
    d = client.get("/api/v1/dashboard", headers=h).json()
    assert d.get("cached") is True, "bản nhớ cũ vẫn phải trả ngay, không bắt người mở trang chờ"
    assert d.get("tuoi_giay", 0) >= 3600
    assert R_._DASH_DIRTY is True, "bản cũ phải được đánh dấu để robot dựng lại"


def test_robot_dung_lai_khi_ban_nho_qua_4_phut_du_khong_ai_ghi():
    from app.api.v1 import routes as R_
    client.get("/api/v1/dashboard?refresh=1", headers=login("ketoan"))
    R_._DASH_DIRTY = False
    for k in list(R_._DASH_CACHE): R_._DASH_CACHE[k] = (__import__("time").time(), R_._DASH_CACHE[k][1])
    assert R_.can_dung_lai() is False
    k = next(iter(R_._DASH_CACHE))
    R_._DASH_CACHE[k] = (R_._DASH_CACHE[k][0] - 300, R_._DASH_CACHE[k][1])
    assert R_.can_dung_lai() is True


def test_vua_khoi_dong_thi_dung_san_cho_chu_tich():
    from app.api.v1 import routes as R_
    from app.db.session import SessionLocal
    R_._DASH_CACHE.clear()
    assert R_.can_dung_lai() is True
    db = SessionLocal(); n = R_.lam_moi_cache_nen(db); db.close()
    assert n == 1 and set(R_._DASH_CACHE) == {("chutich", 0)}
    d = client.get("/api/v1/dashboard", headers=login("chutich")).json()
    assert d.get("cached") is True, "Chủ tịch mở trang đầu tiên sau khởi động không phải chờ"


def test_moi_lan_dung_ghi_thoi_gian_tung_khoi():
    d = client.get("/api/v1/dashboard?refresh=1", headers=login("chutich")).json()
    do = d.get("do_ms") or {}
    for khoi in ("tong", "viec_cho_toi", "khoi_tong_hop", "kpi_thang", "phai_thu_tra", "tien_do_bao_cao"):
        assert khoi in do and isinstance(do[khoi], int), khoi
