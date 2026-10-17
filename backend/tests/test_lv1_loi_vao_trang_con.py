# -*- coding: utf-8 -*-
"""LV-1 · MỖI TRANG CON PHẢI CÓ LỐI VÀO TỪ MÀN CHA — 18/10/2026.

Chuyện đo được trên hệ thật: vòng DX-5 lên main, CI xanh, bốn màn /doi-xe/phat-tai-xe(/moi),
/doi-xe/gia-dau(/moi) mở được bằng địa chỉ — nhưng màn /doi-xe KHÔNG có nút nào dẫn sang. Trang con
cố ý không có mục menu (khuôn TM-1), nên lối vào duy nhất là một nút trên màn cha; thiếu nút ấy thì
về mặt người dùng, cửa nhập vẫn không tồn tại. `test_man_hinh_co_cua_nhap` không thấy được chuyện này
vì nó chỉ đọc các mục CÓ trong menu.

Luật: mọi đường trong các bộ `MAN_CON_*` của access.py phải được gọi đúng tên (chuỗi "/duong/dan")
trong mã của MỘT trang ở đúng một cấp trên nó. Cả các trang con của /lenh-dieu-xe cũng phải giữ luật này.
"""
import re
from pathlib import Path

import pytest

from app.services import access as AC

WEB = Path(__file__).resolve().parents[2] / "web" / "app"


def _ma(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"\{\s*/\*.*?\*/\s*\}", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _trang_con() -> list[str]:
    return sorted({p for ten in dir(AC) if ten.startswith("MAN_CON_")
                   for p in getattr(AC, ten) if isinstance(p, str)})


def _thieu_loi_vao(doc=None) -> list[str]:
    doc = doc or (lambda d: _ma((WEB / d.strip("/") / "page.tsx").read_text(encoding="utf-8")))
    thieu = []
    for p in _trang_con():
        cha = p.rsplit("/", 1)[0]
        if not (WEB / cha.strip("/") / "page.tsx").exists():
            thieu.append(f"{p} (không có màn cha {cha})")
            continue
        # `"/a/b"` hoặc `"/a/b?ky=" + …` — trang con nhận tham số trên đường dẫn vẫn là một lối vào.
        if f'"{p}"' not in doc(cha) and f'"{p}?' not in doc(cha):
            thieu.append(p)
    return thieu


@pytest.mark.skipif(not WEB.is_dir(), reason="không có mã giao diện cạnh mã máy chủ")
def test_lv1_moi_trang_con_co_loi_vao_tu_man_cha():
    ds = _trang_con()
    assert "/doi-xe/phat-tai-xe" in ds and "/lenh-dieu-xe/lap-lenh" in ds, "không đọc được các bộ MAN_CON_*"
    thieu = _thieu_loi_vao()
    assert not thieu, ("trang con không có nút nào dẫn tới từ màn cha — không có mục menu, nên không "
                       f"ai tới được trừ khi gõ địa chỉ: {thieu}")


@pytest.mark.skipif(not WEB.is_dir(), reason="không có mã giao diện cạnh mã máy chủ")
def test_lv1_tu_pha():
    """Bỏ hàng nút «Sổ con» khỏi /doi-xe — đúng tình trạng hệ thật ngày 18/10 — thì phải đỏ."""
    goc = _ma((WEB / "doi-xe" / "page.tsx").read_text(encoding="utf-8"))
    cu = re.sub(r'href="/doi-xe/(phat-tai-xe|gia-dau)"', 'href="#"', goc)
    assert cu != goc
    thieu = _thieu_loi_vao(lambda d: cu if d == "/doi-xe" else
                           _ma((WEB / d.strip("/") / "page.tsx").read_text(encoding="utf-8")))
    assert "/doi-xe/phat-tai-xe" in thieu and "/doi-xe/gia-dau" in thieu
