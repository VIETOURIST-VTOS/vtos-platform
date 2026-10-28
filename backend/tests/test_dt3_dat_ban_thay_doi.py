# -*- coding: utf-8 -*-
"""DT-3 · Đặt bàn đợt 2 (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Đổi lịch: báo trước 24 giờ, miễn phí 1 lần, nhà hàng nhận lại khung mới; từ chối → giữ lịch cũ hoặc hủy hoàn đủ.
  2. Số khách: bớt áp ngay (trước 24 giờ theo số mới; trong 24 giờ tính tối thiểu 80%), phần trả dư thành khoản hoàn;
     thêm chờ nhà hàng nhận, đủ đoàn thì cọc 50%, trả thêm được khi đang giữ bàn.
  3. Ghi sổ (đại lý thu hộ, sổ công ty mẹ): tiền QR Nợ 1121 / Có 3388; thẻ Nợ 1121 + Nợ 6428 phí / Có 3388; hoàn
     Nợ 3388 / Có 1121; hoàn được nhiều lần, không hoàn quá số phải hoàn.
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_dt2_dat_ban import NAY, NGAY, _dat, _ncc, _nhan, _tk, _tra_qr, _txn, _u, db  # noqa: F401


def _yc(s, d):
    from app.models.cong_khach import YeuCauKhach
    return s.get(YeuCauKhach, d.yeu_cau_id)


def _ct(s, ma):
    from app.models.accounting import JournalEntry
    e = s.execute(select(JournalEntry).where(JournalEntry.code == ma)).scalars().one()
    return e, sorted((l.account_code, int(l.debit), int(l.credit), l.partner) for l in e.lines)


def test_1_doi_lich_nha_hang_nhan_mot_lan(db):
    from app.services import dat_ban as S
    tk = _tk(db, "0901000001")
    d = _nhan(db, _dat(db, cach="du")); _tra_qr(db, d, sid="A")
    moi = NGAY + dt.timedelta(days=1)
    S.thay_doi(db, tk, d.ma, moi, "19:00", None, None, NAY)
    assert d.thay_doi == {"ngay": moi.isoformat(), "gio": "19:00", "nguoi_lon": 2, "tre_em": 0} and d.ngay == NGAY
    with pytest.raises(S.LoiDatBan, match="chờ nhà hàng"):
        S.thay_doi(db, tk, d.ma, None, "", 3, None, NAY)
    S.ncc_thay_doi(db, _tk(db, "0901000004"), _ncc(db), _yc(db, d).id, True, now=NAY)
    assert d.ngay == moi and d.gio == "19:00" and d.so_lan_doi == 1 and d.thay_doi is None and d.trang_thai == "da_giu"
    assert _yc(db, d).ngay_mong_muon == moi and _yc(db, d).gio_den == "19:00"
    with pytest.raises(S.LoiDatBan, match="1 lần"):
        S.thay_doi(db, tk, d.ma, moi + dt.timedelta(days=1), "19:00", None, None, NAY)
    d2 = _nhan(db, _dat(db, cach="du")); _tra_qr(db, d2, sid="B")
    with pytest.raises(S.LoiDatBan, match="trước 24 giờ"):
        S.thay_doi(db, tk, d2.ma, moi, "19:00", None, None, S.gio_an(d2) - dt.timedelta(hours=5))


def test_1b_nha_hang_tu_choi_thi_huy_hoan_du(db):
    from app.services import dat_ban as S
    tk = _tk(db, "0901000001")
    d = _nhan(db, _dat(db, nl=10, cach="du")); _tra_qr(db, d, sid="C")
    S.thay_doi(db, tk, d.ma, NGAY + dt.timedelta(days=2), "12:00", None, None, NAY)
    with pytest.raises(S.LoiDatBan, match="lý do"):
        S.ncc_thay_doi(db, _tk(db, "0901000004"), _ncc(db), _yc(db, d).id, False, "", NAY)
    S.ncc_thay_doi(db, _tk(db, "0901000004"), _ncc(db), _yc(db, d).id, False, "Kín bàn", NAY)
    assert d.ngay == NGAY and d.huy_mien_phi and d.thay_doi is None
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=1))       # đoàn hủy sát giờ vẫn hoàn đủ
    assert d.so_giu == 0 and d.so_hoan == int(d.tam_tinh)


def test_1c_chua_nhan_ban_thi_ap_ngay(db):
    from app.services import dat_ban as S
    d = _dat(db, nl=2)
    S.thay_doi(db, _tk(db, "0901000001"), d.ma, NGAY + dt.timedelta(days=1), "20:00", 4, 1, NAY)
    assert d.thay_doi is None and d.nguoi_lon == 4 and d.tre_em == 1 and int(d.tam_tinh) == 4 * 450000 + 225000
    assert d.so_lan_doi == 1 and _yc(db, d).so_khach == 5


def test_2_bot_khach_truoc_va_trong_24_gio(db):
    from app.services import dat_ban as S
    tk = _tk(db, "0901000001")
    d = _nhan(db, _dat(db, nl=4, cach="du")); _tra_qr(db, d, sid="D")             # 1.800.000 đ đã trả
    S.thay_doi(db, tk, d.ma, None, "", 3, None, NAY)                                  # ≥24 giờ: theo số mới
    assert d.thay_doi is None and int(d.tam_tinh) == 1350000 and d.so_hoan == 450000 and d.hoan_tt == "cho_sales"
    d2 = _nhan(db, _dat(db, nl=10, cach="du")); _tra_qr(db, d2, sid="E")            # 4.500.000 đ
    S.thay_doi(db, tk, d2.ma, None, "", 5, None, S.gio_an(d2) - dt.timedelta(hours=10))
    assert int(d2.tam_tinh) == 3600000 and d2.so_hoan == 900000                      # tối thiểu 80%
    assert not d2.la_doan                                                             # còn 5 khách: không còn là đoàn


def test_2b_them_khach_thanh_doan_tra_them(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, nl=8, cach="coc")); _tra_qr(db, d, sid="F")               # cọc 10% của 3.600.000 = 360.000
    S.thay_doi(db, _tk(db, "0901000001"), d.ma, None, "", 10, None, NAY)
    assert d.thay_doi and d.nguoi_lon == 8                                            # chờ nhà hàng
    S.ncc_thay_doi(db, _tk(db, "0901000004"), _ncc(db), _yc(db, d).id, True, now=NAY)
    assert d.la_doan and d.ty_le_coc == 50 and int(d.phai_tra_truoc) == 2250000 and d.trang_thai == "da_giu"
    assert S._co_the_tra(d, S.da_tra(db, d))
    assert S.ra(db, d, NAY)["con_phai_tra_truoc"] == 2250000 - 360000


def test_3_ghi_so_thu_ho(db):
    from app.services import dat_ban as S
    from app.models.core import Company
    me = db.execute(select(Company)).scalars().one()
    d = _nhan(db, _dat(db, nl=4, cach="du"))
    t = _tra_qr(db, d, sid="G")
    tt = db.execute(select(S.ThanhToanDatBan).where(S.ThanhToanDatBan.bank_txn_id == t.id)).scalars().one()
    e, dong = _ct(db, tt.but_toan)
    assert dong == [("1121", 1800000, 0, ""), ("3388", 0, 1800000, "Nhà hàng Hương Biển")] and e.company_id == me.id
    # bớt khách → hoàn lần 1; hủy → hoàn lần 2; mỗi lần một phiếu chi đúng phần còn phải hoàn
    S.thay_doi(db, _tk(db, "0901000001"), d.ma, None, "", 3, None, NAY)
    S.sales_xac_nhan_hoan(db, _u(db, "nvkd"), d.id, "")
    S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 1", NAY)
    assert int(d.da_hoan_tien) == 450000
    with pytest.raises(S.LoiDatBan):
        S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 1b", NAY)                          # không còn gì phải hoàn
    S.huy_boi_nguoi_dat(db, _tk(db, "0901000001"), d.ma, "", S.gio_an(d) - dt.timedelta(days=2))
    assert d.so_hoan == 1800000 and d.hoan_tt == "cho_sales"
    S.sales_xac_nhan_hoan(db, _u(db, "nvkd"), d.id, "")
    S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 2", NAY)
    from app.models.accounting import JournalEntry
    hoan = db.execute(select(JournalEntry).where(JournalEntry.source_type == "dat_ban", JournalEntry.source_ref.like(f"{d.ma}:hoan%"))
                      .order_by(JournalEntry.id)).scalars().all()
    assert [int(sum(l.debit for l in e.lines if l.account_code == "3388")) for e in hoan] == [450000, 1350000]


def test_3b_doi_soat_the_ghi_phi(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, nl=2, cach="du"))
    t = S.ThanhToanDatBan(don_id=d.id, kenh="onepay", so_tien=900000, trang_thai="thanh_cong", ma_gd=f"{d.ma}T9", so_gd_cong="777", luc=NAY)
    db.add(t); db.commit()
    with pytest.raises(S.LoiDatBan, match="phí thẻ"):
        S.kt_doi_soat(db, _u(db, "kt"), t.id, None, NAY)
    S.kt_doi_soat(db, _u(db, "kt"), t.id, 19800, NAY)
    _e, dong = _ct(db, t.but_toan)
    assert dong == [("1121", 880200, 0, ""), ("3388", 0, 900000, "Nhà hàng Hương Biển"), ("6428", 19800, 0, "")]
    assert t.trang_thai == "da_doi_soat" and int(t.phi_the) == 19800
