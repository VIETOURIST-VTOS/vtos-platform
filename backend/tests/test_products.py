"""Sản phẩm tour, mở chuyến từ sản phẩm (dự toán tự sinh), chi tiết tour theo tab, lịch sử quy trình có ghi chú."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_products.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_products.db"): os.remove("test_products.db")
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


PROD = {"code": "PT001", "name": "PHAN THIẾT BIỂN XANH 3N2Đ", "tour_type": "le_noi_dia", "transport": "Xe", "vehicle_type": "45", "length_text": "3N2Đ", "days": 3, "reference_price": 1990000, "deposit_pct": 30, "days_to_close": 3,
        "cost_structure": {"bao_hiem": 5000, "qua_tang": 20000},
        "cost_lines": [{"loai": "GUIDE", "ncc": "HDV", "kind": "co_dinh", "mo_ta": "Hướng dẫn viên", "don_gia": 500000, "sl": 3, "so_tien": 1500000},
                       {"loai": "BUS", "ncc": "Xe 45", "kind": "co_dinh", "mo_ta": "Xe", "don_gia": 9000000, "sl": 1, "so_tien": 9000000},
                       {"loai": "HOTEL", "ncc": "Novela", "kind": "theo_khach", "mo_ta": "Resort 2 đêm", "don_gia": 600000, "sl": 1},
                       {"loai": "MEAL", "ncc": "NH", "kind": "theo_khach", "mo_ta": "Ăn", "don_gia": 300000, "sl": 1}]}


def test_product_crud_and_open_tour():
    h = login("dh.lan")
    assert client.post("/api/v1/products", json=PROD, headers=login("kd.hoa")).status_code == 403
    r = client.post("/api/v1/products", json=PROD, headers=h); assert r.status_code == 201, r.text
    p = r.json(); assert p["fixed_cost"] == 10500000 and p["var_cost_per_pax"] == 900000
    start = date.today() + timedelta(days=30)
    # Phép thử này về sau mở lịch lặp THỨ BẢY từ chính ngày `start`. Nếu `start` rơi đúng thứ Bảy thì
    # chuyến lặp đầu tiên trùng ngày với chuyến đơn đã mở, hậu tố _2 bị dùng mất, và chuyến trùng thứ
    # ba nhận _3 – phép thử đỏ dù mã chạy đúng. Ngày 10/9/2026 đúng vào cảnh đó (10/10/2026 là thứ Bảy)
    # và nó đỏ trên CẢ main. Dời một ngày để phép thử không còn phụ thuộc HÔM NAY là thứ mấy; cửa sổ 28
    # ngày vẫn chứa đúng 4 thứ Bảy nên phần dưới không đổi.
    if start.weekday() == 5:
        start += timedelta(days=1)
    r = client.post(f"/api/v1/products/{p['id']}/open-tour", json={"start_date": str(start), "seats": 40, "note": "Mở theo lịch tuần"}, headers=h); assert r.status_code == 201, r.text
    tid = r.json()["tours"][0]["id"]; code = r.json()["tours"][0]["code"]
    assert code == f"PT001.03{start:%d%m%y}"
    d = client.get(f"/api/v1/tours/{tid}/detail", headers=h).json()
    assert d["fixed_cost"] == 10500000 and d["var_cost_per_pax"] == 900000 and d["price_per_pax"] == 1990000 and d["planned_pax"] == 40 and str(d["end_date"]) == str(start + timedelta(days=2))
    assert d["product"]["code"] == "PT001" and d["seats"]["open"] == 40 and d["events"][0]["step"] == "khoi_tao" and "Mở theo lịch tuần" in d["events"][0]["note"]
    assert d["calc"]["margin"] > 0.10
    # lịch lặp: 4 chuyến thứ Bảy trong 4 tuần
    r = client.post(f"/api/v1/products/{p['id']}/open-tour", json={"start_date": str(start), "date_to": str(start + timedelta(days=27)), "weekdays": [5], "seats": 40}, headers=h)
    assert r.status_code == 201 and len(r.json()["tours"]) == 4
    # trùng ngày → hậu tố _2
    r2 = client.post(f"/api/v1/products/{p['id']}/open-tour", json={"start_date": str(start), "seats": 20}, headers=h); assert r2.json()["tours"][0]["code"].endswith("_2")
    pr = client.get(f"/api/v1/products/{p['id']}", headers=h).json(); assert len(pr["tours"]) == 6
    assert client.get("/api/v1/products?q=phan", headers=h).json()[0]["n_tours"] == 6


def test_workflow_events_with_notes():
    h = login("dh.lan")
    t = next(x for x in client.get("/api/v1/tours?q=PT001", headers=h).json()["rows"] if x["status"] == "nhap")
    client.put(f"/api/v1/tours/{t['id']}", json={"price_per_pax": 1990000, "fixed_cost": 10500000, "var_cost_per_pax": 900000, "planned_pax": 40, "rest_stops": "Trạm dừng Long Thành", "justification": ""}, headers=h)
    assert client.post(f"/api/v1/tours/{t['id']}/submit", json={"note": "Tour tuần, dự kiến đủ khách"}, headers=h).status_code == 200
    assert client.post(f"/api/v1/tours/{t['id']}/confirm", json={"note": "TP đã kiểm tra NCC"}, headers=login("tp.dieuhanh")).status_code == 200
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json()
    steps = [(e["step"], e["note"]) for e in d["events"]]
    assert ("tp_xac_nhan", "TP đã kiểm tra NCC") in steps and ("trinh_du_toan", "Tour tuần, dự kiến đủ khách") in steps and steps[-1][0] == "khoi_tao"
    # cũ: submit không body vẫn chạy
    lst = client.get("/api/v1/tours?limit=2", headers=h).json()["rows"]; assert len(lst) == 2
    assert client.get(f"/api/v1/tours?month={date.today() + timedelta(days=30):%Y-%m}", headers=h).status_code == 200


def test_vietrip_product_sync_links_tours():
    h = login("cntt")
    raw = {"id": 188, "ProductCode": "AU002", "ProductName": "MONO SYDNEY 5N4Đ", "TourType": "Quốc tế", "DeparturePoint": "TP HCM", "Transportation": "Máy bay", "VehicleType": "29", "TourLength": "5N4Đ", "Duration": "5",
           "ReferencePrice": "28,990,000", "DepositPercentage": "50", "DaysToCloseTour": "0", "RequiresConfirmation": "true", "Flight": "12,000,000", "Land": "9,000,000", "Insurance": "150,000",
           "cost_lines": [{"loai": "LAND", "ncc": "ABC (0301234567)", "kind": "PerPassenger", "mo_ta": "Landtour", "don_gia": "9,000,000", "sl": "1"}], "PriceInfoText": "Ngày 1: HCM – Sydney…", "NVDH_name": "NGUYỄN THỊ LAN"}
    tour = {"recID": 9001, "tourcode": "AU002.05011026", "ngayKhoiHanh": "2026-10-01T00:00:00", "ngayKetThuc": "2026-10-05T00:00:00", "soChoMoBan": 20, "loaiTour": "TOURLE", "nuoc": "Úc", "fstUser": "NGUYỄN THỊ LAN", "adl": 28990000, "tenSanPham": "MONO SYDNEY 5N4Đ", "soNgay": 5}
    assert client.post("/api/v1/import/vietrip/product", json={"rows": [raw]}, headers=h).status_code == 200
    assert client.post("/api/v1/import/vietrip/tour", json={"rows": [tour]}, headers=h).status_code == 200
    res = client.post("/api/v1/import/vietrip/apply?limit=50", headers=h).json()["applied"]; assert res["products"] == 1 and res["tours"] == 1
    p = client.get("/api/v1/products?q=AU002", headers=h).json()[0]
    assert p["reference_price"] == 28990000 and p["tour_type"] == "le_nuoc_ngoai" and p["cost_structure"]["ve_may_bay"] == 12000000 and p["cost_lines"][0]["kind"] == "theo_khach" and p["operator_name"].upper() == "NGUYỄN THỊ LAN" and p["n_tours"] == 1
    t = next(x for x in client.get("/api/v1/tours?q=AU002", headers=h).json()["rows"])
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json(); assert d["product"]["code"] == "AU002"
    # lịch sử quyết toán Vietrip → tour_events nguồn vietrip
    sett = {"tourId": 9001, "tourcode": "AU002.05011026", "tong_thu": 0, "tong_chi": 0, "lines": [], "step": "Bước 5: Lập Quyết toán Tour",
            "history": [{"title": "Phê duyệt dự toán thành công", "actor": "NGUYỄN DƯƠNG TRUNG HIẾU", "at": "2026-09-05T13:03:00", "note": ""}, {"title": "Đề nghị phê duyệt dự toán", "actor": "BẢO TRÂM", "at": "2026-09-05T12:02:00", "note": "Khách ít, biên thấp, nhờ anh duyệt"}]}
    client.post("/api/v1/import/vietrip/settlement", json={"rows": [sett]}, headers=h); client.post("/api/v1/import/vietrip/apply?limit=50", headers=h)
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json()
    vt = [e for e in d["events"] if e["source"] == "vietrip"]; assert len(vt) == 2 and vt[0]["title"].startswith("Phê duyệt") and "biên thấp" in vt[1]["note"]
