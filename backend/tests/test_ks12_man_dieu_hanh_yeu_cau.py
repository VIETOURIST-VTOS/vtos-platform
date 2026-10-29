# -*- coding: utf-8 -*-
"""KS-12 · Năm phép thử cho màn Điều hành đọc yêu cầu của khách. KHÔNG cần cơ sở dữ liệu.

Phép 4 là phép đáng giá nhất, và nó bắt đúng cái hỏng của vòng trước: màn Điều hành CHỈ đọc
`tom_tat()`. KS-11 thêm bảy cột vào bảng nhưng không thêm vào `tom_tat`, nên đơn khách gửi lên
nằm trong danh sách mà người trực không thấy khách muốn đi đâu — không lỗi, không đỏ, chỉ trống.
Phép ấy đọc mọi ô `d.<tên>` mà màn dùng và đòi `tom_tat` phải có đúng ô ấy. Nó bắt được cả lần
sau, kể cả ô chưa ai thêm hôm nay.
"""
import os
import re
import types
from datetime import date, datetime

from app.services import don_khach_san_ota as D

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DV = os.path.join(GOC, "app", "services", "don_khach_san_ota.py")
MAN = os.path.join(os.path.dirname(GOC), "web", "app", "don-khach-san-ota", "page.tsx")

O_THE = re.compile(r"card_?number|so_the|cvv|cvc|card_holder|expiry", re.I)
O_KHACH = ("cong", "noi_den", "nguoi_nhan_phong", "lien_he", "yeu_cau_them", "gui_luc")


def _don(**kw):
    """Một đơn giả, đủ mọi ô `tom_tat` đọc. Không chạm cơ sở dữ liệu."""
    d = types.SimpleNamespace(
        id=7, the_tham_chieu="VTDTEST", trang_thai="moi", trang_thai_nguon="",
        ma_don_nguon=0, so_xac_nhan_ks="", tham_chieu_nguon="", moi_truong="that",
        ngay_nhan=date(2026, 12, 1), ngay_tra=date(2026, 12, 3), tien_te="VND",
        gia_gom_thue=0, kieu_thanh_toan="", dang_xu_ly=False,
        so_phong=2, nguoi_lon=3, tre_em=1,
        tai_khoan_ngoai_id=None, cong="", noi_den="", nguoi_nhan_phong="", lien_he="",
        yeu_cau_them="", gui_luc=None)
    for k, v in kw.items():
        setattr(d, k, v)
    return d


def _khoa_tom_tat():
    n = open(DV, encoding="utf-8").read()
    than = n[n.index("def tom_tat("):]
    het = re.search(r"\n(?=def |class )", than)
    return set(re.findall(r'"([a-z_]+)":', than[:het.start()] if het else than))


def test_ks12_1_don_cua_khach_mang_du_o_khach_khai():
    r = D.tom_tat(_don(tai_khoan_ngoai_id=9, cong="khach_hang", noi_den="Đà Nẵng",
                       nguoi_nhan_phong="Trần A", lien_he="a@b.c",
                       yeu_cau_them="tầng cao", gui_luc=datetime(2026, 10, 30, 1, 5)))
    assert r["la_yeu_cau_khach"] is True
    for k in O_KHACH:
        assert k in r, "thiếu ô " + k
    assert r["noi_den"] == "Đà Nẵng"
    assert r["gui_luc"].startswith("2026-10-30")
    assert (r["so_phong"], r["nguoi_lon"], r["tre_em"]) == (2, 3, 1)


def test_ks12_2_don_dieu_hanh_tu_dung_khong_co_chu():
    r = D.tom_tat(_don())
    assert r["la_yeu_cau_khach"] is False
    assert r["noi_den"] == "" and r["lien_he"] == "" and r["gui_luc"] is None


def test_ks12_3_tom_tat_khong_co_o_so_the():
    n = open(DV, encoding="utf-8").read()
    than = n[n.index("def tom_tat("):]
    assert O_THE.search(than) is None, "tom_tat KHÔNG được mang ô số thẻ"


def test_ks12_4_man_doc_o_nao_thi_tom_tat_phai_co_o_ay():
    """Hàng rào của vòng này. Màn Điều hành chỉ đọc tom_tat — đọc ô không có là ô trống."""
    khoa = _khoa_tom_tat()
    n = open(MAN, encoding="utf-8").read()
    dung = set(re.findall(r"\bd\.([a-z_]+)\b", n))
    thieu = sorted(dung - khoa)
    assert thieu == [], "màn đọc ô mà tom_tat không có: " + ", ".join(thieu)


def test_ks12_5_man_goi_dung_cua_va_khong_co_o_so_the():
    n = open(MAN, encoding="utf-8").read()
    assert "hoi-gia-yeu-cau" in n, "màn phải gọi cửa nhận yêu cầu của khách"
    assert "la_yeu_cau_khach" in n, "màn phải phân biệt đơn khách với đơn tự dựng"
    assert O_THE.search(n) is None, "màn đơn phòng KHÔNG được có ô số thẻ"
