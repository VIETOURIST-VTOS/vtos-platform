# -*- coding: utf-8 -*-
"""VH-6 · bấm chi tiết ở /xe KHÔNG nhảy sang màn CRM tổng (Chủ tịch dặn 10/11/2026).

Bấm thử thấy bốn lối rò: liên kết của khối hiệu quả, nút «Mở toàn trang ↗», nút ↗ trong trang chi tiết mở
tab mới, và vụn đường «VTOS · Đội xe» dẫn về trang chủ. Phép thử giữ cả bốn lối đã bịt."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_1_lien_ket_doi_xe_mo_tai_cho():
    s = _w("app", "xe", "page.tsx")
    assert "const DUONG_DOI_XE = [" in s and "onClickCapture={giuTaiCho}" in s
    for t in ('"/doi-xe"', '"/lai-lo-doi-xe"', '"/lenh-dieu-xe"', '"/tai-xe"', '"/nap-du-lieu"'):
        assert t in s.split("const DUONG_DOI_XE = [", 1)[1].split("]", 1)[0], t


def test_2_khong_con_mo_toan_trang():
    assert "Mở toàn trang" not in _w("app", "xe", "page.tsx").split("bỏ «Mở toàn trang ↗»", 1)[1]


def test_3_trong_khung_khong_mo_tab_moi_khong_ve_trang_chu():
    s = _w("app", "xe", "page.tsx")
    k = s.split("function KhungNhung", 1)[1].split("\n}\n", 1)[0]
    assert 'doc.addEventListener("click"' in k and "e.preventDefault();" in k
    assert "if (laDoiXe(h)) f.contentWindow?.location.assign(h);" in k
    assert ".thanh-viec .tv-duong" in k


def test_4_khoa_trung_o_doi_xe():
    s = _w("app", "doi-xe", "page.tsx")
    assert '<DonGiaNgay key={"dg-" + chon.id}' in s
