# -*- coding: utf-8 -*-
"""KS-17 · Năm việc IT sau đợt cập nhật 41 khách sạn VTD (Chủ tịch «làm luôn cả 5 việc» 03/11/2026).

  1. Ảnh cũ sửa được loại phòng / nhóm / chú thích — không phải xóa rồi tải lại.
  2. Ảnh có «mô tả thay thế» (alt), ra cổng.
  3. Thuế phí: 0% mặc định KHÔNG phải xác nhận. Chưa xác nhận → không duyệt giá, không mở thanh toán.
  4. Sức chứa: người lớn để trống = chưa xác nhận (không tự gán 1 hay 2); có ô tổng khách; phòng chưa xác nhận
     không bán và không duyệt được giá.
  5. Hủy: giờ chốt + múi giờ của gói; gói «không cho trả sau» thì không có hạn trả sau.
Mỗi phép thử đo hai chiều.
"""
import datetime as dt

import pytest

from tests.test_at1_am_thuc import db, _u  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO, _anh, _ks, _mo_ban

MUA = [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 1_000_000}]


def _ks_chua_thue(s):
    from app.services import khach_san_vtd as S
    return S.luu_ks(s, _u(s, "dh"), {"ten": "Khách sạn Chưa Thuế", "tinh_thanh": "Đà Nẵng", "sao": 3,
                                     "mo_ta": "Khách sạn ba sao gần biển, đi bộ năm phút ra bãi tắm Mỹ Khê."})


def test_ks17_1_anh_cu_sua_duoc_lien_ket_va_mo_ta_thay_the(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp, _g, x = _mo_ban(db, k)
    assert x.loai_phong_id is None
    S.sua_anh(db, _u(db, "dh"), x.id, {"loai_phong_id": lp.id, "nhom": "phong", "chu_thich": "Phòng Deluxe",
                                       "mo_ta_thay_the": "Giường đôi lớn, cửa kính nhìn ra biển"})
    db.refresh(x)
    assert (x.loai_phong_id, x.nhom, x.chu_thich) == (lp.id, "phong", "Phòng Deluxe")
    o = S._anh_out(x, True)
    assert o["mo_ta_thay_the"] == "Giường đôi lớn, cửa kính nhìn ra biển", "chữ thay ảnh phải ra cổng"
    # chiều ngược lại: gỡ liên kết về «không», và không gắn được loại phòng của khách sạn khác
    S.sua_anh(db, _u(db, "dh"), x.id, {"loai_phong_id": None})
    db.refresh(x)
    assert x.loai_phong_id is None
    k2 = _ks(db, ten="Khách sạn Khác")
    lp2 = S.luu_loai_phong(db, _u(db, "dh"), k2.id, {"ten": "Suite", "toi_da_nguoi_lon": 2, "so_phong": 1})
    with pytest.raises(S.LoiKhachSan, match="không thuộc"):
        S.sua_anh(db, _u(db, "dh"), x.id, {"loai_phong_id": lp2.id})


def test_ks17_2_thue_chua_xac_nhan_thi_khong_duyet_gia_khong_mo_thanh_toan(db):
    from app.services import khach_san_vtd as S
    k = _ks_chua_thue(db)
    assert k.thue_phi_xac_nhan is False and (k.thue_phi_pt or 0) == 0
    lp = S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Deluxe", "toi_da_nguoi_lon": 2, "so_phong": 2})
    g = S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "mua": MUA})
    S.gui_duyet_goi(db, _u(db, "dh"), g.id)
    with pytest.raises(S.LoiKhachSan, match="thuế phí"):
        S.duyet_goi(db, _u(db, "tp"), g.id, True)
    with pytest.raises(S.LoiKhachSan, match="thuế phí"):
        S.bat_tt_ks(db, _u(db, "tp"), k.id, True)
    with pytest.raises(S.LoiKhachSan, match="ghi mức %"):
        S.luu_ks(db, _u(db, "dh"), {"ten": k.ten, "tinh_thanh": "Đà Nẵng", "sao": 3, "mo_ta": k.mo_ta,
                                    "thue_phi_xac_nhan": True}, k.id)
    # chiều ngược lại: xác nhận 0% (khách sạn không thu) là hợp lệ, và lúc ấy duyệt được
    S.luu_ks(db, _u(db, "dh"), {"ten": k.ten, "tinh_thanh": "Đà Nẵng", "sao": 3, "mo_ta": k.mo_ta,
                                "thue_phi_pt": 0, "thue_phi_xac_nhan": True}, k.id)
    assert S.duyet_goi(db, _u(db, "tp"), g.id, True).trang_thai == "da_duyet"
    assert S.bat_tt_ks(db, _u(db, "tp"), k.id, True).mo_thanh_toan is True
    # trả lại thì vẫn trả được dù thuế chưa xác nhận — chỉ chặn chiều mở bán
    k3 = _ks_chua_thue(db)
    lp3 = S.luu_loai_phong(db, _u(db, "dh"), k3.id, {"ten": "Deluxe", "toi_da_nguoi_lon": 2, "so_phong": 2})
    g3 = S.luu_goi(db, _u(db, "dh"), lp3.id, {"ten": "Chỉ phòng", "mua": MUA})
    S.gui_duyet_goi(db, _u(db, "dh"), g3.id)
    assert S.duyet_goi(db, _u(db, "tp"), g3.id, False, "Giá chưa khớp hợp đồng").trang_thai == "tra_lai"


