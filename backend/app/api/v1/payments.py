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
    payload = await request.json()
    try:
        txn, created = P.ingest_sepay(db, payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"success": True, "new": created, "match_status": txn.match_status, "note": txn.match_note}


# ---------- Kế toán ----------
@router.get("/bank-transactions")
def list_txns(status: str | None = None, limit: int = 200, u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(BankTransaction).order_by(desc(BankTransaction.transaction_date))
    if status: q = q.where(BankTransaction.match_status.in_(status.split(",")))
    return [txn_out(t, db) for t in db.execute(q.limit(limit)).scalars()]


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
def list_receipts(limit: int = 200, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [receipt_out(r, db) for r in db.execute(select(Receipt).order_by(desc(Receipt.created_at)).limit(limit)).scalars()]


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
    if data.amount <= 0: raise HTTPException(422, "Số tiền phải > 0")
    r = P.cash_receipt(db, u, b, data.amount, data.payer, data.note)
    return {"receipt": receipt_out(r, db), "message": f"Đã lập phiếu thu tiền mặt {r.code}"}


@router.get("/collections/summary")
def collections_summary(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Tổng quan thu tiền: booking còn phải thu, giao dịch chờ Kế toán, phiếu thu chờ xác nhận."""
    rows = []
    for b in db.execute(select(Booking).order_by(desc(Booking.created_at))).scalars():
        due = (b.amount - b.discount) - P.paid_amount(db, b.id)
        rows.append({"booking_id": b.id, "code": b.code, "tour_code": b.tour.code if b.tour else "", "customer_name": b.customer_name,
                     "total": b.amount - b.discount, "paid": b.paid, "due": due})
    return {"bookings": rows,
            "pending_txns": db.execute(select(BankTransaction).where(BankTransaction.match_status == "cho_ke_toan")).scalars().all().__len__(),
            "pending_receipts": db.execute(select(Receipt).where(Receipt.status == "tu_dong")).scalars().all().__len__()}
