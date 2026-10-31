# -*- coding: utf-8 -*-
"""KS-16k · Chính sách trẻ em theo cách Agoda YCS (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Chính sách tuổi + giá trẻ em mặc định theo nhóm tuổi (luôn miễn phí / cố định / % giá phòng) + giá ăn sáng riêng;
     trên nhóm tuổi lớn nhất = người lớn. Nhóm tuổi chồng / hở → từ chối.
  2. Số trẻ ở chung miễn phí mỗi phòng (nhỏ nhất trước); vượt sức chứa cơ bản → giường phụ (trẻ lớn nhất trước).
  3. Ghi đè: gói → loại phòng → khách sạn; gói «tính trẻ như người lớn».
  4. Ô nào chưa xác nhận mà cần tới → không đặt ngay, mời gửi yêu cầu. Giường phụ «theo xác nhận KS» vẫn bán, gắn nhãn.
"""
import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO, _ks, _mo_ban, HN
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401

BANG = [{"tu": 0, "den": 1, "nhom": "so_sinh", "cach": "mien_phi", "an_sang": 0},
        {"tu": 2, "den": 5, "nhom": "tre_em", "cach": "co_dinh", "gia": 100000, "an_sang": 80000},
        {"tu": 6, "den": 11, "nhom": "tre_em", "cach": "co_dinh", "gia": 150000, "an_sang": 120000}]
CS = {"cs_nhan_tre_em": "moi_tuoi", "cs_moc_tuoi": BANG, "cs_so_tre_mien_phi": 1, "cs_phi_giuong_phu": 350000,
      "cs_giuong_phu_kieu": "co_dinh", "cs_noi": "Miễn phí"}
DEM = (RA - VAO).days
PHONG = 1_400_000 * 2 + 1_000_000          # Deluxe «Có bữa sáng» 18–21/12


def _cs(s, k, **them):
    from app.services import khach_san_vtd as S
    return S.luu_ks(s, _u(s, "dh"), {**S._ks_noi_bo(k), **CS, **them}, k.id)


def _lp(s, k, lp, **them):
    from app.services import khach_san_vtd as S
    d = {"ten": lp.ten, "toi_da_nguoi_lon": 2, "so_phong": 3, "toi_da_tre_em": 2, "suc_chua": 2, "khach_them_toi_da": 1,
         "giuong_phu_toi_da": 1, **them}
    return S.luu_loai_phong(s, _u(s, "dh"), k.id, d, lp.id)


def _g(s, k, lp, tuoi, nl=2, sp=1):
    from app.services import khach_san_vtd as S
    r = S.chi_tiet_cong(s, k.id, VAO, RA, nl, len(tuoi), sp, HN, ",".join(map(str, tuoi)))
    return next(p for p in r["phong"] if p["id"] == lp.id)["goi"][0]


def test_kiem_bang(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    with pytest.raises(S.LoiKhachSan, match="hở"):
        _cs(db, k, cs_moc_tuoi=[BANG[0], BANG[2]])
    with pytest.raises(S.LoiKhachSan, match="chồng"):
        _cs(db, k, cs_moc_tuoi=[BANG[0], {**BANG[1], "tu": 1}])
    with pytest.raises(S.LoiKhachSan, match="1 đến 100"):
        _cs(db, k, cs_moc_tuoi=[{**BANG[0], "cach": "phan_tram", "gia": 150}])
    k = _cs(db, k)
    t = S.chinh_sach_tre_cong(k)["dong"]
    assert "Từ 12 tuổi: tính như người lớn." in t and any("6–11 tuổi: 150.000 đ / đêm" in x for x in t)
    assert any("ăn sáng 120.000 đ / đêm" in x for x in t)
    k2 = _ks(db, "KS Hai")
    assert S.chinh_sach_tre_cong(k2)["dong"] == ["Cần khách sạn xác nhận."]


def test_tinh_kieu_agoda(db):
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)                         # gói «Có bữa sáng»
    assert not _g(db, k, lp, [4])["vua"]               # chính sách chưa xác nhận
    k = _cs(db, k)
    assert "số trẻ em của phòng" in _g(db, k, lp, [4])["ly_do"]
    _lp(db, k, lp)
    x = _g(db, k, lp, [4])                             # 1 trẻ miễn phí ở chung; ăn sáng 80k
    assert x["vua"] and x["phu_thu_ky"] == 80000 * DEM
    x = _g(db, k, lp, [4, 8])                          # bé 4 miễn phí; bé 8 = khách thứ 3 → giường phụ 350k + ăn sáng 120k
    assert x["phu_thu_ky"] == (80000 + 350000 + 120000) * DEM
    assert {c["nhan"] for c in x["phu_thu_ct"]} >= {"Bé 8 tuổi · giường phụ", "Bé 4 tuổi · ở chung miễn phí"}
    x = _g(db, k, lp, [1, 8])                          # sơ sinh luôn miễn phí, không tốn suất miễn phí → bé 8 ở chung miễn phí
    assert x["phu_thu_ky"] == 120000 * DEM
    assert "không đủ chỗ" in _g(db, k, lp, [1, 4, 8])["ly_do"]   # 3 trẻ > tối đa 2 trẻ
    assert "không đủ chỗ" in _g(db, k, lp, [3, 4, 8])["ly_do"]   # 2 trẻ phải trả → 2 giường phụ > 1
    assert _g(db, k, lp, [13])["phu_thu_ky"] == 350000 * DEM     # 13 tuổi = người lớn → giường phụ
    k = _cs(db, k, cs_tre_mp_tinh_suc_chua=True)
    assert _g(db, k, lp, [4])["phu_thu_ky"] == (350000 + 80000) * DEM   # trẻ miễn phí tính vào sức chứa → giường phụ
    k = _cs(db, k, cs_tre_mp_tinh_suc_chua=False, cs_so_tre_mien_phi=None)
    assert "số trẻ miễn phí" in _g(db, k, lp, [4])["ly_do"]
    assert _g(db, k, lp, [1])["vua"]                   # sơ sinh luôn miễn phí → không cần số trẻ miễn phí


