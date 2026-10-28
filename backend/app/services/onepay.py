"""DT-2 · Cổng thẻ OnePay (Visa / Master / JCB) — chỉ phần ký và kiểm chữ ký, không giữ trạng thái.

Cách OnePay chạy (cổng quốc tế, giao thức vpc): VTOS ký một đường dẫn chứa số tiền + mã giao dịch → khách
sang trang của OnePay gõ thẻ → OnePay gọi lại đường trả về (trình duyệt) và đường IPN (máy chủ OnePay) với
kết quả có chữ ký. VTOS KHÔNG bao giờ thấy số thẻ.

Chữ ký: nối các tham số bắt đầu bằng `vpc_` / `user_` (bỏ vpc_SecureHash, vpc_SecureHashType, bỏ giá trị
rỗng) theo thứ tự tên tăng dần thành `k=v&k=v`, HMAC-SHA256 với khóa là chuỗi HEX OnePay cấp (giải HEX ra
byte), in HEX chữ hoa.

Ba khóa trong cấu hình máy chủ (Chủ tịch tự nhập sau khi ký hợp đồng). Thiếu một khóa = cổng thẻ TẮT.
"""
from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlencode

from app.core.config import settings

PHAN_HOI_IPN = "responsecode=1&desc=confirm-success"


def bat() -> bool:
    return bool(settings.ONEPAY_MERCHANT and settings.ONEPAY_ACCESS_CODE and settings.ONEPAY_HASH_KEY)


def _chuoi_ky(p: dict) -> str:
    keys = sorted(k for k, v in p.items() if (k.startswith("vpc_") or k.startswith("user_"))
                  and k not in ("vpc_SecureHash", "vpc_SecureHashType") and v not in (None, ""))
    return "&".join(f"{k}={p[k]}" for k in keys)


def ky(p: dict, khoa_hex: str | None = None) -> str:
    khoa = bytes.fromhex(khoa_hex if khoa_hex is not None else settings.ONEPAY_HASH_KEY)
    return hmac.new(khoa, _chuoi_ky(p).encode("utf-8"), hashlib.sha256).hexdigest().upper()


def kiem(p: dict, khoa_hex: str | None = None) -> bool:
    h = str(p.get("vpc_SecureHash") or "")
    if not h:
        return False
    try:
        return hmac.compare_digest(ky(p, khoa_hex), h.upper())
    except ValueError:
        return False


def duong_thanh_toan(ma_gd: str, so_tien: int, thong_tin: str, tra_ve: str, ip: str, quay_lai: str = "") -> str:
    """Đường dẫn sang trang thanh toán OnePay. `so_tien` là đồng; OnePay nhận ×100."""
    if not bat():
        raise ValueError("Cổng thẻ chưa bật")
    p = {"vpc_Version": "2", "vpc_Currency": "VND", "vpc_Command": "pay", "vpc_AccessCode": settings.ONEPAY_ACCESS_CODE,
         "vpc_Merchant": settings.ONEPAY_MERCHANT, "vpc_Locale": "vn", "vpc_ReturnURL": tra_ve, "vpc_MerchTxnRef": ma_gd,
         "vpc_OrderInfo": thong_tin[:32], "vpc_Amount": str(int(so_tien) * 100), "vpc_TicketNo": (ip or "127.0.0.1")[:45]}
    p["vpc_SecureHash"] = ky(p)
    q = {"AgainLink": quay_lai[:64] if quay_lai else "", "Title": "Vietourist", **p}
    return f"{settings.ONEPAY_URL}?{urlencode({k: v for k, v in q.items() if v})}"


def ket_qua(p: dict) -> dict:
    """Đọc kết quả OnePay gửi về. `hop_le` False = chữ ký sai → không tin bất cứ trường nào."""
    hop_le = kiem(p)
    try:
        tien = int(p.get("vpc_Amount") or 0) // 100
    except ValueError:
        tien = 0
    return {"hop_le": hop_le, "ma_gd": str(p.get("vpc_MerchTxnRef") or ""), "thanh_cong": hop_le and str(p.get("vpc_TxnResponseCode")) == "0",
            "ma_kq": str(p.get("vpc_TxnResponseCode") or ""), "so_gd": str(p.get("vpc_TransactionNo") or ""), "so_tien": tien}
