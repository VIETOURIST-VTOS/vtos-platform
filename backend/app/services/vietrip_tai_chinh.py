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
liệu. Việc ghi sổ là vòng sau, và nó cần một luật riêng (phiếu huỷ thì PHẢI GỠ KHỎI SỔ).

KHOÁ KHÔNG BAO GIỜ NẰM TRONG MÃ NGUỒN. Đọc từ biến môi trường `VIETRIP_FINANCE_KEY`, đặt trên
Render. Mã chỉ biết TÊN biến, không biết giá trị.

VÀ KHOÁ KHÔNG ĐƯỢC ĐI RA NGOÀI — VÒNG VT-2 SIẾT LẠI SAU MỘT LẦN RÒ THẬT (05/11/2026).
Bản VT-1 bắt BA loại lỗi đã biết (`HTTPError`, `URLError`, `JSONDecodeError`) rồi dựng câu báo
bằng tay. Hôm ấy biến môi trường bị dán nhầm CẢ CÂU LỆNH `curl` chép từ tài liệu PDF — dính
luôn hai dấu xuống dòng của chỗ ngắt trang — nên `http.client` ném

    ValueError: Invalid header value b'curl -H "X-VieTrip-Key:<KHOÁ>"\\n"https://..."'

KÈM NGUYÊN GIÁ TRỊ TIÊU ĐỀ, tức kèm nguyên khoá. `ValueError` không nằm trong ba loại trên nên
nó đi thẳng ra nhật ký Render, và khoá nằm đó nguyên văn, nhiều lần, cho đến khi người ta đọc
nhật ký mới biết.

BÀI HỌC: liệt kê các loại lỗi cần chặn là không đủ. Chặn rò rỉ phải là MẶC ĐỊNH, không phải
danh sách. Ba chốt của vòng VT-2:

  1. `goi()` có LƯỚI CUỐI bắt mọi `Exception` và chỉ giữ TÊN LOẠI lỗi, không giữ lời lỗi.
  2. `soat_khoa()` chặn ngay từ lúc đọc biến: khoảng trắng, xuống dòng, dấu nháy, `curl`, địa
     chỉ, dấu hai chấm — từ chối, và lời từ chối KHÔNG in giá trị.
  3. `thu_ket_noi()` KHÔNG BAO GIỜ ném lỗi. Một cửa chẩn đoán mà trả 500 là cửa im lặng đúng
     lúc cần nói nhất — và 500 nào cũng kéo theo một chuỗi lỗi vào nhật ký.
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

CHUA_DAT = "chưa được đặt"

# Câu chỉ đường, dùng lại ở nhiều chỗ để chỉ sửa một nơi.
CACH_SUA = ("Vào Render → vtos-api → Environment, xoá sạch ô giá trị rồi dán lại ĐÚNG chuỗi "
            "khoá — không `curl`, không dấu nháy, không địa chỉ, không xuống dòng.")


class ChuaCoKhoa(RuntimeError):
    """Chưa đặt biến môi trường. KHÔNG phải lỗi mạng — và hai thứ ấy sửa khác nhau."""


class KhoaDangSai(RuntimeError):
    """Biến CÓ đặt nhưng giá trị không phải một chuỗi khoá. Cũng không phải lỗi mạng, và cũng
    không phải khoá sai — sửa ở ô giá trị trên Render, không phải đi hỏi Vietrip."""


class LoiGoi(RuntimeError):
    """Gọi được nhưng không ra JSON tử tế. Mang theo mã HTTP để nói đúng việc phải làm."""

    def __init__(self, ma: int, cua: str, loai: str = ""):
        self.ma, self.cua, self.loai = ma, cua, loai
        super().__init__(f"Vietrip trả mã {ma} ở cửa /{cua}: {giai_thich(ma, loai)}")


