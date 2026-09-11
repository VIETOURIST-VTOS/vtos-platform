# -*- coding: utf-8 -*-
"""Bộ đọc KHO QUYẾT TOÁN CŨ – 604 tệp tháng 1–6/2026 do Điều hành lập bằng Excel tự do.

VÌ SAO KHÔNG DÙNG BỘ NẠP MẪU CHUẨN CHO KHO NÀY

app/services/nap_mau_quyet_toan.py đọc tệp do CHÍNH VTOS phát ra: sheet tên cố định, nhãn cột cố
định, dòng tiêu đề ở đúng hàng 2. Kho cũ không có gì cố định cả. Đo trên 604 tệp thật:

    108 bộ sheet KHÁC NHAU. Bộ phổ biến nhất chỉ phủ 16% số tệp; phải gom 50 bộ mới phủ 90%.
    46 tệp chỉ có đúng MỘT sheet. Nhiều nhất là 7 sheet.

Ép kho cũ đi qua bộ nạp mẫu chuẩn thì 100% bị từ chối ngay câu đầu ("tệp thiếu sheet THÔNG TIN").

NHƯNG 108 BỐ CỤC KHÔNG PHẢI 108 HÌNH DẠNG

Đọc kỹ thì chúng khác nhau ở TÊN SHEET và VỊ TRÍ CỘT, không khác ở NHÃN:

    sheet quyết toán tên là 'QUYẾT TOÁN', 'QT', 'TAYNGUYEN', 'PT14012022', 'MN002.03'…
      nhưng đều có 'Mã tour:', 'Số khách:', 'Ngày đi:', và bảng khách có 'TÊN KHÁCH HÀNG'
    sheet chi phí tên là 'CTT', 'QTT', 'CHI PHÍ', 'CHI PHI', 'CHI THỰC TẾ'…
      nhưng đều có hàng tiêu đề 'NGÀY | NỘI DUNG | ĐỐI TÁC | ĐƠN GIÁ | SL | THÀNH TIỀN'
    sheet HDV tên là 'HDV CHI', 'HDV chi', 'ỨNG', 'CTP HDV'…
      nhưng đều có 'Tổng chi', 'ỨNG', 'HOÀN ỨNG', 'CTP'

Nên bộ đọc này KHÔNG hỏi "sheet tên gì" mà hỏi "nhãn nằm ở đâu". Nó quét cả workbook, tìm nhãn, rồi
đọc từ chỗ tìm được. Một bộ đọc cho cả 108 bố cục, và bố cục thứ 109 tháng sau cũng đọc được nếu
người lập vẫn gõ những chữ ấy.

BA ĐIỀU BỘ ĐỌC NÀY TỰ CẤM MÌNH

1. KHÔNG ĐOÁN MÃ TOUR. Không tìm thấy 'Mã tour:' thì trả về rỗng và nói ra, chứ không suy từ tên tệp.
   Tên tệp kho cũ đặt bằng tay ("QT TOUR NHA TRANG 05.06.26"), suy ra mã là suy ra sai.

2. KHÔNG ĐỌC Ô TỔNG. Mọi tổng cộng lại từ dòng. Lý do đo được trên tệp Nha Trang: ô tổng một nhóm
   ghi 3.990.000 trong khi năm dòng của chính nhóm ấy cộng lại được 4.200.000.

3. KHÔNG GHI GÌ. Tệp này chỉ ĐỌC và CHUẨN HOÁ. Phần quyết định có nạp hay không, và nạp thì có đè
   lên dữ liệu đang có hay không, nằm ở chong_trung.py – vì đó là quyết định về dữ liệu thật của
   công ty, không phải quyết định của một hàm đọc tệp.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO

# ---------------------------------------------------------------------------------------------
# Nhãn – rút từ việc đọc 604 tệp thật, không phải từ tưởng tượng
# ---------------------------------------------------------------------------------------------

NHAN_MA_TOUR = ("MÃ TOUR", "MA TOUR", "TOURCODE", "TOUR CODE")
NHAN_TEN_TOUR = ("TÊN TOUR", "TEN TOUR")
NHAN_SO_KHACH = ("SỐ KHÁCH", "SO KHACH", "GROUP SIZE", "SỐ LƯỢNG")
NHAN_HDV = ("HƯỚNG DẪN VIÊN", "HDV", "TL")
NHAN_NGAY_DI = ("NGÀY ĐI", "KHỞI HÀNH", "NGAY DI")
NHAN_NGAY_VE = ("NGÀY VỀ", "KẾT THÚC", "NGAY VE")
NHAN_TEN_DOAN = ("TÊN ĐOÀN", "TEN DOAN")

# Hàng tiêu đề của BẢNG CHI: nhận ra bằng việc có mặt đồng thời vài nhãn này.
TD_CHI_BAT_BUOC = ("NỘI DUNG", "NOI DUNG", "DỊCH VỤ", "DICH VU", "CHI PHÍ", "DIỄN GIẢI",
                   "TÊN DỊCH VỤ", "DESCRIPTION")
TD_CHI_KEM = ("THÀNH TIỀN", "THANH TIEN", "ĐƠN GIÁ", "DON GIA", "TỔNG CHI", "TỔNG TIỀN", "TOTAL",
              "PRICE", "QUANTITY", "AMOUNT")

# SHEET PHẢI BỎ QUA: mẫu trống còn sót lại trong chính tệp quyết toán.
#
# Nhiều tệp tour châu Âu mang theo một sheet tên 'MẪU' – bản mẫu trắng của năm 2020 mà người lập
# quên xoá, có đủ hàng tiêu đề và mấy chục dòng ví dụ ghi ngày 26/01/2020. Bộ đọc nhận ra nó là một
# bảng chi hợp lệ và đọc luôn: giá vốn của tệp ra 14.183 trong khi số thật là 2.188.613.306.
#
# Con số 14.183 ấy là EUR, không phải đồng – tức là vừa sai nguồn vừa sai đơn vị, mà vẫn là một số
# nên không có gì đỏ lên.
SHEET_BO_QUA = ("MẪU", "MAU", "TEMPLATE", "FORM", "HƯỚNG DẪN", "SHEET1", "SHEET2", "SHEET3")
# Hàng tiêu đề của BẢNG KHÁCH.
TD_KHACH = ("TÊN KHÁCH HÀNG", "TEN KHACH HANG", "HỌ VÀ TÊN", "HỌ TÊN", "TÊN KHÁCH", "FULL NAME")

# Những dòng KHÔNG phải dòng dữ liệu – gặp thì bỏ qua (không phải dừng: nhiều tệp có tổng nhóm ở
# giữa bảng rồi lại tiếp tục nhóm sau).
DONG_TONG = ("TỔNG", "TONG", "CỘNG", "CONG", "TOTAL", "SUM")
# Tiêu đề nhóm trong bảng chi: "A. LAND TOUR", "II/ CHI PHÍ:", "B. TRẺ EM"…
RE_NHOM = re.compile(r"^\s*(?:[IVX]+\s*[/.]|[A-H]\s*[.)])\s*", re.I)
# Phần THU trong sheet chiết tính, để tách khỏi phần CHI.
MOC_THU = ("I/GIÁ TOUR", "I/ GIÁ TOUR", "A. THU", "GIÁ TOUR:")
MOC_CHI = ("II/ CHI PHÍ", "II/CHI PHÍ", "B. CHI PHÍ", "II/ CHI PHI")

NHAN_UNG = ("TIỀN CTY ỨNG", "TIỀN ỨNG", "CTY ỨNG", "ỨNG")
NHAN_HOAN_UNG = ("HOÀN ỨNG",)
NHAN_CTP = ("CTP HDV", "CTP", "CÔNG TÁC PHÍ")


# ---------------------------------------------------------------------------------------------
# Dùng chung
# ---------------------------------------------------------------------------------------------

def _chu(v) -> str:
    return "" if v is None else " ".join(str(v).split())


def _hoa(v) -> str:
    return _chu(v).upper()


def _so(v):
    """Số tiền. Rỗng vào thì RỖNG ra – quy ước K2, không suy thành 0."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = _chu(v).replace(" ", "")
    # Bỏ đuôi chữ: "28 khách", "1.290.000đ", "100,000 VND"
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in ("-", ".", ","):
        return None
    # "1.290.000" và "1,290,000" đều là một triệu hai chín. "1.290,50" thì dấu phẩy là thập phân.
    if s.count(",") and s.count("."):
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[-1]) == 3):
        s = s.replace(".", "")
    elif s.count(",") >= 1:
        s = s.replace(",", "") if len(s.split(",")[-1]) == 3 else s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    t = _chu(v)
    if not t:
        return None
    # "14-16/06/2026" và "25 - 28/06/2026": lấy ngày ĐẦU.
    m = re.search(r"(\d{1,2})\s*[-–]\s*\d{1,2}[/.](\d{1,2})[/.](\d{2,4})", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def _ben_phai(ws, r: int, c: int, xa: int = 6):
    """Giá trị của nhãn nằm ở ô KHÔNG RỖNG đầu tiên bên phải.

    Kho cũ đặt nhãn ở cột 1, cột 2 hoặc cột 3 tuỳ tệp, và giá trị có khi cách một ô trống vì người
    lập gộp ô cho đẹp. Đếm cứng "cột nhãn + 1" là hỏng ở một phần ba số tệp.
    """
    for j in range(c + 1, min(c + 1 + xa, ws.max_column + 1)):
        v = ws.cell(r, j).value
        if v not in (None, ""):
            return v
    return None


def _tim_nhan(ws, nhan: tuple, het_hang: int = 14):
    """Tìm một nhãn trong vùng đầu sheet. Trả (giá trị, hàng, cột) hoặc (None, None, None)."""
    for r in range(1, min(het_hang, ws.max_row) + 1):
        for c in range(1, min(ws.max_column, 14) + 1):
            t = _hoa(ws.cell(r, c).value).rstrip(":").strip()
            if not t:
                continue
            for n in nhan:
                # So khớp ĐẦU chuỗi: "Mã tour:" khớp "MÃ TOUR", nhưng "Mã tour cũ" cũng khớp –
                # chấp nhận, vì nhầm ở đây chỉ làm đọc thừa chứ không làm đọc sai số tiền.
                if t == n or t.startswith(n + " ") or t == n + ":":
                    v = _ben_phai(ws, r, c)
                    if v not in (None, ""):
                        return v, r, c
    return None, None, None


def _sach_ma_tour(v) -> str:
    """Cắt mã tour về đúng phần mã.

    Kho cũ gõ ô 'Mã tour:' theo nhiều kiểu, và nhiều tệp ghi kèm cả khoảng ngày vào cùng ô:

        "SM003.04.160126 (16/01/2026 - 19/01/2026)"
        "NT001.03100726 – NHA TRANG"

    Để nguyên thì mã ấy không khớp được với chuyến nào trong VTOS, và cả tệp rơi vào nhóm 'không
    thấy chuyến' dù mã hoàn toàn đúng ở phần đầu. Cắt tại dấu ngoặc, gạch ngang hay khoảng trắng
    đầu tiên là lấy đúng phần mã.

    Chỉ cắt khi phần đầu TRÔNG GIỐNG một mã (có chữ và số, không có khoảng trắng). Không giống thì
    giữ nguyên cả chuỗi và để phần kiểm nói ra – cắt bừa còn tệ hơn không cắt.
    """
    t = _chu(v)
    if not t:
        return ""
    dau = re.split(r"[(\[]|\s[-–—]\s|\s{2,}|\s", t, maxsplit=1)[0].strip(" -–—:")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/]{2,39}", dau) and re.search(r"\d", dau):
        return dau[:40]
    return t[:40]


