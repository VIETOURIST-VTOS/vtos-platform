"""SP-1 · SePay gọi về (IPN cổng thanh toán). Không phiên; xác thực bằng đầu đề X-Secret-Key = khóa IPN trong cấu hình.

Mã giao dịch (order_invoice_number) bắt đầu «KS» → đơn đặt phòng khách sạn VTD (KS-14); «TR» → đặt tour online (TR-1);
còn lại → đặt bàn (DT-2).
Sai khóa → 401, không đổi gì; mã lạ → 200 (để SePay thôi gọi lại) nhưng không ghi gì.
"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import dat_ban as DB
from app.services import don_ks_vtd as KV
from app.services import sepay_pg as SP

router = APIRouter(prefix="/api/v1/sepay-pg", tags=["sepay-pg"])

# Phanh như cửa OnePay: khóa sai thì không đổi gì, phanh chặn dội.
CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO = 600, 60
_LUOT: dict = defaultdict(list)


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    _LUOT[ip] = v


@router.post("/ipn")
async def ipn(request: Request, x_secret_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _phanh(request)
    if not SP.khoa_ipn_dung(x_secret_key):
        raise HTTPException(401, "Sai khóa IPN")
    try:
        p = await request.json()
    except Exception:
        raise HTTPException(400, "Thân IPN không phải JSON")
    kq = SP.doc_ipn(p if isinstance(p, dict) else {})
    if not kq["ma_gd"]:
        return {"success": True, "ghi": False}
    ma = kq["ma_gd"].upper()
    if ma.startswith("TR"):                               # TR-1: đặt tour online trên cổng khách
        from app.services import tour_online as TRO
        r = TRO.sepay_ket_qua(db, kq)
    else:
        r = (KV.sepay_ket_qua if ma.startswith("KS") else DB.sepay_ket_qua)(db, kq)
    return {"success": True, "ghi": r is not None}
