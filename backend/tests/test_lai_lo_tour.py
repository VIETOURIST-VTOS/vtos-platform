"""Lãi lỗ theo tour – chuẩn phép tính chốt 09/9/2026.

Sáu phép thử, mỗi cái canh một chỗ mà nếu sai thì bảng vẫn "chạy được" nhưng con số sai và không ai
thấy. Đó là loại sai đắt nhất trong một báo cáo quản trị: nó không đổ, nó chỉ nói dối.

  LL1  khuyến mãi phải nằm trong GIÁ VỐN, không phải giảm trừ doanh thu (ĐC Điều 3)
  LL2  booking đã huỷ: không tính tiền tour, nhưng phí huỷ giữ lại thì CÓ tính doanh thu
  LL3  chưa có giá vốn thì lợi nhuận phải RỖNG, tuyệt đối không được bằng doanh thu
  LL4  tổng chân bảng chỉ cộng dòng đã có giá vốn – cộng cả dòng thiếu là báo lãi giả
  LL5  giá vốn theo khách chỉ có với dịch vụ lẻ, tour ghép thì không, và nói rõ vì sao
  LL6  cửa nhập hoá đơn đầu vào ghi được và bỏ trống được
"""
import os, sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_lailo.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_lailo.db", "test_lailo.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.core import Booking, Tour, User
from app.models.vietrip import TourCostLine
from app.services import lai_lo_tour as LL

