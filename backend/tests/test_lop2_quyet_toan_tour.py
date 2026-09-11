# -*- coding: utf-8 -*-
"""Lớp 2 của quyết toán tour – bộ đọc bốn sheet và bộ đối chiếu.

Mọi phép thử ở đây dựng workbook trong bộ nhớ theo đúng bố cục tệp thật của Điều hành, và CỐ Ý gài
lại ba chỗ vênh đã đo được trên tệp "QT TOUR NHA TRANG 10.07.26.xlsx":

    ngày khởi hành   sheet QT ghi 07/07, sheet CTT và mã tour đều nói 10/07
    số khách         sheet QT ghi 44, CTT ghi 42, và bảng chỉ có 42 dòng
    chi của HDV      HDV tính vé cho 44 khách, chiết tính tính cho 40 – chênh 120.000 đ

Không dùng tệp thật làm dữ liệu thử: nó chứa họ tên và số điện thoại của 42 khách, và một tệp phép
thử thì nằm trong kho mã, đi theo mọi bản sao, mãi mãi.

Ba phép thử cuối là phép thử ĐỘT BIẾN: chúng dựng workbook KHÔNG có lỗi rồi khẳng định bộ đối chiếu
im lặng. Thiếu chúng thì một bộ đối chiếu luôn luôn kêu cũng qua được cả bộ, và một bộ kiểm kêu ở
mọi tệp thì sau vài lần không ai đọc nữa.
"""
import io
from datetime import date

import pytest

openpyxl = pytest.importorskip("openpyxl")

from app.services import quyet_toan_chi_tiet as QT


# ---------------------------------------------------------------------------------------------
# Dựng tệp thử
# ---------------------------------------------------------------------------------------------

def _sheet_qt(wb, ma_tour, ngay_di, so_khach_ghi, khach):
    ws = wb.create_sheet("QT") if "QT" not in wb.sheetnames else wb["QT"]
    ws["C4"], ws["D4"] = "Mã tour:", ma_tour
    ws["G4"], ws["I4"] = "Tên tour:", "NHA TRANG"
    ws["C5"], ws["D5"] = "Số khách:", so_khach_ghi
    ws["G5"], ws["I5"] = "Hướng dẫn viên:", "MR. MINH CHIẾN"
    ws["C6"], ws["D6"] = "Ngày đi:", ngay_di
    ws["G6"], ws["I6"] = "Ngày về:", "12/07/2026"
    ws["G7"], ws["I7"] = "Biển số xe:", "50H 938.27"
    for c, v in ((1, "NO"), (2, "SALES"), (3, "TÊN KHÁCH HÀNG"), (4, "THU"), (7, "CHI"),
                 (13, "LỢI NHUẬN")):
        ws.cell(8, c, v)
    for c, v in ((4, "GIÁ BÁN"), (5, "THU KHÁC"), (6, "TỔNG THU"), (7, "LAND"), (8, "BH"),
                 (9, "PHÍ TL"), (10, "NƯỚC SUỐI"), (11, "PHÍ KHÁC"), (12, "TỔNG CHI")):
        ws.cell(9, c, v)
    r = 10
    for i, k in enumerate(khach, 1):
        ws.cell(r, 1, i); ws.cell(r, 2, k["sales"]); ws.cell(r, 3, k["ten"])
        ws.cell(r, 4, k["gia"]); ws.cell(r, 5, k.get("thu_khac"))
        ws.cell(r, 6, k["gia"] + (k.get("thu_khac") or 0))
        for c, v in ((7, k["land"]), (8, 5000), (9, 37500), (10, 15750)):
            ws.cell(r, c, v)
        tong_chi = k["land"] + 5000 + 37500 + 15750
        ws.cell(r, 12, tong_chi)
        ws.cell(r, 13, k["gia"] + (k.get("thu_khac") or 0) - tong_chi)
        r += 1
    return ws


