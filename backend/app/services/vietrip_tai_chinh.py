# -*- coding: utf-8 -*-
"""BỘ GỌI HAI CỬA TÀI CHÍNH CỦA VIETRIP — JSON chính thức, CHỈ ĐỌC (05/11/2026).

    GET /api/finance-data/receipts      phiếu thu khách
    GET /api/finance-data/receivables   công nợ phải thu theo booking

VÌ SAO CÓ TỆP NÀY, VÀ NÓ THAY CÁI GÌ. VTOS đang lấy hai bộ số ấy theo hai đường đều yếu:

  · CÔNG NỢ PHẢI THU — NẠP TAY mỗi sáng (`POST /cong-no-vietrip/nap`). Người quên một ngày là
    màn Chủ tịch hôm ấy nói số của hôm trước, và không gì báo.
  · PHIẾU THU — `vietrip_client.py` ĐĂNG NHẬP BẰNG SỐ ĐIỆN THOẠI + MẬT KHẨU rồi ĐỌC HTML. Một
    lần Vietrip đổi bố cục trang là bộ đọc gãy; đổi mật khẩu cũng gãy. Đã gãy nhiều lần thật.

Khoá API không có hai bệnh ấy. Tệp này CHỈ gọi và trả về nguyên văn — KHÔNG ghi vào cơ sở dữ
liệu. Việc ghi sổ là vòng sau, và nó cần một luật riêng (xem GỠ KHỎI SỔ ở cuối).

KHOÁ KHÔNG BAO GIỜ NẰM TRONG MÃ NGUỒN. Đọc từ biến môi trường `VIETRIP_FINANCE_KEY`, đặt trên
Render. Mã chỉ biết TÊN biến, không biết giá trị.

VÀ KHOÁ KHÔNG BAO GIỜ ĐI RA NGOÀI. Mọi lời báo lỗi ở đây đều dựng bằng tay từ mã HTTP và một
câu tiếng Việt. KHÔNG bao giờ ném nguyên `URLError`/`HTTPError` ra ngoài, vì thư viện có thể
kèm cả tiêu đề yêu cầu — tức cả khoá — vào chuỗi lỗi, và chuỗi lỗi thì đi thẳng vào nhật ký
máy chủ, nơi nhiều người đọc được. `vt1_5` canh đúng chỗ này.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

GOC = "https://app.vietrip.com.vn/api/finance-data"
TEN_BIEN = "VIETRIP_FINANCE_KEY"
CUA = ("receipts", "receivables")

# Vietrip giới hạn 60 lần gọi / phút / IP. Hạn chờ 60 giây cho một trang 500–2000 dòng.
HAN_CHO = 60


class ChuaCoKhoa(RuntimeError):
    """Chưa đặt biến môi trường. KHÔNG phải lỗi mạng — và hai thứ ấy sửa khác nhau."""


class LoiGoi(RuntimeError):
    """Gọi được nhưng Vietrip không trả 200. Mang theo mã HTTP để nói đúng việc phải làm."""

    def __init__(self, ma: int, cua: str):
        self.ma, self.cua = ma, cua
        super().__init__(f"Vietrip trả mã {ma} ở cửa /{cua}: {giai_thich(ma)}")


def giai_thich(ma: int) -> str:
    return {
        401: "khoá sai hoặc thiếu — soát lại biến môi trường trên Render",
        403: "khoá không được phép gọi cửa này — hỏi lại bên Vietrip",
        429: "gọi quá nhanh, Vietrip chặn 1 phút — giãn nhịp rồi gọi lại",
        500: "lỗi máy chủ Vietrip, không phải lỗi VTOS — báo bên Vietrip",
    }.get(ma, f"mã lạ {ma}, chưa có trong tài liệu")


def co_khoa() -> bool:
    """Có khoá hay chưa — KHÔNG trả về khoá, và không ai gọi hàm này để lấy khoá."""
    return bool((os.getenv(TEN_BIEN) or "").strip())


def _khoa() -> str:
    k = (os.getenv(TEN_BIEN) or "").strip()
    if not k:
        raise ChuaCoKhoa(
            f"Chưa đặt {TEN_BIEN} trên máy chủ. Vào Render → vtos-api → Environment, thêm biến "
            f"ấy rồi dựng lại. Khoá KHÔNG đặt trong mã nguồn.")
    return k


def goi(cua: str, **loc) -> dict:
    """Gọi MỘT trang. `cua` là 'receipts' hoặc 'receivables'; `loc` là tham số lọc.

    Tham số rỗng hoặc None bị BỎ chứ không gửi đi: gửi `status=` rỗng là một bộ lọc khác hẳn
    với không gửi gì, và tài liệu nói rõ không truyền gì thì trả tất cả.
    """
    if cua not in CUA:
        raise ValueError(f"cửa lạ: {cua} — chỉ có {', '.join(CUA)}")
    tham_so = {k: str(v) for k, v in loc.items() if v not in (None, "")}
    duong = f"{GOC}/{cua}" + (f"?{urllib.parse.urlencode(tham_so)}" if tham_so else "")
    yeu_cau = urllib.request.Request(duong, headers={"X-VieTrip-Key": _khoa(),
                                                     "Accept": "application/json"})
    try:
        with urllib.request.urlopen(yeu_cau, timeout=HAN_CHO) as tra:
            return json.loads(tra.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LoiGoi(e.code, cua) from None          # `from None`: cắt chuỗi gốc, xem đầu tệp
    except urllib.error.URLError:
        raise LoiGoi(0, cua) from None
    except json.JSONDecodeError:
        raise LoiGoi(-1, cua) from None


def thu_ket_noi(cua: str = "receivables") -> dict:
    """Một lần gọi NHẸ NHẤT có thể (`pageSize=1`) để người thật tự xem đường có thông không.

    Trả về thứ ĐỌC ĐƯỢC BẰNG MẮT, không trả dòng dữ liệu nào: có khoá chưa, Vietrip trả gì,
    tổng bao nhiêu dòng, số liệu chụp lúc nào. Con số do máy báo chưa phải là đã nghiệm thu —
    cửa này để Chủ tịch TỰ MỞ RA XEM trên hệ thật, cùng cách `/he-thong/gio-may-chu` đã làm.
    """
    if not co_khoa():
        return {"thong": False, "co_khoa": False,
                "noi": f"Chưa đặt {TEN_BIEN} trên máy chủ — chưa gọi Vietrip lần nào."}
    try:
        d = goi(cua, pageSize=1)
    except LoiGoi as e:
        return {"thong": False, "co_khoa": True, "cua": cua, "ma_http": e.ma,
                "noi": f"Gọi được tới Vietrip nhưng {giai_thich(e.ma)}."
                       if e.ma > 0 else "Không nối được tới máy chủ Vietrip (mạng hoặc tên miền)."}
    return {"thong": True, "co_khoa": True, "cua": cua,
            "tong_dong": d.get("total"), "chup_luc": d.get("generatedAt"),
            "so_dong_tra_ve": len(d.get("data") or []),
            "noi": f"Đường thông. Vietrip đang có {d.get('total')} dòng ở cửa /{cua}, "
                   f"số liệu chụp lúc {d.get('generatedAt')}."}