client = TestClient(app)
MK = "lailo123456"
HOM_NAY = date.today()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for vai in ("chutich", "nv_dh", "ketoan"):
            un = f"ll_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(vai="chutich"):
    r = client.post("/api/v1/auth/login", data={"username": f"ll_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _tour(db, ma, **kw):
    t = Tour(code=ma, name=f"Chuyến {ma}", tour_type=kw.pop("tour_type", "le_noi_dia"),
             start_date=HOM_NAY - timedelta(days=10), end_date=HOM_NAY - timedelta(days=8),
             operator_id=1, status=kw.pop("status", "ket_thuc"), **kw)
    db.add(t); db.flush()
    return t


def _bk(db, t, ma, tien, **kw):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=1, created_by=1,
                customer_name=kw.pop("ten", "Khách thử"), customer_phone="0900000000",
                source="thu", pax=kw.pop("pax", 2), amount=tien, **kw)
    db.add(b); db.flush()
    return b


def _dong(db, t, thuc_chi, **kw):
    l = TourCostLine(tour_id=t.id, description=kw.pop("mo_ta", "Xe 45 chỗ"), actual=thuc_chi,
                     supplier_name=kw.pop("ncc", "NCC thử"), **kw)
    db.add(l); db.flush()
    return l


def _mot(db, t):
    return LL.chi_tiet(db, t)["tong_hop"]


def test_ll1_khuyen_mai_la_gia_von_khong_phai_giam_tru_doanh_thu():
    """Bỏ sót khuyến mãi là thổi lợi nhuận lên đúng bằng giá trị khuyến mãi.

    Đây là lỗi dễ mắc nhất của cả bảng, vì cột này rỗng ở 99,9% tour thật nên gần như không ai để ý là
    nó tồn tại. ĐC Điều 3: giá trị mã khuyến mãi là một dòng giá vốn nội bộ.
    """
    db = _db()
    try:
        t = _tour(db, "LL-KM-01", promo_value=1_000_000)
        _bk(db, t, "LLB-KM-01", 10_000_000)
        _dong(db, t, 6_000_000)
        db.commit(); db.refresh(t)
        r = _mot(db, t)
        assert r["doanh_thu"] == 10_000_000, "khuyến mãi không được trừ vào doanh thu"
        assert r["gia_von"] == 7_000_000, "khuyến mãi phải cộng vào giá vốn (6tr chi phí + 1tr khuyến mãi)"
        assert r["loi_nhuan"] == 3_000_000, (
            "nếu ra 4.000.000 nghĩa là khuyến mãi bị bỏ quên – lợi nhuận bị thổi lên đúng 1.000.000")
    finally:
        db.close()


def test_ll2_booking_huy_khong_tinh_tien_tour_nhung_phi_huy_van_la_doanh_thu():
    """Bỏ cả booking đã huỷ là mất doanh thu thật; tính cả tiền tour của nó là tạo doanh thu ảo."""
    db = _db()
    try:
        t = _tour(db, "LL-HUY-01")
        _bk(db, t, "LLB-HUY-01", 10_000_000)
        _bk(db, t, "LLB-HUY-02", 8_000_000, cancelled=True, cancel_charge=2_000_000, pax=3)
        _dong(db, t, 5_000_000)
        db.commit(); db.refresh(t)
        r = _mot(db, t)
        assert r["doanh_thu"] == 12_000_000, "10tr của khách còn đi + 2tr phí huỷ giữ lại"
        assert r["so_khach"] == 2, "khách đã huỷ không được đếm vào số khách"
        assert r["so_booking_huy"] == 1
    finally:
        db.close()


def test_ll3_chua_co_gia_von_thi_loi_nhuan_phai_RONG():
    """Chỗ nguy hiểm nhất của cả báo cáo.

    Nếu giá vốn thiếu mà bị coi là 0 thì lợi nhuận ra đúng bằng doanh thu – một con số lãi rất đẹp,
    sai theo hướng dễ chịu, nên càng ít người đi kiểm. Trên hệ thống thật có 18 tour đúng vào tình
    huống này.
    """
    db = _db()
    try:
        t = _tour(db, "LL-THIEU-01")
        _bk(db, t, "LLB-THIEU-01", 9_000_000)
        db.commit(); db.refresh(t)
        r = _mot(db, t)
        assert r["doanh_thu"] == 9_000_000
        assert r["gia_von"] is None, "chưa có dòng chi phí nào thì giá vốn phải RỖNG, không phải 0"
        assert r["loi_nhuan"] is None, "lợi nhuận phải RỖNG – nếu ra 9.000.000 là đang báo lãi 100%"
        assert r["nguon_so"] == "thieu_gia_von"
        assert r["bien"] is None, "không có lợi nhuận thì không có biên, kể cả 0%"
    finally:
        db.close()


def test_ll4_tong_chan_bang_chi_cong_dong_da_co_gia_von():
    """Một dòng thiếu giá vốn lọt vào tổng là cả cái tổng thành số lãi giả."""
    db = _db()
    try:
        t1 = _tour(db, "LL-TONG-01"); _bk(db, t1, "LLB-TONG-01", 10_000_000); _dong(db, t1, 6_000_000)
        t2 = _tour(db, "LL-TONG-02"); _bk(db, t2, "LLB-TONG-02", 20_000_000)   # chưa có giá vốn
        db.commit()
        rows = [_mot(db, t1), _mot(db, t2)]
        c = LL._cong(rows)
        assert c["so_dong_tinh"] == 1 and c["so_dong_bo_qua"] == 1
        assert c["doanh_thu"] == 10_000_000, (
            "doanh thu tổng chỉ gồm tour đã có giá vốn – cộng cả 20tr của tour chưa quyết toán vào là "
            "ghép doanh thu của nó với lợi nhuận không có thật")
        assert c["loi_nhuan"] == 4_000_000
    finally:
        db.close()


def test_ll5_gia_von_theo_khach_chi_co_voi_dich_vu_le():
    """Chia giá vốn chuyến cho từng khách là phép phân bổ, không phải sự thật – và bảng phải nói ra."""
    db = _db()
    try:
        tg = _tour(db, "LL-GHEP-01")
        _bk(db, tg, "LLB-GHEP-01", 5_000_000, ten="Nguyễn Văn A")
        _dong(db, tg, 3_000_000)
        tl = _tour(db, "LL-LE-01", tour_type="non_package")
        _bk(db, tl, "LLB-LE-01", 4_000_000, ten="Trần Thị B", cost_amount=2_500_000,
            supplier_name="Đại sứ quán X")
        db.commit(); db.refresh(tg); db.refresh(tl)

        g = LL.chi_tiet(db, tg)
        assert g["co_gia_von_theo_khach"] is False
        assert g["khach"][0]["gia_von_khach"] is None
        assert "phân bổ" in g["vi_sao_khong_co_gia_von_theo_khach"], "phải giải thích, không im lặng bỏ trống"
        assert g["khach"][0]["ten_khach"] == "Nguyễn Văn A", "lớp 2 phải có tên khách"

        l = LL.chi_tiet(db, tl)
        assert l["co_gia_von_theo_khach"] is True
        assert l["khach"][0]["gia_von_khach"] == 2_500_000, "dịch vụ lẻ có giá vốn thật theo khách"
    finally:
        db.close()


def test_ll6_cua_nhap_hoa_don_dau_vao_ghi_duoc_va_bo_trong_duoc():
    """Cửa nhập mới. Ép nhập đủ mới cho lưu là đẩy người ta ghi ra giấy rồi 'nhập sau' – tức không bao giờ."""
    db = _db()
    try:
        t = _tour(db, "LL-HD-01")
        _bk(db, t, "LLB-HD-01", 7_000_000)
        l = _dong(db, t, 4_000_000)
        db.commit(); lid = l.id; tid = t.id
    finally:
        db.close()

    h = login("ketoan")
    r = client.put(f"/api/v1/lai-lo-tour/dong-chi-phi/{lid}/hoa-don",
                   json={"so_hoa_don": "0001234", "ngay_hoa_don": "2026-09-01", "vat_hoa_don": 400_000}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["so_hoa_don"] == "0001234"

    d = client.get(f"/api/v1/lai-lo-tour/{tid}", headers=login()).json()
    cp = d["chi_phi"][0]
    assert cp["so_hoa_don"] == "0001234" and cp["vat_hoa_don"] == 400_000
    assert cp["ncc"] == "NCC thử", "lớp 2 phải có tên nhà cung cấp"

    # Bỏ trống lại được: người nhập có thể gõ nhầm số hoá đơn và cần xoá đi.
    r2 = client.put(f"/api/v1/lai-lo-tour/dong-chi-phi/{lid}/hoa-don", json={}, headers=h)
    assert r2.status_code == 200 and r2.json()["so_hoa_don"] is None
