"""Dòng TIỂU TỔNG và khối KÝ TÊN không được đi vào bảng chi.

VÌ SAO CÓ TỆP NÀY

Đo ngày 18/9/2026 trên VTOS thật: 57 chuyến mang giá vốn ĐÚNG GẤP ĐÔI số của tệp gốc, ghi dư
2.633.963.180 đồng. Không có gì đỏ lên, vì mọi bảng đều cộng đúng từ dòng — chỉ có điều số dòng
nhiều gấp đôi.

Nguồn gốc nằm ở một chi tiết của mẫu quyết toán Phan Thiết / Nam Cát Tiên: tổng của từng mục
được ghi ở dòng ngay dưới mục ấy, và ô duy nhất có chữ trên dòng đó là hai chữ "TC" ở cột SỐ
LƯỢNG. Bộ đọc có sẵn hai hàng rào — `_la_dong_tong()` bắt chữ "TỔNG"/"CỘNG", và luật "dòng không
có chữ ở cột mô tả nào thì là dòng tổng" — nhưng "TC" lọt qua CẢ HAI: nó không bắt đầu bằng
"TỔNG", và nó CÓ chữ cái.

Kèm theo là một đồng lẻ dai dẳng: 2.025. Nó đến từ dòng "Ngày … tháng … năm 2025" trong khối ký
tên dưới bảng — `_so()` cố tình bỏ đuôi chữ để đọc được "1.290.000đ", nên nó đọc chuỗi ấy ra 2025.

Trên tệp PHAN THIẾT 14.07.2026:
    11 dòng chi thật                                   39.991.500
    3 dòng tiểu tổng (37.560.000 + 384.000 + 2.047.500) 39.991.500
    khối ký tên                                             2.025
    ------------------------------------------------ cộng 79.985.025
và 79.985.025 đúng bằng con số `intake_kho_cu` đã ghi cho chuyến ấy.

QUÉT LẠI 769 TỆP SAU KHI VÁ: số tệp có cộng-dòng khớp hàng TỔNG CỘNG của chính tệp tăng từ 300
lên 440, KHÔNG tệp nào đang đúng mà thành sai.
"""
import os
import sys
from io import BytesIO

import openpyxl
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import nap_kho_cu as NK                       # noqa: E402