def _la_dong_tong(ws, r: int, het_cot: int) -> bool:
    for c in range(1, het_cot + 1):
        t = _hoa(ws.cell(r, c).value)
        if t and any(t.startswith(k) for k in DONG_TONG):
            return True
    return False


# ---------------------------------------------------------------------------------------------
# Nhận diện bảng
# ---------------------------------------------------------------------------------------------

def _hang_tieu_de_chi(ws):
    """Hàng tiêu đề của bảng chi phí: hàng có ÍT NHẤT một nhãn bắt buộc và một nhãn kèm."""
    for r in range(1, min(ws.max_row, 30) + 1):
        o = [_hoa(ws.cell(r, c).value) for c in range(1, min(ws.max_column, 20) + 1)]
        co_bb = any(any(x == n or x.startswith(n) for n in TD_CHI_BAT_BUOC) for x in o if x)
        co_kem = any(any(x == n or x.startswith(n) for n in TD_CHI_KEM) for x in o if x)
        if co_bb and co_kem:
            return r
    return None


def _hang_tieu_de_khach(ws):
    for r in range(1, min(ws.max_row, 30) + 1):
        for c in range(1, min(ws.max_column, 20) + 1):
            t = _hoa(ws.cell(r, c).value)
            if t and any(t.startswith(n) for n in TD_KHACH):
                return r
    return None


