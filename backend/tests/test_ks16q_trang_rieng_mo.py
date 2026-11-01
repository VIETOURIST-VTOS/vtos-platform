# -*- coding: utf-8 -*-
"""KS-16q · Ba trang riêng kh.vietourist.vn/hotel, /restaurant, /tours (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Khách CHƯA đăng nhập XEM được: tìm / chi tiết / đánh giá khách sạn, danh sách / chi tiết tour, nhà hàng.
  2. Mọi việc đặt, gửi yêu cầu, tính giá đặt, đơn của tôi vẫn đòi phiên cổng (401 khi không có phiên).
  3. Router /cong/mo chỉ có GET; không trả điểm VTD Rewards; khách sạn chưa đặt được trỏ /hotel.
"""
from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import k3  # noqa: F401


def test_xem_khong_dang_nhap_dat_phai_dang_nhap(db, k3):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.api.v1 import cong_mo as M
    k, lp, g = k3
    app.dependency_overrides[get_db] = lambda: db
    M._LUOT.clear()
    try:
        c = TestClient(app)
        p = {"tinh": "Đà Nẵng", "vao": VAO.isoformat(), "ra": RA.isoformat()}
        r = c.get("/api/v1/cong/mo/ks-vtd/tim", params=p)
        assert r.status_code == 200 and [x["id"] for x in r.json()["khach_san"]] == [k.id]
        assert r.json()["diem"]["dang_bat"] is False
        r = c.get(f"/api/v1/cong/mo/ks-vtd/{k.id}", params=p)
        assert r.status_code == 200 and r.json()["phong"][0]["goi"]
        assert c.get(f"/api/v1/cong/mo/ks-vtd/{k.id}/danh-gia").status_code == 200
        assert c.get("/api/v1/cong/mo/tour").status_code == 200
        assert c.get("/api/v1/cong/mo/nha-hang").status_code == 200
        assert c.get("/api/v1/cong/mo/ks-vtd/999999", params=p).status_code == 404
        # cửa cũ vẫn đòi phiên
        assert c.get("/api/v1/cong/ks-vtd/tim", params=p).status_code == 401
        chon = {"vao": VAO.isoformat(), "ra": RA.isoformat(), "chon": [{"goi_id": g.id, "so": 1}]}
        assert c.post(f"/api/v1/cong/ks-vtd/{k.id}/tinh", json=chon).status_code == 401
        assert c.post(f"/api/v1/cong/ks-vtd/don/dat/{k.id}", json={**chon, "ho_ten": "A B", "lien_he": "0901000001",
                                                                   "dong_y": True}).status_code == 401
        assert c.post(f"/api/v1/cong/ks-vtd/{k.id}/yeu-cau", json={"ngay_nhan": VAO.isoformat(),
                                                                   "ngay_tra": RA.isoformat()}).status_code == 401
        assert c.get("/api/v1/cong/ks-vtd/don").status_code == 401
        assert c.post("/api/v1/cong/khach/yeu-cau", json={"loai": "tour_doan"}).status_code == 401
        assert c.post("/api/v1/cong/dat-ban", json={}).status_code in (401, 422)
    finally:
        app.dependency_overrides.pop(get_db, None); M._LUOT.clear()


def test_router_mo_chi_co_get_va_co_phanh(db, k3):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.api.v1 import cong_mo as M
    pt = {m for r in app.routes if getattr(r, "path", "").startswith("/api/v1/cong/mo") for m in (r.methods or set())}
    assert pt and pt <= {"GET", "HEAD"}
    app.dependency_overrides[get_db] = lambda: db
    M._LUOT.clear()
    try:
        c = TestClient(app)
        M._LUOT["testclient"] = [__import__("time").time()] * M.TOI_DA_TRONG_CUA_SO
        assert c.get("/api/v1/cong/mo/tour").status_code == 429
    finally:
        app.dependency_overrides.pop(get_db, None); M._LUOT.clear()


def test_khach_san_chua_dat_duoc_tro_trang_rieng():
    from app.services import khach_san_vtd as S
    assert S.LINK_KS_NGOAI == "/hotel"
