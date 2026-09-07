"""Nạp nhật trình chuyến và sửa phân loại đề xuất chi từ báo cáo quyết toán xe tháng 8/2026.

Nạp dữ liệu là lúc dễ làm hỏng sổ nhất, nên bộ test này nhắm vào bốn cách hỏng:

  1. Nạp lại cùng một báo cáo lần thứ hai làm doanh thu và chi phí nhân đôi – mỗi dòng vẫn trông đúng.
  2. Biển số gõ sai mà hệ thống tự tạo xe mới: từ đó số liệu của một chiếc chia làm hai chỗ.
  3. Chuyến thiếu ngày bị bỏ im lặng, doanh thu biến mất khỏi báo cáo mà không ai biết.
  4. Xếp "nạp thẻ dầu 150 triệu" thành chi phí nhiên liệu, trong khi tiền dầu thật đã nằm ở phiếu
     chi phí từng chuyến – cộng đúp tiền dầu của cả tháng.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_nap_bc.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nap_bc.db"): os.remove("test_nap_bc.db")
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


def _phieu(ma, bien="50F-009.60", dt=13_000_000, dau=5_555_352):
    return {"ma_phieu": ma, "bien_so": bien, "ten_tour": "Đà Lạt (lẻ)",
            "ngay_di": "2026-08-05", "ngay_ve": "2026-08-07", "km_dau": 100_000, "km_cuoi": 100_647,
            "doanh_thu": dt,
            "chi_phi": {"dau": dau, "lit": 187, "cau_duong": 624_000, "cong_tac_phi": 600_000}}


def test_nap_chuyen_tao_du_dong_chi_phi_va_gan_dung_xe(_startup):
    h = login("ketoan")
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "rows": [_phieu("BC-T8-001")]})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["da_nhap"] == 1 and d["xe_khong_tra_ra"] == []
    tid = d["chi_tiet"][0]["trip_id"]
    ct = next(x for x in client.get("/api/v1/fleet/chuyen", headers=h).json() if x["id"] == tid)
    assert ct["doanh_thu"] == 13_000_000
    # Nhiên liệu, cầu đường, công tác phí đều do Vietourist tạm ứng (chốt 07/9/2026)
    assert ct["tong_chi_vietourist"] == 5_555_352 + 624_000 + 600_000
    assert ct["tong_chi_chu_xe"] == 0


def test_nap_lai_lan_hai_khong_nhan_doi_doanh_thu(_startup):
    """Lỗi tốn kém nhất của mọi lần nạp dữ liệu: doanh thu và chi phí nhân đôi mà mỗi dòng vẫn trông đúng."""
    h = login("ketoan")
    truoc = len(client.get("/api/v1/fleet/chuyen", headers=h).json())
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "rows": [_phieu("BC-T8-001")]})
    assert r.status_code == 201
    assert r.json()["da_nhap"] == 0 and r.json()["bo_qua_da_co"] == 1
    assert len(client.get("/api/v1/fleet/chuyen", headers=h).json()) == truoc


def test_bien_so_la_thi_bao_ra_chu_khong_tu_tao_xe(_startup):
    """Một biển gõ sai mà hệ thống tự tạo xe thì từ đó có hai chiếc cùng tồn tại và số liệu chia đôi."""
    h = login("ketoan")
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "rows": [_phieu("BC-T8-LA", bien="99Z-999.99")]})
    assert r.status_code == 201
    assert r.json()["da_nhap"] == 0
    assert r.json()["xe_khong_tra_ra"] == [{"bien_so": "99Z-999.99", "so_phieu": 1}]
    assert r.json()["da_tao_xe"] == []


def test_chi_tao_xe_khi_nguoi_nap_noi_ro(_startup):
    h = login("ketoan")
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "tao_xe_thieu": True,
                          "rows": [_phieu("BC-T8-MOI", bien="50F 042.59")]})
    assert r.status_code == 201, r.text
    assert r.json()["da_nhap"] == 1 and r.json()["da_tao_xe"] == ["50F 042.59"]


def test_bien_so_ghi_khac_dinh_dang_van_ve_dung_xe_da_co(_startup):
    """Xe vừa tạo ở trên ghi "50F 042.59"; báo cáo sau ghi "50F-042.59" – phải về đúng chiếc đó, không tạo
    thêm chiếc thứ hai."""
    h = login("ketoan")
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "tao_xe_thieu": True,
                          "rows": [_phieu("BC-T8-MOI-2", bien="50F-042.59")]})
    assert r.status_code == 201, r.text
    assert r.json()["da_nhap"] == 1 and r.json()["da_tao_xe"] == []


def test_thieu_ngay_thi_tu_choi_chu_khong_doan(_startup):
    """Bỏ im lặng là mất doanh thu khỏi báo cáo mà không ai biết; tự đoán ngày là gán chuyến vào nhầm kỳ
    quyết toán. Cả hai đều tệ hơn việc báo lỗi ra cho người nạp."""
    h = login("ketoan")
    p = _phieu("BC-T8-THIEU"); p["ngay_di"] = None
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                    json={"nguon": "bao_cao_vietrip", "rows": [p]})
    assert r.status_code == 422 and "không tự đoán ngày" in r.json()["detail"]


def test_thieu_ma_phieu_thi_tu_choi(_startup):
    h = login("ketoan")
    p = _phieu(""); r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h,
                                    json={"nguon": "bao_cao_vietrip", "rows": [p]})
    assert r.status_code == 422 and "chống được nạp trùng" in r.json()["detail"]


# ---------------------------------------------------------------- Sửa phân loại
def test_sua_phan_loai_nap_quy_thi_khong_con_tinh_la_chi_phi(_startup):
    """"Nạp thẻ dầu 150 triệu" nhìn như chi phí nhiên liệu, nhưng tiền dầu thật đã nằm ở phiếu chi phí của
    từng chuyến. Xếp nhầm là cộng đúp tiền dầu của cả tháng."""
    h = login("ketoan")
    client.post("/api/v1/fleet/giao-dich/nhap", headers=h,
                json={"source": "de_xuat_vietrip",
                      "rows": [{"ma_gd": "DX-QUY-1", "thoi_diem": "2026-08-03T00:00:00",
                                "so_tien": 150_000_000, "nhom": "Nhiên liệu & phí đường",
                                "mo_ta": "Nạp thẻ dầu"}]})
    truoc = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    assert truoc["tong_chi_phi"] >= 150_000_000

    r = client.post("/api/v1/fleet/giao-dich/phan-loai", headers=h,
                    json={"source": "de_xuat_vietrip",
                          "items": [{"ma_gd": "DX-QUY-1", "nhom": "Nạp quỹ / tạm ứng",
                                     "khong_phai_chi_phi": True}]})
    assert r.status_code == 200 and r.json()["da_sua"] == 1
    sau = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    assert sau["tong_chi_phi"] == truoc["tong_chi_phi"] - 150_000_000
    assert sau["tong_dieu_chuyen"] == truoc["tong_dieu_chuyen"] + 150_000_000
    dong = next(t for t in sau["rows"] if t["ma_gd"] == "DX-QUY-1")
    assert dong["co"] != "do", "khoản nạp quỹ vốn không thuộc xe nào – không gắn cờ đỏ vì thiếu xe"


def test_phan_loai_khong_sua_duoc_so_tien(_startup):
    """Phân loại là việc của người đọc chứng từ; số liệu gốc phải sửa ở nguồn rồi nạp lại, để hai bên còn
    đối chiếu được với nhau."""
    h = login("ketoan")
    client.post("/api/v1/fleet/giao-dich/phan-loai", headers=h,
                json={"source": "de_xuat_vietrip",
                      "items": [{"ma_gd": "DX-QUY-1", "so_tien": 1, "nhom": "Nạp quỹ / tạm ứng"}]})
    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    assert next(t for t in d["rows"] if t["ma_gd"] == "DX-QUY-1")["so_tien"] == 150_000_000


def test_ma_khong_co_thi_bao_ra_chu_khong_im_lang(_startup):
    r = client.post("/api/v1/fleet/giao-dich/phan-loai", headers=login("ketoan"),
                    json={"source": "de_xuat_vietrip", "items": [{"ma_gd": "KHONG-CO", "nhom": "X"}]})
    assert r.status_code == 200 and r.json()["khong_tim_thay"] == ["KHONG-CO"]