def _map_cot(ws, hang: int) -> dict:
    """{NHÃN VIẾT HOA: chỉ số cột} của một hàng tiêu đề."""
    ra = {}
    for c in range(1, ws.max_column + 1):
        t = _hoa(ws.cell(hang, c).value)
        if t and t not in ra:
            ra[t] = c
    return ra


def _lay(m: dict, *ten):
    for t in ten:
        for k, c in m.items():
            if k == t or k.startswith(t):
                return c
    return None


# ---------------------------------------------------------------------------------------------
# Đọc từng phần
# ---------------------------------------------------------------------------------------------

def _doc_dau(wb) -> dict:
    """Thông tin chuyến. Quét MỌI sheet – tệp nào cũng có, nhưng không tệp nào ở cùng một chỗ."""
    ra = {"ma_tour": "", "ten_tour": "", "so_khach": None, "hdv": "",
          "ngay_di": None, "ngay_ve": None, "ten_doan": ""}
    for ws in wb.worksheets:
        if not ra["ma_tour"]:
            v, _, _ = _tim_nhan(ws, NHAN_MA_TOUR)
            ra["ma_tour"] = _sach_ma_tour(v)
        if not ra["ten_tour"]:
            v, _, _ = _tim_nhan(ws, NHAN_TEN_TOUR)
            ra["ten_tour"] = _chu(v)[:160]
        if ra["so_khach"] is None:
            v, _, _ = _tim_nhan(ws, NHAN_SO_KHACH)
            n = _so(v)
            ra["so_khach"] = int(n) if n is not None and 0 < n < 1000 else None
        if not ra["hdv"]:
            v, _, _ = _tim_nhan(ws, NHAN_HDV)
            ra["hdv"] = _chu(v)[:120]
        if ra["ngay_di"] is None:
            v, _, _ = _tim_nhan(ws, NHAN_NGAY_DI)
            ra["ngay_di"] = _ngay(v)
        if ra["ngay_ve"] is None:
            v, _, _ = _tim_nhan(ws, NHAN_NGAY_VE)
            ra["ngay_ve"] = _ngay(v)
        if not ra["ten_doan"]:
            v, _, _ = _tim_nhan(ws, NHAN_TEN_DOAN)
            ra["ten_doan"] = _chu(v)[:120]
    return ra


