# -*- coding: utf-8 -*-
"""AT-2c · Biên tập và mức hoàn thiện (Chủ tịch chốt 29/10/2026).

  1. Máy chấm từ dữ liệu ĐÃ DUYỆT: bìa 20, album 20, món 15, thực đơn 15, giới thiệu 15, liên hệ 15; ≥ 80% = đủ.
  2. Chỉ Chủ tịch giao việc; người nhận là NV Điều hành / NV Marketing đang làm việc.
  3. Trang khách: nơi dưới 50% xếp xuống cuối, không ẩn.
"""
import pytest

from tests.test_at1_am_thuc import db, _u, HN  # noqa: F401
from tests.test_at2a_album import anh, anh_da_duyet, _nh


def _ct(s):
    from app.models.core import User
    x = User(username="ct", full_name="CT", role="chutich", password_hash="x"); s.add(x); s.commit()
    return x


def _du_het(s, nid):
    """Đưa một nhà hàng lên 100%."""
    from app.services import nha_hang as N
    from app.models.nha_hang import NhaHang
    ps = [anh_da_duyet(s, nid, 20 + i, nhom=("khong_gian" if i % 2 else "mat_tien")) for i in range(5)]
    N.dat_bia(s, _u(s, "dh"), ps[0])
    for i in range(3):
        m = N.luu_mon(s, _u(s, "dh"), nid, {"ten": f"Món {i}", "anh_id": ps[i + 1]})
    N.gui_duyet_mon(s, _u(s, "dh"), nid)
    N.duyet_mon(s, _u(s, "tp"), [x["id"] for x in N.ds_mon(s, _u(s, "dh"), nid)["mon"]], True)
    b = N.tai_thuc_don(s, _u(s, "dh"), nid, "goi_mon", [("t.jpg", anh(40))], None, "Email 29/10/2026")
    N.duyet_thuc_don(s, _u(s, "tp"), b.id, True)
    nh = s.get(NhaHang, nid)
    nh.mo_ta, nh.mon_noi_bat, nh.gio_phuc_vu, nh.khu_vuc, nh.lien_he_xac_minh = "x" * 300, "Chả giò", "10–22h", "Hoàn Kiếm", True
    s.commit()
    return m


def test_cham_diem_tu_du_lieu_da_duyet(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    d = N.diem_hoan_thien(db, [nh.id])[nh.id]
    assert d["diem"] == 0 and not any(m["dat"] for m in d["muc"])
    # ảnh nháp / chưa xác minh không được tính
    N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", anh(1), {"nhom": "mat_tien", "can_cu": "vtd_chup"})
    assert N.diem_hoan_thien(db, [nh.id])[nh.id]["diem"] == 0
    _du_het(db, nh.id)
    d = N.diem_hoan_thien(db, [nh.id])[nh.id]
    assert d["diem"] == 100 and all(m["dat"] for m in d["muc"])
    assert {m["ma"]: m["diem_toi_da"] for m in d["muc"]} == {"bia": 20, "album": 20, "mon": 15, "thuc_don": 15, "gioi_thieu": 15, "lien_he": 15}
    # bỏ giới thiệu → mất 15 điểm, còn 85 vẫn «đủ»
    from app.models.nha_hang import NhaHang
    db.get(NhaHang, nh.id).mo_ta, db.get(NhaHang, nh.id).mon_noi_bat = "", ""
    db.commit()
    assert N.diem_hoan_thien(db, [nh.id])[nh.id]["diem"] == 85
    one = N.hoan_thien_mot(db, _u(db, "mkt"), nh.id)
    assert one["muc_do"] == "du" and one["tin_xin"] == "" and one["nhat_ky"]


def test_chi_chu_tich_giao_viec(db):
    from app.services import nha_hang as N
    ct = _ct(db)
    nh = _nh(db)
    with pytest.raises(N.LoiNhaHang, match="Chủ tịch"):
        N.giao_bien_tap(db, _u(db, "tp"), [nh.id], "dh", None)                                 # TP ĐH không giao
    with pytest.raises(N.LoiNhaHang, match="NV Điều hành hoặc NV Marketing"):
        N.giao_bien_tap(db, ct, [nh.id], "kd", None)                                           # NV KD không nhận
    with pytest.raises(N.LoiNhaHang, match="Hạn"):
        N.giao_bien_tap(db, ct, [nh.id], "dh", "2020-01-01")
    assert N.giao_bien_tap(db, ct, [nh.id], "mkt", "2026-11-05") == 1
    b = N.bang_hoan_thien(db, ct)
    o = b["nha_hang"][0]
    assert o["nguoi"] == "mkt" and o["han"] == "2026-11-05" and o["cot"] == "chua_lam" and b["duoc_giao"] and b["nguoi_nhan"]
    assert N.bang_hoan_thien(db, _u(db, "tp"))["nguoi_nhan"] == []
    assert [x["ten"] for x in N.bang_hoan_thien(db, _u(db, "mkt"), chi_cua="mkt")["nha_hang"]] == ["Phở Hòa"]
    assert N.bang_hoan_thien(db, _u(db, "dh"), chi_cua="dh")["nha_hang"] == []
    # ghi đã xin → cột «Đang xin»; có thứ chờ duyệt → «Chờ duyệt»
    one = N.hoan_thien_mot(db, _u(db, "mkt"), nh.id)
    assert "ảnh bìa" in one["tin_xin"] and "Thực đơn" in one["tin_xin"]
    N.ghi_da_xin(db, _u(db, "mkt"), nh.id)
    assert N.bang_hoan_thien(db, ct)["nha_hang"][0]["cot"] == "dang_xin"
    N.tai_anh_album(db, _u(db, "mkt"), nh.id, "a.jpg", "image/jpeg", anh(2), {"nhom": "mat_tien", "can_cu": "vtd_chup"})
    N.gui_duyet(db, _u(db, "mkt"), nh.id)
    assert N.bang_hoan_thien(db, ct)["nha_hang"][0]["cot"] == "cho_duyet"
    assert N.giao_bien_tap(db, ct, [nh.id], "", None) == 1                                      # bỏ giao
    assert N.bang_hoan_thien(db, ct)["chua_giao"] == 1
    x = N.xuat_thieu_xlsx(db, ct)
    assert x[:2] == b"PK"


def test_cong_xep_noi_thieu_xuong_cuoi(db):
    from app.services import nha_hang as N
    a = _nh(db, "A Quán Thiếu")
    z = _nh(db, "Z Quán Đủ")
    _du_het(db, z.id)
    ten = [o["ten"] for o in N.danh_sach_cong(db)["nha_hang"]]
    assert ten == ["Z Quán Đủ", "A Quán Thiếu"]                                                # không ẩn, chỉ xếp cuối
    assert a.id in [o["id"] for o in N.danh_sach_cong(db)["nha_hang"]]
