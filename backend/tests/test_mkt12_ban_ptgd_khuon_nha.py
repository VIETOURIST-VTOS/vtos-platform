# -*- coding: utf-8 -*-
"""MKT-12 — BÀN PHÓ TGĐ MARKETING ĐỨNG TRONG KHUÔN NHÀ.

Đợt MKT-11 dựng màn này viết riêng, và cái giá của "viết riêng" hiện ra ngay: trang khai 44 mã
màu cứng của chính nó. Hệ thống có HAI bộ giao diện, đổi bằng nút «Giao diện» trên thanh ngang;
một trang khai màu cứng thì nó không đổi theo, và người dùng bộ tối nhận một màn trắng giữa một
ứng dụng tối. Màn `/marketing` đã viết luật ấy từ lâu trong chú thích đầu tệp — «Màn hình này
KHÔNG khai màu riêng một dòng nào» — nhưng luật nằm trong chú thích thì chỉ đúng vào ngày người
viết còn nhớ. Đây là chỗ đo nó.

BỐN PHÉP THỬ ĐẦU ĐỌC CẢ HAI TỆP VÀ SO VỚI NHAU, không chép tay danh sách nào sang đây: chép tay
thì ngày ai đó đổi tên một lớp, bảng chép vẫn đúng và phép thử vẫn xanh, còn trang thật thì mất
kiểu.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI; nó chạy ở lượt hai của vòng.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "ptgd-mkt" / "page.tsx"
GLOBALS = GOC / "web" / "app" / "globals.css"

SRC = TRANG.read_text(encoding="utf-8")


def _khoi_style() -> str:
    """Phần CSS trang này tự khai, nằm trong chuỗi mẫu của thẻ `<style>`."""
    m = re.search(r"<style>\{`(.*?)`\}</style>", SRC, re.S)
    assert m, "không tìm thấy khối <style> của trang — đã đổi cách khai kiểu?"
    return m.group(1)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · KHÔNG KHAI MỘT MÃ MÀU NÀO
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_trang_khong_khai_mot_ma_mau_nao():
    """Chỉ soi CHỖ SINH RA CSS, không soi chú thích.

    Chú thích của trang có nhắc vài mã màu để kể lại lỗi cũ; soi cả chú thích thì phép thử này
    bắt nhầm một câu văn, và một phép thử bắt nhầm sẽ bị người ta tắt đi.
    """
    cho = {"khối <style>": _khoi_style()}
    for i, x in enumerate(re.findall(r"style=\{\{([^}]*)\}\}", SRC)):
        cho["style nội tuyến #%d" % (i + 1)] = x

    hong = []
    for ten, x in cho.items():
        for mau in re.findall(r"#[0-9a-fA-F]{3,8}\b", x):
            hong.append("%s: %s" % (ten, mau))
    assert not hong, (
        "Trang khai mã màu cứng: " + "; ".join(hong) +
        ". Màu phải lấy từ biến của tokens.css — hệ thống có hai bộ giao diện và biến là thứ "
        "duy nhất đổi theo. Màu cứng thì bộ tối nhận một màn sáng.")


def test_moi_bien_mau_dung_deu_co_that_trong_tokens():
    """Một biến gõ sai không nổ: CSS bỏ qua dòng ấy và phần tử rơi về màu mặc định, im lặng."""
    tok = (GOC / "web" / "app" / "tokens.css").read_text(encoding="utf-8")
    khai = set(re.findall(r"(--vtos-[a-z0-9-]+)\s*:", tok))
    assert len(khai) >= 20, "đọc được quá ít biến trong tokens.css — nghi cách đọc đã hỏng"
    dung = set(re.findall(r"var\((--vtos-[a-z0-9-]+)", _khoi_style()))
    assert dung, "trang không dùng biến nào — xem lại, vì nó vẫn phải có màu"
    lac = sorted(dung - khai)
    assert not lac, (
        "Trang dùng biến KHÔNG CÓ trong tokens.css: " + ", ".join(lac) +
        ". Biến gõ sai không nổ, nó chỉ im lặng rơi về màu mặc định.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · DÙNG ĐÚNG LỚP CHUNG, VÀ LỚP CHUNG ẤY PHẢI CÒN ĐÓ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _lop_chung_trang_dung() -> set[str]:
    """Các lớp CHUNG trang này mượn của nhà: tiền tố `mh01-` và `the-`. Lớp riêng (`pt-`) không tính."""
    ra: set[str] = set()
    for chuoi in re.findall(r'"([^"\n]*)"', SRC):
        for t in chuoi.split():
            if t.startswith("mh01-") or t.startswith("the-"):
                ra.add(t)
    return ra


def test_thanh_dau_ban_dung_khuon_chung_cua_vh30():
    lop = _lop_chung_trang_dung()
    thieu = sorted({"mh01-ban", "mh01-ban-ten", "mh01-ban-cum", "mh01-ban-ngay"} - lop)
    assert not thieu, (
        "Thanh đầu bàn không dùng khuôn chung, thiếu: " + ", ".join(thieu) +
        ". Bàn Chủ tịch và bàn Đội xe đội thanh này từ đợt VH-30; bàn Marketing vẽ riêng thì ba "
        "bàn của cùng một hệ thống trông như ba sản phẩm.")


def test_moi_lop_chung_deu_co_that_trong_globals():
    css = GLOBALS.read_text(encoding="utf-8")
    lop = _lop_chung_trang_dung()
    assert len(lop) >= 6, "đọc được quá ít lớp chung — nghi cách đọc đã hỏng, và một phép thử quét trúng tập rỗng thì luôn xanh"
    lac = sorted(t for t in lop if not re.search(r"\." + re.escape(t) + r"\b", css))
    assert not lac, (
        "Trang dùng lớp KHÔNG CÓ trong globals.css: " + ", ".join(lac) +
        ". Hoặc lớp đã bị đổi tên và phải sửa theo, hoặc trang gõ nhầm — cả hai đều ra một màn "
        "mất kiểu mà không ai được báo.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · BA LUẬT NÓI THẬT, VÀ THỨ TỰ ĐỌC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_ba_trang_thai_con_nguyen_va_khong_cai_nao_ve_so_khong():
    for can in ('trang_thai === "loi"', 'trang_thai === "chua_co"', "o.chu"):
        assert can in SRC, (
            "Mất nhánh %r. Một ô đọc hỏng mà hiện 0 là nói với người ngồi bàn rằng hôm nay "
            "không có gì phải làm." % can)
    assert "chưa đọc được" in SRC, "mất câu chữ của ô đọc hỏng"


def test_so_nen_dung_cuoi_chu_khong_dung_dau():
    """Luật (c) của đợt MKT-1: ô mẫu số đứng CUỐI và mang màu khác.

    Đợt MKT-11 đặt khối ấy lên ĐẦU, trên cả việc cần xử lý — đọc ra như thể bốn con số nền là
    thứ phải làm trước. Phép thử này giữ thứ tự đã sửa.
    """
    i_viec = SRC.find("Việc cần xử lý")
    i_doi = SRC.find("Hàng đợi theo dõi")
    i_nen = SRC.find("Số nền của kỳ")
    assert i_viec > 0 and i_doi > 0 and i_nen > 0, "mất một trong ba nhãn khối"
    assert i_viec < i_doi < i_nen, (
        "Thứ tự khối sai: việc cần xử lý phải đứng trước hàng đợi, và số nền đứng CUỐI. "
        "Đang là: việc=%d, hàng đợi=%d, số nền=%d" % (i_viec, i_doi, i_nen))
    assert "pt-nen" in SRC, "khối số nền không mang nền khác — mất nửa sau của luật (c)"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · HAI CÁI BẪY ĐÃ VẤP RỒI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_khong_co_dau_nhay_nguoc_trong_khoi_style():
    """Đợt MKT-6 và MKT-7 cùng vỡ vì một dấu nháy ngược lọt vào trong chuỗi mẫu."""
    assert "`" not in _khoi_style(), (
        "Có dấu nháy ngược bên trong khối <style>. Nó cắt đôi chuỗi mẫu và trang nổ lúc dựng — "
        "đã vấp hai lần, đợt MKT-6 và MKT-7.")


def test_moi_loi_chi_xuat_hien_mot_cho_tren_man():
    """Luật giao diện VTOS 10/11/2026: các nút chức năng không được lặp trên cùng một màn hình."""
    m = re.search(r"const NHOM[^=]*=\s*\[(.*?)\n\];", SRC, re.S)
    assert m, "không đọc được bảng NHOM"
    ten = re.findall(r'"([^"\n]+)"', m.group(1))
    muc = [t for t in ten if t not in [x[0] for x in re.findall(r'\["([^"]+)",\s*\[', m.group(1))]]
    lap = sorted({t for t in muc if muc.count(t) > 1})
    assert not lap, (
        "Lối xuất hiện nhiều hơn một chỗ trên bàn: " + ", ".join(lap) +
        ". Mỗi nút một chỗ — luật giao diện VTOS 10/11/2026.")

    m2 = re.search(r"const AN[^=]*=\s*\[(.*?)\];", SRC, re.S)
    assert m2, "không đọc được bảng AN"
    an = re.findall(r'"([^"\n]+)"', m2.group(1))
    trung = sorted(set(an) & set(muc))
    assert not trung, (
        "Lối vừa bị ẩn vừa được xếp nhóm: " + ", ".join(trung) +
        ". Hai bảng nói ngược nhau thì bảng nào thắng là chuyện của thứ tự dòng mã, không phải "
        "của một quyết định.")