def _doc_khach(ws) -> list[dict]:
    """Bảng khách: mỗi dòng một người.

    DOANH THU CỦA MỘT KHÁCH LÀ TỔNG CÁC CỘT CON DƯỚI NHÃN 'THU', KHÔNG PHẢI Ô 'TỔNG THU'

    Bảng khách của kho cũ có tiêu đề HAI TẦNG và số cột con khác nhau theo từng loại tour:

        trong nước : THU = [GIÁ BÁN, THU KHÁC]                         rồi TỔNG THU
        EU         : THU = [GIÁ BÁN, PHÍ LSQ, JTRAVEL, PHÍ KHÁC]       rồi TỔNG THU
        UK         : THU = [GIÁ TOUR, PHÍ LSQ, KHÁC]                   rồi TỔNG THU

    Đọc cứng "GIÁ BÁN" thì tour châu Âu mất trắng phần phí lãnh sự quán – đo được: trên 232 tệp,
    cách đọc cũ ra 6,7 tỷ trong khi số thật là 50,0 tỷ.

    Nên quy tắc là: tìm cột 'TỔNG THU', tìm nhãn 'THU' đứng một mình bên trái nó, rồi CỘNG MỌI CỘT
    NẰM GIỮA HAI CHỖ ẤY. Cộng lại từ cột con chứ không đọc ô 'TỔNG THU' – vẫn đúng nguyên tắc tin
    dòng, không tin tổng.

    Tiêu đề hai tầng nằm ở đâu cũng được: tệp trong nước đặt 'THU' cùng hàng với 'TÊN KHÁCH HÀNG',
    tệp UK đặt 'THU' ở hàng TRÊN. Nên quét cả ba hàng quanh hàng tìm được tên.
    """
    h = _hang_tieu_de_khach(ws)
    if h is None:
        return []
    hang = [r for r in (h - 1, h, h + 1) if 1 <= r <= ws.max_row]
    m_all = {r: _map_cot(ws, r) for r in hang}

    def tim(*ten):
        """(cột, hàng) của nhãn đầu tiên khớp, quét từ hàng trên xuống."""
        for t in ten:
            for r in hang:
                c = _lay(m_all[r], t)
                if c:
                    return c, r
        return None, None

    c_ten, r_ten = tim("TÊN KHÁCH HÀNG", "TEN KHACH HANG", "HỌ VÀ TÊN", "HỌ TÊN", "TÊN KHÁCH",
                       "FULL NAME")
    if c_ten is None:
        return []
    c_sale, _ = tim("SALES", "SALE", "NGƯỜI BÁN")
    c_code, _ = tim("CODE", "MÃ ĐẶT CHỖ", "PNR")
    c_tong, r_tong = tim("TỔNG THU", "TONG THU")

    # Cột 'THU' đứng MỘT MÌNH (nhãn tầng trên), không phải "TỔNG THU" hay "THU KHÁC".
    c_thu = r_thu = None
    for r in hang:
        for k, c in m_all[r].items():
            if k == "THU" and (c_tong is None or c < c_tong):
                if c_thu is None or c < c_thu:
                    c_thu, r_thu = c, r

    cot_thu = []
    if c_thu is not None and c_tong is not None and c_tong > c_thu:
        cot_thu = list(range(c_thu, c_tong))
    else:
        for t in ("GIÁ BÁN", "GIÁ TOUR", "THU KHÁC", "PHÍ LSQ", "PHÍ KHÁC", "KHÁC"):
            c, _ = tim(t)
            if c and c not in cot_thu and (c_tong is None or c < c_tong):
                cot_thu.append(c)

    # Dòng dữ liệu bắt đầu SAU hàng tiêu đề thấp nhất đã dùng.
    dau = max([r for r in (r_ten, r_tong, r_thu) if r] or [h]) + 1
    ra = []
    for r in range(dau, ws.max_row + 1):
        ten = _chu(ws.cell(r, c_ten).value)
        if not ten:
            continue
        if any(_hoa(ten).startswith(k) for k in DONG_TONG):
            break
        v = [_so(ws.cell(r, c).value) for c in cot_thu]
        v = [x for x in v if x is not None]
        c_gb = cot_thu[0] if cot_thu else None
        ra.append({
            "_hang": r, "ho_ten": ten[:200],
            "sale": _chu(ws.cell(r, c_sale).value)[:120] if c_sale else "",
            # gia_ban giữ cột ĐẦU của khối THU (giá tour thuần); thu_khac là phần còn lại. Tách hai
            # để sau này soát giá bán theo bảng giá mà không lẫn phí lãnh sự quán vào.
            "gia_ban": _so(ws.cell(r, c_gb).value) if c_gb else None,
            "thu_khac": (round(sum(v[1:]), 2) if len(v) > 1 else None),
            "tong_thu": round(sum(v), 2) if v else None,
            "ma_dat_cho": _chu(ws.cell(r, c_code).value)[:40] if c_code else "",
        })
    return ra


