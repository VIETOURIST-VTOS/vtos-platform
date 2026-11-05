# -*- coding: utf-8 -*-
"""KS-16 · VTD Rewards cho khách sạn VTD — giống tour (Chủ tịch duyệt bản xem thử 30/10/2026).

  1. Không có giá thành viên. Đơn khách / cổ đông tự đặt, đã ở, Kế toán đã chốt → cộng floor(B/10.000 × hệ số hạng);
     B = tiền khách thực trả − đã hoàn. Chưa chốt: «chờ chốt, dự kiến +N». Một đơn chỉ cộng cho MỘT chủ điểm.
  2. Khách tự nhập voucher lúc đặt: đúng chủ, còn hạn, tối đa 5% đơn. Khách trả phần còn lại; khách sạn vẫn nhận
     như không có voucher — Kế toán chốt ghi Nợ 641 / Có 3388 phần voucher.
  3. Đơn hủy có hoàn / hết giờ giữ chưa trả → voucher trả điểm ngay; hủy không hoàn → voucher đã dùng hẳn.
"""
import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks14_dat_phong_vtd import NAY, _ct, _dat, _tk, _txn, k3  # noqa: F401

SAU = dt.datetime(2026, 12, 22, 9, 0)          # sau ngày trả phòng 20/12
CHU = "sdt:0901000001"


@pytest.fixture()
def bat(monkeypatch):
    from app.services import rewards as RW
    monkeypatch.setattr(RW, "hieu_luc_tu", lambda s: dt.date(2026, 1, 1))


