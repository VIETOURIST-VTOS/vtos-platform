"""KS-XH (07/11/2026) — khối xu hướng không tính lại tháng cũ mỗi lần dựng, mà số KHÔNG đổi.

Đo trên crm thật: dựng bảng 28 giây thì khối xu hướng 14 giây (hỏi trùng từng tháng, và 36 tháng
cũ tính lại mỗi vài phút). Phép thử canh bốn điều:
  1. số của hàm đọc dùng chung (`doc_cho_bang`) TRÙNG KHỚP số của cách cũ (`doc_that`);
  2. tháng đã đóng được nhớ qua lần dựng, tháng đang chạy thì không;
  3. ghi vào một bảng xu hướng đọc tới (ví dụ Tour) là xoá nhớ ngay — ghi bảng khác thì không;
  4. hai lần dựng không chạy chồng nhau; lần đến sau dùng luôn kết quả lần trước.
"""
import os, sys, threading, time
os.environ["DATABASE_URL"] = "sqlite:///./test_ks_xh.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks_xh.db"): os.remove("test_ks_xh.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def test_so_dung_chung_trung_khop_so_cach_cu():
    from app.services import xu_huong as XH
    XH.xoa_nho_thang_cu()
    db = _db(); hn = date.today()
    try:
        cu_1 = XH.cho_man_hinh(db, so_ky=6, hom_nay=hn)
        cu_2 = XH.ba_ky_cho_man_hinh(db, hom_nay=hn)
        d = XH.doc_cho_bang(db, hom_nay=hn)
        assert XH.cho_man_hinh(db, so_ky=6, hom_nay=hn, doc=d) == cu_1
        assert XH.ba_ky_cho_man_hinh(db, hom_nay=hn, doc=d) == cu_2
        # lần dựng sau lấy tháng cũ từ chỗ nhớ — số vẫn y hệt
        d2 = XH.doc_cho_bang(db, hom_nay=hn)
        assert XH.ba_ky_cho_man_hinh(db, hom_nay=hn, doc=d2) == cu_2
    finally:
        db.close()


def test_chi_nho_thang_da_dong():
    from app.services import xu_huong as XH
    XH.xoa_nho_thang_cu()
    db = _db(); hn = date.today()
    try:
        XH.ba_ky_cho_man_hinh(db, hom_nay=hn, doc=XH.doc_cho_bang(db, hom_nay=hn))
    finally:
        db.close()
    ky_nay = f"{hn.year:04d}-{hn.month:02d}"
    assert XH._NHO_THANG_CU, "tháng đã đóng phải được nhớ"
    assert all(ky < ky_nay for _, ky in XH._NHO_THANG_CU), "tháng đang chạy không được nhớ qua lần dựng"


def test_ghi_tour_xoa_nho_ghi_bang_khac_thi_khong():
    from app.services import xu_huong as XH
    from app.models.core import Tour, Alert
    from sqlalchemy import select
    db = _db(); hn = date.today()
    try:
        XH.ba_ky_cho_man_hinh(db, hom_nay=hn, doc=XH.doc_cho_bang(db, hom_nay=hn))
        assert XH._NHO_THANG_CU
        a = db.execute(select(Alert)).scalars().first()
        if a is not None:
            a.resolved = not a.resolved; db.flush()
            assert XH._NHO_THANG_CU, "ghi cảnh báo không đụng số xu hướng — không được xoá nhớ"
        t = db.execute(select(Tour)).scalars().first()
        t.name = (t.name or "") + " "; db.flush()
        assert not XH._NHO_THANG_CU, "ghi vào Tour phải xoá nhớ tháng cũ ngay"
        db.rollback()
    finally:
        db.close()


def test_lam_moi_xoa_nho_thang_cu():
    from app.services import xu_huong as XH
    XH._NHO_THANG_CU[("doanh_thu_thang", "2000-01")] = (time.time(), 1.0)
    tok = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"}).json()["access_token"]
    client.get("/api/v1/dashboard?refresh=1", headers={"Authorization": f"Bearer {tok}"})
    assert ("doanh_thu_thang", "2000-01") not in XH._NHO_THANG_CU


def test_hai_lan_dung_khong_chong_nhau():
    from app.api.v1 import routes as R_
    from app.models.core import User
    from sqlalchemy import select
    db = _db()
    u = db.execute(select(User).where(User.role == "chutich")).scalars().first()
    dang, dinh = [0], [0]
    goc = R_._dashboard_payload

    def cham(db_, u_):
        dang[0] += 1; dinh[0] = max(dinh[0], dang[0]); time.sleep(0.3)
        try:
            return goc(db_, u_)
        finally:
            dang[0] -= 1
    R_._dashboard_payload = cham
    try:
        ts = [threading.Thread(target=lambda: R_.build_dashboard(_db(), u)) for _ in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
    finally:
        R_._dashboard_payload = goc; db.close()
    assert dinh[0] == 1, "hai lần dựng chạy chồng nhau"


def test_dieu_hanh_do_tung_khoi_con():
    tok = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"}).json()["access_token"]
    do = client.get("/api/v1/dashboard?refresh=1", headers={"Authorization": f"Bearer {tok}"}).json()["do_ms"]
    for k in ("dh_sap_khoi_hanh", "dh_giai_doan", "dh_xe_hom_nay", "dh_hieu_qua_xe", "xu_huong"):
        assert k in do, k


# ── KS-XE · cùng cách cho khối Hiệu quả đội xe ─────────────────────────────────────────────────
def test_xe_so_dung_chung_trung_khop_va_chi_nho_thang_da_dong():
    from app.services import hieu_qua_xe as HQ
    HQ.xoa_nho_thang_cu()
    db = _db(); hn = date.today()
    try:
        cu = HQ.theo_ky(db, hn, hom_nay=hn)
        assert HQ.theo_ky(db, hn, hom_nay=hn, nho=HQ.nho_cho_bang(hn)) == cu
        assert HQ.theo_ky(db, hn, hom_nay=hn, nho=HQ.nho_cho_bang(hn)) == cu   # lần sau lấy từ nhớ
    finally:
        db.close()
    ky_nay = f"{hn.year:04d}-{hn.month:02d}"
    assert all(k < ky_nay for k in HQ._NHO_THANG_CU), "tháng đang chạy không được nhớ qua lần dựng"


def test_xe_ghi_so_chuyen_xoa_nho():
    from app.services import hieu_qua_xe as HQ
    from app.models.hr import Vehicle
    from sqlalchemy import select
    HQ._NHO_THANG_CU["2000-01"] = (time.time(), {})
    db = _db()
    try:
        v = db.execute(select(Vehicle)).scalars().first()
        if v is None:
            pytest.skip("không có xe trong dữ liệu mẫu")
        v.plate = v.plate; db.add(v)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(v, "plate"); db.flush()
        assert not HQ._NHO_THANG_CU, "ghi vào bảng đội xe phải xoá nhớ tháng cũ"
        db.rollback()
    finally:
        db.close()


def test_kpi_lanh_dao_do_tung_phan():
    tok = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"}).json()["access_token"]
    do = client.get("/api/v1/dashboard?refresh=1", headers={"Authorization": f"Bearer {tok}"}).json()["do_ms"]
    for k in ("ld_so_du_no_vay_phai_thu", "ld_du_bao_13_tuan", "ld_lai_lo_thang", "kpi_lanh_dao"):
        assert k in do, k