def _doc_bang_tien(ws, hang_td: int) -> list[dict]:
    """Bảng chi/thu theo hàng tiêu đề đã tìm được. Giữ cả tiêu đề NHÓM để biết dòng thuộc mục nào."""
    m = _map_cot(ws, hang_td)
    c_nd = _lay(m, "NỘI DUNG", "NOI DUNG", "DỊCH VỤ", "DICH VU", "CHI PHÍ", "DIỄN GIẢI")
    c_dt = _lay(m, "ĐỐI TÁC", "DOI TAC", "PARTNER", "NHÀ CUNG CẤP", "NCC")
    c_dg = _lay(m, "ĐƠN GIÁ", "DON GIA", "PRICE", "GIÁ")
    c_sl = _lay(m, "SL", "SỐ LƯỢNG", "QUANTITY", "QTY")
    c_he = _lay(m, "DIỄN GIẢI", "LƯỢT TÍNH", "ĐÊM", "NIGHT", "ĐV")
    c_tt = _lay(m, "THÀNH TIỀN", "THANH TIEN", "TỔNG TIỀN", "TỔNG CHI", "TOTAL", "AMOUNT")
    c_gc = _lay(m, "GHI CHÚ", "GHI CHU", "NOTE")
    c_mst = _lay(m, "MST", "MÃ SỐ THUẾ")
    c_ht = _lay(m, "HTTT", "HÌNH THỨC THANH TOÁN", "HÌNH THỨC TT")
    c_ngay = _lay(m, "NGÀY", "NGAY", "DATE")
    if c_nd is None or c_tt is None:
        return []
    het_cot = max(x for x in m.values())

    # VẠCH NGĂN THU / CHI: hàng "TỔNG CỘNG THU".
    #
    # Phần đầu sheet chiết tính là GIÁ TOUR (doanh thu), phần sau mới là chi phí. Bản đầu chỉ nhận
    # ra vạch ấy qua mấy mốc chữ ("I/GIÁ TOUR", "II/ CHI PHÍ") – tệp nào viết khác là cả khối doanh
    # thu bị đếm thành giá vốn. Đo được trên một tệp: 279 triệu doanh thu chạy sang cột chi phí,
    # và giá vốn của tệp ấy phồng từ 268 triệu lên 936 triệu.
    #
    # "TỔNG CỘNG THU" thì tệp nào cũng có và đứng đúng chỗ ranh giới, nên lấy nó làm vạch.
    hang_het_thu = None
    for r in range(hang_td + 1, ws.max_row + 1):
        for c in range(1, min(het_cot, 6) + 1):
            t = _hoa(ws.cell(r, c).value)
            if t.startswith("TỔNG CỘNG THU") or t.startswith("TONG CONG THU") or t.startswith("A. TỔNG THU"):
                hang_het_thu = r
                break
        if hang_het_thu:
            break

    ra = []
    nhom = ""
    phan = ""          # "thu" hoặc "chi"
    for r in range(hang_td + 1, ws.max_row + 1):
        # Tiêu đề nhóm / mốc phần: một ô chữ, không có số tiền bên cạnh.
        chu_dau = ""
        for c in range(1, min(het_cot, 6) + 1):
            t = _chu(ws.cell(r, c).value)
            if t:
                chu_dau = t
                break
        H = _hoa(chu_dau)
        if H:
            if any(H.startswith(k) for k in MOC_THU):
                phan = "thu"
                continue
            if any(H.startswith(k) for k in MOC_CHI):
                phan = "chi"
                continue
        tt = _so(ws.cell(r, c_tt).value)
        nd = _chu(ws.cell(r, c_nd).value)
        if H and RE_NHOM.match(chu_dau) and not nd:
            nhom = chu_dau[:80]
            continue
        if _la_dong_tong(ws, r, het_cot):
            continue                     # tổng nhóm – KHÔNG đọc, máy tự cộng lại
        # DÒNG KHÔNG CÓ NỘI DUNG MÀ CÓ TIỀN LÀ DÒNG TỔNG NHÓM KHÔNG ĐỀ CHỮ.
        #
        # Nhiều tệp đặt tổng của một mục ở dòng ngay dưới, để trống hết cột chữ và chỉ ghi con số.
        # _la_dong_tong() không bắt được vì không có chữ "TỔNG" nào để bắt. Đo được: một tệp có
        # "Vé máy bay HAN - SGN - HAN 140.062.416" rồi dòng dưới lặp lại đúng 140.062.416 không tên
        # – cộng cả hai là nhân đôi một khoản vé máy bay.
        #
        # Một khoản chi thật luôn có tên Ở ĐÂU ĐÓ. Nhưng "ở đâu đó" không phải lúc nào cũng là cột
        # mà bộ đọc chọn làm 'nội dung': nhiều tệp để tên dịch vụ ở cột 1 ("Chi phí"), tên đối tác ở
        # cột 3, còn cột 'DIỄN GIẢI' thì bỏ trống. Bản đầu chỉ nhìn cột nội dung và đã bỏ nhầm hàng
        # loạt dòng chi thật – giá vốn tụt từ 105% xuống 69% so với số đã đối chiếu.
        #
        # Nên điều kiện đúng là: KHÔNG CÓ CHỮ Ở BẤT KỲ CỘT MÔ TẢ NÀO thì mới là dòng tổng.
        co_chu = any(_chu(ws.cell(r, c).value) and _so(ws.cell(r, c).value) is None
                     for c in range(1, min(c_tt, het_cot + 1)))
        if not co_chu:
            continue
        ra.append({
            "_hang": r,
            "phan": ("thu" if (hang_het_thu is not None and r <= hang_het_thu) else (phan or "chi")),
            "nhom": nhom,
            "noi_dung": nd[:200],
            "doi_tac": _chu(ws.cell(r, c_dt).value)[:200] if c_dt else "",
            "don_gia": _so(ws.cell(r, c_dg).value) if c_dg else None,
            "so_luong": _so(ws.cell(r, c_sl).value) if c_sl else None,
            "he_so": _so(ws.cell(r, c_he).value) if c_he else None,
            "thanh_tien": tt,
            "ghi_chu": _chu(ws.cell(r, c_gc).value)[:200] if c_gc else "",
            "mst": _chu(ws.cell(r, c_mst).value)[:20] if c_mst else "",
            "hinh_thuc_tt": _chu(ws.cell(r, c_ht).value)[:40] if c_ht else "",
            "ngay": _chu(ws.cell(r, c_ngay).value)[:60] if c_ngay else "",
        })
    return ra


