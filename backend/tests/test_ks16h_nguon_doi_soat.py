# -*- coding: utf-8 -*-
"""KS-16h · Nguồn đơn CTV, D06 theo v3, đối soát đối tác, trả điểm khi hủy (Chủ tịch duyệt 31/10/2026).

  1. Giữ nguồn 30 ngày; máy tự gắn CTV vào booking tạo trong hạn; trùng nguồn máy tự xử (CTV trước / Sales 7 ngày /
     không tự giới thiệu); link chỉ khi chưa có nguồn bảo vệ, link mới thay link cũ.
  2. D06 v3: loại VAT, chỉ tour có phụ lục, bỏ đặt bàn; phần hoa hồng từng đơn cộng đúng tổng kỳ.
  3. Đối soát: gửi → đồng ý / khiếu nại (vụ việc có mã) → chỉ chi phần thống nhất; quá hạn = đồng ý.
  4. Voucher trả ngay khi hủy không phí; hủy có phí → đã dùng.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

TR = 1_000_000
NOW = dt.datetime(2026, 12, 2, 9, 0)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    import app.services.nguon_don  # noqa: F401   lắng nghe before_flush
    from app.db.session import Base
    from app.models.core import User
    from app.services import hoa_hong_d06 as H
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("kt", "ketoan"), ("gd", "gd_kd"), ("dh", "nv_dh"), ("kd", "nv_kd"), ("sa", "sales_admin")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    st = {"v3": dt.date(2026, 11, 1)}
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: dt.date(2026, 11, 1))
    monkeypatch.setattr(H, "v3_tu", lambda db: st["v3"])
    monkeypatch.setattr(H, "_hom_nay", lambda: NOW.date())
    s._st = st
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _ctv(s, ma, sdt="0911000000"):
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    d = DoiTacBanHang(ma=ma, ten=f"CTV {ma}", loai="ctv_ban_hang", dien_thoai=sdt, hieu_luc_tu=dt.date(2026, 1, 1))
    s.add(d); s.commit()
    return d


def _tour(s, gia, ket_thuc, phu_luc=True, vat=8, ma=None):
    from app.models.core import Tour
    ma = ma or f"T{len(s.execute(select(Tour)).scalars().all()) + 1}"
    t = Tour(code=ma, name=f"Tour {ma}", tour_type="le_noi_dia", start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status="ket_thuc", price_per_pax=gia, fixed_cost=0, var_cost_per_pax=0, planned_pax=1,
             seats_open=1, d06_phu_luc=phu_luc, vat_pct=vat)
    s.add(t); s.commit()
    return t


def _bk(s, t, gia, sdt, tao, tra_luc=None, doi_tac=None, ma=None):
    from app.models.core import Booking, ServiceRequest
    from app.models.payments import Receipt
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="K", customer_phone=sdt, source="web", pax=1)
    s.add(r); s.flush()
    b = Booking(code=ma or f"BK-{t.code}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="K", customer_phone=sdt, source="web", pax=1, amount=gia, discount=0, doi_tac_id=doi_tac,
                created_at=tao)
    s.add(b); s.flush()
    if tra_luc:
        s.add(Receipt(code=f"PT-{b.code}", booking_id=b.id, amount=gia, status="ke_toan_xac_nhan",
                      created_at=dt.datetime.combine(tra_luc, dt.time(10)), confirmed_at=dt.datetime.combine(tra_luc, dt.time(10))))
    s.commit()
    return b


# ── 1 · nguồn đơn ─────────────────────────────────────────────────────────────────────────────

def test_giu_nguon_va_may_gan_booking(db):
    from app.services import nguon_don as ND
    a = _ctv(db, "DT-0001")
    t = _tour(db, 10 * TR, dt.date(2026, 11, 20))
    n = ND.ghi_nguon(db, a, "0987654321", "gioi_thieu", dt.datetime(2026, 11, 2, 9), "Lê D")
    db.commit()
    assert n.trang_thai == "giu" and n.den == dt.datetime(2026, 12, 2, 9)
    b = _bk(db, t, 10 * TR, "0987654321", dt.datetime(2026, 11, 5, 10))
    assert b.doi_tac_id == a.id and b.nguon_don_id == n.id, "máy gắn CTV lúc tạo booking"
    ngoai = _bk(db, _tour(db, 5 * TR, dt.date(2026, 12, 20)), 5 * TR, "0987654321", dt.datetime(2026, 12, 10), ma="BK-NGOAI")
    assert ngoai.doi_tac_id is None, "quá 30 ngày thì không gắn"
    assert ND.ds_cua_ctv(db, a, dt.datetime(2026, 11, 6))[0]["booking"] == [b.code]
    assert ND.ma_ctv(a) == f"CTV-{a.id:04d}" and ND.doi_tac_tu_ma(db, ND.ma_ctv(a)).id == a.id


def test_trung_nguon_may_tu_xu(db):
    from app.services import nguon_don as ND
    from app.models.crm import Lead
    a, b, c = _ctv(db, "DT-0001"), _ctv(db, "DT-0002"), _ctv(db, "DT-0003", sdt="0977777777")
    t0 = dt.datetime(2026, 11, 2, 9)
    ND.ghi_nguon(db, a, "0987654321", "link", t0)
    n2 = ND.ghi_nguon(db, b, "0987654321", "link", t0 + dt.timedelta(hours=1))
    assert n2.trang_thai == "giu" and ND.nguon_hien_hanh(db, "0987654321", t0 + dt.timedelta(hours=2)).doi_tac_id == b.id, "link mới thay link cũ"
    n3 = ND.ghi_nguon(db, a, "0987654321", "gioi_thieu", t0 + dt.timedelta(hours=3))
    assert n3.trang_thai == "giu", "giới thiệu (được bảo vệ) thay link"
    n4 = ND.ghi_nguon(db, b, "0987654321", "link", t0 + dt.timedelta(hours=4))
    assert n4.trang_thai == "thua" and "CTV khác" in n4.ly_do
    assert ND.ghi_nguon(db, c, "0977777777", "gioi_thieu", t0).trang_thai == "thua", "không tự giới thiệu"
    db.add(Lead(phone="0912345678", channel="web", lead_month="2026-11", sales_id=_u(db, "kd").id, last_contact_at=t0 - dt.timedelta(days=3)))
    db.commit()
    n5 = ND.ghi_nguon(db, a, "0912345678", "gioi_thieu", t0)
    assert n5.trang_thai == "thua" and "Sales" in n5.ly_do


def test_khieu_nai_nguon_chap_nhan_chuyen_booking(db):
    from app.services import nguon_don as ND
    a = _ctv(db, "DT-0001")
    t = _tour(db, 10 * TR, dt.date(2026, 11, 20))
    b = _bk(db, t, 10 * TR, "0987654321", dt.datetime(2026, 11, 5))
    assert b.doi_tac_id is None
    v = ND.mo_vu_viec(db, a, "nguon", "Khách do tôi giới thiệu qua Zalo", booking_ma=b.code, now=dt.datetime(2026, 11, 6, 9))
    db.commit()
    assert v.ma.startswith("VV-2611-") and v.han == dt.date(2026, 11, 13)
    with pytest.raises(ND.LoiNguon):
        ND.xu_ly_vu_viec(db, _u(db, "kd"), v.id, True, "đúng nguồn")
    ND.xu_ly_vu_viec(db, _u(db, "gd"), v.id, True, "Có tin nhắn Zalo ngày 01/11")
    db.refresh(b)
    assert b.doi_tac_id == a.id and b.nguon_don_id


# ── 2 · D06 v3 ────────────────────────────────────────────────────────────────────────────────

def test_d06_v3_loai_vat_chi_tour_phu_luc_va_phan_bo(db):
    from app.services import hoa_hong_d06 as H
    a = _ctv(db, "DT-0001")
    H.dat_hinh_thuc(db, _u(db, "gd"), a.id, "ctv_d06", hom_nay=dt.date(2026, 11, 2))
    _bk(db, _tour(db, 54 * TR, dt.date(2026, 11, 10)), 54 * TR, "0900000001", dt.datetime(2026, 11, 1), dt.date(2026, 11, 10), a.id, "BK-A")
    _bk(db, _tour(db, 108 * TR, dt.date(2026, 11, 12)), 108 * TR, "0900000002", dt.datetime(2026, 11, 1), dt.date(2026, 11, 12), a.id, "BK-B")
    _bk(db, _tour(db, 20 * TR, dt.date(2026, 11, 15), phu_luc=False), 20 * TR, "0900000003", dt.datetime(2026, 11, 1),
        dt.date(2026, 11, 15), a.id, "BK-C")
    th = H.tong_hop(db, "2026-11")
    r = th["dong"][0]
    assert th["v3"] and r["doanh_so"] == 150 * TR, "54tr/1,08 + 108tr/1,08 = 150tr; tour không phụ lục bị loại"
    assert r["tong"] == 3_500_000
    assert [x["hoa_hong"] for x in r["nguon"]] == [1_000_000, 2_500_000] and sum(x["hoa_hong"] for x in r["nguon"]) == r["tong"]
    assert any(c["booking"] == "BK-C" and "phụ lục" in c["ly_do"] for c in th["chua_du"])
    db._st["v3"] = None
    assert H.tong_hop(db, "2026-11")["dong"][0]["doanh_so"] == 182 * TR, "chưa ký v3: cách tính cũ"


# ── 3 · đối soát ──────────────────────────────────────────────────────────────────────────────

def test_doi_soat_dong_y_khieu_nai_va_chi_phan_thong_nhat(db, monkeypatch):
    from app.services import hoa_hong_d06 as H, doi_soat_doi_tac as DS
    a = _ctv(db, "DT-0001")
    H.dat_hinh_thuc(db, _u(db, "gd"), a.id, "ctv_d06", hom_nay=dt.date(2026, 11, 2))
    _bk(db, _tour(db, 54 * TR, dt.date(2026, 11, 10)), 54 * TR, "0900000001", dt.datetime(2026, 11, 1), dt.date(2026, 11, 10), a.id, "BK-A")
    _bk(db, _tour(db, 108 * TR, dt.date(2026, 11, 12)), 108 * TR, "0900000002", dt.datetime(2026, 11, 1), dt.date(2026, 11, 12), a.id, "BK-B")
    with pytest.raises(DS.LoiDoiSoat, match="Tính lại"):
        DS.lap_va_gui(db, _u(db, "kt"), a.id, "2026-11", NOW)
    H.tinh_lai(db, _u(db, "kt"), "2026-11")
    k = H.chot(db, _u(db, "kt"), H.tong_hop(db, "2026-11")["dong"][0]["ky_id"])
    with pytest.raises(H.LoiD06, match="đối soát"):
        H.de_nghi_chi(db, _u(db, "kt"), k.id)
    b = DS.lap_va_gui(db, _u(db, "kt"), a.id, "2026-11", NOW)
    assert b.han_phan_hoi == dt.date(2026, 12, 9) and b.han_tra == dt.date(2026, 12, 15)
    monkeypatch.setattr(DS, "date", type("D", (dt.date,), {"today": staticmethod(lambda: NOW.date())}))
    with pytest.raises(H.LoiD06, match="hạn phản hồi"):
        H.de_nghi_chi(db, _u(db, "kt"), k.id)
    bang = DS.cua_doi_tac(db, a, NOW.date())[0]
    dong_b = next(d for d in bang["dong"] if d["ma_don"] == "BK-B")
    v = DS.khieu_nai(db, a, b.id, dong_b["id"], "Sai giá trị booking", NOW)
    DS.dong_y(db, a, b.id, None, NOW)
    assert DS.trang_thai(db, b, NOW.date()) == "co_khieu_nai" and v.ma.startswith("VV-")
    r = H.de_nghi_chi(db, _u(db, "kt"), k.id)
    assert int(r.amount) == 1_000_000, "chỉ chi phần thống nhất (BK-A 50tr × 2%)"
    assert DS.tom_tat(db, a.id, "2026-11", NOW.date())["so_khieu_nai"] == 1


def test_qua_han_phan_hoi_coi_nhu_dong_y(db):
    from app.services import hoa_hong_d06 as H, doi_soat_doi_tac as DS
    a = _ctv(db, "DT-0001")
    H.dat_hinh_thuc(db, _u(db, "gd"), a.id, "ctv_d06", hom_nay=dt.date(2026, 11, 2))
    _bk(db, _tour(db, 54 * TR, dt.date(2026, 11, 10)), 54 * TR, "0900000001", dt.datetime(2026, 11, 1), dt.date(2026, 11, 10), a.id, "BK-A")
    H.tinh_lai(db, _u(db, "kt"), "2026-11")
    b = DS.lap_va_gui(db, _u(db, "kt"), a.id, "2026-11", NOW)
    sau = dt.date(2026, 12, 10)
    assert DS.trang_thai(db, b, sau) == "qua_han"
    assert DS.cua_doi_tac(db, a, sau)[0]["dong"][0]["y_kien"] == "dong_y"
    with pytest.raises(DS.LoiDoiSoat, match="quá hạn"):
        DS.dong_y(db, a, b.id, None, dt.datetime(2026, 12, 10, 9))


# ── 4 · voucher khi hủy ───────────────────────────────────────────────────────────────────────

def test_voucher_tour_tra_ngay_khi_huy_khong_phi(db, monkeypatch):
    from app.services import rewards as RW, bookings as BK
    from app.models.rewards import VoucherRewards, SoDiem
    t = _tour(db, 10 * TR, dt.date(2026, 12, 20))
    b1 = _bk(db, t, 10 * TR, "0987654321", dt.datetime(2026, 11, 5), ma="BK-1")
    b2 = _bk(db, _tour(db, 10 * TR, dt.date(2026, 12, 21)), 10 * TR, "0987654321", dt.datetime(2026, 11, 5), ma="BK-2")
    v1 = VoucherRewards(ma="VTD-AAAAAA", chu="sdt:0987654321", so_diem=1000, gia_tri=100_000, han_dung=dt.date(2026, 12, 30),
                        trang_thai="da_dung", booking_id=b1.id, tao_luc=NOW)
    v2 = VoucherRewards(ma="VTD-BBBBBB", chu="sdt:0987654321", so_diem=0, gia_tri=50_000, han_dung=dt.date(2026, 12, 30),
                        trang_thai="da_dung", booking_id=b2.id, loai="chao_mung", tao_luc=NOW)
    db.add_all([v1, v2]); db.commit()
    monkeypatch.setattr(BK, "toan_quyen", lambda u: True)
    BK.cancel(db, _u(db, "dh"), b1, "Khách hủy sớm, miễn phí", charge=0)
    db.commit()
    assert v1.trang_thai == "da_hoan" and db.execute(select(SoDiem).where(SoDiem.loai == "TRA_GIU")).scalars().one().so_diem == 1000
    b2.paid = 0
    from app.models.payments import Receipt
    db.add(Receipt(code="PT-X", booking_id=b2.id, amount=3 * TR, status="ke_toan_xac_nhan", created_at=NOW, confirmed_at=NOW)); db.commit()
    BK.cancel(db, _u(db, "dh"), b2, "Khách hủy sát ngày", charge=1 * TR)
    db.commit()
    assert v2.trang_thai == "da_dung", "hủy có phí → voucher đã dùng"
    assert not RW.voucher_tour_tra_lai(db, v2)


def test_cua_api_moi():
    from app.main import app
    paths = {r.path for r in app.routes}
    for p in ("/api/v1/cong/doi-tac/nguon", "/api/v1/cong/doi-tac/khieu-nai", "/api/v1/cong/doi-tac/doi-soat",
              "/api/v1/cong/doi-tac/doi-soat/{bang_id}/dong-y", "/api/v1/cong/doi-tac/doi-soat/{bang_id}/khieu-nai",
              "/api/v1/cong/khach/ctv", "/api/v1/hoa-hong-d06/doi-soat", "/api/v1/hoa-hong-d06/vu-viec",
              "/api/v1/hoa-hong-d06/vu-viec/{vid}", "/api/v1/hoa-hong-d06/tour/{tid}/phu-luc"):
        assert p in paths, p
    from app.services import rules as R
    assert "d06_v3_tu" in R.THAM_SO_NGAY and any(p[0] == "d06_v3_tu" and p[1] == "" for p in R.DEFAULT_PARAMS)
