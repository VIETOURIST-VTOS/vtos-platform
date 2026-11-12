# -*- coding: utf-8 -*-
"""MKT-14 — HAI CHỖ ĐO ĐƯỢC BẰNG MẮT TRÊN TRANG THẬT, SAU KHI ĐỢT MKT-12 ĐÃ GỘP.

Cả hai đều là lỗi của chính đợt MKT-12, và cả hai đều KHÔNG có phép thử nào bắt được — nên
chúng sống qua một lần gộp và chỉ lộ ra khi có người mở trang ra nhìn. Đây là chỗ đóng cả hai
lại.

  · Đơn vị ("lead", "bản thảo") hiện bằng PHÔNG MÁY, vì luật `.pt-dv` để `font-family:inherit`
    mà nơi thừa kế là `.the-so` — chỗ cố ý dùng phông máy cho con số.
  · Chữ giải thích vẫn dài nguyên, vì MKT-12 dựng sẵn khung thu gọn mà không truyền nội dung
    vào ô nào.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI; nó chạy ở lượt hai của vòng.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "ptgd-mkt" / "page.tsx"
SRC = TRANG.read_text(encoding="utf-8")


def _khoi_style() -> str:
    m = re.search(r"<style>\{`(.*?)`\}</style>", SRC, re.S)
    assert m, "không tìm thấy khối <style> của trang"
    return m.group(1)


def test_khong_luat_nao_de_font_family_inherit():
    """`inherit` trong khối này luôn thừa kế từ `.the-so`, và `.the-so` dùng phông máy.

    Không cấm `inherit` ở mọi nơi — cấm đúng chỗ nó đã sai một lần, là các luật của trang này.
    """
    xau = [d.strip() for d in _khoi_style().splitlines() if "font-family:inherit" in d]
    assert not xau, (
        "Còn luật để font-family:inherit: " + "; ".join(xau) +
        ". Ở khối này `inherit` thừa kế từ `.the-so`, chỗ cố ý dùng phông máy cho con số — nên "
        "chữ thường nằm cạnh con số sẽ hiện ra bằng phông máy.")


def test_chu_giai_thich_co_duong_thu_gon_va_duong_doc_ca_cau():
    css = _khoi_style()
    assert "line-clamp" in css, (
        "Mất luật cắt chữ giải thích còn một dòng. Đợt MKT-12 dựng sẵn khung thu gọn mà không "
        "truyền nội dung vào ô nào, nên mọi thẻ in nguyên câu dài — đo được bằng mắt 12/11/2026.")
    assert "pt-gon" in SRC, "lớp cắt chữ không được gắn vào thẻ nào"
    assert "<details" in SRC and "pt-vs" in SRC, (
        "Mất cửa đọc cả câu. Cắt chữ mà không có cửa mở ra là GIẤU chữ, không phải thu gọn.")


def test_cat_bang_css_chu_khong_cat_chuoi_trong_ma():
    """Cắt chuỗi trong mã thì có ngay một câu bị chém đôi giữa chừng, và không ai thấy."""
    for xau in (".slice(0,", ".substring(", ".substr("):
        assert xau not in SRC, (
            f"Trang cắt chuỗi bằng {xau}. Chữ giải thích phải cắt bằng CSS: cắt chuỗi thì một "
            "câu có thể bị chém đôi giữa chừng, và màn hình không có cách nào báo điều đó.")
