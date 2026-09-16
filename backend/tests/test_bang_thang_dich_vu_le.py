# -*- coding: utf-8 -*-
"""BỘ ĐỌC BẢNG THÁNG DỊCH VỤ LẺ – visa theo tháng, land theo tháng, outbound ghép lẻ theo tháng.

Chủ tịch chốt 16/9/2026: mở cửa riêng cho 49 tệp mà vòng nạp kho cũ trả về "không thấy chuyến".

VÌ SAO KHÔNG ÉP CHÚNG QUA CỬA KHO CŨ — ĐO CHỨ KHÔNG SUY

  Bộ đọc kho cũ đọc được 225 dòng khách / 435,1 triệu trên 21 tệp visa, trong khi chính các tệp ấy
  tự khai tổng thu 1.836,3 triệu. Nó đọc được 24% rồi IM LẶNG bỏ phần còn lại.

  Nạp vào 24% mà không báo thiếu là kiểu sai tệ nhất: sai mà trông như đúng.

Chín điều, mỗi điều là một cách hỏng đã nghĩ ra trước — và BA trong số đó là lỗi bộ đọc này ĐÃ MẮC
rồi bị phép đối chiếu với dòng TỔNG CỘNG của chính tệp bắt được (BT6, BT7, BT8).

  BT1  đọc theo NGHĨA của tiêu đề, KHÔNG theo vị trí cột
  BT2  KHÔNG tự quy đổi ngoại tệ – giữ số gốc, báo thiếu tỷ giá
  BT3  KHÔNG đọc dòng TỔNG CỘNG thành một khách
  BT4  lãi = thu − chi do MÁY TRỪ; cột 'LỢI NHUẬN' trong tệp KHÔNG được đọc vào
  BT5  cột có TIỀN mà không nhận ra tên thì PHẢI NÊU RA
  BT6  tiêu đề MỘT hàng: không được ăn mất dòng khách đầu tiên
  BT7  ô gộp ở hàng DỮ LIỆU không được cộng hai lần
  BT8  ô TỔNG CỘNG của tệp lệch với tổng các dòng thì NÓI RA, và lấy theo TỔNG CÁC DÒNG
  BT9  kỳ đọc từ tên tệp; thiếu NĂM thì báo, KHÔNG điền hộ
"""
import os
import sys
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./test_bangthang.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_bangthang.db", "test_bangthang.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import openpyxl                                              # noqa: E402

from app.services import nap_bang_thang as BT                # noqa: E402