def giai_thich(ma: int, loai: str = "") -> str:
    if ma == 0:
        return "không nối được tới máy chủ Vietrip (mạng hoặc tên miền)"
    if ma == -1:
        return "Vietrip trả về thứ không phải JSON"
    if ma == -2:
        return (f"lỗi lạ chưa lường trước ({loai or 'không rõ loại'}) — lời lỗi gốc bị cắt bỏ "
                f"vì nó có thể mang theo khoá")
    return {
        401: "khoá sai hoặc thiếu — soát lại biến môi trường trên Render",
        403: "khoá không được phép gọi cửa này — hỏi lại bên Vietrip",
        429: "gọi quá nhanh, Vietrip chặn 1 phút — giãn nhịp rồi gọi lại",
        500: "lỗi máy chủ Vietrip, không phải lỗi VTOS — báo bên Vietrip",
    }.get(ma, f"mã lạ {ma}, chưa có trong tài liệu")


def soat_khoa() -> str:
    """Soát GIÁ TRỊ biến môi trường. Trả về LÝ DO từ chối, hoặc chuỗi rỗng nếu dùng được.

    KHÔNG BAO GIỜ trả về, in ra, hay ghép giá trị vào lý do — lý do này đi vào nhật ký máy chủ
    và vào cửa `thu-ket-noi`. Người đọc cần biết SAI CHỖ NÀO, không cần nhìn lại khoá của
    chính mình. Độ dài thì nói được: nó phân biệt ngay «dán cả câu lệnh» với «dán đúng khoá».

    Mỗi dấu hiệu dưới đây hoặc đã xảy ra thật, hoặc đứng ngay cạnh cái đã xảy ra thật. Khoá
    Vietrip là chữ và số và gạch dưới; nếu mai kia Vietrip đổi sang khuôn có dấu hai chấm hay
    chữ `http` thì phép thử `vt2_5` sẽ đỏ và chỗ này phải nới ra — cố ý để nó đỏ.
    """
    k = (os.getenv(TEN_BIEN) or "").strip()
    if not k:
        return CHUA_DAT
    n = len(k)
    if any(c.isspace() for c in k):
        return f"đang chứa khoảng trắng hoặc dấu xuống dòng ở giữa (dài {n} ký tự)"
    if '"' in k or "'" in k:
        return f"đang chứa dấu nháy (dài {n} ký tự)"
    if "curl" in k.lower() or "http" in k.lower():
        return f"đang chứa cả câu lệnh hoặc địa chỉ chứ không phải chỉ khoá (dài {n} ký tự)"
    if ":" in k:
        return f"đang chứa dấu hai chấm — có vẻ dán kèm cả tên tiêu đề (dài {n} ký tự)"
    return ""


def co_khoa() -> bool:
    """Có khoá hay chưa — KHÔNG trả về khoá, và không ai gọi hàm này để lấy khoá."""
    return bool((os.getenv(TEN_BIEN) or "").strip())


def _khoa() -> str:
    ly_do = soat_khoa()
    if ly_do == CHUA_DAT:
        raise ChuaCoKhoa(
            f"Chưa đặt {TEN_BIEN} trên máy chủ. Vào Render → vtos-api → Environment, thêm biến "
            f"ấy rồi dựng lại. Khoá KHÔNG đặt trong mã nguồn.")
    if ly_do:
        raise KhoaDangSai(f"{TEN_BIEN} trên máy chủ {ly_do}. {CACH_SUA}")
    return (os.getenv(TEN_BIEN) or "").strip()


