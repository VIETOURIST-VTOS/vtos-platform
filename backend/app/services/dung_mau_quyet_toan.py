# -*- coding: utf-8 -*-
"""Dựng MẪU QUYẾT TOÁN TOUR trống – hai hình thức, sinh ra từ chính danh mục của hệ thống.

VÌ SAO MẪU TRỐNG PHẢI DO PHẦN MỀM SINH RA, KHÔNG PHẢI MỘT TỆP NẰM SẴN

Sheet KHOẢN MỤC trong mẫu là bản sao của app/services/khoan_muc_chi.py. Nếu mẫu là một tệp tĩnh nằm
trong kho, thì mỗi lần danh mục thêm một mã là mẫu cũ đi một bước – và đến lúc nhân viên nạp tệp lên,
một phần dòng mang mã "không có trong danh mục" mà họ không hiểu vì sao, vì họ điền đúng cái ô chọn
mà mẫu đưa cho.

Sinh tại chỗ thì hai thứ ấy không thể lệch: cùng một nguồn, cùng một lần chạy.

HAI HÌNH THỨC DÙNG CHUNG MỘT BỘ DỰNG

Khác nhau ở cờ NN chứ không phải hai tệp mã chép đôi. Chép đôi thì lần sau sửa một phép kiểm sẽ sửa ở
một bản và quên bản kia, rồi hai mẫu âm thầm trôi xa nhau – đúng kiểu hỏng mà cả bộ mẫu này sinh ra
để chống.
"""
from app.services import khoan_muc_chi as KM

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

NAVY, XANH, VANG, XAM, DO, LUC = "1F3864", "DDEBF7", "FFF2CC", "F2F2F2", "FFC7CE", "E2EFDA"
F = "Arial"
mong = Side(style="thin", color="B0B7C3")
VIEN = Border(left=mong, right=mong, top=mong, bottom=mong)

# Hai hình thức dùng CHUNG một bộ dựng, khác nhau ở cờ NN (nước ngoài) chứ không phải ở hai tệp mã
# chép đôi. Chép đôi thì lần sau sửa một phép kiểm sẽ sửa ở một bản và quên bản kia – và hai mẫu âm
# thầm trôi xa nhau, đúng kiểu hỏng mà cả bộ mẫu này sinh ra để chống.
wb = None


def sheet(ten):
    ws = wb.create_sheet(ten)
    ws.sheet_view.showGridLines = False
    return ws


