# -*- coding: utf-8 -*-
"""VH-14 · /xe (Chủ tịch dặn 11/11/2026): hộp xổ xuống của tên người dùng chữ tối (hết chữ trắng trên nền
trắng); chức danh GĐ đội xe in tắt «GĐĐH xe» trên thanh đầu. Chỉ trên /xe, Shell.tsx và tên vai máy chủ giữ."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_menu_chu_toi():
    s = _w("web", "app", "xe", "page.tsx")
    assert ".top .menu-toi a{color:#1d2b3d!important" in s


def test_chuc_danh_tat_chi_gd_doi_xe_tren_xe():
    s = _w("web", "app", "xe", "page.tsx")
    assert 'if (user?.role !== "gd_doi_xe") return;' in s and 'classList.add("xe-chuc-tat")' in s
    assert 'html.xe-chuc-tat .top .who-ten b::after{content:"GĐĐH xe"' in s
    assert '"gd_doi_xe": "Giám đốc điều hành đội xe"' in _w("backend", "app", "models", "core.py")
    assert "GĐĐH xe" not in _w("web", "components", "Shell.tsx")
