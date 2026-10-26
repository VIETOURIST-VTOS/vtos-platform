# -*- coding: utf-8 -*-
"""KH-1 · Cổng khách hàng VTD — Chủ tịch duyệt 26/10/2026.

  1. Tour hiện = đã duyệt, còn chỗ, chưa khởi hành; chỉ thông tin bán, không lộ giá vốn / biên.
  2. «Gửi yêu cầu» tạo lead «Đặt tour web» cho Sales, không tạo booking, không giữ chỗ; nối ghi chú.
  3. «Đơn của tôi» chỉ ghép theo liên hệ ĐÃ XÁC THỰC; không xem được đơn người khác.
  4. Thanh toán tách phục vụ; chỉ phiếu thu kế toán đã xác nhận mới là «đã thu».
  5. Cửa API đòi phiên cổng ngoài loại khách hàng.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
HOM_NAY = dt.date(2026, 11, 1)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "nv_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: HOM_NAY)
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _tour(s, ma, bat_dau, status="da_duyet", gia=3_990_000, cho=20, km=None, loai="le_noi_dia", noi="TP HCM"):
    from app.models.core import Tour
    t = Tour(code=ma, name=f"Tour {ma}", tour_type=loai, start_date=bat_dau, end_date=bat_dau + dt.timedelta(days=2),
             operator_id=_u(s, "dh").id, status=status, price_per_pax=gia, fixed_cost=50_000_000, var_cost_per_pax=2_000_000,
             planned_pax=cho, seats_open=cho, price_promo=km, departure_point=noi, days=3)
    s.add(t); s.commit(); return t


def _booking(s, t, sdt="0901234567", email="", pax=2, amount=7_980_000, huy=False):
    from app.models.core import Booking, ServiceRequest
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="K", customer_phone=sdt, source="web", pax=pax)
    s.add(r); s.flush()
    n = s.execute(select(func.count(Booking.id))).scalar_one() + 1
    b = Booking(code=f"BK{n:03d}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="K", customer_phone=sdt, customer_email=email, source="web", pax=pax, amount=amount, discount=0,
                cancelled=huy)
    s.add(b); s.commit(); return b


def _tk(s, sdt="0901234567", email="", loai="khach_hang"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai=loai, dien_thoai=sdt, email=email, trang_thai="hoat_dong", ho_ten="An")
    s.add(tk); s.commit(); return tk


# ── 1 · tour ──────────────────────────────────────────────────────────────────────────────────

def test_chi_hien_tour_da_duyet_con_cho_chua_khoi_hanh(db):
    from app.services import cong_khach as K
    a = _tour(db, "A", HOM_NAY + dt.timedelta(days=20))
    _tour(db, "NHAP", HOM_NAY + dt.timedelta(days=20), status="nhap")
    _tour(db, "CU", HOM_NAY - dt.timedelta(days=1))
    _tour(db, "HOMNAY", HOM_NAY)
    het = _tour(db, "HET", HOM_NAY + dt.timedelta(days=9), cho=2)
    _booking(db, het, pax=2)
    _tour(db, "XE", HOM_NAY + dt.timedelta(days=9), loai="thue_xe")
    km = _tour(db, "KM", HOM_NAY + dt.timedelta(days=5), km=3_490_000)
    ds = K.tours(db)
    assert [x["ma"] for x in ds] == ["KM", "A"]
    o = next(x for x in ds if x["ma"] == "KM")
    assert o["gia"] == 3_490_000 and o["gia_goc"] == 3_990_000 and o["nhan"] == "Tour khuyến mại"
    for cam in ("fixed_cost", "var_cost_per_pax", "operator_id", "status", "planned_pax", "seats_open", "cost_lines"):
        assert cam not in o
    assert K.tour(db, a.id)["thoi_gian"] == "3 ngày 2 đêm"
    with pytest.raises(K.LoiKhach):
        K.tour(db, het.id)
    assert [x["ma"] for x in K.tours(db, ngan_sach=3_500_000)] == ["KM"]
    assert [x["ma"] for x in K.tours(db, q="tour a")] == ["A"]
    assert K.tours(db, nhom="promo")[0]["ma"] == "KM" and km.id


# ── 2 · yêu cầu ───────────────────────────────────────────────────────────────────────────────

def test_gui_yeu_cau_tao_lead_khong_tao_booking_va_noi_ghi_chu(db):
    from app.services import cong_khach as K
    from app.models.crm import Lead
    from app.models.core import Booking
    a = _tour(db, "A", HOM_NAY + dt.timedelta(days=20))
    tk = _tk(db)
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk, "tour", a.id, 2, "", None, "", dong_y=False)
    K.gui_yeu_cau(db, tk, "tour", a.id, 2, "", None, "ăn chay", dong_y=True, now=dt.datetime(2026, 11, 1, 8))
    K.gui_yeu_cau(db, tk, "tour_doan", None, 30, "0911222333", HOM_NAY + dt.timedelta(days=60), "công ty", dong_y=True,
                  now=dt.datetime(2026, 11, 1, 9))
    leads = db.execute(select(Lead)).scalars().all()
    assert {l.phone for l in leads} == {"0901234567", "0911222333"} and all(l.channel == "Đặt tour web" for l in leads)
    l1 = next(l for l in leads if l.phone == "0901234567")
    assert "ăn chay" in l1.note and "Tour A" in l1.note
    K.gui_yeu_cau(db, tk, "tour", a.id, 3, "", None, "lần hai", dong_y=True, now=dt.datetime(2026, 11, 1, 10))
    db.refresh(l1)
    assert "ăn chay" in l1.note and "lần hai" in l1.note, "ghi chú nối thêm, không đè"
    assert db.execute(select(func.count(Booking.id))).scalar_one() == 0
    assert [y["so_khach"] for y in K.yeu_cau_cua(db, tk)][:1] == [3]
    assert K.tours(db)[0]["con_cho"] is True


def test_yeu_cau_bi_chan(db):
    from app.services import cong_khach as K
    tk_mail = _tk(db, sdt="", email="a@b.vn")
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk_mail, "tour_doan", None, 5, "", None, "", dong_y=True)   # chưa có SĐT gọi lại
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk_mail, "tour_doan", None, 0, "0901111222", None, "", dong_y=True)
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk_mail, "tour", 999, 2, "0901111222", None, "", dong_y=True)
    now = dt.datetime(2026, 11, 1, 10)
    for _ in range(K.YEU_CAU_TOI_DA_NGAY):
        K.gui_yeu_cau(db, tk_mail, "tour_doan", None, 5, "0901111222", None, "", dong_y=True, now=now)
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk_mail, "tour_doan", None, 5, "0901111222", None, "", dong_y=True, now=now)
    dt_tk = _tk(db, sdt="0909999888", loai="doi_tac")
    with pytest.raises(K.LoiKhach):
        K.don_cua_toi(db, dt_tk)


# ── 3–4 · đơn ─────────────────────────────────────────────────────────────────────────────────

def test_don_chi_cua_lien_he_da_xac_thuc_va_tien_tach_phuc_vu(db):
    from app.services import cong_khach as K
    from app.models.payments import Receipt
    a = _tour(db, "A", HOM_NAY + dt.timedelta(days=5))
    cu = _tour(db, "CU", HOM_NAY - dt.timedelta(days=30), status="ket_thuc")
    b1 = _booking(db, a, sdt="+84 901 234 567")
    b2 = _booking(db, cu, sdt="0901234567", amount=6_400_000)
    b3 = _booking(db, a, sdt="0987654321", email="An@Mail.vn")
    _booking(db, a, sdt="0123901234567")                         # đuôi trùng nhưng số khác — không được lọt
    db.add_all([Receipt(code="PT1", booking_id=b1.id, amount=3_000_000, status="ke_toan_xac_nhan"),
                Receipt(code="PT2", booking_id=b1.id, amount=4_980_000, status="tu_dong"),
                Receipt(code="PT3", booking_id=b2.id, amount=6_400_000, status="ke_toan_xac_nhan"),
                Receipt(code="PT4", booking_id=b2.id, amount=1, status="huy")])
    db.commit()
    tk = _tk(db)
    ds = {d["ma"]: d for d in K.don_cua_toi(db, tk)}
    assert set(ds) == {b1.code, b2.code}
    assert ds[b1.code]["thanh_toan"] == "Đã thu một phần" and ds[b1.code]["da_thu"] == 3_000_000 and ds[b1.code]["dang_xac_nhan"] == 4_980_000
    assert ds[b1.code]["phuc_vu"] == "Đã xác nhận" and ds[b1.code]["sap_di"] is True
    assert ds[b2.code]["thanh_toan"] == "Đã thu đủ" and ds[b2.code]["phuc_vu"] == "Đã hoàn tất"
    with pytest.raises(K.LoiKhach):
        K.don(db, tk, b3.code)                                    # đơn người khác: cùng câu với «không có»
    tk_mail = _tk(db, sdt="", email="an@mail.vn")
    assert [d["ma"] for d in K.don_cua_toi(db, tk_mail)] == [b3.code]
    tc = K.trang_chu(db, tk)
    assert tc["sap_di"] == 1 and tc["chuyen_toi"]["ma"] == b1.code


def test_ho_so_va_so_thich(db):
    from app.services import cong_khach as K
    tk = _tk(db)
    K.cap_nhat_ho_so(db, tk, "Bình", "Ẩm thực", True)
    assert tk.ho_ten == "Bình" and tk.so_thich == "Ẩm thực" and tk.nhan_tin_quang_cao is True
    with pytest.raises(K.LoiKhach):
        K.cap_nhat_ho_so(db, tk, None, "linh tinh", None)


# ── 5 · cửa ───────────────────────────────────────────────────────────────────────────────────

def test_cua_api_doi_phien_cong_ngoai():
    from app.api.v1 import cong_khach as A
    paths = {r.path for r in A.router.routes}
    assert {"/api/v1/cong/khach/trang-chu", "/api/v1/cong/khach/tour", "/api/v1/cong/khach/tour/{tour_id}",
            "/api/v1/cong/khach/yeu-cau", "/api/v1/cong/khach/don", "/api/v1/cong/khach/don/{ma}",
            "/api/v1/cong/khach/ho-so"} <= paths
    for r in A.router.routes:
        names = {d.call.__name__ for d in r.dependant.dependencies}
        assert "tai_khoan_ngoai" in names, r.path
    src = (GOC / "web/components/cong/khach/KhachHang.tsx").read_text(encoding="utf-8")
    for s in ("Đơn của tôi", "Gửi yêu cầu", "chưa giữ chỗ", "Tour đoàn theo yêu cầu", "Hồ sơ & riêng tư", "Sắp ra mắt"):
        assert s in src, s
