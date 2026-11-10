# -*- coding: utf-8 -*-
"""VH-10 · /xe: bỏ chữ «THÁNG …» lặp ô chọn kỳ, thay bằng nút vàng «Lịch xe 90 ngày» nổi bật nhất màn
(Chủ tịch duyệt 11/11/2026), mở trang con lich-90 tại chỗ, in số ngày-xe trống 30 ngày tới."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_bo_chu_thang_thay_nut_vang():
    s = _w("app", "xe", "page.tsx")
    assert "<strong>THÁNG {kyDoc(ky)}</strong>" not in s
    assert 'className="xe-n90"' in s and "Lịch xe 90 ngày</span>" in s
    assert 'setNhom("dispatch"); setTrang("lich-90")' in s


def test_nut_vang_sang_va_co_so_trong():
    s = _w("app", "xe", "page.tsx")
    assert ".xe-n90{" in s and "animation:xe-tho" in s and "animation:xe-luot" in s
    assert "prefers-reduced-motion:reduce){.xe-n90,.xe-n90::after{animation:none}" in s
    assert '/fleet/lich-xe-tuong-lai?so_ngay=30' in s and "ngày-xe trống" in s


def test_van_giu_nut_trong_dieu_xe():
    s = _w("app", "xe", "page.tsx")
    assert '{ ma: "lich-90", ten: "Lịch xe 90 ngày", toi: "/lenh-dieu-xe" }' in s
