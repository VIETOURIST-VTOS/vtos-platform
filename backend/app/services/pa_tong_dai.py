"""Tổng đài P.A Việt Nam – đọc lịch sử cuộc gọi và ghi âm.

Đặc tả lấy từ chính trang quản trị (Người phát triển → Kiểm thử API), không phải đoán:

  POST /api/getCDRReport.php   api_key, from_date, to_date (y-m-d), limit (≤1000), page,
                               source, destination, duration_min, duration_max,
                               status = answered | not_answer | busy
      → {"code":"1000","message":"Successful","data":[{date_create, from, to, duration, bill, recording}]}
  POST /api/playRecording.php  api_key, recording_file  (giá trị lấy từ trường `recording` của CDR)
  POST /api/callNow.php        api_key, extension, phone

Ba điều tệp này giữ:

  1. KHOÁ Ở MÁY CHỦ, không đi qua trình duyệt. Trang kiểm thử của P.A điền sẵn khoá vào ô trên web;
     tiện cho một lần thử, nhưng khoá nào đã đi qua trình duyệt thì coi như đã lộ.

  2. HÀM ĐO CHỈ TRẢ VỀ SỐ TỔNG HỢP. Lịch sử cuộc gọi là danh sách số điện thoại khách hàng; câu hỏi
     "một tháng gọi bao nhiêu phút" không cần biết số của ai, nên nó không trả ra số nào cả. Đưa cả
     danh sách ra màn hình chỉ vì tiện là cách một phép đo biến thành một kho dữ liệu cá nhân.

  3. NÓI RÕ KHI ĐO THIẾU. Có trần số trang; chạm trần thì kết quả kèm cờ `cham_tran`. Một con số tổng
     thiếu mà không ai biết là thiếu còn tệ hơn không có con số nào.
"""
import os, json, urllib.request, urllib.parse
from datetime import date, datetime, timedelta

GOC = "https://crm.pavietnam.vn/api"
CDR = f"{GOC}/getCDRReport.php"
GHI_AM = f"{GOC}/playRecording.php"
GOI_NGAY = f"{GOC}/callNow.php"

TRAN_MOI_TRANG = 1000        # P.A giới hạn cứng
TRAN_SO_TRANG = 20           # 20.000 bản ghi cho một lần đo; đủ cho một tháng của hai đầu số
CHO_GIAY = 25

# Bảng mã lỗi của P.A, chép từ trang đặc tả. Dịch ra tiếng Việt vì người đọc cảnh báo là nhân viên
# vận hành, không phải người viết mã.
MA_LOI = {
    "1000": "", "1001": "Chưa khởi tạo được API – liên hệ P.A Việt Nam",
    "1002": "Thiếu tham số", "1003": "Tham số không hợp lệ",
    "1004": "Không được phép thực hiện – kiểm tra khoá API và quyền của tài khoản tổng đài",
    "1005": "Không tìm thấy bản ghi nào", "1006": "P.A chặn vì nghi tấn công",
    "1007": "Tổng đài trả lời quá chậm",
}


def khoa() -> str:
    return (os.getenv("PA_TONG_DAI_API_KEY") or "").strip()


def da_khai() -> bool:
    return bool(khoa())


def _goi(url: str, tham_so: dict) -> dict:
    """Gọi một API của P.A. KHÔNG ghi khoá vào bất kỳ thông báo lỗi nào."""
    k = khoa()
    if not k:
        raise ValueError("Chưa khai PA_TONG_DAI_API_KEY trên máy chủ")
    du_lieu = urllib.parse.urlencode({**tham_so, "api_key": k}).encode()
    req = urllib.request.Request(url, data=du_lieu, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=CHO_GIAY) as r:
        tho = r.read().decode("utf-8", "replace")
    try:
        j = json.loads(tho)
    except Exception:
        raise ValueError(f"Tổng đài trả về thứ không phải JSON: {tho[:160]}")
    ma = str(j.get("code", ""))
    if ma and ma != "1000":
        raise ValueError(MA_LOI.get(ma) or f"Tổng đài báo lỗi {ma}: {str(j.get('message'))[:120]}")
    return j


