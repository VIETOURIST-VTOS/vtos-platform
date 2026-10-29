# -*- coding: utf-8 -*-
"""KS-13 · Danh mục khách sạn hợp tác VTD (Chủ tịch duyệt bản demo 30/10/2026).

  1. Giá: cộng từng đêm theo mùa đã duyệt; đêm thứ Sáu / thứ Bảy lấy giá cuối tuần; đêm không có mùa → gói không bán.
  2. Hai người: người nhập giá / tải ảnh / sửa hồ sơ không tự duyệt / tự bật (trừ Chủ tịch, TGĐ).
  3. Sửa gói đã duyệt → về Nháp, thôi hiện. Mùa giá chồng ngày → từ chối.
  4. Cổng: chỉ khách sạn đang hiện; chỉ gói đã duyệt; ảnh chỉ bản đã duyệt, không bao giờ bản gốc.
  5. Yêu cầu giữ phòng vào hàng chờ KS-11, giá do MÁY tính lại.
"""
import datetime as dt

import pytest

from tests.test_at1_am_thuc import db, _u  # noqa: F401

HN = dt.date(2026, 12, 1)
VAO, RA = dt.date(2026, 12, 18), dt.date(2026, 12, 21)      # đêm T6 18, T7 19, CN 20


def _anh(so=1):
    from io import BytesIO
    from PIL import Image
    b = BytesIO(); Image.new("RGB", (900, 600), (so * 20 % 255, 120, 180)).save(b, "JPEG"); return b.getvalue()


def _ks(s, ten="Khách sạn Biển Xanh", nguoi="dh"):
    from app.services import khach_san_vtd as S
    return S.luu_ks(s, _u(s, nguoi), {"ten": ten, "tinh_thanh": "Đà Nẵng", "sao": 4, "khu_vuc": "Mỹ Khê", "thue_phi_pt": 15,
                                      "mo_ta": "Khách sạn 4 sao trên trục Võ Nguyên Giáp, đi bộ hai phút ra biển Mỹ Khê.",
                                      "tien_ich": ["ho_boi", "wifi"]})


def _mo_ban(s, k, gia=1_000_000, cuoi_tuan=1_400_000):
    """Một loại phòng + một gói đã duyệt phủ tháng 12, một ảnh đã duyệt, bật hiện."""
    from app.services import khach_san_vtd as S
    lp = S.luu_loai_phong(s, _u(s, "dh"), k.id, {"ten": "Deluxe hướng biển", "toi_da_nguoi_lon": 2, "so_phong": 3})
    g = S.luu_goi(s, _u(s, "dh"), lp.id, {"ten": "Có bữa sáng", "bua_sang": True, "huy_truoc_ngay": 2,
                                          "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": gia,
                                                   "gia_cuoi_tuan": cuoi_tuan, "gia_niem_yet": 1_800_000}]})
    S.gui_duyet_goi(s, _u(s, "dh"), g.id)
    S.duyet_goi(s, _u(s, "tp"), g.id, True)
    x, _ = S.tai_anh(s, _u(s, "dh"), k.id, "a.jpg", _anh(), {"nhom": "mat_tien"})
    S.gui_duyet_anh(s, _u(s, "dh"), [x.id])
    S.duyet_anh(s, _u(s, "tp"), [x.id], True)
    S.bat_hien(s, _u(s, "tp"), k.id, True)
    return lp, g, x


def test_gia_tung_dem_va_cuoi_tuan(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)
    mua = S._mua_cua(db, [g.id])[g.id]
    p = S.gia_luu(g, mua, VAO, RA)
    assert p["tong"] == 1_400_000 * 2 + 1_000_000 and p["gia_dem"] == round(3_800_000 / 3)
    assert p["niem_yet_dem"] == 1_800_000
    assert S.gia_luu(g, mua, dt.date(2026, 12, 30), dt.date(2027, 1, 2)) is None     # đêm 31/12 có, 1/1 không
    assert S.han_huy(g, VAO) == dt.date(2026, 12, 16)


