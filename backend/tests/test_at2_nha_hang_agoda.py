# -*- coding: utf-8 -*-
"""AT-2 · Nhà hàng kiểu Agoda trên kh.vietourist.vn/restaurant (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Ghim bản đồ: máy lấy tọa độ từ địa chỉ bằng nút hàng loạt (hàm giả ở đây — không gọi mạng khi lưu hồ sơ);
     Điều hành dán link Google Maps → «tay», nút hàng loạt bỏ qua; đổi địa chỉ thì ghim tự động cũ bị xóa.
  2. Thanh toán chỉ mở khi CẢ công tắc chung và công tắc nhà hàng đều bật — tạo đơn, QR, thẻ đều 409; có nhật ký.
  3. Trang riêng xem không cần đăng nhập: /cong/mo/nha-hang/tat-ca trả mọi nhà hàng + dữ liệu cho bộ lọc «Phù hợp».
"""
import pytest
from sqlalchemy import select

from tests.test_dt2_dat_ban import NAY, _dat, _tk, bat_thanh_toan, db  # noqa: F401


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _nh(s):
    from app.models.nha_hang import NhaHang
    return s.execute(select(NhaHang)).scalars().one()


def _tp(s):
    from app.models.core import User
    if not s.execute(select(User).where(User.username == "tpdh")).scalars().first():
        s.add(User(username="tpdh", full_name="TPDH", role="tp_dh", password_hash="x")); s.commit()
    return _u(s, "tpdh")


def test_ghim_tay_loat_va_doi_dia_chi(db, monkeypatch):
    from app.services import nha_hang as N
    n = _nh(db)
    hoi = []
    monkeypatch.setattr(N, "LAY_TOA_DO", lambda q: hoi.append(q) or (10.2275, 103.9636))
    # lưu hồ sơ không gọi dịch vụ ngoài
    N.luu_nha_hang(db, _u(db, "nvdh"), {"ten": n.ten, "khu_vuc": "12 Trần Hưng Đạo, Dương Đông", "tinh_thanh": "Phú Quốc"}, n.id)
    assert hoi == [] and n.vi_do is None
    with pytest.raises(N.LoiNhaHang, match="TP Điều hành"):
        N.lay_toa_do_loat(db, _u(db, "nvdh"), nghi=0)
    r = N.lay_toa_do_loat(db, _tp(db), nghi=0)
    db.refresh(n)
    assert r["co"] == 1 and (n.vi_do, n.kinh_do, n.toa_do_nguon) == (10.2275, 103.9636, "tu_dong")
    assert "12 Trần Hưng Đạo" in hoi[0]
    # link Google Maps đầy đủ → tay; link rút gọn báo rõ
    N.dat_ghim(db, _u(db, "nvdh"), n.id, "https://www.google.com/maps/place/X/@10.21,103.96,17z/data=!3d10.2123!4d103.9611")
    assert (n.vi_do, n.kinh_do, n.toa_do_nguon) == (10.2123, 103.9611, "tay")
    with pytest.raises(N.LoiNhaHang, match="rút gọn"):
        N.dat_ghim(db, _u(db, "nvdh"), n.id, "https://maps.app.goo.gl/AbC")
    # đổi địa chỉ: ghim tay giữ nguyên
    N.luu_nha_hang(db, _u(db, "nvdh"), {"ten": n.ten, "khu_vuc": "99 Bạch Đằng", "tinh_thanh": "Phú Quốc"}, n.id)
    assert n.toa_do_nguon == "tay" and n.vi_do == 10.2123
    # bỏ ghim tay → đổi địa chỉ làm trống, hàng loạt lấy lại; không thấy → khong_thay
    N.dat_ghim(db, _u(db, "nvdh"), n.id, "")
    assert n.vi_do is None and n.toa_do_nguon == ""
    monkeypatch.setattr(N, "LAY_TOA_DO", lambda q: None)
    r = N.lay_toa_do_loat(db, _tp(db), nghi=0)
    assert r["khong_thay"] == [n.ma] and n.toa_do_nguon == "khong_thay"
    # dịch vụ lỗi mạng: không hỏng, để trống
    monkeypatch.setattr(N, "LAY_TOA_DO", lambda q: (_ for _ in ()).throw(OSError("mang")))
    n.toa_do_nguon = ""; db.commit()
    assert N.lay_toa_do_loat(db, _tp(db), nghi=0)["co"] == 0 and n.vi_do is None


def test_cong_tac_thanh_toan_ca_hai_moi_tra(db, monkeypatch):
    from app.models.core import AuditLog
    from app.services import dat_ban as S
    from app.services import nha_hang as N
    n = _nh(db)
    d = _dat(db)                                       # fixture đã bật cả hai công tắc
    assert d.trang_thai == "cho_nhan" and S.ra(db, d, NAY)["mo_thanh_toan"] is True
    for chung, rieng in ((False, True), (True, False), (False, False)):
        bat_thanh_toan(db, n, chung, rieng); db.commit()
        with pytest.raises(S.LoiDatBan, match="chưa mở") as e:
            _dat(db, tk="0901000002")
        assert e.value.status == 409
        with pytest.raises(S.LoiDatBan, match="chưa mở"):
            S._kiem_mo_tt(db, n.id)
        assert S.ra(db, d, NAY)["mo_thanh_toan"] is False
    # chỉ TP Điều hành / Chủ tịch / TGĐ bật; có nhật ký
    with pytest.raises(N.LoiNhaHang):
        N.bat_tt_chung_nh(db, _u(db, "nvdh"), True)
    N.bat_tt_chung_nh(db, _tp(db), True)
    N.bat_tt_nh(db, _u(db, "ct"), n.id, True)
    assert N.mo_thanh_toan_nh(db, n)
    hd = {a.action for a in db.execute(select(AuditLog)).scalars()}
    assert {"nh_tt_chung_mo", "nh_tt_mo"} <= hd
    assert _dat(db, tk="0901000002").trang_thai == "cho_nhan"


def test_trang_rieng_tat_ca_khong_dang_nhap(db):
    """Gọi thẳng hàm của router công khai (không phụ thuộc phiên); router chỉ GET đã có phép thử KS-16q."""
    from app.api.v1 import cong_mo as M
    from app.models.nha_hang import ThucDonNhaHang
    n = _nh(db)
    n.vi_do, n.kinh_do = 10.22, 103.96
    db.add(ThucDonNhaHang(nha_hang_id=n.id, ten="Tiệc cưới", loai="tiec", gia_nguoi_lon=500000, so_khach_toi_thieu=20))
    db.commit()
    j = M.nh_tat_ca(db=db)
    o = next(x for x in j["nha_hang"] if x["id"] == n.id)
    assert o["mo_dat"] and o["mo_thanh_toan"] and o["vi_do"] == 10.22
    assert o["gia_dinh"] and o["tiec"] and o["phong_rieng"] and o["goi_mon"]
    assert j["tt_chung"] is True and j["tham_so"]["coc_le"] > 0 and j["tong"] >= 1 and "noi_dung" not in j
    assert M.nh_mot(n.id, db=db)["mo_thanh_toan"] is True
    pt = {m for r in __import__("app.main", fromlist=["app"]).app.routes
          if getattr(r, "path", "").startswith("/api/v1/cong/mo/nha-hang") for m in (r.methods or set())}
    assert pt <= {"GET", "HEAD"}
