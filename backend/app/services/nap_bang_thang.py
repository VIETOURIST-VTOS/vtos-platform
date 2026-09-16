# -*- coding: utf-8 -*-
"""BỘ ĐỌC BẢNG THÁNG DỊCH VỤ LẺ – visa theo tháng, land theo tháng, outbound ghép lẻ theo tháng.

Chủ tịch chốt 16/9/2026: mở cửa riêng cho 49 tệp mà vòng nạp kho cũ trả về "không thấy chuyến".

────────────────────────────────────────────────────────────────────────────────
49 TỆP NÀY KHÔNG PHẢI BẢNG TỔNG – CHÚNG LÀ SỔ ĐĂNG KÝ TỪNG KHÁCH
────────────────────────────────────────────────────────────────────────────────

Đây là điều nhìn sai lúc đầu và phải nói lại cho đúng. Mở ra xem thì mỗi dòng là MỘT KHÁCH, có tên,
có sale, có giá bán và có các khoản phí của chính người ấy:

    QUYẾT TOÁN VISA CAN THÁNG 03.2026
      STT · Dịch vụ · Sale · Tên khách hàng · Giá bán · Thu khác · Tổng thu · Phí LSQ · Phí TLS/VFS

    QUYẾT TOÁN OUTBOUND LẺ T05.2026
      STT · SALES · TOUR · ĐỐI TÁC · TÊN KHÁCH HÀNG · GIÁ BÁN · THU KHÁC · TỔNG THU · GIÁ NET

    QUYẾT TOÁN LAND PHU QUOC THÁNG 01.2026
      NO · SALES · TÊN KHÁCH HÀNG · GIÁ BÁN · SL · VMB · SL · Phụ thu · TỔNG THU · LAND

Chúng không thiếu chi tiết. Chúng thiếu CỬA. Trong VTOS chỗ của chúng là dịch vụ lẻ (non-package):
một chuyến `tour_type="non_package"` cho mỗi tháng, mỗi khách một booking mang `service_type` đúng
loại (VISA / LAND / FLIGHT / OTHER), có `amount` (thu) và `cost_amount` (chi).

────────────────────────────────────────────────────────────────────────────────
VÌ SAO KHÔNG ÉP CHÚNG QUA CỬA KHO CŨ
────────────────────────────────────────────────────────────────────────────────

Đo ngày 16/9/2026: bộ đọc kho cũ đọc được 225 dòng khách / 435,1 triệu trên 21 tệp visa, trong khi
chính các tệp ấy tự khai tổng thu 1.836,3 triệu. Nó đọc được 24% rồi IM LẶNG bỏ phần còn lại – vì
đầu bảng visa có hai dòng tiêu đề và một khối tỷ giá mà nó không biết.

Nạp vào 24% mà không báo thiếu là kiểu sai tệ nhất: sai mà trông như đúng.

────────────────────────────────────────────────────────────────────────────────
BỐN LUẬT CỦA BỘ ĐỌC NÀY
────────────────────────────────────────────────────────────────────────────────

1. ĐỌC THEO NGHĨA CỦA TIÊU ĐỀ, KHÔNG THEO VỊ TRÍ CỘT. Đo trên 21 tệp visa: bốn kiểu bảng khác nhau
   (CAN/UK, Lẻ Châu Âu, Úc, Mỹ), cột ở vị trí khác nhau, tiêu đề nằm ở hàng 5 hoặc hàng 7, và có
   bảng dùng HAI hàng tiêu đề lồng nhau. Đếm cột theo vị trí là hỏng ngay tệp thứ hai.

2. KHÔNG TỰ QUY ĐỔI NGOẠI TỆ. Bảng Úc ghi `PHÍ VISA (AUD) 436,2 | TỶ GIÁ 18.500 | TT 8.069.700`.
   Bộ đọc lấy SỐ GỐC và ĐỒNG TIỀN, rồi BÁO THIẾU TỶ GIÁ – người nhập tra sổ tỷ giá (/ty-gia) và
   khai, máy mới nhân. Con số VND sẵn trong tệp được giữ lại làm SỐ ĐỂ ĐỐI CHIẾU, không phải để
   ghi: không ai biết tỷ giá 18.500 ấy của ngày nào và lấy ở đâu.

3. KHÔNG ĐỌC DÒNG `TỔNG CỘNG` THÀNH MỘT KHÁCH. Đọc nhầm một dòng ấy là nhân đôi tiền của cả tháng,
   và nhân đôi êm ru vì tổng vẫn "khớp" với chính nó.

4. LÃI = THU − CHI, MÁY TRỪ RA. Cột `LỢI NHUẬN` / `LN` trong tệp KHÔNG được đọc vào: nó là số dẫn
   xuất, và khi nó lệch với hiệu số thì cái lệch ấy chính là thứ cần nhìn thấy, không phải thứ để
   chép lại.

VÀ MỘT LUẬT NỀN: cột có TIỀN mà bộ đọc không nhận ra tên thì PHẢI NÊU RA, không được im lặng bỏ.
Đây đúng là luật đã cứu 199.500.000 đồng ở ô lạc ngày 16/9 – bỏ im lặng thì không ai biết để tìm.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

NGUON = "bang_thang_h1_2026"


def _kd(s) -> str:
    """Bỏ dấu, viết hoa, gộp khoảng trắng – để so tiêu đề mà không phụ thuộc cách gõ."""
    t = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"\s+", " ", t).strip()


# ── Tiêu đề → VAI TRÒ của cột ────────────────────────────────────────────────────────────────
# Thứ tự trong mỗi nhóm KHÔNG quan trọng, nhưng thứ tự GIỮA các nhóm thì có: khớp lần lượt từ
# trên xuống, nên nhóm hẹp phải đứng trước nhóm rộng. "TONG THU" phải được xét trước "THU", và
# "PHI VISA" trước "VISA".
BO_QUA = (
    # Không phải tiền, hoặc là số dẫn xuất KHÔNG được đọc vào (luật 4).
    "LOI NHUAN", "LN", "NOTE", "NOTES", "GHI CHU", "KET QUA", "STT", "NO", "TT", "SL",
    "SO LUONG", "CHECK IN SB", "ROT", "DAU",
    # NGÀY, không phải tiền. Excel lưu ngày bằng SỐ, nên không khai ở đây thì chúng lọt vào danh
    # sách "cột có tiền chưa nhận ra tên" và người đọc báo cáo phải đi soát bốn cột ngày vô ích.
    "KHOI HANH", "KET THUC", "NGAY", "NGAY DI", "NGAY VE", "NGAY NOP", "HAN",
)
VAI_TRO = [
    ("ten_khach", ("TEN KHACH HANG", "TEN KHACH", "FULL NAME", "HO TEN", "TEN HANH KHACH")),
    ("sale",      ("MA SALE", "SALES", "SALE", "NHAN VIEN")),
    ("doi_tac",   ("DOI TAC", "NHA CUNG CAP", "NCC")),
    ("dich_vu",   ("DICH VU", "QUOC GIA", "CHUONG TRINH", "CODE TOUR", "TOUR", "LOAI VISA")),
    # ── THU ──
    ("tong_thu",  ("TONG THU", "TONG DOANH THU")),
    ("gia_ban",   ("GIA BAN", "GIA THU", "DOANH THU", "GIA VE")),
    ("thu_khac",  ("THU KHAC", "PHU THU", "VMB", "VE MAY BAY")),
    # ── CHI ──  (mọi thứ bắt đầu bằng "PHI" đều là chi; xem `_vai_tro`)
    ("tong_chi",  ("TONG CHI",)),
    ("chi",       ("GIA NET", "TONG LAND", "LAND", "QUA TANG", "GIA VON", "CHI KHAC")),
    # ── Ngoại tệ ──
    ("ty_gia",    ("TY GIA", "TI GIA", "TYGIA")),
]

# Đồng tiền ghi trong ngoặc ngay trên tiêu đề cột: "PHÍ VISA (AUD)", "Phí (USD)".
_RE_TIEN_TE = re.compile(r"\((USD|EUR|AUD|CAD|GBP|JPY|KRW|CNY|SGD|THB|TWD|HKD)\)")

# Dòng kết bảng. Gặp là DỪNG – không đọc thành một khách (luật 3).
_RE_TONG = re.compile(r"^(TONG|CONG|TOTAL)\b")


def _vai_tro(nhan: str) -> tuple[str, str]:
    """Một tiêu đề → (vai trò, đồng tiền). Vai trò rỗng = KHÔNG NHẬN RA."""
    n = _kd(nhan)
    if not n:
        return "", ""
    tt = (_RE_TIEN_TE.search(n) or [None, ""])[1] if _RE_TIEN_TE.search(n) else ""
    # Bỏ phần đồng tiền đi rồi mới so, để "PHI VISA (AUD)" khớp với "PHI VISA".
    n_sach = _RE_TIEN_TE.sub("", n).strip()
    if n_sach in BO_QUA:
        return "bo_qua", ""
    for vt, ds in VAI_TRO:
        if any(n_sach == k or n_sach.startswith(k + " ") or n_sach.endswith(" " + k) for k in ds):
            return vt, tt
    # Tiền tố CHỈ HƯỚNG. Đặt SAU vòng trên để chúng không nuốt mất cột nào đã có tên riêng.
    #
    # Người lập bảng đã tự đặt nhãn nhóm cho cột: "CHI NÓN", "CHI BH", "CHI NỘP THUẾ", "THU VISA",
    # "THU VAT". Đo trên 49 tệp: 30 cột có tiền mang một trong hai tiền tố ấy, và không cột nào
    # trong số đó bị xếp nhầm. Bỏ qua chúng là bỏ rơi tiền có thật chỉ vì chưa ai liệt kê tên.
    if n_sach.startswith("PHI") or n_sach.startswith("CHI "):
        return "chi", tt
    if n_sach.startswith("THU "):
        return "thu_khac", tt
    return "", tt


def _mo_o_gop(ws) -> dict:
    """Ô gộp: openpyxl chỉ để giá trị ở ô trên-trái. Trải ra để mọi cột dưới một tiêu đề gộp đều
    đọc được tiêu đề ấy – bảng visa Mỹ gộp 'TỔNG THU' trên hai cột 'GIÁ BÁN' và 'THU KHÁC'."""
    ra = {}
    for v in ws.merged_cells.ranges:
        goc = ws.cell(v.min_row, v.min_col).value
        if goc is None:
            continue
        for r in range(v.min_row, v.max_row + 1):
            for c in range(v.min_col, v.max_col + 1):
                ra[(r, c)] = goc
    return ra


def _o(ws, gop, r, c):
    v = ws.cell(r, c).value
    return gop.get((r, c)) if v is None else v


def tim_tieu_de(ws, gop, het: int) -> int | None:
    """Hàng tiêu đề = hàng có STT/NO và ÍT NHẤT MỘT cột tiền nhận ra được.

    Tiêu đề nằm ở hàng 5, 7 hoặc 9 tuỳ tệp nên phải TÌM chứ không đếm.

    Bản đầu đòi phải có cột TÊN KHÁCH, và luật ấy SAI: đo trên 49 tệp thì 9 tệp không có cột nào
    mang tên khách – 6 tệp land Đà Nẵng–Huế và 3 bảng tháng của Điều hành ghi theo TOUR và ĐỐI TÁC
    ("VLT501 · Happy Tour · 15/1/2026"), vì chúng là sổ công nợ với đối tác chứ không phải sổ khách.
    Đòi tên khách là loại đúng 9 tệp ấy ra, im lặng.
    """
    for r in range(1, min(het, 20) + 1):
        nhan = [_kd(_o(ws, gop, r, c)) for c in range(1, ws.max_column + 1)]
        if not ({"STT", "NO"} & set(nhan)):
            continue
        # Đếm trên CẢ hàng này và hàng dưới: bảng dùng tiêu đề lồng thì hàng trên chỉ ghi
        # "THU · THU · THU · CHI", tên cột thật nằm ở hàng dưới.
        tien = set()
        for rr in (r, r + 1):
            for c in range(1, ws.max_column + 1):
                vt, _ = _vai_tro(_o(ws, gop, rr, c))
                if vt in ("tong_thu", "gia_ban", "thu_khac", "chi", "tong_chi"):
                    tien.add((rr, c))
        # MỘT cột tiền là đủ. Ngưỡng HAI từng được đặt cho chắc, nhưng nó loại oan một bảng chỉ
        # có một cột tiền duy nhất – mà chữ "STT"/"NO" viết ra đã là mỏ neo đủ chắc: dòng dữ liệu
        # mang SỐ thứ tự, không mang chữ "STT".
        if len(tien) >= 1:
            return r
    return None


def doc_cot(ws, gop, hang_td: int, hang_bd: int | None = None) -> dict[int, tuple[str, str, str]]:
    """Cột → (vai trò, đồng tiền, nhãn đầy đủ). Ghép tiêu đề của hàng `hang_td` với hàng ngay dưới.

    Ghép hai hàng vì bảng Úc và bảng visa Mỹ dùng tiêu đề LỒNG: hàng trên ghi 'PHÍ VISA (AUD)' gộp
    ba cột, hàng dưới ghi 'PHÍ VISA (AUD)' / 'TỶ GIÁ' / 'TT'. Chỉ đọc hàng trên thì ba cột ấy mang
    cùng một tên và cột tỷ giá biến thành một khoản phí.
    """
    # Hàng dưới CHỈ được đọc như tiêu đề khi nó THẬT SỰ là tiêu đề. Bảng tiêu đề MỘT hàng thì hàng
    # ngay dưới đã là DỮ LIỆU, và ghép nó vào nhãn cột làm nhãn dính luôn số tiền của khách đầu
    # tiên: cột "Người dịch" thành "Người dịch 450000". Nhãn bẩn thì lời báo gửi cho người lập cũng
    # bẩn theo, và họ không tìm ra cột nào để sửa.
    if hang_bd is None:
        hang_bd = hang_bat_dau(ws, gop, hang_td, ws.max_row)
    co_hang_duoi = hang_bd > hang_td + 1
    ra = {}
    for c in range(1, ws.max_column + 1):
        tren = str(_o(ws, gop, hang_td, c) or "").strip()
        duoi = str(_o(ws, gop, hang_td + 1, c) or "").strip() if co_hang_duoi else ""
        # Hàng dưới CỤ THỂ HƠN nên xét trước; chỉ lùi về hàng trên khi hàng dưới không nói gì.
        vt, tt = _vai_tro(duoi)
        nhan = duoi
        if not vt:
            vt, tt2 = _vai_tro(tren)
            nhan = tren or duoi
            tt = tt or tt2
        if not vt and tren and duoi and _kd(tren) != _kd(duoi):
            # NHÓM + TÊN RIÊNG. Bảng dùng tiêu đề lồng ghi nhóm ở hàng trên và tên riêng ở hàng
            # dưới: hàng trên "CHI", hàng dưới "NÓN" → cột ấy là "CHI NÓN". Xét riêng từng hàng thì
            # cả hai đều không khớp gì, và một cột tiền có thật rơi vào rổ "không nhận ra".
            # Đo trên 49 tệp: luật này nhận thêm 30 cột, tất cả đều mang nhóm CHI hoặc THU.
            vt, tt3 = _vai_tro(f"{tren} {duoi}")
            nhan = f"{tren} {duoi}"
            tt = tt or tt3
        if not tt:
            tt = (_RE_TIEN_TE.search(_kd(tren)) or _RE_TIEN_TE.search(_kd(duoi)) or [None, ""])[1] \
                if (_RE_TIEN_TE.search(_kd(tren)) or _RE_TIEN_TE.search(_kd(duoi))) else ""
        # Ô TIÊU ĐỀ GỘP TRÊN CẢ HAI HÀNG trả về cùng một chữ ở `tren` và `duoi`, và nối thẳng lại
        # thì nhãn thành "VP VFS VP VFS". Nhãn này đi vào câu báo cho người đọc ("cột 'VP VFS' có
        # tiền nhưng bộ đọc không biết THU hay CHI"), nên một nhãn lặp là một câu khó hiểu đúng lúc
        # người ta đang cần hiểu. Đo trên tệp thật ngày 16/9: 2 trong 3 nhãn lạ bị lặp kiểu này.
        ghep = tren if _kd(tren) == _kd(duoi) else (tren + " " + duoi)
        ra[c] = (vt, tt, re.sub(r"\s+", " ", ghep.strip())[:60])
    return ra


def _so(v) -> float | None:
    """Ô này có phải một con số tiền không. Chuỗi '1.234.567' và '1,234,567' đều được."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        t = v.strip().replace(" ", "")
        if not t or not re.fullmatch(r"-?[\d.,]+", t):
            return None
        # Dấu cuối cùng là dấu thập phân nếu nó cách đuôi 1–2 chữ số, còn lại là dấu nghìn.
        t = t.replace(".", ",")
        *dau, cuoi = t.split(",")
        if dau and len(cuoi) <= 2:
            t = "".join(dau) + "." + cuoi
        else:
            t = "".join(dau) + cuoi
        try:
            return float(t)
        except ValueError:
            return None
    return None


