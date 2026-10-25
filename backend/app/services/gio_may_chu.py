# -*- coding: utf-8 -*-
"""ĐỢT KS-18 — máy chủ đang đứng ở múi giờ nào, và có đúng múi đã khai không.

VÌ SAO CÓ TỆP NÀY. `render.yaml` khai `TZ: Asia/Ho_Chi_Minh`. Nhưng ảnh nền của máy chủ là
`python:3.12-slim`, và ảnh `slim` của Debian KHÔNG mang theo gói `tzdata` — tức không có thư mục
`/usr/share/zoneinfo`. Thiếu tệp ấy thì thư viện C KHÔNG báo lỗi: nó đọc chuỗi `Asia/Ho_Chi_Minh`
như một tên múi giờ POSIX và hiểu thành lệch 0 giờ, tức UTC.

TÁI HIỆN ĐƯỢC, 21/10/2026 (chạy đúng một máy, chỉ khác chỗ có hay không có `zoneinfo`):

    có  tzdata : datetime.now() = 2026-10-22 00:23   ·  time.tzname = ('+07', '+07')
    KHÔNG      : datetime.now() = 2026-10-21 17:23   ·  time.tzname = ('Asia', 'Asia')

`time.tzname` ra `('Asia','Asia')` chính là dấu vết của cú đọc nhầm ấy: thư viện C cắt chuỗi ở dấu
gạch chéo và coi `Asia` là tên múi, lệch 0.

HẬU QUẢ: mỗi ngày từ 00 giờ tới 07 giờ Việt Nam, MỌI chữ "hôm nay" trong VTOS lùi lại một ngày —
công suất khai thác tính tới hôm nay, ngày công, hạn ba ngày làm việc của sự vụ, khung giờ làm
việc của trợ lý AI. Sai lặng lẽ: không có lỗi nào được ghi ra.

Cửa `/he-thong/gio-may-chu` để Chủ tịch TỰ MỞ RA XEM trên hệ thật, không phải tin lời ai.
"""
from __future__ import annotations

import datetime
import time

LECH_MONG_DOI_PHUT = 7 * 60      # Asia/Ho_Chi_Minh: +07:00, không đổi theo mùa


def lech_phut_hien_tai() -> int:
    """Chênh lệch giờ máy so với UTC, tính bằng phút. Đọc từ chính đồng hồ máy, không suy từ tên."""
    bay_gio = datetime.datetime.now()
    return round((bay_gio - datetime.datetime.utcnow()).total_seconds() / 60)


def soat(tz_da_khai: str = "Asia/Ho_Chi_Minh", lech_mong_doi: int = LECH_MONG_DOI_PHUT) -> dict:
    """Máy chủ có đang chạy đúng múi giờ đã khai không. CHỈ ĐỌC, không chạm cơ sở dữ liệu."""
    lech = lech_phut_hien_tai()
    dung = lech == lech_mong_doi
    ten = list(time.tzname)
    # Dấu vết của cú đọc nhầm: tên múi là đoạn đầu của chuỗi TZ (`Asia`) chứ không phải `+07`.
    doc_nham = (not dung) and bool(ten) and tz_da_khai.split("/")[0] in ten
    if dung:
        vi_sao = ""
    elif doc_nham:
        vi_sao = (f"Máy chủ đọc `TZ={tz_da_khai}` thành tên múi `{ten[0]}` lệch 0 giờ — dấu hiệu "
                  f"ảnh máy chủ THIẾU gói `tzdata`. Cài `tzdata` vào ảnh là hết.")
    else:
        vi_sao = (f"Máy chủ lệch {lech} phút so với UTC, trong khi `{tz_da_khai}` phải là "
                  f"{lech_mong_doi} phút.")
    return {
        "tz_da_khai": tz_da_khai,
        "lech_mong_doi_phut": lech_mong_doi,
        "lech_thuc_te_phut": lech,
        "ten_mui_may_doc_duoc": ten,
        "gio_may": datetime.datetime.now().isoformat(timespec="seconds"),
        "gio_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "hom_nay_theo_may": datetime.date.today().isoformat(),
        "dung_gio": dung,
        "vi_sao": vi_sao,
        "anh_huong": "" if dung else (
            "Mọi chữ «hôm nay» trong hệ thống đang lệch: công suất khai thác tính tới hôm nay, "
            "ngày công, hạn ba ngày làm việc của sự vụ, khung giờ làm việc của trợ lý AI."),
    }