def _tep(ky_hieu_tieu_tong: str = "TC", co_khoi_ky_ten: bool = True) -> bytes:
    """Dựng một tệp đúng hình dạng mẫu Phan Thiết: có tiểu tổng và khối ký tên."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CHI PHI"
    ws["A1"] = "CHI PHÍ TOUR PHAN THIẾT"
    ws["A2"], ws["B2"] = "MÃ TOUR:", "PT-THU-001"
    ws["A3"], ws["B3"] = "KHỞI HÀNH:", "14/07/2026"
    ws["A5"], ws["B5"] = "SỐ KHÁCH:", "29 KHÁCH"
    for c, n in enumerate(["NGÀY", "NỘI DUNG", "", "ĐƠN GIÁ", "SL", "DIỄN GIẢI",
                           "CÔNG NỢ", "THÀNH TIỀN", "GHI CHÚ"], start=1):
        ws.cell(7, c, n)
    ws["A9"] = "A/ THU"
    ws.cell(10, 2, "NGƯỜI LỚN"); ws.cell(10, 4, 1_690_000); ws.cell(10, 5, 28); ws.cell(10, 8, 47_320_000)
    ws["A13"] = "TỔNG CỘNG THU"; ws.cell(13, 8, 47_320_000)
    ws["A14"] = "B/ CHI"
    ws["A15"] = "I/CHI PHÍ VẬN CHUYỂN"
    ws.cell(16, 1, "LAND"); ws.cell(16, 2, "XE 45C"); ws.cell(16, 3, "VIETRIP")
    ws.cell(16, 4, 8_000_000); ws.cell(16, 5, 1); ws.cell(16, 8, 8_000_000)
    ws.cell(17, 2, "Lưu trú"); ws.cell(17, 3, "NOVELA")
    ws.cell(17, 4, 350_000); ws.cell(17, 5, 28); ws.cell(17, 8, 19_600_000)
    # DÒNG TIỂU TỔNG: cả dòng trống, trừ ký hiệu ở cột SL.
    ws.cell(18, 5, ky_hieu_tieu_tong); ws.cell(18, 8, 27_600_000)
    ws["A19"] = "II.CHI PHÍ KHÁC:"
    ws.cell(20, 2, "Nước suối"); ws.cell(20, 4, 5_000); ws.cell(20, 5, 96); ws.cell(20, 8, 480_000)
    ws.cell(21, 5, ky_hieu_tieu_tong); ws.cell(21, 8, 480_000)
    ws["A22"] = "TỔNG CỘNG CHI (I+II)"; ws.cell(22, 8, 28_080_000)
    if co_khoi_ky_ten:
        ws.cell(24, 5, "TP. ĐIỀU HÀNH"); ws.cell(24, 8, "Ngày      tháng      năm 2025")
        ws.cell(25, 1, "ĐIỀU HÀNH"); ws.cell(25, 3, "KẾ TOÁN")
    b = BytesIO(); wb.save(b); return b.getvalue()


def _cong_chi(noi: bytes) -> float:
    d = NK.doc_tep(noi, "thử.xlsx")
    return sum(x["thanh_tien"] for x in d["chi"]
               if x.get("phan") == "chi" and x.get("thanh_tien"))


THAT = 8_000_000 + 19_600_000 + 480_000          # 28.080.000 – ba dòng chi thật


def test_dong_tieu_tong_TC_khong_duoc_cong_vao():
    """Đây là phép thử chính: 'TC' ở cột SL không biến dòng tổng thành một khoản chi."""
    assert _cong_chi(_tep()) == THAT


@pytest.mark.parametrize("ky_hieu", ["TC", "T.C", "TC:", "tc", "Tổng", "CỘNG"])
def test_moi_ky_hieu_tieu_tong_deu_bi_loai(ky_hieu):
    assert _cong_chi(_tep(ky_hieu)) == THAT


def test_khoi_ky_ten_khong_sinh_ra_khoan_chi_2025():
    """'Ngày … tháng … năm 2025' bị _so() đọc ra 2025 – đúng đồng lẻ của 57 chuyến sai."""
    assert _cong_chi(_tep(co_khoi_ky_ten=True)) == _cong_chi(_tep(co_khoi_ky_ten=False))


def test_khong_gap_doi_nua():
    """Canh thẳng vào triệu chứng: cộng dòng KHÔNG được bằng hai lần số thật."""
    assert _cong_chi(_tep()) != THAT * 2


def test_mo_ta_that_co_chu_TC_van_duoc_giu():
    """'TC' là ký hiệu chỉ khi nó chiếm TRỌN ô. 'TC Land' là mô tả thật – không được loại.

    So khớp phần đầu chuỗi thay vì trọn ô sẽ làm mất những khoản chi tên bắt đầu bằng TC.
    """
    wb = openpyxl.load_workbook(BytesIO(_tep()))
    ws = wb["CHI PHI"]
    # openpyxl: cell(r, c, None) KHÔNG xoá ô – None nghĩa là "không truyền giá trị".
    # Phải gán qua .value, nếu không ô vẫn còn "TC" và phép thử này soát nhầm chính nó.
    ws.cell(18, 5).value = None               # bỏ ký hiệu tiểu tổng
    ws.cell(18, 2, "TC Land Phan Thiết")      # thay bằng một mô tả thật
    b = BytesIO(); wb.save(b)
    assert _cong_chi(b.getvalue()) == THAT + 27_600_000


def test_dong_chi_that_van_du_so_luong():
    d = NK.doc_tep(_tep(), "thử.xlsx")
    ten = [x["noi_dung"] for x in d["chi"] if x.get("phan") == "chi" and x.get("thanh_tien")]
    assert ten == ["XE 45C", "Lưu trú", "Nước suối"]