def test_hai_nguoi_va_sua_ve_nhap(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp = S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": "Deluxe", "so_phong": 2})
    with pytest.raises(S.LoiKhachSan, match="chồng ngày"):
        S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "mua": [
            {"tu_ngay": "2026-12-01", "den_ngay": "2026-12-20", "gia_thuong": 900000},
            {"tu_ngay": "2026-12-20", "den_ngay": "2026-12-31", "gia_thuong": 1200000}]})
    g = S.luu_goi(db, _u(db, "tp"), lp.id, {"ten": "Chỉ phòng", "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 900000}]})
    S.gui_duyet_goi(db, _u(db, "tp"), g.id)
    with pytest.raises(S.LoiKhachSan, match="không tự duyệt"):
        S.duyet_goi(db, _u(db, "tp"), g.id, True)
    with pytest.raises(S.LoiKhachSan):
        S.duyet_goi(db, _u(db, "dh"), g.id, True)                   # NV không duyệt
    with pytest.raises(S.LoiKhachSan, match="lý do"):
        S.duyet_goi(db, _u(db, "tp2"), g.id, False, "")
    S.duyet_goi(db, _u(db, "tp2"), g.id, True)
    assert g.trang_thai == "da_duyet"
    S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Chỉ phòng", "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 950000}]}, g.id)
    assert g.trang_thai == "nhap"                                      # sửa giá đã duyệt → về nháp
    # bật hiện: thiếu ảnh duyệt → không bật; người vừa sửa hồ sơ không tự bật
    with pytest.raises(S.LoiKhachSan, match="ảnh đã duyệt"):
        S.bat_hien(db, _u(db, "tp"), k.id, True)
    x, _ = S.tai_anh(db, _u(db, "tp"), k.id, "a.jpg", _anh(), {"nhom": "phong", "loai_phong_id": lp.id})
    S.gui_duyet_anh(db, _u(db, "tp"), [x.id])
    assert S.duyet_anh(db, _u(db, "tp"), [x.id], True)["bo_qua"]           # người tải không tự duyệt
    S.duyet_anh(db, _u(db, "tp2"), [x.id], True)
    k2 = S.luu_ks(db, _u(db, "tp"), {"ten": k.ten, "tinh_thanh": "Đà Nẵng", "sao": 4, "mo_ta": k.mo_ta}, k.id)
    with pytest.raises(S.LoiKhachSan, match="không tự bật"):
        S.bat_hien(db, _u(db, "tp"), k2.id, True)
    S.bat_hien(db, _u(db, "tp2"), k2.id, True)
    assert k2.hien_cong


def test_cong_tim_chi_tiet_anh(db):
    from app.services import khach_san_vtd as S
    a = _ks(db, "Khách sạn Biển Xanh")
    lp, g, x = _mo_ban(db, a)
    b = _ks(db, "Khách sạn Chưa Bật")                                   # chưa hiện → không có trên cổng
    r = S.tim(db, "Đà Nẵng", VAO, RA, 2, 0, 1, hom_nay=HN)
    assert [o["ten"] for o in r["khach_san"]] == ["Khách sạn Biển Xanh"] and r["dem"] == 3
    o = r["khach_san"][0]
    assert o["gia_tu"]["gia_dem"] == round(3_800_000 / 3) and o["co_bua_sang"] and o["co_mien_phi_huy"]
    assert o["anh"] and o["anh"][0]["nho"].startswith("/api/v1/ks-vtd-anh/") and "goc" not in o["anh"][0]
    assert "lien_he_noi_bo" not in o and "ghi_chu_noi_bo" not in o
    # 3 người lớn / 1 phòng: phòng tối đa 2 → không có giá từ
    assert S.tim(db, "Đà Nẵng", VAO, RA, 3, 0, 1, hom_nay=HN)["khach_san"][0]["gia_tu"] is None
    ct = S.chi_tiet_cong(db, a.id, VAO, RA, 2, 0, 1, hom_nay=HN)
    assert ct["phong"][0]["goi"][0]["tong"] == 3_800_000 and ct["phong"][0]["goi"][0]["huy_han"] == "2026-12-16"
    with pytest.raises(S.LoiKhachSan):
        S.chi_tiet_cong(db, b.id, VAO, RA, hom_nay=HN)
    # ảnh: cổng không lấy bản gốc, không lấy ảnh chưa duyệt
    data, _att = S.tep_anh(db, None, x.id, "nho")
    assert data
    with pytest.raises(S.LoiKhachSan):
        S.tep_anh(db, None, x.id, "goc")
    y, _ = S.tai_anh(db, _u(db, "dh"), a.id, "b.jpg", _anh(2), {"nhom": "phong"})
    with pytest.raises(S.LoiKhachSan):
        S.tep_anh(db, None, y.id, "hien")
    # ngày đã qua / trả trước nhận
    with pytest.raises(S.LoiKhachSan):
        S.tim(db, "Đà Nẵng", dt.date(2026, 11, 1), RA, hom_nay=HN)
    with pytest.raises(S.LoiKhachSan):
        S.tim(db, "Đà Nẵng", RA, VAO, hom_nay=HN)


