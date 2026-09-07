"""Sổ công nợ toàn hệ thống: phải thu khách, phải trả nhà cung cấp, công nợ đội xe.

Ba cách một bảng công nợ nói sai, và bộ test này chặn cả ba:

  1. Bù trừ phải thu với phải trả ra "công nợ ròng" – con số không đòi được của ai, cũng không trả cho ai.
  2. Tính đề nghị chi ĐANG CHỜ DUYỆT là nợ phải trả – thổi phồng nghĩa vụ và làm hỏng dự báo dòng tiền.
  3. Để khách chuyển thừa thành phải thu ÂM – vừa giấu một khoản phải trả lại, vừa làm tổng phải thu của
     cả công ty nhỏ hơn sự thật.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_cong_no_hthong.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cong_no_hthong.db"): os.remove("test_cong_no_hthong.db")
from datetime import date, timedelta
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


def _sua_booking(**kw):
    """Đặt trực tiếp vào cơ sở dữ liệu: mục tiêu ở đây là cách TÍNH công nợ, không phải luồng bán hàng."""
    from app.db.session import SessionLocal
    from app.models.core import Booking, Tour
    from sqlalchemy import select
    db = SessionLocal()
    b = db.execute(select(Booking).where(Booking.cancelled == False).order_by(Booking.id)).scalars().first()
    assert b is not None, "dữ liệu mẫu phải có ít nhất một booking"
    for k, v in kw.items(): setattr(b, k, v)
    t = db.get(Tour, b.tour_id)
    db.commit(); out = (b.id, b.code, t.start_date if t else None); db.close()
    return out


def test_khong_co_truong_nao_bu_tru_hai_ve(_startup):
    d = client.get("/api/v1/cong-no", headers=login("ketoan")).json()
    assert "phai_thu_khach" in d and "phai_tra_ncc" in d
    for k in d:
        assert "rong" not in k and "net" not in k, f"không được có trường bù trừ: {k}"
    assert any("KHÔNG bù trừ" in g for g in d["giai_thich"])


def test_thu_thua_thanh_khoan_phai_tra_lai_chu_khong_phai_thu_am(_startup):
    """Khách chuyển dư 5 triệu: đó là khoản công ty phải trả lại, không phải phải thu −5 triệu."""
    bid, code, _ = _sua_booking(amount=10_000_000, discount=0, paid=15_000_000)
    d = client.get("/api/v1/cong-no/phai-thu", headers=login("ketoan")).json()
    assert all(x["con_lai"] > 0 for x in d["chi_tiet"]), "cột còn phải thu không được chứa số âm"
    tt = next(x for x in d["thu_thua"] if x["booking_id"] == bid)
    assert tt["phai_tra_lai"] == 5_000_000
    assert d["tong_thu_thua_phai_tra_lai"] >= 5_000_000


def test_qua_han_tinh_theo_ngay_khoi_hanh(_startup):
    """Khách đã đi mà còn nợ là khoản đã ra khỏi tầm kiểm soát, không phải khoản sắp thu."""
    from app.db.session import SessionLocal
    from app.models.core import Booking, Tour
    from sqlalchemy import select
    db = SessionLocal()
    b = db.execute(select(Booking).where(Booking.cancelled == False).order_by(Booking.id)).scalars().first()
    t = db.get(Tour, b.tour_id)
    t.start_date = HOM_NAY - timedelta(days=10)
    b.amount, b.discount, b.paid = 20_000_000, 0, 8_000_000
    db.commit(); bid = b.id; db.close()

    d = client.get("/api/v1/cong-no/phai-thu", headers=login("ketoan")).json()
    dong = next(x for x in d["chi_tiet"] if x["booking_id"] == bid)
    assert dong["con_lai"] == 12_000_000 and dong["qua_han"] is True
    assert d["trong_do_qua_han"] >= 12_000_000


def test_de_nghi_chi_cho_duyet_khong_tinh_la_no_phai_tra(_startup):
    """Một đề nghị đang chờ Trưởng phòng xem có thể bị từ chối – gộp vào phải trả là thổi phồng nghĩa vụ."""
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    db.add(PaymentRequest(code="TEST-CHO-1", category="chi_tour", supplier_name="NCC kiểm thử",
                          amount=30_000_000, description="Đang chờ duyệt", status="cho_tp", created_by="kt"))
    db.add(PaymentRequest(code="TEST-NO-1", category="chi_tour", supplier_name="NCC kiểm thử",
                          amount=7_000_000, description="Đã duyệt, chờ chi", status="cho_chi",
                          has_invoice=True, created_by="kt"))
    db.commit(); db.close()

    d = client.get("/api/v1/cong-no/phai-tra", headers=login("ketoan")).json()
    ma = {x["code"] for x in d["chi_tiet"]}
    assert "TEST-NO-1" in ma and "TEST-CHO-1" not in ma
    assert d["tong_phai_tra"] >= 7_000_000
    assert d["dang_cho_duyet"] >= 30_000_000
    assert "TEST-CHO-1" in {x["code"] for x in d["cho_duyet"]}


def test_khoan_phai_tra_thieu_hoa_don_gtgt_duoc_dem_rieng(_startup):
    """Chi không có hóa đơn GTGT thì không được trừ thuế TNDN – kế toán cần biết phần đó là bao nhiêu
    TRƯỚC khi trả tiền, không phải lúc quyết toán thuế cuối năm."""
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    db.add(PaymentRequest(code="TEST-NO-2", category="chi_tour", supplier_name="NCC không hóa đơn",
                          amount=4_000_000, description="Chờ chi, chưa có hóa đơn", status="cho_chi",
                          has_invoice=False, created_by="kt"))
    db.commit(); db.close()
    d = client.get("/api/v1/cong-no/phai-tra", headers=login("ketoan")).json()
    assert d["thieu_hoa_don_gtgt"] >= 4_000_000


def test_gom_ca_cong_no_doi_xe(_startup):
    d = client.get("/api/v1/cong-no", headers=login("ketoan")).json()
    for k in ("cong_ty_phai_tra_chu_xe", "chu_xe_phai_tra_cong_ty", "con_phai_thu_ban_xe",
              "du_no_vay_the_chap_xe"):
        assert k in d["doi_xe"]


def test_nhan_vien_kinh_doanh_khong_xem_cong_no_toan_cong_ty(_startup):
    """Sổ công nợ là số tiền của cả công ty. Nhân viên kinh doanh theo dõi booking của mình ở màn hình
    bán hàng, không mở sổ công nợ toàn hệ thống."""
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    db.add(User(username="nvkd.congno.kt", full_name="NV kinh doanh kiểm thử", role="nv_kd",
                department="kinh_doanh", staff_code="KT910",
                password_hash=hash_password("123456"), active=True))
    db.commit(); db.close()
    r = client.get("/api/v1/cong-no", headers=login("nvkd.congno.kt"))
    assert r.status_code == 403
