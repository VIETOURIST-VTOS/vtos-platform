"""Lãi lỗ đội xe: ba tầng chi phí, và khoảng cách giữa chúng.

Bảng quyết toán xe tháng 6/2026 của công ty là bài học gốc của bộ test này: cộng lãi gộp 21 chiếc được
938 triệu, nhưng sau bảo hiểm, lương tài xế, phí bãi và 327 triệu lãi vay thì đội xe còn 227 triệu.
Ai chỉ nhìn tầng đầu tưởng đội xe lãi gấp hơn bốn lần thực tế.

Sáu cách một báo cáo lãi lỗ nói dối, và bộ test này chặn cả sáu:

  1. Chỉ trừ chi phí chuyến rồi gọi đó là lợi nhuận đội xe.
  2. Chia lãi vay về từng xe rồi để người đọc tưởng đó là kết quả thật của chiếc xe.
  3. Nhập lại bảng tháng lần thứ hai làm chi phí nhân đôi.
  4. Gắn phí bãi xe vào một chiếc, hoặc để lương tài xế trôi vào khối chi phí chung.
  5. Tính công suất trên số xe CÓ CHẠY, nên chiếc nằm bãi cả tháng biến mất và công suất luôn đẹp.
  6. Trả 0 cho suất tiêu hao khi thiếu số lít – đọc ra là "xe không tốn dầu".
"""
import os, sys, tempfile
# CSDL thử để trong thư mục tạm của máy, không để trong thư mục làm việc: thư mục làm việc là thư mục
# được đồng bộ, và ở đó xoá tệp có thể bị từ chối – bộ test không được phụ thuộc vào quyền xoá.
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_lailo.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; KY = "2026-06"


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        h = login("ketoan")
        # Hai chuyến thật của cùng một xe trong kỳ, để có tầng 1 mà tính.
        for i, (ma, dt, dau, lit) in enumerate([("LL-01", 20_000_000, 8_000_000, 900),
                                                ("LL-02", 14_000_000, 5_000_000, 600)]):
            r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h, json={
                "nguon": "nhap_tay", "rows": [{
                    "ma_phieu": ma, "bien_so": "50F-009.60", "ten_tour": f"Tuyến thử {i+1}",
                    "ngay_di": f"2026-06-0{2*i+1}", "ngay_ve": f"2026-06-0{2*i+3}",
                    "km_dau": 100000 + i * 3000, "km_cuoi": 103000 + i * 3000,
                    "doanh_thu": dt,
                    "chi_phi": {"dau": dau, "lit": lit, "cau_duong": 1_000_000,
                                "cong_tac_phi": 600_000}}]})
            assert r.status_code == 201, r.text
        yield


def bc(phan_bo="khong", who="ketoan"):
    r = client.get(f"/api/v1/fleet/lai-lo?ky={KY}&phan_bo={phan_bo}", headers=login(who))
    assert r.status_code == 200, r.text
    return r.json()


def them(nhom, so_tien, vehicle_id=None, mo_ta="", who="ketoan"):
    return client.post("/api/v1/fleet/chi-phi-ky", headers=login(who),
                       json={"ky": KY, "nhom": nhom, "so_tien": so_tien,
                             "vehicle_id": vehicle_id, "mo_ta": mo_ta})


def _xe_id():
    d = client.get("/api/v1/fleet/xe", headers=login("ketoan")).json()
    rows = d["rows"] if isinstance(d, dict) else d
    return next(x["id"] for x in rows if "009.60" in (x.get("plate") or x.get("bien_so") or ""))


# ---------------------------------------------------------------- Tầng 1
def test_tang_mot_la_lai_gop_chuyen_chua_phai_loi_nhuan(_startup):
    d = bc()
    t = d["tong"]
    assert t["doanh_thu"] == 34_000_000
    assert t["chi_phi_chuyen"] == 8_000_000 + 5_000_000 + 2_000_000 + 1_200_000
    assert t["lai_gop_chuyen"] == t["doanh_thu"] - t["chi_phi_chuyen"]
    # Chưa nhập chi phí kỳ nào thì lợi nhuận ĐANG bằng lãi gộp – và báo cáo phải nói ra là thiếu.
    assert t["loi_nhuan"] == t["lai_gop_chuyen"]
    assert d["nhom_chi_phi_doi_chua_nhap"], "kỳ chưa có chi phí đội nào thì phải liệt kê ra"


def test_theo_tour_moi_chuyen_mot_dong_va_suat_tieu_hao(_startup):
    ds = client.get(f"/api/v1/fleet/lai-lo/theo-chuyen?ky={KY}", headers=login("ketoan")).json()
    d = next(x for x in ds if x["ma_phieu"] == "LL-01")
    assert d["doanh_thu"] == 20_000_000 and d["chi_phi_chuyen"] == 9_600_000
    assert d["lai_gop"] == 10_400_000 and d["km"] == 3000
    assert d["km_moi_lit"] == round(3000 / 900, 2)
    assert d["dau_moi_km"] == round(8_000_000 / 3000)


