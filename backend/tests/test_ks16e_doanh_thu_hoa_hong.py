# -*- coding: utf-8 -*-
"""KS-16e · Doanh thu hoa hồng khách sạn / nhà hàng (Chủ tịch chốt 31/10/2026).

  1. Ghi KHI ĐÃ CHI trả NCC: Kế toán bấm «Đã chi» đề nghị tra_ncc_thu_ho → Nợ 3388 / Có 511 = hoa hồng (chưa gồm VAT).
  2. Phải trả NCC = 0 (hoa hồng = toàn bộ tiền giữ) → ghi ngay lúc chốt.
  3. Đơn cũ (chốt trước, không có đề nghị chi) → Kế toán bấm ghi bù từng đơn; ghi rồi không ghi lại.
"""
import pytest
from sqlalchemy import select

from tests.test_ks14_dat_phong_vtd import NAY, _dat, k3  # noqa: F401
from tests.test_ks16_rewards_khach_san import SAU, _ct, _tra, bat  # noqa: F401
from tests.test_at1_am_thuc import _u, db  # noqa: F401


def _xong_don(db, k, g, sid="T1"):
    from app.services import don_ks_vtd as S
    d = _dat(db, k, g)
    _tra(db, d, sid=sid)
    S.dh_xac_nhan(db, _u(db, "dh"), d.id, "BX-" + sid, NAY); db.commit()
    return d


def test_ghi_khi_da_chi_tra_khach_san(db, k3, bat):
    from app.models.attachments import Attachment
    from app.models.ops import PaymentRequest
    from app.models.suppliers import Supplier
    from app.services import don_ks_vtd as S
    from app.services import ops as O
    k, lp, g = k3
    sup = Supplier(code="NCC0099", ten="CTY Ocean Haven", loai="khach_san", ma_so_thue="0312345678", so_tai_khoan="0123")
    db.add(sup); db.flush(); k.supplier_id = sup.id; db.commit()
    d = _xong_don(db, k, g)
    S.kt_chot(db, _u(db, "kt"), d.id, 400_000, SAU); db.commit()
    r = db.get(PaymentRequest, d.payment_request_id)
    assert r.status == "cho_duyet" and d.dt_but_toan == ""                          # chưa chi → chưa ghi doanh thu
    assert S.hang_ke_toan(db, _u(db, "kt"), SAU)["cho_ghi_dt"] == []
    with pytest.raises(S.LoiDon, match="đã chi"):
        S.kt_ghi_dt_hoa_hong(db, _u(db, "kt"), d.id, SAU)
    r.status = "cho_chi"; db.commit()
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id=r.code, loai="unc", ten_tep="unc.pdf", checksum="u", khoa_luu="u"))
    db.commit()
    O.step(db, _u(db, "kt"), r, "pay", "CK 7", "chuyen_khoan")
    assert r.status == "da_chi" and d.dt_but_toan
    assert _ct(db, d.dt_but_toan) == [("3388", 400_000, 0), ("511", 0, 400_000)]
    with pytest.raises(S.LoiDon, match="Đã ghi"):
        S.kt_ghi_dt_hoa_hong(db, _u(db, "kt"), d.id, SAU)


def test_tra_0_ghi_ngay_va_ghi_bu_don_cu(db, k3, bat):
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    d = _xong_don(db, k, g)
    S.kt_chot(db, _u(db, "kt"), d.id, int(d.tong), SAU); db.commit()                # hoa hồng = toàn bộ → trả 0
    assert d.payment_request_id is None and _ct(db, d.dt_but_toan) == [("3388", int(d.tong), 0), ("511", 0, int(d.tong))]
    # đơn chốt trước KS-16e: có hoa hồng, không đề nghị chi, chưa có bút toán → hiện danh sách chờ ghi, Kế toán ghi bù
    d2 = _xong_don(db, k, g, sid="T2")
    d2.hoa_hong, d2.phai_tra_ks, d2.chot_luc = 300_000, int(d2.tong) - 300_000, SAU; db.commit()
    cho = S.hang_ke_toan(db, _u(db, "kt"), SAU)["cho_ghi_dt"]
    assert [x["ma"] for x in cho] == [d2.ma] and cho[0]["hoa_hong"] == 300_000
    with pytest.raises(S.LoiDon):
        S.kt_ghi_dt_hoa_hong(db, _u(db, "dh"), d2.id, SAU)                          # không phải Kế toán
    S.kt_ghi_dt_hoa_hong(db, _u(db, "kt"), d2.id, SAU); db.commit()
    assert _ct(db, d2.dt_but_toan) == [("3388", 300_000, 0), ("511", 0, 300_000)]
    assert S.hang_ke_toan(db, _u(db, "kt"), SAU)["cho_ghi_dt"] == []
