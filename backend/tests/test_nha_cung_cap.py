"""Nhà cung cấp & đặt dịch vụ.

Đây là đường tiền ra khỏi công ty, nên bộ test nhắm vào bốn chỗ hỏng có hậu quả thật:

  1. Đổi số tài khoản nhà cung cấp mà có hiệu lực NGAY – cách gian lận thanh toán phổ biến nhất là đổi
     tài khoản của một nhà cung cấp có thật rồi để hệ thống tự chuyển tiền vào đó.
  2. Người đề nghị tự bấm nút xác nhận – một chốt chặn hai người mà một người bấm được cả hai nút thì
     không phải chốt chặn.
  3. Đơn đặt dịch vụ không gắn tour – chi phí không quy được vào giá thành, cuối kỳ thành một cục chung.
  4. Tạo hai hồ sơ cho cùng một nhà cung cấp – công nợ của một đối tác nằm ở hai chỗ, không ai cộng lại.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ncc.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ncc.db"): os.remove("test_ncc.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


@pytest.fixture(scope="module")
def ncc(_startup):
    r = client.post("/api/v1/ncc", headers=login("cntt"),
                    json={"ten": "Khách sạn Kiểm Thử", "loai": "khach_san", "ma_so_thue": "0312345678",
                          "so_tai_khoan": "0011223344", "ngan_hang": "Vietcombank",
                          "chu_tai_khoan": "CTY TNHH KIEM THU"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_tao_ncc_va_canh_bao_thieu_ma_so_thue(_startup):
    r = client.post("/api/v1/ncc", headers=login("cntt"),
                    json={"ten": "Nhà hàng Không MST", "loai": "nha_hang"})
    assert r.status_code == 201, r.text
    cb = " ".join(r.json()["canh_bao"])
    assert "mã số thuế" in cb and "TNDN" in cb
    assert "số tài khoản" in cb


def test_khong_tao_hai_ho_so_cho_cung_mot_nha_cung_cap(ncc):
    """Công nợ của một đối tác nằm ở hai chỗ thì không ai cộng lại được."""
    r = client.post("/api/v1/ncc", headers=login("cntt"),
                    json={"ten": "khách sạn kiểm thử", "loai": "khach_san"})
    assert r.status_code == 422 and "dùng lại hồ sơ" in r.json()["detail"]


# ---------------------------------------------------------------- Đổi số tài khoản: hai người
def test_doi_tai_khoan_chua_co_hieu_luc_ngay(ncc):
    """Đây là chốt chặn quan trọng nhất của cả mô-đun: đề nghị đổi KHÔNG làm đổi số đang dùng để chi."""
    r = client.post(f"/api/v1/ncc/{ncc}/doi-tai-khoan", headers=login("cntt"),
                    json={"so_tk_moi": "9998887776", "ngan_hang_moi": "ACB",
                          "chu_tk_moi": "CTY TNHH KIEM THU", "ly_do": "Đổi ngân hàng",
                          "chung_tu": "CV 12/2026 của khách sạn"})
    assert r.status_code == 201, r.text
    s = next(x for x in client.get("/api/v1/ncc", headers=login("ketoan")).json() if x["id"] == ncc)
    assert s["so_tai_khoan"] == "0011223344", "số đang hiệu lực KHÔNG được đổi khi chưa ai xác nhận"
    assert any("chờ người thứ hai" in c for c in s["canh_bao"])


def test_doi_tai_khoan_khong_co_van_ban_thi_tu_choi(ncc):
    r = client.post(f"/api/v1/ncc/{ncc}/doi-tai-khoan", headers=login("cntt"),
                    json={"so_tk_moi": "1112223334"})
    assert r.status_code == 422 and "văn bản" in r.json()["detail"]


def test_nguoi_de_nghi_khong_tu_xac_nhan_duoc(ncc):
    """Một chốt chặn hai người mà một người bấm được cả hai nút thì không phải chốt chặn."""
    cho = client.get("/api/v1/ncc/doi-tai-khoan/cho-xac-nhan", headers=login("ketoan")).json()
    c = next(x for x in cho if x["supplier_id"] == ncc)
    # người đề nghị là "cntt"; thử cho chính cntt xác nhận – nhưng cntt không nằm trong nhóm duyệt,
    # nên trước hết kiểm tra chính vai trò đã chặn.
    r = client.post(f"/api/v1/ncc/doi-tai-khoan/{c['id']}/xac-nhan", headers=login("cntt"),
                    json={"dong_y": True})
    assert r.status_code == 403


def test_nguoi_thu_hai_xac_nhan_thi_so_tai_khoan_moi_co_hieu_luc(ncc):
    cho = client.get("/api/v1/ncc/doi-tai-khoan/cho-xac-nhan", headers=login("ketoan")).json()
    c = next(x for x in cho if x["supplier_id"] == ncc)
    r = client.post(f"/api/v1/ncc/doi-tai-khoan/{c['id']}/xac-nhan", headers=login("ketoan"),
                    json={"dong_y": True, "ghi_chu": "Đã gọi điện xác minh với khách sạn"})
    assert r.status_code == 200, r.text
    s = next(x for x in client.get("/api/v1/ncc", headers=login("ketoan")).json() if x["id"] == ncc)
    assert s["so_tai_khoan"] == "9998887776" and s["ngan_hang"] == "ACB"


def test_xac_nhan_lai_lan_hai_thi_tu_choi(ncc):
    from app.db.session import SessionLocal
    from app.models.suppliers import SupplierBankChange
    from sqlalchemy import select
    db = SessionLocal()
    c = db.execute(select(SupplierBankChange).where(SupplierBankChange.supplier_id == ncc)
                   .order_by(SupplierBankChange.id.desc())).scalars().first()
    cid = c.id; db.close()
    r = client.post(f"/api/v1/ncc/doi-tai-khoan/{cid}/xac-nhan", headers=login("chutich"),
                    json={"dong_y": True})
    assert r.status_code == 422 and "không xử lý lại" in r.json()["detail"]


def test_so_tai_khoan_khong_sua_duoc_qua_duong_sua_ho_so(ncc):
    """Đóng luôn cửa sau: nếu form sửa hồ sơ nhận được số tài khoản thì chốt chặn hai người thành vô nghĩa."""
    r = client.put(f"/api/v1/ncc/{ncc}", headers=login("cntt"),
                   json={"nguoi_lien_he": "Chị Lan", "so_tai_khoan": "0000000000"})
    assert r.status_code == 200
    s = next(x for x in client.get("/api/v1/ncc", headers=login("ketoan")).json() if x["id"] == ncc)
    assert s["so_tai_khoan"] == "9998887776", "sửa hồ sơ KHÔNG được đổi số tài khoản"
    assert s["nguoi_lien_he"] == "Chị Lan"


# ---------------------------------------------------------------- Đơn đặt dịch vụ
def test_dat_dich_vu_phai_gan_tour(ncc):
    r = client.post("/api/v1/ncc/don", headers=login("cntt"),
                    json={"supplier_id": ncc, "tour_id": 999999, "noi_dung": "20 phòng đôi",
                          "so_luong": 20, "don_gia": 800_000})
    assert r.status_code == 422 and "gắn TOUR" in r.json()["detail"]


def test_tao_don_va_tinh_thanh_tien(ncc):
    tours = client.get("/api/v1/tours", headers=login("cntt")).json()["rows"]
    if not tours: pytest.skip("dữ liệu mẫu không có tour")
    tid = tours[0]["id"]
    r = client.post("/api/v1/ncc/don", headers=login("cntt"),
                    json={"supplier_id": ncc, "tour_id": tid, "noi_dung": "20 phòng đôi 2 đêm",
                          "so_luong": 20, "don_vi": "phòng", "don_gia": 800_000,
                          "ngay_su_dung": str(HOM_NAY)})
    assert r.status_code == 201, r.text
    assert r.json()["thanh_tien"] == 16_000_000
    d = client.get(f"/api/v1/ncc/don?tour_id={tid}", headers=login("ketoan")).json()
    assert d["tong_tien"] >= 16_000_000


def test_ghi_ncc_da_xac_nhan_phai_co_can_cu(ncc):
    """Không có căn cứ thì sau này không ai biết đơn đã được nhận hay chưa – và đó là lúc khách tới nơi
    mà khách sạn không có phòng."""
    d = client.get("/api/v1/ncc/don", headers=login("ketoan")).json()["rows"]
    if not d: pytest.skip("chưa có đơn")
    did = d[0]["id"]
    r = client.post(f"/api/v1/ncc/don/{did}/trang-thai", headers=login("cntt"),
                    json={"status": "da_xac_nhan"})
    assert r.status_code == 422 and "căn cứ" in r.json()["detail"]
    r = client.post(f"/api/v1/ncc/don/{did}/trang-thai", headers=login("cntt"),
                    json={"status": "da_xac_nhan", "xac_nhan_ncc": "Email xác nhận 07/9"})
    assert r.status_code == 200, r.text
