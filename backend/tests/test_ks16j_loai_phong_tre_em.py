# -*- coding: utf-8 -*-
"""KS-16j · Form loại phòng + chính sách trẻ em kiểu Agoda (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Đặc điểm ngắn quá 300 ký tự → báo lỗi, không tự cắt; mô tả chi tiết ≤3.000.
  2. Số phòng VTD 0 lưu là 0; «Đang bán» cần ≥1. Trẻ em để trống = chưa xác nhận (None), khác 0.
  3. Nguồn & đối chiếu lưu nguyên; trạng thái Điều hành tự ghi, không chặn bán.
  4. Trẻ em: chưa xác nhận → không đặt ngay; mốc tuổi miễn phí / phụ thu / như người lớn; ai vượt sức chứa nằm giường
     phụ (trẻ lớn nhất trước); máy tự cộng phụ thu vào tiền phòng khi đặt.
"""
import datetime as dt

import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO, _ks, _mo_ban, HN
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401

CS = {"cs_nhan_tre_em": "moi_tuoi", "cs_phi_giuong_phu": 350000, "cs_giuong_phu_an_sang": True, "cs_noi": "Miễn phí, theo yêu cầu",
      "cs_moc_tuoi": [{"tu": 0, "den": 5, "cach": "mien_phi", "an_sang": True},
                      {"tu": 6, "den": 11, "cach": "phu_thu", "phu_thu": 150000, "an_sang": True},
                      {"tu": 12, "den": 17, "cach": "nguoi_lon"}]}


def _cs(s, k, **them):
    from app.services import khach_san_vtd as S
    d = {**S._ks_noi_bo(k), **CS, **them}
    return S.luu_ks(s, _u(s, "dh"), d, k.id)


