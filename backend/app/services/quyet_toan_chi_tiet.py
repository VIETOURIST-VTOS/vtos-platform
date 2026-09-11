"""Lớp 2 của quyết toán tour – đọc bảng KHÁCH trong tệp quyết toán của Điều hành.

Lớp 1 (bảng tour_settlements) trả lời "chuyến này lãi bao nhiêu". Lớp 2 trả lời "lãi ấy đến từ đâu":
mỗi khách thu bao nhiêu, chi bao nhiêu, sale nào bán. Đó cũng là lớp duy nhất trả lời được câu hỏi
kiểm toán hay hỏi nhất – "cho xem chứng từ của con số này" – mà không phải mở lại tệp Excel gốc.

BỐN SHEET, VÀ VÌ SAO PHẢI ĐỌC CẢ BỐN

Tệp thật của Điều hành có bốn sheet, và chúng KHÔNG khớp nhau. Tệp Nha Trang 10/07/2026 dùng để dựng
bộ đọc này là ví dụ sống:

    QT   – bảng từng khách. Ô "Ngày đi" ghi 07/07/2026.
    CTT  – chiết tính. Ô "KHỞI HÀNH" ghi 10/07/2026, "SỐ LƯỢNG" ghi 42.
    DT   – doanh thu theo booking.
    mã tour NT001.03100726 – sáu số cuối là 10/07/26.

Hai trong ba nguồn nói 10/07, sheet QT nói 07/07, còn ô "Số khách" của QT ghi 44 trong khi CTT ghi 42
(33 người lớn + 7 trẻ em + 2 trẻ em free). Đọc mỗi sheet QT rồi tin luôn là nạp vào sổ một chuyến
không tồn tại, và kỳ kế toán lệch ba ngày – đủ để rơi sang tháng khác ở những chuyến cuối tháng.

Nên bộ đọc này đọc cả bốn sheet và ĐỐI CHIẾU. Nó KHÔNG tự chọn nguồn nào đúng: nó ghi ra từng chỗ
lệch kèm số của từng nguồn, rồi để Điều hành sửa tệp. Máy chọn hộ một lần là sai vĩnh viễn, vì sau đó
không còn dấu vết nào cho thấy đã từng có hai số.

CỘT CHI KHÔNG CỐ ĐỊNH

Tour lẻ chia chi phí thành LAND, BH, PHÍ TL, NƯỚC SUỐI, PHÍ KHÁC. Đoàn MICE chia thành LAND UK, VMB
XUẤT LẺ, TIỄN SÂN BAY, VISA UK, PHÍ KHÁCH CHI TIỀN MẶT, CTP HDV + TIPPING. Bộ đọc lấy khối cột nằm
GIỮA ô "CHI" và ô "TỔNG CHI", giữ nguyên văn nhãn, và tra mã khoản qua từ điển. Nhãn chưa có trong
từ điển thì mã để TRỐNG và vào hàng đợi chờ người xếp – không dồn vào "phí khác".
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime

# Nhãn của khối THU và mấy ô tổng. Mọi so khớp đều đi qua _kd() nên không phụ thuộc dấu và hoa/thường.
NHAN_GIA_BAN = ("GIA BAN", "GIA")
NHAN_THU_KHAC = ("THU KHAC", "PHU THU")
NHAN_TONG_THU = ("TONG THU",)
NHAN_TONG_CHI = ("TONG CHI",)
NHAN_LOI_NHUAN = ("LOI NHUAN", "LAI")
NHAN_KHACH = ("TEN KHACH HANG", "TEN KHACH", "HO TEN KHACH", "KHACH HANG")

# Ô nhãn ở khối đầu tệp -> tên trường. Giá trị nằm ở ô ngay bên phải (hoặc cách một ô, do gộp ô).
NHAN_DAU = {
    "MA TOUR": "ma_tour", "TEN TOUR": "ten_chuong_trinh", "SO KHACH": "so_khach",
    "HUONG DAN VIEN": "hdv", "HDV": "hdv", "NGAY DI": "ngay_di", "NGAY VE": "ngay_ve",
    "BIEN SO XE": "bien_so_xe", "KHOI HANH": "ngay_di", "SO LUONG": "so_khach",
}


def _kd(v) -> str:
    """Chuẩn hoá để so khớp nhãn: bỏ dấu, bỏ khoảng trắng thừa, viết hoa."""
    if v is None:
        return ""
    s = unicodedata.normalize("NFD", str(v))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().upper().rstrip(":").strip()


def _so(v):
    """Chỉ nhận số thật. Chuỗi '1.790.000' cũng nhận, nhưng ô rỗng trả None – không trả 0."""
    if isinstance(v, bool) or v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v)).replace(".", "").replace(",", ".")
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def _ngay(v):
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def ngay_tu_ma(ma: str):
    """Sáu chữ số cuối của mã tour là ddmmyy. NT001.03100726 -> 10/07/2026.

    Đây là nguồn ngày ĐỘC LẬP với mọi ô ngày trong tệp, nên nó là chỗ duy nhất bắt được lỗi gõ ngày.
    """
    if not ma or "." not in str(ma):
        return None
    d = re.sub(r"[^0-9]", "", str(ma).split(".", 1)[1])
    if len(d) > 8:
        d = d[:8]
    if len(d) < 6:
        return None
    s = d[-6:]
    try:
        return date(2000 + int(s[4:]), int(s[2:4]), int(s[:2]))
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------
# Đọc
# ---------------------------------------------------------------------------------------------

def _o_ben_phai(ws, r, c, xa=3):
    """Giá trị của nhãn nằm ở ô kế bên. Ô gộp làm nó lùi một, hai ô – nên dò tối đa `xa` ô."""
    for k in range(1, xa + 1):
        v = ws.cell(r, c + k).value
        if v not in (None, ""):
            return v
    return None


def _doc_dau(ws, den_hang: int) -> dict:
    """Khối đầu tệp: mã tour, tên chương trình, số khách, HDV, ngày đi/về, biển số xe."""
    ra: dict = {}
    for r in range(1, min(den_hang, 40)):
        for c in range(1, min(ws.max_column, 20) + 1):
            k = _kd(ws.cell(r, c).value)
            if k in NHAN_DAU and NHAN_DAU[k] not in ra:
                ra[NHAN_DAU[k]] = _o_ben_phai(ws, r, c)
    return ra


def _tim_hang_tieu_de(ws):
    """Hàng tiêu đề là hàng có ô 'TÊN KHÁCH HÀNG'. Hàng ngay dưới là tiêu đề con của THU và CHI."""
    for r in range(1, min(ws.max_row, 40) + 1):
        for c in range(1, min(ws.max_column, 30) + 1):
            if _kd(ws.cell(r, c).value) in NHAN_KHACH:
                return r, c
    return None, None


def doc_sheet_qt(ws) -> dict:
    """Đọc sheet QT thành khối đầu + danh sách dòng khách. Không kiểm, không sửa gì."""
    r0, c_khach = _tim_hang_tieu_de(ws)
    if r0 is None:
        return {"dau": {}, "dong": [], "cot_chi": [], "loi_doc": "Không thấy cột 'Tên khách hàng'"}

    r1 = r0 + 1
    M = min(ws.max_column, 40)
    c_no = c_sales = c_gia = c_thukhac = c_tongthu = c_chi = c_tongchi = c_ln = None
    for c in range(1, M + 1):
        a, b = _kd(ws.cell(r0, c).value), _kd(ws.cell(r1, c).value)
        if a == "NO" and c_no is None:
            c_no = c
        if a in ("SALES", "SALE") and c_sales is None:
            c_sales = c
        if a == "CHI" and c_chi is None:
            c_chi = c
        if (a in NHAN_LOI_NHUAN or b in NHAN_LOI_NHUAN) and c_ln is None:
            c_ln = c
        if b in NHAN_GIA_BAN and c_gia is None:
            c_gia = c
        if b in NHAN_THU_KHAC and c_thukhac is None:
            c_thukhac = c
        if b in NHAN_TONG_THU and c_tongthu is None:
            c_tongthu = c
        if b in NHAN_TONG_CHI and c_tongchi is None:
            c_tongchi = c
    if c_no is None:
        c_no = 1

    # Khối CHI: mọi cột GIỮA ô "CHI" và ô "TỔNG CHI". Không lấy tràn sang cột lợi nhuận, và không
    # lấy chính cột TỔNG CHI – cộng cả cột tổng vào là đếm mỗi khoản hai lần.
    bat_dau = (c_chi or ((c_tongthu or 0) + 1))
    ket = c_tongchi or c_ln or (M + 1)
    cot_chi = []
    for c in range(bat_dau, ket):
        nhan = str(ws.cell(r1, c).value or "").strip()
        if nhan:
            cot_chi.append({"cot": c, "nhan": nhan})

    dong = []
    for r in range(r1 + 1, ws.max_row + 1):
        stt = _so(ws.cell(r, c_no).value)
        ten = str(ws.cell(r, c_khach).value or "").strip()
        if stt is None and not ten:
            continue
        if stt is None:                      # dòng cộng ở chân bảng – không phải một khách
            continue
        dong.append({
            "stt": int(stt),
            "sales": str(ws.cell(r, c_sales).value or "").strip() if c_sales else "",
            "ten_khach": ten,
            "gia_ban": _so(ws.cell(r, c_gia).value) if c_gia else None,
            "thu_khac": _so(ws.cell(r, c_thukhac).value) if c_thukhac else None,
            "tong_thu": _so(ws.cell(r, c_tongthu).value) if c_tongthu else None,
            "tong_chi": _so(ws.cell(r, c_tongchi).value) if c_tongchi else None,
            "loi_nhuan_tep": _so(ws.cell(r, c_ln).value) if c_ln else None,
            "khoan_chi": [{"nhan": k["nhan"], "so_tien": _so(ws.cell(r, k["cot"]).value)}
                          for k in cot_chi],
        })
    return {"dau": _doc_dau(ws, r0), "dong": dong,
            "cot_chi": [k["nhan"] for k in cot_chi], "loi_doc": ""}


def _hang_co(ws, *nhan, den=40):
    """Tìm hàng tiêu đề: hàng chứa ĐỦ các nhãn cho trước. Trả (hàng, {nhãn: cột})."""
    for r in range(1, min(ws.max_row, den) + 1):
        vi = {}
        for c in range(1, min(ws.max_column, 30) + 1):
            k = _kd(ws.cell(r, c).value)
            if k in nhan and k not in vi:
                vi[k] = c
        if len(vi) == len(nhan):
            return r, vi
    return None, {}


def doc_sheet_ctt(ws) -> dict:
    """Sheet chiết tính: khối đầu, từng dòng thu/chi kèm đối tác – chứng từ – MST, và các ô tổng.

    Bố cục thật: I/GIÁ TOUR ... TỔNG CỘNG THU ... II/ CHI PHÍ ... A. LAND TOUR / B. TRẺ EM /
    C. CHI PHÍ KHÁC ... TỔNG CỘNG CHI. Bộ đọc bám vào những dòng tiêu đề ấy để biết mỗi dòng thuộc
    VẾ nào và NHÓM nào – không đoán theo vị trí, vì đoàn MICE chia nhóm khác hẳn tour lẻ.
    """
    r0, vi = _hang_co(ws, "NOI DUNG", "DON GIA", "THANH TIEN")
    if r0 is None:
        return {"dau": _doc_dau(ws, 12), "dong": [], "tong": {}}
    c_nd = vi["NOI DUNG"]; c_dg = vi["DON GIA"]; c_tt = vi["THANH TIEN"]
    c_ngay = c_dt = c_sl = c_hs = c_gc = c_mst = None
    for c in range(1, min(ws.max_column, 20) + 1):
        k = _kd(ws.cell(r0, c).value)
        if k == "NGAY": c_ngay = c
        elif k in ("DOI TAC", "NCC"): c_dt = c
        elif k in ("SL", "SO LUONG"): c_sl = c
        elif k in ("DIEN GIAI", "DG"): c_hs = c
        elif k in ("GHI CHU", "SO HOA DON", "SO CHUNG TU"): c_gc = c
        elif k == "MST": c_mst = c

    ve, nhom = "", ""
    dong, tong = [], {}
    for r in range(r0 + 1, ws.max_row + 1):
        nhan_a = _kd(ws.cell(r, 1).value)
        if nhan_a.startswith("I/"): ve, nhom = "thu", ""; continue
        if nhan_a.startswith("II/"): ve, nhom = "chi", ""; continue
        if re.match(r"^[A-Z]\.\s", nhan_a): nhom = str(ws.cell(r, 1).value).strip(); continue
        if nhan_a.startswith("TONG CONG THU"):
            tong["thu"] = _so(ws.cell(r, c_tt).value); continue
        if nhan_a.startswith("TONG CONG CHI"):
            tong["chi"] = _so(ws.cell(r, c_tt).value); continue
        if nhan_a.startswith("GIA NET"):
            break
        dg, tt = _so(ws.cell(r, c_dg).value), _so(ws.cell(r, c_tt).value)
        if dg is None and tt is None:
            continue
        # Tiêu đề ghi cột A là "NGÀY", nhưng trong tệp thật KHÔNG dòng nào có ngày ở đó – Điều hành
        # dùng cột ấy làm nội dung ("Ăn trưa ngày 1", "LƯU TRÚ", "Tham quan") và đẩy nhà cung cấp
        # sang cột "NỘI DUNG". Đọc theo đúng tên cột thì tên món ăn thành ngày, còn tên nhà cung cấp
        # thành nội dung – và bảng kê thuế đầu vào mất cột đối tác.
        #
        # Nên lấy theo NỘI DUNG THẬT của ô, và giữ cả ba ô: A có chữ thì A là nội dung, B là đối tác;
        # A rỗng thì B là nội dung, C là đối tác. Trường hợp lệch tiêu đề được ghi cờ ở mức bản
        # quyết toán, không im lặng sửa.
        oa = str(ws.cell(r, 1).value or "").strip()
        ob = str(ws.cell(r, c_nd).value or "").strip()
        oc = str(ws.cell(r, c_dt).value or "").strip() if c_dt else ""
        if oa:
            nd, dtac = oa, ob
        else:
            nd, dtac = ob, oc
        dong.append({
            "ve": ve or "chi", "nhom": nhom,
            "ngay": "",
            "noi_dung": nd,
            "doi_tac": dtac,
            "o_phu": oc if oa else "",
            "don_gia": dg,
            "so_luong": _so(ws.cell(r, c_sl).value) if c_sl else None,
            "he_so": _so(ws.cell(r, c_hs).value) if c_hs else None,
            "thanh_tien": tt,
            "so_chung_tu": str(ws.cell(r, c_gc).value or "").strip() if c_gc else "",
            "mst_ncc": str(ws.cell(r, c_mst).value or "").strip() if c_mst else "",
        })
    # ô tổng ở chân: TỔNG THU / TỔNG CHI / LỢI NHUẬN nằm ngoài bảng, dò riêng
    for r in range(r0, min(ws.max_row, r0 + 60) + 1):
        for c in range(1, min(ws.max_column, 12) + 1):
            k = _kd(ws.cell(r, c).value)
            if k == "TONG THU" and "thu" not in tong: tong["thu"] = _so(_o_ben_phai(ws, r, c))
            elif k == "TONG CHI" and "chi" not in tong: tong["chi"] = _so(_o_ben_phai(ws, r, c))
            elif k == "LOI NHUAN" and "loi_nhuan" not in tong: tong["loi_nhuan"] = _so(_o_ben_phai(ws, r, c))
    return {"dau": _doc_dau(ws, r0), "dong": dong, "tong": tong}


def doc_sheet_hdv(ws) -> dict:
    """Sheet HDV CHI: từng khoản HDV chi trên tour, cộng ba ô tiền ứng / dư / CTP ở chân bảng."""
    r0, vi = _hang_co(ws, "NOI DUNG", "DON GIA", "TONG CHI")
    if r0 is None:
        return {"dong": [], "tien_ung": None, "du": None, "ctp": None, "tong_chi": None}
    c_nd, c_dg, c_tc = vi["NOI DUNG"], vi["DON GIA"], vi["TONG CHI"]
    c_sl = c_gc = None
    for c in range(1, min(ws.max_column, 15) + 1):
        k = _kd(ws.cell(r0, c).value)
        if k in ("SO LUONG", "SL"): c_sl = c
        elif k == "GHI CHU": c_gc = c
    dong, ra = [], {"tien_ung": None, "du": None, "ctp": None, "tong_chi": None}
    for r in range(r0 + 1, ws.max_row + 1):
        nhan = " ".join(_kd(ws.cell(r, c).value) for c in range(1, min(ws.max_column, 8) + 1)).strip()
        so_ben = None
        for c in range(1, min(ws.max_column, 10) + 1):
            k = _kd(ws.cell(r, c).value)
            if k in ("TONG CHI", "TIEN UNG", "DU", "CTP"):
                so_ben = (k, _so(_o_ben_phai(ws, r, c, xa=4)))
        if so_ben:
            k, v = so_ben
            ra[{"TONG CHI": "tong_chi", "TIEN UNG": "tien_ung", "DU": "du", "CTP": "ctp"}[k]] = v
            continue
        dg, tc = _so(ws.cell(r, c_dg).value), _so(ws.cell(r, c_tc).value)
        if dg is None and tc is None:
            continue
        nd = str(ws.cell(r, c_nd).value or "").strip()
        if not nd:
            nd = str(ws.cell(r, c_nd + 1).value or "").strip()
        dong.append({"noi_dung": nd, "don_gia": dg,
                     "so_luong": _so(ws.cell(r, c_sl).value) if c_sl else None,
                     "tong_chi": tc,
                     "ghi_chu": str(ws.cell(r, c_gc).value or "").strip() if c_gc else ""})
    ra["dong"] = dong
    return ra


def doc_sheet_dt(ws) -> dict:
    """Sheet DT: từng booking. BookingID là cầu duy nhất nối sang hệ đặt chỗ – không dò theo tên."""
    r0, vi = _hang_co(ws, "BOOKINGID")
    if r0 is None:
        return {"dong": [], "tong_thu": None, "da_dong": None}
    c_bk = vi["BOOKINGID"]
    c = {}
    for k in range(1, min(ws.max_column, 30) + 1):
        a, b = _kd(ws.cell(r0, k).value), _kd(ws.cell(r0 + 1, k).value)
        for nhan, ten in (("TEN NGUOI BOOK", "ten_nguoi_book"), ("SO DIEN THOAI", "dien_thoai"),
                          ("GIA TOUR", "gia_tour"), ("SO LUONG KHACH", "so_khach"),
                          ("KHUYEN MAI", "khuyen_mai"), ("TONG THU", "tong_thu"),
                          ("DA DONG", "da_dong"), ("NGUOI BAN", "nguoi_ban"),
                          ("TONG GIA TOUR", "tong_gia_tour"), ("PHI VISA", "phi_visa"),
                          ("PHI KHAC", "phi_khac")):
            if (a == nhan or b == nhan) and ten not in c:
                c[ten] = k
    dong, tong = [], {}
    for r in range(r0 + 2, ws.max_row + 1):
        ma = ws.cell(r, c_bk).value
        nhan = _kd(ma)
        if nhan.startswith("TONG CONG"):
            tong["tong_thu"] = _so(ws.cell(r, c["tong_thu"]).value) if "tong_thu" in c else None
            tong["da_dong"] = _so(ws.cell(r, c["da_dong"]).value) if "da_dong" in c else None
            continue
        if ma in (None, ""):
            continue
        g = lambda t: (ws.cell(r, c[t]).value if t in c else None)
        dong.append({
            "ma_booking_nguon": str(ma).strip(),
            "ten_nguoi_book": str(g("ten_nguoi_book") or "").strip(),
            "dien_thoai": str(g("dien_thoai") or "").strip(),
            "gia_tour": _so(g("gia_tour")), "so_khach": _so(g("so_khach")),
            "tong_gia_tour": _so(g("tong_gia_tour")), "phi_visa": _so(g("phi_visa")),
            "phi_khac": _so(g("phi_khac")), "khuyen_mai": _so(g("khuyen_mai")),
            "tong_thu": _so(g("tong_thu")), "da_dong": _so(g("da_dong")),
            "nguoi_ban": str(g("nguoi_ban") or "").strip(),
        })
    return {"dong": dong, **tong}


def doc_tep(noi_dung: bytes, ten_tep: str = "") -> dict:
    """Đọc cả workbook: sheet QT là dữ liệu, CTT và DT là nguồn đối chiếu."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(noi_dung), data_only=True)
    qt = ctt = hdv = dt = None
    for ws in wb.worksheets:
        t = _kd(ws.title)
        if t == "QT" and qt is None:
            qt = ws
        elif t.startswith("CTT") and ctt is None:
            ctt = ws
        elif t.startswith("HDV") and hdv is None:
            hdv = ws
        elif t == "DT" and dt is None:
            dt = ws
    if qt is None:                       # tệp không đặt tên sheet: lấy sheet có bảng khách
        for ws in wb.worksheets:
            if _tim_hang_tieu_de(ws)[0] is not None:
                qt = ws
                break
    if qt is None:
        raise ValueError("Không thấy sheet nào có bảng khách (cột 'Tên khách hàng')")

    ra = doc_sheet_qt(qt)
    ra["ten_tep"] = ten_tep
    ra["sheet_qt"] = qt.title
    ra["ctt"] = doc_sheet_ctt(ctt) if ctt is not None else {"dau": {}, "dong": [], "tong": {}}
    ra["hdv_chi"] = doc_sheet_hdv(hdv) if hdv is not None else {"dong": []}
    ra["dt"] = doc_sheet_dt(dt) if dt is not None else {"dong": []}
    return ra


