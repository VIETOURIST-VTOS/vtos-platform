# -*- coding: utf-8 -*-
"""VH-12 → LOGO-1: logo nền trắng đã về thanh đầu dùng chung (làn R2, PR #788). VH-14 gỡ lớp ghi đè tạm ở /xe —
giữ lại hai lớp là vẽ hai lần cùng một thứ, và lần sau R2 chỉnh thì /xe lệch."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_logo_o_thanh_dau_chung_khong_ghi_de_o_xe():
    s = _w("app", "xe", "page.tsx")
    assert "xe-logo-o" not in s and "khoachu-holdings-ngang" not in s
    assert "khoachu-holdings-ngang.svg" in _w("components", "Shell.tsx")
