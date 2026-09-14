# -*- coding: utf-8 -*-
"""Xuất khối dòng tiền của màn hình 01 ra Excel (anh Tuấn chốt 14/9/2026: "em nối luôn").

Trước vòng này nút "Xuất Excel" chỉ hiện câu "đang xây dựng". Một nút hứa rồi không làm còn tệ hơn
không có nút: người dùng bấm, không được gì, và lần sau họ không tin nút nào nữa.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN ĐIỀU TỆP NÀY GIỮ
═══════════════════════════════════════════════════════════════════════════════════════════════

1. EXCEL VÀ MÀN HÌNH KHÔNG BAO GIỜ NÓI KHÁC NHAU. Hàm này nhận ĐÚNG cái gói mà
   `khung_dong_tien.ghep()` đã trả cho màn hình, không truy vấn lại cơ sở dữ liệu lần nữa. Truy vấn
   lại là mở đường cho hai con số: màn hình lấy lúc 9 giờ, Excel lấy lúc 9 giờ 5, và người đọc
   không có cách nào biết vì sao lệch.

2. SEC-02 — CẮT DÒNG Ở MÁY CHỦ. Gói vào đã được cắt theo vai đăng nhập; tệp này chỉ ghi lại đúng
   những dòng nhận được. KHÔNG có một câu `if vai ==` nào trong đây, và cũng không được có: thêm
   một câu như thế là Excel bày ra dòng mà màn hình đã giấu.

3. RỖNG KHÁC KHÔNG — CẢ TRONG EXCEL. Ô chưa có nguồn ghi chữ "Chưa có nguồn", KHÔNG ghi số 0 và
   cũng không để trắng. Để trắng thì mở trong Excel, bấm Sum một cột là nó cộng như thể ô ấy bằng
   0 — đúng cái nhầm mà cả hệ thống đang chống. Ghi chữ thì Sum bỏ qua, và người đọc thấy ngay.

4. BA TRANG, KHÔNG MỘT. Màn hình có hai kiểu xem (luỹ kế và trong từng khoảng) và một trang nguồn
   số. Xuất mỗi kiểu đang xem thì hai người xuất hai lúc ra hai tệp khác nhau cùng tên. Nên tệp
   nào cũng có đủ ba trang:
        Luỹ kế · Trong từng khoảng · Nguồn số
   Trang "Nguồn số" chính là trang /dong-tien/nguon: dòng nào đầy đủ, dòng nào còn thiếu, ai nhập,
   cửa nhập nào phải dựng. Đó là phần người nhận tệp cần nhất để đi đòi số.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.services import khung_dong_tien as KHUNG

# Màu lấy từ bộ nhận diện VTOS bản SÁNG — tệp Excel in ra giấy và mở trên máy người khác, không
# theo nền tối của trang web. openpyxl dùng mã ARGB, nên tiền tố "FF".
NAVY = "FF14538D"
NAVY_NHAT = "FFE7EFF7"
XAM_NHAT = "FFF4F7FA"
VIEN = "FFE3E9EF"
DO = "FFC0392B"
VANG = "FF8A6D1B"
XANH = "FF2E6F3E"

CHUA_CO = "Chưa có nguồn"

_vien = Side(style="thin", color=VIEN)
_khung = Border(left=_vien, right=_vien, top=_vien, bottom=_vien)


def _dau(o, chu_hoa=False):
    o.font = Font(bold=True, color="FFFFFFFF", size=10)
    o.fill = PatternFill("solid", fgColor=NAVY)
    o.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    o.border = _khung


def _o_tien(o, gia_tri):
    """Một ô tiền. None → chữ "Chưa có nguồn"; số → số thật có định dạng nghìn.

    KHÔNG dùng 0 và không để trắng cho ô rỗng — xem điều 3 ở đầu tệp.
    """
    o.border = _khung
    if gia_tri is None:
        o.value = CHUA_CO
        o.font = Font(italic=True, color="FF7B8B99", size=10)
        o.alignment = Alignment(horizontal="right")
    else:
        o.value = gia_tri
        o.number_format = '#,##0;[Red]-#,##0'
        o.alignment = Alignment(horizontal="right")


def _rong_cot(ws, rong: list[int]):
    for i, w in enumerate(rong, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _tieu_de_trang(ws, k: dict, ten_phu: str, so_cot: int):
    """Ba dòng đầu của mỗi trang: tên bảng · phạm vi · vai đang xem. Người nhận tệp qua Zalo hay
    email không có màn hình bên cạnh để đối chiếu, nên tệp phải tự nói nó là của ai và của cái gì."""
    pn = ten_phap_nhan(k)
    ws.cell(1, 1, f"VTOS · Dòng tiền — {ten_phu}" + (f" · {pn}" if pn else "")).font = Font(
        bold=True, size=13, color=NAVY)
    ws.cell(2, 1, k.get("cau_pham_vi") or "").font = Font(size=10, color="FF64798C")
    ws.cell(3, 1, f"Vai đang xem: {k.get('vai_tro') or ''}"
                  f" · Xuất lúc {date.today():%d-%m-%Y}").font = Font(size=10, color="FF64798C")
    for d in (1, 2, 3):
        ws.merge_cells(start_row=d, start_column=1, end_row=d, end_column=max(so_cot, 2))


def _trang_bang(wb: Workbook, k: dict, theo_khoang: bool):
    cot = k.get("cot") or []
    ten = "Trong từng khoảng" if theo_khoang else "Lũy kế"
    ws = wb.create_sheet(ten)
    _tieu_de_trang(ws, k, ten, len(cot) + 2)

    h = 5
    ws.cell(h, 1, "Dòng tiền")
    _dau(ws.cell(h, 1))
    for i, c in enumerate(cot, start=2):
        tu = (c.get("tu_hien_khoang") if theo_khoang else c.get("tu_hien")) or ""
        o = ws.cell(h, i, f"{c.get('ten','')}\n{tu} – {c.get('den_hien','')}")
        _dau(o)
    o = ws.cell(h, len(cot) + 2, "Nguồn số")
    _dau(o)

    d = h + 1
    for r in k.get("dong") or []:
        ws.cell(d, 1, r.get("ten") or "").border = _khung
        if r.get("tu_tinh"):
            ws.cell(d, 1).font = Font(bold=True, size=10)
            ws.cell(d, 1).fill = PatternFill("solid", fgColor=XAM_NHAT)

        if r.get("mot_moc"):
            # Dòng MỘT MỐC: một con số tại ngày đối soát, không phải một số cho mỗi mốc. Gộp ô lại
            # và nói rõ, thay vì chép cùng một số ra bốn cột cho đầy — chép ra bốn cột thì người đọc
            # sẽ so bốn cột với nhau và tưởng nó không đổi qua thời gian.
            _o_tien(ws.cell(d, 2), r.get("so_mot_moc"))
            ws.merge_cells(start_row=d, start_column=2, end_row=d, end_column=len(cot) + 1)
            ws.cell(d, 2).alignment = Alignment(horizontal="right")
        else:
            so = (r.get("so_khoang") if (theo_khoang and r.get("la_dong_chay")) else r.get("so")) or {}
            for i, c in enumerate(cot, start=2):
                _o_tien(ws.cell(d, i), so.get(c.get("ma")))

        o = ws.cell(d, len(cot) + 2, "Tự cộng" if r.get("tu_tinh") else (r.get("nhan_trang_thai") or ""))
        o.border = _khung
        o.font = Font(size=10, color={"con_thieu": DO, "chua_doi_soat": VANG,
                                      "day_du": XANH}.get(r.get("trang_thai"), "FF64798C"))
        d += 1

    # Dòng đáy: TÊN do máy chủ cắt theo vai (bản TGĐ mang tên khác), không gõ cứng ở đây.
    ws.cell(d, 1, k.get("ten_dong_thuan") or "").font = Font(bold=True, size=10)
    ws.cell(d, 1).border = _khung
    ws.cell(d, 1).fill = PatternFill("solid", fgColor=NAVY_NHAT)
    thuan = (k.get("dong_tien_thuan_khoang") if theo_khoang else k.get("dong_tien_thuan")) or {}
    for i, c in enumerate(cot, start=2):
        _o_tien(ws.cell(d, i), thuan.get(c.get("ma")))
        ws.cell(d, i).font = Font(bold=True, size=10)
        ws.cell(d, i).fill = PatternFill("solid", fgColor=NAVY_NHAT)
    ws.cell(d, len(cot) + 2).border = _khung
    ws.cell(d, len(cot) + 2).fill = PatternFill("solid", fgColor=NAVY_NHAT)

    # Câu nhắc đi THEO KIỂU XEM, giống hệt trên màn hình: luỹ kế thì cộng bốn cột là sai, theo
    # khoảng thì cộng bốn cột lại đúng. Câu này ở lại trong tệp vì tệp sẽ đi xa khỏi màn hình.
    nhac = (k.get("cong_bon_cot_khi_xem_khoang") if theo_khoang else k.get("cong_bon_cot_la_sai")) or ""
    o = ws.cell(d + 2, 1, nhac)
    o.font = Font(size=9, italic=True, color="FF64798C")
    o.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=d + 2, start_column=1, end_row=d + 4, end_column=len(cot) + 2)

    o = ws.cell(d + 6, 1, "Ô ghi “Chưa có nguồn” là CHƯA AI NHẬP, không phải bằng 0 — đừng thay "
                          "bằng số 0 khi dùng lại tệp này.")
    o.font = Font(size=9, italic=True, color="FF64798C")
    ws.merge_cells(start_row=d + 6, start_column=1, end_row=d + 6, end_column=len(cot) + 2)

    ws.row_dimensions[h].height = 34
    _rong_cot(ws, [34] + [17] * len(cot) + [15])
    ws.freeze_panes = ws.cell(h + 1, 2)


def _trang_nguon(wb: Workbook, k: dict):
    """Trang NGUỒN SỐ — bản Excel của trang /dong-tien/nguon."""
    ws = wb.create_sheet("Nguồn số")
    _tieu_de_trang(ws, k, "nguồn số của từng dòng", 7)

    tt = k.get("tom_tat_trang_thai") or {}
    o = ws.cell(4, 1, f"{tt.get('day_du', 0)} đầy đủ · {tt.get('chua_doi_soat', 0)} chưa đối soát · "
                      f"{tt.get('con_thieu', 0)} còn thiếu")
    o.font = Font(bold=True, size=10)

    cot = ["Dòng tiền", "Nguồn số", "Nguyên nhân", "Bộ phận chịu", "Nguồn hiện có",
           "Cửa nhập phải dựng", "Hạn xử lý"]
    for i, c in enumerate(cot, start=1):
        _dau(ws.cell(6, i, c))

    d = 7
    for r in k.get("dong") or []:
        if r.get("tu_tinh"):
            continue          # dòng tự cộng không có cửa nhập — rỗng vì dòng khác rỗng
        gia = [r.get("ten") or "", r.get("nhan_trang_thai") or "", r.get("nguyen_nhan") or "",
               r.get("bo_phan") or "chưa gán", r.get("nguon") or "chưa khai",
               (r.get("cua") or "chưa khai") + (" · cửa do đề xuất, chờ chốt"
                                                if r.get("cua_do_de_xuat") else ""),
               "chưa đặt"]
        for i, v in enumerate(gia, start=1):
            o = ws.cell(d, i, v)
            o.border = _khung
            o.alignment = Alignment(wrap_text=True, vertical="top")
            o.font = Font(size=10)
        ws.cell(d, 2).font = Font(size=10, bold=True,
                                  color={"con_thieu": DO, "chua_doi_soat": VANG,
                                         "day_du": XANH}.get(r.get("trang_thai"), "FF64798C"))
        d += 1

    o = ws.cell(d + 1, 1, "Cột “Hạn xử lý” chưa có nguồn: hệ thống chưa có bảng nào ghi hạn khắc "
                          "phục cho từng dòng dòng tiền, và cũng chưa có cửa nhập hạn. Đây là việc "
                          "còn thiếu, không phải ô để trống cho đẹp.")
    o.font = Font(size=9, italic=True, color="FF64798C")
    o.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=d + 1, start_column=1, end_row=d + 3, end_column=7)

    ws.row_dimensions[6].height = 28
    _rong_cot(ws, [30, 14, 42, 20, 40, 46, 12])
    ws.freeze_panes = ws.cell(7, 2)


def dung_tep(k: dict) -> bytes:
    """Dựng tệp Excel từ ĐÚNG gói mà màn hình đang đọc. Không chạm cơ sở dữ liệu."""
    if not k.get("xem_duoc"):
        raise ValueError(k.get("ly_do") or "Vai này không xem được khối dòng tiền")
    wb = Workbook()
    wb.remove(wb.active)          # bỏ trang trắng openpyxl tạo sẵn
    _trang_bang(wb, k, theo_khoang=False)
    _trang_bang(wb, k, theo_khoang=True)
    _trang_nguon(wb, k)
    b = BytesIO()
    wb.save(b)
    return b.getvalue()


def _khong_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt RỒI mới lọc, chứ không lọc thẳng.

    Lọc thẳng `[^A-Za-z0-9._-]` thì "Một Thành Viên" ra "Mt-Thnh-Vin" — chữ nào có dấu là mất luôn
    cả chữ cái. Người nhận tệp đọc tên ấy không đoán ra công ty nào. Bỏ dấu trước thì ra
    "Mot-Thanh-Vien", đọc được. Chữ đ không tự tách dấu theo NFD nên phải thay tay.
    """
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9._-]", "", s.replace(" ", "-"))