# ---------------------------------------------------------------------------------------------
# Kiểm – không ghi gì, chỉ nói ra chỗ lệch
# ---------------------------------------------------------------------------------------------

def _gan(a, b, sai_so=1.0) -> bool:
    return a is not None and b is not None and abs(a - b) <= sai_so


def kiem(doc: dict, ma_khoan_map: dict | None = None) -> dict:
    """Kiểm một bản quyết toán đã đọc. Trả về tổng, cờ từng dòng và danh sách chỗ lệch giữa các nguồn.

    Nguyên tắc xuyên suốt: KHÔNG sửa số nào. Mỗi chỗ lệch là một dòng trong 'doi_chieu', kèm số của
    từng nguồn, để người sửa tệp gốc. Máy san bằng hộ là xoá mất bằng chứng.
    """
    from app.models.quyet_toan import MA_KHOAN
    ma_map = ma_khoan_map if ma_khoan_map is not None else MA_KHOAN

    dau = doc.get("dau") or {}
    dong = doc.get("dong") or []
    ma_tour = str(dau.get("ma_tour") or "").strip()

    tong_thu = tong_chi = 0.0
    co_thu = co_chi = False
    nhan_la: set[str] = set()
    for d in dong:
        cb = []
        # 1. Trong một dòng: tổng thu phải bằng giá bán cộng thu khác.
        if d["tong_thu"] is not None and d["gia_ban"] is not None:
            if not _gan(d["tong_thu"], d["gia_ban"] + (d["thu_khac"] or 0)):
                cb.append("Tổng thu khác giá bán cộng thu khác")
        # 2. Tổng chi tệp ghi phải bằng tổng các khoản chi của chính dòng ấy.
        cong_khoan = sum(k["so_tien"] for k in d["khoan_chi"] if k["so_tien"])
        if d["tong_chi"] is not None and d["khoan_chi"]:
            if not _gan(d["tong_chi"], cong_khoan):
                cb.append(f"Tổng chi ghi {d['tong_chi']:,.0f} khác tổng các khoản {cong_khoan:,.0f}")
        # 3. Lợi nhuận tệp ghi phải bằng tổng thu trừ tổng chi.
        if d["loi_nhuan_tep"] is not None and d["tong_thu"] is not None and d["tong_chi"] is not None:
            if not _gan(d["loi_nhuan_tep"], d["tong_thu"] - d["tong_chi"]):
                cb.append("Lợi nhuận ghi khác tổng thu trừ tổng chi")
        d["co_lech"] = "; ".join(cb)
        for k in d["khoan_chi"]:
            k["ma_khoan"] = ma_map.get(_kd(k["nhan"]), "")
            if not k["ma_khoan"]:
                nhan_la.add(k["nhan"])
        if d["tong_thu"] is not None:
            tong_thu += d["tong_thu"]
            co_thu = True
        if d["tong_chi"] is not None:
            tong_chi += d["tong_chi"]
            co_chi = True

    # ---- đối chiếu giữa các nguồn trong cùng một tệp ----
    dc = []
    ng_ma = ngay_tu_ma(ma_tour)
    ng_qt = _ngay(dau.get("ngay_di"))
    ng_ctt = _ngay(((doc.get("ctt") or {}).get("dau") or {}).get("ngay_di"))
    nguon_ngay = {"mã tour": ng_ma, "sheet QT": ng_qt, "sheet CTT": ng_ctt}
    co = {k: v for k, v in nguon_ngay.items() if v}
    if len(set(co.values())) > 1:
        dc.append({"muc": "ngay_khoi_hanh", "nang": True,
                   "noi_dung": "Ngày khởi hành không khớp giữa các nguồn trong cùng một tệp",
                   "nguon": {k: str(v) for k, v in co.items()},
                   "vi_sao": "Ngày khởi hành quyết định chuyến thuộc kỳ kế toán nào. Lệch vài ngày ở "
                             "chuyến cuối tháng là lệch cả kỳ, và bảng vẫn cân nên không ai nhìn ra."})

    sk_qt = _so(dau.get("so_khach"))
    sk_ctt = _so(((doc.get("ctt") or {}).get("dau") or {}).get("so_khach"))
    sk_dong = len(dong) or None
    sk_dt = sum(b["so_khach"] or 0 for b in ((doc.get("dt") or {}).get("dong") or [])) or None
    nguon_khach = {"sheet QT": sk_qt, "sheet CTT": sk_ctt, "số dòng khách": sk_dong,
                   "cộng khách sheet DT": sk_dt}
    cok = {k: v for k, v in nguon_khach.items() if v}
    if len(set(cok.values())) > 1:
        dc.append({"muc": "so_khach", "nang": False,
                   "noi_dung": "Số khách không khớp giữa các nguồn",
                   "nguon": {k: int(v) for k, v in cok.items()},
                   "vi_sao": "Thường là do trẻ em free đếm ở nguồn này mà không đếm ở nguồn kia. "
                             "Không phải lỗi tiền, nhưng nó đổi giá vốn bình quân đầu khách."})

    tt_ctt = ((doc.get("ctt") or {}).get("tong") or {}).get("thu")
    tt_dt = (doc.get("dt") or {}).get("tong_thu")
    nguon_thu = {"cộng dòng khách (QT)": tong_thu if co_thu else None,
                 "sheet CTT": tt_ctt, "sheet DT": tt_dt}
    cot = {k: round(v) for k, v in nguon_thu.items() if v}
    if len(set(cot.values())) > 1:
        dc.append({"muc": "doanh_thu", "nang": True,
                   "noi_dung": "Doanh thu không khớp giữa các sheet",
                   "nguon": cot,
                   "vi_sao": "Ba sheet cùng nói về một chuyến mà ra ba con số. Chỉ một trong ba vào "
                             "được sổ; chọn số nào là việc của Kế toán, không phải của máy."})

    # ---- 4. Chiết tính: thành tiền phải bằng đơn giá x số lượng x hệ số ----
    ctt_dong = ((doc.get("ctt") or {}).get("dong") or [])
    ctt_lech = []
    for x in ctt_dong:
        if x["thanh_tien"] is None or x["don_gia"] is None:
            continue
        tinh = x["don_gia"] * (x["so_luong"] or 1) * (x["he_so"] or 1)
        if not _gan(x["thanh_tien"], tinh):
            x["co_lech"] = (f"Thành tiền {x['thanh_tien']:,.0f} khác đơn giá × số lượng × hệ số "
                            f"= {tinh:,.0f}")
            ctt_lech.append(x)
        else:
            x["co_lech"] = ""
    if ctt_lech:
        dc.append({"muc": "chiet_tinh_sai_phep_nhan", "nang": True,
                   "noi_dung": f"{len(ctt_lech)} dòng chiết tính có thành tiền khác phép nhân",
                   "nguon": {x["noi_dung"][:40]: x["co_lech"] for x in ctt_lech[:5]},
                   "vi_sao": "Cột 'DIỄN GIẢI' trong tệp là hệ số nhân (số đêm lưu trú, số bữa ăn) chứ "
                             "không phải diễn giải. Đo trên tệp mẫu đúng 20/20 dòng, nên một dòng lệch "
                             "là gõ tay đè lên công thức."})

    # ---- 4b. Ô TỔNG của chiết tính phải bằng tổng các dòng của chính nó ----
    #
    # Phép kiểm 4 ở trên soát TỪNG DÒNG: thành tiền có bằng đơn giá × số lượng × hệ số không. Nó
    # không soát PHÉP CỘNG. Trong Excel, ô tổng là một công thức mà không ai kiểm, và một dải =SUM()
    # bỏ sót một dòng thì bảng vẫn cân ở mọi tầng phía sau – vì mọi tầng đều lấy lại đúng cái tổng đã
    # sai ấy.
    #
    # Đo trên tệp mẫu "QT TOUR NHA TRANG 10.07.26.xlsx": nhóm "B. TRẺ EM" ghi tổng 3.990.000 đ, cộng
    # lại năm dòng của chính nhóm ấy được 4.200.000 đ. Thiếu đúng 210.000 đ – dòng Tham quan Tháp Bà
    # của trẻ em. Con số 3.990.000 sai ấy đi thẳng vào tổng chi 50.650.000, rồi vào cột LAND của cả
    # 42 dòng quyết toán, rồi vào lợi nhuận 20.515.000. Phép kiểm 4 báo 0/20 dòng lệch, và đúng: mỗi
    # dòng đều nhân đúng. Cái sai nằm ở chỗ không dòng nào chịu trách nhiệm.
    #
    # Đây chính là lý do của nguyên tắc Chủ tịch chốt 10/9/2026: MÁY CHỦ CỘNG, NGƯỜI KHÔNG GÕ TỔNG.
    # Ở đây máy không sửa được tệp, nên nó làm việc gần nhất: cộng lại và nói ra chỗ lệch.
    cong_nhom: dict[str, float] = {}
    for x in ctt_dong:
        if x["ve"] != "chi" or x["thanh_tien"] is None:
            continue
        cong_nhom[x["nhom"] or "(không nhóm)"] = (
            cong_nhom.get(x["nhom"] or "(không nhóm)", 0.0) + x["thanh_tien"])
    cong_chi_dong = sum(cong_nhom.values())
    tong_ghi = ((doc.get("ctt") or {}).get("tong") or {}).get("chi")
    if tong_ghi is not None and ctt_dong and not _gan(tong_ghi, cong_chi_dong):
        chenh = cong_chi_dong - tong_ghi
        dc.append({
            "muc": "tong_chi_khac_tong_dong", "nang": True,
            "noi_dung": f"Ô tổng chi ghi {tong_ghi:,.0f} đ, cộng lại các dòng được "
                        f"{cong_chi_dong:,.0f} đ – lệch {chenh:+,.0f} đ",
            "nguon": {**{f"cộng lại {k}": round(v) for k, v in cong_nhom.items()},
                      "cộng lại tất cả": round(cong_chi_dong),
                      "ô tổng tệp ghi": round(tong_ghi),
                      "lệch": round(chenh)},
            "vi_sao": "Ô tổng trong Excel là một công thức mà không ai kiểm. Thiếu một dòng trong dải "
                      "=SUM() thì bảng vẫn cân ở mọi tầng phía sau, vì mọi tầng đều lấy lại đúng cái "
                      "tổng đã sai. Lệch ở đây đi thẳng vào giá vốn và vào lợi nhuận của chuyến."})

    # ---- 5. Chi phí khác nhau giữa chiết tính và bảng chi thật của HDV ----
    hdv = (doc.get("hdv_chi") or {})
    for h in (hdv.get("dong") or []):
        ten = _kd(h["noi_dung"])
        if not ten or h["tong_chi"] is None:
            continue
        khop = [x for x in ctt_dong if x["ve"] == "chi" and x["thanh_tien"] is not None
                and (ten in _kd(x["noi_dung"]) or ten in _kd(x["doi_tac"])
                     or _kd(x["noi_dung"]).startswith(ten[:12]))]
        if not khop:
            continue
        tong_ctt = sum(x["thanh_tien"] for x in khop)
        if not _gan(h["tong_chi"], tong_ctt):
            dc.append({"muc": "hdv_chi_khac_chiet_tinh", "nang": True,
                       "noi_dung": f"HDV chi '{h['noi_dung']}' khác số trong chiết tính",
                       "nguon": {"HDV chi thật": round(h["tong_chi"]),
                                 "chiết tính": round(tong_ctt),
                                 "chênh": round(h["tong_chi"] - tong_ctt)},
                       "vi_sao": "HDV chi theo số khách THỰC ĐI, chiết tính lập theo số khách ĐÃ ĐẶT. "
                                 "Phần chênh là tiền đã ra khỏi công ty mà chưa vào giá vốn – nó không "
                                 "nằm trong giá vốn, không trong công nợ, cũng không trong hoàn ứng."})
    if hdv.get("tien_ung") is not None and hdv.get("tong_chi") is not None:
        con = hdv["tien_ung"] - hdv["tong_chi"]
        if hdv.get("du") is not None and not _gan(hdv["du"], con):
            dc.append({"muc": "hdv_du_sai", "nang": True,
                       "noi_dung": "Ô 'Dư' của HDV khác tiền ứng trừ tổng chi",
                       "nguon": {"tiền ứng": round(hdv["tien_ung"]), "tổng chi": round(hdv["tong_chi"]),
                                 "dư ghi": round(hdv["du"]), "dư đúng": round(con)},
                       "vi_sao": "Dư là số phải hoàn lại công ty. Ghi sai là mất dấu một khoản tạm ứng."})

    # ---- 6. Doanh thu theo booking: đã đóng đủ chưa ----
    dt = (doc.get("dt") or {})
    for b in (dt.get("dong") or []):
        if b["tong_thu"] is not None and b["da_dong"] is not None and b["da_dong"] < b["tong_thu"] - 1:
            dc.append({"muc": "booking_chua_thu_du", "nang": False,
                       "noi_dung": f"Booking {b['ma_booking_nguon']} chưa thu đủ",
                       "nguon": {"tổng thu": round(b["tong_thu"]), "đã đóng": round(b["da_dong"]),
                                 "còn phải thu": round(b["tong_thu"] - b["da_dong"])},
                       "vi_sao": "Tour đã chạy mà booking chưa thu đủ là công nợ khách, phải có người theo."})

    return {
        "ma_tour": ma_tour,
        "ten_chuong_trinh": str(dau.get("ten_chuong_trinh") or "").strip(),
        "so_khach": int(sk_qt) if sk_qt else None,
        "hdv": str(dau.get("hdv") or "").strip(),
        "bien_so_xe": str(dau.get("bien_so_xe") or "").strip(),
        "ngay_kh": ng_qt or ng_ma or ng_ctt,
        "ngay_kt": _ngay(dau.get("ngay_ve")),
        "so_dong": len(dong),
        # Làm tròn về ĐỒNG trước khi con số rời khỏi bộ đọc. Sheet QT phân bổ giá vốn theo đầu khách
        # bằng phép chia không hết (1.343.030,3030... × 33 người lớn), nên cộng 42 dòng lại ra
        # 50.649.999,99999988 trong khi ô TỔNG CỘNG CHI của chính tệp ấy ghi 50.650.000. Ghi số có
        # đuôi float vào cột tiền thì mọi bản đối chiếu về sau đều lệch 0,00000012đ – không đủ lớn để
        # ai sửa, nhưng đủ để câu "khớp tuyệt đối" không bao giờ còn đúng.
        "tong_thu": round(tong_thu, 2) if co_thu else None,
        "tong_chi": round(tong_chi, 2) if co_chi else None,
        "loi_nhuan": round(tong_thu - tong_chi, 2) if (co_thu and co_chi) else None,
        "gia_ban": _gia_ban_pho_bien(dong),
        "nhieu_muc_gia": len({d["gia_ban"] for d in dong if d["gia_ban"]}) > 1,
        "so_dong_lech": sum(1 for d in dong if d["co_lech"]),
        "nhan_chi_chua_xep_ma": sorted(nhan_la),
        "doi_chieu": dc,
        "dong": dong,
        "chiet_tinh": ctt_dong,
        "hdv_chi": hdv,
        "booking": (dt.get("dong") or []),
        "so_dong_chiet_tinh_lech": len(ctt_lech),
        "so_chung_tu_co_mst": sum(1 for x in ctt_dong if x.get("mst_ncc")),
        "cot_chi": doc.get("cot_chi", []),
    }