def la_dong_tong(ws, gop, r, ncol) -> bool:
    """Dòng này có phải dòng TỔNG CỘNG không (luật 3).

    Nhận theo CHỮ ở ba ô đầu chứ không theo vị trí: dòng tổng của bảng Úc ghi 'TỔNG CỘNG' ở cột 1,
    của bảng visa lẻ ghi ở cột 1 nhưng cột 2–4 rỗng. Đọc nhầm nó thành một khách là nhân đôi tiền
    của cả tháng, và nhân đôi êm ru vì tổng vẫn khớp với chính nó.
    """
    for c in range(1, min(ncol, 4) + 1):
        v = _o(ws, gop, r, c)
        if isinstance(v, str) and _RE_TONG.match(_kd(v)):
            return True
    return False


def hang_bat_dau(ws, gop, hang_td: int, het: int) -> int:
    """Dòng dữ liệu đầu tiên. Tiêu đề có bảng MỘT hàng, có bảng HAI hàng lồng nhau.

    Bản đầu luôn nhảy hai hàng, và luật ấy SAI với bảng tiêu đề một hàng: nó ăn mất DÒNG KHÁCH ĐẦU
    TIÊN. Đo được trên 'QUYẾT TOÁN VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY' – tệp có đúng hai khách,
    bộ đọc lấy một, ra 3.200.000 trong khi dòng TỔNG CỘNG của chính tệp ghi 6.400.000. Mất đúng một
    nửa, và mất im lặng.

    Cách nhận: hàng ngay dưới tiêu đề mà ô đầu là SỐ (số thứ tự 1) thì đó đã là dữ liệu.
    """
    r = hang_td + 1
    if r > het:
        return r
    for c in range(1, min(ws.max_column, 3) + 1):
        if isinstance(ws.cell(r, c).value, (int, float)) and not isinstance(ws.cell(r, c).value, bool):
            return r
    return hang_td + 2


