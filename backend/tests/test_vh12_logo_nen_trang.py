# -*- coding: utf-8 -*-
"""VH-12 · /xe: logo trên ô nền trắng bo tròn, to hơn, viền ba màu và quầng sáng (Chủ tịch duyệt 11/11/2026).
Shell.tsx (làn R2) không sửa — /xe đổi sang bản chữ navy khi mở và trả lại khi rời."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_doi_logo_nen_sang_va_tra_lai():
    s = _w("app", "xe", "page.tsx")
    assert 'img.setAttribute("src", "/thuong-hieu/v2/khoachu-holdings-ngang.svg")' in s
    assert 'img.setAttribute("src", cu); img.classList.remove("xe-logo-o")' in s
    assert os.path.exists(os.path.join(GOC, "web", "public", "thuong-hieu", "v2", "khoachu-holdings-ngang.svg"))


def test_o_trang_bo_tron_noi_bat():
    s = _w("app", "xe", "page.tsx")
    assert "a.brand img.xe-logo-o{box-sizing:content-box;height:46px" in s and "border-radius:16px" in s
    assert "animation:xe-logo-vien" in s and "prefers-reduced-motion:reduce){a.brand img.xe-logo-o{animation:none}" in s
    assert "khoachu-holdings-ngang" not in _w("components", "Shell.tsx")
