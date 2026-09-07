"""Form nhập tay của Giám đốc điều hành đội xe: sửa nhật trình chuyến và lập đề xuất chi.

Số liệu đội xe sẽ do người nhập và sửa tay, nên bộ test này giữ đúng những chỗ mà "cho sửa" dễ thành
"sửa mất dấu vết":

  1. Chuyến ĐÃ XÁC NHẬN không sửa thẳng được – phải mở lại kèm lý do, và lý do phải nằm lại trên chuyến.
  2. Chuyến thuộc kỳ quyết toán ĐÃ ĐÓNG thì không mở lại được: đó là con số hai bên đã thỏa thuận xong.
  3. Km cuối nhỏ hơn km đầu, ngày về trước ngày đi – chặn ngay lúc sửa, không để thành dữ liệu.
  4. Đề xuất chi bắt buộc có NHÓM: "nạp thẻ dầu" và "sửa xe" nhìn giống nhau lúc lập phiếu, nhưng một cái
     là nạp quỹ còn một cái là chi phí. Không phân loại lúc lập thì cuối tháng phải đọc lại từng phiếu.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_form_xe.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_form_xe.db"): os.remove("test_form_xe.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def xe(plate: str) -> dict:
    return next(x for x in client.get("/api/v1/fleet/xe", headers=login("cntt")).json() if x["plate"] == plate)


@pytest.fixture()
def chuyen():
    v = xe("50F-009.60")
    r = client.post("/api/v1/fleet/chuyen", headers=login("ketoan"),
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY + timedelta(days=2)),
                          "km_dau": 300_000, "km_cuoi": 300_800, "doanh_thu": 20_000_000,
                          "ten_tour": "Đà Lạt (lẻ)"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------- Sửa nhật trình
def test_sua_duoc_nhat_trinh_chuyen_chua_xac_nhan(chuyen):
    h = login("ketoan")
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}", headers=h,
                   json={"doanh_thu": 22_000_000, "ten_tour": "Đà Lạt - Vĩnh Hy (lẻ)", "km_cuoi": 300_950})
    assert r.status_code == 200, r.text
    ct = next(x for x in client.get("/api/v1/fleet/chuyen", headers=h).json() if x["id"] == chuyen)
    assert ct["doanh_thu"] == 22_000_000 and ct["ten_tour"] == "Đà Lạt - Vĩnh Hy (lẻ)"


def test_km_cuoi_nho_hon_km_dau_thi_chan_ngay_luc_sua(chuyen):
    """Để lọt thì quãng đường thành số âm, và mọi chỉ số đồng/km của xe đó sai theo."""
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}", headers=login("ketoan"), json={"km_cuoi": 299_000})
    assert r.status_code == 422 and "Km cuối nhỏ hơn km đầu" in r.json()["detail"]


def test_ngay_ve_truoc_ngay_di_thi_chan(chuyen):
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}", headers=login("ketoan"),
                   json={"ngay_ve": str(HOM_NAY - timedelta(days=1))})
    assert r.status_code == 422 and "Ngày về trước ngày đi" in r.json()["detail"]


def test_chuyen_da_xac_nhan_thi_khong_sua_thang_duoc(chuyen):
    """Sửa thẳng vào chuyến đã chốt là đổi con số hai bên đã đối chiếu mà không ai biết ai sửa, sửa gì."""
    h = login("ketoan")
    assert client.post(f"/api/v1/fleet/chuyen/{chuyen}/xac-nhan", headers=login("cntt")).status_code == 200
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}", headers=h, json={"doanh_thu": 1})
    assert r.status_code == 422 and "mở lại" in r.json()["detail"]


def test_mo_lai_phai_co_ly_do_va_ly_do_nam_lai_tren_chuyen(chuyen):
    h = login("ketoan")
    client.post(f"/api/v1/fleet/chuyen/{chuyen}/xac-nhan", headers=login("cntt"))
    r = client.post(f"/api/v1/fleet/chuyen/{chuyen}/mo-lai", headers=h, json={"ly_do": "   "})
    assert r.status_code == 422 and "lý do" in r.json()["detail"]

    r = client.post(f"/api/v1/fleet/chuyen/{chuyen}/mo-lai", headers=h,
                    json={"ly_do": "Kế toán phát hiện tiền dầu ghi thiếu một hóa đơn"})
    assert r.status_code == 200, r.text
    ct = next(x for x in client.get("/api/v1/fleet/chuyen", headers=h).json() if x["id"] == chuyen)
    assert ct["status"] == "cho_xac_nhan"
    assert "ghi thiếu một hóa đơn" in (ct.get("note") or ""), "lý do phải nằm lại trên chuyến"
    # mở lại rồi thì sửa được
    assert client.put(f"/api/v1/fleet/chuyen/{chuyen}", headers=h, json={"doanh_thu": 25_000_000}).status_code == 200


def test_khong_mo_lai_duoc_chuyen_thuoc_ky_da_dong(_startup):
    """Kỳ đã đóng là con số hai bên đã thỏa thuận và đã trả tiền. Sửa ngược vào đó là sửa một khoản đã chi."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe form test"}).json()["id"]
    v = xe("50E-955.31")
    client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h, json={"vehicle_id": v["id"], "partner_id": pid})
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                          "km_dau": 10_000, "km_cuoi": 10_200, "doanh_thu": 9_000_000,
                          "ten_tour": "Chuyến kỳ đóng"}).json()
    client.post(f"/api/v1/fleet/chuyen/{t['id']}/xac-nhan", headers=login("cntt"))
    ky = f"{HOM_NAY:%Y-%m}"
    st = client.post(f"/api/v1/fleet/quyet-toan/{ky}/{pid}/dung", headers=h).json()
    assert client.post(f"/api/v1/fleet/quyet-toan/{st['id']}/dong-ky", headers=login("chutich")).status_code == 200

    r = client.post(f"/api/v1/fleet/chuyen/{t['id']}/mo-lai", headers=h, json={"ly_do": "Sửa doanh thu"})
    assert r.status_code == 422 and "đã ĐÓNG" in r.json()["detail"]


