# -*- coding: utf-8 -*-
"""KS-20d · Tìm nhiều phòng ghép được nhiều loại phòng (thử thật 06/11/2026: tìm 3 phòng ra 0 khách sạn vì mỗi loại
chỉ còn 2 phòng). Chủ tịch chọn «Cộng các loại phòng»: khách sạn hiện khi TỔNG các loại phòng có gói hợp người còn đủ
số phòng khách cần; một loại phòng không cần tự đủ."""
from tests.test_at1_am_thuc import db  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _ks, _mo_ban
from tests.test_ks20b_chia_phong import _family


def test_ks20d_1_cong_cac_loai_phong(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)                                   # Deluxe 3 phòng
    fl, fg = _family(db, k)                                      # Family 2 phòng
    assert len(S.tim(db, "Đà Nẵng", VAO, RA, 5, 0, 5, hom_nay=HN)["khach_san"]) == 1     # 3 + 2 = 5 phòng
    o = S.tim(db, "Đà Nẵng", VAO, RA, 4, 0, 4, hom_nay=HN)["khach_san"][0]
    assert {x["lp"] for x in o["goi_ban"]} == {lp.id, fl.id}     # cả hai loại đều là offer của tìm 4 phòng
    assert S.tim(db, "Đà Nẵng", VAO, RA, 6, 0, 6, hom_nay=HN)["khach_san"] == []          # 6 > 5 phòng còn


def test_ks20d_2_du_phong():
    from app.services import khach_san_vtd as S
    gb = [{"lp": 1, "con": 2}, {"lp": 1, "con": 2}, {"lp": 2, "con": 1}]
    assert S.du_phong(gb, 3) and not S.du_phong(gb, 4) and S.du_phong([], 0) is False
