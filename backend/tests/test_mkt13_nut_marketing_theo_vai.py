# -*- coding: utf-8 -*-
"""MKT-13 — NÚT «MARKETING & PR» ĐƯA ĐÚNG VAI VỀ ĐÚNG BÀN, VÀ KHÔNG AI RƠI VÀO 403.

Cái bẫy của đợt này không nằm ở giao diện mà nằm ở quyền. Màn `/marketing` mở cho tám vai, còn
hai cửa bàn chỉ mở cho sáu và cho hai. Đưa một vai ngoài danh sách ấy sang bàn thì họ bấm nút
và rơi vào một màn 403 — mà màn hình không có cách nào nói cho họ biết vì sao. Hai vai `gd_kd`
và `ketoan` nằm đúng chỗ ấy.

BA CA ĐẦU ĐỌC CẢ HAI TỆP VÀ SO VỚI NHAU, không chép tay danh sách vai sang đây: chép tay thì
ngày ai đó thêm một vai, bảng chép vẫn đúng và phép thử vẫn xanh, còn người dùng thì gặp 403.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI; nó chạy ở lượt hai của vòng.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
SHELL = GOC / "web" / "components" / "Shell.tsx"
SRC = SHELL.read_text(encoding="utf-8")


def _mang(ten: str) -> list[str]:
    m = re.search(r"const " + ten + r"\s*=\s*\[(.*?)\];", SRC, re.S)
    assert m, "không đọc được bảng %s trong Shell.tsx" % ten
    ds = re.findall(r'"([a-z0-9_]+)"', m.group(1))
    assert ds, "bảng %s rỗng — một hàng rào quét trúng tập rỗng thì luôn xanh" % ten
    return ds


def test_vai_duoc_dua_sang_ban_deu_mo_duoc_cua_ban_ay():
    from app.api.v1 import ban_mkt as C
    for ten_mang, ten_cua, cua in (("VAI_BAN_PTGD", "XEM_PTGD", C.XEM_PTGD),
                                   ("VAI_BAN_NV", "XEM_NV", C.XEM_NV)):
        du = sorted(set(_mang(ten_mang)) - set(cua))
        assert not du, (
            "Nút «Marketing & PR» đưa các vai sau sang bàn mà chúng KHÔNG mở được cửa: " +
            ", ".join(du) + f". Bảng {ten_mang} phải nằm gọn trong {ten_cua} của "
            "api/v1/ban_mkt.py — rộng hơn một vai là vai ấy bấm nút rồi rơi vào 403.")


def test_hai_bang_vai_khong_chong_nhau_va_khong_vai_nao_ngoai_man_marketing():
    from app.services import access as AC
    ptgd, nv = set(_mang("VAI_BAN_PTGD")), set(_mang("VAI_BAN_NV"))

    chong = sorted(ptgd & nv)
    assert not chong, ("Vai nằm ở CẢ HAI bảng bàn: " + ", ".join(chong) +
                       ". Vai ấy đi đâu là do thứ tự dòng mã quyết, không phải do ai quyết.")

    la = sorted((ptgd | nv) - set(AC.MENU_ROLES["/marketing"]))
    assert not la, (
        "Bảng bàn có vai KHÔNG mở được màn /marketing: " + ", ".join(la) +
        ". Vai ấy không thấy nút «Marketing & PR», nên dòng khai nó không canh gì cả.")


def test_hai_vai_khong_co_ban_van_giu_dich_cu():
    """Bỏ nhánh này là `gd_kd` và `ketoan` bấm nút rồi rơi vào 403 ở mọi ô."""
    from app.services import access as AC
    con_lai = sorted(set(AC.MENU_ROLES["/marketing"]) - set(_mang("VAI_BAN_PTGD"))
                     - set(_mang("VAI_BAN_NV")))
    assert con_lai, (
        "Không vai nào còn ở nhánh đích cũ. Nếu đúng là mọi vai đều có bàn thì bỏ nhánh ấy cho "
        "sạch; còn nếu không, đó là một nhánh chết mà ai đọc mã cũng tưởng nó đang chạy.")
    m = re.search(r"export function dichCuaNhom\([^)]*\)[^{]*\{(.*?)\n\}", SRC, re.S)
    assert m, "không đọc được hàm dichCuaNhom"
    than = m.group(1)
    assert than.rstrip().endswith('return g.href || "";'), (
        "Hàm chọn đích không còn lối về đích cũ cho các vai không có bàn: " + ", ".join(con_lai) +
        ". Hai vai ấy mở được màn Marketing nhưng không đọc được bàn nào.")


def test_chi_doi_dich_chu_khong_doi_bang_menu():
    """Đợt này hứa KHÔNG đụng bảng `GROUPS`. Đây là chỗ đo lời hứa ấy.

    Hai mục con của nhóm Marketing phải còn nguyên: ai muốn mở thẳng một bàn vẫn mở được, và
    `test_menu` cùng bảng phân quyền không nhúc nhích.
    """
    for ten, duong in (("Bàn Phó TGĐ Marketing", "/ptgd-mkt"),
                       ("Bàn nhân viên Marketing", "/ban-mkt")):
        assert f'["{ten}", "{duong}"]' in SRC, (
            f"Mục menu «{ten}» đã bị đụng. Đợt này chỉ đổi ĐÍCH của một nút, không sửa bảng menu.")
    assert 'href: "/marketing", blocks:' in SRC, (
        "Đích khai sẵn của nhóm Marketing đã bị đổi. Nó phải giữ nguyên: đó là đích cho hai vai "
        "không có bàn, và là dòng mà bảng phân quyền đang dựa vào.")


def test_dich_chon_o_cho_dung_bang_chu_khong_o_cho_ve_nut():
    """Lần bấm đầu tiên của đợt này đỏ đúng ở đây, nên ca thử giữ lấy bài học.

    Bản đầu đổi thẳng dòng vẽ nút `<Link href={g.href!}` thành một lời gọi hàm, và
    `test_thanh_phan_he_chi_co_mot_hanh_vi_la_bam` chặn ngay: nó ghim đúng chuỗi ấy vì nó canh
    một việc thật — nhóm không xổ ra phải là một đường dẫn THẬT, để bấm giữa chuột mở được tab
    mới. Đổi chỗ vẽ là phá đúng cái hàng rào ấy đang giữ.

    Nên đích được chọn ở chỗ DỰNG BẢNG, còn chỗ vẽ không nhúc nhích một ký tự.
    """
    assert "href: dichCuaNhom(g," in SRC, (
        "Đích của nhóm không còn được chọn lúc dựng bảng `groups`. Nếu chuyển phép chọn sang "
        "chỗ vẽ thì hàng rào của thanh phân hệ sẽ đỏ, và bấm giữa chuột thôi mở tab mới.")
    assert "<Link href={g.href!}" in SRC, (
        "Chỗ vẽ nút nhóm đã bị đổi. Nó phải giữ nguyên `<Link href={g.href!}` — đó là thứ "
        "`test_thanh_phan_he_chi_co_mot_hanh_vi_la_bam` ghim, và là thứ giữ cho bấm giữa chuột "
        "mở được tab mới.")
