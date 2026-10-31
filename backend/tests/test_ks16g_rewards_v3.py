# -*- coding: utf-8 -*-
"""KS-16g · VTD Rewards theo đề xuất v3 (Chủ tịch duyệt 31/10/2026), bật bằng `rewards_v3_tu`.

  1. Plus 40 tr; điểm mới hết hạn 18 tháng.   2. Hạng kỳ 12 tháng, gia hạn Plus 20 tr / Premium 70 tr.
  3. KS / nhà hàng: 20% hoa hồng VTD.          4. Chào mừng · sinh nhật · trưởng đoàn · giới thiệu.
  5. Trần ưu đãi mới C ≤ min(40%·G, G − 5%·B); tour chưa có dự toán → không phát.
"""
import datetime as dt
from fractions import Fraction

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

HL = dt.date(2026, 11, 1)
CHU = "sdt:0901234567"


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import rewards as RW
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "nv_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    st = {"hl": HL, "v3": HL, "gt": False}
    monkeypatch.setattr(RW, "hieu_luc_tu", lambda db: st["hl"])
    monkeypatch.setattr(RW, "v3_tu", lambda db: st["v3"])
    monkeypatch.setattr(RW, "gioi_thieu_mo", lambda db: st["gt"])
    s._st = st
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


_n = {"i": 0}


def _bk(s, net, ket_thuc, tra=True, sdt="0901234567", pax=1, gia=None, cp_khach=None, khach_ke_hoach=None, tao=None):
    from app.models.core import Tour, Booking, ServiceRequest
    from app.models.payments import Receipt
    _n["i"] += 1; i = _n["i"]
    t = Tour(code=f"G{i}", name=f"Tour {i}", tour_type="le_noi_dia", start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status="ket_thuc", price_per_pax=gia if gia is not None else net,
             planned_pax=khach_ke_hoach or pax, var_cost_per_pax=cp_khach)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="An", customer_phone=sdt, source="web", pax=pax)
    s.add(r); s.flush()
    b = Booking(code=f"BG{i:04d}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="An", customer_phone=sdt, source="web", pax=pax, amount=net, discount=0,
                created_at=tao or dt.datetime(2026, 10, 1))
    s.add(b); s.flush()
    if tra:
        s.add(Receipt(code=f"PG{i}", booking_id=b.id, amount=net, status="ke_toan_xac_nhan",
                      created_at=dt.datetime.combine(ket_thuc, dt.time(9)), confirmed_at=dt.datetime.combine(ket_thuc, dt.time(9))))
    s.commit()
    return b


def _tk(s, sdt="0901234567", email=""):
    from app.models.cong_ngoai import TaiKhoanNgoai
    t = TaiKhoanNgoai(loai="khach_hang", ho_ten="An", dien_thoai=sdt, email=email, trang_thai="hoat_dong")
    s.add(t); s.commit()
    return t


# 1 + 2 ─────────────────────────────────────────────────────────────────────────────────────────

def test_hang_ky_12_thang_gia_han_va_ha(db):
    from app.services import rewards as RW
    _bk(db, 45_000_000, dt.date(2026, 11, 5))
    h = RW.hang(db, CHU, dt.date(2026, 11, 10))
    assert h["hang"] == "Plus" and h["han_hang"] == "2027-11-05" and h["gia_han_can"] == 20_000_000 and h["het_ky_ve"] == "Member"
    assert RW.hang(db, CHU, dt.date(2027, 11, 4))["hang"] == "Plus"
    assert RW.hang(db, CHU, dt.date(2027, 11, 5))["hang"] == "Member", "hết kỳ không đủ 20 tr → Member"
    _bk(db, 25_000_000, dt.date(2027, 3, 1))                                   # trong kỳ đủ 20 tr → gia hạn
    h = RW.hang(db, CHU, dt.date(2027, 11, 6))
    assert h["hang"] == "Plus" and h["han_hang"] == "2028-11-05"


def test_premium_ha_xuong_plus_roi_member(db):
    from app.services import rewards as RW
    _bk(db, 105_000_000, dt.date(2026, 11, 5))
    assert RW.hang(db, CHU, dt.date(2026, 11, 6))["hang"] == "Premium"
    _bk(db, 50_000_000, dt.date(2027, 6, 1))                                   # < 70 tr trong kỳ
    h = RW.hang(db, CHU, dt.date(2027, 11, 6))
    assert h["hang"] == "Plus" and h["han_hang"] == "2028-11-05"
    assert RW.hang(db, CHU, dt.date(2028, 11, 5))["hang"] == "Member", "Plus sau khi hạ vẫn cần 20 tr"


