"""LOGO v2 · 07/11/2026 — anh Tuấn duyệt bản xem thử «Logo v2 trên VTOS và VTD».

"chỉ lấy logo Vietourist và thêm nhận diện màu xanh navy nhiều hơn":
  · mọi thanh trên (VTOS, cổng khách /hotel /restaurant /tours, cổng khách – đối tác – cổ đông – NCC,
    trang đăng nhập) dùng logo Vietourist Holdings bộ v2, không còn dấu VTOS, không còn logo.png cũ;
  · thanh trên navy chính thức #14538D; nút chính và tab đang chọn của cổng là navy;
  · một biểu tượng chung (app-icon-holdings) cho tab trình duyệt và icon app; 16 ảnh chờ nền navy.
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W = os.path.join(ROOT, "web")


def _doc(*p):
    with open(os.path.join(W, *p), encoding="utf-8") as f:
        return f.read()


def test_bo_tep_v2_co_du_va_logo_cu_van_giu():
    for ten in ("khoachu-holdings-nen-toi.svg", "khoachu-holdings-nen-trong.svg", "khoachu-holdings-ngang.svg",
                "bieu-tuong-chinh.svg", "bieu-tuong-nen-toi.svg", "app-icon-holdings.svg"):
        assert os.path.exists(os.path.join(W, "public", "thuong-hieu", "v2", ten)), ten
    # bản dùng trên thanh navy: bỏ ô nền #0B2545 của bản nền tối, giữ nguyên nét
    trong = _doc("public", "thuong-hieu", "v2", "khoachu-holdings-nen-trong.svg")
    assert "#0B2545" not in trong and "#5A9BD4" in trong and "#FF6F96" in trong and "#5FAE66" in trong
    # logo cũ giữ trong kho để tra cứu
    for cu in ("thuong-hieu/vtos-logo-nen-toi.svg", "cong/logo.png"):
        assert os.path.exists(os.path.join(W, "public", cu)), cu


def test_moi_thanh_tren_dung_logo_vietourist_v2():
    logo = "/thuong-hieu/v2/khoachu-holdings-nen-trong.svg"
    for p in (("components", "Shell.tsx"), ("components", "cong", "KhungRieng.tsx"),
              ("components", "cong", "khach", "KhachHang.tsx"), ("components", "cong", "doi-tac", "DoiTac.tsx"),
              ("components", "cong", "co-dong", "CoDong.tsx"), ("components", "cong", "ncc", "CongNcc.tsx"),
              ("components", "cong", "manh.ts")):
        s = _doc(*p)
        # LOGO-1 · 11/11/2026 (Chủ tịch duyệt): thanh đầu CRM đổi sang bản chữ navy trên ô trắng.
        # Các cổng ngoài (khách, đối tác, cổ đông, NCC) vẫn dùng bản nền trong trên thanh navy.
        assert (("/thuong-hieu/v2/khoachu-holdings-ngang.svg" if p == ("components", "Shell.tsx") else logo) in s), p
        assert "/cong/logo.png" not in s and "VTD<small>" not in s and "VIET<em>OURIST" not in s, p


def test_navy_chinh_thuc_tren_thanh_va_nut():
    assert "--vtos-nav-bg:       #14538D" in _doc("app", "tokens.css")
    kr = _doc("components", "cong", "KhungRieng.tsx")
    assert ".kr-top{background:#14538D" in kr and "border-bottom:4px solid #0B2545" in kr
    css = _doc("public", "cong", "vtd.css")
    i = css.index("LOGO v2 · 07/11/2026")
    khoi = css[i:]
    assert "#vtd-access .v3-topbar{background:#14538D" in khoi
    assert "--v3-navy:#14538D;--v3-accent:#14538D" in khoi
    assert "#1557b0" not in _doc("components", "cong", "KhachSanVtd.tsx")
    for p in (("app", "cong", "page.tsx"), ("app", "login", "page.tsx"), ("components", "cong", "KhungRieng.tsx")):
        assert "/cong/vtd.css?v=42" in _doc(*p), p   # KS-MUC3 nâng v=42 (trả màu báo lỗi)


def test_mot_bieu_tuong_va_mau_mo_app():
    icon = _doc("public", "favicon", "app-icon.svg")
    for mau in ('fill="#14538D"', 'fill="#FC4D7A"', 'fill="#3B8C43"', 'fill="#FFFFFF"'):
        assert mau in icon, f"favicon/app-icon.svg phải là app-icon-holdings bộ v2 (thiếu {mau})"
    mf = json.loads(_doc("public", "manifest.json"))
    assert mf["background_color"] == mf["theme_color"] == "#14538D"
    assert 'themeColor: "#14538D"' in _doc("app", "layout.tsx")
    try:
        from PIL import Image
    except ImportError:
        return
    for s in (16, 32, 48, 64, 192, 256, 512):
        im = Image.open(os.path.join(W, "public", "favicon", f"icon-{s}.png"))
        assert im.size == (s, s)
    # icon 180 (iOS tự bo góc) và maskable phải nền trắng tràn, không góc trong suốt
    for ten in ("icon-180.png", "icon-maskable-192.png", "icon-maskable-512.png"):
        assert Image.open(os.path.join(W, "public", "favicon", ten)).convert("RGBA").getpixel((0, 0)) == (255, 255, 255, 255)
