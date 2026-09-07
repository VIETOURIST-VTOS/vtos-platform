"""Nạp bộ đề xuất chi trên phần mềm Vietrip vào VTOS để đối chiếu (tháng 8/2026).

Ba điều bộ test này giữ, cả ba đều là chuyện con số báo cáo ra ngoài:

  1. Điều chuyển tiền nội bộ KHÔNG được cộng vào chi phí. Trong 36 khoản tháng 8/2026 có 3 khoản
     (127.360.494 đ) chỉ là chuyển tiền giữa các tài khoản của chính công ty.
  2. Nhập lại cùng một bộ dữ liệu hai lần không được nhân đôi số liệu.
  3. Khoản không quy được về xe nào phải được ĐẾM RIÊNG chứ không im lặng bỏ qua – đó là 660 triệu
     tiền dầu và ePass nộp theo tài khoản chung, và nó là lý do phần mềm chưa tính được giá thành từng xe.
"""
import os, sys, json
os.environ["DATABASE_URL"] = "sqlite:///./test_dexuat_vtrip.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dexuat_vtrip.db"): os.remove("test_dexuat_vtrip.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
BO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "de_xuat_chi_vietrip_2026_08.json")


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


@pytest.fixture(scope="module")
def bo_du_lieu():
    with open(BO, encoding="utf-8") as f:
        return json.load(f)


def test_bo_du_lieu_thang_8_du_36_khoan(bo_du_lieu):
    """Chốt số liệu đã trích ngày 07/9/2026 để lần nạp sau còn so được."""
    rows = bo_du_lieu["rows"]
    assert len(rows) == 36
    assert sum(r["so_tien"] for r in rows) == 1_249_185_988
    assert sum(r["so_tien"] for r in rows if r["khong_phai_chi_phi"]) == 127_360_494


def test_nap_vao_thi_tong_chi_phi_khong_gom_dieu_chuyen_tien(bo_du_lieu):
    """127.360.494 đ điều chuyển nội bộ mà cộng vào chi phí thì báo cáo tháng 8 sai đúng khoản đó."""
    h = login("ketoan")
    r = client.post("/api/v1/fleet/giao-dich/nhap", headers=h,
                    json={"source": "de_xuat_vietrip", "rows": bo_du_lieu["rows"]})
    assert r.status_code == 201, r.text
    assert r.json()["da_nhap"] == 36

    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    assert d["tong_dieu_chuyen"] == 127_360_494
    assert d["tong_chi_phi"] == 1_249_185_988 - 127_360_494
    assert "cộng chung" in d["ghi_chu"]


def test_nap_lai_lan_hai_khong_nhan_doi_so_lieu(bo_du_lieu):
    """Người dùng nạp lại file là chuyện thường; nhân đôi số liệu thì không."""
    h = login("ketoan")
    truoc = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()["tong_chi_phi"]
    r = client.post("/api/v1/fleet/giao-dich/nhap", headers=h,
                    json={"source": "de_xuat_vietrip", "rows": bo_du_lieu["rows"]})
    assert r.status_code == 201 and r.json()["da_nhap"] == 0 and r.json()["ban_ghi_lap"] == 36
    sau = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()["tong_chi_phi"]
    assert sau == truoc


def test_khoan_chua_quy_ve_xe_duoc_dem_rieng_chu_khong_im_lang(bo_du_lieu):
    """660 triệu tiền dầu và ePass nộp theo tài khoản chung nên không gắn được vào xe nào. Im lặng bỏ qua
    thì người đọc tưởng chi phí đội xe chỉ là mấy chục triệu sửa chữa."""
    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=login("ketoan")).json()
    assert d["tong_chua_quy_ve_xe"] > 600_000_000
    nhien_lieu = next(n for n in d["theo_nhom"] if n["nhom"] == "Nhiên liệu & phí đường")
    assert nhien_lieu["so_tien"] == 660_000_000 and nhien_lieu["so_khoan"] == 11


def test_dong_dieu_chuyen_khong_bi_gan_co_do_vi_thieu_xe(bo_du_lieu):
    """Cờ đỏ để dành cho khoản đáng lẽ phải có xe mà chưa tra ra. Một khoản chuyển tiền nội bộ vốn dĩ không
    thuộc xe nào – gắn cờ đỏ cho nó là dạy người dùng bỏ qua cờ đỏ."""
    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=login("ketoan")).json()
    for t in d["rows"]:
        if t["khong_phai_chi_phi"]:
            assert t["co"] != "do"
            assert "không phải chi phí" in t["ghi_chu"]


def test_nguon_khong_hop_le_thi_bao_ro(_startup):
    r = client.post("/api/v1/fleet/giao-dich/nhap", headers=login("ketoan"),
                    json={"source": "linh_tinh", "rows": [{"ma_gd": "x", "thoi_diem": "2026-08-01T00:00:00"}]})
    assert r.status_code == 422 and "de_xuat_vietrip" in r.json()["detail"]
