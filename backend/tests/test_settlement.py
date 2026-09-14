"""Quyết toán tour soạn trên VTOS: dòng NCC (kiểm tra nhập, cách tính), chứng từ, khớp đã thanh toán với lệnh chi/tạm ứng, đóng số lấy tổng dòng, Kế toán trả lại → V.02, hoàn ứng 141→154."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_settlement.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_settlement.db"): os.remove("test_settlement.db")
import pytest
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


def tour(code):
    return next(t for t in client.get("/api/v1/tours", headers=login("dh.lan")).json()["rows"] if t["code"] == code)


def pay_request(cat, tid, ncc, mst, amount, desc):
    r = client.post("/api/v1/payment-requests", json={"category": cat, "tour_id": tid, "supplier_name": ncc, "supplier_tax_code": mst, "amount": amount, "description": desc, "has_document": True, "has_invoice": cat != "tam_ung"}, headers=login("dh.lan"))
    assert r.status_code == 201, r.text
    rid = r.json()["request"]["id"]
    for a, w in (("confirm", "tp.dieuhanh"), ("check", "ketoan"), ("approve", "tgd"), ("pay", "ketoan")):
        x = client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": a, "reason": "CK 123" if a == "pay" else ""}, headers=login(w)); assert x.status_code == 200, x.text
    return rid


def test_lines_validation_and_calc():
    t = tour("DN-HCM-0820"); h = login("dh.lan"); base = f"/api/v1/tours/{t['id']}/settlement"
    # chỉ người điều hành chuyến
    assert client.post(f"{base}/lines", json={"description": "HDV", "supplier_name": "X", "unit_price": 1}, headers=login("dh.minh")).json()["detail"]["gate"] == "CONG_6"
    # kiểm tra nhập như Vietrip
    assert client.post(f"{base}/lines", json={"description": "", "supplier_name": "X"}, headers=h).status_code == 422
    assert "Nhà cung cấp" in client.post(f"{base}/lines", json={"description": "HDV", "supplier_name": ""}, headers=h).json()["detail"]["message"]
    assert "Pax" in client.post(f"{base}/lines", json={"description": "KS", "supplier_name": "KS", "cost_kind": "theo_khach", "unit_price": 100, "qty": 0}, headers=h).json()["detail"]["message"]
    assert "âm" in client.post(f"{base}/lines", json={"description": "KS", "supplier_name": "KS", "unit_price": -1}, headers=h).json()["detail"]["message"]
    # cố định: đơn giá × hệ số; theo khách: đơn giá × pax × hệ số
    l1 = client.post(f"{base}/lines", json={"description": "HƯỚNG DẪN VIÊN", "service_type": "GUIDE", "cost_kind": "co_dinh", "supplier_name": "NGUYỄN TẤT THẮNG", "unit_price": 350000, "qty": 45, "coef": 3, "budget": 1050000}, headers=h).json()
    assert l1["actual"] == 1050000 and l1["line_no"] == 1 and l1["version"] == 1
    l2 = client.post(f"{base}/lines", json={"description": "KS ĐÀ NẴNG 2 ĐÊM", "service_type": "HOTEL", "cost_kind": "theo_khach", "supplier_name": "KS Đà Nẵng", "supplier_tax_code": "0400", "unit_price": 1200000, "qty": 45, "coef": 1, "budget": 54000000}, headers=h).json()
    assert l2["actual"] == 54000000
    l3 = client.post(f"{base}/lines", json={"description": "XE 45 CHỖ", "service_type": "VEHICLE", "cost_dinh": 1, "supplier_name": "CÔNG TY TNHH VẬN TẢI VIETRIP", "supplier_tax_code": "0317478116", "unit_price": 30000000, "qty": 45, "coef": 1, "budget": 20000000}, headers=h).json()
    # vượt dự toán 50% không giải trình → chặn đóng số
    s = client.get(base, headers=h).json()
    assert s["summary"]["actual"] == 85050000 and s["summary"]["lines"] == 3 and s["can_edit"] is True
    assert any(c["level"] == "block" and c["line"] == 3 for c in s["checks"])
    r = client.post(f"/api/v1/tours/{t['id']}/close", json={"actual_revenue": 189000000, "actual_cost": 0}, headers=h); assert r.status_code == 422 and r.json()["detail"]["gate"] == "QT_NHAP"
    # sửa dòng có ghi chú giải trình
    l3 = client.put(f"{base}/lines/{l3['id']}", json={**{k: l3[k] for k in ("description", "service_type", "cost_kind", "supplier_name", "supplier_tax_code", "unit_price", "qty", "coef", "budget")}, "note": "Đổi xe 45 sang 2 xe 29 do đường đèo"}, headers=h).json()
    assert l3["source"] == "vtos" and not any(c["level"] == "block" for c in client.get(base, headers=h).json()["checks"])
    # chứng từ theo dòng
    assert client.post(f"{base}/lines/{l2['id']}/doc", json={"name": "hoadon-ks.png", "data": "data:image/png;base64,iVBORw0KGgo="}, headers=h).status_code == 200
    assert client.post(f"{base}/lines/{l2['id']}/doc", json={"name": "x.txt", "data": "data:text/plain;base64,QQ=="}, headers=h).status_code == 422
    d = client.get(f"{base}/lines/{l2['id']}/doc", headers=login("ketoan")); assert d.status_code == 200 and d.headers["content-type"].startswith("image/png")
    # hủy dòng phải có lý do
    l4 = client.post(f"{base}/lines", json={"description": "NƯỚC SUỐI", "service_type": "GIFT", "supplier_name": "Lavie", "unit_price": 500000}, headers=h).json()
    assert client.post(f"{base}/lines/{l4['id']}/cancel", json={"note": ""}, headers=h).status_code == 422
    assert client.post(f"{base}/lines/{l4['id']}/cancel", json={"note": "Nhập trùng"}, headers=h).status_code == 200
    s = client.get(base, headers=h).json(); assert s["summary"]["lines"] == 3 and s["summary"]["cancelled"] == 1 and s["summary"]["with_doc"] == 1


def test_match_paid_close_return_and_advance_posting():
    t = tour("DN-HCM-0820"); h = login("dh.lan"); base = f"/api/v1/tours/{t['id']}/settlement"
    # lệnh chi NCC (MST) + tạm ứng HDV (trùng tên) đã chi
    pay_request("chi_tour", t["id"], "KS Đà Nẵng", "0400", 54000000, "Phòng đoàn")
    pay_request("tam_ung", t["id"], "Nguyễn Tất Thắng", "", 1000000, "Tạm ứng HDV")
    m = client.post(f"{base}/match-paid", headers=h).json(); assert m["matched"] == 2 and m["unmatched"] == 1
    ls = {l["description"]: l for l in client.get(base, headers=h).json()["lines"]}
    assert ls["KS ĐÀ NẴNG 2 ĐÊM"]["paid"] == 54000000 and ls["HƯỚNG DẪN VIÊN"]["paid"] == 1000000 and ls["HƯỚNG DẪN VIÊN"]["remaining"] == 50000
    # đóng số: giá vốn = tổng dòng (bỏ qua số nhập tay), lịch sử ghi phiên bản
    r = client.post(f"/api/v1/tours/{t['id']}/close", json={"actual_revenue": 189000000, "actual_cost": 1, "note": "Đoàn 45 khách"}, headers=h); assert r.status_code == 200, r.text
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json()
    assert d["actual_cost"] == 85050000 and d["status"] == "da_dong_so" and "V.01" in d["events"][0]["note"] and d["settlement_edit"]["can_edit"] is False
    assert client.post(f"{base}/lines", json={"description": "Thêm sau đóng số", "supplier_name": "X", "unit_price": 1}, headers=h).json()["detail"]["gate"] == "TRANG_THAI"
    # Kế toán trả lại → V.02, Điều hành sửa được
    assert client.post(f"/api/v1/tours/{t['id']}/kt-return", json={"note": ""}, headers=login("ketoan")).status_code == 422
    assert "V.02" in client.post(f"/api/v1/tours/{t['id']}/kt-return", json={"note": "Thiếu hóa đơn xe"}, headers=login("ketoan")).json()["message"]
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json(); assert d["status"] == "ket_thuc" and d["settlement_edit"]["version"] == 2 and d["events"][0]["step"] == "kt_tra_lai"
    l5 = client.post(f"{base}/lines", json={"description": "BẢO HIỂM", "service_type": "INSURANCE", "cost_kind": "theo_khach", "supplier_name": "BH Toàn Cầu", "unit_price": 5000, "qty": 45}, headers=h).json(); assert l5["version"] == 2
    assert client.post(f"/api/v1/tours/{t['id']}/close", json={"actual_revenue": 189000000, "actual_cost": 0}, headers=h).status_code == 200
    assert client.post(f"/api/v1/tours/{t['id']}/kt-confirm", json={"note": "Đủ chứng từ"}, headers=login("ketoan")).status_code == 200
    d = client.get(f"/api/v1/tours/{t['id']}/detail", headers=h).json(); assert d["actual_cost"] == 85275000
    es = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == "tour:DN-HCM-0820"]
    pairs = {(l["account"], l["debit"], l["credit"]) for e in es for l in e["lines"]}
    # hoàn ứng 141 → 154; phần chưa có lệnh chi (85.275.000 − 54.000.000 − 1.000.000) trích 335; kết chuyển 632
    assert ("154", 1000000, 0) in pairs and ("141", 0, 1000000) in pairs and ("335", 0, 30275000) in pairs and ("632", 85275000, 0) in pairs
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
