# -*- coding: utf-8 -*-
"""KS-16d · Tự lập đề nghị chi trả khách sạn / nhà hàng tiền thu hộ (Chủ tịch chốt 31/10/2026).

  1. Mỗi đơn một đề nghị: Kế toán chốt đơn khách sạn → máy lập ngay đề nghị chi loại «tra_ncc_thu_ho» bằng đúng
     phải trả khách sạn, cho công ty mẹ, bước đầu chờ TP Điều hành xác nhận.
  2. Đặt bàn: Kế toán gõ hoa hồng lúc chốt; phải trả nhà hàng = thu hộ − hoàn + voucher VTD chịu − hoa hồng → đề nghị chi.
  3. Duyệt đề nghị: Nợ 3388 / Có 331 (xóa khoản thu hộ, ghi phải trả NCC); chi: Nợ 331 / Có 112.
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_ks14_dat_phong_vtd import NAY, _dat, k3  # noqa: F401
from tests.test_ks16_rewards_khach_san import SAU, _tra, _vc, bat  # noqa: F401
from tests.test_at1_am_thuc import _u, db  # noqa: F401


def _dong(s, r):
    from app.models.accounting import JournalEntry
    e = s.get(JournalEntry, r.entry_ids[-1])
    return sorted((l.account_code, int(l.debit), int(l.credit)) for l in e.lines)


def test_khach_san_chot_lap_de_nghi(db, k3, bat):
    from app.models.core import Company
    from app.models.ops import PaymentRequest
    from app.models.suppliers import Supplier
    from app.services import don_ks_vtd as S
    from app.services import ops as O
    k, lp, g = k3
    _vc(db)
    d = _dat(db, k, g, ma_voucher="VTD-AAAAAA")
    _tra(db, d)
    S.dh_xac_nhan(db, _u(db, "dh"), d.id, "BX-9", NAY); db.commit()
    S.kt_chot(db, _u(db, "kt"), d.id, 400_000, SAU); db.commit()
    r = db.get(PaymentRequest, d.payment_request_id)
    assert r.category == "tra_ncc_thu_ho" and int(r.amount) == 3_970_000 == d.phai_tra_ks
    assert r.has_document and d.ma in r.description and "BX-9" in r.document_ref
    assert r.company_id == db.execute(select(Company.id).where(Company.kind == "me")).scalar_one()
    # robot kế toán: xác nhận thay bộ phận; khách sạn chưa gắn NCC → DỪNG ở bước kiểm, ghi lý do
    assert r.status == "cho_kt" and r.tp_by == "robot" and "chưa gắn nhà cung cấp" in r.robot_ghi_chu
    kt = S.hang_ke_toan(db, _u(db, "kt"), SAU)["phai_tra_ks"][0]["de_nghi_chi"]
    assert kt == [{"don": d.ma, "id": r.id, "code": r.code, "status": "cho_kt", "so_tien": 3_970_000}]
    for ai, buoc in (("tp", "confirm"), ("kt", "check")):
        with pytest.raises(ValueError, match="robot"):
            O.step(db, _u(db, ai), r, buoc)
    # bổ sung NCC thiếu số tài khoản → robot vẫn dừng; đủ → chuyển duyệt, lấy tên / MST / tài khoản từ danh bạ NCC
    sup = Supplier(code="NCC0099", ten="CTY TNHH Ocean Haven", loai="khach_san", ma_so_thue="0312345678")
    db.add(sup); db.flush(); k.supplier_id = sup.id; db.commit()
    S.robot_kiem_de_nghi(db, _u(db, "kt"), r)
    assert r.status == "cho_kt" and "thiếu số tài khoản" in r.robot_ghi_chu
    sup.so_tai_khoan, sup.ngan_hang = "0123456789", "VCB"; db.commit()
    S.robot_kiem_de_nghi(db, _u(db, "kt"), r)
    assert r.status == "cho_duyet" and r.kt_by == "robot" and r.robot_ghi_chu == ""
    assert r.supplier_name == "CTY TNHH Ocean Haven" and r.supplier_tax_code == "0312345678" and "0123456789" in r.supplier_bank
    with pytest.raises(S.LoiDon, match="đang chờ kiểm"):
        S.robot_kiem_de_nghi(db, _u(db, "kt"), r)
    O._post_liability(db, r); db.commit()
    assert _dong(db, r) == [("331", 0, 3_970_000), ("3388", 3_970_000, 0)]
    assert db.execute(select(PaymentRequest).where(PaymentRequest.category == "tra_ncc_thu_ho")).scalars().all() == [r]
    with pytest.raises(ValueError, match="máy tự lập"):
        O.create_request(db, _u(db, "kt"), {"category": "tra_ncc_thu_ho", "supplier_name": "X", "amount": 1, "description": "x"})


def test_khach_san_khong_con_gi_tra_thi_khong_lap(db, k3, bat):
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    d = _dat(db, k, g)
    _tra(db, d)
    S.dh_xac_nhan(db, _u(db, "dh"), d.id, "BX-1", NAY); db.commit()
    S.kt_chot(db, _u(db, "kt"), d.id, int(d.tong), SAU); db.commit()          # hoa hồng = toàn bộ → phải trả 0
    assert d.phai_tra_ks == 0 and d.payment_request_id is None



def _cho_duyet(db, ma):
    from app.models.ops import PaymentRequest
    r = PaymentRequest(code=ma, category="tra_ncc_thu_ho", supplier_name="KS A", amount=900_000_000,
                       description="x", has_document=True, created_by="kt", status="cho_duyet", tp_by="tp")
    db.add(r); db.commit()
    return r


def test_tgd_hoac_chu_tich_mot_nguoi_bam_la_xong(db, k3, bat):
    """Chủ tịch chốt 31/10/2026: TGĐ / Chủ tịch đều ký được và đều có nút; một trong hai bấm thì bên kia chỉ còn thấy."""
    from app.models.core import User
    from app.services import ops as O
    db.add(User(username="tgd1", full_name="TGĐ", role="tgd", password_hash="x")); db.commit()
    nguoi = lambda t: db.query(User).filter_by(username=t).one()
    r = _cho_duyet(db, "DC-T1")                                       # 900 triệu, chưa chốt mốc vẫn duyệt được
    c = O.cap_duyet(db, r)
    assert c["can_tgd"] and c["can_chutich"] and not c["chua_chot"] and sorted(O.vai_ky_duoc(db, r)) == ["chutich", "tgd"]
    with pytest.raises(ValueError, match="TGĐ hoặc Chủ tịch"):
        O.step(db, nguoi("kd"), r, "approve")
    O.step(db, nguoi("tgd1"), r, "approve"); db.commit()
    assert r.status == "cho_chi" and r.signed_tgd and not r.signed_chutich and O.vai_ky_duoc(db, r) == []
    r2 = _cho_duyet(db, "DC-T2")
    O.step(db, nguoi("ct"), r2, "approve"); db.commit()
    assert r2.status == "cho_chi" and r2.signed_chutich and not r2.signed_tgd


def test_da_chi_phai_co_unc(db, k3, bat):
    """Chủ tịch chốt 31/10/2026: MỌI loại chi — tải UNC / phiếu chi rồi mới bấm «Đã chi»."""
    from app.models.attachments import Attachment
    from app.services import ops as O
    r = _cho_duyet(db, "DC-U1")
    r.status = "cho_chi"; db.commit()
    with pytest.raises(ValueError, match="UNC"):
        O.step(db, _u(db, "kt"), r, "pay", "CK 1")
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id="DC-U1", loai="chung_tu", ten_tep="hd.pdf", checksum="a", khoa_luu="a"))
    db.commit()
    with pytest.raises(ValueError, match="UNC"):
        O.step(db, _u(db, "kt"), r, "pay", "CK 1")                    # chứng từ khác không thay được UNC
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id="DC-U1", loai="unc", ten_tep="unc.pdf", checksum="b", khoa_luu="b"))
    db.commit()
    O.step(db, _u(db, "kt"), r, "pay", "CK 1"); db.commit()
    assert r.status == "da_chi"