def _doc_hdv(ws) -> dict:
    """Sheet HDV: các dòng chi, cộng với ứng / hoàn ứng / CTP nằm rải dưới bảng."""
    h = _hang_tieu_de_chi(ws)
    dong = _doc_bang_tien(ws, h) if h is not None else []
    ra = {"dong": [x for x in dong if x["thanh_tien"] is not None],
          "tien_ung": None, "hoan_ung": None, "ctp": None}
    for nhom, khoa in ((NHAN_UNG, "tien_ung"), (NHAN_HOAN_UNG, "hoan_ung"), (NHAN_CTP, "ctp")):
        for r in range(1, ws.max_row + 1):
            for c in range(1, min(ws.max_column, 10) + 1):
                t = _hoa(ws.cell(r, c).value).rstrip(":").strip()
                if t and any(t == n or t.startswith(n) for n in nhom):
                    v = _so(_ben_phai(ws, r, c, xa=8))
                    if v is not None:
                        ra[khoa] = v
                        break
            if ra[khoa] is not None:
                break
    return ra


# ---------------------------------------------------------------------------------------------
# Cửa chính
# ---------------------------------------------------------------------------------------------

def doc_tep(noi_dung: bytes, ten_tep: str = "") -> dict:
    """Đọc MỘT tệp quyết toán cũ. Chỉ đọc và chuẩn hoá – không kiểm, không ghi."""
    import openpyxl
    wb = openpyxl.load_workbook(BytesIO(noi_dung), data_only=True)

    d = {"ten_tep": ten_tep, "sheets": list(wb.sheetnames)}
    d.update(_doc_dau(wb))

    khach, thu, chi, hdv = [], [], [], {"dong": [], "tien_ung": None, "hoan_ung": None, "ctp": None}
    ngoai_te = []
    sheet_khach = sheet_chi = sheet_hdv = ""
    for ws in wb.worksheets:
        ten = _hoa(ws.title)
        if any(ten == k or ten.startswith(k) for k in SHEET_BO_QUA):
            continue
        if not khach:
            k = _doc_khach(ws)
            if k:
                khach, sheet_khach = k, ws.title
        # Sheet HDV nhận ra bằng TÊN – đây là chỗ duy nhất tên sheet mang thông tin thật, vì bảng
        # chi của HDV và bảng chi của chuyến có hình dạng giống hệt nhau.
        la_hdv = "HDV" in ten or "CTP" in ten or ten.startswith("ỨNG") or ten.startswith("UNG")
        if la_hdv and not hdv["dong"]:
            hdv, sheet_hdv = _doc_hdv(ws), ws.title
            continue
        if la_hdv:
            continue
        h = _hang_tieu_de_chi(ws)
        if h is not None:
            tte = tien_te_bang_chi(ws, h)
            if tte != "VND":
                # Bảng ngoại tệ: GIỮ dòng để người xem, nhưng KHÔNG cộng vào giá vốn VND.
                ngoai_te.append({"sheet": ws.title, "tien_te": tte,
                                 "dong": _doc_bang_tien(ws, h)})
                continue
            b = _doc_bang_tien(ws, h)
            t = [x for x in b if x["phan"] == "thu"]
            c = [x for x in b if x["phan"] != "thu"]
            if c and not chi:
                chi, sheet_chi = c, ws.title
            elif c:
                chi += c
            if t and not thu:
                thu = t

    d.update({"khach": khach, "thu": thu, "chi": chi, "hdv": hdv, "ngoai_te": ngoai_te,
              "sheet_khach": sheet_khach, "sheet_chi": sheet_chi, "sheet_hdv": sheet_hdv})
    d["tong_thu"] = tong_thu(d)
    d["tong_chi"] = tong_chi(d)
    d["thieu"] = thieu_gi(d)
    return d


