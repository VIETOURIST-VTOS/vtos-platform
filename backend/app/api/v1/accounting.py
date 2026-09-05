"""API kế toán TT99: danh mục TK, chứng từ ghi sổ, sổ cái, cân đối phát sinh, hóa đơn điện tử, khóa kỳ."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Booking, User
from app.models.accounting import Account, JournalEntry, Invoice, PeriodLock
from app.services import accounting as ACC

router = APIRouter(prefix="/api/v1", tags=["ke-toan"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks", "ptgd_doan", "hcns")


def entry_out(e: JournalEntry) -> dict:
    return {"id": e.id, "code": e.code, "entry_date": e.entry_date, "period": e.period, "description": e.description, "source_type": e.source_type,
            "source_ref": e.source_ref, "tour_id": e.tour_id, "status": e.status, "created_by": e.created_by, "posted_by": e.posted_by, "posted_at": e.posted_at,
            "reversed_by_id": e.reversed_by_id, "amount": sum(l.debit for l in e.lines),
            "lines": [{"id": l.id, "account": l.account_code, "debit": l.debit, "credit": l.credit, "partner": l.partner, "booking_id": l.booking_id, "note": l.note} for l in e.lines]}


def invoice_out(i: Invoice, db: Session) -> dict:
    b = db.get(Booking, i.booking_id) if i.booking_id else None
    return {"id": i.id, "series": i.series, "number": i.number, "no": f"{i.series}-{i.number:07d}" if i.number else "", "issue_date": i.issue_date,
            "booking_id": i.booking_id, "booking_code": b.code if b else "", "tour_code": b.tour.code if b and b.tour else "",
            "customer_name": i.customer_name, "customer_tax_code": i.customer_tax_code, "customer_address": i.customer_address, "description": i.description,
            "pre_tax": i.pre_tax, "vat_rate": i.vat_rate, "vat": i.vat, "total": i.total, "status": i.status, "provider": i.provider, "provider_ref": i.provider_ref,
            "entry_id": i.entry_id, "created_by": i.created_by, "issued_by": i.issued_by, "issued_at": i.issued_at}


@router.get("/accounts")
def accounts(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"code": a.code, "name": a.name, "kind": a.kind, "parent": a.parent} for a in db.execute(select(Account).order_by(Account.code)).scalars()]


# ---------- Chứng từ ----------
@router.get("/journal")
def journal(period: str | None = None, status: str | None = None, limit: int = 300, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(JournalEntry).order_by(desc(JournalEntry.entry_date), desc(JournalEntry.id))
    if period: q = q.where(JournalEntry.period == period)
    if status: q = q.where(JournalEntry.status == status)
    return [entry_out(e) for e in db.execute(q.limit(limit)).scalars()]


class LineIn(BaseModel):
    account: str
    debit: float = 0
    credit: float = 0
    partner: str = ""
    note: str = ""
    booking_id: int | None = None
    tour_id: int | None = None


class EntryIn(BaseModel):
    entry_date: date
    description: str
    lines: list[LineIn]
    tour_id: int | None = None
    post: bool = False


@router.post("/journal", status_code=201)
def create_entry(data: EntryIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        e = ACC.post_entry(db, u.username, u.role, data.entry_date, data.description, [l.model_dump() for l in data.lines], "thu_cong", "", data.tour_id, post=data.post)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit(); db.refresh(e)
    return {"entry": entry_out(e), "message": f"Đã {'ghi sổ' if data.post else 'lập nháp'} {e.code}"}


@router.post("/journal/{eid}/post")
def post_entry(eid: int, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    e = db.get(JournalEntry, eid)
    if not e: raise HTTPException(404, "Không có chứng từ")
    try:
        ACC.post_draft(db, u, e)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã ghi sổ {e.code}"}


class ReasonIn(BaseModel):
    reason: str = ""


@router.post("/journal/{eid}/reverse")
def reverse(eid: int, data: ReasonIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    e = db.get(JournalEntry, eid)
    if not e: raise HTTPException(404, "Không có chứng từ")
    if not data.reason.strip(): raise HTTPException(422, "Phải ghi lý do đảo bút toán")
    try:
        r = ACC.reverse_entry(db, u, e, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"entry": entry_out(r), "message": f"Đã lập chứng từ đảo {r.code}"}


# ---------- Sổ sách ----------
@router.get("/ledger")
def ledger(account: str, period: str | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return ACC.ledger(db, account, period)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/trial-balance")
def trial_balance(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    rows = ACC.trial_balance(db, period)
    tot = {k: sum(r[k] for r in rows) for k in ("open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit")}
    return {"period": period, "rows": rows, "total": tot, "balanced": abs(tot["debit"] - tot["credit"]) < 1 and abs(tot["close_debit"] - tot["close_credit"]) < 1}


# ---------- Hóa đơn điện tử ----------
@router.get("/invoices")
def invoices(status: str | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(Invoice).order_by(desc(Invoice.id))
    if status: q = q.where(Invoice.status == status)
    return [invoice_out(i, db) for i in db.execute(q).scalars()]


class InvoiceIn(BaseModel):
    booking_id: int
    vat_rate: float | None = None
    customer_tax_code: str = ""
    customer_address: str = ""
    description: str = ""


@router.post("/invoices", status_code=201)
def create_invoice(data: InvoiceIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    b = db.get(Booking, data.booking_id)
    if not b: raise HTTPException(404, "Không có booking")
    try:
        inv = ACC.create_invoice(db, u, b, data.vat_rate, data.customer_tax_code, data.customer_address, data.description)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"invoice": invoice_out(inv, db), "message": "Đã lập hóa đơn nháp – kiểm tra rồi phát hành"}


@router.post("/invoices/{iid}/issue")
def issue(iid: int, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "Không có hóa đơn")
    try:
        ACC.issue_invoice(db, u, inv)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"invoice": invoice_out(inv, db), "message": f"Đã phát hành {inv.series}-{inv.number:07d}, mã tra cứu {inv.provider_ref}"}


@router.post("/invoices/{iid}/cancel")
def cancel(iid: int, data: ReasonIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "Không có hóa đơn")
    if not data.reason.strip(): raise HTTPException(422, "Phải ghi lý do hủy")
    try:
        ACC.cancel_invoice(db, u, inv, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": "Đã hủy hóa đơn" + (" và lập bút toán đảo" if inv.entry_id else "")}


# ---------- Khóa kỳ ----------
@router.get("/periods")
def periods(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    locks = {p.period: p for p in db.execute(select(PeriodLock)).scalars()}
    used = sorted(set(db.execute(select(JournalEntry.period).distinct()).scalars()) | set(locks) | {ACC.period_of(date.today())}, reverse=True)
    return [{"period": p, "locked": p in locks, "locked_by": locks[p].locked_by if p in locks else "", "locked_at": locks[p].locked_at if p in locks else None, "note": locks[p].note if p in locks else ""} for p in used]


class LockIn(BaseModel):
    note: str = ""


@router.post("/periods/{period}/lock")
def lock(period: str, data: LockIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        ACC.lock_period(db, u, period, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã khóa kỳ {period}"}
