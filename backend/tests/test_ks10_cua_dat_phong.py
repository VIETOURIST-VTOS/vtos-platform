# -*- coding: utf-8 -*-
"""KS-10 · Cửa máy chủ cho đơn khách sạn — bảy phép, không phép nào đụng cơ sở dữ liệu.

Sáu phép đầu soi các hàm thuần của lớp cửa. Phép cuối soi NGUỒN của chính cửa máy chủ: không
cửa nào để trống vai, không chỗ nào gọi mạng, không ô nào nhận số thẻ.
"""
import re
from datetime import date, datetime
from pathlib import Path

from app.models.don_khach_san_ota import KIEU_THANH_TOAN
from app.services import dat_phong_ota as C
from app.services import khach_san_ota as S

GOC_APP = Path(S.__file__).resolve().parents[1]
BAY_GIO = datetime(2026, 10, 29, 9, 30, 0)


class _Ota:
    def __init__(self, quyen="AFFILIATE,SEARCH,BOOK,CANCEL", moi_truong="that"):
        self.id, self.ma = 3, "agoda"
        self.quyen, self.moi_truong = quyen, moi_truong


class _Don:
    def __init__(self, **kw):
        self.id = 1
        self.ma_tim, self.ma_khoi, self.the_chao = 0, "", ""
        self.ma_khach_san, self.ma_phong, self.ma_goi_gia = 0, 0, 0
        self.kieu_thanh_toan, self.phu_thu = "", ""
        self.gia_gom_thue, self.tim_luc, self.trang_thai = 0, None, "moi"
        for k, v in kw.items():
            setattr(self, k, v)


def _du(**kw):
    d = {"ota_id": 3, "ngay_nhan": date(2026, 12, 20), "ngay_tra": date(2026, 12, 22),
         "so_phong": 1, "nguoi_lon": 2, "tre_em": 0}
    d.update(kw)
    return d


def test_ks10_1_chua_du_dieu_kien_thi_khong_dung_duoc_don():
    assert C.thieu_de_hoi_gia(_Ota(), _du()) == []

    assert "chưa ghi nhận nguồn cấp quyền SEARCH" in C.thieu_de_hoi_gia(
        _Ota(quyen="AFFILIATE"), _du())
    assert any("môi trường đang Tắt" in x for x in
               C.thieu_de_hoi_gia(_Ota(moi_truong="tat"), _du()))
    assert any("ngày nhận" in x for x in C.thieu_de_hoi_gia(_Ota(), _du(ngay_nhan=None)))
    # Trả trước ngày nhận là một đơn không tồn tại, nhưng Agoda chỉ báo lỗi lúc gọi Book.
    assert any("sau ngày nhận" in x for x in
               C.thieu_de_hoi_gia(_Ota(), _du(ngay_tra=date(2026, 12, 19))))
    assert any("số phòng" in x for x in C.thieu_de_hoi_gia(_Ota(), _du(so_phong=0)))
    assert any("người lớn" in x for x in C.thieu_de_hoi_gia(_Ota(), _du(nguoi_lon=0)))


def test_ks10_2_chay_that_thi_may_khong_duoc_bia_mot_con_so_nao():
    """Sáu con số của nguồn phải do Điều hành dán sang, và thiếu cái nào phải gọi đúng tên nó."""
    thieu = C.thieu_so_nguon("that", {})
    assert len(thieu) == len(C.SO_CUA_NGUON)
    for k in C.SO_CUA_NGUON:
        assert any(C.TEN_O[k] in x for x in thieu), k

    du = {"ma_tim": 633141408144250000, "ma_khoi": "aBc_123", "ma_khach_san": 7001,
          "ma_phong": 9001, "ma_goi_gia": 11001, "gia_gom_thue": 2400000}
    assert C.thieu_so_nguon("that", du) == []
    # Giá 0 không phải là «đã dán»: đơn giá 0 lọt xuống báo cáo tiền là một lỗ thủng.
    assert any(C.TEN_O["gia_gom_thue"] in x
               for x in C.thieu_so_nguon("that", {**du, "gia_gom_thue": 0}))

    # Môi trường Thử thì không đòi dán gì — máy sinh.
    assert C.thieu_so_nguon("thu", {}) == []
    assert C.thieu_so_nguon("tat", {}) == []