def _vc(s, gia_tri=150_000,   # KS-19: đơn mẫu 3.800.000 (đã gồm VAT) — trần 5% = 190.000
        chu=CHU, ma="VTD-AAAAAA"):
    from app.models.rewards import SoDiem, VoucherRewards
    s.add(SoDiem(chu=chu, loai="GIU", so_diem=-gia_tri // 100, luc=NAY, ghi_chu="đổi"))
    v = VoucherRewards(ma=ma, chu=chu, so_diem=gia_tri // 100, gia_tri=gia_tri, han_dung=dt.date(2026, 12, 31), tao_luc=NAY)
    s.add(v); s.commit()
    return v


def _tra(s, d, sid="T1"):
    from app.services import don_ks_vtd as S
    from app.services import payments as P
    P.match_transaction(s, _txn(s, d.tong, d.ma, sid=sid)); s.commit()
    tt = s.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    S.kt_xac_nhan_qr(s, _u(s, "kt"), tt.id, NAY); s.commit()


def test_voucher_diem_va_so_ke_toan(db, k3, bat):
    from app.models.rewards import SoDiem
    from app.services import don_ks_vtd as S
    from app.services import rewards as RW
    k, lp, g = k3
    v = _vc(db)
    to = _vc(db, 300_000, ma="VTD-BBBBBB")
    with pytest.raises(RW.LoiDiem, match="tối đa 5%"):
        RW.kiem_voucher_ks(db, _tk(db), to.ma, 3_800_000, NAY.date())             # trần 190.000 đ
    with pytest.raises(RW.LoiDiem, match="tài khoản của bạn"):
        RW.kiem_voucher_ks(db, _tk(db, 2), v.ma, 3_800_000, NAY.date())          # người khác
    with pytest.raises(S.LoiDon, match="tối đa 5%"):
        _dat(db, k, g, ma_voucher=to.ma)
    d = _dat(db, k, g, ma_voucher=" vtd-aaaaaa ")
    assert d.tong == 3_650_000 and d.giam_voucher == 150_000 and d.voucher_id == v.id
    assert v.trang_thai == "da_dung" and v.don_ks_id == d.id
    assert S.ra_khach(db, d, NAY)["voucher"]["ma"] == "VTD-AAAAAA"
    with pytest.raises(S.LoiDon, match="đã dùng"):
        _dat(db, k, g, tk=_tk(db), ma_voucher=v.ma)
    _tra(db, d)
    assert d.trang_thai == "da_xac_nhan"   # KS-19
    S.dh_xac_nhan(db, _u(db, "dh"), d.id, "BX-1", NAY); db.commit()
    hn = SAU.date()
    RW.tinh(db, CHU, hn)
    assert db.execute(select(SoDiem).where(SoDiem.don_ks_id == d.id)).scalars().all() == []    # chưa chốt
    tq = RW.tong_quan(db, [CHU], hn)
    assert tq["cho_cong"] == [{"ma": d.ma, "co_so": 3_650_000, "du_kien": 365}]
    # Kế toán chốt: khách sạn nhận như không có voucher; voucher ghi Nợ 641 / Có 3388
    S.kt_chot(db, _u(db, "kt"), d.id, 400_000, SAU); db.commit()
    assert d.phai_tra_ks == 3_400_000 and S.khuyen_mai(db, d) == 150_000
    assert _ct(db, d.km_but_toan) == [("3388", 0, 150_000), ("641", 150_000, 0)]
    kt = S.hang_ke_toan(db, _u(db, "kt"), SAU)["phai_tra_ks"][0]
    assert kt["phai_tra"] == 3_400_000 and kt["khuyen_mai"] == 150_000
    RW.tinh(db, CHU, hn)
    r = db.execute(select(SoDiem).where(SoDiem.don_ks_id == d.id)).scalars().one()
    assert r.loai == "CONG" and r.so_diem == 365 and r.co_so == 3_650_000                       # Member ×1
    assert RW.hang(db, CHU, hn)["chi_tieu_12_thang"] == 3_650_000
    tq = RW.tong_quan(db, [CHU], hn)
    assert tq["cho_cong"] == [] and tq["lich_su"][0]["nguon"] == "khach_san"
    assert [x for x in RW.khoan(db, CHU, hn) if x["loai"] == "Khách sạn"][0]["diem"] == 365
    RW.tinh(db, CHU, hn)
    assert len(db.execute(select(SoDiem).where(SoDiem.don_ks_id == d.id)).scalars().all()) == 1   # chạy lại không ghi
    he = RW.he_so_cua(db, _tk(db), hn)
    assert he["dang_bat"] and he["hang"] == "Member" and he["he_so"] == 1.0


def test_huy_het_gio_tra_diem_voucher(db, k3, bat):
    from app.models.rewards import SoDiem
    from app.services import don_ks_vtd as S
    from app.services import payments as P
    k, lp, g = k3
    v = _vc(db)
    # 1) hủy trước hạn miễn phí → hoàn đủ số khách đã trả; voucher trả điểm ngay
    d = _dat(db, k, g, ma_voucher=v.ma)
    _tra(db, d)
    S.huy_boi_khach(db, _tk(db), d.ma, "", NAY); db.commit()
    assert d.so_hoan == 3_650_000 and v.trang_thai == "da_hoan" and S.khuyen_mai(db, d) == 0
    tra = db.execute(select(SoDiem).where(SoDiem.voucher_id == v.id, SoDiem.loai == "TRA_GIU")).scalars().one()
    assert tra.so_diem == 1_500
    # 2) giữ phòng hết 15 phút chưa trả → voucher trả; tiền về muộn → hủy hoàn đủ
    v2 = _vc(db, ma="VTD-CCCCCC")
    d2 = _dat(db, k, g, ma_voucher=v2.ma)
    S.cap_nhat(db, d2, NAY + dt.timedelta(minutes=16)); db.commit()
    assert d2.trang_thai == "het_han" and v2.trang_thai == "da_hoan"
    P.match_transaction(db, _txn(db, d2.tong, d2.ma, sid="T7")); db.commit()
    assert d2.trang_thai == "da_huy" and d2.so_hoan == d2.tong
    # 3) hủy sau hạn (gói không còn hoàn) → voucher đã dùng hẳn, VTD chịu
    v3 = _vc(db, ma="VTD-DDDDDD")
    d3 = _dat(db, k, g, ma_voucher=v3.ma)
    _tra(db, d3, sid="T8")
    S.huy_boi_khach(db, _tk(db), d3.ma, "", dt.datetime(2026, 12, 17, 10, 0)); db.commit()
    assert d3.so_hoan == 0 and v3.trang_thai == "da_dung" and S.khuyen_mai(db, d3) == 150_000
    S.kt_chot(db, _u(db, "kt"), d3.id, 0, SAU); db.commit()
    assert d3.phai_tra_ks == 3_800_000                                                    # 3.650.000 + 150.000


def test_hoan_mot_phan_tru_voucher():
    from app.services import don_ks_vtd as S
    d = SimpleNamespace(giam_voucher=200_000, dong=[
        {"tien": 2_000_000, "thue": 0, "huy_han": "2026-12-16"},     # còn hạn miễn phí
        {"tien": 3_000_000, "thue": 0, "huy_han": None}])            # không hoàn
    assert S.so_hoan_neu_huy(d, 4_800_000, dt.date(2026, 12, 1)) == 1_800_000
    d.giam_voucher = 0
    assert S.so_hoan_neu_huy(d, 5_000_000, dt.date(2026, 12, 1)) == 2_000_000


def test_mot_don_mot_chu_diem_va_doi_tac(db, k3, bat):
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.services import rewards as RW
    k, lp, g = k3
    tk = _tk(db)
    tk.email = "lan@vd.vn"; db.commit()
    assert RW.chu_chinh(tk) == CHU
    d = _dat(db, k, g)
    assert [x.ma for x in RW._don_ks(db, CHU)] == [d.ma] and RW._don_ks(db, "email:lan@vd.vn") == []
    dt_tk = TaiKhoanNgoai(loai="doi_tac", dien_thoai="0901000009", ho_ten="Đại lý", trang_thai="hoat_dong")
    db.add(dt_tk); db.commit()
    assert not RW.he_so_cua(db, dt_tk, NAY.date())["dang_bat"]
    with pytest.raises(RW.LoiDiem, match="đối tác"):
        RW.kiem_voucher_ks(db, dt_tk, "VTD-AAAAAA", 3_800_000, NAY.date())