def _gia_ban_pho_bien(dong: list) -> float | None:
    """Giá bán của chương trình = mức giá NHIỀU KHÁCH TRẢ NHẤT, không phải bình quân.

    Bình quân của 33 người lớn 1.790.000 và 7 trẻ em 1.500.000 ra 1.739.250 – một con số không có
    trong bảng giá nào và không ai đối chiếu được. Mức phổ biến nhất thì tra được ngay trong bảng giá.
    """
    dem: dict[float, int] = {}
    for d in dong:
        g = d.get("gia_ban")
        if g:
            dem[g] = dem.get(g, 0) + 1
    if not dem:
        return None
    return max(dem.items(), key=lambda kv: (kv[1], kv[0]))[0]


# ---------------------------------------------------------------------------------------------
# Nạp – ghi cả bốn mặt vào cùng một bản quyết toán
# ---------------------------------------------------------------------------------------------

def nap(db, kq: dict, boi: str, ten_tep: str = "", ky: str = ""):
    """Ghi một bản quyết toán chi tiết. Trả về bản ghi lớp 1 đã kèm đủ bốn mặt của lớp 2.

    Ba điều bộ nạp này CỐ Ý không làm:

      1. Không sửa số nào của tệp. Lớp 1 lấy tổng do tệp ghi; chênh giữa lớp 1 và tổng lớp 2 ghi vào
         chenh_thu / chenh_chi. San bằng hộ là xoá mất bằng chứng.
      2. Không tự chọn ngày khởi hành khi các sheet nói khác nhau – lấy ngày ở sheet QT và để nguyên
         phát hiện trong ghi_chu. Người sửa tệp, không phải máy sửa sổ.
      3. Không đoán mã khoản cho nhãn chi lạ – để trống, vào hàng đợi.

    Nạp lại cùng mã tour thì XOÁ hết lớp 2 cũ rồi ghi lại, chứ không cộng thêm. Cộng thêm là nhân đôi
    doanh thu một cách âm thầm, và bảng vẫn cân.
    """
    from sqlalchemy import select, delete
    from app.models.quyet_toan import (TourSettlement, TourSettlementLine, TourSettlementCost,
                                       TourSettlementCostLine, TourGuideAdvance,
                                       TourSettlementBooking)

    ma = kq["ma_tour"]
    if not ma:
        raise ValueError("Tệp không có mã tour – không biết ghi vào chuyến nào")
    kt = kq.get("ngay_kt") or kq.get("ngay_kh")
    s = db.execute(select(TourSettlement).where(TourSettlement.ma_tour == ma)).scalars().first()
    moi = s is None
    if moi:
        s = TourSettlement(ma_tour=ma)
        db.add(s)
    s.ky = ky or (f"{kt:%Y-%m}" if kt else "")
    s.ten_tour = (kq.get("ten_chuong_trinh") or "")[:300]
    s.ten_chuong_trinh = (kq.get("ten_chuong_trinh") or "")[:200]
    s.so_khach = kq.get("so_khach")
    s.hdv = (kq.get("hdv") or "")[:120]
    s.bien_so_xe = (kq.get("bien_so_xe") or "")[:30]
    s.ngay_kh, s.ngay_kt = kq.get("ngay_kh"), kq.get("ngay_kt")
    s.gia_ban = kq.get("gia_ban")
    s.nhieu_muc_gia = 1 if kq.get("nhieu_muc_gia") else 0
    s.doanh_thu = kq.get("tong_thu")
    s.gia_von = kq.get("tong_chi")
    s.trang_thai_qt = "da_qt"
    s.nguon = "nap_tep_chi_tiet"
    s.ten_tep = (ten_tep or "")[:200]
    s.boi = (boi or "")[:50]
    s.luc = datetime.now()
    ghi = [f"{d['noi_dung']}: {d['nguon']}" for d in kq.get("doi_chieu", [])]
    s.ghi_chu = " | ".join(str(x) for x in ghi)[:4000]
    db.flush()

    if not moi:
        for bang in (TourSettlementCost,):
            db.execute(delete(bang).where(bang.line_id.in_(
                select(TourSettlementLine.id).where(TourSettlementLine.settlement_id == s.id))))
        for bang in (TourSettlementLine, TourSettlementCostLine, TourGuideAdvance,
                     TourSettlementBooking):
            db.execute(delete(bang).where(bang.settlement_id == s.id))
        db.flush()

    # --- mặt 1: từng khách ---
    cong_thu = cong_chi = 0.0
    for d in kq.get("dong", []):
        ln = TourSettlementLine(
            settlement_id=s.id, stt=d.get("stt"), sales=(d.get("sales") or "")[:120],
            ten_khach=(d.get("ten_khach") or "")[:200], gia_ban=d.get("gia_ban"),
            thu_khac=d.get("thu_khac"), tong_thu=d.get("tong_thu"), tong_chi=d.get("tong_chi"),
            loi_nhuan_tep=d.get("loi_nhuan_tep"), co_lech=d.get("co_lech", ""))
        db.add(ln)
        db.flush()
        for k in d.get("khoan_chi", []):
            if k.get("so_tien") is None:
                continue
            db.add(TourSettlementCost(line_id=ln.id, ma_khoan=k.get("ma_khoan", ""),
                                      nhan=(k.get("nhan") or "")[:120], so_tien=k["so_tien"]))
        cong_thu += d.get("tong_thu") or 0
        cong_chi += d.get("tong_chi") or 0

    # --- mặt 2: chiết tính ---
    for x in kq.get("chiet_tinh", []):
        db.add(TourSettlementCostLine(
            settlement_id=s.id, ve=x.get("ve", "chi"), nhom=(x.get("nhom") or "")[:80],
            ngay=(x.get("ngay") or "")[:60], noi_dung=(x.get("noi_dung") or "")[:200],
            doi_tac=(x.get("doi_tac") or "")[:200], don_gia=x.get("don_gia"),
            so_luong=x.get("so_luong"), he_so=x.get("he_so"), thanh_tien=x.get("thanh_tien"),
            so_chung_tu=(x.get("so_chung_tu") or "")[:60], mst_ncc=(x.get("mst_ncc") or "")[:30],
            co_lech=x.get("co_lech", "")))

    # --- mặt 3: chi trên tour của HDV ---
    hd = kq.get("hdv_chi") or {}
    for x in (hd.get("dong") or []):
        db.add(TourGuideAdvance(settlement_id=s.id, noi_dung=(x.get("noi_dung") or "")[:200],
                                don_gia=x.get("don_gia"), so_luong=x.get("so_luong"),
                                tong_chi=x.get("tong_chi"), ghi_chu=(x.get("ghi_chu") or "")[:120]))
    if hd.get("tong_chi") is not None or hd.get("tien_ung") is not None:
        db.add(TourGuideAdvance(settlement_id=s.id, noi_dung="TỔNG", tong_chi=hd.get("tong_chi"),
                                tien_ung=hd.get("tien_ung"), du=hd.get("du"), ctp=hd.get("ctp"),
                                la_dong_tong=1))

    # --- mặt 4: doanh thu theo booking ---
    for b in kq.get("booking", []):
        db.add(TourSettlementBooking(
            settlement_id=s.id, ma_booking_nguon=(b.get("ma_booking_nguon") or "")[:40],
            ten_nguoi_book=(b.get("ten_nguoi_book") or "")[:200],
            dien_thoai=(b.get("dien_thoai") or "")[:30], gia_tour=b.get("gia_tour"),
            so_khach=int(b["so_khach"]) if b.get("so_khach") else None,
            tong_gia_tour=b.get("tong_gia_tour"), phi_visa=b.get("phi_visa"),
            phi_khac=b.get("phi_khac"), khuyen_mai=b.get("khuyen_mai"),
            tong_thu=b.get("tong_thu"), da_dong=b.get("da_dong"),
            nguoi_ban=(b.get("nguoi_ban") or "")[:120]))

    # Chênh giữa hai lớp: GHI LẠI, không sửa. Bằng 0 cũng ghi 0 – "đã đối chiếu, khớp" khác với
    # "chưa đối chiếu bao giờ", và cột NULL không phân biệt được hai chuyện đó.
    s.chenh_thu = (s.doanh_thu - cong_thu) if s.doanh_thu is not None else None  # k2-doc-an-toan: đã chặn None; cong_thu cộng dồn từ 0.0
    s.chenh_chi = (s.gia_von - cong_chi) if s.gia_von is not None else None  # k2-doc-an-toan: đã chặn None; cong_chi cộng dồn từ 0.0
    db.flush()
    return s


