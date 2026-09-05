"""API ngân quỹ – tài chính: hợp đồng vay/đầu tư (3.9), lịch thu-trả, dự báo 13 tuần, báo cáo tài chính tuần."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User
from app.models.finance import FinContract, FinSchedule, CashPlanItem, CONTRACT_KINDS
from app.services import finance as F
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["tai-chinh"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks")
WRITE = ("ketoan",)


def c_out(c: FinContract) -> dict:
    return {"id": c.id, "code": c.code, "kind": c.kind, "kind_name": CONTRACT_KINDS.get(c.kind, c.kind), "entity": c.entity, "partner": c.partner, "contract_no": c.contract_no,
            "signed_on": c.signed_on, "principal": c.principal, "outstanding": c.outstanding, "interest_rate": c.interest_rate, "maturity": c.maturity, "collateral": c.collateral,
            "purpose": c.purpose, "owner": c.owner, "approval_ref": c.approval_ref, "related_party": c.related_party, "status": c.status, "note": c.note,
            "schedule": [{"id": s.id, "due_date": s.due_date, "kind": s.kind, "amount": s.amount, "status": s.status, "done_on": s.done_on, "bank_ref": s.bank_ref} for s in c.schedule]}


@router.get("/fin/meta")
def meta(u: User = Depends(current_user)):
    return {"kinds": CONTRACT_KINDS}


@router.get("/fin/contracts")
def contracts(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return [c_out(c) for c in db.execute(select(FinContract).order_by(FinContract.kind, desc(FinContract.id))).scalars()]


class ContractIn(BaseModel):
    kind: str
    entity: str = "Công ty mẹ"
    partner: str
    contract_no: str = ""
    signed_on: date | None = None
    principal: float
    outstanding: float = 0
    interest_rate: float = 0
    maturity: date | None = None
    collateral: str = ""
    purpose: str = ""
    owner: str = ""
    approval_ref: str = ""
    related_party: bool = False
    note: str = ""
    months: int = 0
    first_due: date | None = None


@router.post("/fin/contracts", status_code=201)
def create(data: ContractIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    d = data.model_dump(); months = d.pop("months"); first = d.pop("first_due")
    try:
        c = F.create_contract(db, u, d, months, first)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"contract": c_out(c), "message": f"Đã lập hồ sơ {c.code}" + (f" – {len(c.schedule)} dòng lịch" if c.schedule else "")}


class SchedIn(BaseModel):
    due_date: date
    kind: str
    amount: float


@router.post("/fin/contracts/{cid}/schedule", status_code=201)
def add_sched(cid: int, data: SchedIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = db.get(FinContract, cid)
    if not c: raise HTTPException(404, "Không có hợp đồng")
    if data.kind not in ("tra_goc", "tra_lai", "thu_hoi", "giai_ngan", "nhan_vay"): raise HTTPException(422, "Loại lịch không hợp lệ")
    db.add(FinSchedule(contract_id=c.id, **data.model_dump()))
    R.audit(db, u.username, u.role, "them_lich_tai_chinh", f"fin:{c.code}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã thêm dòng lịch"}


class SettleIn(BaseModel):
    done_on: date
    bank_ref: str = ""
    amount: float | None = None


@router.post("/fin/schedule/{sid}/settle")
def settle(sid: int, data: SettleIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    s = db.get(FinSchedule, sid)
    if not s: raise HTTPException(404, "Không có dòng lịch")
    try:
        F.settle(db, u, s, data.done_on, data.bank_ref, data.amount)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã ghi nhận {s.kind} {s.amount:,.0f} đ – dư nợ còn {s.contract.outstanding:,.0f} đ"}


@router.get("/fin/forecast")
def forecast(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return F.forecast_13w(db)


@router.get("/fin/weekly")
def weekly(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return F.weekly_finance(db)


@router.get("/fin/plan")
def plan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return [{"id": i.id, "due_date": i.due_date, "direction": i.direction, "category": i.category, "description": i.description, "amount": i.amount, "recurring_monthly": i.recurring_monthly}
            for i in db.execute(select(CashPlanItem).order_by(CashPlanItem.due_date)).scalars()]


class PlanIn(BaseModel):
    due_date: date
    direction: str
    category: str
    description: str
    amount: float
    recurring_monthly: bool = False


@router.post("/fin/plan", status_code=201)
def plan_add(data: PlanIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    if data.direction not in ("in", "out"): raise HTTPException(422, "direction: in/out")
    db.add(CashPlanItem(**data.model_dump(), created_by=u.username)); db.commit()
    return {"message": "Đã thêm khoản kế hoạch"}


@router.delete("/fin/plan/{pid}")
def plan_del(pid: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    i = db.get(CashPlanItem, pid)
    if i: db.delete(i); db.commit()
    return {"message": "Đã xóa"}
