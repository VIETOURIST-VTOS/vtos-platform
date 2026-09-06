"""Cổng biên và tách dự toán khỏi thực chi (B1, B2, B3, B7 – Ý kiến thẩm định 06/9/2026).

B1: giá vốn 0 từng cho biên 100% → cổng biên luôn "ĐẠT". Thiếu chi phí không phải là chi phí bằng 0.
B2: dự toán của tour nhập từ Vietrip từng được suy ngược từ dòng quyết toán → biên kế hoạch luôn bằng
    biên thực tế, cảnh báo vượt dự toán không bao giờ kích hoạt.
B3: đầu trang tour đang bán từng hiện "lợi nhuận ước" xấp xỉ toàn bộ doanh thu.
B7: tổng booking phải lấy từ truy vấn tổng, không lấy số dòng đang hiển thị.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_budget_gate.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_budget_gate.db"): os.remove("test_budget_gate.db")
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services import rules as R

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def new_tour(code, price=2_000_000, fixed=0, var=0, pax=20):
    d = date.today() + timedelta(days=30)
    r = client.post("/api/v1/tours", json={"code": code, "name": "Chuyến kiểm thử " + code, "tour_type": "le_noi_dia",
                                           "start_date": str(d), "end_date": str(d + timedelta(days=2)), "operator_id": 0,
                                           "price_per_pax": price, "fixed_cost": fixed, "var_cost_per_pax": var,
                                           "planned_pax": pax, "rest_stops": "Trạm dừng Tân Phú"}, headers=login("dh.lan"))
    assert r.status_code == 201, r.text
    return r.json()


def test_b1_gia_von_0_khong_duoc_bao_dat():
    """Giá vốn 0 → biên 100% → cổng từng báo ĐẠT. Nay phải là 'chưa đủ cơ sở tính'."""
    t = new_tour("KT-B1-0001", fixed=0, var=0)
    c = t["calc"]
    assert c["has_cost"] is False
    assert c["complete"] is False, "dự toán thiếu giá vốn không được coi là đủ ba con số"
    assert c["pass_gate"] is False, "cổng biên không được ĐẠT khi chưa có giá vốn"
    assert c["gate_state"] == "chua_du_co_so"
    assert c["budget_source"] == "chua_co"


def test_b1_khong_trinh_duyet_duoc_khi_thieu_gia_von():
    t = new_tour("KT-B1-0002", fixed=0, var=0)
    r = client.post(f"/api/v1/tours/{t['id']}/submit", json={"note": ""}, headers=login("dh.lan"))
    assert r.status_code == 422, r.text
    d = r.json()["detail"]
    assert d["gate"] == "CONG_5" and "chi phí" in d["message"].lower()


def test_b1_du_toan_du_gia_von_van_chay_binh_thuong():
    t = new_tour("KT-B1-0003", price=2_000_000, fixed=10_000_000, var=1_200_000, pax=20)
    c = t["calc"]
    assert c["complete"] is True and c["has_cost"] is True and c["budget_source"] == "du_toan_tour"
    assert c["gate_state"] in ("dat", "khong_dat")
    r = client.post(f"/api/v1/tours/{t['id']}/submit", json={"note": "ok"}, headers=login("dh.lan"))
    assert r.status_code == 200, r.text


def test_b2_du_toan_khong_suy_nguoc_tu_quyet_toan():
    """Nạp một tour Vietrip kèm dòng quyết toán: dự toán của chuyến phải KHÔNG bị đặt bằng số thực chi."""
    d = date.today() - timedelta(days=10)
    rows = [{"recID": 880001, "tourcode": "KT-B2-VT01", "tenSanPham": "Tour Vietrip kiểm thử", "loaiTour": "TOURLE",
             "ngayKhoiHanh": d.strftime("%Y-%m-%d"), "ngayKetThuc": (d + timedelta(days=2)).strftime("%Y-%m-%d"),
             "fstUser": "NGUYỄN THỊ LAN", "adl": 3_000_000, "chd": 0, "inf": 0, "soChoMoBan": 10,
             "quyetToan": True, "duyetChi": False, "doanhThu": 30_000_000, "tongChiPhi": 26_000_000, "nuoc": ""}]
    assert client.post("/api/v1/import/vietrip/tour", json={"rows": rows}, headers=login("cntt")).status_code == 200
    st = [{"tourId": 880001, "tourcode": "KT-B2-VT01", "tong_thu": 30_000_000, "tong_chi": 26_000_000,
           "lines": [{"mo_ta": "Khách sạn theo khách", "loai": "HOTEL", "ncc": "KS A", "don_gia": 1_500_000, "sl": 10, "hs": 1, "thuc_chi": 15_000_000, "da_tt": 0},
                     {"mo_ta": "Xe cố định", "loai": "VEHICLE", "ncc": "Đội xe", "don_gia": 11_000_000, "sl": 1, "hs": 1, "thuc_chi": 11_000_000, "da_tt": 0}]}]
    assert client.post("/api/v1/import/vietrip/settlement", json={"rows": st}, headers=login("cntt")).status_code == 200
    assert client.post("/api/v1/import/vietrip/apply", headers=login("cntt")).status_code == 200

    t = next(x for x in client.get("/api/v1/tours?limit=1000", headers=login("cntt")).json() if x["code"] == "KT-B2-VT01")
    assert t["fixed_cost"] == 0 and t["var_cost_per_pax"] == 0, "không được suy ngược dự toán từ dòng quyết toán"
    det = client.get(f"/api/v1/tours/{t['id']}/detail", headers=login("cntt")).json()
    assert det["settlement_edit"]["summary"]["actual"] == 26_000_000, "thực chi vẫn lấy đủ từ dòng quyết toán"
    assert det["settlement_edit"]["summary"]["has_budget"] is False
    assert det["calc"]["budget_source"] == "chua_co" and det["calc"]["complete"] is False
    checks = [c["msg"] for c in det["settlement_edit"]["checks"]]
    assert any("chưa có dự toán" in m.lower() for m in checks)


def test_b2_cong_cu_don_du_toan_suy_nguoc():
    r = client.post("/api/v1/import/vietrip/repair-budget", headers=login("cntt"))
    assert r.status_code == 200 and "tours" in r.json()


def test_b3_dau_trang_tour_ghi_ro_tam_tinh():
    t = new_tour("KT-B3-0001", price=2_000_000, fixed=10_000_000, var=1_200_000, pax=20)
    det = client.get(f"/api/v1/tours/{t['id']}/detail", headers=login("cntt")).json()
    sm = det["summary"]
    assert sm["profit_state"] == "tam_tinh"
    assert sm["cost_lines"] == 0 and sm["cost_basis"] == "chua_co"
    assert sm["warning"], "chuyến chưa có dòng chi phí phải hiện cảnh báo ngay cạnh chỉ tiêu"


def test_b7_tong_booking_lay_tu_truy_van_tong():
    c = client.get("/api/v1/bookings/count", headers=login("cntt")).json()
    assert c["total"] >= c["filtered"] >= 0
    một_dòng = client.get("/api/v1/bookings?limit=1", headers=login("cntt")).json()
    assert len(một_dòng) <= 1
    assert c["total"] >= len(một_dòng), "tổng không được suy từ số dòng đang hiển thị"
    trang2 = client.get("/api/v1/bookings?limit=1&offset=1", headers=login("cntt")).json()
    if c["total"] > 1:
        assert trang2 and trang2[0]["code"] != một_dòng[0]["code"], "phân trang phải trả trang khác nhau"
    loc = client.get("/api/v1/bookings/count?status=cancelled", headers=login("cntt")).json()
    assert loc["filtered"] <= loc["total"]


def test_b1_du_toan_tham_chieu_tu_san_pham_khong_mo_cong_bien():
    """Cơ cấu chi phí sản phẩm chỉ để tham chiếu: 21/313 mã có số và phần lớn sai (có mã ghi 11 đ/khách
    → biên 99,99%). Dùng nó mở cổng thì cổng lại bị vô hiệu hóa lần nữa."""
    from app.db.session import SessionLocal
    from app.models.core import Product, Tour
    from app.services import rules as R
    db = SessionLocal()
    p = Product(code="SP-KT-9001", name="Sản phẩm kiểm thử", reference_price=2_000_000,
                cost_structure={"xe": 11}, source="vtos")
    db.add(p); db.commit()
    t = db.execute(__import__("sqlalchemy").select(Tour).where(Tour.code == "KT-B1-0001")).scalars().first()
    t.product_code = "SP-KT-9001"; t.product_id = p.id; db.commit()
    f, v, src = R.budget_of(db, t)
    assert src == "san_pham" and v == 11
    c = R.calc_db(db, t, 0.10)
    assert c["reference_only"] is True
    assert c["margin"] > 0.9, "số tham chiếu cho biên rất cao – đúng là dữ liệu sản phẩm đang sai"
    assert c["complete"] is False and c["pass_gate"] is False, "tham chiếu không được mở cổng biên"
    assert c["gate_state"] == "chua_du_co_so"
    db.close()


def test_b3_tong_chi_phi_vietrip_khong_phai_gia_von_khi_chua_quyet_toan():
    """tour DL001.03130926 có tongChiPhi = 6.500 chính là phí bảo hiểm/khách, không phải giá vốn chuyến."""
    d = date.today() + timedelta(days=20)
    rows = [{"recID": 880002, "tourcode": "KT-B3-VT02", "tenSanPham": "Tour đang bán", "loaiTour": "TOURLE",
             "ngayKhoiHanh": d.strftime("%Y-%m-%d"), "ngayKetThuc": (d + timedelta(days=2)).strftime("%Y-%m-%d"),
             "fstUser": "NGUYỄN THỊ LAN", "adl": 1_290_000, "chd": 0, "inf": 0, "soChoMoBan": 44,
             "quyetToan": False, "duyetChi": False, "doanhThu": 0, "tongChiPhi": 6500, "baoHiem": 6500, "nuoc": ""}]
    assert client.post("/api/v1/import/vietrip/tour", json={"rows": rows}, headers=login("cntt")).status_code == 200
    assert client.post("/api/v1/import/vietrip/apply", headers=login("cntt")).status_code == 200
    t = next(x for x in client.get("/api/v1/tours?limit=1000", headers=login("cntt")).json() if x["code"] == "KT-B3-VT02")
    assert t["actual_cost"] == 0, "phí bảo hiểm 6.500 không được nhận là giá vốn chuyến"
    det = client.get(f"/api/v1/tours/{t['id']}/detail", headers=login("cntt")).json()
    assert det["summary"]["profit_state"] == "tam_tinh" and det["summary"]["warning"]
