# -*- coding: utf-8 -*-
"""KS-15 · Đánh giá khách sạn VTD (Chủ tịch duyệt bản xem thử 30/10/2026) — như AT-3, thang 10.

  1. Chỉ người đặt của đơn ĐÃ XÁC NHẬN, từ ngày trả phòng, trong 30 ngày; một bài / đơn; sửa trong 7 ngày.
  2. Điểm chung 1–10 bắt buộc; mục phụ bỏ trống ≠ 0. Dưới 3 bài đang hiện: không có điểm trung bình.
  3. Chỉ Marketing ẩn, phải có lý do vi phạm + ghi thêm; TP Điều hành xem lại; người ẩn không tự xem lại.
  4. Khách sạn trả lời qua cổng NCC khi đã gắn NCC; một lần, sửa trong 24 giờ.
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import NAY, _dat, _tk, _txn, k3  # noqa: F401

SAU = dt.datetime.combine(RA, dt.time(15, 0))


def _o_xong(s, k, g, i=1, sid="T1"):
    """Đơn đã trả + Điều hành xác nhận."""
    from app.services import don_ks_vtd as S
    from app.services import payments as P
    d = _dat(s, k, g, tk=_tk(s, i))
    P.match_transaction(s, _txn(s, d.tong, d.ma, sid=sid)); s.commit()
    S.dh_xac_nhan(s, _u(s, "dh"), d.id, f"BX-{i}", NAY); s.commit()
    return d


def test_chi_khach_da_o_viet_duoc(db, k3):
    from app.services import danh_gia_ks as G
    k, lp, g = k3
    d = _o_xong(db, k, g)
    t = G.trang_thai_don(db, d, NAY)
    assert not t["duoc_viet"]                                             # chưa tới ngày trả phòng
    with pytest.raises(G.LoiDanhGiaKs, match="từ ngày trả phòng"):
        G.viet(db, _tk(db), d.ma, {"diem": 9, "dong_y": True}, now=NAY)
    assert G.trang_thai_don(db, d, SAU)["duoc_viet"]
    with pytest.raises(G.LoiDanhGiaKs, match="1 đến 10"):
        G.viet(db, _tk(db), d.ma, {"diem": 11, "dong_y": True}, now=SAU)
    with pytest.raises(G.LoiDanhGiaKs, match="đồng ý"):
        G.viet(db, _tk(db), d.ma, {"diem": 9}, now=SAU)
    with pytest.raises(G.LoiDanhGiaKs):
        G.viet(db, _tk(db, 2), d.ma, {"diem": 9, "dong_y": True}, now=SAU)     # người khác
    x = G.viet(db, _tk(db), d.ma, {"diem": 9, "diem_sach": 10, "diem_phong": "", "di_cung": "gia_dinh_tre_nho",
                                   "tieu_de": "Phòng sạch", "nhan_xet": "Nhân viên nhiệt tình", "dong_y": True}, now=SAU)
    assert x.diem == 9 and x.diem_sach == 10 and x.diem_phong is None and x.ten_hien == "Khách L***" and x.so_dem == 3
    assert not G.trang_thai_don(db, d, SAU)["duoc_viet"] and G.trang_thai_don(db, d, SAU)["duoc_sua"]
    G.viet(db, _tk(db), d.ma, {"diem": 7, "dong_y": True}, now=SAU + dt.timedelta(days=2))
    assert x.diem == 7 and x.sua_luc
    with pytest.raises(G.LoiDanhGiaKs, match="7 ngày"):
        G.viet(db, _tk(db), d.ma, {"diem": 8, "dong_y": True}, now=SAU + dt.timedelta(days=8))
    # quá 30 ngày thì đóng (đơn khác)
    d2 = _o_xong(db, k, g, 2, "T2")
    with pytest.raises(G.LoiDanhGiaKs, match="30 ngày"):
        G.viet(db, _tk(db, 2), d2.ma, {"diem": 8, "dong_y": True}, now=SAU + dt.timedelta(days=32))


def test_diem_trung_binh_tu_3_bai(db, k3):
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.services import danh_gia_ks as G
    from app.services import khach_san_vtd as KS
    k, lp, g = k3
    db.add(TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000003", ho_ten="Châu", trang_thai="hoat_dong")); db.commit()
    for i, (diem, sach) in enumerate(((9, 10), (8, None), (10, 9)), start=1):
        d = _o_xong(db, k, g, i, f"T{i}")
        G.viet(db, _tk(db, i), d.ma, {"diem": diem, "diem_sach": sach, "dong_y": True}, now=SAU)
        tt = G.tom_tat(db, [k.id])[k.id]
        assert (tt["diem_tb"] is None) == (i < 3)
    tt = G.tom_tat(db, [k.id])[k.id]
    assert tt["diem_tb"] == 9.0 and tt["nhan"] == "Xuất sắc" and tt["muc"]["diem_sach"] == 9.5
    the = KS.chi_tiet_cong(db, k.id, VAO, RA, hom_nay=NAY.date())   # KS-19: danh sách chỉ hiện KS còn phòng
    assert the["danh_gia"]["diem_tb"] == 9.0 and the["danh_gia"]["so_bai"] == 3
    assert [b["diem"] for b in G.cong(db, k.id, xep="thap")["bai"]] == [8, 9, 10]


def test_an_vi_pham_va_xem_lai(db, k3):
    from app.services import danh_gia_ks as G
    k, lp, g = k3
    d = _o_xong(db, k, g)
    x = G.viet(db, _tk(db), d.ma, {"diem": 2, "nhan_xet": "Gọi 0909xxx để đặt rẻ hơn", "dong_y": True}, now=SAU)
    with pytest.raises(G.LoiDanhGiaKs, match="Marketing"):
        G.an(db, _u(db, "tp"), x.id, "quang_cao", "dẫn khách sang số riêng")
    with pytest.raises(G.LoiDanhGiaKs, match="lý do vi phạm"):
        G.an(db, _u(db, "mkt"), x.id, "bai_che", "khách chê phòng ồn")
    with pytest.raises(G.LoiDanhGiaKs, match="Ghi thêm"):
        G.an(db, _u(db, "mkt"), x.id, "quang_cao", "")
    G.an(db, _u(db, "mkt"), x.id, "quang_cao", "dẫn khách sang số riêng")
    assert x.an and G.cong(db, k.id)["tong"] == 0
    G.xem_lai(db, _u(db, "tp"), x.id, False)
    assert not x.an and x.xem_lai == "hien" and G.cong(db, k.id)["tong"] == 1


def test_khach_san_tra_loi_qua_cong_ncc(db, k3):
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.suppliers import Supplier
    from app.services import danh_gia_ks as G
    k, lp, g = k3
    d = _o_xong(db, k, g)
    x = G.viet(db, _tk(db), d.ma, {"diem": 6, "tieu_de": "Cách âm kém", "dong_y": True}, now=SAU)
    s = Supplier(code="NCC-BX", ten="Công ty Biển Xanh")
    db.add(s); db.commit()
    tk = TaiKhoanNgoai(loai="doi_tac", loai_doi_tac="ncc", dien_thoai="0901999999", trang_thai="hoat_dong", ncc_id=s.id)
    db.add(tk); db.commit()
    assert G.ds_ncc(db, s)["bai"] == []                                    # chưa gắn khách sạn
    with pytest.raises(G.LoiDanhGiaKs):
        G.gan_ncc(db, _u(db, "dh"), k.id, s.id)                              # NV ĐH không gắn
    G.gan_ncc(db, _u(db, "tp"), k.id, s.id); db.commit()
    b = G.ds_ncc(db, s)
    assert [o["id"] for o in b["bai"]] == [x.id] and b["bai"][0]["duoc_tra_loi"]
    G.tra_loi(db, tk, s, x.id, "Cảm ơn anh, khách sạn đang lắp cửa cách âm.", now=SAU)
    assert G.cong(db, k.id)["bai"][0]["tra_loi"].startswith("Cảm ơn")
    G.tra_loi(db, tk, s, x.id, "Cảm ơn anh — đã lắp cửa cách âm tầng 5.", now=SAU + dt.timedelta(hours=2))
    with pytest.raises(G.LoiDanhGiaKs, match="24 giờ"):
        G.tra_loi(db, tk, s, x.id, "Sửa lần nữa", now=SAU + dt.timedelta(hours=30))
    s2 = Supplier(code="NCC-KHAC", ten="NCC khác"); db.add(s2); db.commit()
    with pytest.raises(G.LoiDanhGiaKs):
        G.tra_loi(db, tk, s2, x.id, "không phải khách sạn của tôi", now=SAU)
