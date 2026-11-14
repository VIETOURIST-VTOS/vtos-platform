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
    # R5-25 (Chủ tịch duyệt 14/11/2026): nút lên thanh đầu navy như mọi bàn — vẫn mở Lịch xe 90 ngày tại chỗ.
    assert 'className="n90s xe-n90s"' in s and "Lịch xe 90 ngày</span>" in s
    assert 'setNhom("dispatch"); setTrang("lich-90")' in s


def test_nut_vang_sang_va_co_so_trong():
    s = _w("app", "xe", "page.tsx")
    # R5-25: kiểu nút là `.n90s` chung (globals.css), số trống nền hồng logo.
    assert ".n90s b{" in _w("app", "globals.css")
    assert '/fleet/lich-xe-tuong-lai?so_ngay=30' in s and "{trong30} trống</b>" in s


def test_van_giu_nut_trong_dieu_xe():
    s = _w("app", "xe", "page.tsx")
    assert '{ ma: "lich-90", ten: "Lịch xe 90 ngày", toi: "/lenh-dieu-xe" }' in s