# ---------------------------------------------------------------- Sửa và xóa dòng chi phí
def test_sua_va_xoa_duoc_dong_chi_phi_nhap_nham(chuyen):
    h = login("ketoan")
    cid = client.post(f"/api/v1/fleet/chuyen/{chuyen}/chi-phi", headers=h,
                      json={"kind": "dau", "amount": 5_000_000, "lit": 170, "chung_tu": "HD-1"}).json()["id"]
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}/chi-phi/{cid}", headers=h,
                   json={"amount": 5_500_000, "lit": 185})
    assert r.status_code == 200, r.text
    ct = next(x for x in client.get("/api/v1/fleet/chuyen", headers=h).json() if x["id"] == chuyen)
    assert ct["tong_chi_vietourist"] == 5_500_000

    assert client.delete(f"/api/v1/fleet/chuyen/{chuyen}/chi-phi/{cid}", headers=h).status_code == 200
    ct = next(x for x in client.get("/api/v1/fleet/chuyen", headers=h).json() if x["id"] == chuyen)
    assert ct["tong_chi_vietourist"] == 0


def test_sua_chi_phi_len_qua_nguong_ma_khong_co_chung_tu_thi_chan(chuyen):
    """Chặn cứng B6 phải áp cả lúc SỬA, không chỉ lúc thêm – nếu không thì thêm 1 đồng rồi sửa lên 50 triệu
    là đi vòng qua được chốt chặn."""
    h = login("ketoan")
    cid = client.post(f"/api/v1/fleet/chuyen/{chuyen}/chi-phi", headers=h,
                      json={"kind": "cau_duong", "amount": 500_000}).json()["id"]
    r = client.put(f"/api/v1/fleet/chuyen/{chuyen}/chi-phi/{cid}", headers=h, json={"amount": 50_000_000})
    assert r.status_code == 422 and "chứng từ gốc" in r.json()["detail"]


# ---------------------------------------------------------------- Đề xuất chi
def test_lap_de_xuat_chi_tren_vtos(_startup):
    h = login("ketoan")
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=h,
                    json={"ngay": str(HOM_NAY), "so_tien": 8_400_000, "bien_so": "50F-009.60",
                          "noi_dung": "Thay bình ắc quy", "nhom": "Chi phí riêng của xe",
                          "nguoi_thu_huong": "CTY TNHH TM DV Năm Tuội", "so_tai_khoan": "060058950621",
                          "ngan_hang": "Sacombank", "chung_tu": "HD-00007769"})
    assert r.status_code == 201, r.text
    ma = r.json()["ma_gd"]
    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    dong = next(t for t in d["rows"] if t["ma_gd"] == ma)
    assert dong["so_tien"] == 8_400_000 and dong["xe"] == "50F-009.60"
    assert "Năm Tuội" in dong["mo_ta"] if "mo_ta" in dong else True


def test_de_xuat_chi_bat_buoc_chon_nhom(_startup):
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 1_000_000, "noi_dung": "Nạp thẻ dầu"})
    assert r.status_code == 422 and "nhóm" in r.json()["detail"]


def test_de_xuat_chi_lon_khong_co_chung_tu_thi_chan(_startup):
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 50_000_000, "noi_dung": "Sửa hộp số",
                          "nhom": "Chi phí riêng của xe"})
    assert r.status_code == 422 and "chứng từ gốc" in r.json()["detail"]


def test_de_xuat_nap_quy_khong_cong_vao_chi_phi(_startup):
    """Nạp thẻ dầu là chuyển tiền vào quỹ, tiền dầu thật nằm ở phiếu chi phí từng chuyến. Cộng cả hai là
    tính đúp tiền dầu của cả tháng."""
    h = login("ketoan")
    truoc = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=h,
                    json={"ngay": str(HOM_NAY), "so_tien": 150_000_000, "noi_dung": "Nạp thẻ dầu VTH",
                          "nhom": "Nạp quỹ / tạm ứng", "khong_phai_chi_phi": True})
    assert r.status_code == 201, r.text
    sau = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=h).json()
    assert sau["tong_chi_phi"] == truoc["tong_chi_phi"]
    assert sau["tong_dieu_chuyen"] == truoc["tong_dieu_chuyen"] + 150_000_000
