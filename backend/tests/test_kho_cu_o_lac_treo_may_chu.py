# -*- coding: utf-8 -*-
"""MỘT Ô LẠC Ở HÀNG THỨ MỘT TRIỆU LÀM TREO MÁY CHỦ — đo trên bản chạy thật 16/9/2026.

Nạp cửa 1 cho 604 tệp kho cũ T1–T6 thì 47 tệp trả về HTTP 502 TRONG 0 GIÂY. Không phải lỗi mạng,
không phải tệp hỏng: mở "QUYẾT TOÁN VISA MỸ THÁNG 1.xlsx" (30 KB) ra thì thấy

    sheet 'MỸ VISA ONLY'   max_row = 1.048.525      (đúng trần của Excel)
    dữ liệu thật           hàng 1 → 40
    ĐÚNG MỘT Ô lạc         (1048525, 5) = 199.500.000

Một ô số tiền bị dán nhầm xuống hàng cuối cùng của sheet. Excel khai kích thước sheet theo ô xa
nhất, nên `ws.max_row` thành hơn một triệu. Bộ đọc duyệt `range(..., ws.max_row + 1)` và gọi
`ws.cell(r, c)` — mà `ws.cell()` TẠO RA ô nếu chưa có. Hơn một triệu lượt tạo đối tượng cho mỗi
cột: tiến trình treo, cổng web hết giờ chờ, 502.

CÁI GIÁ THẬT KHÔNG PHẢI 47 TỆP. Cửa nạp là cửa mở cho nhân viên Điều hành: một người tải lên đúng
một tệp như thế là TREO MỘT TIẾN TRÌNH của máy chủ, bất cứ ngày nào.

HAI PHÉP THỬ, VÀ PHÉP THỨ HAI MỚI LÀ PHÉP QUAN TRỌNG

  OL1  đọc xong trong vài giây, không treo
  OL2  ô lạc PHẢI được nói ra

OL2 tồn tại vì cách sửa dễ nhất là cắt vùng quét rồi thôi. Làm thế là đổi một lỗi TREO — ai cũng
thấy — lấy một lỗi THIẾU TIỀN, mà 199.500.000 biến mất thì không ai thấy. Bộ đọc này viết ra để
tránh đúng loại hỏng im lặng ấy.
"""
from __future__ import annotations

import time
from io import BytesIO

import openpyxl

from app.services import nap_kho_cu as K

HANG_LAC = 1048525
TIEN_LAC = 199500000


def _tep_co_o_lac() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MỸ VISA ONLY"
    ws.cell(1, 1, "Mã tour:"); ws.cell(1, 2, "MY001.01010126")
    ws.cell(2, 1, "Ngày đi:"); ws.cell(2, 2, "01/01/2026")
    ws.cell(4, 1, "STT"); ws.cell(4, 2, "TÊN KHÁCH HÀNG"); ws.cell(4, 3, "TỔNG THU")
    for i in range(5, 35):
        ws.cell(i, 1, i - 4); ws.cell(i, 2, f"KHACH {i - 4}"); ws.cell(i, 3, 1000000)
    # Ô lạc – đúng chỗ đã làm treo bản chạy thật.
    ws.cell(HANG_LAC, 5, TIEN_LAC)
    b = BytesIO()
    wb.save(b)
    return b.getvalue()


def test_ol1_khong_treo_khi_sheet_khai_mot_trieu_hang():
    """Đọc phải xong nhanh. Bản chưa vá chạy quá 120 giây rồi bị giết, không ra kết quả."""
    noi_dung = _tep_co_o_lac()
    t = time.time()
    d = K.doc_tep(noi_dung, "co-o-lac.xlsx")
    giay = time.time() - t
    assert giay < 20, (
        f"đọc mất {giay:.0f} giây – bộ đọc vẫn đang quét tới ws.max_row ({HANG_LAC:,}). "
        "Trên máy chủ thì đây là 502 và một tiến trình bị treo.")
    assert len(d["khach"]) == 30, "cắt vùng quét không được cắt mất dữ liệu thật"


def test_ol2_o_lac_phai_duoc_noi_ra_chu_khong_im_lang_bo_qua():
    """Cắt vùng quét mà im lặng là đổi lỗi treo lấy lỗi thiếu tiền. Lỗi thiếu tiền không ai thấy."""
    d = K.doc_tep(_tep_co_o_lac(), "co-o-lac.xlsx")
    lac = d.get("o_lac") or []
    assert lac, ("ô mang 199.500.000 bị bỏ ngoài vùng quét mà bộ đọc không nói gì – "
                 "đúng kiểu hỏng im lặng mà bộ đọc này viết ra để tránh")
    t = " ".join(lac)
    assert str(TIEN_LAC) in t or f"{TIEN_LAC:,}" in t, "phải nói RA con số bị bỏ, không nói chung chung"
    assert "1,048,525" in t or str(HANG_LAC) in t, "phải nói ô ấy nằm ở hàng nào"
    assert any(x in " ".join(d["thieu"]) for x in (str(TIEN_LAC), f"{TIEN_LAC:,}")), (
        "ô lạc phải đi vào phần `thieu` – đó là chỗ người duyệt thực sự đọc")