def _tep(hang, gop=(), ten_sheet="Sheet1") -> bytes:
    """Dựng một bảng tháng: `hang` là danh sách (chỉ_số_hàng, [ô...]) đặt từ cột 1."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ten_sheet
    for r, cols in hang:
        for i, v in enumerate(cols, start=1):
            if v is not None:
                ws.cell(r, i, v)
    for v in gop:
        ws.merge_cells(v)
    b = BytesIO()
    wb.save(b)
    return b.getvalue()


# Bảng chuẩn dùng lại: tiêu đề HAI hàng, hai khách, một dòng TỔNG CỘNG.
def _bang_chuan(**kw) -> bytes:
    return _tep([
        (1, [None, None, "CÔNG TY CP DU LỊCH VIETOURIST"]),
        (5, ["STT", "Sale", "Tên khách hàng", "Giá bán", "Thu khác", "Tổng thu", "Phí LSQ"]),
        (6, [None, None, None, None, None, None, None]),
        (7, [1, "HẢI ĐĂNG", "NGUYEN VAN A", 7_000_000, 0, 7_000_000, 4_810_000]),
        (8, [2, "TỐ UYÊN", "TRAN THI B", 6_000_000, 500_000, 6_500_000, 4_995_000]),
        (9, ["TỔNG CỘNG", None, None, 13_000_000, 500_000, 13_500_000, 9_805_000]),
    ], **kw)


# =============================================================================================
# BT1 · ĐỌC THEO NGHĨA, KHÔNG THEO VỊ TRÍ
# =============================================================================================
def test_bt1_doi_thu_tu_cot_thi_ket_qua_khong_doi():
    """Đo trên 21 tệp visa: BỐN kiểu bảng khác nhau (CAN/UK, Lẻ Châu Âu, Úc, Mỹ), cột nằm ở vị trí
    khác nhau, tiêu đề ở hàng 5 hoặc hàng 7. Đếm cột theo vị trí là hỏng ngay tệp thứ hai."""
    a = BT.doc_tep(_bang_chuan(), "QUYẾT TOÁN VISA CAN THÁNG 03.2026.xlsx")
    # Cùng nội dung, ĐẢO thứ tự cột và đẩy tiêu đề xuống hàng 7.
    b = BT.doc_tep(_tep([
        (7, ["STT", "Phí LSQ", "Tên khách hàng", "Tổng thu", "Sale", "Giá bán", "Thu khác"]),
        (9, [1, 4_810_000, "NGUYEN VAN A", 7_000_000, "HẢI ĐĂNG", 7_000_000, 0]),
        (10, [2, 4_995_000, "TRAN THI B", 6_500_000, "TỐ UYÊN", 6_000_000, 500_000]),
        (11, ["TỔNG CỘNG", 9_805_000, None, 13_500_000]),
    ]), "QUYẾT TOÁN VISA CAN THÁNG 03.2026.xlsx")
    assert (a["tong_thu"], a["tong_chi"]) == (13_500_000, 9_805_000)
    assert (b["tong_thu"], b["tong_chi"]) == (13_500_000, 9_805_000), \
        "đảo thứ tự cột mà kết quả đổi nghĩa là bộ đọc đang đếm theo VỊ TRÍ"
    assert [x["ten_khach"] for x in a["dong"]] == [x["ten_khach"] for x in b["dong"]]


# =============================================================================================
# BT2 · KHÔNG TỰ QUY ĐỔI NGOẠI TỆ
# =============================================================================================
def test_bt2_khoan_ngoai_te_KHONG_duoc_tu_quy_doi():
    """Bảng Úc ghi `PHÍ VISA (AUD) 436,2 | TỶ GIÁ 18.500 | TT 8.069.700`.

    Chủ tịch chốt 16/9/2026: tỷ giá do NHÂN VIÊN tự nhập tại từng thời điểm, kèm chứng từ. Con số
    VND sẵn trong tệp không dùng được để ghi: không ai biết tỷ giá 18.500 ấy của ngày nào, lấy ở
    đâu, là giá niêm yết hay giá thực tế đã chuyển khoản.
    """
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "GIÁ THU\n(VNĐ)", "PHÍ VISA \n(AUD)", "TỶ GIÁ", "TT"]),
        (7, [1, "Phương Nhi", "LE PHAN VIEN HY", 10_000_000, 436.2, 18_500, 8_069_700]),
        (8, ["TỔNG CỘNG", None, None, 10_000_000, 436.2, 18_500, 8_069_700]),
    ]), "VTD04.2026 QT VISA ÚC.xlsx")

    assert len(d["dong"]) == 1
    x = d["dong"][0]
    assert x["cho_ty_gia"] is True
    assert x["ngoai_te"] and x["ngoai_te"][0]["tien_te"] == "AUD"
    assert x["ngoai_te"][0]["so_tien_goc"] == 436.2, "phải giữ SỐ GỐC bằng đồng tiền gốc"
    assert x["chi"] == 0, \
        ("KHÔNG được cộng 8.069.700 vào chi: đó là số tệp tự nhân với một tỷ giá không ai biết "
         "của ngày nào")
    assert x["lai"] is None, \
        "còn khoản chờ tỷ giá thì CHƯA có lãi – trừ thiếu chi ra một con số lãi cao hơn sự thật"
    assert d["lai"] is None and d["so_cho_ty_gia"] == 1
    assert any("TỶ GIÁ" in t.upper() or "ty-gia" in t for t in d["thieu"]), \
        "phải chỉ người lập sang Sổ tỷ giá, không im lặng"


# =============================================================================================
# BT3 · KHÔNG ĐỌC DÒNG TỔNG CỘNG THÀNH MỘT KHÁCH
# =============================================================================================
def test_bt3_dong_tong_cong_khong_phai_mot_khach():
    """Đọc nhầm một dòng ấy là nhân đôi tiền của cả tháng, và nhân đôi ÊM RU vì tổng vẫn 'khớp'
    với chính nó – không phép cộng nào lệch, không ai nhìn ra."""
    d = BT.doc_tep(_bang_chuan(), "QUYẾT TOÁN VISA CAN THÁNG 03.2026.xlsx")
    assert len(d["dong"]) == 2, f"phải đúng 2 khách, đang đọc {len(d['dong'])}"
    assert d["tong_thu"] == 13_500_000, "đọc thêm dòng tổng là ra 27.000.000 – gấp đôi"


# =============================================================================================
# BT4 · LÃI LÀ HIỆU SỐ, KHÔNG PHẢI SỐ CHÉP LẠI
# =============================================================================================
def test_bt4_lai_la_thu_tru_chi_KHONG_doc_cot_loi_nhuan_trong_tep():
    """Chủ tịch chốt 16/9/2026: "doanh thu − chi phí = lợi nhuận, viết theo cấu trúc này."

    Cột 'LỢI NHUẬN' trong tệp là số DẪN XUẤT. Khi nó lệch với hiệu số thì cái lệch ấy chính là thứ
    cần nhìn thấy, không phải thứ để chép lại – ở đây tệp ghi lãi 9.999.999 trong khi thu trừ chi
    ra 2.190.000.
    """
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "GIÁ THU", "PHÍ VISA", "PHÍ ĐH", "LỢI NHUẬN"]),
        (6, [1, "HẢI ĐĂNG", "DO THI THAO", 3_200_000, 900_000, 110_000, 9_999_999]),
        (7, ["TỔNG CỘNG", None, None, 3_200_000, 900_000, 110_000, 9_999_999]),
    ]), "QUYẾT TOÁN VISA LẺ T3.2026.xlsx")
    x = d["dong"][0]
    assert x["thu"] == 3_200_000
    assert x["chi"] == 1_010_000, "phí visa + phí ĐH, máy cộng từ các cột"
    assert x["lai"] == 2_190_000, "lãi phải là HIỆU SỐ, không phải 9.999.999 chép từ tệp"
    assert all(k["so_tien"] != 9_999_999 for k in x["khoan_chi"]), \
        "cột LỢI NHUẬN không được lọt vào danh sách khoản chi"
    # Và bộ đọc phải BIẾT nó là số dẫn xuất, chứ không phải "cột lạ không nhận ra tên": báo nó ra
    # cho người lập là bắt họ đi giải thích một cột hoàn toàn bình thường.
    assert not any("LỢI NHUẬN" in n.upper() for n in d["cot_khong_nhan_ra"]), \
        "LỢI NHUẬN là số DẪN XUẤT đã biết – phải bỏ qua có chủ ý, không báo là cột lạ"
    assert all(o["so_tien"] != 9_999_999 for o in x["o_khong_nhan_ra"])


# =============================================================================================
# BT5 · CỘT CÓ TIỀN MÀ KHÔNG NHẬN RA TÊN THÌ PHẢI NÊU RA
# =============================================================================================
def test_bt5_cot_co_tien_khong_nhan_ra_thi_NOI_RA_chu_khong_bo_im_lang():
    """Đúng luật đã cứu 199.500.000 đồng ở ô lạc ngày 16/9: bỏ im lặng thì không ai biết để tìm.

    Đo trên 49 tệp: còn 6 cột như thế ('Người dịch', 'HÓA ĐƠN', 'VP VFS'). Bộ đọc KHÔNG đoán chúng
    là thu hay chi – đoán sai một cột là sai cả một tháng.
    """
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "GIÁ THU", "Người dịch"]),
        (6, [1, "HẢI ĐĂNG", "DO THI THAO", 3_200_000, 450_000]),
        (7, ["TỔNG CỘNG", None, None, 3_200_000, 450_000]),
    ]), "QUYẾT TOÁN VISA LẺ T3.2026.xlsx")
    assert "Người dịch" in d["cot_khong_nhan_ra"]
    assert any("Người dịch" in t for t in d["thieu"]), "phải nêu tên cột ra cho người lập"
    x = d["dong"][0]
    assert x["chi"] == 0 and x["thu"] == 3_200_000, \
        "không được đoán 450.000 là chi hay thu – chỉ được NÊU RA"
    assert any(o["so_tien"] == 450_000 for o in x["o_khong_nhan_ra"])


# =============================================================================================
# BT6 · TIÊU ĐỀ MỘT HÀNG – KHÔNG ĐƯỢC ĂN MẤT DÒNG KHÁCH ĐẦU TIÊN
# =============================================================================================
def test_bt6_tieu_de_MOT_hang_khong_duoc_mat_dong_khach_dau_tien():
    """LỖI BỘ ĐỌC NÀY ĐÃ MẮC. Bản đầu luôn nhảy hai hàng sau tiêu đề, đúng với bảng tiêu đề lồng
    hai hàng và SAI với bảng một hàng.

    Bắt được trên 'QUYẾT TOÁN VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY': tệp có đúng hai khách, bộ đọc
    lấy một, ra 3.200.000 trong khi dòng TỔNG CỘNG của chính tệp ghi 6.400.000. Mất đúng một nửa,
    và mất im lặng.
    """
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "QUỐC GIA", "GIÁ THU", "PHÍ VISA"]),
        (6, [1, "HẢI ĐĂNG", "DO THI THAO NHUNG", "NHATBAN", 3_200_000, 1_700_000]),
        (7, [2, "HẢI ĐĂNG", "PHAM VO TUAN ANH", "NHATBAN", 3_200_000, 1_600_000]),
        (8, ["TỔNG CỘNG", None, None, None, 6_400_000, 3_300_000]),
    ]), "QUYẾT TOÁN VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY.xlsx")
    assert len(d["dong"]) == 2, f"phải đủ HAI khách, đang đọc {len(d['dong'])}"
    assert d["tong_thu"] == 6_400_000, "mất dòng đầu là ra 3.200.000 – đúng một nửa"


# =============================================================================================
# BT7 · Ô GỘP Ở HÀNG DỮ LIỆU KHÔNG ĐƯỢC CỘNG HAI LẦN
# =============================================================================================
def test_bt7_o_gop_o_hang_du_lieu_khong_duoc_cong_hai_lan():
    """LỖI BỘ ĐỌC NÀY ĐÃ MẮC. Trải ô gộp ra là ĐÚNG cho hàng tiêu đề (mọi cột dưới một tiêu đề gộp
    phải đọc được tiêu đề ấy) và SAI hẳn cho hàng dữ liệu.

    Đo trên 49 tệp: trải ô gộp ở hàng dữ liệu cho tổng thu 10.359.011.855 đ trong khi chính các tệp
    tự khai 5.202.295.011 đ – gần đúng GẤP ĐÔI. Con số gấp đôi ấy trông vẫn hợp lý nếu không ai đi
    đối chiếu, và đó là điều nguy hiểm của nó.
    """
    # Tiêu đề GỘP trên hai cột và ô dữ liệu cũng GỘP trên đúng hai cột ấy – y như bảng visa Mỹ.
    # Phải gộp cả tiêu đề, nếu không cột thứ hai không mang vai trò nào và phép thử không kiểm được
    # gì (bản đầu của phép thử này mắc đúng lỗi ấy: bẻ mã mà nó vẫn xanh).
    # Cột gộp phải là cột CỘNG DỒN ('Giá bán'), không phải 'Tổng thu'. Ô 'Tổng thu' được GÁN chứ
    # không cộng, nên đọc nó hai lần vẫn ra đúng một con số – bản đầu của phép thử này dùng
    # 'Tổng thu' và vì thế bẻ mã mà nó vẫn xanh. Lỗi thật chỉ lộ ra ở cột cộng dồn.
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "Giá bán", None, "Phí LSQ"]),
        (6, [1, "HẢI ĐĂNG", "NGUYEN VAN A", 7_000_000, None, 4_810_000]),
        (7, ["TỔNG CỘNG", None, None, 7_000_000, None, 4_810_000]),
    ], gop=("D5:E5", "D6:E6")), "QUYẾT TOÁN VISA CAN THÁNG 03.2026.xlsx")
    assert d["tong_thu"] == 7_000_000, \
        f"ô 'Giá bán' gộp hai cột bị cộng hai lần – ra {d['tong_thu']:,.0f} thay vì 7.000.000"


# =============================================================================================
# BT8 · Ô TỔNG CỘNG CỦA TỆP LỆCH THÌ NÓI RA, VÀ LẤY THEO TỔNG CÁC DÒNG
# =============================================================================================
def test_bt8_o_tong_cua_tep_lech_thi_noi_ra_va_lay_theo_tong_cac_dong():
    """Đo 16/9/2026: ô TỔNG CỘNG của 'QUYẾT TOÁN OUTBOUND LẺ T01.2026' là `=SUM(H6:H52)` trong khi
    bảng chạy tới hàng 55 – BA khách cuối nằm NGOÀI vùng cộng, 19.970.000 đ. Tờ quyết toán ấy báo
    thiếu ngần ấy tiền từ lúc lập tới nay.

    Nên VTOS cộng từ DÒNG, không chép ô tổng: chép ô tổng là chép luôn cái sót. Nhưng cũng không
    được im lặng – chỗ lệch là việc người lập phải biết.
    """
    d = BT.doc_tep(_tep([
        (5, ["STT", "SALES", "TÊN KHÁCH", "TỔNG THU", "GIÁ NET"]),
        (6, [1, "HẢI ĐĂNG", "NGUYEN VAN A", 6_790_000, 6_240_000]),
        (7, [2, "KIM LOAN", "TRAN THI B", 6_590_000, 6_040_000]),
        # Ô tổng chỉ cộng hàng 6, bỏ sót hàng 7 – đúng kiểu SUM hụt vùng.
        (8, ["TỔNG CỘNG", None, None, 6_790_000, 6_240_000]),
    ]), "QUYẾT TOÁN OUTBOUND LẺ T01.2026_MaiNguyen.xlsx")
    assert d["tong_thu"] == 13_380_000, "phải cộng từ DÒNG, không chép ô tổng của tệp"
    assert d["tong_trong_tep"] == 6_790_000
    assert any("TỔNG CỘNG" in t and "lệch" in t for t in d["thieu"]), \
        "lệch giữa ô tổng và tổng các dòng phải được NÓI RA"


# =============================================================================================
# BT9 · KỲ ĐỌC TỪ TÊN TỆP; THIẾU NĂM THÌ BÁO, KHÔNG ĐIỀN HỘ
# =============================================================================================
def test_bt9_ky_doc_tu_ten_tep_va_thieu_nam_thi_bao():
    """Sáu cách viết kỳ, đo trên 49 tệp. Và sáu tệp visa Mỹ chỉ nói THÁNG, không nói NĂM.

    Điền hộ 2026 vì "các tệp khác đều 2026" là đoán – đoán sai một lần là cả một tháng tiền nằm
    nhầm năm tài chính.
    """
    assert BT.ky_tu_ten_tep("QUYẾT TOÁN VISA CAN THÁNG 03.2026.xlsx") == (2026, 3)
    assert BT.ky_tu_ten_tep("QT OUTBOUND GHÉP LE T01.26- ĐH PHẠM THÚY VY.xlsx") == (2026, 1)
    assert BT.ky_tu_ten_tep("VTD04.2026 QT VISA ÚC.xlsx") == (2026, 4)
    assert BT.ky_tu_ten_tep("QTOB LE 02.2026 - ĐH HỒNG VY .xlsx") == (2026, 2)
    # Chỉ nói tháng: trả về năm RỖNG, không điền hộ.
    assert BT.ky_tu_ten_tep("QUYẾT TOÁN VISA MỸ THÁNG 4.xlsx") == (None, 4)
    # Một NGÀY đầy đủ không phải một tháng – đọc nhầm là xếp một đoàn vào bảng tháng.
    assert BT.ky_tu_ten_tep("QTT LAND VĨNH HY 03.03.2026 - SALE DIỆU TRINH VTD).xlsx") is None

    d = BT.doc_tep(_bang_chuan(), "QUYẾT TOÁN VISA MỸ THÁNG 4.xlsx")
    assert d["ky"] == (None, 4)
    assert any("không nói năm" in t.lower() or "KHÔNG nói năm" in t for t in d["thieu"]), \
        "thiếu năm thì phải báo, không im lặng lấy năm nay"
    assert d["loai_dich_vu"] == "VISA"


# =============================================================================================
# BT10 · BỘ NÀY KHÔNG GHI GÌ
# =============================================================================================
def test_bt10_bo_doc_nay_khong_ghi_mot_dong_nao():
    """Đọc và GHI là hai bước riêng – đó là cả lý do bộ đọc này tách khỏi cửa nạp. Một lời gọi ghi
    lọt vào đây thì bước 'xem trước' không còn là xem trước nữa, và không ai nhận ra."""
    import ast
    cay = ast.parse(open(BT.__file__, encoding="utf-8").read())
    cam = {"add", "commit", "flush", "delete", "execute", "merge", "bulk_save_objects"}
    # Chỉ soi lời gọi trên một PHIÊN cơ sở dữ liệu. Soi theo tên phương thức không thôi thì `set.add`
    # của Python cũng bị kể là ghi – phép thử kêu oan là phép thử lần sau không ai đọc.
    phien = {"db", "s", "ss", "sess", "session", "conn"}
    thay = [f"dòng {n.lineno}: .{n.func.attr}()"
            for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in cam
            and isinstance(n.func.value, ast.Name) and n.func.value.id in phien]
    assert not thay, f"bộ ĐỌC đang gọi lệnh ghi cơ sở dữ liệu: {thay}"
    assert "Session" not in open(BT.__file__, encoding="utf-8").read(), \
        "bộ đọc không được nhận phiên cơ sở dữ liệu"
