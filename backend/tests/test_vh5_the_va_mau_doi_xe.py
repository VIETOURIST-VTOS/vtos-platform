# -*- coding: utf-8 -*-
"""VH-5 · kiểu thẻ + đồng bộ màu trang chi tiết đội xe + sửa tràn ngang điện thoại (Chủ tịch duyệt 10/11/2026)."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_1_bon_trang_doi_xe_boc_bo_mau():
    for p in (("app", "doi-xe", "page.tsx"), ("app", "doi-xe", "gia-dau", "page.tsx"),
              ("app", "doi-xe", "phat-tai-xe", "page.tsx"), ("app", "doi-xe", "xe-hom-nay", "page.tsx")):
        s = _w(*p)
        assert 'import MauDoiXe from "@/components/doixe/MauDoiXe";' in s, p
        assert "<Shell><MauDoiXe>" in s, p


def test_2_bo_mau_chi_song_trong_dx_mau():
    s = _w("components", "doixe", "MauDoiXe.tsx")
    css = s.split("const CSS = `", 1)[1].split("`;", 1)[0]
    for dong in css.strip().splitlines():
        assert dong.startswith(".dx-mau"), dong          # không một luật nào lọt ra ngoài trang đội xe
    assert "--dx-nhan:#2c5fa2" in css


def test_3_tab_doi_xe_xuong_hang_khong_cat_chu():
    s = _w("app", "doi-xe", "page.tsx")
    assert '<div className="dx-tabs">' in s
    assert ".dx-mau .dx-tabs{display:flex;flex-wrap:wrap" in _w("components", "doixe", "MauDoiXe.tsx")


def test_4_viec_can_xu_ly_la_the():
    s = _w("app", "xe", "page.tsx")
    assert 'className="xe-the-luoi"' in s and "xe-the-ma" in s and "NHAN_MUC" in s
    assert ".xe-the{background:#fbfcfe;border:1px solid #d6dfeb;border-radius:13px" in s     # VH-7: thẻ trên nền thẻ trắng


def test_5_khoi_hieu_qua_xuong_hang_tren_dien_thoai():
    k = _w("components", "KhoiV14.tsx")
    assert '<div className="mh01-dau" style={{ flexWrap: "wrap", rowGap: 6 }}>' in k
    assert k.count('className="tag" style={{ whiteSpace: "normal" }}') >= 2
