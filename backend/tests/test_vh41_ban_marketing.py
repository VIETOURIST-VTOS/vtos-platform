"""VH-41 · Bàn làm việc Marketing & PR như bàn /xe (Chủ tịch duyệt bản xem trước 12/11/2026 22:17)."""
import os
import re

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_1_bay_nhom_dung_ten_dung_thu_tu_khung_hoang_do():
    s = _w("app", "marketing", "page.tsx")
    khoi = s[s.index("const NHOM_MKT"):s.index("const DUONG_MKT")]
    ten = re.findall(r'\{ ma: "\w+", ten: "([^"]+)"', khoi)
    assert ten == ["Trang chủ", "Khách tiềm năng & Sales", "Chiến dịch & ngân sách", "Nội dung & thương hiệu",
                   "Khủng hoảng & PR", "Doanh thu & đối soát", "Chăm sóc & khiếu nại"]
    assert '{ ma: "kh", ten: "Khủng hoảng & PR", khan: true' in khoi


def test_2_moi_tab_cu_deu_con_mot_cho_trong_nhom():
    s = _w("app", "marketing", "page.tsx")
    khoi = s[s.index("const NHOM_MKT"):s.index("const DUONG_MKT")]
    for t in ("tongquan", "khach", "chuyendoi", "chiendich", "doisoat", "noidung", "thuonghieu"):
        assert f'tab: "{t}"' in khoi, t
    for d in ("/noi-dung", "/bao-chi-kol", "/dong-gop-marketing", "/doi-soat-marketing", "/chuyen-doi-lead",
              "/cham-soc", "/khieu-nai"):
        assert f'toi: "{d}"' in khoi, d


def test_3_khong_lap_nut_bo_hang_lien_ket_va_hang_8_nut_cu():
    s = _w("app", "marketing", "page.tsx")
    ve = s[s.index("function Marketing()"):]
    assert 'className="mkt-man"' not in ve and 'className="mkt-chuc"' not in ve
    assert '["ngansach", "Kế hoạch & ngân sách"]].map' not in ve   # hai nút trong tab chiến dịch đã là trang con


def test_4_trang_chu_theo_vai_va_nut_crm_tong_tro_marketing():
    s = _w("app", "marketing", "page.tsx")
    assert 'VAI_BAN_NV.includes(vai) ? "/ban-mkt" : VAI_BAN_PTGD.includes(vai) ? "/ptgd-mkt" : ""' in s
    sh = _w("components", "Shell.tsx")
    assert 'if (g.key === "marketing") return "/marketing";' in sh
    assert 'startsWith("/marketing") ? "/marketing" : path?.startsWith("/fit") ? "/fit" : "/xe"' in sh


def test_5_khung_nhung_chan_lien_ket_ra_crm_tong():
    k = _w("components", "KhungNhung.tsx")
    assert ".top,aside.side{display:none!important}" in k
    assert "if (ngoai && ngoai(h)) return;" in k and "if (cuaBan(h)) f.contentWindow?.location.assign(h);" in k
