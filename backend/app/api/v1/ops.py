"""API vận hành: báo cáo ngày (Điều 12), ca trực page, đề nghị chi – lệnh chi (R3), bảng dòng tiền tour."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Tour, User, ROLES
from app.models.hr import Employee
from app.models.ops import DailyReport, PageShift, PaymentRequest
from app.services import ops as O
from app.services import access as AC
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["van-hanh"])
MANAGERS = ("tp_dh", "gd_kd", "ptgd_doan", "ptgd_mkt", "tgd", "chutich", "hcns", "cntt", "bks")
DEPT_OF_ROLE = {"nv_kd": ("Kinh doanh Lẻ", "Kinh doanh Đoàn"), "nv_dh": ("Điều hành",)}


# ---------- Báo cáo ngày ----------
def report_out(r: DailyReport, users: dict) -> dict:
    u = users.get(r.user_id)
    return {"id": r.id, "user_id": r.user_id, "user": u.full_name if u else r.user_id, "department": u.department if u else "", "role": u.role if u else "",
            "report_date": r.report_date, "part1_done": r.part1_done, "part2_numbers": r.part2_numbers, "part3_issues": r.part3_issues, "part4_plan": r.part4_plan,
            "submitted_at": r.submitted_at, "on_time": r.on_time, "robot_score": r.robot_score, "robot_note": r.robot_note, "manager_score": r.manager_score,
            "manager_note": r.manager_note, "reviewed_by": r.reviewed_by, "reviewed_at": r.reviewed_at}


class ReportIn(BaseModel):
    report_date: date
    part1_done: str
    part2_numbers: str = ""
    part3_issues: str = ""
    part4_plan: str


@router.post("/daily-reports", status_code=201)
def submit(data: ReportIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        r = O.submit_report(db, u, data.report_date, data.part1_done, data.part2_numbers, data.part3_issues, data.part4_plan)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã nộp báo cáo {r.report_date:%d/%m} – điểm nháp robot {r.robot_score:.0f}/10 ({r.robot_note})", "report": report_out(r, {u.id: u})}


@router.get("/daily-reports")
def list_reports(period: str | None = None, mine: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db)):
    users = {x.id: x for x in db.execute(select(User)).scalars()}
    q = select(DailyReport).order_by(desc(DailyReport.report_date), DailyReport.user_id)
    if mine or u.role not in MANAGERS:
        q = q.where(DailyReport.user_id == u.id)
    rows = [r for r in db.execute(q.limit(1000)).scalars() if not period or f"{r.report_date:%Y-%m}" == period]
    return [report_out(r, users) for r in rows]


class ReviewIn(BaseModel):
    score: float
    note: str = ""


@router.post("/daily-reports/{rid}/review")
def review(rid: int, data: ReviewIn, u: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    r = db.get(DailyReport, rid)
    if not r: raise HTTPException(404, "Không có báo cáo")
    try:
        O.review_report(db, u, r, data.score, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã chấm {data.score:g}/10"}


@router.get("/daily-reports/summary")
def summary(period: str, u: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    """Tổng hợp tháng theo người: số ngày nộp / ngày làm việc, đúng giờ, điểm bình quân, xếp loại A/B/C/D (nháp – cảnh báo sớm)."""
    y, m = map(int, period.split("-"))
    today = date.today()
    days = O.work_days_in(y, m, until=today if (y, m) == (today.year, today.month) else None)
    users = {x.id: x for x in db.execute(select(User)).scalars()}
    emps = db.execute(select(Employee).where(Employee.active == True, Employee.department.in_(O.NO_TIMESHEET_DEPTS), Employee.user_id != None)).scalars().all()
    reports = [r for r in db.execute(select(DailyReport)).scalars() if f"{r.report_date:%Y-%m}" == period]
    out = []
    for e in emps:
        mine = [r for r in reports if r.user_id == e.user_id]
        grade, avg = O.monthly_grade(mine, len(days))
        out.append({"code": e.code, "name": e.full_name, "department": e.department, "submitted": len(mine), "work_days": len(days), "on_time": sum(1 for r in mine if r.on_time),
                    "reviewed": sum(1 for r in mine if r.reviewed_by), "avg": avg, "grade": grade, "missing": len(days) - len(mine)})
    out.sort(key=lambda r: (-r["avg"], r["name"]))
    return {"period": period, "work_days": len(days), "rows": out}


@router.post("/daily-reports/check-missing")
def check_missing(u: User = Depends(require_roles("cntt", "hcns", "tgd")), db: Session = Depends(get_db)):
    n = O.check_missing_reports(db)
    return {"message": f"Robot đã rà: {n} cảnh báo thiếu báo cáo ngày", "new_alerts": n}


# ---------- Ca trực page ----------
@router.get("/page-shifts")
def shifts(period: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows = db.execute(select(PageShift).order_by(desc(PageShift.shift_date), PageShift.slot)).scalars().all()
    return [{"id": s.id, "shift_date": s.shift_date, "slot": s.slot, "employee_id": s.employee_id, "employee": emps.get(s.employee_id, ""), "assigned_by": s.assigned_by,
             "missed": s.missed, "missed_note": s.missed_note, "scanned_at": s.scanned_at, "responded": s.responded, "penalty": O.shift_penalty(s.missed)[0], "kicked": O.shift_penalty(s.missed)[1]}
            for s in rows if not period or f"{s.shift_date:%Y-%m}" == period]


class ShiftIn(BaseModel):
    shift_date: date
    slot: str
    employee_id: int


@router.post("/page-shifts", status_code=201)
def create_shift(data: ShiftIn, u: User = Depends(require_roles("gd_kd", "cntt")), db: Session = Depends(get_db)):
    if data.slot not in ("sang", "chieu", "toi"): raise HTTPException(422, "Ca: sang / chieu / toi")
    s = PageShift(**data.model_dump(), assigned_by=u.username); db.add(s); db.flush()
    R.audit(db, u.username, u.role, "phan_ca_truc_page", f"shift:{s.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã phân ca"}


class ScanIn(BaseModel):
    missed: int
    note: str = ""


@router.post("/page-shifts/{sid}/scan")
def scan(sid: int, data: ScanIn, u: User = Depends(require_roles("cntt", "gd_kd")), db: Session = Depends(get_db)):
    """Robot AI quét fanpage (hoặc CNTT nhập) số lượt sót > 5 phút của ca."""
    s = db.get(PageShift, sid)
    if not s: raise HTTPException(404, "Không có ca")
    s.missed, s.missed_note, s.scanned_at = max(0, data.missed), data.note, datetime.now()
    pen, kicked = O.shift_penalty(s.missed)
    R.audit(db, u.username, u.role, "quet_ca_truc_page", f"shift:{s.id}", after={"sot": s.missed, "phat": pen, "loai_ca": kicked}); db.commit()
    return {"message": f"Ca {s.shift_date:%d/%m} {s.slot}: {s.missed} lượt sót → chế tài {pen:,.0f} đ" + (" – loại khỏi ca tháng sau" if kicked else "")}


class RespondIn(BaseModel):
    text: str


@router.post("/page-shifts/{sid}/respond")
def respond(sid: int, data: RespondIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(PageShift, sid)
    if not s: raise HTTPException(404, "Không có ca")
    s.responded = data.text[:300]
    R.audit(db, u.username, u.role, "phan_hoi_ca_truc", f"shift:{s.id}", after={"noi_dung": s.responded}); db.commit()
    return {"message": "Đã ghi phản hồi"}


# ---------- Đề nghị chi – lệnh chi ----------
def pr_out(r: PaymentRequest, db: Session) -> dict:
    t = db.get(Tour, r.tour_id) if r.tour_id else None
    nxt = {"cho_tp": "Bộ phận xác nhận", "cho_kt": "Kế toán kiểm tra", "cho_duyet": ("Chủ tịch + TGĐ" if r.two_signatures else "TGĐ") + " duyệt", "cho_chi": "Kế toán chi trên ngân hàng",
           "da_chi": "Hoàn tất", "tu_choi": "Từ chối"}[r.status]
    return {"id": r.id, "code": r.code, "category": r.category, "tour_id": r.tour_id, "tour_code": t.code if t else "", "supplier_name": r.supplier_name, "supplier_tax_code": r.supplier_tax_code,
            "supplier_bank": r.supplier_bank, "amount": r.amount, "description": r.description, "has_document": r.has_document, "document_ref": r.document_ref, "has_invoice": r.has_invoice,
            "over_budget": r.over_budget, "two_signatures": r.two_signatures, "status": r.status, "next": nxt, "created_by": r.created_by, "created_at": r.created_at, "tp_by": r.tp_by,
            "kt_by": r.kt_by, "approved_by": r.approved_by, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "approved_at": r.approved_at, "reject_reason": r.reject_reason,
            "paid_at": r.paid_at, "paid_ref": r.paid_ref, "paid_method": r.paid_method, "entry_ids": r.entry_ids}


@router.get("/payment-requests")
def list_pr(status: str | None = None, tour_id: int | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    AC.require(u, AC.PAYMENT_REQUEST_ROLES, "đề nghị chi")
    q = select(PaymentRequest).order_by(desc(PaymentRequest.id))
    if u.role in ("gd_kd", "ptgd_mkt", "hcns"): q = q.where(PaymentRequest.created_by == u.username)   # bộ phận ngoài Điều hành chỉ thấy đề nghị mình lập
    if status: q = q.where(PaymentRequest.status.in_(status.split(",")))
    if tour_id: q = q.where(PaymentRequest.tour_id == tour_id)
    return [pr_out(r, db) for r in db.execute(q.limit(300)).scalars()]


class PRIn(BaseModel):
    category: str
    tour_id: int | None = None
    supplier_name: str
    supplier_tax_code: str = ""
    supplier_bank: str = ""
    amount: float
    description: str
    has_document: bool = False
    document_ref: str = ""
    has_invoice: bool = False


@router.post("/payment-requests", status_code=201)
def create_pr(data: PRIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "ptgd_mkt", "hcns", "cntt", "gd_kd", "nv_kd")), db: Session = Depends(get_db)):
    try:
        r = O.create_request(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, {"gate": "CONG_14", "message": str(ex)} if "cổng 14" in str(ex) else str(ex))
    flags = []
    if r.over_budget: flags.append("NGOÀI DỰ TOÁN → 2 chữ ký (cổng 15)")
    if r.two_signatures and not r.over_budget: flags.append("≥ hạn mức Marketing → 2 chữ ký (cổng 15)")
    return {"request": pr_out(r, db), "message": f"Đã lập {r.code}" + (" – " + "; ".join(flags) if flags else "")}


class StepIn(BaseModel):
    action: str          # confirm / check / approve / pay / reject
    reason: str = ""


@router.post("/payment-requests/{rid}/step")
def pr_step(rid: int, data: StepIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(PaymentRequest, rid)
    if not r: raise HTTPException(404, "Không có đề nghị chi")
    try:
        msg = O.step(db, u, r, data.action, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg, "request": pr_out(r, db)}


@router.get("/tours/{tid}/cashflow")
def cashflow(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    AC.require(u, AC.COST_ROLES, "dòng tiền tour")
    cf = O.tour_cashflow(db, t)
    cf["requests"] = [pr_out(r, db) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == tid).order_by(desc(PaymentRequest.id))).scalars()]
    return cf


@router.get("/cashflow")
def cashflow_all(u: User = Depends(require_roles(*MANAGERS, "ketoan", "nv_dh")), db: Session = Depends(get_db)):
    return [O.tour_cashflow(db, t) for t in db.execute(select(Tour).where(Tour.status.in_(["da_duyet", "ket_thuc", "da_dong_so", "kt_xac_nhan"])).order_by(Tour.start_date)).scalars()]