def doc_dong(ws, gop, cot: dict, hang_td: int, het: int) -> tuple[list, list]:
    """Đọc các dòng dữ liệu. Trả (dòng, than_phiền).

    Dừng ở dòng TỔNG CỘNG. Dòng hoàn toàn rỗng thì bỏ qua chứ KHÔNG dừng: nhiều bảng có một dòng
    trắng ngăn giữa hai nhóm khách, dừng ở đó là mất nửa bảng dưới.
    """
    dong, than = [], []
    for r in range(hang_bat_dau(ws, gop, hang_td, het), het + 1):
        if la_dong_tong(ws, gop, r, ws.max_column):
            break
        d = {"_hang": r, "ten_khach": "", "sale": "", "doi_tac": "", "dich_vu": "",
             "thu": 0.0, "chi": 0.0, "khoan_chi": [], "ngoai_te": [], "tong_thu_trong_tep": None,
             "tong_chi_trong_tep": None, "o_khong_nhan_ra": []}
        tp_thu = 0.0
        co_gi = False
        for c, (vt, tt, nhan) in cot.items():
            # Ở DÒNG DỮ LIỆU đọc THẲNG ô, KHÔNG trải ô gộp ra.
            #
            # Trải ô gộp là đúng cho HÀNG TIÊU ĐỀ (mọi cột dưới một tiêu đề gộp phải đọc được tiêu
            # đề ấy) và SAI hẳn cho hàng dữ liệu: một ô 'Tổng thu' gộp trên hai cột sẽ trả cùng một
            # số ở cả hai, và số ấy được cộng hai lần.
            #
            # Đo ngày 16/9/2026 trên 49 tệp: trải ô gộp ở hàng dữ liệu cho tổng thu 10.359.011.855 đ
            # trong khi chính các tệp tự khai 5.202.295.011 đ – gần đúng GẤP ĐÔI. Con số gấp đôi ấy
            # trông vẫn hợp lý nếu không ai đi đối chiếu, và đó là điều nguy hiểm của nó.
            v = ws.cell(r, c).value
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            if vt in ("ten_khach", "sale", "doi_tac", "dich_vu"):
                if isinstance(v, str) and v.strip():
                    d[vt] = (d[vt] + " " + v.strip()).strip()[:200]
                    co_gi = True
                continue
            if vt in ("bo_qua", "ty_gia"):
                continue
            n = _so(v)
            if n is None:
                continue
            co_gi = True
            if tt:
                # KHÔNG NHÂN. Giữ số gốc và đồng tiền; tỷ giá là việc của người nhập (luật 2).
                d["ngoai_te"].append({"khoan": nhan, "tien_te": tt, "so_tien_goc": n})
            elif vt == "tong_thu":
                d["tong_thu_trong_tep"] = n
            elif vt == "tong_chi":
                d["tong_chi_trong_tep"] = n
            elif vt in ("gia_ban", "thu_khac"):
                tp_thu += n
            elif vt == "chi":
                d["chi"] += n
                d["khoan_chi"].append({"khoan": nhan, "so_tien": n})
            elif not vt:
                d["o_khong_nhan_ra"].append({"cot": c, "nhan": nhan, "so_tien": n})
        if not co_gi:
            continue

        # THU: ưu tiên ô TỔNG THU của chính tệp, nhưng KHÔNG im lặng khi nó lệch với tổng các phần.
        # Người lập gõ tay ô tổng ở nhiều bảng; lệch ở đó là lệch giữa hai con số của cùng một người,
        # và đó đúng là thứ phải đưa ra chứ không phải thứ để chọn hộ.
        if d["tong_thu_trong_tep"] is not None:
            d["thu"] = d["tong_thu_trong_tep"]
            if tp_thu and abs(tp_thu - d["tong_thu_trong_tep"]) >= 1:
                than.append(f"Dòng {r}: ô 'Tổng thu' ghi {d['tong_thu_trong_tep']:,.0f} nhưng cộng "
                            f"các cột thu ra {tp_thu:,.0f} – lệch {abs(tp_thu - d['tong_thu_trong_tep']):,.0f}. "
                            f"Lấy theo ô 'Tổng thu'; người lập cần soát lại.")
        else:
            d["thu"] = tp_thu

        if d["tong_chi_trong_tep"] is not None and d["chi"] \
                and abs(d["chi"] - d["tong_chi_trong_tep"]) >= 1:
            than.append(f"Dòng {r}: ô 'Tổng chi' ghi {d['tong_chi_trong_tep']:,.0f} nhưng cộng các "
                        f"cột chi ra {d['chi']:,.0f}. Lấy theo TỔNG CÁC CỘT – ô tổng là số gõ tay.")
        if d["tong_chi_trong_tep"] is not None and not d["chi"]:
            d["chi"] = d["tong_chi_trong_tep"]

        for o in d["o_khong_nhan_ra"]:
            than.append(f"Dòng {r}: cột {o['nhan']!r} mang {o['so_tien']:,.0f} đ nhưng bộ đọc không "
                        f"biết đây là THU hay CHI – KHÔNG cộng vào đâu cả. Người lập cần đặt lại tên "
                        f"cột, hoặc báo để khai thêm.")

        # Lãi là HIỆU SỐ, máy trừ ra (luật 4). Còn khoản ngoại tệ chưa có tỷ giá thì CHƯA có lãi –
        # trừ khi biết chi là bao nhiêu thì ra một con số lãi cao hơn sự thật.
        d["cho_ty_gia"] = bool(d["ngoai_te"])
        d["lai"] = None if d["cho_ty_gia"] else round(d["thu"] - d["chi"], 2)
        dong.append(d)
    return dong, than


