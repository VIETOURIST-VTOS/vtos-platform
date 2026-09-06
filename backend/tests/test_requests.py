"""Trang yêu cầu đặt dịch vụ (sửa lỗi B4/B5/B8 – Ý kiến thẩm định 06/9/2026):
- mỗi yêu cầu trả về người phụ trách, hạn xử lý, góc nhìn và bước tiếp theo (không chỉ thời gian chờ);
- danh sách vai trò được gửi yêu cầu là nguồn duy nhất ở máy chủ, có đủ trưởng nhóm và trưởng phòng Kinh doanh;
- booking nhập từ hệ thống khác không có mốc tiếp nhận → sla_known = False ("Chưa đủ dữ liệu"), không phải 0 phút.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_requests.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_requests.db"): os.remove("test_requests.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import access as AC

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def tour(code):
    return next(t for t in client.get("/api/v1/tours", headers=login("cntt")).json() if t["code"] == code)


def test_vai_tro_gui_yeu_cau_du_khoi_kinh_doanh():
    """Lỗi B5: giao diện thiếu tn_kd và tp_kd trong khi máy chủ cho phép → 6 người không gửi được yêu cầu."""
    for role in ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_dh", "tp_dh"):
        assert role in AC.REQUEST_CREATE_ROLES, f"{role} phải được gửi yêu cầu đặt dịch vụ"
    for role in ("ketoan", "hcns", "bks", "nv_mkt"):
        assert role not in AC.REQUEST_CREATE_ROLES


def test_auth_me_tra_ve_quyen_cho_giao_dien():
    """Giao diện lấy quyền từ máy chủ, không dựng lại danh sách vai trò (nguồn lệch)."""
    me_kd = client.get("/api/v1/auth/me", headers=login("kd.hoa")).json()
    assert me_kd["can_create_request"] is True and me_kd["can_create_booking"] is False
    me_dh = client.get("/api/v1/auth/me", headers=login("dh.lan")).json()
    assert me_dh["can_create_request"] is True and me_dh["can_create_booking"] is True
    me_tgd = client.get("/api/v1/auth/me", headers=login("tgd")).json()
    assert me_tgd["can_create_request"] is False, "TGĐ không gửi yêu cầu – giao diện phải ẩn hẳn khung tạo"
    assert me_tgd["can_create_booking"] is False


def test_yeu_cau_co_nguoi_phu_trach_han_xu_ly_va_buoc_tiep_theo():
    t = tour("PT-DL-0912")
    r = client.post("/api/v1/requests", json={"tour_id": t["id"], "customer_name": "Đỗ Thị Mai", "customer_phone": "0912345678",
                                             "source": "Zalo", "care_note": "khách quen", "pax": 2}, headers=login("kd.hoa"))
    assert r.status_code == 201, r.text
    rid = r.json()["request"]["id"]
    row = next(x for x in client.get("/api/v1/requests", headers=login("dh.lan")).json() if x["id"] == rid)
    assert row["operator_name"], "yêu cầu phải có người chịu trách nhiệm nhận việc"
    assert row["deadline"] and row["sla_minutes"] == 120
    assert row["view"] == "cho_phan_cong" and row["sla_state"] == "cho_phan_cong"
    assert "tạo booking" in row["next_step"].lower()
    assert row["amount"] == t["price_per_pax"] * 2      # giá trị booking, không phải cột "Tiền" chung chung
    assert row["tour_start"] and row["sales_id"]

    # tạo booking → chuyển góc nhìn Hoàn tất, bước tiếp theo ghi mã booking
    b = client.post(f"/api/v1/requests/{rid}/booking", headers=login("dh.lan"))
    assert b.status_code == 201, b.text
    code = b.json()["booking"]["code"]
    row = next(x for x in client.get("/api/v1/requests", headers=login("dh.lan")).json() if x["id"] == rid)
    assert row["view"] == "hoan_tat" and row["booking_code"] == code and code in row["next_step"]


def test_loc_theo_goc_nhin():
    rows_all = client.get("/api/v1/requests", headers=login("dh.lan")).json()
    done = client.get("/api/v1/requests?view=hoan_tat", headers=login("dh.lan")).json()
    assert done and all(x["view"] == "hoan_tat" for x in done)
    assert len(done) <= len(rows_all)
    mine = client.get("/api/v1/requests?view=cua_toi", headers=login("kd.hoa")).json()
    assert all(x["sales_id"] is not None for x in mine)


def test_sla_booking_nhap_tu_he_thong_khac_ghi_chua_du_du_lieu():
    """Lỗi B8: booking Vietrip có sla_minutes = 0 và sla_ok = True → không được hiển thị là xử lý trong 0 phút."""
    from app.db.session import SessionLocal
    from app.models.core import Booking
    db = SessionLocal()
    b = db.query(Booking).first()
    assert b is not None
    vt = Booking(code="VT999999", tour_id=b.tour_id, request_id=0, sales_id=b.sales_id, created_by=b.created_by,
                 customer_name="Khách Vietrip", customer_phone="0900000000", source="Vietrip", pax=2, amount=1_000_000,
                 sla_minutes=0, sla_ok=True, vietrip_id=999999)
    db.add(vt); db.commit(); db.close()
    rows = client.get("/api/v1/bookings?limit=300", headers=login("cntt")).json()
    imported = next(x for x in rows if x["code"] == "VT999999")
    assert imported["sla_known"] is False, "booking nhập từ Vietrip phải ghi Chưa đủ dữ liệu"
    vtos = next(x for x in rows if x["code"].startswith("BK"))
    assert vtos["sla_known"] is True