def ma_phap_nhan(k: dict) -> str:
    """Mã pháp nhân, ĐỌC ĐÚNG HÌNH DẠNG máy chủ trả về.

    LỖI ĐÃ GẶP TRÊN TRANG THẬT 14/9/2026 — điểm nối Excel trả 500 ngay lần đầu. Tệp này đoán
    `phap_nhan` là một chuỗi mã, nhưng máy chủ trả một ĐỐI TƯỢNG {id, ma, ten}. Nhét đối tượng ấy
    vào tên tệp ra chuỗi kiểu

        VTOS_dong_tien_{'id': 8, 'ma': 'BUFFALO', 'ten': 'Công ty Cổ phần Việt Nam Buffalotours'}_...

    — có dấu nháy, dấu ngoặc và chữ có dấu. Chuỗi ấy đi vào tiêu đề Content-Disposition, mà tiêu đề
    HTTP chỉ nhận latin-1, nên máy chủ ném lỗi và trả 500. Bài học: hình dạng dữ liệu của làn khác
    phải ĐO, đừng đoán — cùng một lỗi đoán mà cả chuỗi vòng này đã tránh được ở chỗ khác.

    Nhận cả ba hình dạng để không gãy lần nữa nếu làn kia đổi: đối tượng, chuỗi, hay thiếu hẳn.
    """
    pn = k.get("phap_nhan")
    if isinstance(pn, dict):
        ma = pn.get("ma") or pn.get("code") or pn.get("ten") or ""
    else:
        ma = str(pn or "")
    return _khong_dau(ma) or "VTOS"


def ten_phap_nhan(k: dict) -> str:
    """Tên đầy đủ để in lên đầu trang tính — tệp đi xa khỏi màn hình nên phải tự nói nó của ai."""
    pn = k.get("phap_nhan")
    if isinstance(pn, dict):
        return str(pn.get("ten") or pn.get("ma") or "")
    return str(pn or "")


def ten_tep(k: dict) -> str:
    """Tên tệp CHỈ gồm chữ cái không dấu, số và ba dấu nối.

    Không phải vì thẩm mỹ: tên tệp này đi thẳng vào tiêu đề Content-Disposition. Một chữ có dấu ở
    đây là một lỗi 500, và lỗi ấy chỉ lộ ra khi có người bấm nút.
    """
    return f"VTOS_dong_tien_{ma_phap_nhan(k)}_{date.today():%d-%m-%Y}.xlsx"


# Giữ tham chiếu để người đọc thấy ngay tệp này ăn khớp với đâu; cũng là chốt chặn khi ai đó đổi
# tên hằng bên kia mà quên bên này.
assert hasattr(KHUNG, "ghep"), "xuat_dong_tien_excel đọc gói do khung_dong_tien.ghep() dựng"