def test_ghi_de_phong_va_goi(db):
    from app.services import khach_san_vtd as S
    k = _cs(db, _ks(db))
    lp, g, _x = _mo_ban(db, k)
    _lp(db, k, lp, so_tre_mien_phi=0, phi_giuong_phu=10, giuong_phu_kieu="phan_tram",
        gia_tre_rieng=[{"tu": 0, "den": 6, "cach": "phan_tram", "gia": 20, "an_sang": 0}])
    _lp(db, k, lp, suc_chua=3, so_tre_mien_phi=0, phi_giuong_phu=10, giuong_phu_kieu="phan_tram",
        gia_tre_rieng=[{"tu": 0, "den": 6, "cach": "phan_tram", "gia": 20, "an_sang": 0}])
    x = _g(db, k, lp, [5])                             # phòng: 0 trẻ miễn phí, 20% giá phòng; 7 tuổi trở lên = người lớn
    assert x["phu_thu_ky"] == round(PHONG * 0.2)
    assert _g(db, k, lp, [8])["phu_thu_ky"] == 0       # 8 tuổi = người lớn thứ 3, sức chứa 3 → không phụ thu
    assert _g(db, k, lp, [8, 9])["phu_thu_ky"] == round(PHONG * 0.10)  # người thứ 4 → giường phụ 10% giá phòng
    S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": g.ten, "bua_sang": True, "huy_truoc_ngay": 2, "tre_em_che_do": "nhu_nguoi_lon",
                                        "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 1_000_000,
                                                 "gia_cuoi_tuan": 1_400_000}]}, g.id)
    S.gui_duyet_goi(db, _u(db, "dh"), g.id)
    S.duyet_goi(db, _u(db, "tp"), g.id, True)
    assert _g(db, k, lp, [3, 4])["phu_thu_ky"] == round(PHONG * 0.10)  # gói tính trẻ như người lớn → 4 người → giường phụ
    with pytest.raises(S.LoiKhachSan, match="ít nhất một nhóm"):
        S.luu_goi(db, _u(db, "dh"), lp.id, {"ten": g.ten, "tre_em_che_do": "rieng", "mua": [
            {"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 1_000_000}]}, g.id)


def test_dat_giuong_phu_cho_xac_nhan(db, k3):  # noqa: F811
    from app.services import don_ks_vtd as D
    from app.services import khach_san_vtd as S
    k, lp, g = k3
    _cs(db, k)
    _lp(db, k, lp, giuong_phu_xac_nhan=True)
    t = S.tinh_lua_chon(db, k.id, VAO, RA, [{"goi_id": g.id, "so": 1}], HN, 2, 2, [4, 8])
    pt = (80000 + 350000 + 120000) * DEM
    assert t["phu_thu"] == pt and t["cho_xac_nhan"] and t["tien_phong"] == PHONG + pt
    d = D.dat(db, _tk(db), k.id, {"vao": VAO, "ra": RA, "nguoi_lon": 2, "tre_em": 2, "tuoi_tre_em": [4, 8],
                                  "chon": [{"goi_id": g.id, "so": 1}], "ho_ten": "Nguyễn Thị Lan", "lien_he": "0901 000 001",
                                  "dong_y": True}, NAY)
    assert int(d.tien_phong) == PHONG + pt and d.dong[0]["giuong_phu_cho_xac_nhan"] is True
    assert int(d.thue_phi) == round((PHONG + pt) * 0.15) and d.yeu_cau.startswith("Tuổi trẻ em: 4, 8")
    with pytest.raises(D.LoiDon, match="Chọn tuổi"):
        D.dat(db, _tk(db, 2), k.id, {"vao": VAO, "ra": RA, "nguoi_lon": 2, "tre_em": 1, "chon": [{"goi_id": g.id, "so": 1}],
                                     "ho_ten": "Trần Văn Bình", "lien_he": "0901 000 002", "dong_y": True}, NAY)
