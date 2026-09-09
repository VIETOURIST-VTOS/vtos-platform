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
from app.services import rules as R_
from app.services import pham_vi_phap_nhan as PV
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["ke-toan"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks", "ptgd_doan", "hcns")


def entry_out(e: JournalEntry) -> dict:
    return {"id": e.id, "code": e.code, "entry_date": e.entry_date, "period": e.period, "description": e.description, "source_type": e.source_type,
            "source_ref": e.source_ref, "tour_id": e.tour_id, "status": e.status, "created_by": e.created_by, "posted_by": e.posted_by, "posted_at": e.posted_at,
            "reversed_by_id": e.reversed_by_id, "amount": sum((l.debit or 0) for l in e.lines),
            "lines": [{"id": l.id, "account": l.account_code, "debit": l.debit, "credit": l.credit, "partner": l.partner, "partner_code": l.partner_code, "project_code": l.project_code, "item_code": l.item_code, "doc_no": l.doc_no, "booking_id": l.booking_id, "note": l.note} for l in e.lines]}


def invoice_out(i: Invoice, db: Session) -> dict:
    b = db.get(Booking, i.booking_id) if i.booking_id else None
    return {"id": i.id, "series": i.series, "number": i.number, "no": f"{i.series}-{i.number:07d}" if i.number else "", "issue_date": i.issue_date,
            "booking_id": i.booking_id, "booking_code": b.code if b else "", "tour_code": b.tour.code if b and b.tour else "",
            "customer_name": i.customer_name, "customer_tax_code": i.customer_tax_code, "customer_address": i.customer_address, "description": i.description,
            "pre_tax": i.pre_tax, "vat_rate": i.vat_rate, "vat": i.vat, "total": i.total, "status": i.status, "provider": i.provider, "provider_ref": i.provider_ref,
            "entry_id": i.entry_id, "created_by": i.created_by, "issued_by": i.issued_by, "issued_at": i.issued_at}


@router.get("/accounts")
def accounts(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"code": a.code, "name": a.name, "kind": a.kind, "parent": a.parent, "level": a.level, "is_detail": a.is_detail, "bs_debit": a.bs_debit, "bs_credit": a.bs_credit, "pl_code": a.pl_code, "misa": a.misa}
            for a in db.execute(select(Account).order_by(Account.code)).scalars()]


