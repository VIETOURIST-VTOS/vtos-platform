# -*- coding: utf-8 -*-
"""KS-16b · Voucher VTD Rewards khi trả trước đặt bàn (Chủ tịch duyệt 30/10/2026).

  1. Khách / cổ đông tự đặt nhập voucher trước khi trả: trừ vào số phải trả trước; trần = 5% tạm tính và không quá
     số trả trước. Đại lý / CTV không dùng. Đã trả thì không áp / bỏ được.
  2. Nhà hàng coi như đã nhận đủ trước: thu tại bàn và tiền thu hộ tính cả voucher. Đã dùng → Kế toán chốt ghi
     Nợ 641 / Có 3388 phần voucher.
  3. Như khách sạn: hủy có hoàn / chưa trả đồng nào → trả điểm voucher; không hoàn đồng nào → voucher dùng hẳn, nhà
     hàng nhận phần phạt còn thiếu từ voucher (Kế toán ghi tay).
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_dt2_dat_ban import NAY, _dat, _ncc, _nhan, _tk, _tra_qr, _u, db  # noqa: F401

CHU = "sdt:0901000001"


def _vc(s, gia_tri, ma):
    from app.models.rewards import SoDiem, VoucherRewards
    s.add(SoDiem(chu=CHU, loai="GIU", so_diem=-gia_tri // 100, luc=NAY, ghi_chu="đổi"))
    v = VoucherRewards(ma=ma, chu=CHU, so_diem=gia_tri // 100, gia_tri=gia_tri,
                       han_dung=NAY.date() + dt.timedelta(days=30), tao_luc=NAY)
    s.add(v); s.commit()
    return v


def _ct(s, ma):
    from app.models.accounting import JournalEntry
    e = s.execute(select(JournalEntry).where(JournalEntry.code == ma)).scalars().one()
    return sorted((l.account_code, int(l.debit), int(l.credit)) for l in e.lines)


def test_tra_du_voucher_va_chot(db):
    from app.models.cong_khach import YeuCauKhach
    from app.services import dat_ban as S
    v = _vc(db, 50_000, "VTD-AAAAAA")
    d = _nhan(db, _dat(db, nl=4, cach="du"))                                     # tạm tính 1.800.000, trả đủ
    S.ap_voucher(db, _tk(db, "0901000001"), d.ma, " vtd-aaaaaa ", NAY)
    assert int(d.phai_tra_truoc) == 1_750_000 and d.giam_voucher == 50_000 and v.trang_thai == "da_dung" and v.dat_ban_id == d.id
    r = S.ra(db, d, NAY)
    assert r["tra_tai_ban_du_kien"] == 1_750_000 and r["voucher"]["ma"] == "VTD-AAAAAA"
    _tra_qr(db, d)
    assert d.trang_thai == "da_giu" and S.ra(db, d, NAY)["tra_tai_ban_du_kien"] == 0
    with pytest.raises(S.LoiDatBan, match="Đã trả"):
        S.bo_voucher(db, _tk(db, "0901000001"), d.ma, NAY)
    n = S.ra_ncc(db, d, NAY)
    assert n["da_tra_vtd"] == 1_800_000 and n["thu_tai_ban_du_kien"] == 0 and n["phai_tra_truoc"] == 1_800_000
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(db, _tk(db, "0901000004"), _ncc(db), db.get(YeuCauKhach, d.yeu_cau_id).id, 2_000_000, 200_000, "", now=ve)
    db.commit()
    assert S.khuyen_mai(db, d) == 50_000
    S.kt_chot(db, _u(db, "kt"), d.id, 2_000_000, ve); db.commit()
    # ĐỢT TKC-5 08/11/2026 — `641` là tài khoản TỔNG HỢP (sáu con). Voucher VTD Rewards ghi
    # vào `6418` (chi phí bằng tiền khác) theo bảng khai `services/tk_chi_tiet.py`.
    assert _ct(db, d.km_but_toan) == [("3388", 0, 50_000), ("6418", 50_000, 0)]
    th = S.thu_ho_ncc(db, _ncc(db))[0]
    assert th["thuoc_nha_hang"] == 1_800_000 and th["voucher_vtd"] == 50_000


def test_tran_doi_tac_va_bo_voucher(db):
    from app.services import dat_ban as S
    _vc(db, 50_000, "VTD-BBBBBB")
    v2 = _vc(db, 40_000, "VTD-CCCCCC")
    d = _nhan(db, _dat(db, nl=2, cach="coc"))                                    # tạm tính 900.000, cọc 90.000
    with pytest.raises(S.LoiDatBan, match="45.000"):
        S.ap_voucher(db, _tk(db, "0901000001"), d.ma, "VTD-BBBBBB", NAY)          # trần 5% = 45.000
    S.ap_voucher(db, _tk(db, "0901000001"), d.ma, "VTD-CCCCCC", NAY)
    assert int(d.phai_tra_truoc) == 50_000
    with pytest.raises(S.LoiDatBan, match="bỏ voucher cũ"):
        S.ap_voucher(db, _tk(db, "0901000001"), d.ma, "VTD-BBBBBB", NAY)
    S.bo_voucher(db, _tk(db, "0901000001"), d.ma, NAY)
    assert int(d.phai_tra_truoc) == 90_000 and v2.trang_thai == "cho_dung" and v2.dat_ban_id is None
    dl = _nhan(db, _dat(db, tk="0901000003", ten_khach="Minh", dien_thoai="0901000001", dong_y_khach=True, nl=2))
    with pytest.raises(S.LoiDatBan, match="đại lý"):
        S.ap_voucher(db, _tk(db, "0901000003"), dl.ma, "VTD-CCCCCC", NAY)


def test_huy_va_khong_den(db):
    from app.models.cong_khach import YeuCauKhach
    from app.models.rewards import SoDiem
    from app.services import dat_ban as S
    # hủy sớm → hoàn đủ tiền mặt, voucher trả điểm
    v = _vc(db, 40_000, "VTD-DDDDDD")
    d = _nhan(db, _dat(db, nl=2, cach="coc"))
    S.ap_voucher(db, _tk(db, "0901000001"), d.ma, v.ma, NAY)
    _tra_qr(db, d)
    S.huy_boi_nguoi_dat(db, _tk(db, "0901000001"), d.ma, "", NAY)
    assert d.so_hoan == 50_000 and v.trang_thai == "da_hoan" and S.khuyen_mai(db, d) == 0
    assert db.execute(select(SoDiem).where(SoDiem.voucher_id == v.id, SoDiem.loai == "TRA_GIU")).scalars().one().so_diem == 400
    # không đến: phạt 10% = 90.000 > 50.000 tiền mặt → voucher dùng hẳn, nhà hàng nhận thêm 40.000 từ voucher
    v2 = _vc(db, 40_000, "VTD-EEEEEE")
    d2 = _nhan(db, _dat(db, nl=2, cach="coc", gio="19:00"))
    S.ap_voucher(db, _tk(db, "0901000001"), d2.ma, v2.ma, NAY)
    _tra_qr(db, d2, sid="T2")
    S.ncc_khong_den(db, _tk(db, "0901000004"), _ncc(db), db.get(YeuCauKhach, d2.yeu_cau_id).id,
                    now=S.gio_an(d2) + dt.timedelta(minutes=40)); db.commit()
    assert d2.so_hoan == 0 and v2.trang_thai == "da_dung" and S.khuyen_mai(db, d2) == 40_000
    S.kt_ghi_km(db, _u(db, "kt"), d2.id, NAY); db.commit()
    assert _ct(db, d2.km_but_toan) == [("3388", 0, 40_000), ("6418", 40_000, 0)]
    with pytest.raises(S.LoiDatBan, match="Đã ghi"):
        S.kt_ghi_km(db, _u(db, "kt"), d2.id, NAY)
    # chưa trả mà hết hạn trả → voucher trả điểm
    v3 = _vc(db, 40_000, "VTD-FFFFFF")
    d3 = _nhan(db, _dat(db, nl=2, cach="coc", gio="20:00"))
    S.ap_voucher(db, _tk(db, "0901000001"), d3.ma, v3.ma, NAY)
    S.cap_nhat(db, d3, d3.han_tra + dt.timedelta(minutes=1)); db.commit()
    assert d3.trang_thai == "het_han" and v3.trang_thai == "da_hoan"
