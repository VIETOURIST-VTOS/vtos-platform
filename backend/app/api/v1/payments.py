"""API thu tiền: webhook SePay + màn hình Kế toán."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.models.core import Booking, User
from app.models.payments import BankTransaction, Receipt
from app.services import payments as P
from app.services import access as AC
from app.services import pham_vi_phap_nhan as PV
from app.services import sepay as SP

router = APIRouter(prefix="/api/v1", tags=["thu-tien"])


def txn_out(t: BankTransaction, db: Session) -> dict:
    b = db.get(Booking, t.booking_id) if t.booking_id else None
    return {"id": t.id, "sepay_id": t.sepay_id, "gateway": t.gateway, "account_number": t.account_number, "transaction_date": t.transaction_date,
            "transfer_type": t.transfer_type, "amount": t.amount, "content": t.content, "reference_code": t.reference_code,
            "match_status": t.match_status, "match_note": t.match_note, "booking_id": t.booking_id, "booking_code": b.code if b else "",
            "received_at": t.received_at}


def receipt_out(r: Receipt, db: Session) -> dict:
    b = db.get(Booking, r.booking_id)
    return {"id": r.id, "code": r.code, "booking_id": r.booking_id, "booking_code": b.code if b else "", "customer_name": b.customer_name if b else "",
            "tour_code": b.tour.code if b and b.tour else "", "amount": r.amount, "method": r.method, "payer": r.payer, "note": r.note,
            "status": r.status, "created_by": r.created_by, "confirmed_by": r.confirmed_by, "created_at": r.created_at, "confirmed_at": r.confirmed_at}


# ---------- Webhook SePay ----------
@router.post("/sepay/webhook", status_code=201)
async def sepay_webhook(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """SePay gọi POST kèm header `Authorization: Apikey <SEPAY_WEBHOOK_KEY>`."""
    expected = f"Apikey {settings.SEPAY_WEBHOOK_KEY}"
    if not settings.SEPAY_WEBHOOK_KEY or authorization != expected:
        raise HTTPException(401, "Sai khóa webhook SePay")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(422, "Body không phải JSON")
    if not isinstance(payload, dict) or not (payload.get("id") or payload.get("sepay_id")):
        # SePay "Gửi thử" / ping không có id giao dịch → xác nhận kết nối, không ghi
        return {"success": True, "test": True, "note": "Kết nối OK – gói tin không có id giao dịch nên không ghi nhận"}
    try:
        txn, created = P.ingest_sepay(db, payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"success": True, "new": created, "match_status": txn.match_status, "note": txn.match_note}


# ---------- Kết nối API SePay (kéo) ----------
@router.get("/sepay/status")
def sepay_status(u: User = Depends(require_roles("ketoan", "cntt", "tgd", "chutich", "bks")), db: Session = Depends(get_db)):
    return SP.status(db)


class PullIn(BaseModel):
    from_date: str | None = None   # YYYY-MM-DD
    to_date: str | None = None
    account_number: str = ""


@router.post("/sepay/pull")
def sepay_pull(data: PullIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    """Kéo giao dịch từ SePay User API vào VTOS (idempotent). Robot R1 đối chiếu như webhook."""
    from datetime import date as _d
    try:
        f = _d.fromisoformat(data.from_date) if data.from_date else None
        t = _d.fromisoformat(data.to_date) if data.to_date else None
        res = SP.pull(db, f, t, data.account_number or settings.SEPAY_ACCOUNT_NUMBER)
    except ValueError as e:
        raise HTTPException(422, f"Ngày không hợp lệ: {e}")
    except SP.SePayError as e:
        raise HTTPException(502, str(e))
    from app.services import rules as R
    R.audit(db, u.username, u.role, "sepay_keo_giao_dich", "sepay", after=res); db.commit()
    res["message"] = f"Đã kéo {res['fetched']} giao dịch, mới {res['new']} (khớp {res['matched']}, chờ Kế toán {res['pending']})"
    return res


@router.post("/robot/sepay/pull")
def robot_sepay_pull(data: PullIn, x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    """n8n gọi định kỳ (X-Robot-Token) để đối chiếu bù khi webhook lỗi."""
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    from datetime import date as _d, timedelta
    f = _d.fromisoformat(data.from_date) if data.from_date else _d.today() - timedelta(days=3)
    t = _d.fromisoformat(data.to_date) if data.to_date else _d.today()
    try:
        return SP.pull(db, f, t, data.account_number or settings.SEPAY_ACCOUNT_NUMBER)
    except SP.SePayError as e:
        raise HTTPException(502, str(e))


# ---------- Kế toán ----------
@router.get("/bank-transactions")
def list_txns(status: str | None = None, limit: int = 200, u: User = Depends(require_roles(*AC.FINANCE_ROLES, mo_ta="giao dịch ngân hàng")), db: Session = Depends(get_db)):
    q = select(BankTransaction).order_by(desc(BankTransaction.transaction_date))
    if status: q = q.where(BankTransaction.match_status.in_(status.split(",")))
    return [txn_out(t, db) for t in db.execute(q.limit(limit)).scalars()]


@router.post("/bank-transactions/rematch")
def rematch(u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    """Chạy lại robot R1 cho các giao dịch tiền vào đang chờ (sau khi nạp booking mới / cải tiến quy tắc khớp)."""
    n = m = 0
    for t in db.execute(select(BankTransaction).where(BankTransaction.transfer_type == "in", BankTransaction.match_status.in_(["cho_ke_toan", "chua_khop"]))).scalars():
        P.match_transaction(db, t); n += 1
        if t.match_status == "da_khop": m += 1
    from app.services import rules as R
    R.audit(db, u.username, u.role, "chay_lai_khop_giao_dich", "sepay", after={"xet": n, "khop": m}); db.commit()
    return {"checked": n, "matched": m, "message": f"Đã xét lại {n} giao dịch, khớp thêm {m}"}


@router.get("/bank-transactions/{tid}/raw")
def txn_raw(tid: int, u: User = Depends(require_roles("ketoan", "cntt", "bks")), db: Session = Depends(get_db)):
    """Gói tin gốc SePay của giao dịch (đối chiếu/kiểm toán)."""
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    return {"id": t.id, "sepay_id": t.sepay_id, "raw": t.raw}


class AssignIn(BaseModel):
    booking_id: int
    note: str = ""


@router.post("/bank-transactions/{tid}/assign")
def assign_txn(tid: int, data: AssignIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    t = db.get(BankTransaction, tid); b = db.get(Booking, data.booking_id)
    if not t or not b: raise HTTPException(404, "Không có giao dịch/booking")
    try:
        r = P.accountant_assign(db, u, t, b, data.note)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"receipt": receipt_out(r, db), "message": f"Đã lập {r.code} cho {b.code}"}


class IgnoreIn(BaseModel):
    note: str = ""


@router.post("/bank-transactions/{tid}/ignore")
def ignore_txn(tid: int, data: IgnoreIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    P.ignore_transaction(db, u, t, data.note)
    return {"message": "Đã bỏ qua giao dịch"}


@router.get("/receipts")
def list_receipts(limit: int = 200, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="phiếu thu")), db: Session = Depends(get_db)):
    q = select(Receipt).order_by(desc(Receipt.created_at))
    q = PV.loc(q, Receipt, u)                # P6: phạm vi pháp nhân của phiên đăng nhập
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: q = q.join(Booking, Booking.id == Receipt.booking_id).where(Booking.sales_id.in_(vis))   # sale/nhóm chỉ thấy phiếu thu của khách mình
    return [receipt_out(r, db) for r in db.execute(q.limit(limit)).scalars()]


@router.post("/receipts/{rid}/confirm")
def confirm_receipt(rid: int, u: User = Depends(require_roles("ketoan",)), db: Session = Depends(get_db)):
    r = db.get(Receipt, rid)
    if not r: raise HTTPException(404, "Không có phiếu thu")
    try:
        P.accountant_confirm(db, u, r)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"message": f"Kế toán đã xác nhận {r.code}"}


class CashIn(BaseModel):
    booking_id: int
    amount: float
    payer: str = ""
    note: str = ""


@router.post("/receipts/cash", status_code=201)
def cash_receipt(data: CashIn, u: User = Depends(require_roles("ketoan",)), db: Session = Depends(get_db)):
    b = db.get(Booking, data.booking_id)
    if not b: raise HTTPException(404, "Không có booking")
    if (data.amount or 0) <= 0: raise HTTPException(422, "Số tiền phải > 0")
    r = P.cash_receipt(db, u, b, data.amount, data.payer, data.note)
    return {"receipt": receipt_out(r, db), "message": f"Đã lập phiếu thu tiền mặt {r.code}"}


@router.get("/collections/summary")
def collections_summary(u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="tổng quan thu tiền")), db: Session = Depends(get_db)):
    """Tổng quan thu tiền: booking còn phải thu, giao dịch chờ Kế toán, phiếu thu chờ xác nhận."""
    rows = []
    qb = select(Booking).order_by(desc(Booking.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qb = qb.where(Booking.sales_id.in_(vis))
    for b in db.execute(qb).scalars():
        due = ((b.amount or 0) - (b.discount or 0)) - P.paid_amount(db, b.id)
        rows.append({"booking_id": b.id, "code": b.code, "tour_code": b.tour.code if b.tour else "", "customer_name": b.customer_name,
                     "total": (b.amount or 0) - (b.discount or 0), "paid": (b.paid or 0), "due": due})
    return {"bookings": rows,
            "pending_txns": db.execute(select(BankTransaction).where(BankTransaction.match_status == "cho_ke_toan")).scalars().all().__len__(),
            "pending_receipts": db.execute(select(Receipt).where(Receipt.status == "tu_dong")).scalars().all().__len__()}