def test_tinh_lai_va_yeu_cau_giu(db):
    from app.services import khach_san_vtd as S
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.don_khach_san_ota import DonKhachSanOta, BuocDonOta
    for t in (DonKhachSanOta, BuocDonOta):            # mô hình KS-6 chưa nạp qua app.models → dựng bảng cho phép thử
        t.__table__.create(db.get_bind(), checkfirst=True)
    # Khoá BigInteger không tự tăng trên SQLite (Postgres thì có) — cấp số cho phép thử.
    from sqlalchemy import event
    dem = iter(range(1, 1000))

    def _cap_id(_m, _c, o):
        if o.id is None:
            o.id = next(dem)
    event.listen(DonKhachSanOta, "before_insert", _cap_id)
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)
    t = S.tinh_lua_chon(db, k.id, VAO, RA, [{"goi_id": g.id, "so": 2}], hom_nay=HN)
    assert t["tien_phong"] == 7_600_000 and t["thue_phi"] == 1_140_000 and t["tong"] == 8_740_000
    with pytest.raises(S.LoiKhachSan, match="tối đa 3"):
        S.tinh_lua_chon(db, k.id, VAO, RA, [{"goi_id": g.id, "so": 4}], hom_nay=HN)
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000009", ho_ten="Lan", trang_thai="hoat_dong")
    db.add(tk); db.commit()
    r = S.gui_yeu_cau_giu(db, tk, k.id, {"ngay_nhan": VAO, "ngay_tra": RA, "nguoi_lon": 2, "chon": [{"goi_id": g.id, "so": 1}],
                                          "nguoi_nhan_phong": "Nguyễn Thị Lan", "lien_he": "0901000009", "yeu_cau_them": "Tầng cao"},
                          hom_nay=HN)
    don = db.get(DonKhachSanOta, r["id"])
    assert don.tai_khoan_ngoai_id == tk.id and don.so_phong == 1 and "Biển Xanh" in don.noi_den
    assert "3.800.000 đ / 3 đêm" in don.yeu_cau_them and "4.370.000" in don.yeu_cau_them and "Tầng cao" in don.yeu_cau_them
    # gói bị sửa (về nháp) → yêu cầu có chọn phòng bị chặn, giá cũ không lọt qua
    S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": "Có bữa sáng", "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 20000}]}, g.id)
    with pytest.raises(S.LoiKhachSan, match="đã thay đổi"):
        S.gui_yeu_cau_giu(db, tk, k.id, {"ngay_nhan": VAO, "ngay_tra": RA, "chon": [{"goi_id": g.id, "so": 1}],
                                          "nguoi_nhan_phong": "Lan", "lien_he": "0901000009"}, hom_nay=HN)
    event.remove(DonKhachSanOta, "before_insert", _cap_id)


def test_vtos_doc(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    _mo_ban(db, k)
    d = S.ds_vtos(db, _u(db, "tp"))
    assert d["khach_san"][0]["anh_duyet"] == 1 and d["khach_san"][0]["goi_duyet"] == 1 and d["duoc_duyet"]
    m = S.mot_vtos(db, _u(db, "dh"), k.id)
    assert m["loai_phong"][0]["goi"][0]["mua"][0]["gia_cuoi_tuan"] == 1_400_000 and all(c["ok"] for c in m["dieu_kien"])
    assert S.cho_duyet(db, _u(db, "tp"))["goi"] == []
    with pytest.raises(S.LoiKhachSan):
        S.luu_ks(db, _u(db, "mkt"), {"ten": "X sạn", "tinh_thanh": "Đà Nẵng"})
