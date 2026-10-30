"""SP-1 · Cổng thanh toán SePay (Payment Gateway) — thẻ Visa / Mastercard / JCB, thẻ nội địa và QR NAPAS khi hợp
đồng SePay của Vietourist cho phép (Chủ tịch chốt 29/10/2026: SePay THAY OnePay cho thanh toán thẻ).

Cách chạy (theo tài liệu developer.sepay.vn › Cổng thanh toán, bản v1):
  1. VTOS dựng biểu mẫu POST tới https://pay.sepay.vn/v1/checkout/init (thử: pay-sandbox.sepay.vn) gồm số tiền, mã
     đơn (order_invoice_number), mô tả, ba đường quay về, và CHỮ KÝ: HMAC-SHA256 (khóa bí mật merchant) của chuỗi
     «trường=giá trị» nối bằng dấu phẩy, theo đúng thứ tự TRUONG_KY, bỏ trường không gửi; kết quả mã base64.
     Trình duyệt khách gửi biểu mẫu → trang thanh toán của SePay. Vietourist không thấy, không lưu số thẻ.
  2. SePay gọi IPN (POST JSON) về /api/v1/sepay-pg/ipn, kèm đầu đề X-Secret-Key = khóa IPN Vietourist đặt trong trang
     quản trị SePay (kiểu xác thực SECRET_KEY). Sai khóa → 401, không đổi gì. ORDER_PAID + APPROVED + đúng số tiền
     → khoản thanh toán «thành công» (Kế toán đối soát + ghi phí như thẻ OnePay).
  3. Đường success_url chỉ đưa khách về cổng — KHÔNG coi là đã trả (khách có thể đóng trình duyệt; kẻ gian có thể gõ
     tay đường này). Chỉ IPN có khóa đúng mới đổi trạng thái.

Bốn khóa trong cấu hình máy chủ (Chủ tịch tự nhập sau khi ký hợp đồng). Thiếu khóa nào = cổng TẮT:
  SEPAY_PG_MERCHANT_ID, SEPAY_PG_SECRET_KEY, SEPAY_PG_IPN_KEY; SEPAY_PG_ENV = sandbox | production.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

from app.core.config import settings

# Thứ tự ký theo tài liệu «Tạo form thanh toán»: trường không gửi thì bỏ, thứ tự còn lại giữ nguyên.
TRUONG_KY = ("order_amount", "merchant", "currency", "operation", "order_description", "order_invoice_number",
             "customer_id", "payment_method", "success_url", "error_url", "cancel_url")


def bat() -> bool:
    return bool(settings.SEPAY_PG_MERCHANT_ID and settings.SEPAY_PG_SECRET_KEY and settings.SEPAY_PG_IPN_KEY)


def goc_checkout() -> str:
    return "https://pay-sandbox.sepay.vn/v1/checkout" if (settings.SEPAY_PG_ENV or "").lower() == "sandbox" \
        else "https://pay.sepay.vn/v1/checkout"


def ky(truong: dict, khoa: str | None = None) -> str:
    chuoi = ",".join(f"{k}={truong[k]}" for k in TRUONG_KY if truong.get(k) not in (None, ""))
    so = hmac.new((khoa or settings.SEPAY_PG_SECRET_KEY).encode(), chuoi.encode(), hashlib.sha256).digest()
    return base64.b64encode(so).decode()


def bieu_mau(ma_gd: str, so_tien: int, mo_ta: str, ve_ok: str, ve_loi: str, ve_huy: str) -> dict:
    """{action, fields:[[tên, giá trị]…]} — trình duyệt dựng <form method=POST> theo đúng thứ tự này rồi gửi."""
    t = {"order_amount": str(int(so_tien)), "merchant": settings.SEPAY_PG_MERCHANT_ID, "currency": "VND",
         "operation": "PURCHASE", "order_description": mo_ta[:200], "order_invoice_number": ma_gd,
         "success_url": ve_ok, "error_url": ve_loi, "cancel_url": ve_huy}
    o = [[k, t[k]] for k in TRUONG_KY if t.get(k) not in (None, "")]
    o.append(["signature", ky(t)])
    return {"action": f"{goc_checkout()}/init", "fields": o}


def khoa_ipn_dung(x_secret_key: str | None) -> bool:
    k = settings.SEPAY_PG_IPN_KEY or ""
    return bool(k) and hmac.compare_digest((x_secret_key or "").encode(), k.encode())


def doc_ipn(p: dict) -> dict:
    """Rút gọn thông báo IPN. so_tien lấy từ giao dịch (transaction_amount), rơi về order_amount."""
    o, t = (p.get("order") or {}), (p.get("transaction") or {})
    try:
        so = int(round(float(t.get("transaction_amount") or o.get("order_amount") or 0)))
    except (TypeError, ValueError):
        so = -1
    loai = str(p.get("notification_type") or "")
    thanh_cong = (loai == "ORDER_PAID" and str(t.get("transaction_status") or "").upper() == "APPROVED"
                  and str(o.get("order_status") or "CAPTURED").upper() in ("CAPTURED", "PAID", "APPROVED")
                  and str(o.get("order_currency") or t.get("transaction_currency") or "VND").upper() == "VND")
    return {"ma_gd": str(o.get("order_invoice_number") or ""), "loai": loai, "thanh_cong": thanh_cong, "so_tien": so,
            "so_gd": str(t.get("transaction_id") or o.get("order_id") or "")[:40],
            "ma_kq": str(t.get("transaction_status") or loai)[:10], "cach": str(t.get("payment_method") or "")[:20],
            "the": " ".join(x for x in (str(t.get("card_brand") or ""), str(t.get("card_number") or "")[-4:]) if x)[:40]}


def cong_the_bat() -> bool:
    """Có cổng thẻ nào đang mở — SePay ưu tiên; OnePay chỉ còn khi SePay chưa có khóa."""
    from app.services import onepay as OP
    return bat() or OP.bat()
