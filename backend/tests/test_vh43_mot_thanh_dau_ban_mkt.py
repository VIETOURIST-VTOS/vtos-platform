"""VH-43 · Bàn Marketing chỉ còn MỘT thanh đầu bàn (Chủ tịch 13/11/2026): khuôn `.mh01-ban` như bàn Chủ tịch và
bàn GĐ đội xe — tên bàn theo vai, ô Hôm nay, nút Lịch xe 90 ngày; thanh đầu của bàn nhúng bị giấu."""
import os

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_1_mot_thanh_dau_khuon_chung():
    s = _w("app", "marketing", "page.tsx")
    ve = s[s.index("function Marketing()"):]
    assert ve.count('className="mh01-ban"') == 1 and 'className="mkt-ban"' not in ve
    assert '<h1 className="mh01-ban-ten">{tenBan(role)}</h1>' in ve
    assert '<div className="mh01-ban-ngay"><span>Hôm nay</span>' in ve and "<NutLich90 />" in ve
    assert ve.index('className="mh01-ban"') < ve.index('className="mkt-nhom"')     # thanh thứ hai, trên bảy nhóm


def test_2_ten_theo_vai_va_giau_thanh_cua_ban_nhung():
    s = _w("app", "marketing", "page.tsx")
    assert '"Bàn làm việc P.TGĐ Marketing"' in s and '"Bàn làm việc nhân viên Marketing"' in s
    assert "anDauBan />" in s
    assert '.mh01-ban{display:none!important}' in _w("components", "KhungNhung.tsx")


def test_3_lich_xe_90_mo_tai_cho():
    s = _w("app", "marketing", "page.tsx")
    assert 'if (h.startsWith("/lich-xe-trong")) { e.preventDefault(); setNhom(""); setCon(0); setKhung(h); }' in s
    assert '"/lich-xe-trong", "/ptgd-mkt"' in s


def test_4_chu_he_thong_dieu_hanh_ve_crm_tong():
    s = _w("app", "marketing", "page.tsx")
    assert 'document.querySelector("a.brand small")' in s and 'window.location.assign("/")' in s
