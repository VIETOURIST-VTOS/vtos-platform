# -*- coding: utf-8 -*-
"""R5-29 · Đầu bảng navy trên nền trắng sáng cho toàn hệ thống (Chủ tịch 14/11/2026)."""
from pathlib import Path
import re

CSS = (Path(__file__).resolve().parents[2] / "web/app/globals.css").read_text(encoding="utf-8")


def test_luat_chung_cho_moi_bang_dung_sau_luat_goc():
    k = CSS[CSS.index("R5-29 · ĐẦU BẢNG NAVY"):]
    assert "th{background:var(--vtos-info-bg);color:var(--vtos-navy);text-transform:none" in k
    assert "border-bottom:2px solid var(--vtos-sky)}" in k and "th.num{font-family:inherit}" in k
    assert CSS.index("text-transform:uppercase;letter-spacing:.04em}") < CSS.index("R5-29 · ĐẦU BẢNG NAVY")
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", k), "màu phải dùng token"
