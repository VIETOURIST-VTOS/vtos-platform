"""R5-3 · Chủ tịch chốt 13/11/2026: GĐ, TP, trưởng nhóm, NV Kinh doanh lẻ đăng nhập là vào /fit.

Đăng nhập luôn về "/" (app/login), nên chốt nằm ở trang chủ: bốn vai ấy được chuyển sang /fit
trước khi trang chủ gọi /dashboard. Danh sách vai phải bằng đúng SALES — ai mở được /fit.
"""
import pathlib
import re

from app.services import access as AC

TRANG = (pathlib.Path(__file__).resolve().parents[2] / "web/app/page.tsx").read_text(encoding="utf-8")


def test_bon_vai_kd_le_vao_fit():
    m = re.search(r"const VAI_VAO_FIT = \[([^\]]*)\]", TRANG)
    assert m, "trang chủ mất VAI_VAO_FIT"
    assert set(re.findall(r'"([a-z_]+)"', m.group(1))) == set(AC.SALES)
    assert 'router.replace("/fit")' in TRANG
    # Chuyển TRƯỚC khi gọi /dashboard — không tải bảng điều hành chung cho bốn vai này.
    i = TRANG.index('router.replace("/fit")')
    assert TRANG.index("tai();", i) > i


def test_vai_vao_fit_deu_mo_duoc_fit():
    for vai in AC.SALES:
        assert vai in AC.MENU_ROLES["/fit"]


def test_trang_chi_export_default():
    """Bài học VH-41: page.tsx export thêm thì `next build` đỏ."""
    assert re.findall(r"^export ", TRANG, re.M) == ["export "]
