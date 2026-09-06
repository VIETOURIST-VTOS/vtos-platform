"""Công ty chủ quản của hồ sơ nghiệp vụ (Ý kiến thẩm định 06/9/2026 – Đợt 2 mục 2).

Yêu cầu nghiệm thu ghi rõ: "hồ sơ cũ chưa xác định được đưa vào danh sách đối chiếu, KHÔNG tự gán về
công ty mẹ". Bộ phép thử này giữ đúng câu đó:
- không có đường nào (tạo mới, suy từ hồ sơ cha, chạy lại nhiều lần) đặt được pháp nhân mà không có căn cứ;
- suy từ hồ sơ cha chỉ chạy khi hồ sơ cha ĐÃ có pháp nhân, và không ghi đè hồ sơ đã gán tay;
- tour không có hồ sơ cha nên luôn phải do người chỉ định, có ghi nhật ký kèm tiêu chí.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_phap_nhan_ho_so.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_phap_nhan_ho_so.db"): os.remove("test_phap_nhan_ho_so.db")
import pytest
from datetime import date, timedelta
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


def cos():
    return {c["code"]: c for c in client.get("/api/v1/companies", headers=login("cntt")).json()}


def new_tour(code, company_id=None):
    d = date.today() + timedelta(days=20)
    body = {"code": code, "name": "Chuyến " + code, "tour_type": "le_noi_dia", "start_date": str(d),
            "end_date": str(d + timedelta(days=2)), "operator_id": 0, "price_per_pax": 3_000_000,
            "fixed_cost": 10_000_000, "var_cost_per_pax": 1_000_000, "planned_pax": 20, "rest_stops": "Tân Phú"}
    if company_id: body["company_id"] = company_id
    r = client.post("/api/v1/tours", json=body, headers=login("dh.lan"))
    assert r.status_code == 201, r.text
    return r.json()


def test_coverage_liet_ke_du_nam_loai_ho_so():
    cv = client.get("/api/v1/companies/scope/coverage", headers=login("cntt")).json()
    ks = {r["kind"] for r in cv["rows"]}
    assert ks == {"tour", "booking", "receipt", "chi", "chung_tu"}
    tour = next(r for r in cv["rows"] if r["kind"] == "tour")
    assert tour["suy_duoc_tu"] is None, "tour không có hồ sơ cha – phải do người chỉ định"
    assert next(r for r in cv["rows"] if r["kind"] == "booking")["suy_duoc_tu"] == "Tour"


def test_tour_moi_khong_ghi_phap_nhan_thi_vao_danh_sach_doi_chieu():
    t = new_tour("KT-PN-0001")
    ds = client.get("/api/v1/companies/scope/tour/pending?limit=500", headers=login("cntt")).json()
    assert any(r["id"] == t["id"] for r in ds["rows"]), "tour chưa xác định pháp nhân phải nằm trong danh sách đối chiếu"


def test_suy_tu_ho_so_cha_khong_cham_toi_ho_so_khong_co_can_cu():
    """Chạy suy nhiều lần: chỉ hồ sơ có cha đã xác định mới được gán; hồ sơ không có căn cứ vẫn để trống."""
    from app.db.session import SessionLocal
    from app.models.core import Booking, Tour
    from app.models.payments import Receipt

    vtd = cos()["VTD"]["id"]
    t_co = new_tour("KT-PN-0002", company_id=vtd)
    t_khong = new_tour("KT-PN-0003")

    db = SessionLocal()
    mau = db.query(Booking).first()
    ids = {}
    for t in (t_co, t_khong):
        b = Booking(code="KTPN" + t["code"][-4:], tour_id=t["id"], request_id=0, sales_id=mau.sales_id,
                    created_by=mau.created_by, customer_name="Khách " + t["code"], customer_phone="0912000111",
                    source="Zalo", pax=2, amount=6_000_000)
        db.add(b); db.flush()
        db.add(Receipt(code="KTPT" + t["code"][-4:], booking_id=b.id, amount=1_000_000, payer="Khách"))
        ids[t["code"]] = b.id
    db.commit(); db.close()

    d1 = client.post("/api/v1/companies/scope/derive", headers=login("cntt"))
    assert d1.status_code == 200, d1.text
    assert d1.json()["da_suy"]["booking"] >= 1 and d1.json()["da_suy"]["receipt"] >= 1
    d2 = client.post("/api/v1/companies/scope/derive", headers=login("cntt")).json()
    assert d2["da_suy"]["booking"] == 0, "chạy lại lần hai không được gán thêm gì (không có căn cứ mới)"

    db = SessionLocal()
    assert db.get(Booking, ids["KT-PN-0002"]).company_id == vtd
    assert db.get(Booking, ids["KT-PN-0003"]).company_id is None, "tour chưa xác định thì booking cũng phải để trống"
    assert db.get(Tour, t_khong["id"]).company_id is None, "không có đường nào tự gán pháp nhân cho tour"
    r_co = db.query(Receipt).filter(Receipt.code == "KTPT0002").first()
    r_khong = db.query(Receipt).filter(Receipt.code == "KTPT0003").first()
    assert r_co.company_id == vtd and r_khong.company_id is None, "phiếu thu đi theo booking, hai bậc vẫn đúng"
    db.close()


def test_gan_tay_khong_bi_suy_de_len():
    """Người đã gán tay là quyết định cuối; chạy suy sau đó không được đổi."""
    from app.db.session import SessionLocal
    from app.models.core import Booking
    vtd, vtrip = cos()["VTD"]["id"], cos()["VTRIP-VT"]["id"]
    t = new_tour("KT-PN-0007", company_id=vtd)
    db = SessionLocal()
    mau = db.query(Booking).first()
    b = Booking(code="KTPN0007", tour_id=t["id"], request_id=0, sales_id=mau.sales_id, created_by=mau.created_by,
                customer_name="Khách 7", customer_phone="0912000111", source="Zalo", pax=1, amount=1_000_000)
    db.add(b); db.commit(); bid = b.id; db.close()
    assert client.post("/api/v1/companies/scope/booking/assign", json={"ids": [bid], "company_id": vtrip},
                       headers=login("ketoan")).status_code == 200
    client.post("/api/v1/companies/scope/derive", headers=login("cntt"))
    db = SessionLocal()
    assert db.get(Booking, bid).company_id == vtrip, "suy tự động không được ghi đè lên quyết định của người"
    db.close()


def test_gan_tay_va_go_ve_chua_xac_dinh():
    vtrip = cos()["VTRIP-VT"]["id"]
    t = new_tour("KT-PN-0004")
    r = client.post("/api/v1/companies/scope/tour/assign", json={"ids": [t["id"]], "company_id": vtrip}, headers=login("ketoan"))
    assert r.status_code == 200 and r.json()["da_gan"] == 1, r.text
    ds = client.get("/api/v1/companies/scope/tour/pending?limit=500", headers=login("cntt")).json()
    assert not any(x["id"] == t["id"] for x in ds["rows"])
    r = client.post("/api/v1/companies/scope/tour/assign", json={"ids": [t["id"]], "company_id": None}, headers=login("ketoan"))
    assert r.status_code == 200 and "chưa xác định" in r.json()["message"]
    ds = client.get("/api/v1/companies/scope/tour/pending?limit=500", headers=login("cntt")).json()
    assert any(x["id"] == t["id"] for x in ds["rows"])


def test_gan_phap_nhan_khong_co_trong_danh_muc_bi_tu_choi():
    t = new_tour("KT-PN-0005")
    r = client.post("/api/v1/companies/scope/tour/assign", json={"ids": [t["id"]], "company_id": 999999}, headers=login("ketoan"))
    assert r.status_code == 422


def test_gan_lo_tour_theo_tieu_chi_ghi_nhat_ky():
    vtd = cos()["VTD"]["id"]
    d = date.today() + timedelta(days=20)
    r = client.post("/api/v1/companies/scope/tour/assign-filter",
                    json={"company_id": vtd, "nguon": "vtos", "tu_ngay": str(d), "den_ngay": str(d), "chi_chua_gan": True},
                    headers=login("ketoan"))
    assert r.status_code == 200, r.text
    assert r.json()["da_gan"] >= 1 and r.json()["tieu_chi"]["nguon"] == "vtos"
    nk = client.get("/api/v1/audit?limit=50", headers=login("cntt")).json()
    rows = nk["rows"] if isinstance(nk, dict) else nk
    assert any(x.get("action") == "gan_phap_nhan_lo_tour" for x in rows), "gán theo lô phải để lại dấu vết"


def test_vai_tro_khong_co_quyen_khong_gan_duoc():
    t = new_tour("KT-PN-0006")
    r = client.post("/api/v1/companies/scope/tour/assign", json={"ids": [t["id"]], "company_id": cos()["VTD"]["id"]}, headers=login("kd.hoa"))
    assert r.status_code == 403


def test_gan_lo_chung_tu_va_de_nghi_chi_khong_gan_tour():
    """Chứng từ nạp từ MISA và chi hành chính không gắn tour nên không suy được – phải gán theo kỳ / nhóm chi."""
    from app.db.session import SessionLocal
    from app.models.accounting import JournalEntry
    vtd = cos()["VTD"]["id"]

    nhom = client.get("/api/v1/companies/scope/chung_tu/groups", headers=login("ketoan")).json()
    assert nhom["theo"] == "nguồn chứng từ × kỳ"

    db = SessionLocal()
    tong_truoc = db.query(JournalEntry).filter(JournalEntry.company_id.is_(None)).count()
    db.close()

    r = client.post("/api/v1/companies/scope/chung_tu/assign-batch",
                    json={"company_id": vtd, "khong_co_tour": True, "chi_chua_gan": True}, headers=login("ketoan"))
    assert r.status_code == 200, r.text
    assert r.json()["da_gan"] <= tong_truoc
    assert r.json()["tieu_chi"]["khong_co_tour"] is True

    # chạy lại: không còn hồ sơ nào thỏa điều kiện nên không gán thêm
    r2 = client.post("/api/v1/companies/scope/chung_tu/assign-batch",
                     json={"company_id": vtd, "khong_co_tour": True, "chi_chua_gan": True}, headers=login("ketoan"))
    assert r2.json()["da_gan"] == 0

    rc = client.post("/api/v1/companies/scope/chi/assign-batch",
                     json={"company_id": vtd, "nhom": "hanh_chinh", "chi_chua_gan": True}, headers=login("ketoan"))
    assert rc.status_code == 200, rc.text

    # loại hồ sơ không thuộc diện gán theo lô thì bị từ chối, không âm thầm gán bừa
    rt = client.post("/api/v1/companies/scope/tour/assign-batch", json={"company_id": vtd}, headers=login("ketoan"))
    assert rt.status_code == 422


def test_gan_lo_ho_so_can_quyen():
    r = client.post("/api/v1/companies/scope/chung_tu/assign-batch",
                    json={"company_id": cos()["VTD"]["id"]}, headers=login("kd.hoa"))
    assert r.status_code == 403