# ---------- Chứng từ ----------
@router.get("/journal")
def journal(period: str | None = None, status: str | None = None, limit: int = 300, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(JournalEntry).order_by(desc(JournalEntry.entry_date), desc(JournalEntry.id))
    q = PV.loc(q, JournalEntry, u)           # P6: phạm vi pháp nhân của phiên đăng nhập
    if period: q = q.where(JournalEntry.period == period)
    if status: q = q.where(JournalEntry.status == status)
    return [entry_out(e) for e in db.execute(q.limit(limit)).scalars()]


class LineIn(BaseModel):
    account: str
    debit: float | None = None
    credit: float | None = None
    partner: str = ""
    partner_code: str = ""
    project_code: str = ""
    item_code: str = ""
    doc_no: str = ""
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
    return {"period": period, "rows": rows, "total": tot, "balanced": abs((tot["debit"] or 0) - (tot["credit"] or 0)) < 1 and abs(tot["close_debit"] - tot["close_credit"]) < 1}


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


# ---------- BCTC & tờ khai thuế (robot R5/R7) ----------
from fastapi import Response
from app.services import reports as RP


@router.get("/reports/balance-sheet")
def balance_sheet(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.balance_sheet(db, period)


@router.get("/reports/income-statement")
def income_statement(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.income_statement(db, period)


@router.get("/reports/cash-flow")
def cash_flow(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.cash_flow(db, period)


@router.post("/reports/closing-entries/{period}")
def closing(period: str, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        es = RP.closing_entries_draft(db, u, period)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Robot đã lập {len(es)} chứng từ kết chuyển NHÁP kỳ {period} – Kế toán trưởng kiểm tra rồi ghi sổ", "entries": [entry_out(e) for e in es]}


@router.get("/tax/vat")
def vat(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.vat_return(db, period)


@router.get("/tax/pit")
def pit(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.pit_return(db, period)


@router.get("/tax/{kind}/xml")
def tax_xml(kind: str, period: str, u: User = Depends(require_roles("ketoan", "cntt", "tgd")), db: Session = Depends(get_db)):
    ret = RP.vat_return(db, period) if kind == "vat" else RP.pit_return(db, period) if kind == "pit" else None
    if not ret: raise HTTPException(404, "Loại tờ khai: vat / pit")
    R_.audit(db, u.username, u.role, "xuat_xml_to_khai", f"tax:{kind}:{period}", after={"mau": ret["form"]}); db.commit()
    return Response(content=RP.to_xml(ret, tax_code=settings.COMPANY_TAX_CODE, company=settings.COMPANY_NAME), media_type="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="{kind}_{period}.xml"'})


# ---------- MISA ↔ VTOS (định hướng 06/9/2026) ----------
from fastapi import UploadFile, File, Form
from app.services import misa as MISA
from app.services import bctc as BCTC
from app.models.accounting import Partner, Project

MISA_WRITE = ("ketoan", "cntt")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content=content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/misa/trial-balance/preview")
async def misa_tb_preview(file: UploadFile = File(...), u: User = Depends(require_roles(*READ))):
    try: p = MISA.parse_trial_balance(await file.read())
    except ValueError as ex: raise HTTPException(422, str(ex))
    leafs = MISA.leaf_rows(p["rows"])
    return {"period": p["period"], "accounts": len(p["rows"]), "detail_accounts": len(leafs),
            "open_debit": sum(r["open_d"] for r in leafs), "open_credit": sum(r["open_c"] for r in leafs), "close_debit": sum(r["close_d"] for r in leafs), "close_credit": sum(r["close_c"] for r in leafs), "rows": p["rows"]}


@router.post("/misa/opening-balance")
async def misa_opening(file: UploadFile = File(...), objects: UploadFile | None = File(default=None), as_of: date = Form(...), column: str = Form("close"), replace: bool = Form(False),
                       u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try:
        return {"message": "Đã ghi số dư đầu kỳ từ MISA", **MISA.import_opening_balance(db, u, await file.read(), as_of, column, await objects.read() if objects else None, replace)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/kiem-toan-checkpoint")
async def misa_kiem_toan(column: str = Form("close"), replace: bool = Form(False),
                          u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    """Chốt sổ theo BCTC đã kiểm toán/soát xét (thay vì số MISA thô) – dùng khi phát hiện số MISA chưa chuẩn."""
    try:
        return {"message": "Đã chốt sổ theo BCTC kiểm toán/soát xét", **MISA.import_audited_checkpoint(db, u, column, replace)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/partners")
async def misa_partners(file: UploadFile = File(...), kind: str = Form("auto"), u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã nạp danh mục đối tượng", **MISA.import_partners(db, await file.read(), kind)}
    except (ValueError, StopIteration) as ex: raise HTTPException(422, f"Không đọc được tệp danh mục: {ex}")


@router.post("/misa/projects")
async def misa_projects(file: UploadFile = File(...), u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã nạp danh mục công trình", **MISA.import_projects(db, await file.read())}
    except (ValueError, StopIteration) as ex: raise HTTPException(422, f"Không đọc được tệp công trình: {ex}")


@router.post("/misa/journal")
async def misa_journal(file: UploadFile = File(...), date_from: date | None = Form(None), date_to: date | None = Form(None), dry_run: bool = Form(False), limit: int | None = Form(None),
                       u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã đọc sổ nhật ký chung" if dry_run else "Đã nạp sổ nhật ký chung MISA", **MISA.import_journal(db, u, await file.read(), date_from, date_to, dry_run, limit)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/reconcile")
async def misa_reconcile(file: UploadFile = File(...), column: str = Form("close"), u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try: return MISA.reconcile(db, await file.read(), column)
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.get("/misa/export/purchases.xlsx")
def misa_export_purchases(date_from: date, date_to: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_purchases(db, date_from, date_to), f"Import_MISA_MuaDichVu_{date_from:%d%m}_{date_to:%d%m%Y}.xlsx")


@router.get("/misa/export/projects.xlsx")
def misa_export_projects(date_from: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_projects(db, date_from), "Import_DanhMuc_CongTrinh_VTOS.xlsx")


@router.get("/misa/export/entries.xlsx")
def misa_export_entries(date_from: date, date_to: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_general_entries(db, date_from, date_to), f"Import_MISA_ButToan_{date_from:%d%m}_{date_to:%d%m%Y}.xlsx")


@router.get("/partners")
def partners(q: str = "", kind: str | None = None, limit: int = 30, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return MISA.partner_lookup(db, q, kind, limit)


@router.get("/partners/stats")
def partners_stats(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from sqlalchemy import func
    return {"partners": db.execute(select(func.count()).select_from(Partner)).scalar(), "customers": db.execute(select(func.count()).select_from(Partner).where(Partner.is_customer == True)).scalar(),
            "suppliers": db.execute(select(func.count()).select_from(Partner).where(Partner.is_supplier == True)).scalar(), "projects": db.execute(select(func.count()).select_from(Project)).scalar(),
            "projects_linked": db.execute(select(func.count()).select_from(Project).where(Project.tour_id != None)).scalar(),
            "misa_entries": db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.source_type == "misa")).scalar(),
            "opening_entries": [e.code for e in db.execute(select(JournalEntry).where(JournalEntry.source_type == "so_du_dau_ky", JournalEntry.status == "da_ghi_so")).scalars()]}


@router.get("/projects")
def projects(q: str = "", limit: int = 50, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = select(Project)
    if q: s = s.where((Project.code.ilike(f"%{q}%")) | (Project.name.ilike(f"%{q}%")))
    return [{"code": p.code, "name": p.name, "start_date": p.start_date, "end_date": p.end_date, "status": p.status, "tour_id": p.tour_id, "technical": p.technical} for p in db.execute(s.order_by(Project.code).limit(limit)).scalars()]


@router.get("/reports/bctc")
def bctc_report(upto: date, since: date | None = None, compare_upto: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    r = BCTC.bctc(db, upto, since, compare_upto); r.pop("detail", None); return r


@router.get("/reports/bctc.xlsx")
def bctc_xlsx(upto: date, since: date | None = None, compare_upto: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    r = BCTC.bctc(db, upto, since, compare_upto)
    R_.audit(db, u.username, u.role, "xuat_bctc_tt99", f"bctc:{upto}", after={"since": str(r["since"])}); db.commit()
    return _xlsx(BCTC.bctc_xlsx(r), f"BCTC_TT99_{upto:%Y%m%d}.xlsx")


@router.get("/reports/vay-341")
def vay_341(upto: date, since: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    since = since or date(upto.year, 1, 1)
    return BCTC.loan_bank_detail_341(db, since, upto)


@router.get("/reports/vay-341.xlsx")
def vay_341_xlsx(upto: date, since: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    since = since or date(upto.year, 1, 1)
    r = BCTC.loan_bank_detail_341(db, since, upto)
    R_.audit(db, u.username, u.role, "xuat_chi_tiet_vay_341", f"vay341:{upto}", after={"since": str(since)}); db.commit()
    return _xlsx(BCTC.loan_bank_detail_xlsx(r), f"CHI_TIET_VAY_341_{since:%d%m}_{upto:%d%m%Y}.xlsx")