# ── KỲ của bảng: tháng nào, năm nào ─────────────────────────────────────────────────────────────
# Đo trên 49 tệp: kỳ nằm trong TÊN TỆP và chỉ trong tên tệp, với sáu cách viết khác nhau —
#   "THÁNG 03.2026" · "THÁNG 1.2026" · "T3.2026" · "T01.26" · "VTD01.2026" · "LẺ THÁNG 03.2026"
# Không tệp nào khai kỳ ở một ô bên trong. Đây là chỗ DUY NHẤT được phép suy từ tên tệp, và chỉ
# suy ra một cái NHÃN (tháng nào), không suy ra một con số tiền nào.
_RE_KY = (
    re.compile(r"THANG\s*(\d{1,2})[.\-/\s]+(\d{2,4})"),     # THANG 03.2026
    re.compile(r"\bT\s*(\d{1,2})[.\-/](\d{2,4})"),          # T3.2026 · T01.26
    re.compile(r"\bVTD\s*(\d{1,2})[.\-/](\d{2,4})"),        # VTD01.2026
    re.compile(r"^(\d{1,2})[.\-/](\d{4})"),                 # 1.2026 (tệp tên "THÁNG 1.2026")
)


# Kỳ viết THIẾU NĂM: "QUYẾT TOÁN VISA MỸ THÁNG 1". Đọc ra tháng, để năm TRỐNG, và NÓI RA.
# Sáu tệp visa Mỹ viết kiểu này. Điền hộ năm 2026 vì "các tệp khác đều 2026" là đoán — và đoán sai
# một lần là cả một tháng tiền nằm nhầm năm tài chính.
_RE_THANG_TRONG = re.compile(r"THANG\s*(\d{1,2})(?!\s*[.\-/]?\s*\d)")
# Kỳ viết KHÔNG có chữ THÁNG và không có chữ T: "QTOB LE 02.2026". Chỉ dùng khi tên tệp KHÔNG chứa
# một ngày đầy đủ – "QTT LAND VĨNH HY 03.03.2026" là một NGÀY, không phải một tháng, và đọc nhầm nó
# thành tháng 3 là xếp một đoàn vào bảng tháng.
_RE_NGAY_DAY_DU = re.compile(r"\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}")
_RE_KY_TRAN = re.compile(r"(?<!\d)(\d{1,2})[.\-/](\d{4})(?!\d)")