def tong_thu(d: dict) -> float | None:
    """Doanh thu: ưu tiên cộng từ DÒNG KHÁCH, không có thì cộng từ phần THU của sheet chiết tính.

    Dòng khách là nguồn mịn hơn và là nguồn duy nhất nói được ai bán. Phần THU của sheet chiết tính
    là bản tóm ("NGƯỜI LỚN × 35"), dùng khi tệp không có bảng khách – 95% tệp kho cũ không có.
    """
    if d["khach"]:
        v = [x["tong_thu"] for x in d["khach"] if x["tong_thu"] is not None]
        if v:
            return round(sum(v), 2)
    v = [x["thanh_tien"] for x in d["thu"] if x["thanh_tien"] is not None]
    return round(sum(v), 2) if v else None


NGOAI_TE = ("EUR", "EURO", "GBP", "GPB", "USD", "SGD", "THB", "JPY", "CHF", "AUD", "CNY")


def tien_te_bang_chi(ws, hang_td: int) -> str:
    """Bảng chi này ghi bằng tiền gì. VND nếu không thấy dấu hiệu nào khác.

    Sheet land của tour châu Âu và UK ghi bằng EUR/GBP – "Bus 50s 8D7N … 7000" là 7.000 EUR. Cộng
    thẳng những con số ấy vào giá vốn là ra 14.183 cho một chuyến 2,19 tỷ: vừa sai nguồn tiền vừa
    sai đơn vị, mà kết quả vẫn là một con số nên không chỗ nào đỏ lên.
    """
    for r in range(max(1, hang_td - 2), min(hang_td + 2, ws.max_row) + 1):
        for c in range(1, min(ws.max_column, 20) + 1):
            t = _hoa(ws.cell(r, c).value)
            for k in NGOAI_TE:
                if t == k or t.startswith(k + " ") or t.endswith("(" + k + ")") or f"({k})" in t:
                    return "GBP" if k == "GPB" else ("EUR" if k == "EURO" else k)
    return "VND"