# ---------------------------------------------------------------------------------------------
# Nối vào khung nạp chung (/nap-du-lieu). Cùng bốn bước, cùng một nhật ký, cùng một khoá chống trùng.
# ---------------------------------------------------------------------------------------------
#
# Khung nạp đòi doc_tep trả về một DANH SÁCH dòng. Tệp này là MỘT chuyến, nên danh sách có đúng một
# phần tử: chính bản quyết toán đã đọc. Ép nó thành nhiều dòng phẳng là mất cấu trúc bốn mặt – và
# mất đúng những chỗ chỉ lộ ra khi đặt bốn mặt cạnh nhau.

def doc_tep_lo(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    d = doc_tep(noi_dung, ten_tep)
    # Doanh thu để phẳng ở gốc để nhật ký nạp ghi được tổng tiền của tệp. Không có ô này thì K5 đọc
    # ra "lô không có cột tiền" và báo thiếu tiền ở mọi lần nạp đi qua đường này.
    d["doanh_thu"] = sum(x["tong_thu"] or 0 for x in d.get("dong", [])) or None

    # Tám cột đã KHAI ở cửa nạp phải có mặt phẳng ở gốc, vì màn hình xem trước dựng bảng theo đúng
    # danh sách khai ấy. Ngày 10/9 chỉ có doanh_thu và ma_tour được để phẳng, nên bảng xem trước hiện
    # tên tour, ngày đi, số khách, HDV và biển số đều RỖNG – trong khi bộ đọc biết đủ cả. Người nạp
    # nhìn bảng trống thì kết luận tệp đọc hỏng và bỏ đi, đúng lúc bộ kiểm đã đọc xong xuôi.
    #
    # Lấy nguyên văn ô đầu sheet QT, KHÔNG sửa theo mã tour: ngày ở đây có thể sai (chuyến Nha Trang
    # 10/07 ghi 07/07), và chỗ nói ra cái sai ấy là phát hiện đối chiếu, không phải chỗ lặng lẽ vá.
    dau = d.get("dau") or {}
    d["ma_tour"] = str(dau.get("ma_tour") or "").strip()
    d["ten_chuong_trinh"] = str(dau.get("ten_chuong_trinh") or "").strip()
    d["ngay_di"] = dau.get("ngay_di") or ""
    d["ngay_ve"] = dau.get("ngay_ve") or ""
    d["so_khach"] = _so(dau.get("so_khach"))
    d["hdv"] = str(dau.get("hdv") or "").strip()
    d["bien_so_xe"] = str(dau.get("bien_so_xe") or "").strip()
    return [d]


def _mot_ban(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Tệp không đọc được bản quyết toán nào")
    if len(rows) > 1:
        raise ValueError("Một tệp chỉ được chứa một chuyến – tệp này có nhiều hơn một")
    return rows[0]


def kiem_lo(db, rows: list[dict]) -> dict:
    """Xem trước. Không ghi gì. Mỗi phát hiện nặng đếm là một 'dòng lỗi' của khung nạp chung.

    Vì sao phát hiện NẶNG chặn nạp: ba thứ được xếp nặng đều đổi con số vào sổ – ngày khởi hành đổi
    kỳ kế toán, chiết tính sai phép nhân đổi giá vốn, HDV chi hơn chiết tính là tiền đã ra khỏi công
    ty mà chưa vào giá vốn. Số khách lệch thì xếp NHẸ: nó không đổi đồng nào, chỉ đổi giá vốn bình
    quân đầu khách, nên chặn nạp vì nó là làm phiền chứ không phải bảo vệ.
    """
    from sqlalchemy import select
    from app.models.quyet_toan import TourSettlement

    d = _mot_ban(rows)
    kq = kiem(d)
    nang = [x for x in kq["doi_chieu"] if x["nang"]]
    da_co = db.execute(select(TourSettlement).where(
        TourSettlement.ma_tour == kq["ma_tour"])).scalars().first() is not None
    return {
        "so_dong": kq["so_dong"],
        "hop_le": kq["so_dong"] - kq["so_dong_lech"],
        "da_co": 1 if da_co else 0,
        "dong_loi": len(nang),
        "tong_doanh_thu": kq["tong_thu"] or 0,
        "ban": kq,
        "dong": [{"dong": x["stt"], "ma_tour": kq["ma_tour"], "ten_khach": x["ten_khach"],
                  "doanh_thu": x["tong_thu"], "gia_von": x["tong_chi"],
                  "loi": [x["co_lech"]] if x["co_lech"] else [], "canh_bao": []}
                 for x in kq["dong"]],
        "phat_hien": kq["doi_chieu"],
        "nhan_chi_chua_xep_ma": kq["nhan_chi_chua_xep_ma"],
        "ghi_chu": ("Nạp lại cùng mã tour thì GHI ĐÈ lớp 2 chứ không cộng thêm – cộng thêm là nhân "
                    "đôi doanh thu một cách âm thầm, và bảng vẫn cân."),
    }


def nap_lo(db, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    kt = kiem_lo(db, rows)
    if kt["dong_loi"] and not bo_qua_dong_loi:
        return {**kt, "da_nap": 0,
                "message": (f"Có {kt['dong_loi']} phát hiện nặng nên KHÔNG nạp gì cả. Sửa tệp rồi "
                            "nạp lại, hoặc chọn bỏ qua để nạp kèm phát hiện.")}
    s = nap(db, kt["ban"], boi, ten_tep)
    return {**kt, "da_nap": kt["so_dong"], "settlement_id": s.id,
            "message": (f"Đã nạp chuyến {s.ma_tour}: {kt['so_dong']} dòng khách, "
                        f"{len(kt['ban'].get('chiet_tinh') or [])} dòng chiết tính, "
                        f"{len(kt['ban'].get('booking') or [])} booking.")}