def ky_tu_ten_tep(ten_tep: str) -> tuple[int | None, int] | None:
    """(năm, tháng) đọc từ tên tệp. Năm có thể là None khi tên tệp chỉ nói tháng.

    KHÔNG đoán nếu tên tệp không nói. Đây là chỗ DUY NHẤT được phép suy từ tên tệp, và chỉ suy ra
    một cái NHÃN – không suy ra một con số tiền nào.
    """
    t = _kd(re.sub(r"\.(xlsx|xlsm|xls)$", "", ten_tep or "", flags=re.I))
    for rx in _RE_KY:
        m = rx.search(t)
        if not m:
            continue
        thang, nam = int(m.group(1)), int(m.group(2))
        if nam < 100:
            nam += 2000
        if 1 <= thang <= 12 and 2020 <= nam <= 2030:
            return nam, thang
    if not _RE_NGAY_DAY_DU.search(t):
        m = _RE_KY_TRAN.search(t)
        if m and 1 <= int(m.group(1)) <= 12 and 2020 <= int(m.group(2)) <= 2030:
            return int(m.group(2)), int(m.group(1))
    m = _RE_THANG_TRONG.search(t)
    if m and 1 <= int(m.group(1)) <= 12:
        return None, int(m.group(1))       # biết tháng, KHÔNG biết năm
    return None


