# -*- coding: utf-8 -*-
"""KS-16s · Bản đồ, bộ lọc kiểu Agoda, giờ đến dự kiến, công tắc mở thanh toán (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Tọa độ: máy tự lấy từ địa chỉ khi lưu hồ sơ (dịch vụ tra địa chỉ — ở đây là hàm giả); Điều hành dán link Google
     Maps → «tay», máy không ghi đè; link rút gọn báo lỗi rõ; nút lấy hàng loạt chỉ cho TP Điều hành / Chủ tịch / TGĐ.
  2. Thanh toán chỉ mở khi CẢ công tắc chung và công tắc khách sạn đều bật — đặt, QR, thẻ đều bị chặn 409; có nhật ký.
  3. Giờ đến dự kiến lưu vào đơn; Điều hành chốt đơn → gửi email xác nhận (hàm giả), lỗi gửi không hỏng việc chốt.
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import VAO, RA
from tests.test_ks14_dat_phong_vtd import NAY, _dat, _tk, _txn, k3  # noqa: F401


def test_toa_do_tu_dong_link_tay_va_loat(db, k3, monkeypatch):
    from app.services import khach_san_vtd as S
    k, lp, g = k3
    hoi = []
    monkeypatch.setattr(S, "LAY_TOA_DO", lambda q: hoi.append(q) or (16.0544, 108.2453))
    S.luu_ks(db, _u(db, "dh"), {**S._ks_noi_bo(k), "dia_chi": "12 Võ Nguyên Giáp"}, k.id)
    db.refresh(k)
    assert (k.vi_do, k.kinh_do, k.toa_do_nguon) == (16.0544, 108.2453, "tu_dong") and "12 Võ Nguyên Giáp" in hoi[0]
    # link Google Maps đầy đủ → «tay»; đổi địa chỉ sau đó KHÔNG ghi đè
    S.luu_ks(db, _u(db, "dh"), {**S._ks_noi_bo(k), "link_ggmap":
                                "https://www.google.com/maps/place/X/@16.0611,108.2470,17z/data=!3d16.06123!4d108.24711"}, k.id)
    db.refresh(k)
    assert (k.vi_do, k.kinh_do, k.toa_do_nguon) == (16.06123, 108.24711, "tay")
    S.luu_ks(db, _u(db, "dh"), {**S._ks_noi_bo(k), "dia_chi": "99 Trần Phú"}, k.id)
    db.refresh(k)
    assert k.toa_do_nguon == "tay" and k.vi_do == 16.06123
    assert S.doc_link_ggmap("https://maps.google.com/?q=10.7769,106.7009") == (10.7769, 106.7009)
    with pytest.raises(S.LoiKhachSan, match="rút gọn"):
        S.doc_link_ggmap("https://maps.app.goo.gl/AbCdEf")
    with pytest.raises(S.LoiKhachSan, match="ngoài Việt Nam"):
        S.doc_link_ggmap("https://www.google.com/maps/@48.85,2.35,15z")
    # lấy hàng loạt: bỏ qua ghim tay, ghi «khong_thay» khi dịch vụ không ra kết quả
    k2 = S.luu_ks(db, _u(db, "dh"), {"ten": "Khách sạn Núi", "tinh_thanh": "Đà Nẵng", "sao": 3})
    k2.vi_do, k2.toa_do_nguon = None, ""
    db.commit()
    monkeypatch.setattr(S, "LAY_TOA_DO", lambda q: None)
    with pytest.raises(S.LoiKhachSan):
        S.lay_toa_do_loat(db, _u(db, "dh"), nghi=0)                     # NV Điều hành không chạy hàng loạt
    r = S.lay_toa_do_loat(db, _u(db, "tp"), nghi=0)
    assert r["co"] == 0 and r["khong_thay"] == [k2.ma]
    db.refresh(k2)
    assert k2.toa_do_nguon == "khong_thay"
    monkeypatch.setattr(S, "LAY_TOA_DO", lambda q: (_ for _ in ()).throw(OSError("mạng")))
    S.luu_ks(db, _u(db, "dh"), {**S._ks_noi_bo(k2), "dia_chi": "1 Bạch Đằng"}, k2.id)   # lỗi mạng không hỏng việc lưu


def test_cong_tac_thanh_toan_ca_hai(db, k3):
    from app.models.core import AuditLog
    from app.services import don_ks_vtd as D
    from app.services import khach_san_vtd as S
    k, lp, g = k3                                                        # mẫu mở sẵn cả hai công tắc
    assert S.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())["mo_thanh_toan"]
    S.bat_tt_ks(db, _u(db, "tp"), k.id, False)
    the = S.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())
    assert not the["mo_thanh_toan"] and the["phong"]                     # vẫn xem, chọn phòng được
    with pytest.raises(D.LoiDon, match="chưa mở") as e:
        _dat(db, k, g)
    assert e.value.status == 409
    S.bat_tt_ks(db, _u(db, "tp"), k.id, True)
    S.bat_tt_chung(db, _u(db, "tp"), False)
    with pytest.raises(D.LoiDon, match="chưa mở"):
        _dat(db, k, g)
    assert not S.tim(db, "Đà Nẵng", VAO, RA, hom_nay=NAY.date())["khach_san"][0]["mo_thanh_toan"]
    S.bat_tt_chung(db, _u(db, "tp"), True)
    d = _dat(db, k, g)
    S.bat_tt_chung(db, _u(db, "tp"), False)                              # đơn đang chờ trả: QR / thẻ cũng bị chặn
    with pytest.raises(D.LoiDon, match="chưa mở"):
        D.qr(db, _tk(db), d.ma, NAY)
    with pytest.raises(D.LoiDon, match="chưa mở"):
        D.the_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.1.1.1", NAY)
    with pytest.raises(S.LoiKhachSan):
        S.bat_tt_chung(db, _u(db, "dh"), True)                           # NV Điều hành không bật
    viec = {a.action for a in db.execute(select(AuditLog)).scalars()}
    assert {"ks_vtd_tt_chung_mo", "ks_vtd_tt_chung_dong", "ks_vtd_tt_mo", "ks_vtd_tt_dong"} <= viec


def test_gio_den_va_email_xac_nhan(db, k3, monkeypatch):
    from app.services import don_ks_vtd as D
    from app.services import payments as P
    k, lp, g = k3
    with pytest.raises(D.LoiDon, match="Giờ đến"):
        _dat(db, k, g, gio_den="3 giờ sáng")
    d = _dat(db, k, g, gio_den="20:00–21:00", email="lan@example.com")
    assert d.gio_den == "20:00–21:00" and D.ra_khach(db, d, NAY)["gio_den"] == "20:00–21:00"
    gui = []
    monkeypatch.setattr(D, "GUI_XAC_NHAN", lambda don, ten: gui.append((don.ma, ten, don.ma_xac_nhan_ks)) or True)
    P.match_transaction(db, _txn(db, d.tong, d.ma)); db.commit()
    # KS-19: đủ tiền là máy xác nhận + gửi email ngay; Điều hành ghi mã khách sạn sau, không gửi email lần hai
    assert d.trang_thai == "da_xac_nhan" and d.xac_nhan_boi == "may" and gui == [(d.ma, k.ten, "")]
    assert [x["ma"] for x in D.ds_vtos(db, _u(db, "dh"), "cho_chot", now=NAY)["don"]] == [d.ma]
    D.dh_xac_nhan(db, _u(db, "dh"), d.id, "BX-7781", NAY); db.commit()
    assert gui == [(d.ma, k.ten, "")] and d.ma_xac_nhan_ks == "BX-7781" and d.xac_nhan_boi == "may"
    assert D.ds_vtos(db, _u(db, "dh"), "cho_chot", now=NAY)["don"] == []
    d2 = _dat(db, k, g, tk=_tk(db, 2))
    monkeypatch.setattr(D, "GUI_XAC_NHAN", lambda *a: (_ for _ in ()).throw(RuntimeError("smtp")))
    P.match_transaction(db, _txn(db, d2.tong, d2.ma, sid="T2")); db.commit()   # email lỗi không làm hỏng xác nhận
    assert d2.trang_thai == "da_xac_nhan"


def test_bo_loc_kieu_agoda(db, k3):
    from app.services import khach_san_vtd as S
    k, lp, g = k3
    lp.giuong = "1 giường đôi lớn"
    db.commit()
    o = S.tim(db, "Đà Nẵng", VAO, RA, hom_nay=NAY.date())["khach_san"][0]
    assert o["giuong_tom"] == ["doi"] and not o["gia_dinh"] and o["co_uu_dai"] and o["co_tra_sau"] and o["co_tra_ngay"]
    assert not o["co_chi_phong"] and "vi_do" in o
    assert S._kieu_giuong("2 giường đơn") == {"don2"} and S._kieu_giuong("Twin") == {"don2"}
