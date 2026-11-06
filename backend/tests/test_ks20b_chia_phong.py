# -*- coding: utf-8 -*-
"""KS-20b · Nhiều phòng, khai khách từng phòng (bản v1.3 D2/M1/M2 — Chủ tịch chọn «Máy nhận đúng cách chia», 06/11/2026).

  1. Khách khai từng phòng [{nl, te, tuoi}], tối đa 9; mỗi phòng ≥ 1 người lớn; có trẻ thì phải có tuổi từng bé.
  2. Máy tự ghép phòng ↔ nhóm khách hợp sức chứa (phòng rộng cho nhóm đông); phụ thu tính theo người trong TỪNG phòng.
  3. Khách đổi cách ghép (`xep`); ghép không vừa thì báo rõ phòng nào.
  4. Số phòng chọn phải bằng số phòng khai.
  5. Đơn ghi «Phòng 1 — … · loại phòng · gói» để Điều hành gửi khách sạn; tổng người lớn / trẻ em = cộng các phòng.
  6. Giao diện có ô khai từng phòng, khung «Chia phòng», cột «Đã chọn x/y phòng» và gửi chia / xep.
"""
from pathlib import Path

import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO, HN
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401
from tests.test_ks16k_gia_tre_em_agoda import DEM, _cs, _lp


def _family(s, k):
    from app.services import khach_san_vtd as S
    lp = S.luu_loai_phong(s, _u(s, "dh"), k.id, {"ten": "Family Suite", "toi_da_nguoi_lon": 3, "so_phong": 2, "toi_da_tre_em": 1,
                                                 "suc_chua": 3, "khach_them_toi_da": 1, "giuong_phu_toi_da": 1})
    g = S.luu_goi(s, _u(s, "dh"), lp.id, {"ten": "Có bữa sáng", "bua_sang": True, "huy_truoc_ngay": 2,
                                          "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 2_000_000,
                                                   "gia_cuoi_tuan": 2_000_000, "gia_niem_yet": 2_500_000}]})
    S.gui_duyet_goi(s, _u(s, "dh"), g.id)
    S.duyet_goi(s, _u(s, "tp"), g.id, True)
    return lp, g


@pytest.fixture()
def hai(db, k3):
    k, lp, g = k3
    k = _cs(db, k)
    _lp(db, k, lp)                                       # Deluxe: 2 NL cơ bản, +1 giường phụ, tối đa 2 trẻ
    fl, fg = _family(db, k)
    return k, g, fg


def _tinh(s, k, chon, chia, xep=None):
    from app.services import khach_san_vtd as S
    return S.tinh_lua_chon(s, k.id, VAO, RA, chon, HN, chia=chia, xep=xep)


def test_ks20b_1_doc_chia():
    from app.services import khach_san_vtd as S
    assert S.doc_chia([]) is None
    assert S.doc_chia([{"nl": 2, "te": 1, "tuoi": [7]}]) == [{"nl": 2, "te": 1, "tuoi": [7]}]
    with pytest.raises(S.LoiKhachSan, match="Tối đa 9"):
        S.doc_chia([{"nl": 1}] * 10)
    with pytest.raises(S.LoiKhachSan, match="Phòng 2 cần ít nhất 1 người lớn"):
        S.doc_chia([{"nl": 1}, {"nl": 0, "te": 1, "tuoi": [5]}])
    with pytest.raises(S.LoiKhachSan, match="Phòng 1: chọn tuổi"):
        S.doc_chia([{"nl": 2, "te": 1}])
    assert S.ta_nhom({"nl": 2, "te": 2, "tuoi": [4, 8]}) == "2 người lớn + 2 trẻ (4, 8 tuổi)"


def test_ks20b_2_may_tu_ghep_phong_rong_cho_nhom_dong(db, hai):
    k, g, fg = hai
    chon = [{"goi_id": g.id, "so": 1}, {"goi_id": fg.id, "so": 1}]      # Deluxe trước, Family sau
    r = _tinh(db, k, chon, [{"nl": 1}, {"nl": 4}])
    assert r["xep"] == [0, 1]                                            # Deluxe ↔ 1 NL; Family ↔ 4 NL
    de, fa = r["dong"]
    assert de["khach"] == [{"phong": 1, "nl": 1, "te": 0, "tuoi": []}] and de["phu_thu"] == 0
    assert fa["khach"] == [{"phong": 2, "nl": 4, "te": 0, "tuoi": []}]
    assert fa["phu_thu"] == 350_000 * DEM                                # người thứ 4 nằm giường phụ ở Family
    r = _tinh(db, k, chon, [{"nl": 4}, {"nl": 1}])                      # khai ngược thứ tự → máy vẫn ghép đúng
    assert r["xep"] == [1, 0] and r["dong"][1]["khach"][0]["phong"] == 1


