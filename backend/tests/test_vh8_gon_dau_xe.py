# -*- coding: utf-8 -*-
"""VH-8 · /xe gọn đầu trang (Chủ tịch dặn 11/11/2026): bỏ «Chỉ dữ liệu đội xe», «Trang tổng CRM» gộp vào chữ
«HỆ THỐNG ĐIỀU HÀNH», năm nhóm chia đều, hai cửa nhập canh giữa không dòng bước, khối hiệu quả bỏ ghi chú."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_dau_trang_gon():
    s = _w("app", "xe", "page.tsx")
    assert "Chỉ dữ liệu đội xe" not in s
    assert 'className="xe-ra"' not in s and "Trang tổng CRM →</Link>" not in s
    assert 'document.querySelector("a.brand small")' in s and 'window.location.assign("/")' in s


def test_nam_nhom_chia_deu_va_cua_nhap_canh_giua():
    s = _w("app", "xe", "page.tsx")
    assert ".xe-nhom{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))" in s
    assert "{c.buoc}" not in s and "align-items:center;justify-content:center;text-align:center!important" in s


def test_khoi_hieu_qua_bo_ghi_chu_chi_o_xe():
    k = _w("components", "KhoiV14.tsx")
    assert "{moc && !gon && " in k and "{o.so_sanh && !gon && " in k and "o.tieu_hao_nguong_thieu && !gon && (" in k
    assert "Mũi tên {o.so_sanh.nhan}." in k            # màn Chủ tịch vẫn có
