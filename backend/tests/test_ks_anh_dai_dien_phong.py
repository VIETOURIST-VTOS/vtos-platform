# -*- coding: utf-8 -*-
"""KS-ANH (Chủ tịch 05/11/2026: «khách sạn nào chưa có ảnh phòng em lấy ảnh đại diện khách sạn»).

Trên cổng khách, loại phòng chưa có ảnh riêng thì hiện ảnh đại diện của khách sạn (ảnh bìa, cờ `anh_dai_dien`);
có ảnh riêng thì chỉ hiện ảnh riêng, không lẫn ảnh đại diện.
"""
from tests.test_at1_am_thuc import db, _u  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _anh, _ks, _mo_ban


def test_ks_anh_phong_chua_co_anh_lay_anh_dai_dien(db):
    from app.services import khach_san_vtd as S
    k = _ks(db, "Khách sạn Ảnh Đại Diện")
    lp, _g, x = _mo_ban(db, k)
    S.sua_anh(db, _u(db, "dh"), x.id, {"la_bia": True})
    p = next(o for o in S.chi_tiet_cong(db, k.id, VAO, RA, 2, 0, 1, hom_nay=HN)["phong"] if o["id"] == lp.id)
    assert p["anh_dai_dien"] is True and [a["id"] for a in p["anh"]] == [x.id]

    y, _ = S.tai_anh(db, _u(db, "dh"), k.id, "p.jpg", _anh(7), {"nhom": "phong", "loai_phong_id": lp.id})
    p = next(o for o in S.chi_tiet_cong(db, k.id, VAO, RA, 2, 0, 1, hom_nay=HN)["phong"] if o["id"] == lp.id)
    assert p["anh_dai_dien"] is False and [a["id"] for a in p["anh"]] == [y.id]
