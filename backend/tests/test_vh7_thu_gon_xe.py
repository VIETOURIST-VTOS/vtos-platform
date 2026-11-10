# -*- coding: utf-8 -*-
"""VH-7 · /xe thu gọn như trang Khách sạn (kh.vietourist.vn/hotel): nội dung tối đa 1440px, canh giữa (Chủ tịch duyệt 11/11/2026)."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_xe_rong_toi_da_1440_canh_giua():
    s = open(os.path.join(GOC, "web", "app", "xe", "page.tsx"), encoding="utf-8").read()
    assert "const RONG = <style>{`main{max-width:1440px!important;margin:0 auto!important}" in s
    g = open(os.path.join(GOC, "web", "app", "globals.css"), encoding="utf-8").read()
    # 1440px: đo trên kh.vietourist.vn/hotel (.kr-in max-width 1440px), Chủ tịch chọn 11/11/2026.


def _xe():
    return open(os.path.join(GOC, "web", "app", "xe", "page.tsx"), encoding="utf-8").read()


def test_tieu_de_len_dau_nam_nhom_xuong_duoi():
    s = _xe()
    assert s.index('<div className="xe-dau">') < s.index('<nav aria-label="Nghiệp vụ đội xe" className="xe-nhom">')
    assert "@keyframes xe-sang" in s and "prefers-reduced-motion:reduce){.xe-dau h1{animation:none" in s


def test_hai_tang_va_ba_the_so():
    s = _xe()
    assert "body,.shell{background:#eaf0f7!important}" in s
    assert ".xe-so-chu{" in s
    k = open(os.path.join(GOC, "web", "components", "KhoiV14.tsx"), encoding="utf-8").read()
    assert 'className={gon ? "xe-so-chu" : undefined}' in k
    assert "repeat(auto-fit,minmax(min(100%,220px),1fr))" in s     # thẻ việc giãn đều hết hàng
    assert 'className="xe-cho"' in s                                # khung chờ thay chữ «Đang đọc số…»
