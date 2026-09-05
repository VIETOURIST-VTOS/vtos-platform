"""Đồng bộ Vietrip: nạp thô idempotent, ánh xạ tour/booking/phiếu thu/chi NCC/user/xe/dòng chi phí."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vt.db"): os.remove("test_vt.db")
import pytest
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


TOUR = {"recID": 11775, "tourcode": "PT001.03060926", "ghiChu": "PHAN THIẾT BIỂN XANH", "ngayKhoiHanh": "2026-09-06T00:00:00", "ngayKetThuc": "2026-09-07T00:00:00", "soChoMoBan": 44, "soChoMoBan_KM": 0,
        "loaiTour": "TOURLE", "nuoc": "", "fstUser": "NGUYỄN THỊ LAN", "adl": 1990000, "chd": 1490000, "inf": 0, "adl_KM": 0, "quyetToan": True, "duyetChi": False, "doanhThu": 27240000, "tongChiPhi": 25790000,
        "tenSanPham": "PHAN THIẾT BIỂN XANH - Trong tuần", "soNgay": 2, "phuongTien": "Xe", "diemKhoiHanh": "HCM", "loaiXe": "45 chỗ"}
BOOK = {"recID": 125204, "tourcode": "PT001.03060926", "tenNguoiBook": "NGUYET THANH", "phone": "0903623012", "adl": 2, "chd": 0, "inf": 0, "totalDue": 3980000, "pmtStatus": "DEPO",
        "deadlineHuyCho": "2026-09-06T10:00:00", "fstUser": "VĂN THỊ TỐ UYÊN", "fstUpdate": "2026-09-05T14:25:00", "status": "OK"}
BOOK2 = {**BOOK, "recID": 125205, "status": "Đã huỷ", "tenNguoiBook": "HỦY"}
REC = {"RecID": 88400, "Tourcode": "PT001.03060926", "TenNguoiBook": "NGUYET THANH", "BookingID": "125204", "SoTien": 1690000, "NguoiThanhToan": "NGUYET THANH", "HinhThuc": "Chuyển khoản",
       "TaiKhoanCongTy": "NGÂN HÀNG TIÊN PHONG (TPB)", "FstUser": "VĂN THỊ TỐ UYÊN", "FstUpdate": "2026-09-05T14:19:00", "Status": "KC"}
SUP = {"RecID": 7032, "OrgID": 0, "FOP": "BTF", "Amount": 6998400, "Status": "KC", "FstUpdate": "2026-09-05T09:00:00", "MoTa": "ĂN TỐI NGÀY 2", "Tourcode": "PT001.03060926", "TenNCC": "NHÀ HÀNG BIỂN"}
SET = {"tourId": 11775, "tourcode": "PT001.03060926", "tong_thu": 27240000, "tong_chi": 25790000, "lines": [
    {"mo_ta": "HƯỚNG DẪN VIÊN | Cố định", "loai": "GUIDE", "ncc": "NGUYỄN TẤT THẮNG", "don_gia": 350000, "sl": 16, "hs": 3, "thuc_chi": 1050000, "da_tt": 0},
    {"mo_ta": "RESORT NOVELA | Theo khách", "loai": "HOTEL", "ncc": "CÔNG TY CP VIỆT GROUP (3401254663)", "don_gia": 600000, "sl": 16, "hs": 1, "thuc_chi": 9600000, "da_tt": 9600000}]}
USR = {"recID": 220, "phone": "0345675492", "hoTen": "BẠC CẦM DUY DI", "chucVu": "Nhân viên", "phongBan": "Kế toán", "email": "x@vietourist.com.vn"}
VEH = {"recID": 1, "licensePlate": "50F 017.37", "manufactureYear": 2019, "driverName": "Đoàn Hoàng Tuấn", "totalKm": 247889, "status": "OK", "lstUpdate": "2026-09-04T15:30:00"}


def test_ingest_idempotent_and_apply():
    h = login("cntt")
    assert client.post("/api/v1/import/vietrip/tour", json={"rows": [TOUR]}, headers=login("kd.hoa")).status_code == 403
    r = client.post("/api/v1/import/vietrip/tour", json={"rows": [TOUR]}, headers=h).json(); assert r["new"] == 1
    r = client.post("/api/v1/import/vietrip/tour", json={"rows": [TOUR]}, headers=h).json(); assert r["new"] == 0 and r["updated"] == 0
    for e, rows in (("booking", [BOOK, BOOK2]), ("receipt", [REC]), ("supplier_payment", [SUP]), ("settlement", [SET]), ("user", [USR]), ("vehicle", [VEH])):
        assert client.post(f"/api/v1/import/vietrip/{e}", json={"rows": rows}, headers=h).status_code == 200
    st = client.get("/api/v1/import/vietrip/status", headers=login("bks")).json()
    assert st["booking"]["total"] == 2 and st["tour"]["applied"] == 0
    res = client.post("/api/v1/import/vietrip/apply", headers=h).json()["applied"]
    assert res["tours"] == 1 and res["bookings"] == 2 and res["receipts"] == 1 and res["supplier_payments"] == 1 and res["users"] == 1 and res["vehicles"] == 1 and res["settlements"] == 1
    t = next(x for x in client.get("/api/v1/tours", headers=h).json() if x["code"] == "PT001.03060926")
    assert t["status"] == "kt_xac_nhan" and t["actual_revenue"] == 27240000 and t["tour_type"] == "le_noi_dia" and t["price_per_pax"] == 1990000
    cl = client.get(f"/api/v1/tours/{t['id']}/cost-lines", headers=h).json()
    assert len(cl["rows"]) == 2 and cl["rows"][1]["supplier_tax_code"] == "3401254663" and cl["rows"][1]["cost_kind"] == "theo_khach" and cl["total_actual"] == 10650000
    bk = {b["code"]: b for b in client.get("/api/v1/bookings", headers=h).json()}
    assert bk["VT125204"]["paid"] == 1690000 and bk["VT125204"]["pax"] == 2 and bk["VT125204"]["pmt_status"] == "DEPO"
    assert bk["VT125205"]["cancelled"] is True and bk["VT125205"]["amount"] == 0
    pr = next(x for x in client.get("/api/v1/payment-requests?status=da_chi", headers=h).json() if x["code"] == "VTDC7032")
    assert pr["tour_code"] == "PT001.03060926" and pr["supplier_name"] == "NHÀ HÀNG BIỂN"
    emps = client.get("/api/v1/employees", headers=login("hcns")).json()
    assert any(e["full_name"] == "BẠC CẦM DUY DI" and e["department"] == "ketoan" for e in emps) and any(e["full_name"] == "Đoàn Hoàng Tuấn" and e["position"] == "tai_xe" for e in emps)
    veh = client.get("/api/v1/vehicles", headers=login("hcns")).json()
    assert any(v["plate"] == "50F-017.37" and v["driver"] == "Đoàn Hoàng Tuấn" for v in veh)
    # chạy lại apply: không nhân bản
    res2 = client.post("/api/v1/import/vietrip/apply", headers=h).json()["applied"]
    assert res2["tours"] == 0 and len([b for b in client.get("/api/v1/bookings", headers=h).json() if b["code"] == "VT125204"]) == 1
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