def _giay(v) -> int:
    try: return int(float(v or 0))
    except Exception: return 0


def lich_su(tu: str, den: str, trang: int = 1, moi_trang: int = TRAN_MOI_TRANG) -> list[dict]:
    """Một trang lịch sử cuộc gọi. Trả về đúng những gì P.A trả, chưa diễn giải."""
    j = _goi(CDR, {"from_date": tu, "to_date": den,
                   "limit": min(int(moi_trang), TRAN_MOI_TRANG), "page": int(trang)})
    ds = j.get("data") or []
    return ds if isinstance(ds, list) else []


def do_khoi_luong(tu: str, den: str, tran_trang: int = TRAN_SO_TRANG) -> dict:
    """CÂU HỎI DUY NHẤT: khoảng này gọi bao nhiêu cuộc, bao nhiêu phút, bao nhiêu cuộc có ghi âm?

    Đây là con số để quyết có làm chuyển giọng nói thành văn bản hay không, và tốn bao nhiêu một
    tháng. Nó KHÔNG trả về số điện thoại nào – xem ghi chú đầu tệp.
    """
    tong = giay = co_ghi_am = giay_ghi_am = 0
    theo_trang_thai: dict[str, int] = {}
    theo_ngay: dict[str, int] = {}
    trang, cham_tran = 1, False
    while trang <= tran_trang:
        ds = lich_su(tu, den, trang)
        if not ds: break
        for x in ds:
            tong += 1
            g = _giay(x.get("duration"))
            giay += g
            tt = str(x.get("status") or x.get("disposition") or "?")
            theo_trang_thai[tt] = theo_trang_thai.get(tt, 0) + 1
            d = str(x.get("date_create") or "")[:10]
            if d: theo_ngay[d] = theo_ngay.get(d, 0) + 1
            if x.get("recording"):
                co_ghi_am += 1; giay_ghi_am += g
        if len(ds) < TRAN_MOI_TRANG: break
        trang += 1
    else:
        cham_tran = True
    return {
        "tu": tu, "den": den, "so_cuoc": tong,
        "tong_phut": round(giay / 60, 1),
        "phut_trung_binh": round(giay / 60 / tong, 2) if tong else 0,
        "so_cuoc_co_ghi_am": co_ghi_am,
        "phut_co_ghi_am": round(giay_ghi_am / 60, 1),
        "theo_trang_thai": theo_trang_thai,
        "so_ngay_co_cuoc": len(theo_ngay),
        "so_trang_da_doc": trang,
        # Chạm trần thì con số dưới đây là SÀN, không phải tổng. Nói ra, vì một con số thiếu mà không
        # ai biết là thiếu thì tệ hơn không có con số nào.
        "cham_tran": cham_tran,
    }


def uoc_chi_phi_chuyen_chu(phut: float) -> dict:
    """Ước chi phí chuyển giọng nói thành văn bản theo SỐ PHÚT ĐO ĐƯỢC.

    Đơn giá là giá công bố tháng 9/2026 của OpenAI, ghi thẳng ra đây kèm ngày để lần sau ai đọc cũng
    biết con số này cũ tới đâu. Nhà cung cấp trong nước (FPT.AI, Viettel AI) báo giá theo hợp đồng nên
    không đưa vào đây được – phải xin báo giá rồi thay số.
    """
    don_gia = {"gpt-4o-mini-transcribe": 0.003, "whisper-1 / gpt-4o-transcribe": 0.006}
    return {"phut": phut, "ngay_bang_gia": "2026-09",
            "usd_moi_thang": {k: round(phut * v, 2) for k, v in don_gia.items()},
            "ghi_chu": "Đơn giá USD/phút công bố của OpenAI. Chưa gồm nhà cung cấp trong nước."}
