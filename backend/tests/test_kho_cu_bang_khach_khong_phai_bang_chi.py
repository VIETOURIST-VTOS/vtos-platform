# -*- coding: utf-8 -*-
"""Bảng KHÁCH có cột chi phí KHÔNG phải là bảng CHI PHÍ.

VÌ SAO PHÉP THỬ NÀY TỒN TẠI — một con số đo được, không phải một lo xa

Ngày 13/9/2026 Chủ tịch duyệt cấu trúc và giao nạp kho T1–T6/2026 lên để chạy trên số thật. Trước
khi nạp, chạy bộ đọc lên cả 604 tệp và đếm chất lượng từng dòng. Kết quả:

    4.113 / 13.438 dòng chi (30%) có ô "nội dung" chứa một CON SỐ thay vì chứa chữ, ở 328 tệp.

Nguyên nhân là MỘT hình dạng bảng, rất phổ biến trong kho cũ — BẢNG KHÁCH CÓ CỘT CHI PHÍ:

    TT | SALES | TÊN KHÁCH HÀNG | THU……… | TỔNG THU | CHI PHÍ…………… | TỔNG CHI | LỢI NHUẬN
                                 GIÁ BÁN|THU KHÁC       CP TREN TOUR|TL|BH|NƯỚC

Mỗi dòng dưới là MỘT KHÁCH; cột "CHI PHÍ" là giá vốn phân bổ cho khách ấy. Nhưng hàng tiêu đề có
"CHI PHÍ" (nhãn bắt buộc của bảng chi) và "TỔNG CHI" (nhãn kèm), nên luật cũ nhận nhầm là bảng chi
và đọc mỗi khách thành một dòng chi phí với nội dung = 475142.857.

HỎNG NÀY IM LẶNG THEO ĐÚNG CÁCH TỆ NHẤT: vẫn ra một con số, vẫn cộng được, không có gì đỏ lên. Và
nó còn CHE MẤT bảng chi thật — ở tệp Nam Cát Tiên, bảng chi thật nằm ở sheet "CHI PHI" với đủ
NGÀY | NỘI DUNG | ĐỐI TÁC | ĐƠN GIÁ | SL | THÀNH TIỀN, nhưng sheet khách được đọc trước nên chiếm chỗ.

Sau khi sửa, đo lại trên đúng 604 tệp ấy: lệch cột còn 293 dòng (3%), dòng đọc đúng lên 80%.

  BK1  hàng tiêu đề có nhãn TÊN KHÁCH thì KHÔNG được nhận là hàng tiêu đề bảng chi
  BK2  bảng chi thật ở sheet khác vẫn phải đọc được — sửa mà che mất bảng đúng thì vô nghĩa
  BK3  ô "nội dung" của dòng chi không được là một con số
  BK4  bảng chi BÌNH THƯỜNG không bị luật mới đụng tới (chốt chặn chống chữa lợn lành)
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_bangkhach.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_bangkhach.db", "test_bangkhach.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import re                                                            # noqa: E402
from io import BytesIO                                               # noqa: E402

import openpyxl                                                      # noqa: E402

from app.services import nap_kho_cu as KHO                           # noqa: E402


def _so(v):
    """Ô nội dung có phải chỉ là một con số không — chính phép đo đã dùng trên 604 tệp."""
    s = (v or "").strip().replace(",", "").replace(".", "")
    return bool(s) and re.fullmatch(r"-?\d+", s) is not None


def _tep_nam_cat_tien() -> bytes:
    """Dựng lại ĐÚNG hình dạng đã gây ra 4.113 dòng hỏng.

    Hai sheet, và thứ tự quan trọng: sheet KHÁCH đứng TRƯỚC sheet chi phí thật — đúng như tệp
    "QT NAM CÁT TIÊN 02.05.2026" trong kho, vì đó là điều khiến bảng sai chiếm chỗ của bảng đúng.
    """
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "NCT"
    ws["A1"] = "Mã tour:"; ws["B1"] = "NCT010526"
    ws["A2"] = "Ngày đi:"; ws["B2"] = "2026-05-01"
    ws["A3"] = "Số khách:"; ws["B3"] = 3
    # Hàng tiêu đề "hai tầng" – đây là chỗ bẫy.
    ws["A7"] = "TT"; ws["B7"] = "SALES"; ws["C7"] = "TÊN KHÁCH HÀNG"
    ws["D7"] = "THU "; ws["F7"] = "TỔNG THU"; ws["G7"] = "CHI PHÍ"
    ws["M7"] = "TỔNG CHI"; ws["N7"] = "LỢI NHUẬN"
    ws["D8"] = "GIÁ BÁN"; ws["E8"] = "THU KHÁC"; ws["G8"] = "CP TREN TOUR"; ws["H8"] = "TL"
    for i, ten in enumerate(("LƯƠNG NGUYỄN HỒNG", "TRẦN HUỲNH", "HUỲNH TUYẾT LAN"), start=9):
        ws.cell(i, 1, i - 8); ws.cell(i, 3, ten)
        ws.cell(i, 4, 690000); ws.cell(i, 6, 690000)
        ws.cell(i, 7, 475142.857); ws.cell(i, 8, 11904.76)
        ws.cell(i, 13, 494561.90); ws.cell(i, 14, 195438.09)

    ws2 = wb.create_sheet("CHI PHI")
    ws2["A7"] = "NGÀY"; ws2["B7"] = "NỘI DUNG"; ws2["C7"] = "ĐỐI TÁC"
    ws2["D7"] = "ĐƠN GIÁ"; ws2["E7"] = "SL"; ws2["H7"] = "THÀNH TIỀN"
    for i, (nd, dg, sl, tt) in enumerate((("XE 45 CHỖ", 4500000, 1, 4500000),
                                          ("ĂN TRƯA", 150000, 22, 3300000),
                                          ("VÉ THAM QUAN", 80000, 22, 1760000)), start=8):
        ws2.cell(i, 2, nd); ws2.cell(i, 4, dg); ws2.cell(i, 5, sl); ws2.cell(i, 8, tt)

    b = BytesIO(); wb.save(b); return b.getvalue()


def test_bk1_hang_tieu_de_co_ten_khach_thi_khong_phai_bang_chi():
    """Luật thêm vào, phát biểu thẳng: một hàng không thể vừa là tiêu đề bảng khách vừa là tiêu đề
    bảng chi. Đây là chỗ sửa, nên canh thẳng vào nó."""
    wb = openpyxl.load_workbook(BytesIO(_tep_nam_cat_tien()), data_only=True)
    ws = wb["NCT"]
    assert KHO._hang_tieu_de_chi(ws) is None, (
        "Hàng tiêu đề của BẢNG KHÁCH (có 'TÊN KHÁCH HÀNG') vẫn bị nhận là hàng tiêu đề BẢNG CHI. "
        "Đọc như vậy thì mỗi KHÁCH thành một dòng chi phí, nội dung là một con số, và không có gì "
        "đỏ lên vì con số nào cũng cộng được.")


def test_bk2_bang_chi_that_o_sheet_khac_van_doc_duoc():
    """Chốt chặn quan trọng nhất của bản sửa: bỏ được bảng sai mà vẫn lấy được bảng đúng.

    Bỏ bảng sai rồi không đọc được gì thì mới là làm hỏng — giá vốn về 0 mà vẫn "chạy được".
    """
    d = KHO.doc_tep(_tep_nam_cat_tien(), "QT NAM CÁT TIÊN thử.xlsx")
    assert d["sheet_chi"] == "CHI PHI", \
        f"phải lấy bảng chi ở sheet 'CHI PHI', đang lấy ở {d['sheet_chi']!r}"
    assert len(d["chi"]) == 3, f"phải đọc đủ 3 dòng chi, đang được {len(d['chi'])}"
    assert d["khach"] and len(d["khach"]) == 3, "bảng khách vẫn phải đọc được bình thường"


def test_bk3_o_noi_dung_cua_dong_chi_khong_duoc_la_mot_con_so():
    """Phép đo đã dùng trên 604 tệp, đưa vào phép thử để nó không mòn đi."""
    d = KHO.doc_tep(_tep_nam_cat_tien(), "QT NAM CÁT TIÊN thử.xlsx")
    xau = [c for c in d["chi"] if _so(c.get("noi_dung"))]
    assert not xau, (
        "Dòng chi có ô nội dung là một CON SỐ – bộ đọc đang map lệch cột: "
        f"{[(c.get('noi_dung'), c.get('thanh_tien')) for c in xau[:3]]}")
    assert {(c.get("noi_dung") or "").strip() for c in d["chi"]} == \
        {"XE 45 CHỖ", "ĂN TRƯA", "VÉ THAM QUAN"}


def test_bk4_bang_chi_binh_thuong_khong_bi_dung_toi():
    """Chống chữa lợn lành. Luật mới chỉ được loại hàng tiêu đề CÓ nhãn tên khách; một bảng chi
    bình thường – không có cột tên khách – phải đọc y như trước."""
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "QT"
    ws["A1"] = "Mã tour:"; ws["B1"] = "TN001.04010126"
    ws["A5"] = "NGÀY"; ws["B5"] = "NỘI DUNG"; ws["C5"] = "ĐỐI TÁC"
    ws["D5"] = "ĐƠN GIÁ"; ws["E5"] = "SL"; ws["F5"] = "THÀNH TIỀN"
    ws["B6"] = "KHÁCH SẠN"; ws["D6"] = 800000; ws["E6"] = 10; ws["F6"] = 8000000
    ws["B7"] = "HDV"; ws["D7"] = 1200000; ws["E7"] = 1; ws["F7"] = 1200000
    b = BytesIO(); wb.save(b)

    d = KHO.doc_tep(b.getvalue(), "binh thuong.xlsx")
    assert len(d["chi"]) == 2, f"bảng chi bình thường phải đọc đủ 2 dòng, đang được {len(d['chi'])}"
    assert [c["noi_dung"] for c in d["chi"]] == ["KHÁCH SẠN", "HDV"]
    assert KHO.tong_chi(d) == 9200000
