# -*- coding: utf-8 -*-
"""VH-11 · /xe (Chủ tịch duyệt 11/11/2026): bỏ nút nhóm «Hiệu quả» (tổng kết kỳ + bản tin sáng trùng bàn
làm việc); hai phần không trùng — xếp hạng xe & tài xế, nhìn lại thuê xe ngoài — về «Báo cáo & chi phí»;
thêm nút «Trang chủ» đầu dòng, về bàn làm việc tại chỗ."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_bo_nhom_hieu_qua_chuyen_hai_trang_ve_bao_cao():
    s = _w("app", "xe", "page.tsx")
    assert 'ma: "performance"' not in s and 'ten: "Hiệu quả",' not in s
    i = s.index('{ ma: "finance", ten: "Báo cáo & chi phí"')
    j = s.index('{ ma: "technical"')
    nhom = s[i:j]
    assert '{ ma: "hieu-qua", ten: "Xếp hạng xe & tài xế", toi: "/hieu-qua-doi-xe?chi=xep-hang" }' in nhom
    assert '{ ma: "nhin-lai", ten: "Nhìn lại thuê xe ngoài", toi: "/doi-xe?tab=nhin-lai" }' in nhom


def test_nut_trang_chu_dau_dong():
    s = _w("app", "xe", "page.tsx")
    nav = s[s.index('<nav aria-label="Nghiệp vụ đội xe" className="xe-nhom">'):]
    assert nav.index("Trang chủ") < nav.index("{NHOM.map(")
    assert 'aria-pressed={nhom === null}' in nav and "setNhom(null); setTrang(null)" in nav


def test_xep_hang_giau_khoi_trung():
    h = _w("app", "hieu-qua-doi-xe", "page.tsx")
    assert 'get("chi") === "xep-hang"' in h
    assert "{bt && !chiXepHang &&" in h and "{d.tong && !chiXepHang &&" in h
