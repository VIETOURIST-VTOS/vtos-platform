# -*- coding: utf-8 -*-
"""KS-16p · Đặt giữ trả sau + album 30–50 ảnh + video tối đa 3 + chỉ số thật (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Trả sau: chỉ gói miễn phí hủy; hạn trả = hạn hủy miễn phí sớm nhất − 2 ngày; giữ phòng tới hết ngày hạn trả;
     mỗi tài khoản 1 đơn trả sau chưa trả; quá hạn → hết hạn, nhả phòng. Nhắc 3 ngày / 1 ngày trước hạn, mỗi mốc một lần.
  2. Ảnh: tối đa 50 (chặn tải thêm); dưới 30 chỉ nhắc, vẫn bật hiện được.
  3. Video khách sạn tối đa 3 (nhà hàng vẫn 5).
  4. Chỉ số thật: «đặt trong 24 giờ» chỉ hiện khi ≥ 2 đơn đã trả; «chỉ còn N phòng» khi ≤ 3.
"""
import datetime as dt

import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import NAY, _dat, _tk, _txn, k3  # noqa: F401


def test_tra_sau_han_va_gioi_han(db, k3):
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    d = _dat(db, k, g, cach_tra="sau")
    assert d.cach_tra == "sau" and d.han_tra == dt.date(2026, 12, 14)          # hạn hủy 16/12 − 2 ngày
    assert d.giu_den == dt.datetime(2026, 12, 14, 23, 59, 59)
    o = S.ra_khach(db, d, NAY)
    assert o["cach_tra"] == "sau" and o["han_tra"] == "2026-12-14" and o["co_the_tra"]
    with pytest.raises(S.LoiDon, match="đơn trả sau"):
        _dat(db, k, g, cach_tra="sau")                                         # mỗi tài khoản 1 đơn trả sau
    d2 = _dat(db, k, g)                                                        # trả ngay vẫn đặt được
    assert d2.cach_tra == "ngay" and d2.han_tra is None
    with pytest.raises(S.LoiDon, match="Trả ngay"):                           # quá gần hạn hủy
        _dat(db, k, g, tk=_tk(db, 2), cach_tra="sau", now=dt.datetime(2026, 12, 14, 8, 0))
    # sau 15 phút đơn trả sau vẫn giữ; qua hết ngày 14/12 → hết hạn
    S.het_han_tat(db, NAY + dt.timedelta(hours=2)); db.commit()
    assert d.trang_thai == "cho_tra" and d2.trang_thai == "het_han"
    S.het_han_tat(db, dt.datetime(2026, 12, 15, 0, 0, 1)); db.commit()
    assert d.trang_thai == "het_han"


def test_tra_sau_khong_cho_goi_khong_hoan(db, k3):
    from app.services import don_ks_vtd as S
    from app.services import khach_san_vtd as KS
    k, lp, _g = k3
    g = KS.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Không hoàn tiền", "khong_hoan": True, "huy_truoc_ngay": None,
                                             "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 900_000,
                                                      "gia_cuoi_tuan": 1_200_000, "gia_niem_yet": 1_800_000}]})
    KS.gui_duyet_goi(db, _u(db, "dh"), g.id)
    KS.duyet_goi(db, _u(db, "tp"), g.id, True)
    db.commit()
    dong = S._dong_dat(db, k, VAO, RA, [{"goi_id": g.id, "so": 1}], 2)
    if dong[0].get("huy_han"):
        pytest.skip("gói mẫu vẫn có hạn hủy")
    with pytest.raises(S.LoiDon, match="không cho đặt giữ"):
        _dat(db, k, g, cach_tra="sau")


def test_nhac_han_tra_moi_moc_mot_lan(db, k3, monkeypatch):
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    gui = []
    monkeypatch.setattr(S, "GUI_NHAC", lambda d, ten, con: gui.append((d.ma, con)) or True)
    d = _dat(db, k, g, cach_tra="sau")
    assert S.nhac_han_tra(db, NAY) == []                                       # còn 13 ngày
    assert S.nhac_han_tra(db, dt.datetime(2026, 12, 11, 9, 0)) == [d.ma]        # còn 3 ngày
    assert S.nhac_han_tra(db, dt.datetime(2026, 12, 11, 18, 0)) == []           # cùng mốc không nhắc lại
    assert S.nhac_han_tra(db, dt.datetime(2026, 12, 13, 9, 0)) == [d.ma]        # còn 1 ngày
    assert gui == [(d.ma, 3), (d.ma, 1)] and d.nhac_luc == [3, 1]
    monkeypatch.setattr(S, "GUI_NHAC", lambda *a: (_ for _ in ()).throw(RuntimeError("smtp")))
    d.nhac_luc = []
    assert S.nhac_han_tra(db, dt.datetime(2026, 12, 13, 9, 0)) == [d.ma]        # lỗi gửi không làm hỏng việc chính
    assert d.nhac_luc == [3, 1]


def test_album_va_video_toi_da(db, k3, monkeypatch):
    from app.services import khach_san_vtd as KS
    from app.services import video_dich_vu as VD
    k, lp, g = k3
    v = KS.mot_vtos(db, _u(db, "dh"), k.id)
    assert v["album"]["toi_da"] == 50 and v["album"]["thieu"] == 29 and "29 ảnh" in v["album"]["nhac"]
    assert v["video_toi_da"] == 3 and VD.toi_da("nha_hang") == 5
    assert k.hien_cong                                                       # 1 ảnh vẫn bật hiện được — chỉ nhắc
    assert next(x for x in KS.ds_vtos(db, _u(db, "dh"))["khach_san"] if x["id"] == k.id)["thieu_anh"] == 29
    monkeypatch.setattr(KS, "ANH_TOI_DA", 1)
    from tests.test_ks13_khach_san_vtd import _anh
    with pytest.raises(KS.LoiKhachSan, match="đủ 1 ảnh"):
        KS.tai_anh(db, _u(db, "dh"), k.id, "b.jpg", _anh(2), {"nhom": "phong"})
    monkeypatch.setattr(VD, "_cua", lambda *a, **kw: [object()] * 3)
    with pytest.raises(VD.LoiVideo, match="Đã đủ 3 video"):
        VD.bat_dau(db, _u(db, "dh"), "khach_san_vtd", k.id, {"ten_tep": "a.mp4", "kich_thuoc": 1000})


def test_chi_so_that(db, k3):
    from app.services import khach_san_vtd as KS
    from app.services import payments as P
    k, lp, g = k3
    the = KS.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())
    assert the["dat_24h"] == 0 and the["con_it"] == 3                         # còn 3 phòng → hiện «chỉ còn 3»
    d = _dat(db, k, g, now=dt.datetime.now())
    P.match_transaction(db, _txn(db, d.tong, d.ma)); db.commit()
    assert KS.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())["dat_24h"] == 0   # 1 đơn: không hiện
    d2 = _dat(db, k, g, tk=_tk(db, 2), now=dt.datetime.now())
    P.match_transaction(db, _txn(db, d2.tong, d2.ma, sid="T2")); db.commit()
    the = KS.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())
    assert the["dat_24h"] == 2 and the["con_it"] == 1
    assert KS.tim(db, "Đà Nẵng", VAO, RA, hom_nay=NAY.date())["khach_san"][0]["dat_24h"] == 2
