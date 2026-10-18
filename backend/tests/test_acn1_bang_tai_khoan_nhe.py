# -*- coding: utf-8 -*-
"""AC-NHE · Bảng tài khoản /access KHÔNG dựng sẵn ô chọn trên mọi dòng — 18/10/2026.

Đo trên hệ thật 18/10: mỗi dòng của bảng 121 tài khoản dựng sẵn hai ô chọn (29 vai trò + 10 pháp
nhân) — ≈ 4.700 lựa chọn lúc mở màn, trình duyệt ì đến mức công cụ chụp màn hình quá giờ. Chủ tịch
duyệt bản xem thử cùng ngày: vai trò và pháp nhân hiện CHỮ, bấm «đổi» trên dòng nào thì chỉ dòng ấy
có ô chọn; ghi vẫn qua đúng hai cửa cũ.

Phép thử đọc mã nguồn: hai ô chọn phải nằm SAU điều kiện `doiUid === r.id`.
"""
import re
from pathlib import Path

import pytest

TRANG = Path(__file__).resolve().parents[2] / "web" / "app" / "access" / "page.tsx"


def _ma(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _o_chon_deu_sau_dieu_kien(src: str) -> list[str]:
    hong = []
    for ten, mau in (("vai trò", r"<select value=\{r\.role\}"), ("pháp nhân", r"<select value=\{r\.company_id")):
        for m in re.finditer(mau, src):
            truoc = src[max(0, m.start() - 120):m.start()]
            if "doiUid === r.id" not in truoc:
                hong.append(ten)
    return hong


@pytest.mark.skipif(not TRANG.exists(), reason="không có mã giao diện cạnh mã máy chủ")
def test_acn1_o_chon_chi_dung_o_dong_dang_doi():
    src = _ma(TRANG.read_text(encoding="utf-8"))
    assert re.search(r"<select value=\{r\.role\}", src), "mất ô đổi vai trò"
    assert re.search(r"<select value=\{r\.company_id", src), "mất ô đổi pháp nhân"
    hong = _o_chon_deu_sau_dieu_kien(src)
    assert not hong, f"ô chọn {hong} lại dựng sẵn trên mọi dòng — bảng 121 dòng ì trở lại"
    assert "setDoiUid(r.id)" in src and "setDoiUid(null)" in src, "thiếu nút «đổi» / «Xong»"
    # Ghi vẫn qua đúng hai cửa cũ.
    assert "doiVaiTro(r, e.target.value)" in src and "/access/users/${r.id}/company" in src


@pytest.mark.skipif(not TRANG.exists(), reason="không có mã giao diện cạnh mã máy chủ")
def test_acn1_tu_pha():
    src = _ma(TRANG.read_text(encoding="utf-8"))
    cu = src.replace("canWrite && doiUid === r.id", "canWrite", 1)
    assert _o_chon_deu_sau_dieu_kien(cu), "bỏ điều kiện mà phép thử không đỏ"
