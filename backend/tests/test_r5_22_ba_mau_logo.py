# -*- coding: utf-8 -*-
"""R5-22 · Ba màu logo (Chủ tịch 14/11/2026, phương án A «điểm xuyết»): navy sáng chính, hồng cảnh báo,
xanh lá logo làm điểm nhấn ấn tượng — áp cho giao diện và mọi quy trình qua một chỗ (tokens.css)."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
doc = lambda p: (WEB / p).read_text(encoding="utf-8")  # noqa: E731


def _sang(bien: str) -> str:
    s = doc("app/tokens.css")
    khoi = s[s.index(':root[data-nen="sang"]'):]
    khoi = khoi[:khoi.index("}")]
    return khoi.split(bien + ":")[1].split(";")[0].strip()


def _tuong_phan(a: str, b: str = "#FFFFFF") -> float:
    def L(h):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    x, y = sorted([L(a), L(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)


def test_thanh_cong_la_sac_la_logo_va_doc_duoc():
    assert _sang("--vtos-success").upper() == "#2F7D3B"
    assert _tuong_phan("#2F7D3B") >= 4.5 and _tuong_phan("#2F7D3B", "#ECF7EE") >= 4.5
    assert "--vtos-la-to:          #5FAE66" in doc("app/tokens.css")


def test_vach_ba_mau_duoi_thanh_dau_ban():
    css = doc("app/globals.css")
    k = css[css.index("R5-22 · BA MÀU LOGO"):]
    assert ".mh01-ban::after" in k
    for t in ("--vtos-logo-la", "--vtos-logo-hong", "--vtos-logo-xanh"):
        assert t in k


def test_ban_kd_diem_xuyet_xanh_la_va_hong_thay_do():
    for f in ("components/BanKdKhung.tsx", "components/BanGdKdLe.tsx"):
        s = doc(f).lower()
        assert "inset 0 -3px 0 #5fae66" in s, f                       # vạch lá dưới tab đang mở
        for cu in ("#1c7a52", "#1c6f50", "#b3281f", "#fdeceb"):          # lục cũ / đỏ cũ
            assert cu not in s, (f, cu)
    s = doc("components/BanKdKhung.tsx")
    assert '(i < 3 && x.tien > 0 ? " v1" : "")' in s                    # hạng 1–3
    assert 'className={x.ty_le >= 1 ? "dat" : undefined}' in s           # thanh đạt chỉ tiêu