def test_ks20b_3_khach_doi_cach_ghep(db, hai):
    from app.services import khach_san_vtd as S
    k, g, fg = hai
    chon = [{"goi_id": g.id, "so": 1}, {"goi_id": fg.id, "so": 1}]
    r = _tinh(db, k, chon, [{"nl": 2}, {"nl": 3}], xep=[1, 0])          # khách đổi: Deluxe ↔ 3 NL (giường phụ)
    assert r["xep"] == [1, 0] and r["dong"][0]["phu_thu"] == 350_000 * DEM and r["dong"][1]["phu_thu"] == 0
    with pytest.raises(S.LoiKhachSan, match="Phòng 2 .*không xếp được vào «Deluxe hướng biển»"):
        _tinh(db, k, chon, [{"nl": 1}, {"nl": 4}], xep=[1, 0])
    r = _tinh(db, k, chon, [{"nl": 1}, {"nl": 4}], xep=[0, 0])          # xep sai → máy tự ghép
    assert r["xep"] == [0, 1]


def test_ks20b_4_so_phong_phai_bang_so_khai(db, hai):
    from app.services import khach_san_vtd as S
    k, g, fg = hai
    with pytest.raises(S.LoiKhachSan, match="khai 2 phòng nhưng mới chọn 1"):
        _tinh(db, k, [{"goi_id": g.id, "so": 1}], [{"nl": 2}, {"nl": 2}])
    with pytest.raises(S.LoiKhachSan, match="chọn 3 phòng nhưng chỉ khai 2"):
        _tinh(db, k, [{"goi_id": g.id, "so": 3}], [{"nl": 2}, {"nl": 2}])


def test_ks20b_5_phu_thu_theo_nguoi_trong_tung_phong(db, hai):
    k, g, _fg = hai
    chon = [{"goi_id": g.id, "so": 2}]
    r = _tinh(db, k, chon, [{"nl": 1, "te": 2, "tuoi": [4, 8]}, {"nl": 2}])
    phong1 = [x for x in r["dong"][0]["khach"] if x["phong"] == 1][0]
    assert phong1["tuoi"] == [4, 8]
    # Phòng 1: bé 4 ở chung miễn phí, bé 8 trả 150k + ăn sáng 80k + 120k; phòng 2 không phụ thu
    assert r["dong"][0]["phu_thu"] == (150_000 + 80_000 + 120_000) * DEM


def test_ks20b_6_dat_ghi_chia_phong(db, hai):
    from app.services import don_ks_vtd as KV
    k, g, fg = hai
    d = KV.dat(db, _tk(db), k.id, {"vao": VAO, "ra": RA, "chon": [{"goi_id": g.id, "so": 1}, {"goi_id": fg.id, "so": 1}],
                                    "chia": [{"nl": 4}, {"nl": 1, "te": 1, "tuoi": [7]}], "ho_ten": "Nguyễn Thị Lan",
                                    "lien_he": "0901 000 001", "dong_y": True, "yeu_cau": "Phòng gần nhau"}, NAY)
    db.commit()
    assert d.so_phong == 2 and d.nguoi_lon == 5 and d.tre_em == 1
    assert d.yeu_cau.startswith("Phòng 1 — 4 người lớn · Family Suite · Có bữa sáng\n"
                                "Phòng 2 — 1 người lớn + 1 trẻ (7 tuổi) · Deluxe hướng biển · Có bữa sáng\n")
    assert d.yeu_cau.endswith("Phòng gần nhau")
    assert [kh["phong"] for x in d.dong for kh in x["khach"]] == [2, 1]
    with pytest.raises(KV.LoiDon, match="mới chọn 1"):
        KV.dat(db, _tk(db, 2), k.id, {"vao": VAO, "ra": RA, "chon": [{"goi_id": g.id, "so": 1}], "chia": [{"nl": 1}, {"nl": 1}],
                                       "ho_ten": "Trần Văn Bình", "lien_he": "0901 000 002", "dong_y": True}, NAY)


def test_ks20b_7_giao_dien():
    c = (Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "KhachSanVtd.tsx").read_text(encoding="utf-8")
    for t in ("Phòng và khách", "Thêm phòng", "Chia phòng", "Đã chọn", "chia: q.chia", "xep:", "ksv13-chia", "ksv13-side",
              "Hệ thống tự gợi ý phòng hợp sức chứa từng phòng; bạn đổi được.", "/phòng ·"):
        assert t in c, t