def _sheet_ctt(wb, ma_tour, khoi_hanh, so_luong, chi):
    ws = wb.create_sheet("CTT")
    ws["A2"], ws["B2"] = "MÃ TOUR:", ma_tour
    ws["C2"], ws["D2"] = "SỐ LƯỢNG", so_luong
    ws["A3"], ws["B3"] = "KHỞI HÀNH:", khoi_hanh
    ws["G4"], ws["H4"] = "HDV: ", "MINH CHIẾN"
    for c, v in ((1, "NGÀY"), (2, "NỘI DUNG"), (3, "ĐỐI TÁC"), (4, "ĐƠN GIÁ"), (5, "SL"),
                 (6, "DIỄN GIẢI"), (7, "THÀNH TIỀN"), (8, "GHI CHÚ"), (9, "MST")):
        ws.cell(6, c, v)
    ws.cell(7, 1, "II/ CHI PHÍ:")
    ws.cell(8, 1, "A. LAND TOUR")
    r = 9
    for x in chi:
        ws.cell(r, 1, x["noi_dung"]); ws.cell(r, 2, x.get("doi_tac", ""))
        ws.cell(r, 4, x["don_gia"]); ws.cell(r, 5, x["sl"]); ws.cell(r, 6, x.get("he_so"))
        ws.cell(r, 7, x.get("thanh_tien", x["don_gia"] * x["sl"] * (x.get("he_so") or 1)))
        ws.cell(r, 8, x.get("chung_tu", "")); ws.cell(r, 9, x.get("mst", ""))
        r += 1
    ws.cell(r, 1, "TỔNG CỘNG CHI")
    ws.cell(r, 7, sum(x.get("thanh_tien", x["don_gia"] * x["sl"] * (x.get("he_so") or 1))
                      for x in chi))
    return ws


def _sheet_hdv(wb, dong, tien_ung, du):
    ws = wb.create_sheet("HDV CHI")
    for c, v in ((2, "Nội dung"), (4, "Đơn giá"), (5, "Số lượng"), (6, "Tổng chi"), (7, "Ghi chú")):
        ws.cell(4, c, v)
    r = 5
    for x in dong:
        ws.cell(r, 3, x["noi_dung"]); ws.cell(r, 4, x["don_gia"]); ws.cell(r, 5, x["sl"])
        ws.cell(r, 6, x["don_gia"] * x["sl"])
        r += 1
    ws.cell(r, 2, "TỔNG CHI"); ws.cell(r, 6, sum(x["don_gia"] * x["sl"] for x in dong))
    ws.cell(r + 1, 2, "TIỀN ỨNG: "); ws.cell(r + 1, 4, tien_ung)
    ws.cell(r + 2, 5, "Dư"); ws.cell(r + 2, 6, du)
    return ws


def _sheet_dt(wb, booking):
    ws = wb.create_sheet("DT")
    for c, v in ((1, "BookingID"), (2, "Tên người book"), (3, "Số điện thoại"), (4, "Giá tour"),
                 (5, "Số lượng khách"), (10, "TỔNG THU"), (11, "Đã đóng"), (12, "Người bán")):
        ws.cell(4, c, v)
    r = 6
    for b in booking:
        ws.cell(r, 1, b["ma"]); ws.cell(r, 2, b["ten"]); ws.cell(r, 4, b["gia"])
        ws.cell(r, 5, b["khach"]); ws.cell(r, 10, b["tong"]); ws.cell(r, 11, b["da_dong"])
        r += 1
    ws.cell(r, 1, "TỔNG CỘNG")
    ws.cell(r, 10, sum(b["tong"] for b in booking))
    ws.cell(r, 11, sum(b["da_dong"] for b in booking))
    return ws


