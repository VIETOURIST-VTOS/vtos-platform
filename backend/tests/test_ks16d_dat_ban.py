# -*- coding: utf-8 -*-
"""KS-16d · Đặt bàn: Kế toán gõ hoa hồng lúc chốt → phải trả nhà hàng → máy lập một đề nghị chi."""
import datetime as dt

import pytest

from tests.test_dt2_dat_ban import NAY, _dat, _ncc, _nhan, _tk, _tra_qr, _u, db  # noqa: F401
from tests.test_ks16b_voucher_dat_ban import _vc


def _dung(db, d, bill=2_000_000):
    from app.models.cong_khach import YeuCauKhach
    from app.services import dat_ban as S
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(db, _tk(db, "0901000004"), _ncc(db), db.get(YeuCauKhach, d.yeu_cau_id).id, bill, 200_000, "", now=ve)
    db.commit()
    return ve


def test_chot_hoa_hong_lap_de_nghi(db):
    from app.models.ops import PaymentRequest
    from app.services import dat_ban as S
    _vc(db, 50_000, "VTD-AAAAAA")
    d = _nhan(db, _dat(db, nl=4, cach="du"))                                     # tạm tính 1.800.000
    S.ap_voucher(db, _tk(db, "0901000001"), d.ma, "VTD-AAAAAA", NAY)
    _tra_qr(db, d)                                                               # khách trả 1.750.000
    ve = _dung(db, d)
    with pytest.raises(S.LoiDatBan, match="1.800.000"):
        S.kt_chot(db, _u(db, "kt"), d.id, 2_000_000, ve, 1_900_000)
    S.kt_chot(db, _u(db, "kt"), d.id, 2_000_000, ve, 180_000); db.commit()
    assert d.hoa_hong == 180_000 and d.phai_tra_nh == 1_620_000                  # 1.750.000 + 50.000 − 180.000
    r = db.get(PaymentRequest, d.payment_request_id)
    assert r.category == "tra_ncc_thu_ho" and int(r.amount) == 1_620_000
    assert r.status == "cho_kt" and "thiếu số tài khoản" in r.robot_ghi_chu      # NCC có MST, chưa có số tài khoản
    sup = _ncc(db); sup.so_tai_khoan = "999888777"; db.commit()
    from app.services import don_ks_vtd as KS
    KS.robot_kiem_de_nghi(db, _u(db, "kt"), r)
    assert r.status == "cho_duyet"
    assert r.supplier_name == "Nhà hàng Hương Biển" and r.supplier_tax_code == "0311111111" and d.ma in r.description
    o = S.ra(db, d, ve, noi_bo=True)
    assert o["phai_tra_nh"] == 1_620_000 and o["de_nghi_chi"]["code"] == r.code


def test_chot_khong_hoa_hong(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, nl=2, cach="coc"))                                    # cọc 90.000
    _tra_qr(db, d)
    ve = _dung(db, d)
    S.kt_chot(db, _u(db, "kt"), d.id, 900_000, ve); db.commit()
    assert d.hoa_hong == 0 and d.phai_tra_nh == 90_000 and d.payment_request_id


def test_ks16e_dat_ban_ghi_doanh_thu_hoa_hong(db):
    """KS-16e: đã chi trả nhà hàng → Nợ 3388 / Có 511 hoa hồng; trả 0 → ghi ngay lúc chốt."""
    from app.models.attachments import Attachment
    from app.models.ops import PaymentRequest
    from app.services import dat_ban as S
    from app.services import ops as O
    from tests.test_ks16b_voucher_dat_ban import _ct
    from app.services import accounting as ACC
    ACC.seed_accounts(db)
    sup = _ncc(db); sup.so_tai_khoan = "999"; db.commit()
    d = _nhan(db, _dat(db, nl=2, cach="coc"))                                    # cọc 90.000
    _tra_qr(db, d)
    ve = _dung(db, d)
    S.kt_chot(db, _u(db, "kt"), d.id, 900_000, ve, 20_000); db.commit()
    r = db.get(PaymentRequest, d.payment_request_id)
    assert r.status == "cho_duyet" and d.dt_but_toan == ""
    r.status = "cho_chi"
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id=r.code, loai="unc", ten_tep="u.pdf", checksum="u", khoa_luu="u"))
    db.commit()
    O.step(db, _u(db, "kt"), r, "pay", "CK 9")
    assert _ct(db, d.dt_but_toan) == [("3388", 20_000, 0), ("511", 0, 20_000)]
    with pytest.raises(S.LoiDatBan, match="Đã ghi"):
        S.kt_ghi_dt_hoa_hong(db, _u(db, "kt"), d.id, ve)
    d2 = _nhan(db, _dat(db, nl=2, cach="coc", gio="19:00"))
    _tra_qr(db, d2, sid="T2")
    ve2 = _dung(db, d2)
    S.kt_chot(db, _u(db, "kt"), d2.id, 900_000, ve2, 90_000); db.commit()        # hoa hồng = toàn bộ → trả 0
    assert d2.payment_request_id is None and _ct(db, d2.dt_but_toan) == [("3388", 90_000, 0), ("511", 0, 90_000)]