def test_ks10_3_ma_gia_cua_moi_truong_thu_phai_la_so_64_bit():
    """Sinh số nhỏ thì phép thử không bao giờ chạm chỗ tràn số, và chỗ ấy nổ vào ngày chạy thật."""
    a, b = C.sinh_so_thu(), C.sinh_so_thu()
    for k in ("ma_tim", "ma_khach_san", "ma_phong", "ma_goi_gia", "gia_gom_thue"):
        assert k in a and int(a[k]) > 0, k
    assert a["ma_tim"] > 2 ** 32, "mã tìm phải vượt 32 bit như mẫu trong tài liệu Agoda"
    assert a["ma_tim"] != b["ma_tim"]
    assert a["kieu_thanh_toan"] in KIEU_THANH_TOAN
    assert C.thieu_so_nguon("that", a) == [], "mã sinh ra phải đủ như mã dán tay"


def test_ks10_4_the_tham_chieu_khong_duoc_trung():
    """Thẻ trùng nghĩa là tra Booking List ra hai đơn — và không ai biết đơn nào đã bị tính tiền."""
    ds = [C.the_tham_chieu_moi() for _ in range(3000)]
    assert len(set(ds)) == 3000
    for t in ds[:50]:
        assert len(t) <= 50 and re.fullmatch(r"[A-Z0-9]+", t), t


def test_ks10_5_chep_so_nguon_vao_don():
    don = _Don()
    C.nhan_so_nguon(don, {"ma_tim": 633141408144250000, "ma_khoi": "aBc_123-xyz=",
                          "ma_khach_san": 7001, "ma_phong": 9001, "ma_goi_gia": 11001,
                          "gia_gom_thue": 2400000, "kieu_thanh_toan": "merchant"}, BAY_GIO)
    assert don.ma_tim == 633141408144250000 and don.ma_khoi == "aBc_123-xyz="
    assert don.gia_gom_thue == 2400000 and don.tim_luc == BAY_GIO
    assert don.trang_thai == "da_hoi_gia"

    # Kiểu thanh toán lạ thì bỏ trống, không chép bừa chữ của người gõ vào cột của Agoda.
    don2 = _Don()
    C.nhan_so_nguon(don2, {"kieu_thanh_toan": "tra-sau-cho-vui"}, BAY_GIO)
    assert don2.kieu_thanh_toan == ""


def test_ks10_6_bang_tham_so_du_cho_man_hinh():
    """Màn hình không được gõ lại bảng mã của Agoda lần nữa — gõ lại là sai chính tả lần nữa."""
    t = C.tham_so()
    assert len(t["trang_thai_nguon"]) == 10
    assert set(t["buoc"]) == {"tim", "soat_truoc", "dat", "tra_don", "xem_huy", "huy"}
    assert 0 in t["ly_do_huy"] and 44 in t["ly_do_huy"]
    assert t["han_ma_tim_giay"] == 3600 and t["han_dat_giay"] == 120
    assert set(t["so_cua_nguon"]) == set(C.SO_CUA_NGUON)


def test_ks10_7_soi_nguon_cua_may_chu():
    """Ba điều soi thẳng vào mã, vì ba điều này hỏng là hỏng lặng lẽ."""
    cua = (GOC_APP / "api" / "v1" / "don_khach_san_ota.py").read_text(encoding="utf-8")
    dv = (GOC_APP / "services" / "dat_phong_ota.py").read_text(encoding="utf-8")

    # 1. Không cửa nào để trống vai.
    duong = re.findall(r"@router_vtos\.(get|post)\(([^)]*)\)\ndef (\w+)\(([^)]*)\)",
                       cua, re.S)
    assert len(duong) >= 8, "thiếu cửa so với sáu bước"
    for _pp, _dd, ten, tham in duong:
        assert "require_roles" in tham, "cửa «%s» không đòi vai" % ten

    # 2. Không chỗ nào gọi mạng. Chưa có đường nối Agoda; có dòng gọi mạng ở đây nghĩa là ai đó
    #    đã nối lén mà không qua cửa nhập.
    for ten, noi_dung in (("cửa", cua), ("dịch vụ", dv)):
        assert not re.search(r"\b(httpx|aiohttp|urllib\.request|socket)\b", noi_dung), ten
        assert not re.search(r"\brequests\.(get|post|put|delete)\b", noi_dung), ten

    # 3. Không ô nào nhận số thẻ. Fulfill Assisted: «Agoda will directly charge your customers».
    for ten, noi_dung in (("cửa", cua), ("dịch vụ", dv)):
        assert not re.search(r"(?i)\b(card_?number|so_the|cvv|cvc|card_holder|expiry)\b",
                             noi_dung), ten
