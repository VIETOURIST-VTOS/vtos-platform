"""API Hồ sơ nhân sự – Hợp đồng – Chấm công – Người phụ thuộc (phân hệ Nhân sự kiểu MISA AMIS)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User
from app.models.hr import Employee
from app.models.hrm import (EmployeeProfile, LaborContract, Dependent, LeaveRequest,
                            CONTRACT_KINDS, CONTRACT_STATUS, RELATIONS, LEAVE_KINDS, LEAVE_STATUS, ATT_KINDS)
from app.services import hrm as H
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["nhan-su-ho-so"])
HR_ADMIN = ("hcns", "cntt", "tgd", "chutich")
HR_READ = ("hcns", "cntt", "tgd", "chutich", "bks", "ketoan")


def _emp(db: Session, eid: int) -> Employee:
    e = db.get(Employee, eid)
    if not e:
        raise HTTPException(404, "Không tìm thấy nhân viên")
    return e


def _self_employee(db: Session, u: User) -> Employee | None:
    return db.execute(select(Employee).where(Employee.user_id == u.id)).scalar_one_or_none()


def contract_out(c: LaborContract) -> dict:
    return {"id": c.id, "employee_id": c.employee_id, "code": c.code, "kind": c.kind,
            "kind_name": CONTRACT_KINDS.get(c.kind, {}).get("ten", c.kind),
            "bhxh": CONTRACT_KINDS.get(c.kind, {}).get("bhxh", False),
            "signed_on": c.signed_on, "effective_from": c.effective_from, "effective_to": c.effective_to,
            "salary": c.salary, "si_salary": c.si_salary, "allowance": c.allowance,
            "annual_leave_days": c.annual_leave_days, "status": c.status,
            "status_name": CONTRACT_STATUS.get(c.status, c.status), "terminated_on": c.terminated_on,
            "terminate_reason": c.terminate_reason, "note": c.note, "created_by": c.created_by}


def profile_out(p: EmployeeProfile | None) -> dict | None:
    if p is None:
        return None
    return {"employee_id": p.employee_id, "dob": p.dob, "gender": p.gender, "id_number": p.id_number,
            "id_issued_on": p.id_issued_on, "id_issued_by": p.id_issued_by,
            "permanent_address": p.permanent_address, "current_address": p.current_address,
            "phone": p.phone, "email": p.email, "tax_code": p.tax_code,
            "social_insurance_no": p.social_insurance_no, "bank_account": p.bank_account, "bank_name": p.bank_name,
            "marital_status": p.marital_status, "education": p.education, "emergency_contact": p.emergency_contact,
            "note": p.note, "updated_by": p.updated_by, "updated_at": p.updated_at}


def leave_out(r: LeaveRequest, e: Employee | None = None) -> dict:
    return {"id": r.id, "employee_id": r.employee_id, "employee_code": e.code if e else "",
            "employee_name": e.full_name if e else "", "department": e.department if e else "",
            "kind": r.kind, "kind_name": LEAVE_KINDS.get(r.kind, {}).get("ten", r.kind),
            "date_from": r.date_from, "date_to": r.date_to, "days": r.days, "ot_hours": r.ot_hours,
            "reason": r.reason, "status": r.status, "status_name": LEAVE_STATUS.get(r.status, r.status),
            "approved_by": r.approved_by, "approved_at": r.approved_at, "decision_note": r.decision_note,
            "created_by": r.created_by, "created_at": r.created_at}


@router.get("/hrm/meta")
def meta(u: User = Depends(current_user)):
    return {"contract_kinds": CONTRACT_KINDS, "contract_status": CONTRACT_STATUS, "relations": RELATIONS,
            "leave_kinds": LEAVE_KINDS, "leave_status": LEAVE_STATUS, "attendance_kinds": ATT_KINDS}


# ---------- Hồ sơ nhân sự ----------

class ProfileIn(BaseModel):
    dob: date | None = None
    gender: str | None = None
    id_number: str | None = None
    id_issued_on: date | None = None
    id_issued_by: str | None = None
    permanent_address: str | None = None
    current_address: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_code: str | None = None
    social_insurance_no: str | None = None
    bank_account: str | None = None
    bank_name: str | None = None
    marital_status: str | None = None
    education: str | None = None
    emergency_contact: str | None = None
    note: str | None = None


@router.get("/employees/{eid}/profile")
def get_profile(eid: int, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    e = _emp(db, eid)
    return {"employee": {"id": e.id, "code": e.code, "full_name": e.full_name, "department": e.department,
                         "position": e.position, "title": e.title, "start_date": e.start_date, "active": e.active},
            "profile": profile_out(H.profile_of(db, eid)),
            "completeness": H.profile_completeness(db, eid),
            "contract": (lambda c: contract_out(c) if c else None)(H.active_contract(db, eid))}


@router.put("/employees/{eid}/profile")
def put_profile(eid: int, data: ProfileIn, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    _emp(db, eid)
    p = H.save_profile(db, u, eid, {k: v for k, v in data.model_dump().items() if v is not None})
    return profile_out(p)


@router.get("/hrm/profile-gaps")
def profile_gaps(u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    """Danh sách nhân sự còn thiếu thông tin hồ sơ bắt buộc – việc HCNS phải đi đòi hằng tháng."""
    out = []
    for e in db.execute(select(Employee).where(Employee.active == True).order_by(Employee.code)).scalars():
        c = H.profile_completeness(db, e.id)
        if c["missing"]:
            out.append({"employee_id": e.id, "code": e.code, "full_name": e.full_name, "department": e.department,
                        "percent": c["percent"], "missing": c["missing"]})
    return {"count": len(out), "rows": out, "required_fields": list(H.PROFILE_REQUIRED)}


# ---------- Hợp đồng lao động ----------

class ContractIn(BaseModel):
    employee_id: int
    code: str
    kind: str = "xac_dinh_12"
    signed_on: date | None = None
    effective_from: date
    effective_to: date | None = None
    salary: float | None = None
    si_salary: float | None = None
    allowance: float | None = None
    annual_leave_days: float = 12
    note: str = ""


@router.get("/labor-contracts")
def list_contracts(employee_id: int = 0, status: str = "", u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    q = select(LaborContract).order_by(LaborContract.effective_from.desc(), LaborContract.id.desc())
    if employee_id:
        q = q.where(LaborContract.employee_id == employee_id)
    if status:
        q = q.where(LaborContract.status == status)
    emps = {e.id: e for e in db.execute(select(Employee)).scalars()}
    out = []
    for c in db.execute(q).scalars():
        d = contract_out(c)
        e = emps.get(c.employee_id)
        d.update({"employee_code": e.code if e else "", "employee_name": e.full_name if e else "",
                  "department": e.department if e else ""})
        out.append(d)
    return out


@router.post("/labor-contracts", status_code=201)
def add_contract(data: ContractIn, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    _emp(db, data.employee_id)
    if data.kind not in CONTRACT_KINDS:
        raise HTTPException(422, f"Loại hợp đồng {data.kind} không hợp lệ")
    if not data.code.strip():
        raise HTTPException(422, "Thiếu số hợp đồng")
    if db.execute(select(LaborContract).where(LaborContract.code == data.code.strip())).scalar_one_or_none():
        raise HTTPException(422, f"Số hợp đồng {data.code} đã tồn tại")
    if data.effective_to and data.effective_to < data.effective_from:
        raise HTTPException(422, "Ngày hết hiệu lực phải sau ngày có hiệu lực")
    c = LaborContract(employee_id=data.employee_id, code=data.code.strip()[:40], kind=data.kind,
                      signed_on=data.signed_on, effective_from=data.effective_from, effective_to=data.effective_to,
                      salary=data.salary, si_salary=data.si_salary, allowance=data.allowance,
                      annual_leave_days=data.annual_leave_days, note=data.note[:300], created_by=u.username)
    db.add(c); db.flush()
    R.audit(db, u.username, u.role, "ky_hop_dong_lao_dong", f"hdld:{c.code}",
            after={"nhan_vien_id": c.employee_id, "loai": c.kind, "tu": str(c.effective_from), "den": str(c.effective_to or "")})
    db.commit()
    return contract_out(c)


class TerminateIn(BaseModel):
    on: date
    reason: str = ""


@router.post("/labor-contracts/{cid}/terminate")
def terminate_contract(cid: int, data: TerminateIn, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    c = db.get(LaborContract, cid)
    if not c:
        raise HTTPException(404, "Không tìm thấy hợp đồng")
    if c.status == "cham_dut":
        raise HTTPException(422, "Hợp đồng đã chấm dứt")
    c.status, c.terminated_on, c.terminate_reason = "cham_dut", data.on, data.reason[:300]
    R.audit(db, u.username, u.role, "cham_dut_hop_dong", f"hdld:{c.code}", after={"ngay": str(data.on), "ly_do": data.reason})
    db.commit()
    return contract_out(c)


@router.get("/labor-contracts/alerts")
def alerts(within_days: int = 45, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    H.close_expired_contracts(db)
    return H.contract_alerts(db, within_days)


# ---------- Người phụ thuộc ----------

class DependentIn(BaseModel):
    employee_id: int
    full_name: str
    relation: str = "con"
    dob: date | None = None
    tax_code: str = ""
    id_number: str = ""
    from_period: str = ""
    to_period: str = ""
    note: str = ""


@router.get("/dependents")
def list_dependents(employee_id: int, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    return [{"id": d.id, "employee_id": d.employee_id, "full_name": d.full_name, "relation": d.relation,
             "relation_name": RELATIONS.get(d.relation, d.relation), "dob": d.dob, "tax_code": d.tax_code,
             "id_number": d.id_number, "from_period": d.from_period, "to_period": d.to_period, "active": d.active,
             "note": d.note}
            for d in H.dependents_of(db, employee_id)]


@router.post("/dependents", status_code=201)
def add_dependent(data: DependentIn, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    _emp(db, data.employee_id)
    if data.relation not in RELATIONS:
        raise HTTPException(422, f"Quan hệ {data.relation} không hợp lệ")
    d = Dependent(employee_id=data.employee_id, full_name=data.full_name.strip()[:120], relation=data.relation,
                  dob=data.dob, tax_code=data.tax_code[:20], id_number=data.id_number[:20],
                  from_period=data.from_period[:7], to_period=data.to_period[:7], note=data.note[:200],
                  created_by=u.username)
    if not d.full_name:
        raise HTTPException(422, "Thiếu họ tên người phụ thuộc")
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "them_nguoi_phu_thuoc", f"npt:{d.id}",
            after={"nhan_vien_id": d.employee_id, "ho_ten": d.full_name, "quan_he": d.relation})
    db.commit()
    return {"id": d.id, "employee_id": d.employee_id, "full_name": d.full_name, "relation": d.relation}


@router.delete("/dependents/{did}")
def remove_dependent(did: int, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    d = db.get(Dependent, did)
    if not d:
        raise HTTPException(404, "Không tìm thấy người phụ thuộc")
    d.active = False
    R.audit(db, u.username, u.role, "ngung_nguoi_phu_thuoc", f"npt:{d.id}", after={"ho_ten": d.full_name})
    db.commit()
    return {"message": f"Đã ngừng giảm trừ cho {d.full_name}"}


@router.get("/employees/{eid}/pit-deduction")
def pit_deduction(eid: int, period: str, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    _emp(db, eid)
    return H.pit_deduction(db, eid, period)


# ---------- Đơn từ & phép năm ----------

class LeaveIn(BaseModel):
    employee_id: int = 0            # 0 = tự gửi đơn cho chính mình
    kind: str = "phep_nam"
    date_from: date
    date_to: date | None = None
    days: float | None = None
    ot_hours: float = 0
    reason: str = ""


@router.get("/leaves")
def list_leaves(status: str = "", employee_id: int = 0, kind: str = "",
                u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(LeaveRequest).order_by(LeaveRequest.date_from.desc(), LeaveRequest.id.desc())
    if u.role not in HR_READ:                                # nhân viên thường chỉ xem đơn của mình
        me = _self_employee(db, u)
        if not me:
            return []
        q = q.where(LeaveRequest.employee_id == me.id)
    elif employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    if status:
        q = q.where(LeaveRequest.status == status)
    if kind:
        q = q.where(LeaveRequest.kind == kind)
    emps = {e.id: e for e in db.execute(select(Employee)).scalars()}
    return [leave_out(r, emps.get(r.employee_id)) for r in db.execute(q).scalars()]


@router.post("/leaves", status_code=201)
def add_leave(data: LeaveIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.employee_id and u.role in HR_ADMIN:
        e = _emp(db, data.employee_id)
    else:
        e = _self_employee(db, u)
        if not e:
            raise HTTPException(422, "Tài khoản chưa gắn với hồ sơ nhân sự – HCNS cần ghép tài khoản trước")
    try:
        r = H.create_leave(db, u, e, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return leave_out(r, e)


class DecisionIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/leaves/{lid}/decide")
def decide_leave(lid: int, data: DecisionIn, u: User = Depends(require_roles("hcns", "tgd", "chutich", "gd_kd", "ptgd_doan", "tp_kd", "cntt")),
                 db: Session = Depends(get_db)):
    r = db.get(LeaveRequest, lid)
    if not r:
        raise HTTPException(404, "Không tìm thấy đơn")
    try:
        H.decide_leave(db, u, r, data.approve, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return leave_out(r, db.get(Employee, r.employee_id))


@router.get("/leave-balance")
def leave_balance(year: int = 0, employee_id: int = 0, u: User = Depends(current_user), db: Session = Depends(get_db)):
    year = year or date.today().year
    if u.role in HR_READ:
        q = select(Employee).where(Employee.active == True)
        if employee_id:
            q = q.where(Employee.id == employee_id)
        return [H.leave_balance(db, e, year) for e in db.execute(q.order_by(Employee.code)).scalars()]
    me = _self_employee(db, u)
    if not me:
        raise HTTPException(422, "Tài khoản chưa gắn với hồ sơ nhân sự")
    return [H.leave_balance(db, me, year)]


# ---------- Bảng chấm công ----------

@router.get("/attendance")
def attendance(period: str, department: str = "", u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    return H.attendance_sheet(db, period, department)


class AttendanceIn(BaseModel):
    employee_id: int
    day: date
    kind: str = "lam_viec"
    work: float = 1
    ot_hours: float = 0
    note: str = ""


@router.post("/attendance")
def set_attendance(data: AttendanceIn, u: User = Depends(require_roles(*HR_ADMIN)), db: Session = Depends(get_db)):
    _emp(db, data.employee_id)
    try:
        row = H.set_attendance(db, u, data.employee_id, data.day, data.kind, data.work, data.ot_hours, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"employee_id": row.employee_id, "day": row.day, "kind": row.kind, "work": row.work,
            "ot_hours": row.ot_hours, "note": row.note}