def tieu_de(ws, text, rong=8):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=rong)
    c = ws.cell(1, 1, text)
    c.font = Font(name=F, bold=True, size=13, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 26


def dau_bang(ws, hang, cot, ghi_chu=None):
    """cot = [(nhãn, độ rộng, 'nhap'|'ct'|'tt')]"""
    for i, (nhan, rong, loai) in enumerate(cot, start=1):
        c = ws.cell(hang, i, nhan)
        c.font = Font(name=F, bold=True, size=9, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = VIEN
        ws.column_dimensions[get_column_letter(i)].width = rong
        if ghi_chu and nhan in ghi_chu:
            c.comment = Comment(ghi_chu[nhan], "Mẫu chuẩn VTOS")
    ws.row_dimensions[hang].height = 34


def to_mau(ws, hang_dau, hang_cuoi, cot):
    """Tô nền theo loại ô: nhap = vàng (người gõ), ct = xanh (công thức), tt = xám (tham chiếu)."""
    mau = {"nhap": VANG, "ct": XANH, "tt": XAM}
    for r in range(hang_dau, hang_cuoi + 1):
        for i, (_, _, loai) in enumerate(cot, start=1):
            c = ws.cell(r, i)
            c.fill = PatternFill("solid", fgColor=mau[loai])
            c.border = VIEN
            c.font = Font(name=F, size=9)


def tien(ws, cot_chu, r1, r2, dinh_dang='#,##0'):
    for r in range(r1, r2 + 1):
        ws[f"{cot_chu}{r}"].number_format = dinh_dang




def dung(NN: bool, ten_tep: str | None = None) -> bytes:
    """NN=True: tour nước ngoài. NN=False: tour trong nước.

    KHÁC NHAU Ở ĐÂU

        ngoại tệ      : chỉ tour nước ngoài có (tỷ giá, số tiền gốc, ngày tỷ giá)
        chi theo khách: chỉ tour nước ngoài (vé quốc tế và phí lãnh sự quán mỗi khách một giá)
        giấy tờ khách : trong nước dùng CCCD, nước ngoài dùng hộ chiếu
        tỷ lệ em bé   : trong nước 10%, nước ngoài 30% – hai con số khác nhau, đọc từ tham số VTOS

    GIỐNG NHAU Ở ĐÂU: mọi thứ còn lại. Dòng khách, dòng doanh thu có VAT và có dòng âm theo biên bản
    thanh lý, chiết tính và thực chi cùng một dòng, phương tiện từng chặng, HDV ứng–chi–vượt, và
    nguyên tắc máy cộng người không gõ tổng.
    """
    global wb
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    # =============================================================================================
    # 0. HƯỚNG DẪN
    # =============================================================================================
    hd = sheet("HƯỚNG DẪN")
    tieu_de(hd, f"MẪU QUYẾT TOÁN TOUR {'NƯỚC NGOÀI' if NN else 'TRONG NƯỚC'} – CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS", 7)
    hd.column_dimensions["A"].width = 4
    hd.column_dimensions["B"].width = 34
    hd.column_dimensions["C"].width = 96

    dong = [
        ("", "", ""),
        ("MUC", "SÁU NGUYÊN TẮC CỦA MẪU NÀY", ""),
        ("1", "Máy cộng, người không gõ tổng",
         "Mọi ô tổng là công thức. Biểu nhập không có ô nào cho người gõ tổng vào. Đo trên tệp thật: một "
         "nhóm chi ghi tổng 3.990.000 trong khi năm dòng của chính nhóm ấy cộng lại được 4.200.000 – "
         "thiếu 210.000 đ, và con số sai ấy đi thẳng vào lợi nhuận mà mọi tầng vẫn cân."),
        ("2", "Rỗng khác không",
         "Ô tiền để trống nghĩa là CHƯA AI NHẬP, không phải 0 đồng. Đừng gõ 0 để 'cho đẹp bảng' – một ô 0 "
         "giả làm chuyến báo lãi 100%."),
        ("3", "Ngoại tệ phải có tỷ giá VÀ ngày tỷ giá" if NN else "Thuế suất ghi trên TỪNG DÒNG",
         ("Tỷ giá lấy tại NGÀY CHI THẬT. Trong một tệp thật có hai tỷ giá GBP khác nhau (36.000 và "
          "35.944); riêng trên một khoản land, 56 đồng chênh ấy là 1.667.155 đ. Không ghi ngày thì "
          "không phân xử được.") if NN else
         ("Một chuyến có nhiều thuế suất cùng lúc: mẫu đoàn Đà Lạt có 8% cho nhà hàng và lưu trú, 0% "
          "cho banner và ăn nội bộ. Ghi ở cuối bảng một con số chung là không dựng lại được bảng kê "
          "thuế GTGT đầu vào.")),
        ("4", "Quy tắc phân bổ phải KHAI, không giấu trong công thức",
         "Mỗi dòng chi mang theo cách chia của nó. Khi ai hỏi 'vì sao khách này chịu 15.750 mà khách kia "
         "không chịu' thì có câu trả lời tra được, thay vì phải mở lại tệp gốc."),
        ("5", "Ngày sinh thu ở khâu ĐĂNG KÝ, không phải ở quyết toán",
         "Quy tắc giá theo tuổi chỉ kiểm được khi có ngày sinh. Đến lúc quyết toán thì khách đã đi rồi – "
         "hỏi tuổi lúc ấy là hỏi để hợp thức hoá, không phải để tính giá."),
        ("6", "Số âm được phép, nhưng phải có căn cứ",
         "Hoàn tiền và thanh lý hợp đồng là số âm bình thường. Bắt buộc ghi số hiệu chứng từ – không có thì "
         "không phân biệt được với gõ nhầm dấu trừ."),
        ("", "", ""),
        ("MUC", "MÀU Ô", ""),
        ("", "Nền VÀNG", "Ô người nhập. Chỉ gõ vào đây."),
        ("", "Nền XANH", "Ô công thức. ĐỪNG gõ đè – gõ đè là mất phép kiểm."),
        ("", "Nền XÁM", "Ô tham chiếu, lấy tự động từ sheet khác."),
        ("", "", ""),
        ("MUC", "THỨ TỰ LÀM", ""),
        ("B1", "THÔNG TIN", "Điền đầu bảng, tỷ giá và ba tham số giá trẻ em."),
        ("B2", "KHÁCH", "Mỗi người ngồi trên chuyến một dòng – kể cả trưởng đoàn, nội bộ, khách của đại lý."),
        ("B3", "THU", "Dòng doanh thu. Tour lẻ: mỗi khách một dòng. Tour đoàn: mỗi khoản hợp đồng một dòng."),
        ("B4", "CHI", "Chiết tính và thực chi NẰM CÙNG MỘT DÒNG, để so được từng khoản."),
    ] + ([("B5", "CHI THEO KHÁCH",
           "Vé máy bay, visa, dịch thuật – những khoản mỗi khách một giá, không chia.")] if NN else []) + [
        (f"B{6 if NN else 5}", "PHƯƠNG TIỆN", "Từng chặng: ô tô, máy bay, tàu hoả, tàu thuỷ."),
        (f"B{7 if NN else 6}", "HDV", "Ứng bao nhiêu, chi những gì, vượt chiết tính bao nhiêu, ai duyệt."),
        (f"B{8 if NN else 7}", "LÃI LỖ", "Tự cộng. Không gõ gì ở đây."),
        (f"B{9 if NN else 8}", "ĐỐI CHIẾU",
         f"{'Chín' if NN else 'Tám'} phép kiểm tự chạy. Còn dòng LỆCH thì tờ chưa xong."),
    ]
    r = 3
    for a, b, c in dong:
        if a == "MUC":
            hd.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
            cc = hd.cell(r, 2, b)
            cc.font = Font(name=F, bold=True, size=11, color=NAVY)
            cc.fill = PatternFill("solid", fgColor=LUC)
        else:
            hd.cell(r, 1, a).font = Font(name=F, bold=True, size=9, color=NAVY)
            hd.cell(r, 2, b).font = Font(name=F, bold=True, size=10)
            cc = hd.cell(r, 3, c)
            cc.font = Font(name=F, size=9)
            cc.alignment = Alignment(wrap_text=True, vertical="top")
            if c:
                hd.row_dimensions[r].height = 30
        r += 1
    hd["B12"].fill = PatternFill("solid", fgColor=VANG)
    hd["B13"].fill = PatternFill("solid", fgColor=XANH)
    hd["B14"].fill = PatternFill("solid", fgColor=XAM)

    # =============================================================================================
    # 1. THÔNG TIN
    # =============================================================================================
    ti = sheet("THÔNG TIN")
    tieu_de(ti, "THÔNG TIN CHUYẾN – điền trước tiên", 5)
    ti.column_dimensions["A"].width = 30
    ti.column_dimensions["B"].width = 26
    ti.column_dimensions["C"].width = 62

    muc = [
        ("Mã tour", "", "Bắt buộc. Phải GIỐNG NHAU ở mọi sheet – tệp thật từng có hai mã khác nhau trong một tệp."),
        ("Tên tour", "", ""),
        ("Số khách", "", "Số người NGỒI TRÊN CHUYẾN, kể cả miễn phí và nội bộ. Phép kiểm 1 đối chiếu với số dòng ở sheet KHÁCH."),
        ("Hình thức", "nuoc_ngoai" if NN else "trong_nuoc", "Mẫu này dành riêng cho hình thức trên – "
         "đừng đổi ô này; tour hình thức kia có mẫu riêng, vì tỷ lệ giá và cột ngoại tệ khác nhau."),
        ("Ngày khởi hành", "", "Quyết định tuổi của khách và kỳ kế toán của chuyến."),
        ("Ngày kết thúc", "", ""),
        ("Điều hành", "", ""),
        ("Sale phụ trách", "", ""),
        ("Hướng dẫn viên / TL", "", ""),
        ("", "", ""),
    ] + ([("TỶ GIÁ", "", "Tỷ giá của NGÀY CHI THẬT. Mỗi dòng chi vẫn khai riêng ngày tỷ giá của nó."),
          ("USD", "", ""), ("EUR", "", ""), ("GBP", "", ""), ("Khác (ghi rõ)", "", ""),
          ("", "", "")] if NN else []) + [
        ("QUY TẮC GIÁ THEO TUỔI", "", "Chủ tịch chốt 10/9/2026, sửa tỷ lệ 11/9/2026. Ghi ở đây để người "
                                      "lập tờ biết quy tắc đang áp. Mẫu này KHÔNG tự tính giá chuẩn – "
                                      "VTOS mới là nơi đối chiếu giá bán với quy tắc."),
        ("Dưới … tuổi là em bé", 2, ""),
        ("Dưới … tuổi là trẻ em", 12, ""),
        ("Giá em bé bằng … giá người lớn", 0.3 if NN else 0.1,
         "Chủ tịch chốt 11/9/2026. Hai hình thức hai tỷ lệ: nước ngoài 30%, trong nước 10% – vì tour "
         "nước ngoài có vé quốc tế, visa và bảo hiểm mà trẻ nhỏ vẫn trả gần bằng người lớn."),
        ("Giá trẻ em bằng … giá người lớn", 0.9,
         "Đo trên mẫu thật: SIN/MAL 89,99% – UK 88,67% – Nha Trang 83,80%."),
        ("Giá người lớn chuẩn của chuyến", "", "Mức giá gốc của chuyến, để đối chiếu."),
    ]
    r = 3
    for a, b, c in muc:
        ca = ti.cell(r, 1, a)
        ca.font = Font(name=F, bold=bool(a and a.isupper()), size=10,
                       color=NAVY if (a and a.isupper()) else "000000")
        if a and not a.isupper():
            cb = ti.cell(r, 2, b if b != "" else None)
            cb.fill = PatternFill("solid", fgColor=VANG)
            cb.border = VIEN
            cb.font = Font(name=F, size=10)
        cc = ti.cell(r, 3, c)
        cc.font = Font(name=F, size=9, italic=True, color="555555")
        cc.alignment = Alignment(wrap_text=True, vertical="center")
        if c:
            ti.row_dimensions[r].height = 28
        r += 1
    # Hai dòng tỷ lệ và một dòng tiền. Bỏ dòng "Pháp nhân xuất hoá đơn" nên mọi dòng từ đó xuống lùi
    # lên một hàng; số hàng dưới đây đếm lại từ danh sách `muc` ở trên, không chép lại từ bản cũ.
    # Số hàng KHÔNG viết cứng: mẫu trong nước không có khối tỷ giá nên mọi hàng dưới đó lùi lên sáu
    # dòng. Đếm lại từ chính danh sách `muc` vừa dựng – bản đầu viết cứng và lệch đúng một dòng vì hai
    # hàng tiêu đề chen vào, phép tính vẫn chạy mà ra sai số.
    _hang = {a: i for i, (a, _b, _c) in enumerate(muc, start=3) if a}
    SO_KHACH = f"'THÔNG TIN'!$B${_hang['Số khách']}"
    NGAY_DI = f"'THÔNG TIN'!$B${_hang['Ngày khởi hành']}"
    ti[f"B{_hang['Giá em bé bằng … giá người lớn']}"].number_format = "0%"
    ti[f"B{_hang['Giá trẻ em bằng … giá người lớn']}"].number_format = "0%"
    ti[f"B{_hang['Giá người lớn chuẩn của chuyến']}"].number_format = "#,##0"

    # =============================================================================================
    # 2. KHÁCH
    # =============================================================================================
    kh = sheet("KHÁCH")
    tieu_de(kh, "DÒNG KHÁCH – mỗi người ngồi trên chuyến một dòng, kể cả người không trả tiền", 14)
    cot_kh = [("STT", 6, "nhap"), ("Nhóm khách", 14, "nhap"), ("Họ và tên", 28, "nhap"),
              ("Giới tính", 8, "nhap"), ("Ngày sinh", 12, "nhap"), ("Điện thoại", 14, "nhap"),
              ("Email", 24, "nhap"), ("Sale", 14, "nhap"), ("Giá bán", 15, "nhap"),
              ("Note", 30, "nhap"),
              ("Số hộ chiếu" if NN else "CCCD", 15, "nhap"),
              ("Mã đặt chỗ", 13, "nhap"), ("Mã booking", 16, "nhap")]
    gc_kh = {
        "Nhóm khách": "tra_tien / mien_phi / noi_bo / dai_ly.\n\nAI TRẢ TIỀN. Khách của đại lý và người nội bộ vẫn ngồi ghế và vẫn ăn suất ăn, nhưng không mang doanh thu – nên vẫn phải ghi vào đây.",
        "Ngày sinh": "Thu ở khâu ĐĂNG KÝ, không phải ở quyết toán.\n\nCần cho vé máy bay, visa, bảo hiểm, và cho quy tắc giá theo tuổi (VTOS kiểm, mẫu này chỉ ghi).",
        "Điện thoại": "Số liên hệ trực tiếp của khách – dùng khi có sự cố trên đường.",
        "Note": "Ghi chú tự do: phụ thu phòng đơn, khuyến mãi đã duyệt, khách tự lo vé, yêu cầu ăn kiêng…",
        "Mã đặt chỗ": "PNR của HÃNG BAY (ví dụ KCLWRD). Không phải mã phiếu đặt của công ty.",
        "Mã booking": "Mã PHIẾU ĐẶT của khách này trong hệ thống – nhận mã VTOS, số Vietrip (cột "
                      "'BookingID' trên báo cáo doanh thu), hoặc số id.\n\nBẮT BUỘC khi chuyến có "
                      "từ HAI phiếu đặt trở lên. Đo trên tệp Nha Trang thật: 42 khách thuộc 9 phiếu "
                      "đặt của 10 sale; thiếu ô này thì doanh thu chạy sang sale khác và số 'đã "
                      "đóng' của khách sang theo, mà tổng chuyến vẫn đúng nên không ai thấy.",
    }
    _k = {nhan: get_column_letter(i) for i, (nhan, _w, _kk) in enumerate(cot_kh, start=1)}
    dau_bang(kh, 2, cot_kh, gc_kh)
    K1, K2 = 3, 62
    to_mau(kh, K1, K2, cot_kh)
    for r in range(K1, K2 + 1):
        kh[f"E{r}"].number_format = "dd/mm/yyyy"
        # Điện thoại để dạng CHỮ: số 0 đứng đầu của số điện thoại Việt Nam biến mất nếu Excel đọc nó
        # thành số, và một số điện thoại mất số 0 đầu thì gọi không được.
        kh[f"F{r}"].number_format = "@"
    tien(kh, "I", K1, K2)
    kh.cell(K2 + 1, 1, "CỘNG").font = Font(name=F, bold=True, size=10)
    cc = kh.cell(K2 + 1, 9, f"=SUM(I{K1}:I{K2})")
    cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
    cc.fill = PatternFill("solid", fgColor=XANH)
    # VÍ DỤ ĐI VÀO CHÚ THÍCH CỦA TỪNG CỘT, KHÔNG ĐI VÀO MỘT DÒNG DƯỚI BẢNG
    #
    # Bản đầu để một dòng ví dụ ngay dưới dòng CỘNG, kèm chữ "XOÁ DÒNG NÀY TRƯỚC KHI DÙNG". Hai chỗ
    # hỏng cùng lúc: bộ đọc không nhận ra dòng CỘNG nên đọc luôn dòng ví dụ, và một hàng khách tên
    # NGUYEN VAN A trị giá 1.790.000 đ vào thẳng hệ thống khi nhân viên tải mẫu trống lên chưa điền
    # gì. Bộ đọc đã được vá (xem _la_dong_dung trong nap_mau_quyet_toan.py), nhưng một mẫu chỉ an
    # toàn nhờ người dùng NHỚ XOÁ thì sớm muộn cũng có một lần không nhớ.
    #
    # Ví dụ nằm trong chú thích thì đi theo đúng cột nó giải thích, hiện ra khi rê chuột vào chỗ
    # đang gõ, và không bao giờ trở thành dữ liệu.
    vi_du = {"STT": "1", "Nhóm khách": "tra_tien", "Họ và tên": "NGUYEN VAN A", "Giới tính": "M",
             "Ngày sinh": "21/04/1953", "Điện thoại": "0901234567", "Email": "a@vidu.com",
             "Sale": "PHƯƠNG NHI", "Giá bán": "53.900.000" if NN else "1.790.000",
             "Note": "Phụ thu phòng đơn",
             ("Số hộ chiếu" if NN else "CCCD"): "C1234567" if NN else "079xxxxxxxxx",
             "Mã đặt chỗ": "KCLWRD" if NN else "NT-042"}
    for i, (nhan, _, _) in enumerate(cot_kh, start=1):
        if nhan not in vi_du:
            continue
        c = kh.cell(2, i)
        cu = c.comment.text if c.comment else ""
        c.comment = Comment((cu + "\n\n" if cu else "") + f"Ví dụ: {vi_du[nhan]}", "Mẫu chuẩn VTOS")
    kh.freeze_panes = "C3"

    # =============================================================================================
    # 3. THU
    # =============================================================================================
    th = sheet("THU")
    tieu_de(th, "DÒNG DOANH THU – tour lẻ ghi theo khách, tour đoàn ghi theo khoản hợp đồng", 11)
    cot_th = [("Loại", 13, "nhap"), ("Nội dung", 34, "nhap"), ("Khách (STT)", 11, "nhap"),
              ("Mã booking", 16, "nhap"),
              ("Đối tượng", 11, "nhap"), ("Đơn giá trước thuế", 16, "nhap"), ("Số lượng", 9, "nhap"),
              ("Thành tiền trước thuế", 17, "ct"), ("Thuế suất", 10, "nhap"), ("Tiền thuế", 14, "ct"),
              ("TỔNG THU", 15, "ct"), ("Chứng từ (bắt buộc nếu ÂM)", 26, "nhap")]
    _t = {nhan: get_column_letter(i) for i, (nhan, _w, _k) in enumerate(cot_th, start=1)}
    gc_th = {
        "Loại": "hop_dong / thanh_ly / phu_thu / charge_huy / thu_khac",
        "Mã booking": "Phiếu đặt mà khoản thu này thuộc về. Cùng cách ghi với sheet KHÁCH.\n\nTour đoàn bán theo hợp đồng thì mọi dòng cùng một mã; tour lẻ thì mỗi phiếu đặt một mã.",
        "Thuế suất": "Bán cho doanh nghiệp thì có VAT (0,08). Bán lẻ thì để trống.",
        "Chứng từ (bắt buộc nếu ÂM)": "Dòng ÂM (hoàn tiền, thanh lý) PHẢI ghi số hiệu biên bản.\nKhông có thì không phân biệt được với gõ nhầm dấu trừ.",
    }
    dau_bang(th, 2, cot_th, gc_th)
    T1, T2 = 3, 32
    to_mau(th, T1, T2, cot_th)
    DG_T, SL_T = _t["Đơn giá trước thuế"], _t["Số lượng"]
    TRUOC_T, TS_T, THUE_T, TONG_T = (_t["Thành tiền trước thuế"], _t["Thuế suất"],
                                     _t["Tiền thuế"], _t["TỔNG THU"])
    for r in range(T1, T2 + 1):
        th[f"{TRUOC_T}{r}"] = (f'=IF(OR(${DG_T}{r}="",${SL_T}{r}=""),"",'
                               f'ROUND(${DG_T}{r}*${SL_T}{r},0))')
        th[f"{THUE_T}{r}"] = (f'=IF(OR(${TRUOC_T}{r}="",${TS_T}{r}=""),"",'
                              f'ROUND(${TRUOC_T}{r}*${TS_T}{r},0))')
        th[f"{TONG_T}{r}"] = (f'=IF(${TRUOC_T}{r}="","",'
                              f'${TRUOC_T}{r}+IF(${THUE_T}{r}="",0,${THUE_T}{r}))')
        th[f"{TS_T}{r}"].number_format = "0%"
    for nhan in ("Đơn giá trước thuế", "Thành tiền trước thuế", "Tiền thuế", "TỔNG THU"):
        tien(th, _t[nhan], T1, T2)
    th.cell(T2 + 1, 2, "CỘNG").font = Font(name=F, bold=True, size=10)
    for nhan in ("Thành tiền trước thuế", "Tiền thuế", "TỔNG THU"):
        c = _t[nhan]; i = [x[0] for x in cot_th].index(nhan) + 1
        cc = th.cell(T2 + 1, i, f"=SUM({c}{T1}:{c}{T2})")
        cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
        cc.fill = PatternFill("solid", fgColor=XANH)
    th.freeze_panes = "C3"

    # =============================================================================================
    # 3b. DANH MỤC KHOẢN MỤC – nguồn của ô chọn ở sheet CHI
    # =============================================================================================
    # Danh mục này là BẢN SAO của app/services/khoan_muc_chi.py trong VTOS, dựng TỰ ĐỘNG khi tạo tệp.
    # Chép tay sang Excel thì hai nơi trôi xa nhau, và đến lúc nạp tệp vào hệ thống thì một phần số
    # dòng mang mã không tồn tại.
    dm = sheet("KHOẢN MỤC")
    tieu_de(dm, "DANH MỤC KHOẢN MỤC CHI PHÍ – chọn ở sheet CHI, đừng gõ tay tên khoản", 6)
    dau_bang(dm, 2, [("Mã", 24, "tt"), ("Tên khoản mục", 42, "tt"), ("Nhóm", 26, "tt"),
                     ("Đối tượng", 13, "tt"), ("Quy tắc phân bổ", 20, "tt"),
                     ("Đích danh?", 11, "tt")])
    _km = KM.danh_sach("nuoc_ngoai" if NN else "trong_nuoc")
    for _i, k in enumerate(_km, start=3):
        for _j, v in enumerate([k["ma"], k["ten"], k["ten_nhom"], k["doi_tuong"],
                                k["quy_tac_phan_bo"], "x" if k["dich_danh"] else ""], start=1):
            c = dm.cell(_i, _j, v)
            c.font = Font(name=F, size=9)
            c.fill = PatternFill("solid", fgColor=XAM)
            c.border = VIEN
    _km_cuoi = 2 + len(_km)
    dm.cell(_km_cuoi + 2, 1,
            "Mã kết thúc bằng '_khac' là đường thoát khi chưa có mã riêng. Dùng được, nhưng phải ghi "
            "rõ ở cột Nội dung – nhiều tiền rơi vào 'khác' là dấu hiệu danh mục còn thiếu mã."
            ).font = Font(name=F, size=9, italic=True, color="555555")
    dm.freeze_panes = "A3"

    # =============================================================================================
    # 4. CHI
    # =============================================================================================
    ch = sheet("CHI")
    tieu_de(ch, "CHIẾT TÍNH VÀ THỰC CHI – hai cột NẰM CÙNG MỘT DÒNG để so được từng khoản", 18)
    cot_ch = ([("Ngày", 11, "nhap"), ("Mã khoản mục", 22, "nhap"), ("Nhóm", 16, "ct"),
               ("Nội dung", 30, "nhap"),
               ("Đối tác", 24, "nhap"), ("MST đối tác", 14, "nhap"), ("Đối tượng", 11, "nhap"),
               ("Quy tắc phân bổ", 18, "nhap")]
              + ([("Tiền tệ", 8, "nhap"), ("Số tiền gốc", 13, "nhap"), ("Tỷ giá", 10, "nhap"),
                  ("Ngày tỷ giá", 12, "nhap")] if NN else [])
              # Đơn giá / Số lượng / Hệ số: ba ô mô tả CHIẾT TÍNH của dòng, đúng như sheet CTT của
              # tệp thật ghi ("115.000 × 33 suất × 1 ngày"). Vẫn là ô TUỲ Ý – ai chỉ biết số tổng thì
              # gõ thẳng vào DỰ CHI. Điền cả ba thì sheet ĐỐI CHIẾU soát lại tích số có khớp DỰ CHI
              # không, và lúc lệch dự/thực mới tách được lệch do GIÁ hay do SỐ LƯỢNG.
              + [("Đơn giá", 13, "nhap"), ("Số lượng", 9, "nhap"), ("Hệ số", 8, "nhap"),
                 ("DỰ CHI (VND)", 14, "nhap"), ("THỰC CHI (VND)", 15, "ct" if NN else "nhap"),
                 ("Chênh dự/thực", 14, "ct"), ("Thuế suất", 9, "nhap"), ("Tiền thuế", 13, "ct"),
                 ("Phần KHÔNG hoá đơn", 15, "nhap"), ("Số hoá đơn", 13, "nhap")]
              # Phần THANH TOÁN. Tệp UK ghi đủ ("Bank transfer", "Wise 9078", Paid Date, Deadline,
              # Invoice/Receipt) và Kế toán đang phải mở tệp gốc để đối chiếu với sao kê thẻ.
              + [("Hình thức TT", 13, "nhap"), ("Thẻ / tài khoản trả", 17, "nhap"),
                 ("Ngày thanh toán", 13, "nhap"), ("Hạn thanh toán", 13, "nhap"),
                 ("Loại chứng từ", 14, "nhap")])
    # Cột chạy khác nhau giữa hai mẫu, nên KHÔNG gọi cột bằng chữ cái viết cứng. Dò theo nhãn.
    _c = {nhan: get_column_letter(i) for i, (nhan, _w, _k) in enumerate(cot_ch, start=1)}
    gc_ch = {
        "Mã khoản mục": "CHỌN từ ô thả xuống – danh mục ở sheet KHOẢN MỤC.\n\nTrên tám tệp quyết toán "
                        "thật, cùng một khoản có nhiều tên (LAND / LAND MCB / Landtour ADL / Giá "
                        "land). Chữ tự do thì không cộng được theo khoản mục, nên câu 'cả năm chi "
                        "bao nhiêu tiền khách sạn' không có câu trả lời.",
        "Nhóm": "MÁY TỰ ĐIỀN từ mã khoản mục. Đừng gõ đè.",
        "Nội dung": "Chi tiết riêng của dòng: tên nhà hàng, tên khách sạn, ngày nào.\nTên KHOẢN MỤC "
                    "đã nằm ở cột mã rồi – ở đây ghi cái phân biệt dòng này với dòng kia.",
        "Quy tắc phân bổ": "deu_moi_khach / deu_khach_co_thu / theo_doi_tuong /\ntheo_ty_le_doanh_thu / khong_phan_bo\n\nĐể trống = CHƯA AI CHỌN. Máy không đoán hộ.",
        "Tỷ giá": "Tỷ giá của NGÀY CHI THẬT, không phải tỷ giá lập chiết tính.",
        "THỰC CHI (VND)": "VND thì gõ ở cột DỰ CHI và cột này lấy theo.\nNgoại tệ thì máy nhân số gốc × tỷ giá.",
        "Phần KHÔNG hoá đơn": "Đã xác nhận KHÔNG CÓ hoá đơn – khác với 'chưa nhập'.\nĐây là phần giá vốn không khấu trừ được thuế.",
        "Đơn giá": "TUỲ Ý. Đơn giá một suất/một đêm/một vé theo chiết tính.\n\nĐiền cả ba ô Đơn giá – Số lượng – Hệ số thì sheet ĐỐI CHIẾU soát lại tích số có bằng DỰ CHI không. Chỉ biết số tổng thì bỏ trống ba ô này và gõ thẳng DỰ CHI.",
        "Số lượng": "Số suất / số đêm / số vé theo chiết tính.\n\nĐây là ô trả lời câu 'dự toán 40 suất Tháp Bà, thực chi 44 suất' – không có nó thì lệch do GIÁ và lệch do SỐ LƯỢNG trộn vào nhau.",
        "Hệ số": "Số lần lặp lại: 2 đêm, 3 bữa… Để trống hiểu là 1.",
        "Hình thức TT": "bank / card / tien_mat / bu_tru",
        "Thẻ / tài khoản trả": "Ghi đúng như người trả ghi: 'Wise 9078', 'Tech 735'.\n\nĐây là thứ Kế toán dùng để dò ngược khoản chi này trong sao kê thẻ.",
        "Ngày thanh toán": "Ngày tiền RỜI tài khoản – không phải ngày lập chứng từ.",
        "Hạn thanh toán": "Deadline của đối tác. Phòng đặt qua Agoda/Booking quá hạn là mất phòng.",
        "Loại chứng từ": "invoice / receipt / ticket / booking_confirm / khong_co",
    }
    dau_bang(ch, 2, cot_ch, gc_ch)
    C1, C2 = 3, 92
    to_mau(ch, C1, C2, cot_ch)
    # Ô CHỌN cho mã khoản mục, lấy thẳng từ sheet KHOẢN MỤC. Gõ tay một mã lạ thì Excel chặn ngay tại
    # chỗ gõ – không đợi tới lúc nạp vào hệ thống mới báo.
    MA, NHOM_C = _c["Mã khoản mục"], _c["Nhóm"]
    _chon = DataValidation(type="list",
                           formula1=f"='KHOẢN MỤC'!$A$3:$A${_km_cuoi}",
                           allow_blank=True, showDropDown=False)
    _chon.error = ("Mã khoản mục không có trong danh mục. Chọn từ ô thả xuống, hoặc dùng mã "
                   "'..._khac' rồi ghi rõ ở cột Nội dung.")
    _chon.errorTitle = "Mã khoản mục lạ"
    ch.add_data_validation(_chon)
    _chon.add(f"{MA}{C1}:{MA}{C2}")

    DU, THUC = _c["DỰ CHI (VND)"], _c["THỰC CHI (VND)"]
    CHENH, TS, TT = _c["Chênh dự/thực"], _c["Thuế suất"], _c["Tiền thuế"]
    for r in range(C1, C2 + 1):
        if NN:
            TE, GOC, TG, NTG = _c["Tiền tệ"], _c["Số tiền gốc"], _c["Tỷ giá"], _c["Ngày tỷ giá"]
            ch[f"{THUC}{r}"] = (f'=IF(AND(${TE}{r}<>"",${TE}{r}<>"VND"),'
                                f'IF(OR(${GOC}{r}="",${TG}{r}=""),"",ROUND(${GOC}{r}*${TG}{r},0)),'
                                f'IF(${DU}{r}="","",${DU}{r}))')
            ch[f"{NTG}{r}"].number_format = "dd/mm/yyyy"
            tien(ch, GOC, r, r)
            tien(ch, TG, r, r, "#,##0.00")
        ch[f"{CHENH}{r}"] = f'=IF(OR(${DU}{r}="",${THUC}{r}=""),"",${THUC}{r}-${DU}{r})'
        ch[f"{TT}{r}"] = f'=IF(OR(${THUC}{r}="",${TS}{r}=""),"",ROUND(${THUC}{r}*${TS}{r},0))'
        # Nhóm do MÁY tra từ danh mục, không ai gõ – nhóm gõ tay là nhóm sai, và nhóm sai thì báo
        # cáo chi phí theo nhóm sai theo mà không ai thấy.
        ch[f"{NHOM_C}{r}"] = (f'=IF(${MA}{r}="","",IFERROR(INDEX(\'KHOẢN MỤC\'!$C$3:$C${_km_cuoi},'
                              f'MATCH(${MA}{r},\'KHOẢN MỤC\'!$A$3:$A${_km_cuoi},0)),"(mã lạ)"))')
        ch[f"{_c['Ngày']}{r}"].number_format = "dd/mm/yyyy"
        ch[f"{TS}{r}"].number_format = "0%"
        ch[f"{_c['Ngày thanh toán']}{r}"].number_format = "dd/mm/yyyy"
        ch[f"{_c['Hạn thanh toán']}{r}"].number_format = "dd/mm/yyyy"
    tien(ch, _c["Đơn giá"], C1, C2)
    for nhan in ("DỰ CHI (VND)", "THỰC CHI (VND)", "Chênh dự/thực", "Tiền thuế",
                 "Phần KHÔNG hoá đơn"):
        tien(ch, _c[nhan], C1, C2)
    ch.cell(C2 + 1, 3, "CỘNG").font = Font(name=F, bold=True, size=10)
    for nhan in ("DỰ CHI (VND)", "THỰC CHI (VND)", "Chênh dự/thực", "Tiền thuế",
                 "Phần KHÔNG hoá đơn"):
        c = _c[nhan]; i = [x[0] for x in cot_ch].index(nhan) + 1
        cc = ch.cell(C2 + 1, i, f"=SUM({c}{C1}:{c}{C2})")
        cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
        cc.fill = PatternFill("solid", fgColor=XANH)
    ch.freeze_panes = "D3"

    # =============================================================================================
    # 5. CHI THEO KHÁCH – CHỈ tour nước ngoài
    # ---------------------------------------------------------------------------------------
    # Tour trong nước không có khoản nào mỗi khách một giá: vé, visa và dịch thuật là chuyện của
    # tour nước ngoài. Dựng sheet rỗng cho mẫu trong nước là mời người ta điền vào một chỗ không
    # ai đọc.
    D1 = D2 = 0
    if NN:
        # 5. CHI THEO KHÁCH
        # =============================================================================================
        ck = sheet("CHI THEO KHÁCH")
        tieu_de(ck, "CHI PHÍ ĐÍCH DANH – khoản mỗi khách một giá, KHÔNG chia, KHÔNG phân bổ", 11)
        ck.cell(2, 1, "Vé máy bay, phí lãnh sự quán, dịch thuật, quà tặng. Trên tệp thật, cùng một chuyến mà vé "
                      "khách này 22.435.959 đ còn khách kia 21.903.700 đ, phí lãnh sự quán chạy từ 7.875.750 đến "
                      "8.290.750, và bốn khách không mua visa vì đã có sẵn. Ép vào phép chia là làm hỏng cả hai đầu."
                ).font = Font(name=F, size=9, italic=True, color="555555")
        ck.merge_cells(start_row=2, start_column=1, end_row=2, end_column=11)
        ck.row_dimensions[2].height = 30
        cot_ck = [("Khách (STT)", 11, "nhap"), ("Họ và tên", 26, "nhap"), ("Loại chi phí", 15, "nhap"),
                  ("Nội dung", 26, "nhap"), ("Nhà cung cấp", 22, "nhap"), ("MST", 14, "nhap"),
                  ("Tiền tệ", 8, "nhap"), ("Số tiền gốc", 13, "nhap"), ("Tỷ giá", 10, "nhap"),
                  ("Thành tiền (VND)", 15, "ct"), ("Số hoá đơn", 13, "nhap")]
        dau_bang(ck, 3, cot_ck, {"Loại chi phí": "ve_may_bay / visa / dich_thuat / qua_tang / bao_hiem / khac"})
        D1, D2 = 4, 63
        to_mau(ck, D1, D2, cot_ck)
        for r in range(D1, D2 + 1):
            ck[f"J{r}"] = (f'=IF(AND($G{r}<>"",$G{r}<>"VND"),IF(OR($H{r}="",$I{r}=""),"",'
                           f'ROUND($H{r}*$I{r},0)),IF($H{r}="","",$H{r}))')
        tien(ck, "H", D1, D2); tien(ck, "J", D1, D2); tien(ck, "I", D1, D2, "#,##0.00")
        cc = ck.cell(D2 + 1, 10, f"=SUM(J{D1}:J{D2})")
        cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
        cc.fill = PatternFill("solid", fgColor=XANH)
        ck.cell(D2 + 1, 4, "CỘNG").font = Font(name=F, bold=True, size=10)
        ck.freeze_panes = "C4"

        # =============================================================================================
    # 6. PHƯƠNG TIỆN
    # =============================================================================================
    pt = sheet("PHƯƠNG TIỆN")
    tieu_de(pt, "PHƯƠNG TIỆN TỪNG CHẶNG – một chuyến có nhiều chặng, mỗi chặng một nhà cung cấp", 13)
    cot_pt = [("Loại", 11, "nhap"), ("Chặng", 20, "nhap"), ("Ngày", 11, "nhap"),
              ("Số hiệu / biển số", 15, "nhap"), ("Mã đặt chỗ", 12, "nhap"),
              ("Nhà cung cấp", 22, "nhap"), ("MST", 13, "nhap"), ("Xe nhà?", 9, "nhap"),
              ("Số chỗ", 8, "nhap"), ("Số khách dùng", 12, "nhap"), ("Thành tiền (VND)", 15, "nhap"),
              ("Dòng CHI tương ứng", 16, "nhap"), ("Ghi chú", 24, "nhap")]
    dau_bang(pt, 2, cot_pt, {
        "Loại": "o_to / may_bay / tau_hoa / tau_thuy / khac",
        "Xe nhà?": "x = xe của đội xe trong nhóm.\nKhoản ấy là CÔNG NỢ NỘI BỘ, không phải tiền trả bên thứ ba – hợp nhất báo cáo thì phải loại trừ.",
        "Dòng CHI tương ứng": "Số dòng ở sheet CHI. Chặng không nối được vào dòng chi nào là chặng CHƯA VÀO GIÁ VỐN."})
    P1, P2 = 3, 22
    to_mau(pt, P1, P2, cot_pt)
    tien(pt, "K", P1, P2)
    for r in range(P1, P2 + 1):
        pt[f"C{r}"].number_format = "dd/mm/yyyy"
    cc = pt.cell(P2 + 1, 11, f"=SUM(K{P1}:K{P2})")
    cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
    cc.fill = PatternFill("solid", fgColor=XANH)
    pt.freeze_panes = "C3"

    # =============================================================================================
    # 7. HDV
    # =============================================================================================
    hv = sheet("HDV")
    tieu_de(hv, "HƯỚNG DẪN VIÊN – ứng, chi, và HAI phép so khác nhau", 11)
    hv.cell(2, 1, "VƯỢT = thực chi − chiết tính (vượt DỰ TOÁN, Chủ tịch chốt: vượt mà không được duyệt thì HDV bù). "
                  "CÒN LẠI = tiền ứng − thực chi (âm nghĩa là CÔNG TY nợ HDV). Hai chiều ngược nhau và cả hai đều "
                  "xảy ra thật – gộp một cột là có lúc đi đòi tiền người đang được công ty nợ."
            ).font = Font(name=F, size=9, italic=True, color="555555")
    hv.merge_cells(start_row=2, start_column=1, end_row=2, end_column=11)
    hv.row_dimensions[2].height = 30
    cot_hv = [("Nội dung", 30, "nhap"), ("Đơn giá", 12, "nhap"), ("Số lượng", 9, "nhap"),
              ("Tiền tệ", 8, "nhap"), ("Số gốc", 12, "nhap"),
              ("Tỷ giá", 10, "nhap"), ("Ngày tỷ giá", 12, "nhap"),
              ("Thực chi (VND)", 14, "ct"), ("Theo chiết tính", 14, "nhap"),
              ("VƯỢT", 13, "ct"),
              # TIỀN ỨNG là nửa còn lại của phép so. Bản đầu chỉ có MỘT ô ứng đặt dưới bảng, mà bộ
              # đọc chỉ đọc các dòng GIỮA tiêu đề và dòng CỘNG – nên con số ấy không bao giờ vào
              # được hệ thống. Mẫu đoàn Đà Lạt: ứng 3.300.000, chi 3.696.000 → công ty NỢ HDV
              # 396.000. Không có cột này thì chỉ chạy được chiều HDV chi vượt, và cái nửa thiếu
              # chính là nửa khiến đi đòi tiền người đang được công ty nợ.
              ("Tiền ứng", 13, "nhap"), ("CÒN LẠI", 13, "ct"),
              ("Chứng từ", 12, "nhap"), ("Thu hộ khách?", 12, "nhap"),
              ("Duyệt", 11, "nhap"), ("Lý do duyệt / từ chối", 26, "nhap")]
    # Dò cột theo NHÃN, không viết cứng chữ cái: bảng này vừa thêm năm cột, và mọi công thức viết
    # cứng "E"/"G" ở bản trước đều trỏ sai một chỗ khác sau khi chèn.
    _h = {nhan: get_column_letter(i) for i, (nhan, _w, _k) in enumerate(cot_hv, start=1)}
    dau_bang(hv, 3, cot_hv, {
        "Chứng từ": "phieu_thu / hoa_don / khong_co",
        "Tiền ứng": "Tiền công ty ĐƯA TRƯỚC cho HDV.\n\nỨng một lần cho cả tour thì gõ vào MỘT dòng – ô CỘNG ỨNG phía dưới tự cộng lại.",
        "CÒN LẠI": "MÁY TÍNH: tiền ứng − thực chi.\nÂM nghĩa là công ty còn NỢ LẠI HDV.",
        "VƯỢT": "MÁY TÍNH: thực chi − theo chiết tính.\nDƯƠNG nghĩa là HDV tiêu quá dự toán.",
        "Thu hộ khách?": "x = tiền của KHÁCH, không phải của công ty.\nKhông vào giá vốn, cũng không vào doanh thu.",
        "Duyệt": "cho_duyet / da_duyet / tu_choi.\nIM LẶNG KHÔNG PHẢI ĐỒNG Ý – còn dòng cho_duyet thì tờ chưa đóng được."})
    H1, H2 = 4, 33
    to_mau(hv, H1, H2, cot_hv)
    TE_H, GOC_H, TG_H = _h["Tiền tệ"], _h["Số gốc"], _h["Tỷ giá"]
    DG_H, SL_H = _h["Đơn giá"], _h["Số lượng"]
    THUC_H, CT_H, VUOT_H = _h["Thực chi (VND)"], _h["Theo chiết tính"], _h["VƯỢT"]
    UNG_H, CL_H, DUYET_H = _h["Tiền ứng"], _h["CÒN LẠI"], _h["Duyệt"]
    for r in range(H1, H2 + 1):
        # Ngoại tệ thì số gốc × tỷ giá. Nội tệ thì đơn giá × số lượng khi có đủ, còn không thì lấy
        # thẳng số gốc – tệp thật ghi cả hai kiểu ("30.000 × 44 suất" và một số tổng trần).
        hv[f"{THUC_H}{r}"] = (
            f'=IF(AND(${TE_H}{r}<>"",${TE_H}{r}<>"VND"),'
            f'IF(OR(${GOC_H}{r}="",${TG_H}{r}=""),"",ROUND(${GOC_H}{r}*${TG_H}{r},0)),'
            f'IF(AND(${DG_H}{r}<>"",${SL_H}{r}<>""),ROUND(${DG_H}{r}*${SL_H}{r},0),'
            f'IF(${GOC_H}{r}="","",${GOC_H}{r})))')
        hv[f"{VUOT_H}{r}"] = (f'=IF(OR(${THUC_H}{r}="",${CT_H}{r}=""),"",'
                              f'${THUC_H}{r}-${CT_H}{r})')
        hv[f"{CL_H}{r}"] = (f'=IF(OR(${UNG_H}{r}="",${THUC_H}{r}=""),"",'
                            f'${UNG_H}{r}-${THUC_H}{r})')
        hv[f"{_h['Ngày tỷ giá']}{r}"].number_format = "dd/mm/yyyy"
    for nhan in ("Đơn giá", "Số gốc", "Thực chi (VND)", "Theo chiết tính", "VƯỢT",
                 "Tiền ứng", "CÒN LẠI"):
        tien(hv, _h[nhan], H1, H2)
    tien(hv, TG_H, H1, H2, "#,##0.00")

    hv.cell(H2 + 1, 1, "CỘNG").font = Font(name=F, bold=True, size=10)
    for nhan in ("Thực chi (VND)", "VƯỢT", "Tiền ứng"):
        i = [x[0] for x in cot_hv].index(nhan) + 1
        c = _h[nhan]
        cc = hv.cell(H2 + 1, i, f"=SUM({c}{H1}:{c}{H2})")
        cc.font = Font(name=F, bold=True, size=10); cc.number_format = "#,##0"
        cc.fill = PatternFill("solid", fgColor=XANH)

    # Bốn con số kết luận. Cột đặt chúng cũng dò theo nhãn, vì bản trước đặt cứng ở cột E và cột E
    # nay là "Số gốc".
    COT_KQ = [x[0] for x in cot_hv].index("Thực chi (VND)") + 1
    O_KQ = get_column_letter(COT_KQ)
    # Ghi lại SỐ DÒNG của từng con số kết luận, để sheet LÃI LỖ và ĐỐI CHIẾU trỏ vào bằng biến chứ
    # không đếm tay. Bản trước trỏ cứng "HDV'!E{H2+5}" và cả hai thứ đều đã đổi: cột E nay là "Số
    # gốc", còn hàng thì lùi một dòng vì ô ứng rời xuống thành một cột trong bảng.
    HANG_KQ = {}
    for i, (nhan, ct, mau) in enumerate([
        ("CÒN LẠI  (ứng − chi; ÂM = công ty nợ HDV)",
         f'=IF(OR({_h["Tiền ứng"]}{H2+1}="",{THUC_H}{H2+1}=""),"",'
         f'{_h["Tiền ứng"]}{H2+1}-{THUC_H}{H2+1})', XANH),
        ("PHẢI THU HDV  (phần vượt bị từ chối)",
         f'=SUMIFS(${VUOT_H}${H1}:${VUOT_H}${H2},${DUYET_H}${H1}:${DUYET_H}${H2},"tu_choi")', XANH),
        ("Còn dòng CHỜ DUYỆT",
         f'=COUNTIF(${DUYET_H}${H1}:${DUYET_H}${H2},"cho_duyet")', DO),
    ], start=3):
        hv.cell(H2 + i, 1, nhan).font = Font(name=F, bold=True, size=10,
                                             color="9C1F1F" if mau == DO else "000000")
        cc = hv.cell(H2 + i, COT_KQ, ct)
        cc.font = Font(name=F, bold=True, size=10)
        cc.fill = PatternFill("solid", fgColor=mau)
        if mau == XANH:
            cc.number_format = "#,##0"
        HANG_KQ[nhan.split("  ")[0].split(" (")[0]] = H2 + i

    # =============================================================================================
    # 8. LÃI LỖ
    # =============================================================================================
    ll = sheet("LÃI LỖ")
    tieu_de(ll, "LÃI LỖ CHUYẾN – toàn bộ là công thức, không gõ gì ở sheet này", 4)
    ll.column_dimensions["A"].width = 6
    ll.column_dimensions["B"].width = 44
    ll.column_dimensions["C"].width = 20
    ll.column_dimensions["D"].width = 60

    # Số dòng KHÔNG viết cứng: dựng bảng rồi mới ráp công thức từ đúng số dòng đã ghi. Bản đầu viết cứng
    # "=C8+C9+C10" và lệch đúng một dòng vì hai hàng tiêu đề chen vào giữa – phép tính vẫn chạy, không
    # báo lỗi nào, chỉ ra sai số. Đây đúng là kiểu hỏng mà cả mẫu này sinh ra để chống.
    D = {}


    def dong_ll(ma, nhan, f_, note="", dam=False, pt_format=False):
        nonlocal r
        ll.cell(r, 1, ma).font = Font(name=F, size=9, color="777777")
        ll.cell(r, 2, nhan).font = Font(name=F, bold=dam, size=10)
        c = ll.cell(r, 3, f_)
        c.font = Font(name=F, bold=dam, size=10)
        c.fill = PatternFill("solid", fgColor=XANH)
        c.border = VIEN
        c.number_format = "0.0%" if pt_format else "#,##0"
        cn = ll.cell(r, 4, note)
        cn.font = Font(name=F, size=9, italic=True, color="555555")
        cn.alignment = Alignment(wrap_text=True, vertical="center")
        if note:
            ll.row_dimensions[r].height = 28
        D[ma] = r
        r += 1


    def nhom_ll(so, ten):
        nonlocal r
        ll.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        c = ll.cell(r, 1, f"{so}.  {ten}")
        c.font = Font(name=F, bold=True, size=11, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        r += 2 if False else 1


    r = 3
    nhom_ll("I", "DOANH THU")
    dong_ll("thu_truoc", "Tổng thu trước thuế", f"='THU'!{_t['Thành tiền trước thuế']}{T2+1}")
    dong_ll("thue_ra", "Thuế GTGT đầu ra", f"='THU'!{_t['Tiền thuế']}{T2+1}")
    dong_ll("tong_thu", "TỔNG THU", f"='THU'!{_t['TỔNG THU']}{T2+1}", "Gồm cả dòng âm của thanh lý hợp đồng.", dam=True)
    r += 1
    nhom_ll("II", "GIÁ VỐN")
    dong_ll("chi_chung", "Chi phí chung (sheet CHI)", f"='CHI'!{THUC}{C2+1}")
    if NN:
        dong_ll("chi_khach", "Chi phí đích danh theo khách", f"='CHI THEO KHÁCH'!J{D2+1}",
                "Vé, visa, dịch thuật – mỗi khách một giá, không chia.")
    dong_ll("hdv_tu_choi", "Trừ: HDV chi vượt bị từ chối", f"=-'HDV'!{O_KQ}{HANG_KQ['PHẢI THU HDV']}",
            "Phần vượt không được duyệt thì HDV bù, công ty không chịu – nên TRỪ khỏi giá vốn.")
    _von = "+".join(f"C{D[k]}" for k in ("chi_chung", "chi_khach", "hdv_tu_choi") if k in D)
    dong_ll("tong_von", "TỔNG GIÁ VỐN", f"={_von}", "", dam=True)
    r += 1
    nhom_ll("III", "KẾT QUẢ")
    dong_ll("loi_nhuan", "LỢI NHUẬN",
            f"=IF(OR(C{D['tong_thu']}=\"\",C{D['tong_von']}=\"\"),\"\",C{D['tong_thu']}-C{D['tong_von']})",
            "", dam=True)
    dong_ll("ty_le", "Tỷ lệ lợi nhuận",
            f"=IF(OR(C{D['tong_thu']}=\"\",C{D['tong_thu']}=0,C{D['loi_nhuan']}=\"\"),\"\","
            f"C{D['loi_nhuan']}/C{D['tong_thu']})", "", pt_format=True)
    r += 1
    nhom_ll("IV", "CHẤT LƯỢNG CHỨNG TỪ")
    dong_ll("khong_hd", "Giá vốn KHÔNG có hoá đơn", f"='CHI'!{_c['Phần KHÔNG hoá đơn']}{C2+1}")
    dong_ll("ty_le_khong_hd", "Tỷ lệ không hoá đơn",
            f"=IF(OR('CHI'!{THUC}{C2+1}=\"\",'CHI'!{THUC}{C2+1}=0),\"\","
            f"C{D['khong_hd']}/'CHI'!{THUC}{C2+1})",
            "Chủ tịch chốt KHÔNG bắt buộc mã số thuế – nhưng vẫn đếm và hiện ra.", pt_format=True)
    dong_ll("thue_vao", "Thuế GTGT đầu vào", f"='CHI'!{TT}{C2+1}")

    # =============================================================================================
    # 9. ĐỐI CHIẾU
    # =============================================================================================
    dc = sheet("ĐỐI CHIẾU")
    tieu_de(dc, "CHÍN PHÉP KIỂM TỰ CHẠY – còn dòng LỆCH thì tờ quyết toán chưa xong", 5)
    dc.column_dimensions["A"].width = 5
    dc.column_dimensions["B"].width = 46
    dc.column_dimensions["C"].width = 17
    dc.column_dimensions["D"].width = 12
    dc.column_dimensions["E"].width = 62
    dau_bang(dc, 2, [("#", 5, "tt"), ("Phép kiểm", 46, "tt"), ("Số đo", 17, "ct"),
                     ("Kết luận", 12, "ct"), ("Bắt được lỗi gì", 62, "tt")])

    R0 = 3   # dòng đầu của bảng kiểm
    kiem = [
        ("Số dòng khách khác số khách đầu bảng",
         f'=IF({SO_KHACH}="","",COUNTA(\'KHÁCH\'!C{K1}:C{K2})-{SO_KHACH})',
         'IF(C{r}="","—",IF(C{r}=0,"ĐÚNG","LỆCH"))',
         "Tệp thật ghi 'Số khách 44' trong khi đếm được 42, và tờ ấy đã có bốn chữ ký."),
        ("Khách chưa có ngày sinh",
         f'=COUNTIFS(\'KHÁCH\'!C{K1}:C{K2},"<>",\'KHÁCH\'!E{K1}:E{K2},"")',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Thiếu ngày sinh thì quy tắc giá theo tuổi không kiểm được cho những khách ấy."),
        ("Khách trả tiền chưa có giá bán",
         f'=COUNTIFS(\'KHÁCH\'!{_k["Nhóm khách"]}{K1}:{_k["Nhóm khách"]}{K2},"tra_tien",'
         f'\'KHÁCH\'!{_k["Giá bán"]}{K1}:{_k["Giá bán"]}{K2},"")',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Ô giá bán để trống nghĩa là CHƯA AI NHẬP, không phải bán 0 đồng. Bỏ sót một khách là hụt "
         "nguyên một suất trong doanh thu mà bảng vẫn cân."),
        ("Thu theo hợp đồng khác tổng giá bán ở sheet KHÁCH",
         # Chỉ cộng dòng loại "hop_dong". Dòng thanh_ly (hoàn tiền theo biên bản) theo định nghĩa KHÔNG
         # có mặt ở giá bán trên sheet KHÁCH, nên đem cả chúng vào phép so là báo lệch ở mọi chuyến có
         # hoàn tiền – một phép kiểm lúc nào cũng đỏ thì chẳng khác gì không có.
         f"=IF(COUNTIFS('THU'!{_t['Nội dung']}{T1}:{_t['Nội dung']}{T2},\"<>\","
         f"'THU'!{_t['Khách (STT)']}{T1}:{_t['Khách (STT)']}{T2},\"<>\")=0,\"\","
         f"SUMIFS('THU'!${_t['TỔNG THU']}${T1}:${_t['TỔNG THU']}${T2},"
         f"'THU'!${_t['Loại']}${T1}:${_t['Loại']}${T2},\"hop_dong\")"
         f"-'KHÁCH'!{_k['Giá bán']}{K2+1})",
         'IF(C{r}="","—",IF(ABS(C{r})<1000,"ĐÚNG","LỆCH"))',
         "Chỉ chạy khi sheet THU ghi theo TỪNG KHÁCH (tour lẻ), và chỉ soi dòng hợp đồng."),
        ("Dòng thu ÂM mà không có chứng từ",
         f'=SUMPRODUCT((N(\'THU\'!J{T1}:J{T2})<0)*(\'THU\'!K{T1}:K{T2}=""))',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Hoàn tiền phải có biên bản thanh lý, nếu không thì không phân biệt được với gõ nhầm dấu."),
        ("Dòng chi chưa khai quy tắc phân bổ",
         f'=COUNTIFS(\'CHI\'!{_c["Nội dung"]}{C1}:{_c["Nội dung"]}{C2},"<>",'
         f'\'CHI\'!{_c["Quy tắc phân bổ"]}{C1}:{_c["Quy tắc phân bổ"]}{C2},"")',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Chưa khai thì máy KHÔNG chia và KHÔNG đoán – phần ấy không vào giá vốn của khách nào."),
    ] + ([
        ("Khoản ngoại tệ thiếu tỷ giá hoặc ngày tỷ giá",
         f'=SUMPRODUCT((\'CHI\'!{_c["Tiền tệ"]}{C1}:{_c["Tiền tệ"]}{C2}<>"")'
         f'*(\'CHI\'!{_c["Tiền tệ"]}{C1}:{_c["Tiền tệ"]}{C2}<>"VND")'
         f'*(((\'CHI\'!{_c["Tỷ giá"]}{C1}:{_c["Tỷ giá"]}{C2}="")'
         f'+(\'CHI\'!{_c["Ngày tỷ giá"]}{C1}:{_c["Ngày tỷ giá"]}{C2}=""))>0))',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Một tệp thật có hai tỷ giá GBP khác nhau; riêng trên một khoản land, chênh 56 đ là 1.667.155 đ."),
    ] if NN else []) + [
        ("Chặng phương tiện chưa nối vào dòng chi nào",
         f'=COUNTIFS(\'PHƯƠNG TIỆN\'!A{P1}:A{P2},"<>",\'PHƯƠNG TIỆN\'!L{P1}:L{P2},"")',
         'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Chặng không nối được vào dòng chi là chặng CHƯA VÀO GIÁ VỐN."),
        ("HDV còn khoản chờ duyệt",
         f"='HDV'!{O_KQ}{HANG_KQ['Còn dòng CHỜ DUYỆT']}", 'IF(C{r}=0,"ĐÚNG","LỆCH")',
         "Im lặng không được tính là đồng ý. Còn dòng chờ duyệt thì tờ chưa đóng được."),
    ]
    r = R0
    for i, (ten, do, kl, vi_sao) in enumerate(kiem, start=1):
        dc.cell(r, 1, i).font = Font(name=F, size=9, color="777777")
        dc.cell(r, 2, ten).font = Font(name=F, size=10)
        c = dc.cell(r, 3, do)
        c.fill = PatternFill("solid", fgColor=XANH); c.border = VIEN
        c.font = Font(name=F, size=10); c.number_format = "#,##0"
        k = dc.cell(r, 4, "=" + kl.format(r=r))
        k.fill = PatternFill("solid", fgColor=XANH); k.border = VIEN
        k.font = Font(name=F, bold=True, size=10)
        k.alignment = Alignment(horizontal="center")
        cn = dc.cell(r, 5, vi_sao)
        cn.font = Font(name=F, size=9, italic=True, color="555555")
        cn.alignment = Alignment(wrap_text=True, vertical="center")
        dc.row_dimensions[r].height = 30
        for j in range(1, 6):
            dc.cell(r, j).border = VIEN
        r += 1
    R9 = r - 1
    dc.cell(r + 1, 2, "CÒN BAO NHIÊU PHÉP KIỂM LỆCH").font = Font(name=F, bold=True, size=11, color="9C1F1F")
    c = dc.cell(r + 1, 4, f'=COUNTIF(D{R0}:D{R9},"LỆCH")')
    c.font = Font(name=F, bold=True, size=12); c.fill = PatternFill("solid", fgColor=DO)
    c.alignment = Alignment(horizontal="center"); c.border = VIEN
    dc.cell(r + 2, 2, "Khác 0 nghĩa là tờ quyết toán CHƯA XONG. Sửa ở sheet nguồn, đừng sửa ở đây."
            ).font = Font(name=F, size=9, italic=True, color="555555")
    dc.cell(r + 3, 2, "Dấu — nghĩa là phép kiểm ấy không áp cho loại tour này."
            ).font = Font(name=F, size=9, italic=True, color="555555")


    # LUÔN trả về bytes, kể cả khi có ghi ra tệp. Bản đầu trả về CHUỖI tên tệp trong nhánh ten_tep,
    # trong khi chữ ký hàm khai là -> bytes: người gọi nào truyền tên tệp rồi đem kết quả làm thân
    # phản hồi HTTP sẽ gửi cho nhân viên một tệp .xlsx dài đúng bằng đường dẫn. ten_tep là TÁC DỤNG
    # PHỤ (ghi ra đĩa để chạy tay ở máy), không phải thứ đổi kiểu trả về.
    from io import BytesIO
    b = BytesIO()
    wb.save(b)
    noi_dung = b.getvalue()
    if ten_tep:
        with open(ten_tep, "wb") as f:
            f.write(noi_dung)
    return noi_dung


