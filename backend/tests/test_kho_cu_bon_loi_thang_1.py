# -*- coding: utf-8 -*-
"""Bốn lỗi của bộ đọc kho cũ, đo được trên 81 tệp quyết toán tháng 1/2026 ngày 15/9/2026.

Chủ tịch bác số đã báo ("sai hoàn toàn") và yêu cầu đọc từng tệp, từng sheet. Mở hết 309 sheet thì
ra bốn lỗi riêng biệt, mỗi lỗi một cơ chế, cộng lại làm giá vốn tháng 1 thiếu 2.271.716.615 đồng:

    thu 7.965.008.452  chi 4.392.577.191  lãi gộp 3.572.431.261  (44,85% – số đã báo, sai)
    thu 7.958.828.586  chi 6.664.293.806  lãi gộp 1.294.534.780  (16,27% – số đo lại)

Doanh thu gần như đúng. Toàn bộ sai số nằm ở cột chi.

Mỗi phép thử dưới đây dựng lại ĐÚNG hình dạng sheet đã gây ra lỗi, lấy từ tệp thật. Không dùng tệp
thật trong phép thử: tệp thật có tên khách và số tiền của khách hàng, không đưa vào kho mã nguồn.
"""
from __future__ import annotations

from io import BytesIO

import openpyxl

from app.services import nap_kho_cu as K


