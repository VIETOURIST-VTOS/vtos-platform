# -*- coding: utf-8 -*-
"""Chi phí nằm NGANG thành cột cạnh bảng khách — phương ngữ của tour EU / UK / SIN-MAL.

VÌ SAO CÓ TỆP NÀY

Đo 19/9/2026 trên hệ thật: 30 chuyến kho cũ mang 26.716.442.308 đ doanh thu mà giá vốn BẰNG 0,
trong đó 11 chuyến ngoại tệ chiếm 23.087.962.308 đ. Mở tệp ra thì chi phí có đủ — nó chỉ không
nằm thành bảng dọc như bộ đọc cũ biết tìm, mà nằm thành CỘT bên phải bảng khách.

PHÉP THỬ QUAN TRỌNG NHẤT là `test_dong_tong_khong_ten_khong_duoc_cong`. Dòng tổng của bảng khách
tệp EU không mang một chữ nào — cột số thứ tự trống, cột tên trống, chỉ có tiền. Cộng nó vào là ra
ĐÚNG GẤP ĐÔI, và vì kết quả vẫn là một con số nên không chỗ nào đỏ lên. Đó đúng là hình dạng của
lỗi 3,09 tỷ giá vốn ảo vừa phải gỡ khỏi báo cáo cùng ngày.
"""
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import openpyxl                                                    # noqa: E402
import pytest                                                      # noqa: E402
from app.services import nap_kho_cu as NK                          # noqa: E402

KHOAN = ["VMB", "LAND", "BH", "QUÀ TẶNG"]