def goi(cua: str, **loc) -> dict:
    """Gọi MỘT trang. `cua` là 'receipts' hoặc 'receivables'; `loc` là tham số lọc.

    Tham số rỗng hoặc None bị BỎ chứ không gửi đi: gửi `status=` rỗng là một bộ lọc khác hẳn
    với không gửi gì, và tài liệu nói rõ không truyền gì thì trả tất cả.
    """
    if cua not in CUA:
        raise ValueError(f"cửa lạ: {cua} — chỉ có {', '.join(CUA)}")
    tham_so = {k: str(v) for k, v in loc.items() if v not in (None, "")}
    duong = f"{GOC}/{cua}" + (f"?{urllib.parse.urlencode(tham_so)}" if tham_so else "")
    khoa = _khoa()                               # ngoài `try`: lỗi khoá KHÔNG phải lỗi gọi
    try:
        yeu_cau = urllib.request.Request(duong, headers={"X-VieTrip-Key": khoa,
                                                         "Accept": "application/json"})
        with urllib.request.urlopen(yeu_cau, timeout=HAN_CHO) as tra:
            return json.loads(tra.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LoiGoi(e.code, cua) from None      # `from None`: cắt chuỗi gốc, xem đầu tệp
    except urllib.error.URLError:
        raise LoiGoi(0, cua) from None
    except json.JSONDecodeError:
        raise LoiGoi(-1, cua) from None
    except Exception as e:
        # LƯỚI CUỐI. Giữ ĐÚNG TÊN LOẠI lỗi (an toàn, và đủ để lần ra chỗ hỏng); vứt bỏ lời lỗi
        # vì chính lời lỗi là thứ đã mang khoá ra nhật ký ngày 05/11/2026.
        raise LoiGoi(-2, cua, type(e).__name__) from None


def thu_ket_noi(cua: str = "receivables") -> dict:
    """Một lần gọi NHẸ NHẤT có thể (`pageSize=1`) để người thật tự xem đường có thông không.

    Trả về thứ ĐỌC ĐƯỢC BẰNG MẮT, không trả dòng dữ liệu nào: có khoá chưa, khoá có dùng được
    không, Vietrip trả gì, tổng bao nhiêu dòng, số liệu chụp lúc nào. Con số do máy báo chưa
    phải là đã nghiệm thu — cửa này để Chủ tịch TỰ MỞ RA XEM trên hệ thật.

    HÀM NÀY KHÔNG BAO GIỜ ĐƯỢC NÉM LỖI. Ném lỗi là trả 500, mà 500 thì vừa im lặng đúng lúc
    cần nói, vừa kéo một chuỗi lỗi vào nhật ký — đúng hai chuyện vòng VT-2 sinh ra để chặn.
    """
    ly_do = soat_khoa()
    if ly_do == CHUA_DAT:
        return {"thong": False, "co_khoa": False, "khoa_dung_duoc": False,
                "noi": f"Chưa đặt {TEN_BIEN} trên máy chủ — chưa gọi Vietrip lần nào."}
    if ly_do:
        return {"thong": False, "co_khoa": True, "khoa_dung_duoc": False,
                "noi": f"{TEN_BIEN} trên máy chủ {ly_do}. {CACH_SUA}"}
    try:
        d = goi(cua, pageSize=1)
        tra = {"thong": True, "co_khoa": True, "khoa_dung_duoc": True, "cua": cua,
               "tong_dong": d.get("total"), "chup_luc": d.get("generatedAt"),
               "so_dong_tra_ve": len(d.get("data") or []),
               "noi": f"Đường thông. Vietrip đang có {d.get('total')} dòng ở cửa /{cua}, "
                      f"số liệu chụp lúc {d.get('generatedAt')}."}
    except LoiGoi as e:
        return {"thong": False, "co_khoa": True, "khoa_dung_duoc": True, "cua": cua,
                "ma_http": e.ma,
                "noi": (f"Gọi được tới Vietrip nhưng {giai_thich(e.ma, e.loai)}."
                        if e.ma > 0 else
                        f"Chưa nói chuyện được với Vietrip: {giai_thich(e.ma, e.loai)}.")}
    except Exception as e:
        # LƯỚI CUỐI của cửa. Kể cả chỗ dựng câu trả lời ở trên cũng nằm trong này — Vietrip đổi
        # khuôn JSON (trả mảng thay vì đối tượng) là `.get` nổ, và nổ ở đây thì thành 500.
        return {"thong": False, "co_khoa": True, "khoa_dung_duoc": True, "cua": cua,
                "loai_loi": type(e).__name__,
                "noi": f"Lỗi lạ chưa lường trước khi gọi Vietrip ({type(e).__name__}). Lời lỗi "
                       f"gốc bị cắt bỏ vì nó có thể mang theo khoá — đọc mã, đừng đợi nhật ký."}
    return tra