def test_ks17_3_suc_chua_trong_la_chua_xac_nhan(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp = S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Family", "toi_da_nguoi_lon": "", "so_phong": 2})
    assert lp.toi_da_nguoi_lon is None, "trống phải là chưa xác nhận, không tự gán 1 hay 2"
    g = S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "mua": MUA})
    S.gui_duyet_goi(db, _u(db, "dh"), g.id)
    with pytest.raises(S.LoiKhachSan, match="người lớn tối đa"):
        S.duyet_goi(db, _u(db, "tp"), g.id, True)
    r = S._mot_phong(k, lp, 2, [], 1_000_000, False)
    assert r["ok"] is False and "xác nhận" in r["ly_do"]
    with pytest.raises(S.LoiKhachSan, match="Tổng khách"):
        S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Twin", "toi_da_nguoi_lon": 3, "tong_khach_toi_da": 2,
                                                   "so_phong": 1}, lp.id)
    # chiều ngược lại: đã xác nhận 2 NL, tổng 3 khách → 2 NL + 1 trẻ vừa, 2 NL + 2 trẻ không vừa
    lp = S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Family", "toi_da_nguoi_lon": 2, "tong_khach_toi_da": 3,
                                                    "toi_da_tre_em": 2, "so_phong": 2}, lp.id)
    assert (lp.toi_da_nguoi_lon, lp.tong_khach_toi_da) == (2, 3)
    tre = [{"tuoi": 5, "cach": "mien_phi"}]
    assert "tối đa 3 khách" not in (S._mot_phong(k, lp, 2, tre, 1_000_000, False).get("ly_do") or "")
    r2 = S._mot_phong(k, lp, 2, tre * 2, 1_000_000, False)
    assert r2["ok"] is False and "tối đa 3 khách" in r2["ly_do"]


def test_ks17_4_gio_chot_huy_mui_gio_va_tra_sau(db):
    from app.services import don_ks_vtd as KV
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp = S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Deluxe", "toi_da_nguoi_lon": 2, "so_phong": 2})
    with pytest.raises(S.LoiKhachSan, match="HH:MM"):
        S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "huy_truoc_ngay": 3, "huy_gio_chot": "25:00", "mua": MUA})
    with pytest.raises(S.LoiKhachSan, match="Múi giờ"):
        S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "huy_truoc_ngay": 3, "huy_mui_gio": "Sao Hỏa", "mua": MUA})
    g = S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "huy_truoc_ngay": 3, "huy_gio_chot": "18:00",
                                            "huy_mui_gio": "UTC", "cho_tra_sau": False, "mua": MUA})
    o = S._goi_out(g, [])
    assert (o["huy_gio_chot"], o["huy_mui_gio"], o["cho_tra_sau"]) == ("18:00", "UTC", False)
    hom_nay = dt.date(2026, 11, 3)
    dong = [{"huy_han": "2026-12-15", "cho_tra_sau": False}]
    assert KV.han_tra_sau(dong, hom_nay) is None, "gói không cho trả sau thì không có hạn trả sau"
    # chiều ngược lại: gói mặc định (cũ) vẫn cho trả sau như trước
    g2 = S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Có bữa sáng", "bua_sang": True, "huy_truoc_ngay": 3, "mua": MUA})
    assert (g2.huy_gio_chot, g2.huy_mui_gio, g2.cho_tra_sau) == ("", "Asia/Ho_Chi_Minh", True)
    assert KV.han_tra_sau([{"huy_han": "2026-12-15", "cho_tra_sau": True}], hom_nay) is not None
