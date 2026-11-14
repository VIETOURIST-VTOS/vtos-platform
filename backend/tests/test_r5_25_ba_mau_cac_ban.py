# -*- coding: utf-8 -*-
"""R5-25 · Ba màu logo và khung navy cho các bàn còn lại (Chủ tịch duyệt bản xem trước 14/11/2026 07:14)."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
doc = lambda p: (WEB / p).read_text(encoding="utf-8")  # noqa: E731


def test_ban_doi_xe_ve_khuon_chung():
    s = doc("app/xe/page.tsx")
    assert '<div className="mh01-ban">' in s and 'className="mh01-ban-ten"' in s
    assert s.count("Lịch xe 90 ngày</span>") == 1                       # một nút một chỗ
    assert "inset 0 -3px 0 #5fae66" in s                                # vạch lá dưới tab đang mở
    assert ".xe-so-chu{background:#fff!important" in s                  # ba ô số thành thẻ trắng
    assert "--xe-do:#d6336c" in s                                        # đỏ cũ → hồng logo


def test_ban_ptgd_doan_co_thanh_dau_va_dau_bang_navy():
    s = doc("app/ptgd-doan/page.tsx")
    assert '<div className="ban-navy">' in s and "Bàn làm việc Phó TGĐ Đoàn" in s and "<NutLich90 />" in s
    assert ".ban-navy th{" in doc("app/globals.css").replace("html.vtos-khung-ban th,", "")


def test_khung_ban_chung_o_moi_ban():
    k = doc("components/KhungNhung.tsx")
    assert "export function batKhungBan(" in k
    assert "if (khungBan) batKhungBan(doc, b);" in doc("app/xe/page.tsx")
    assert s_has(doc("app/xe/page.tsx"), "mo={moSan || undefined} khungBan />", "ten={caNhan.ten} khungBan />")
    assert "anDauBan khungBan />" in doc("app/marketing/page.tsx")
    assert 'cuaBan={(h) => h !== "/"} khungBan />' in doc("components/Shell.tsx")


def s_has(s, *ds):
    return all(d in s for d in ds)


def test_viec_nghiem_trong_mau_hong_logo():
    c = doc("components/KhoiVanHanh.css")
    assert ".vh-khoi.do{border-left-color:var(--vtos-logo-hong)}" in c and ".c-do{background:var(--vtos-logo-hong)}" in c