def _dung(khach, tong_ghi=None, dong_tong_khong_ten=None, hai_tang=True,
          them_dong_tong_thu_hai=False):
    """Dựng một tệp hình dạng EU: THU | TỔNG THU | CHI | <các khoản>.

    `khach`      : [(tên, giá bán, [chi theo từng khoản])]
    `dong_tong_khong_ten`: danh sách tiền đặt vào một dòng KHÔNG có tên khách (cái bẫy).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "QT"
    ws["A1"] = "Mã tour:"; ws["B1"] = "TEST001"
    ws["A2"] = "Ngày đi:"; ws["B2"] = "01/02/2026"
    # hàng 4 = tầng trên, hàng 5 = tên cột
    ws.cell(4, 1, "NO"); ws.cell(4, 2, "TÊN KHÁCH HÀNG"); ws.cell(4, 3, "THU")
    ws.cell(4, 4, "TỔNG THU"); ws.cell(4, 5, "TỔNG CHI"); ws.cell(4, 6, "CHI")
    ws.cell(5, 3, "GIÁ BÁN")
    for i, k in enumerate(KHOAN):
        ws.cell(5, 6 + i, k)
    if not hai_tang:
        # Biến thể UK: `CHI` ở hàng TRÊN hàng tên khách, tên khoản NẰM CÙNG hàng tên khách.
        #
        # `ws.cell(4, 2, None)` KHÔNG xoá ô — openpyxl bỏ qua giá trị None khi gọi kiểu ấy, ô vẫn
        # giữ chữ cũ. Bản đầu của tệp thử này viết như thế, nên hàng tiêu đề tìm được vẫn là hàng
        # 4 và hình dạng UK không bao giờ được dựng ra: phép thử xanh, mà đem bản hỏng chạy trên
        # tệp UK thật thì mất trắng 1,59 tỷ giá vốn. Phải gán .value.
        ws.cell(4, 2).value = None
        ws.cell(5, 2, "TÊN KHÁCH HÀNG"); ws.cell(5, 3, "GIÁ BÁN")

    r = 6
    for ten, gb, chi in khach:
        ws.cell(r, 1, r - 5); ws.cell(r, 2, ten); ws.cell(r, 3, gb)
        ws.cell(r, 4, gb)
        ws.cell(r, 5, sum(x for x in chi if x) or None)
        for i, v in enumerate(chi):
            ws.cell(r, 6 + i, v)
        r += 1
    if dong_tong_khong_ten is not None:
        ws.cell(r, 3, sum(k[1] for k in khach))
        ws.cell(r, 4, sum(k[1] for k in khach))
        ws.cell(r, 5, tong_ghi if tong_ghi is not None else sum(dong_tong_khong_ten))
        for i, v in enumerate(dong_tong_khong_ten):
            ws.cell(r, 6 + i, v)
        r += 1
    if them_dong_tong_thu_hai:
        ws.cell(r, 5, 1)
        for i, v in enumerate(dong_tong_khong_ten or []):
            ws.cell(r, 6 + i, v)
        r += 1
    b = BytesIO(); wb.save(b)
    return b.getvalue()


def _chi(d):
    return {x["noi_dung"]: x["thanh_tien"] for x in d["chi"]}


# ----------------------------------------------------------------- đọc được cái trước đây mất trắng

def test_doc_duoc_chi_phi_nam_ngang():
    t = _dung([("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000]),
               ("TRAN THI B", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])])
    d = NK.doc_tep(t, "eu.xlsx")
    assert _chi(d) == {"VMB": 20_000_000, "LAND": 40_000_000, "BH": 200_000, "QUÀ TẶNG": 100_000}
    assert d["chi_theo_cot"]["kieu"] == "theo_khach"
    assert d["tong_chi_cong_dong"] == 60_300_000


def test_du_cac_khoan_chu_tich_chot_17_9():
    """Luật 2 (17/9/2026): phải có đủ land tour, vé máy bay, bảo hiểm, quà tặng — không gộp một cục."""
    t = _dung([("NGUYEN VAN A", 50_000_000, [1, 2, 3, 4])])
    assert set(_chi(NK.doc_tep(t, "eu.xlsx"))) == set(KHOAN)


def test_bien_the_uk_nhan_chi_o_hang_tren():
    t = _dung([("NGUYEN VAN A", 50_000_000, [7, 8, 9, 10])], hai_tang=False)
    assert _chi(NK.doc_tep(t, "uk.xlsx")) == {"VMB": 7, "LAND": 8, "BH": 9, "QUÀ TẶNG": 10}


# ----------------------------------------------------------------- CÁI BẪY: dòng tổng không tên

def test_dong_tong_khong_ten_khong_duoc_cong():
    """Phép thử chính. Dòng tổng của tệp EU không mang chữ nào — cộng vào là ra gấp đôi."""
    k = [("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000]),
         ("TRAN THI B", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])]
    t = _dung(k, dong_tong_khong_ten=[20_000_000, 40_000_000, 200_000, 100_000])
    d = NK.doc_tep(t, "eu.xlsx")
    assert _chi(d) == {"VMB": 20_000_000, "LAND": 40_000_000, "BH": 200_000, "QUÀ TẶNG": 100_000}
    assert d["tong_chi_cong_dong"] == 60_300_000, "đã cộng cả dòng tổng — giá vốn gấp đôi"


# ----------------------------------------------------------------- SIN-MAL: cả chuyến một dòng tổng

def test_khong_khach_nao_mang_chi_thi_lay_dong_tong():
    """Tệp SIN-MAL gói cả chuyến vào một dòng tổng nằm ngang. Phải đọc được, nếu không mất trắng."""
    k = [("NGUYEN VAN A", 50_000_000, [None, None, None, None]),
         ("TRAN THI B", 50_000_000, [None, None, None, None])]
    t = _dung(k, dong_tong_khong_ten=[26_844_553, 57_720_000, 366_600, 324_000])
    d = NK.doc_tep(t, "sinmal.xlsx")
    assert d["chi_theo_cot"]["kieu"] == "mot_dong_tong"
    assert _chi(d) == {"VMB": 26_844_553, "LAND": 57_720_000, "BH": 366_600, "QUÀ TẶNG": 324_000}


def test_hai_dong_tong_thi_khong_doan():
    """Hai dòng tổng không tên: KHÔNG chọn bừa. Đoán ở đây là quay lại đúng cái bẫy trên."""
    k = [("NGUYEN VAN A", 50_000_000, [None, None, None, None])]
    t = _dung(k, dong_tong_khong_ten=[1_000, 2_000, 3_000, 4_000], them_dong_tong_thu_hai=True)
    d = NK.doc_tep(t, "mo.xlsx")
    assert d["chi"] == []
    assert any("KHÔNG đoán" in c for c in d["chi_theo_cot"]["canh_bao"])
    assert any("KHÔNG đoán" in c for c in d["thieu"])


# ----------------------------------------------------------------- không được cộng hai đường

def test_co_bang_doc_thi_giu_bang_doc_va_noi_ra():
    """Có CẢ bảng chi dọc lẫn khối cột: giữ bảng dọc, KHÔNG cộng thêm, và phải nói ra.

    Cộng cả hai là tính hai lần — mà tính hai lần thì ra một con số trông vẫn bình thường.
    """
    wb = openpyxl.load_workbook(BytesIO(
        _dung([("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])])))
    ws = wb.create_sheet("CHI THỰC TẾ")
    ws.cell(1, 1, "NỘI DUNG"); ws.cell(1, 2, "THÀNH TIỀN")
    ws.cell(2, 1, "Xe 45 chỗ"); ws.cell(2, 2, 9_000_000)
    b = BytesIO(); wb.save(b)
    d = NK.doc_tep(b.getvalue(), "hai.xlsx")
    assert _chi(d) == {"Xe 45 chỗ": 9_000_000}
    assert any("tính hai lần" in c for c in d["chi_theo_cot"]["canh_bao"])
    assert any("tính hai lần" in c for c in d["thieu"])


# ----------------------------------------------------------------- nói ra khi tệp tự mâu thuẫn

def test_o_tong_chi_lech_voi_cong_cot_thi_phai_noi_ra():
    """Lệch một đồng cũng phải nói: hai con số nằm CÙNG MỘT HÀNG, tệp tự mâu thuẫn với chính nó.

    Đo tệp thật EU 14.01.26: ô TỔNG CHI ghi 1.800.816.553 còn các cột chi cộng ra 1.819.664.117 —
    lệch 18.847.565 đ, tức 1,05%, lọt qua ngưỡng 2% của đường bảng dọc mà không ai hay.
    """
    k = [("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])]
    t = _dung(k, dong_tong_khong_ten=[10_000_000, 20_000_000, 100_000, 50_000],
              tong_ghi=30_000_000)                    # tệp tự ghi thiếu 150.000
    d = NK.doc_tep(t, "lech.xlsx")
    assert any("tự mâu thuẫn" in x for x in d["thieu"]), d["thieu"]
    assert any("30,000,000" in x and "30,150,000" in x for x in d["thieu"]), d["thieu"]


def test_khong_lech_thi_khong_noi_gi():
    k = [("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])]
    t = _dung(k, dong_tong_khong_ten=[10_000_000, 20_000_000, 100_000, 50_000])
    d = NK.doc_tep(t, "khop.xlsx")
    assert not any("tự mâu thuẫn" in x for x in d["thieu"]), d["thieu"]


# ----------------------------------------------------------------- không nhận nhầm cột không phải tiền

def test_khong_nhan_cot_ghi_chu_lam_khoan_tien():
    wb = openpyxl.load_workbook(BytesIO(
        _dung([("NGUYEN VAN A", 50_000_000, [1, 2, 3, 4])])))
    ws = wb["QT"]
    ws.cell(5, 10, "GHI CHÚ"); ws.cell(6, 10, "khách VIP")
    ws.cell(5, 11, "HOÁ ĐƠN"); ws.cell(6, 11, 999)
    b = BytesIO(); wb.save(b)
    assert set(_chi(NK.doc_tep(b.getvalue(), "gc.xlsx"))) == set(KHOAN)


def test_hang_ten_khoan_ma_la_so_thi_bo_ca_khoi():
    """Trúng nhầm một dòng dữ liệu thì tên khoản là số. Thà bỏ cả khối còn hơn ghi tiền dưới tên vô nghĩa."""
    wb = openpyxl.load_workbook(BytesIO(
        _dung([("NGUYEN VAN A", 50_000_000, [1, 2, 3, 4])])))
    ws = wb["QT"]
    for i in range(len(KHOAN)):
        ws.cell(5, 6 + i, 12345 + i)
    b = BytesIO(); wb.save(b)
    d = NK.doc_tep(b.getvalue(), "so.xlsx")
    assert d["chi"] == [] and d["chi_theo_cot"]["kieu"] == ""


# ----------------------------------------------------------------- không phá đường cũ

def test_tep_khong_co_nhan_chi_thi_khong_doi_gi():
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "CHI THỰC TẾ"
    ws.cell(1, 1, "Mã tour:"); ws.cell(1, 2, "CU001")
    ws.cell(3, 1, "NỘI DUNG"); ws.cell(3, 2, "THÀNH TIỀN")
    ws.cell(4, 1, "Xe 45 chỗ"); ws.cell(4, 2, 9_000_000)
    ws.cell(5, 1, "Khách sạn"); ws.cell(5, 2, 5_000_000)
    b = BytesIO(); wb.save(b)
    d = NK.doc_tep(b.getvalue(), "cu.xlsx")
    assert _chi(d) == {"Xe 45 chỗ": 9_000_000, "Khách sạn": 5_000_000}
    assert d["chi_theo_cot"]["kieu"] == ""


def test_thay_khoi_cot_nhung_khong_dung_thi_khong_mang_nham_ten():
    """Tệp có bảng dọc THẮNG khối cột — thì hai câu soi phải nói về BẢNG DỌC, không nói về cột.

    Bản đầu soi theo `kieu` ("có thấy khối cột") chứ không theo `dung` ("có lấy số từ khối cột").
    Hậu quả: tệp lấy giá vốn từ bảng dọc lại bị mắng "các cột chi của tệp lệch nhau" — một câu vừa
    sai vừa đẩy người đọc đi tìm nhầm chỗ. Quét 232 tệp phép thử bắt được đúng chỗ này.
    """
    wb = openpyxl.load_workbook(BytesIO(
        _dung([("NGUYEN VAN A", 50_000_000, [10_000_000, 20_000_000, 100_000, 50_000])],
              dong_tong_khong_ten=[10_000_000, 20_000_000, 100_000, 50_000], tong_ghi=99_000_000)))
    ws = wb.create_sheet("CHI THỰC TẾ")
    ws.cell(1, 1, "NỘI DUNG"); ws.cell(1, 2, "THÀNH TIỀN")
    ws.cell(2, 1, "Xe 45 chỗ"); ws.cell(2, 2, 9_000_000)
    b = BytesIO(); wb.save(b)
    d = NK.doc_tep(b.getvalue(), "hai.xlsx")
    assert d["chi_theo_cot"]["kieu"] and not d["chi_theo_cot"]["dung"]
    assert not any("tự mâu thuẫn" in x for x in d["thieu"]), d["thieu"]
    assert any("cộng lại từ dòng" in x for x in d["thieu"]), d["thieu"]