# Loại dịch vụ của VTOS (`bookings.service_type`) suy từ TÊN TỆP. Suy từ tên là suy được ở đây vì
# chính người lập đặt tên theo loại việc: "QUYẾT TOÁN VISA CAN THÁNG 03", "LAND PHU QUOC THÁNG 01".
def loai_dich_vu(ten_tep: str) -> str:
    T = _kd(ten_tep)
    if "VISA" in T:
        return "VISA"
    if "LAND" in T:
        return "LAND"
    return "OTHER"


def doc_tep(noi_dung: bytes, ten_tep: str) -> dict:
    """Đọc MỘT bảng tháng. KHÔNG ghi gì, KHÔNG chạm cơ sở dữ liệu.

    Trả về đủ thứ người duyệt cần nhìn trước khi quyết:
      · `dong`        – từng khách, có thu, chi, lãi (máy trừ) và các khoản ngoại tệ chờ tỷ giá
      · `thieu`       – mọi điều bộ đọc không chắc, NÓI RA hết chứ không im lặng bỏ
      · `tong_*`      – tổng do MÁY CỘNG TỪ DÒNG, không chép ô tổng của tệp
      · `tong_trong_tep` – ô TỔNG CỘNG của chính tệp, để NGƯỜI ĐỐI CHIẾU, không để ghi

    Vì sao tách hai con số tổng: đo ngày 16/9/2026 trên 49 tệp, ô TỔNG CỘNG của
    'QUYẾT TOÁN OUTBOUND LẺ T01.2026' là `=SUM(H6:H52)` trong khi bảng chạy tới hàng 55 — ba khách
    cuối nằm NGOÀI vùng cộng, 19.970.000 đ. Tệp ấy báo thiếu ngần ấy tiền từ lúc lập tới nay, và
    chép lại ô tổng là chép luôn cái sót.
    """
    from io import BytesIO

    import openpyxl

    from app.services.nap_kho_cu import het_hang_that

    wb = openpyxl.load_workbook(BytesIO(noi_dung), data_only=True)
    ws = wb[wb.sheetnames[0]]
    het = het_hang_that(ws)
    gop = _mo_o_gop(ws)
    td = tim_tieu_de(ws, gop, het)

    d = {"ten_tep": ten_tep, "loai_dich_vu": loai_dich_vu(ten_tep), "ky": ky_tu_ten_tep(ten_tep),
         "so_sheet": len(wb.sheetnames), "hang_tieu_de": td,
         "dong": [], "thieu": [], "cot_khong_nhan_ra": [],
         "tong_thu": 0.0, "tong_chi": 0.0, "so_cho_ty_gia": 0, "tong_trong_tep": None}

    if td is None:
        d["thieu"].append("Không tìm được hàng tiêu đề (hàng có STT/NO và ít nhất hai cột tiền). "
                          "Bộ đọc KHÔNG đoán theo vị trí cột – tệp này cần người xem lại bố cục.")
        return d
    if d["ky"] is None:
        d["thieu"].append("Tên tệp không nói tháng nào. Bảng tháng phải biết kỳ của nó, và bộ đọc "
                          "không đoán kỳ từ nội dung – người lập cần đặt lại tên tệp có tháng/năm.")
    elif d["ky"][0] is None:
        d["thieu"].append(f"Tên tệp nói THÁNG {d['ky'][1]} nhưng KHÔNG nói năm. Bộ đọc không điền hộ "
                          f"năm – người nạp phải chọn năm, vì đoán sai một lần là cả một tháng tiền "
                          f"nằm nhầm năm tài chính.")

    cot = doc_cot(ws, gop, td, hang_bat_dau(ws, gop, td, het))
    for c, (vt, tt, nhan) in cot.items():
        if vt or not nhan:
            continue
        if any(_so(ws.cell(r, c).value) is not None for r in range(td + 1, min(het, td + 40) + 1)):
            d["cot_khong_nhan_ra"].append(nhan)

    d["dong"], than = doc_dong(ws, gop, cot, td, het)
    d["thieu"].extend(than)
    d["tong_thu"] = round(sum(x["thu"] for x in d["dong"]), 2)
    d["tong_chi"] = round(sum(x["chi"] for x in d["dong"]), 2)
    d["so_cho_ty_gia"] = sum(1 for x in d["dong"] if x["cho_ty_gia"])
    # Lãi CỦA CẢ BẢNG cũng là hiệu số, và chỉ có khi không còn khoản nào chờ tỷ giá.
    d["lai"] = None if d["so_cho_ty_gia"] else round(d["tong_thu"] - d["tong_chi"], 2)

    # Ô TỔNG CỘNG của chính tệp – để đối chiếu, KHÔNG để ghi.
    rt = next((r for r in range(td + 2, het + 1) if la_dong_tong(ws, gop, r, ws.max_column)), None)
    if rt is not None:
        ctt = [c for c, (vt, tt, _) in cot.items() if vt == "tong_thu" and not tt] \
            or [c for c, (vt, tt, _) in cot.items() if vt in ("gia_ban", "thu_khac") and not tt]
        s = sum(_so(ws.cell(rt, c).value) or 0 for c in ctt)
        if s:
            d["tong_trong_tep"] = s
            if abs(s - d["tong_thu"]) >= 1:
                d["thieu"].append(
                    f"Ô TỔNG CỘNG của tệp ghi {s:,.0f} đ, nhưng cộng {len(d['dong'])} dòng ra "
                    f"{d['tong_thu']:,.0f} đ – lệch {abs(s - d['tong_thu']):,.0f} đ. VTOS lấy theo "
                    f"TỔNG CÁC DÒNG. Người lập cần soát lại vùng cộng của ô tổng.")

    if d["so_cho_ty_gia"]:
        n = sum(len(x["ngoai_te"]) for x in d["dong"])
        d["thieu"].append(
            f"{n} khoản ngoại tệ trên {d['so_cho_ty_gia']} dòng CHƯA CÓ TỶ GIÁ. Bộ đọc KHÔNG tự quy "
            f"đổi – người lập vào Sổ tỷ giá (/ty-gia) khai tỷ giá của NGÀY CHI THẬT kèm chứng từ, "
            f"rồi máy mới nhân. Số VND sẵn trong tệp chỉ dùng để đối chiếu.")
    for nhan in d["cot_khong_nhan_ra"]:
        d["thieu"].append(f"Cột {nhan!r} có tiền nhưng bộ đọc không biết đây là THU hay CHI – "
                          f"KHÔNG cộng vào đâu cả. Người lập cần đặt lại tên cột.")
    return d
