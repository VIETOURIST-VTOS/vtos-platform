# -*- coding: utf-8 -*-
"""KH-3 · VTD Rewards — Chủ tịch chốt số dự thảo và duyệt bản xem thử 26/10/2026.

  1. Hạng theo chi tiêu 12 tháng (30 tr / 100 tr), giữ hạng 30 ngày khi tụt.
  2. Cộng điểm = floor(B/10.000 × hệ số hạng lúc đủ điều kiện, không tính chính chuyến ấy); chỉ booking trực tiếp,
     tour xong + thu đủ, từ ngày hiệu lực; chạy lại không ghi; hủy sau khi cộng → trừ.
  3. Đổi voucher giữ điểm; hết hạn trả điểm; Sales áp: đúng chủ, ≤ 5%, cộng vào giảm giá, có nhật ký.
  4. Điểm quá 12 tháng hết hạn; yêu thích nhắc giá giảm.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
HL = dt.date(2026, 11, 1)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import rewards as RW, cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "nv_kd"), ("kt", "ketoan")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    st = {"hl": HL}
    monkeypatch.setattr(RW, "hieu_luc_tu", lambda db: st["hl"])
    monkeypatch.setattr(K, "_hom_nay", lambda: dt.date(2026, 11, 1))
    s._st = st
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


_n = {"i": 0}


def _bk(s, net, ket_thuc, tra_luc=None, sdt="0901234567", doi_tac=None, huy=False):
    from app.models.core import Tour, Booking, ServiceRequest
    from app.models.payments import Receipt
    _n["i"] += 1; i = _n["i"]
    t = Tour(code=f"T{i}", name=f"Tour {i}", tour_type="le_noi_dia", start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status="ket_thuc", price_per_pax=net, planned_pax=30)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="An", customer_phone=sdt, source="web", pax=1)
    s.add(r); s.flush()
    b = Booking(code=f"BK2611{i:04d}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="An", customer_phone=sdt, source="web", pax=1, amount=net, discount=0, doi_tac_id=doi_tac, cancelled=huy)
    s.add(b); s.flush()
    if tra_luc:
        s.add(Receipt(code=f"PT{i}", booking_id=b.id, amount=net, status="ke_toan_xac_nhan",
                      created_at=dt.datetime.combine(tra_luc, dt.time(9)), confirmed_at=dt.datetime.combine(tra_luc, dt.time(9))))
    s.commit()
    return b


CHU = "sdt:0901234567"


def test_hang_va_giu_hang():
    from app.services import rewards as RW
    assert RW.hang_theo_chi_tieu(29_999_999, RW.HANG_CU)[0] == "Member" and RW.hang_theo_chi_tieu(30_000_000, RW.HANG_CU)[0] == "Plus"
    assert RW.hang_theo_chi_tieu(39_999_999)[0] == "Member" and RW.hang_theo_chi_tieu(40_000_000)[0] == "Plus"
    assert RW.hang_theo_chi_tieu(100_000_000)[0] == "Premium" and float(RW.hang_theo_chi_tieu(100_000_000)[1]) == 1.5


def test_giu_hang_30_ngay(db):
    from app.services import rewards as RW
    _bk(db, 40_000_000, dt.date(2025, 11, 20), dt.date(2025, 11, 20))
    h = RW.hang(db, CHU, dt.date(2026, 11, 10))           # chuyến 20/11/2025 rơi khỏi 12 tháng ngày 20/11/2026? chưa
    assert h["hang"] == "Plus" and h["giu_den"] is None
    h = RW.hang(db, CHU, dt.date(2026, 11, 25))           # đã rơi khỏi cửa sổ từ 20/11 → còn giữ tới 19/12
    assert h["hang_theo_chi_tieu"] == "Member" and h["hang"] == "Plus" and h["giu_den"] == "2026-12-19"
    assert RW.hang(db, CHU, dt.date(2026, 12, 25))["hang"] == "Member"


def test_cong_diem_he_so_va_doi_chieu(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    _bk(db, 35_000_000, dt.date(2026, 10, 20), dt.date(2026, 10, 20))   # trước hiệu lực: tính hạng, không cộng
    b = _bk(db, 10_000_000, dt.date(2026, 11, 5), dt.date(2026, 11, 5))
    _bk(db, 9_000_000, dt.date(2026, 11, 6), dt.date(2026, 11, 6), doi_tac=None, sdt="0909999999")
    _bk(db, 20_000_000, dt.date(2026, 11, 7))                          # chưa thu
    hom = dt.date(2026, 11, 10)
    RW.tinh(db, CHU, hom)
    rows = db.execute(select(SoDiem).where(SoDiem.chu == CHU)).scalars().all()
    assert [(r.loai, r.so_diem, r.booking_id, r.hang) for r in rows] == [("CONG", 1250, b.id, "Plus")]   # 10tr × 1,25
    assert RW.tinh(db, CHU, hom)["ghi"] == 0, "chạy lại không ghi"
    b.cancelled = True; db.commit()
    RW.tinh(db, CHU, hom)
    assert RW.so_du(db, CHU, hom)["kha_dung"] == 0
    assert db.execute(select(SoDiem).where(SoDiem.loai == "DAO")).scalars().one().so_diem == -1250
    db._st["hl"] = None
    assert RW.tinh(db, CHU, hom)["dang_bat"] is False


def test_dai_ly_khong_tich(db):
    from app.services import rewards as RW
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    d = DoiTacBanHang(ma="DL1", ten="Đại lý", loai="dai_ly", hieu_luc_tu=dt.date(2026, 1, 1)); db.add(d); db.commit()
    _bk(db, 10_000_000, dt.date(2026, 11, 5), dt.date(2026, 11, 5), doi_tac=d.id)
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    assert RW.so_du(db, CHU, dt.date(2026, 11, 10))["kha_dung"] == 0


def test_voucher_doi_ap_het_han_hoan(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    _bk(db, 20_000_000, dt.date(2026, 11, 5), dt.date(2026, 11, 5))     # 2.000 điểm (Member)
    hom = dt.date(2026, 11, 10)
    with pytest.raises(RW.LoiDiem):
        RW.doi_voucher(db, CHU, 50, hom)
    with pytest.raises(RW.LoiDiem):
        RW.doi_voucher(db, CHU, 2001, hom)
    v = RW.doi_voucher(db, CHU, 1500, hom)
    assert v.gia_tri == 150_000 and RW.so_du(db, CHU, hom) == {**RW.so_du(db, CHU, hom), "kha_dung": 500, "dang_giu": 1500}
    # áp: sai vai, sai chủ, vượt 5%, đúng
    moi = _bk(db, 2_000_000, dt.date(2026, 12, 20))                      # 5% = 100.000 < 150.000
    lon = _bk(db, 8_000_000, dt.date(2026, 12, 22))
    khac = _bk(db, 8_000_000, dt.date(2026, 12, 22), sdt="0911111111")
    with pytest.raises(RW.LoiDiem):
        RW.ap_voucher(db, _u(db, "kt"), v.ma, lon.code, hom)
    with pytest.raises(RW.LoiDiem):
        RW.ap_voucher(db, _u(db, "kd"), v.ma, khac.code, hom)
    with pytest.raises(RW.LoiDiem):
        RW.ap_voucher(db, _u(db, "kd"), v.ma, moi.code, hom)
    r = RW.ap_voucher(db, _u(db, "kd"), v.ma, lon.code, hom)
    assert r["giam_gia_moi"] == 150_000 and v.trang_thai == "da_dung"
    with pytest.raises(RW.LoiDiem):
        RW.ap_voucher(db, _u(db, "kd"), v.ma, lon.code, hom)            # dùng hai lần
    # booking dùng voucher bị hủy → hoàn điểm, hạn ít nhất +30 ngày
    lon.cancelled = True; db.commit()
    RW.tinh(db, CHU, hom)
    assert v.trang_thai == "da_hoan" and RW.so_du(db, CHU, hom)["kha_dung"] == 2000
    tra = db.execute(select(SoDiem).where(SoDiem.loai == "TRA_GIU")).scalars().one()
    assert tra.so_diem == 1500 and tra.het_han >= hom + dt.timedelta(days=30)
    # voucher hết hạn chưa dùng → trả điểm
    v2 = RW.doi_voucher(db, CHU, 1000, hom)
    RW.tinh(db, CHU, hom + dt.timedelta(days=31))
    assert v2.trang_thai == "het_han" and RW.so_du(db, CHU, hom + dt.timedelta(days=31))["kha_dung"] == 2000


def test_diem_het_han_12_thang(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    _bk(db, 10_000_000, dt.date(2026, 11, 5), dt.date(2026, 11, 5))
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    assert RW.so_du(db, CHU, dt.date(2027, 10, 20))["sap_het_han"] == 1000
    RW.tinh(db, CHU, dt.date(2027, 11, 15))
    assert db.execute(select(func.sum(SoDiem.so_diem)).where(SoDiem.chu == CHU)).scalar_one() == 0
    assert db.execute(select(SoDiem).where(SoDiem.loai == "HET_HAN")).scalars().one().so_diem == -1000


def test_yeu_thich_nhac_gia(db):
    from app.services import rewards as RW
    from app.models.core import Tour
    from app.models.cong_ngoai import TaiKhoanNgoai
    t = Tour(code="PQ", name="Phú Quốc", tour_type="le_noi_dia", start_date=dt.date(2026, 11, 20), end_date=dt.date(2026, 11, 22),
             operator_id=_u(db, "dh").id, status="da_duyet", price_per_pax=3_990_000, planned_pax=30, seats_open=30)
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong")
    db.add_all([t, tk]); db.commit()
    RW.luu_yeu_thich(db, tk, t.id, True)
    RW.luu_yeu_thich(db, tk, t.id, True)
    assert RW.id_yeu_thich(db, tk) == [t.id]
    t.price_promo = 3_490_000; db.commit()
    y = RW.ds_yeu_thich(db, tk)[0]
    assert y["giam"] == 500_000 and y["con_ban"] is True
    t.status = "huy"; db.commit()
    assert RW.ds_yeu_thich(db, tk)[0]["con_ban"] is False
    RW.luu_yeu_thich(db, tk, t.id, False)
    assert RW.id_yeu_thich(db, tk) == []


def test_cua_va_man_hinh():
    from app.services import access as AC, rewards as RW, rules as R
    from app.api.v1 import rewards as A, cong_khach as CK
    assert AC.MAN_HINH_API["/vtd-rewards"] == ("/api/v1/rewards",)
    assert "rewards_hieu_luc_tu" in R.THAM_SO_NGAY and any(p[0] == "rewards_hieu_luc_tu" and p[1] == "" for p in R.DEFAULT_PARAMS)
    assert "ketoan" not in RW.VAI_AP and "nv_kd" in RW.VAI_AP
    assert {"/api/v1/rewards/ap-voucher", "/api/v1/rewards/tra-cuu"} <= {r.path for r in A.router.routes}
    assert {"/api/v1/cong/khach/diem", "/api/v1/cong/khach/diem/doi", "/api/v1/cong/khach/yeu-thich"} <= {r.path for r in CK.router.routes}
    src = (GOC / "web/components/cong/khach/RewardsKhach.tsx").read_text(encoding="utf-8")
    for c in ("Đổi voucher", "Giá đã giảm", "giữ hạng"):
        assert c in src, c