def test_len_hang_ngay_khi_cham_nguong_va_moc_cu(db):
    from app.services import rewards as RW
    _bk(db, 35_000_000, dt.date(2026, 10, 20))                                 # trước mốc v3: ngưỡng cũ 30 tr
    h = RW.hang(db, CHU, dt.date(2026, 11, 2))
    assert h["hang"] == "Plus" and h["han_hang"] == "2027-10-20"
    db._st["v3"] = None                                                        # luật cũ: giữ hạng 30 ngày
    assert RW.hang(db, CHU, dt.date(2026, 11, 2))["luat"] == "cu"


def test_he_so_hang_truoc_giao_dich_va_han_18_thang(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    b1 = _bk(db, 45_000_000, dt.date(2026, 11, 5))
    b2 = _bk(db, 10_000_000, dt.date(2026, 11, 8))
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    rows = {r.booking_id: r for r in db.execute(select(SoDiem).where(SoDiem.loai == "CONG")).scalars()}
    assert rows[b1.id].so_diem == 4500 and rows[b1.id].hang == "Member"      # hạng trước giao dịch
    assert rows[b2.id].so_diem == 1250 and rows[b2.id].hang == "Plus"
    assert rows[b1.id].het_han == dt.date(2028, 5, 10)
    assert RW.tinh(db, CHU, dt.date(2026, 11, 10))["ghi"] == 0


# 3 ─────────────────────────────────────────────────────────────────────────────────────────────

def test_khach_san_nha_hang_20_phan_tram_hoa_hong():
    from app.services import rewards as RW
    x = RW._thu_ho(("k", 1), "KS1", dt.date(2026, 11, 5), 5_000_000, 500_000, HL)
    assert x.uu_dai == 100_000 and x.chi == 0 and x.v3                         # 1.000 điểm × hệ số, không vào hạng
    assert int(x.uu_dai / RW.GIA_TRI_DIEM * Fraction(5, 4)) == 1250
    cu = RW._thu_ho(("k", 1), "KS1", dt.date(2026, 10, 5), 5_000_000, 500_000, HL)
    assert cu.uu_dai == 50_000 and cu.chi == 5_000_000                         # trước mốc: luật cũ


# 4 + 5 ─────────────────────────────────────────────────────────────────────────────────────────

def test_truong_doan_phan_minh_va_thuong_trong_tran(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    # 20 khách × 2 tr = 40 tr; chi phí 1,5 tr/khách → G = 10 tr; trần = min(4 tr, 8 tr)
    b = _bk(db, 40_000_000, dt.date(2026, 11, 5), pax=20, gia=2_000_000, cp_khach=1_500_000)
    p = RW.phong_uu_dai_tour(db, b)
    assert p["G"] == 10_000_000 and p["tran"] == 4_000_000
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    r = {x.loai: x.so_diem for x in db.execute(select(SoDiem).where(SoDiem.chu == CHU)).scalars()}
    assert r == {"CONG": 200, "THUONG": 2000}                                  # 2 tr × 1% / 100 + 2.000
    assert RW.hang(db, CHU, dt.date(2026, 11, 10))["chi_tieu_12_thang"] == 2_000_000
    assert RW.tinh(db, CHU, dt.date(2026, 11, 10))["ghi"] == 0
    b.cancelled = True; db.commit()
    RW.tinh(db, CHU, dt.date(2026, 11, 11))
    assert RW.so_du(db, CHU, dt.date(2026, 11, 11))["kha_dung"] == 0


def test_truong_doan_het_tran_hoac_khong_du_toan(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    _bk(db, 40_000_000, dt.date(2026, 11, 5), pax=20, gia=2_000_000, cp_khach=1_950_000)   # G = 1 tr < 5% B
    _bk(db, 40_000_000, dt.date(2026, 11, 6), pax=20, gia=2_000_000)                       # không dự toán
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    assert not db.execute(select(SoDiem).where(SoDiem.loai == "THUONG")).scalars().all()


def test_voucher_chao_mung(db):
    from app.services import rewards as RW
    tk = _tk(db)
    ma = RW.phat_qua(db, tk, dt.date(2026, 11, 2))
    assert len(ma) == 1 and RW.phat_qua(db, tk, dt.date(2026, 11, 3)) == []
    hn = dt.date(2026, 11, 3)
    nho = _bk(db, 4_000_000, dt.date(2026, 12, 20), tra=False, gia=4_000_000, cp_khach=2_000_000)
    with pytest.raises(RW.LoiDiem, match="5.000.000"):
        RW.ap_voucher(db, _u(db, "kd"), ma[0], nho.code, hn)
    nho.cancelled = True; db.commit()
    khong_dt = _bk(db, 8_000_000, dt.date(2026, 12, 20), tra=False)
    with pytest.raises(RW.LoiDiem, match="dự toán"):
        RW.ap_voucher(db, _u(db, "kd"), ma[0], khong_dt.code, hn)
    khong_dt.cancelled = True; db.commit()
    ok = _bk(db, 8_000_000, dt.date(2026, 12, 20), tra=False, gia=8_000_000, cp_khach=5_000_000)
    sau = _bk(db, 8_000_000, dt.date(2026, 12, 21), tra=False, gia=8_000_000, cp_khach=5_000_000)
    with pytest.raises(RW.LoiDiem, match="đầu tiên"):
        RW.ap_voucher(db, _u(db, "kd"), ma[0], sau.code, hn)
    assert RW.ap_voucher(db, _u(db, "kd"), ma[0], ok.code, hn)["giam_gia_moi"] == 50_000
    # hủy booking → voucher quà mở lại, không sinh điểm
    ok.cancelled = True; db.commit()
    RW.tinh(db, CHU, hn)
    from app.models.rewards import VoucherRewards
    v = db.execute(select(VoucherRewards).where(VoucherRewards.ma == ma[0])).scalars().one()
    assert v.trang_thai == "cho_dung" and v.booking_id is None and RW.so_du(db, CHU, hn)["kha_dung"] == 0


def test_voucher_sinh_nhat(db):
    from app.services import rewards as RW
    _bk(db, 1_000_000, dt.date(2026, 10, 1))                                    # đã có tour → không chào mừng
    tk = _tk(db)
    tk.ngay_sinh, tk.ngay_sinh_luc = dt.date(1990, 12, 9), dt.datetime(2026, 12, 2)
    db.commit()
    assert RW.phat_qua(db, tk, dt.date(2026, 12, 3)) == [], "khai trong tháng sinh → chưa phát năm nay"
    tk.ngay_sinh_luc = dt.datetime(2026, 11, 2); db.commit()
    assert len(RW.phat_qua(db, tk, dt.date(2026, 12, 3))) == 1
    assert RW.phat_qua(db, tk, dt.date(2026, 12, 20)) == []
    assert len(RW.phat_qua(db, tk, dt.date(2027, 12, 1))) == 1
    with pytest.raises(RW.LoiDiem):
        RW.khai_ngay_sinh(db, tk, dt.date(1991, 1, 1))


def test_gioi_thieu(db):
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    a = _tk(db, "0901234567")
    b = _tk(db, "0912345678")
    now = dt.datetime(2026, 11, 2, 9)
    with pytest.raises(RW.LoiDiem, match="chưa mở"):
        RW.nhap_ma_gioi_thieu(db, b, "X", now)
    db._st["gt"] = True
    ma = RW.ma_gioi_thieu(db, a)
    with pytest.raises(RW.LoiDiem, match="chính mình"):
        RW.nhap_ma_gioi_thieu(db, a, ma, now)
    RW.nhap_ma_gioi_thieu(db, b, ma, now)
    with pytest.raises(RW.LoiDiem):
        RW.nhap_ma_gioi_thieu(db, b, ma, now)
    _bk(db, 8_000_000, dt.date(2026, 11, 20), sdt="0912345678", gia=8_000_000, cp_khach=5_000_000, tao=dt.datetime(2026, 11, 3))
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    assert not db.execute(select(SoDiem).where(SoDiem.loai == "THUONG")).scalars().all(), "tour chưa xong"
    RW.tinh(db, CHU, dt.date(2026, 11, 25))
    assert db.execute(select(SoDiem).where(SoDiem.chu == CHU, SoDiem.loai == "THUONG")).scalars().one().so_diem == 1000
    assert RW.ho_so_qua(db, a)["da_gioi_thieu"][0]["trang_thai"] == "da_thuong"


def test_khong_hoi_to_khoan_da_cong_truoc_moc(db):
    """Ngày áp v3 ký lùi về trước: khoản đã cộng trước ngày ký vẫn giữ cách tính cũ, không ghi chênh."""
    from app.services import rewards as RW
    from app.models.rewards import SoDiem
    db._st["v3"] = None
    _bk(db, 40_000_000, dt.date(2026, 11, 5), pax=20, gia=2_000_000, cp_khach=1_500_000)
    RW.tinh(db, CHU, dt.date(2026, 11, 10))
    assert db.execute(select(SoDiem)).scalars().one().so_diem == 4000
    db._st["v3"] = dt.date(2026, 11, 1)
    RW.tinh(db, CHU, dt.date(2026, 11, 20))
    assert [r.so_diem for r in db.execute(select(SoDiem).where(SoDiem.loai.in_(("CONG", "DAO")))).scalars()] == [4000]