def tong_chi(d: dict) -> float | None:
    """Giá vốn: cộng từ dòng chi. KHÔNG cộng dòng HDV vào đây – xem giải thích dưới.

    Sheet HDV là tiền HDV tiêu trên đường, và trên phần lớn tệp nó đã nằm sẵn trong sheet chiết tính
    dưới dạng một khoản 'CTP HDV' hoặc 'PHÍ TL'. Cộng cả hai là tính hai lần. Cộng hay không là
    quyết định phải nhìn từng tệp mới biết, nên bộ đọc trả riêng hai con số và để người quyết.
    """
    v = [x["thanh_tien"] for x in d["chi"] if x["thanh_tien"] is not None]
    return round(sum(v), 2) if v else None


def tong_hdv(d: dict) -> float | None:
    v = [x["thanh_tien"] for x in d["hdv"]["dong"] if x["thanh_tien"] is not None]
    return round(sum(v), 2) if v else None


def thieu_gi(d: dict) -> list[str]:
    """Những thứ tệp này KHÔNG cho biết. Nói ra để người xử, không tự bịa ra cho đủ."""
    t = []
    if not d["ma_tour"]:
        t.append("không tìm thấy 'Mã tour' ở bất kỳ sheet nào")
    if not d["chi"]:
        t.append("không nhận ra bảng chi phí nào")
    if d["tong_thu"] is None:
        t.append("không có doanh thu: tệp không có bảng khách và cũng không có phần I/GIÁ TOUR")
    if not d["khach"]:
        t.append("không có bảng khách (chỉ có số tổng)")
    if d["ngay_di"] is None:
        t.append("không đọc được ngày đi")
    if d.get("ngoai_te"):
        tt = ", ".join(sorted({x["tien_te"] for x in d["ngoai_te"]}))
        t.append(f"có bảng chi bằng {tt} chưa quy đổi ra đồng – giá vốn đọc được KHÔNG gồm phần này")
    # Giá vốn nhỏ bất thường so với doanh thu là dấu hiệu đọc nhầm bảng hoặc nhầm đơn vị tiền.
    if d["tong_thu"] and d["tong_chi"] is not None and d["tong_chi"] < d["tong_thu"] * 0.30:
        t.append(f"giá vốn đọc được chỉ bằng {d['tong_chi']/d['tong_thu']*100:.0f}% doanh thu – "
                 f"nhiều khả năng còn bảng chi chưa đọc tới")
    return t