def _tep(sheets: dict) -> bytes:
    """{tên sheet: [[ô,…],…]} -> bytes xlsx. Sheet đầu trong dict là sheet đầu trong tệp."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for ten, hang in sheets.items():
        ws = wb.create_sheet(ten)
        for r, dong in enumerate(hang, 1):
            for c, v in enumerate(dong, 1):
                if v is not None:
                    ws.cell(r, c, v)
    b = BytesIO()
    wb.save(b)
    return b.getvalue()


def _o(n: int) -> list:
    return [None] * n


# =============================================================================================
# LỖI 1 — SHEET MA: quyết toán của chuyến năm cũ còn sót trong tệp
# =============================================================================================

def _sheet_quyet_toan(ma: str, ngay: str, ten_khach: list, gia: int, chi_1: int) -> list:
    """Bảng khách chuẩn kho cũ: STT | SALES | TÊN KHÁCH HÀNG | GIÁ BÁN | THU KHÁC | TỔNG THU | …"""
    h = [
        _o(2) + ["Công ty Cổ Phần Vietourist Holdings"],
        _o(2) + ["Mã tour:", ma, None, None, "Tên tour:", "TOUR THỬ"],
        _o(2) + ["Ngày đi:", ngay, None, None, "Ngày về:", ngay],
        ["NO", "SALES", "TÊN KHÁCH HÀNG", "THU ", None, None, "CHI", None, None, "LỢI NHUẬN"],
        [None, None, None, "GIÁ BÁN", "THU KHÁC", "TỔNG THU", "LAND", "BH", "TỔNG CHI"],
    ]
    for i, t in enumerate(ten_khach, 1):
        h.append([i, "SALE A", t, gia, None, gia, chi_1, 0, chi_1, gia - chi_1])
    n = len(ten_khach)
    h.append([None, None, None, gia * n, None, gia * n, chi_1 * n, 0, chi_1 * n,
              (gia - chi_1) * n])
    return h


def test_loi1_bo_sheet_cua_chuyen_nam_cu():
    """9 tệp mang sheet 'PT14012022' – quyết toán Phan Thiết 14/01/2022 người lập quên xoá.

    Bộ đọc lấy sheet khớp ĐẦU TIÊN, nên 9 chuyến 2026 vào sổ với doanh thu 26.000.000 của năm 2022.
    """
    b = _tep({
        "PT14012022": _sheet_quyet_toan("PT14012022", "14/01/2022", ["KHÁCH CŨ"] * 20,
                                        1_300_000, 1_107_114),
        "PHANTHIET": _sheet_quyet_toan("PT001.04040126", "04/01/2026", ["KHÁCH MỚI"] * 44,
                                       1_502_727, 1_245_541),
    })
    d = K.doc_tep(b, "thu.xlsx")

    assert d["sheet_ma"] == ["PT14012022"], "sheet năm 2022 phải bị nhận ra và loại"
    assert d["ma_tour"] == "PT001.04040126", "đầu tệp phải là của chuyến 2026, không phải 2022"
    assert d["tong_thu"] == 1_502_727 * 44
    assert any("năm cũ" in x for x in d["thieu"]), "phải NÓI RA là đã bỏ sheet nào"


def test_loi1_khong_bo_sheet_khi_moi_sheet_cung_nam():
    """Luật chỉ được loại sheet năm CŨ HƠN. Cùng năm thì không đụng tới."""
    b = _tep({
        "XE 1": _sheet_quyet_toan("DL002.01", "04/01/2026", ["A"] * 10, 1_000_000, 800_000),
        "XE 2": _sheet_quyet_toan("DL002.01", "04/01/2026", ["B"] * 10, 1_000_000, 800_000),
    })
    d = K.doc_tep(b, "thu.xlsx")
    assert d["sheet_ma"] == []


def test_loi1_sheet_chi_phi_chep_sot_o_NGAY_KHONG_PHAI_sheet_ma():
    """CHỖ LUẬT NĂM SUÝT NUỐT MẤT TIỀN THẬT — bắt được khi chạy thử nạp cả 81 tệp ngày 15/9/2026.

    Tệp "QTT ĐOÀN PHAN THIẾT 15.01.2026 - SALE KIM OANH" có sheet 'CHI THỰC TẾ' ghi KHỞI HÀNH
    "13-14/12/2025" và sheet 'HDV CHI' ghi "15-17/01/2025" – ô ngày chép sót từ tệp tháng trước,
    còn nội dung bên dưới là chi phí THẬT của chuyến 15/01/2026.

    Bản đầu của luật chỉ hỏi "năm có cũ hơn không" nên bỏ cả hai sheet ấy. Tổng tiền của tệp VẪN
    ĐÚNG vì lấy từ hàng tổng bảng khách – nên không có gì đỏ lên – nhưng toàn bộ DÒNG chi phí biến
    mất. Đúng kiểu hỏng im lặng mà cả bộ đọc này viết ra để tránh.

    Sheet ma thật là một BẢN QUYẾT TOÁN ĐẦY ĐỦ của chuyến khác: có bảng khách riêng. Sheet chi phí
    chép sót ô ngày thì không có bảng khách nào.
    """
    chi_chep_sot = [
        ["CHI PHÍ ĐOÀN PHAN THIẾT"],
        ["MÃ TOUR:", "PT001.04", "SỐ LƯƠNG", 25],
        ["KHỞI HÀNH:", "13-14/12/2025"],          # ô ngày CHÉP SÓT của tệp tháng trước
        _o(0),
        ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
        ["II/ CHI PHÍ:"],
        [None, "XE 45C", "VIETRIP", 9_000_000, 1, 1, 9_000_000],
        [None, "LƯU TRÚ", "Sea Links", 700_000, 25, 1, 17_500_000],
        ["TỔNG CỘNG CHI", None, None, None, None, None, 26_500_000],
    ]
    b = _tep({
        "QUYẾT TOÁN": _sheet_quyet_toan("PT001.04", "15/01/2026", ["K"] * 25,
                                        1_840_000, 1_060_000),
        "CHI THỰC TẾ": chi_chep_sot,
    })
    d = K.doc_tep(b, "thu.xlsx")

    assert d["sheet_ma"] == [], (
        f"bỏ nhầm {d['sheet_ma']} – sheet chi phí chép sót ô ngày KHÔNG phải sheet ma, vì nó không "
        "có bảng khách của riêng nó")
    assert d["tong_chi_cong_dong"] == 26_500_000, "mất dòng chi phí thật vì luật năm quá tay"
    assert len(d["chi"]) == 2


# =============================================================================================
# LỖI 2 — MICE: một sheet có HAI hàng tiêu đề, xếp cột khác nhau
# =============================================================================================

def _sheet_chi_thuc_te_mice() -> list:
    """Sheet 'CHI THỰC TẾ' của tệp đoàn: bảng GIÁ TOUR rồi bảng CHI PHÍ, mỗi bảng một tiêu đề.

    Cột THÀNH TIỀN của bảng trên là E; của bảng dưới là F. Ô E của bảng dưới là 'LƯỢT TÍNH' = 1.
    """
    return [
        ["CHI PHÍ ĐOÀN THỬ"],
        ["MÃ TOUR:", "HT001.01", "SỐ LƯƠNG", 24],
        ["KHỞI HÀNH:", "09/01/2026"],
        _o(0),
        _o(0),
        ["NGÀY", "NỘI DUNG ", "ĐƠN GIÁ", "SL", "THÀNH TIỀN", "VAT", "TIỀN THUẾ", "THÀNH TIỀN"],
        ["I/GIÁ TOUR:"],
        [None, "NGƯỜI LỚN ", 5_000_000, 24, 120_000_000, 0.08, 9_600_000, 129_600_000],
        _o(6) + [9_600_000, 129_600_000],
        _o(0),
        _o(0),
        # hàng mốc KIÊM hàng tiêu đề mới – cột tiền dịch từ E sang F
        ["II/ CHI PHÍ:", None, "ĐƠN GIÁ", "SL", "LƯỢT TÍNH", "THÀNH TIỀN", "VAT", "TỔNG CỘNG"],
        ["A. VẬN CHUYỂN:"],
        ["Vận Chuyển", "45 chỗ Vietrip", 13_000_000, 1, 1, 13_000_000, 0.08, 962_962],
        ["Lưu Trú", "Seava Thứ 6", 600_000, 24, 1, 14_400_000, 0.08, 1_066_666],
        [None, "Ăn Trưa", 250_000, 25, 1, 6_250_000, 0.08, 462_962],
        ["TỔNG", None, None, None, None, 33_650_000],
    ]


def test_loi2_mice_doc_dung_cot_tien_cua_bang_duoi():
    """Bản cũ đọc cột E (LƯỢT TÍNH = 1) làm tiền chi: 9 tệp MICE ra tổng 173 ĐỒNG."""
    b = _tep({
        "TN": _sheet_quyet_toan("HT001.01", "09/01/2026", ["KHÁCH"] * 24, 5_400_000, 4_585_249),
        "CHI THỰC TẾ": _sheet_chi_thuc_te_mice(),
    })
    d = K.doc_tep(b, "thu.xlsx")

    dong = [x for x in d["chi"] if x["thanh_tien"] is not None]
    tien = sorted(x["thanh_tien"] for x in dong)
    assert 13_000_000 in tien, f"phải đọc được xe 13 triệu, đang đọc: {tien}"
    assert 14_400_000 in tien
    assert 6_250_000 in tien
    assert 1 not in tien, "1 là 'LƯỢT TÍNH' của bảng dưới, không phải tiền"
    assert d["tong_chi_cong_dong"] == 33_650_000


def test_loi2_khong_doi_cot_khi_sheet_chi_co_mot_tieu_de():
    """Sheet một tiêu đề (đa số tệp) phải đọc y như cũ – không được đổi cột bừa."""
    b = _tep({"QT": _sheet_quyet_toan("DL002.01", "04/01/2026", ["A"] * 5, 1_000_000, 800_000),
              "CTT": [
                  ["CHI PHÍ TOUR THỬ"],
                  ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
                  ["II/ CHI PHÍ:"],
                  [None, "XE 45C", "VIETRIP", 9_000_000, 1, 1, 9_000_000],
                  ["LƯU TRÚ", "KHÁCH SẠN 3*", "Lan Anh", 175_000, 5, 2, 1_750_000],
                  ["TỔNG CỘNG CHI", None, None, None, None, None, 10_750_000],
              ]})
    d = K.doc_tep(b, "thu.xlsx")
    assert d["tong_chi_cong_dong"] == 10_750_000


# =============================================================================================
# LỖI 3 — CÔNG NỢ bị cộng thêm lên trên tổng chi
# =============================================================================================

def test_loi3_khong_cong_sheet_cong_no_vao_gia_von():
    """19 tệp cộng thừa nguyên sheet CÔNG NỢ. Khoản trong đó ĐÃ nằm trong sheet chi phí.

    Sheet CÔNG NỢ có tiêu đề trông y hệt bảng chi (DỊCH VỤ | ĐƠN GIÁ | SL | ĐÊM | TỔNG TIỀN) nên bản
    cũ nhận là bảng chi thứ hai. Phần thừa đo được khớp đúng từng đồng với tổng sheet ấy.
    """
    ctt = [
        ["CHI PHÍ TOUR ĐÀ LẠT"],
        ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
        ["II/ CHI PHÍ:"],
        [None, "XE 45C", "VIETRIP", 9_000_000, 1, 1, 9_000_000],
        ["LƯU TRÚ", "KHÁCH SẠN 3*", "Lan Anh Hotel", 175_000, 39, 2, 13_650_000],
        [None, "ĂN SÁNG", "Lan Anh Hotel", 90_000, 39, 1, 3_510_000],
        ["TỔNG CỘNG CHI", None, None, None, None, None, 26_160_000],
    ]
    cong_no = [
        ["CÔNG NỢ ĐOÀN SG"],
        ["DỊCH VỤ", None, "ĐƠN GIÁ", "SL", "ĐÊM", "TỔNG TIỀN"],
        ["KHÁCH SẠN 3*", "Lan Anh Hotel", 175_000, 39, 2, 13_650_000],
        ["ĂN SÁNG", "Lan Anh Hotel", 90_000, 39, 1, 3_510_000],
        ["TỔNG", None, None, None, None, 17_160_000],
    ]
    b = _tep({
        "QUYẾT TOÁN": _sheet_quyet_toan("DL002.03", "23/01/2026", ["K"] * 39, 1_099_487, 848_769),
        "CTT": ctt,
        "CÔNG NỢ": cong_no,
    })
    d = K.doc_tep(b, "thu.xlsx")

    assert d["tong_chi_cong_dong"] == 26_160_000, "17.160.000 của CÔNG NỢ KHÔNG được cộng thêm"
    assert [x["sheet"] for x in d["dien_giai"]] == ["CÔNG NỢ"], "vẫn phải GIỮ để người xem"
    assert sum(x["thanh_tien"] for x in d["dien_giai"][0]["dong"]
               if x["thanh_tien"] is not None) == 17_160_000


# =============================================================================================
# LỖI 4 — không có bảng chi riêng: chi phí nằm ngay trên bảng khách
# =============================================================================================

def test_loi4_lay_tong_tep_ghi_khi_khong_co_bang_chi_rieng():
    """5 tệp (EU + 4 tệp SM) ghi chi = 0 vì chi phí nằm trong cột của chính bảng khách.

    Bộ đọc đi tìm sheet có tiêu đề bảng chi; các tệp này không có sheet nào như thế. Cột 'TỔNG CHI'
    của bảng khách thì có. EU 14.01: chi thật 1.800.816.553, vào sổ thành 0.
    """
    b = _tep({"QT": _sheet_quyet_toan("EU001.01", "14/01/2026", ["K"] * 38,
                                      52_544_178, 47_390_000)})
    d = K.doc_tep(b, "thu.xlsx")

    assert d["tong_chi"] == 47_390_000 * 38, "phải lấy được giá vốn từ cột TỔNG CHI của bảng khách"
    assert d["tong_chi"] != 0


# =============================================================================================
# TỔNG ƯU TIÊN — tệp ghi tổng thì lấy tổng, không ghi thì cộng dòng, lệch thì nói ra
# =============================================================================================

def test_tong_tep_ghi_duoc_uu_tien_va_van_giu_so_cong_dong():
    b = _tep({
        "QUYẾT TOÁN": _sheet_quyet_toan("DL002.03", "23/01/2026", ["K"] * 39, 1_099_487, 848_769),
        "CTT": [
            ["CHI PHÍ"],
            ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
            ["II/ CHI PHÍ:"],
            [None, "XE 45C", "VIETRIP", 9_000_000, 1, 1, 9_000_000],
        ],
    })
    d = K.doc_tep(b, "thu.xlsx")
    assert d["tong_ghi"]["chi"] == 848_769 * 39
    assert d["tong_chi_cong_dong"] == 9_000_000
    assert d["tong_chi"] == d["tong_ghi"]["chi"], "số chốt là số TỆP GHI"
    assert any("cộng lại từ dòng" in x for x in d["thieu"]), "lệch lớn thì PHẢI nói ra"


def test_khong_co_tong_ghi_thi_van_cong_tu_dong():
    """Tệp không ghi tổng nào thì luật cũ vẫn chạy nguyên – không được hỏng vì bản sửa này."""
    b = _tep({"CTT": [
        ["CHI PHÍ TOUR"],
        ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
        ["II/ CHI PHÍ:"],
        [None, "XE 45C", "VIETRIP", 9_000_000, 1, 1, 9_000_000],
        [None, "KHÁCH SẠN", "Lan Anh", 175_000, 10, 2, 3_500_000],
    ]})
    d = K.doc_tep(b, "thu.xlsx")
    assert d["tong_ghi"]["chi"] is None
    assert d["tong_chi"] == 12_500_000


def test_hai_cach_doc_tong_lech_nhau_thi_neu_ten():
    """Hàng tổng bảng khách và nhãn TỔNG trên sheet chi phí không gặp nhau -> phải nói ra."""
    b = _tep({
        "QUYẾT TOÁN": _sheet_quyet_toan("DL002.03", "23/01/2026", ["K"] * 10, 1_000_000, 800_000),
        "CTT": [
            ["CHI PHÍ"],
            ["NGÀY", "NỘI DUNG ", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN"],
            ["II/ CHI PHÍ:"],
            [None, "XE 45C", "VIETRIP", 8_000_000, 1, 1, 8_000_000],
            [None, None, None, None, None, "TỔNG THU", 10_000_000],
            [None, None, None, None, None, "TỔNG CHI", 7_777_777],
        ],
    })
    d = K.doc_tep(b, "thu.xlsx")
    assert any("lệch" in x and "TỔNG" in x for x in d["thieu"]), d["thieu"]