def test_form_loai_phong(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    u = _u(db, "dh")
    with pytest.raises(S.LoiKhachSan, match="412/300"):
        S.luu_loai_phong(db, u, k.id, {"ten": "Superior", "mo_ta": "x" * 412, "so_phong": 1})
    with pytest.raises(S.LoiKhachSan, match="≥ 1"):
        S.luu_loai_phong(db, u, k.id, {"ten": "Superior", "so_phong": 0})
    lp = S.luu_loai_phong(db, u, k.id, {"ten": "Superior Double Room", "mo_ta": "Cửa sổ mở được", "mo_ta_dai": "y" * 2500,
                                        "so_phong": 0, "dang_ban": False, "toi_da_tre_em": "", "tien_nghi": ["Máy lạnh", "Wifi", "Wifi"],
                                        "nguon": "agoda", "ky_doi_chieu": "10–11/12/2026", "ma_hang": "", "ten_tuong_duong": "Superior",
                                        "can_xac_nhan": ["ten_hang", "tre_em", "han_muc"], "ghi_chu_doi_chieu": "Cửa sổ mâu thuẫn",
                                        "trang_thai_dc": "dang_doi_chieu"})
    db.refresh(lp)
    assert lp.so_phong == 0 and lp.toi_da_tre_em is None and len(lp.mo_ta_dai) == 2500
    assert lp.tien_nghi == ["Máy lạnh", "Wifi"] and lp.nguon == "agoda" and lp.can_xac_nhan == ["ten_hang", "tre_em", "han_muc"]
    lp = S.luu_loai_phong(db, u, k.id, {"ten": "Superior Double Room", "so_phong": 0, "dang_ban": False, "toi_da_tre_em": 0}, lp.id)
    assert lp.toi_da_tre_em == 0                                  # 0 là «không nhận» — đã xác nhận
    with pytest.raises(S.LoiKhachSan, match="Nguồn"):
        S.luu_loai_phong(db, u, k.id, {"ten": "X1", "so_phong": 1, "nguon": "expedia"})
    with pytest.raises(S.LoiKhachSan, match="3000"):
        S.luu_loai_phong(db, u, k.id, {"ten": "X1", "so_phong": 1, "mo_ta_dai": "z" * 3001})
    v = S.mot_vtos(db, u, k.id)["loai_phong"][0]
    assert v["ky_doi_chieu"] == "" and v["trang_thai_dc"] == "" and v["toi_da_tre_em"] == 0


def test_chinh_sach_tre_hop_le(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    with pytest.raises(S.LoiKhachSan, match="chồng nhau"):
        _cs(db, k, cs_moc_tuoi=[{"tu": 0, "den": 6, "cach": "mien_phi"}, {"tu": 6, "den": 11, "cach": "phu_thu", "phu_thu": 1e5}])
    with pytest.raises(S.LoiKhachSan, match="ít nhất một mốc"):
        _cs(db, k, cs_moc_tuoi=[])
    with pytest.raises(S.LoiKhachSan, match="số tiền phụ thu"):
        _cs(db, k, cs_moc_tuoi=[{"tu": 6, "den": 11, "cach": "phu_thu"}])
    k = _cs(db, k)
    t = S.chinh_sach_tre_cong(k)
    assert t["dong"][0] == "Nhận trẻ em mọi lứa tuổi." and "6–11 tuổi: phụ thu 150.000 đ/đêm (gồm ăn sáng)." in t["dong"]
    assert "Từ 12 tuổi: tính như người lớn." in t["dong"]


def _phong(s, k, lp, tuoi, nl=2, sp=1):
    from app.services import khach_san_vtd as S
    r = S.chi_tiet_cong(s, k.id, VAO, RA, nl, len(tuoi), sp, HN, ",".join(map(str, tuoi)))
    return next(p for p in r["phong"] if p["id"] == lp.id)


def test_tim_phong_tre_em(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)                                   # Deluxe 2 NL, trẻ em chưa xác nhận
    p = _phong(db, k, lp, [4])
    assert not p["vua"] and "đang được xác nhận" in p["ly_do"]
    assert _phong(db, k, lp, [])["vua"]                          # không có trẻ — như cũ
    k = _cs(db, k)
    assert not _phong(db, k, lp, [4, 8])["vua"]                   # loại phòng chưa xác nhận trẻ em ở chung
    S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": lp.ten, "toi_da_nguoi_lon": 2, "so_phong": 3, "toi_da_tre_em": 1,
                                              "giuong_phu_toi_da": 1}, lp.id)
    dem = (RA - VAO).days
    assert _phong(db, k, lp, [4])["phu_thu_ky"] == 0
    assert _phong(db, k, lp, [8])["phu_thu_ky"] == 150000 * dem
    p = _phong(db, k, lp, [4, 8])                                # bé 8 tuổi nằm giường phụ, bé 4 tuổi miễn phí
    assert p["vua"] and p["phu_thu_ky"] == 350000 * dem and p["phu_thu_ct"] == ["1 giường phụ"]
    assert _phong(db, k, lp, [13])["phu_thu_ky"] == 350000 * dem  # 13 tuổi tính như người lớn → giường phụ
    p = _phong(db, k, lp, [4, 8, 10])
    assert not p["vua"] and "không đủ chỗ" in p["ly_do"]
    assert _phong(db, k, lp, [4, 8, 10], nl=2, sp=2)["vua"]      # hai phòng thì đủ
    k = _cs(db, k, cs_nhan_tre_em="tu_tuoi", cs_tre_tu_tuoi=6)
    assert "từ 6 tuổi" in _phong(db, k, lp, [4])["ly_do"]
    r = S.chi_tiet_cong(db, k.id, VAO, RA, 2, 1, 1, HN, "")
    assert not r["phong"][0]["vua"] and "Chọn tuổi" in r["phong"][0]["ly_do"]


def test_dat_cong_phu_thu(db, k3):  # noqa: F811
    from app.services import don_ks_vtd as D
    from app.services import khach_san_vtd as S
    k, lp, g = k3
    _cs(db, k)
    S.luu_loai_phong(db, _u(db, "dh"), k.id, {"ten": lp.ten, "toi_da_nguoi_lon": 2, "so_phong": 3, "toi_da_tre_em": 1,
                                              "giuong_phu_toi_da": 1}, lp.id)
    base = {"vao": VAO, "ra": RA, "nguoi_lon": 2, "chon": [{"goi_id": g.id, "so": 1}], "ho_ten": "Nguyễn Thị Lan",
            "lien_he": "0901 000 001", "dong_y": True}
    with pytest.raises(D.LoiDon, match="Chọn tuổi"):
        D.dat(db, _tk(db), k.id, {**base, "tre_em": 2}, NAY)
    t = S.tinh_lua_chon(db, k.id, VAO, RA, [{"goi_id": g.id, "so": 1}], HN, 2, 2, [4, 8])
    phong = 1_400_000 * 2 + 1_000_000
    assert t["phu_thu"] == 350000 * 3 and t["tien_phong"] == phong + 350000 * 3
    d = D.dat(db, _tk(db), k.id, {**base, "tre_em": 2, "tuoi_tre_em": [4, 8]}, NAY)
    assert int(d.tien_phong) == phong + 350000 * 3 and d.dong[0]["phu_thu"] == 350000 * 3
    assert int(d.thue_phi) == round((phong + 350000 * 3) * 0.15) and d.yeu_cau.startswith("Tuổi trẻ em: 4, 8")