def test_thieu_so_lit_thi_de_trong_chu_khong_tra_0(_startup):
    """0 km/lít đọc ra là 'xe không tốn dầu' – tệ hơn hẳn một ô để trống."""
    h = login("ketoan")
    r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h, json={
        "nguon": "nhap_tay", "rows": [{"ma_phieu": "LL-03", "bien_so": "50F-009.60",
                                       "ten_tour": "Không ghi lít", "ngay_di": "2026-06-20",
                                       "ngay_ve": "2026-06-21", "doanh_thu": 5_000_000,
                                       "chi_phi": {"dau": 1_000_000}}]})
    assert r.status_code == 201, r.text
    ds = client.get(f"/api/v1/fleet/lai-lo/theo-chuyen?ky={KY}", headers=h).json()
    d = next(x for x in ds if x["ma_phieu"] == "LL-03")
    assert d["km_moi_lit"] is None and d["km"] is None


# ---------------------------------------------------------------- Tầng 2 & 3
def test_chi_phi_cua_xe_tru_thang_vao_ket_qua_chiec_do(_startup):
    xid = _xe_id()
    assert them("bao_hiem", 3_000_000, xid, "Bảo hiểm tháng 6").status_code == 201
    assert them("luong_tai_xe", 6_442_450, xid).status_code == 201
    d = bc()
    xe = next(x for x in d["xe"] if x["vehicle_id"] == xid)
    assert xe["chi_phi_xe"] == 9_442_450
    assert xe["ket_qua_xe"] == xe["lai_gop_chuyen"] - 9_442_450
    assert d["tong"]["ket_qua_sau_chi_phi_xe"] == d["tong"]["lai_gop_chuyen"] - 9_442_450


def test_chi_phi_doi_khong_tru_vao_xe_nao_nhung_tru_vao_loi_nhuan(_startup):
    assert them("lai_vay", 20_000_000).status_code == 201
    assert them("bai_xe", 4_000_000).status_code == 201
    d = bc()
    t = d["tong"]
    assert t["chi_phi_doi"] == 24_000_000
    assert t["loi_nhuan"] == t["ket_qua_sau_chi_phi_xe"] - 24_000_000
    for x in d["xe"]:
        assert "phan_bo_chi_phi_doi" not in x, "mặc định KHÔNG chia chi phí đội về từng xe"
    assert any(c["nhom"] == "lai_vay" for c in d["chi_tiet_chi_phi_doi"])


def test_muon_phan_bo_thi_phai_chon_tieu_thuc_va_ket_qua_nam_o_cot_rieng(_startup):
    d = bc("ngay_khai_thac")
    x = d["xe"][0]
    assert x["phan_bo_chi_phi_doi"] > 0
    assert x["ket_qua_sau_phan_bo"] == x["ket_qua_xe"] - x["phan_bo_chi_phi_doi"]
    assert x["ket_qua_xe"] != x["ket_qua_sau_phan_bo"], "hai con số phải nằm ở hai cột khác nhau"
    # Tổng không đổi dù chia kiểu nào – phân bổ chỉ chuyển chỗ, không tạo ra hay làm mất tiền.
    assert bc("doanh_thu")["tong"]["loi_nhuan"] == d["tong"]["loi_nhuan"]


def test_tieu_thuc_la_thi_tu_choi(_startup):
    r = client.get(f"/api/v1/fleet/lai-lo?ky={KY}&phan_bo=linh_tinh", headers=login("ketoan"))
    assert r.status_code == 422


# ---------------------------------------------------------------- Chốt chặn khi nhập
def test_nhap_lai_cung_khoan_thi_chan_chu_khong_cong_don(_startup):
    r = them("bai_xe", 4_000_000)
    assert r.status_code == 422 and "nhân đôi" in r.json()["detail"]


def test_chi_phi_cua_xe_bat_buoc_chon_xe(_startup):
    r = them("bao_duong", 1_000_000)
    assert r.status_code == 422 and "phải chọn xe" in r.json()["detail"]


def test_chi_phi_cua_doi_khong_gan_vao_mot_xe(_startup):
    r = them("bai_xe", 1_000_000, _xe_id(), "gắn nhầm")
    assert r.status_code == 422 and "gánh phần của cả đội" in r.json()["detail"]


def test_go_mot_khoan_phai_ghi_ly_do(_startup):
    ds = client.get(f"/api/v1/fleet/chi-phi-ky?ky={KY}", headers=login("ketoan")).json()["rows"]
    cid = ds[0]["id"]
    assert client.delete(f"/api/v1/fleet/chi-phi-ky/{cid}", headers=login("ketoan")).status_code == 422
    r = client.delete(f"/api/v1/fleet/chi-phi-ky/{cid}?ly_do=ghi nhầm kỳ", headers=login("ketoan"))
    assert r.status_code == 200


# ---------------------------------------------------------------- Công suất
def test_cong_suat_tinh_tren_so_xe_trong_doi_khong_phai_so_xe_co_chay(_startup):
    """Mẫu số bằng số xe có chạy thì chiếc nằm bãi cả tháng biến mất, và công suất luôn đẹp."""
    d = bc()
    t = d["tong"]
    assert t["so_xe_trong_doi"] >= t["so_xe_khai_thac"]
    assert t["cong_suat"] == round(t["ngay_khai_thac"] / (t["so_xe_trong_doi"] * d["so_ngay_ky"]), 4)