def _tep(ma_tour="NT001.03100726", ngay_di_qt="10/07/2026", khoi_hanh_ctt="10/07/2026",
         so_khach_ghi=40, so_luong_ctt=40, so_khach_hdv=40, chi_sai_phep_nhan=False,
         so_dong_khach=40):
    """Dựng workbook bốn sheet. Mặc định KHÔNG có lỗi nào – từng phép thử tự gài lỗi của nó."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    khach = [{"sales": f"SALE {i%3}", "ten": f"KHACH {i}", "gia": 1790000, "land": 1343030,
              "thu_khac": 100000 if i % 4 == 0 else None} for i in range(1, so_dong_khach + 1)]
    _sheet_qt(wb, ma_tour, ngay_di_qt, so_khach_ghi, khach)
    chi = [{"noi_dung": "Tham quan", "doi_tac": "THÁP BÀ", "don_gia": 30000, "sl": 40,
            "chung_tu": "HD 0027533", "mst": "4200330404"},
           {"noi_dung": "LƯU TRÚ", "doi_tac": "KS SKY BEACH", "don_gia": 450000, "sl": 15,
            "he_so": 2, "chung_tu": "BILL 85454"}]
    if chi_sai_phep_nhan:
        chi[1]["thanh_tien"] = 99_000_000        # gõ tay đè lên công thức
    _sheet_ctt(wb, ma_tour, khoi_hanh_ctt, so_luong_ctt, chi)
    _sheet_hdv(wb, [{"noi_dung": "Tháp Bà", "don_gia": 30000, "sl": so_khach_hdv}],
               tien_ung=30000 * so_khach_hdv, du=0)
    # Tổng của sheet DT phải bằng tổng dòng khách ở sheet QT, kể cả phần "thu khác".
    # Bản đầu của tệp thử này quên cộng thu khác vào DT, nên "tệp sạch" vẫn lệch 1.000.000 đ và phép
    # thử đột biến bên dưới đỏ ngay. Đó đúng là việc của nó: một tệp thử sai làm mọi phép thử khác
    # mất nghĩa, vì chúng đo trên một hiện thực không tồn tại.
    tong_qt = sum(k["gia"] + (k.get("thu_khac") or 0) for k in khach)
    _sheet_dt(wb, [{"ma": "115069", "ten": "KHACH 1", "gia": 1790000, "khach": so_dong_khach,
                    "tong": tong_qt, "da_dong": tong_qt}])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _kiem(**kw):
    return QT.kiem(QT.doc_tep(_tep(**kw), "thu.xlsx"))


def _muc(kq, ten):
    return [x for x in kq["doi_chieu"] if x["muc"] == ten]


# ---------------------------------------------------------------------------------------------
# Đọc đủ bốn mặt
# ---------------------------------------------------------------------------------------------

def test_doc_du_bon_mat_cua_mot_chuyen():
    """Một bản quyết toán phải ra đủ bốn mặt. Thiếu một mặt là mất một loại câu hỏi trả lời được."""
    d = QT.doc_tep(_tep(), "thu.xlsx")
    assert len(d["dong"]) == 40, "mặt 1 – từng khách"
    assert len(d["ctt"]["dong"]) == 2, "mặt 2 – chiết tính"
    assert len(d["hdv_chi"]["dong"]) == 1, "mặt 3 – chi trên tour của HDV"
    assert len(d["dt"]["dong"]) == 1, "mặt 4 – doanh thu theo booking"


def test_chiet_tinh_giu_doi_tac_chung_tu_va_mst():
    """Đây là lý do tồn tại của mặt chiết tính: nó là bảng kê thuế đầu vào.

    Sheet QT không có cột nào chứa ba thứ này, nên bỏ mặt chiết tính đi là mất hẳn khả năng đối
    chiếu tour với tờ khai thuế – mất im lặng, vì tổng tiền vẫn đúng.
    """
    kq = _kiem()
    tq = [x for x in kq["chiet_tinh"] if "Tham quan" in x["noi_dung"]][0]
    assert tq["doi_tac"] == "THÁP BÀ"
    assert tq["so_chung_tu"] == "HD 0027533"
    assert tq["mst_ncc"] == "4200330404"
    assert kq["so_chung_tu_co_mst"] >= 1


def test_cot_tong_chi_khong_bi_cong_them_mot_lan_nua():
    """Khối CHI là các cột GIỮA 'CHI' và 'TỔNG CHI' – không gồm chính cột tổng.

    Gộp cả cột TỔNG CHI vào là mỗi khoản đếm hai lần: giá vốn gấp đôi, biên lãi âm ở mọi chuyến, và
    vì mọi chuyến đều sai như nhau nên nhìn qua bảng vẫn "hợp lý".
    """
    kq = _kiem()
    assert kq["cot_chi"] == ["LAND", "BH", "PHÍ TL", "NƯỚC SUỐI", "PHÍ KHÁC"]
    assert "TỔNG CHI" not in kq["cot_chi"]
    assert "LỢI NHUẬN" not in kq["cot_chi"]
    mot_dong = kq["dong"][0]
    cong = sum(k["so_tien"] for k in mot_dong["khoan_chi"] if k["so_tien"])
    assert abs(cong - mot_dong["tong_chi"]) < 1


def test_nhan_chi_chua_xac_nhan_nghia_thi_khong_duoc_doan_ma():
    """'PHÍ TL' phải nằm ở hàng đợi chờ người xếp, không được tự xếp thành phí tham quan.

    Bản nháp đầu ngày 10/9 xếp nó thành phi_tham_quan vì đọc tắt. Đối chiếu chiết tính của tệp thật
    thì sai: 1.500.000 của cột ấy là HDV cộng ăn nội bộ, còn phí tham quan nằm trong khối LAND.
    Xếp nhầm một nhãn thì mọi báo cáo cộng theo khoản đều sai mà tổng vẫn cân.
    """
    from app.models.quyet_toan import MA_KHOAN
    assert "PHI TL" not in MA_KHOAN, "PHÍ TL chưa xác nhận nghĩa – không được có mã"
    kq = _kiem()
    assert "PHÍ TL" in kq["nhan_chi_chua_xep_ma"]
    phi_tl = [k for k in kq["dong"][0]["khoan_chi"] if k["nhan"] == "PHÍ TL"][0]
    assert phi_tl["ma_khoan"] == "", "nhãn chưa xếp mã phải để TRỐNG, không rơi vào phí khác"


# ---------------------------------------------------------------------------------------------
# Bắt ba chỗ vênh đã gặp thật
# ---------------------------------------------------------------------------------------------

def test_bat_ngay_khoi_hanh_lech_giua_cac_sheet():
    """Ngày khởi hành quyết định chuyến thuộc kỳ nào – lệch vài ngày ở chuyến cuối tháng là lệch kỳ."""
    kq = _kiem(ngay_di_qt="07/07/2026")
    x = _muc(kq, "ngay_khoi_hanh")
    assert x, "sheet QT ghi 07/07 trong khi mã tour và CTT nói 10/07 – phải kêu"
    assert x[0]["nang"] is True
    assert x[0]["nguon"]["mã tour"] == "2026-07-10"
    assert x[0]["nguon"]["sheet QT"] == "2026-07-07"


def test_bat_so_khach_lech_giua_cac_nguon():
    kq = _kiem(so_khach_ghi=44, so_luong_ctt=42, so_dong_khach=42)
    x = _muc(kq, "so_khach")
    assert x, "ô Số khách ghi 44 mà bảng chỉ có 42 dòng – phải kêu"
    assert x[0]["nguon"]["sheet QT"] == 44
    assert x[0]["nguon"]["số dòng khách"] == 42


def test_bat_hdv_chi_nhieu_hon_chiet_tinh():
    """Khoản chênh này là tiền đã ra khỏi công ty mà chưa vào giá vốn.

    Không mặt nào khác thấy được: sheet QT và CTT đều cân, sheet DT nói về thu. Chỉ khi đặt bảng chi
    thật của HDV cạnh chiết tính mới lộ ra – và nó lộ ra ở mọi chuyến, không riêng chuyến nào.
    """
    kq = _kiem(so_khach_hdv=44, so_luong_ctt=40)
    x = _muc(kq, "hdv_chi_khac_chiet_tinh")
    assert x, "HDV tính vé cho 44 khách, chiết tính tính cho 40 – phải kêu"
    assert x[0]["nguon"]["chênh"] == 120000


def test_bat_chiet_tinh_go_tay_de_len_phep_nhan():
    """Thành tiền phải bằng đơn giá × số lượng × hệ số. Đúng 20/20 dòng trên tệp thật.

    Cột 'DIỄN GIẢI' của tệp chính là hệ số (số đêm lưu trú, số bữa ăn) – tên cột không nói ra điều
    đó, nên bộ đọc phải kiểm bằng phép nhân chứ không tin tên cột.
    """
    kq = _kiem(chi_sai_phep_nhan=True)
    assert _muc(kq, "chiet_tinh_sai_phep_nhan"), "một dòng bị gõ tay đè công thức – phải kêu"
    assert kq["so_dong_chiet_tinh_lech"] == 1


# ---------------------------------------------------------------------------------------------
# Phép thử đột biến: tệp SẠCH thì bộ đối chiếu phải IM
# ---------------------------------------------------------------------------------------------

def test_tong_tien_khong_mang_duoi_float_khi_gia_von_chia_theo_dau_khach():
    """Cột tiền phải sạch đuôi float, vì bản đối chiếu sau này so bằng dấu bằng.

    Tệp Nha Trang thật: sheet QT phân bổ LAND theo đầu khách bằng phép chia không hết
    (1.343.030,3030… × 33 người lớn). Cộng 42 dòng lại được 50.649.999,99999988 trong khi ô
    TỔNG CỘNG CHI của chính tệp ấy ghi 50.650.000. Chênh 0,00000012đ không đủ lớn để ai đi sửa,
    nhưng đủ để mọi câu "khớp tuyệt đối" về sau không bao giờ còn đúng.
    """
    # Sáu khách, mỗi khách gánh đúng 1/6 của 1.000.000. Cộng sáu số ấy lại bằng float ra
    # 999.999,9999999999 – cùng một kiểu trôi với tệp Nha Trang thật, chỉ nhỏ hơn cho gọn.
    # Các ô chi khác để 0 để phép cộng của tệp thử không tự khử mất chỗ trôi cần đo.
    #
    # CỘNG DỒN BẰNG `+=`, KHÔNG DÙNG `sum()`. Hai lý do, và lý do thứ hai đã làm đỏ CI thật:
    #
    #   1. Máy chủ cộng bằng `+=` (quyet_toan_chi_tiet.py: `tong_chi += d["tong_chi"]` trong vòng
    #      lặp từng dòng khách), và bảng tính Excel cũng cộng dồn từng ô một. Phép tự kiểm phải
    #      tái hiện đúng cách cộng của chỗ mình đang canh, không phải một cách cộng khác.
    #
    #   2. Từ Python 3.12, `sum()` trên số thực cộng có BÙ SAI SỐ (Neumaier), nên
    #      `sum(1000000/6 for _ in range(6))` ra đúng 1000000.0 – hết trôi. Máy người viết chạy
    #      3.11 thì dòng này xanh; CI chạy 3.12 thì phép tự kiểm kêu "không còn tái hiện được chỗ
    #      trôi" và cả bộ đứng lại ở đây (tests/run_all.sh có `set -e`, đỏ một tệp là dừng, mọi
    #      tệp xếp sau không chạy nữa). Đúng việc phép tự kiểm phải làm – nó từ chối chạy một
    #      khẳng định đã mất ý nghĩa – nhưng chỗ phải sửa là CÁCH CỘNG ở đây, không phải mã máy
    #      chủ. `+=` trôi y hệt nhau trên cả 3.11 lẫn 3.12.
    n, tong_that = 6, 1000000
    mot_phan = tong_that / n
    cong_don = 0.0
    for _ in range(n):
        cong_don += mot_phan
    assert cong_don != float(tong_that), \
        "tệp thử không còn tái hiện được chỗ trôi float – chọn lại n hoặc tổng"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("QT")
    ws["C4"], ws["D4"] = "Mã tour:", "XX001.03100726"
    ws["C6"], ws["D6"] = "Ngày đi:", "10/07/2026"
    for c, v in ((1, "NO"), (3, "TÊN KHÁCH HÀNG"), (4, "THU"), (7, "CHI"), (13, "LỢI NHUẬN")):
        ws.cell(8, c, v)
    for c, v in ((4, "GIÁ BÁN"), (5, "THU KHÁC"), (6, "TỔNG THU"), (7, "LAND"), (8, "BH"),
                 (9, "PHÍ TL"), (10, "NƯỚC SUỐI"), (11, "PHÍ KHÁC"), (12, "TỔNG CHI")):
        ws.cell(9, c, v)
    for i in range(n):
        r = 10 + i
        ws.cell(r, 1, i + 1); ws.cell(r, 3, f"KHACH {i + 1}")
        ws.cell(r, 4, 250000); ws.cell(r, 6, 250000)
        ws.cell(r, 7, mot_phan)
        for c in (8, 9, 10, 11):
            ws.cell(r, c, 0)
        ws.cell(r, 12, mot_phan)
        ws.cell(r, 13, 250000 - mot_phan)
    b = io.BytesIO(); wb.save(b)

    kq = QT.kiem(QT.doc_tep(b.getvalue(), "t.xlsx"))
    assert kq["tong_chi"] == tong_that, f"giá vốn còn đuôi float: {kq['tong_chi']!r}"
    assert kq["tong_thu"] == 250000 * n, f"doanh thu còn đuôi float: {kq['tong_thu']!r}"
    assert kq["loi_nhuan"] == 250000 * n - tong_that, \
        f"lợi nhuận còn đuôi float: {kq['loi_nhuan']!r}"


def test_tep_sach_thi_khong_kieu_gi_ca():
    """Một bộ kiểm kêu ở mọi tệp thì sau vài lần không ai đọc nữa – và lúc ấy nó vô dụng hơn là không có.

    Phép thử này là thứ giữ cho ba phép thử trên có nghĩa: thiếu nó, một hàm 'luôn luôn kêu' vẫn
    qua được cả bộ.
    """
    kq = _kiem()
    assert kq["doi_chieu"] == [], f"tệp sạch mà vẫn kêu: {kq['doi_chieu']}"
    assert kq["so_dong_lech"] == 0
    assert kq["so_dong_chiet_tinh_lech"] == 0


def test_gia_ban_lay_muc_pho_bien_khong_lay_binh_quan():
    """Bình quân của 33 người lớn 1.790.000 và 7 trẻ em 1.500.000 ra 1.739.250 – một con số không có
    trong bảng giá nào và không ai đối chiếu được. Mức phổ biến nhất thì tra được ngay."""
    d = QT.doc_tep(_tep(), "thu.xlsx")
    for i in range(30, 40):
        d["dong"][i]["gia_ban"] = 1500000
    kq = QT.kiem(d)
    assert kq["gia_ban"] == 1790000
    assert kq["nhieu_muc_gia"] is True


def test_ngay_tu_ma_tour_la_nguon_doc_lap():
    """Sáu số cuối mã tour là nguồn ngày duy nhất KHÔNG do người gõ vào ô ngày.

    Nhờ nó mà lỗi gõ ngày ở sheet QT bị bắt. Bỏ hàm này đi thì hai ô ngày còn lại có thể cùng sai
    theo một hướng mà không gì phát hiện được.
    """
    assert QT.ngay_tu_ma("NT001.03100726") == date(2026, 7, 10)
    assert QT.ngay_tu_ma("MICEUK6N6D.06200726") == date(2026, 7, 20)
    assert QT.ngay_tu_ma("KHONG-CO-DAU-CHAM") is None
