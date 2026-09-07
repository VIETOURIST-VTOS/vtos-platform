"""Chiến dịch marketing – Đợt 1 (đề xuất 07/9/2026, Ban TGĐ duyệt).

Chiến dịch là trục nối tiền – khách – doanh thu. Bộ kiểm thử này khoá lại đúng những chỗ mà nếu lỏng
thì màn hình vẫn chạy nhưng số liệu vô nghĩa:

  M1 không có chỉ tiêu thì không lập được – không có chỉ tiêu thì không đánh giá được
  M2 mục tiêu "bán tour cụ thể" phải chọn sản phẩm, nếu không thì không quy được doanh thu
  M3 đề xuất do AI lập LUÔN dừng ở nháp và phải ghi căn cứ
  M4 người lập không tự duyệt chiến dịch của chính mình
  M5 không nhảy cóc trạng thái
  M6 kết thúc mà chưa ghi đánh giá thì không đóng được
  M7 chi phí và doanh thu ĐỌC từ đề nghị chi và booking, không có ô nào cho người gõ
  M8 gán lead cũ không đè lên lead đã thuộc chiến dịch khác
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_chiendich.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_chiendich.db"): os.remove("test_chiendich.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


BASE = {"name": "Tết 2026 – Miền Bắc", "objective": "ra_lead", "mang": "le",
        "channels": ["facebook", "zalo"], "from_date": str(date.today()),
        "budget": 50_000_000, "target_leads": 400, "target_bookings": 40}


def test_m1_khong_co_chi_tieu_thi_khong_lap_duoc():
    mk = login("cntt")
    xau = dict(BASE, target_leads=0, target_bookings=0)
    r = client.post("/api/v1/marketing/campaigns", json=xau, headers=mk)
    assert r.status_code == 422 and "chỉ tiêu" in r.json()["detail"]
    assert client.post("/api/v1/marketing/campaigns", json=dict(BASE, channels=[]), headers=mk).status_code == 422
    assert client.post("/api/v1/marketing/campaigns", json=dict(BASE, budget=0), headers=mk).status_code == 422


def test_m2_ban_tour_cu_the_phai_chon_san_pham():
    mk = login("cntt")
    r = client.post("/api/v1/marketing/campaigns", json=dict(BASE, objective="ban_tour"), headers=mk)
    assert r.status_code == 422 and "sản phẩm" in r.json()["detail"]


def test_m3_de_xuat_do_ai_luon_dung_o_nhap_va_phai_ghi_can_cu():
    mk = login("cntt")
    assert client.post("/api/v1/marketing/campaigns",
                       json=dict(BASE, name="AI đề xuất – Hè 2026", nguon_tao="ai"), headers=mk).status_code == 422
    r = client.post("/api/v1/marketing/campaigns",
                    json=dict(BASE, name="AI đề xuất – Hè 2026", nguon_tao="ai",
                              ai_ghi_chu="Dựa trên 3 kỳ gần nhất: chi phí/lead kênh Zalo thấp hơn Facebook 32%"),
                    headers=mk).json()
    c = r["campaign"]
    assert c["status"] == "nhap" and c["nguon_tao"] == "ai"
    assert "cần người có thẩm quyền" in r["message"]
    CTX["ai_id"] = c["id"]


def test_m4_nguoi_lap_khong_tu_duyet_chien_dich_cua_minh():
    # cntt lập → cntt không đưa vào chạy được; và cntt cũng không thuộc nhóm có quyền duyệt
    c = client.post("/api/v1/marketing/campaigns", json=BASE, headers=login("cntt")).json()["campaign"]
    CTX["id"] = c["id"]
    client.post(f"/api/v1/marketing/campaigns/{c['id']}/chuyen-trang-thai", json={"status": "cho_duyet"}, headers=login("cntt"))
    r = client.post(f"/api/v1/marketing/campaigns/{c['id']}/chuyen-trang-thai", json={"status": "dang_chay"}, headers=login("cntt"))
    assert r.status_code == 403
    r2 = client.post(f"/api/v1/marketing/campaigns/{c['id']}/chuyen-trang-thai", json={"status": "dang_chay"}, headers=login("tgd"))
    assert r2.status_code == 200 and r2.json()["campaign"]["approved_by"] == "tgd"


def test_m5_khong_nhay_coc_trang_thai():
    cid = CTX["ai_id"]
    r = client.post(f"/api/v1/marketing/campaigns/{cid}/chuyen-trang-thai", json={"status": "ket_thuc"}, headers=login("tgd"))
    assert r.status_code == 422 and "Không chuyển thẳng" in r.json()["detail"]


def test_m6_ket_thuc_ma_chua_danh_gia_thi_khong_dong_duoc():
    cid = CTX["id"]
    assert client.post(f"/api/v1/marketing/campaigns/{cid}/chuyen-trang-thai", json={"status": "ket_thuc"}, headers=login("tgd")).status_code == 200
    r = client.post(f"/api/v1/marketing/campaigns/{cid}/chuyen-trang-thai", json={"status": "da_danh_gia"}, headers=login("tgd"))
    assert r.status_code == 422 and "đánh giá" in r.json()["detail"]
    ok = client.post(f"/api/v1/marketing/campaigns/{cid}/chuyen-trang-thai",
                     json={"status": "da_danh_gia", "danh_gia": "Zalo hiệu quả gấp đôi Facebook, kỳ sau dồn ngân sách"},
                     headers=login("tgd"))
    assert ok.status_code == 200 and ok.json()["campaign"]["evaluation"].startswith("Zalo")


def test_m7_chi_phi_va_doanh_thu_doc_tu_chung_tu_khong_ai_go_tay():
    from app.db.session import SessionLocal
    from app.models.crm import Lead
    from app.models.ops import PaymentRequest
    from app.models.core import Booking
    from sqlalchemy import select
    cid = CTX["id"]
    db = SessionLocal()
    bk = db.execute(select(Booking).where(Booking.cancelled == False)).scalars().first()
    db.add(Lead(phone="0900000001", name="Khách A", channel="Facebook", lead_month="2026-09",
                campaign_id=cid, booking_id=bk.id))
    db.add(Lead(phone="0900000002", name="Khách B", channel="Zalo", lead_month="2026-09", campaign_id=cid))
    db.add(PaymentRequest(code="DCTEST-01", category="marketing", campaign_id=cid, supplier_name="Meta",
                          amount=10_000_000, description="Quảng cáo", status="da_chi", created_by="cntt"))
    db.add(PaymentRequest(code="DCTEST-02", category="marketing", campaign_id=cid, supplier_name="Zalo",
                          amount=4_000_000, description="Tin nhắn ZNS", status="cho_kt", created_by="cntt"))
    db.commit(); doanh_thu_bk = bk.amount - bk.discount; db.close()

    k = client.get(f"/api/v1/marketing/campaigns/{cid}", headers=login("ptgd.mkt")).json()["ket_qua"]
    assert k["so_lead"] == 2 and k["chuyen_doi"] == 1 and k["ty_le_chuyen_doi"] == 0.5
    assert k["chi_phi"] == 10_000_000 and k["chi_phi_treo"] == 4_000_000      # đang treo tách riêng
    assert k["con_lai_ngan_sach"] == 50_000_000 - 14_000_000
    assert k["chi_phi_moi_lead"] == 5_000_000 and k["chi_phi_moi_booking"] == 10_000_000
    assert k["doanh_thu"] == doanh_thu_bk
    assert k["dat_chi_tieu_lead"] is False and k["vuot_ngan_sach"] is False
    # không có đường nào để người dùng tự ghi chi phí hay doanh thu
    r = client.put(f"/api/v1/marketing/campaigns/{cid}", json={"chi_phi": 999}, headers=login("cntt"))
    assert client.get(f"/api/v1/marketing/campaigns/{cid}", headers=login("ptgd.mkt")).json()["ket_qua"]["chi_phi"] == 10_000_000


def test_m8_gan_lead_cu_khong_de_len_lead_da_thuoc_chien_dich_khac():
    from app.db.session import SessionLocal
    from app.models.crm import Lead
    from sqlalchemy import select
    db = SessionLocal()
    db.add(Lead(phone="0900000003", name="Khách C", channel="Facebook", lead_month="2026-09", campaign="tet2026"))
    db.add(Lead(phone="0900000004", name="Khách D", channel="Facebook", lead_month="2026-09", campaign="tet2026"))
    db.commit(); db.close()
    moi = client.post("/api/v1/marketing/campaigns", json=dict(BASE, name="Chiến dịch nhận lead cũ"),
                      headers=login("cntt")).json()["campaign"]
    chua = client.get("/api/v1/marketing/campaigns/lead-chua-gan", headers=login("cntt")).json()
    assert any(n["campaign_cu"] == "tet2026" and n["so_lead"] == 2 for n in chua["nhom"])
    r = client.post(f"/api/v1/marketing/campaigns/{moi['id']}/gan-lead",
                    json={"campaign_cu": "tet2026"}, headers=login("cntt")).json()
    assert r["da_gan"] == 2
    # chạy lại: không gán thêm lần nữa, và lead của chiến dịch cũ không bị kéo sang
    assert client.post(f"/api/v1/marketing/campaigns/{moi['id']}/gan-lead",
                       json={"campaign_cu": "tet2026"}, headers=login("cntt")).json()["da_gan"] == 0
    assert client.get(f"/api/v1/marketing/campaigns/{CTX['id']}", headers=login("cntt")).json()["ket_qua"]["so_lead"] == 2


def test_m9_vai_tro_ngoai_marketing_khong_lap_duoc():
    assert client.post("/api/v1/marketing/campaigns", json=BASE, headers=login("hcns")).status_code == 403
    assert client.get("/api/v1/marketing/campaigns", headers=login("hcns")).status_code == 403
    assert client.get("/api/v1/marketing/campaigns", headers=login("ptgd.mkt")).status_code == 200
