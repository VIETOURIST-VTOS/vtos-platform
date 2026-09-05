"""API nhân sự – lương: hồ sơ, visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương (robot R6)."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Tour, User
from app.models.hr import Employee, VisaFile, GuideAssignment, Vehicle, DispatchOrder, Incident, PayrollRun, DEPARTMENTS, POSITIONS, OFFICES
from app.services import hr as H
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["nhan-su"])
HR_WRITE = ("hcns", "cntt")
HR_READ = ("hcns", "cntt", "ketoan", "tgd", "chutich", "bks", "tp_dh", "gd_kd", "ptgd_doan")


def emp_out(e: Employee) -> dict:
    return {"id": e.id, "code": e.code, "user_id": e.user_id, "full_name": e.full_name, "department": e.department, "department_name": DEPARTMENTS.get(e.department, e.department),
            "position": e.position, "position_name": POSITIONS.get(e.position, e.position), "office": e.office, "office_name": OFFICES.get(e.office, e.office),
            "contract_type": e.contract_type, "base_salary": e.base_salary, "start_date": e.start_date, "probation": e.probation, "transition_list": e.transition_list,
            "card_no": e.card_no, "card_type": e.card_type, "card_expiry": e.card_expiry, "member_org": e.member_org, "ctv_contract": e.ctv_contract,
            "advance_limit": e.advance_limit, "active": e.active, "guide_ok": H.guide_eligible(e, date.today())[0] if e.department == "huong_dan" else None}


@router.get("/hr/meta")
def hr_meta(u: User = Depends(current_user)):
    return {"departments": DEPARTMENTS, "positions": POSITIONS, "offices": OFFICES}


# ---------- Hồ sơ nhân sự ----------
@router.get("/employees")
def employees(department: str | None = None, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    q = select(Employee).order_by(Employee.department, Employee.code)
    if department: q = q.where(Employee.department == department)
    return [emp_out(e) for e in db.execute(q).scalars()]


class EmployeeIn(BaseModel):
    full_name: str
    department: str
    position: str = "nv"
    office: str = "hcm"
    contract_type: str = "hdld"
    base_salary: float = 0
    user_id: int | None = None
    start_date: date | None = None
    probation: bool = False
    card_no: str = ""
    card_type: str = ""
    card_expiry: date | None = None
    member_org: bool = False
    ctv_contract: bool = False
    advance_limit: float = 0


@router.post("/employees", status_code=201)
def create_employee(data: EmployeeIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    if data.department not in DEPARTMENTS or data.position not in POSITIONS: raise HTTPException(422, "Phòng/chức danh không hợp lệ")
    e = Employee(code=H.next_code(db, Employee, "NS"), **data.model_dump())
    db.add(e); db.flush()
    R.audit(db, u.username, u.role, "tao_ho_so_nhan_su", f"emp:{e.code}", after={"ten": e.full_name, "phong": e.department, "luong": e.base_salary})
    db.commit(); db.refresh(e)
    return {"employee": emp_out(e), "message": f"Đã tạo hồ sơ {e.code}"}


@router.put("/employees/{eid}")
def update_employee(eid: int, data: EmployeeIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    e = db.get(Employee, eid)
    if not e: raise HTTPException(404, "Không có hồ sơ")
    before = {"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department}
    for k, v in data.model_dump().items(): setattr(e, k, v)
    R.audit(db, u.username, u.role, "sua_ho_so_nhan_su", f"emp:{e.code}", before=before, after={"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department})
    db.commit()
    return {"employee": emp_out(e), "message": "Đã cập nhật (tăng lương/điều chỉnh nhân sự cần Chủ tịch duyệt theo Điều 9 – ghi nhật ký)"}


# ---------- Hồ sơ visa ----------
@router.get("/visa")
def visa_list(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [{"id": f.id, "code": f.code, "customer_name": f.customer_name, "market": f.market, "method": f.method, "handler_id": f.handler_id, "handler": emps.get(f.handler_id, ""),
             "office": f.office, "alliance": f.alliance, "tour_id": f.tour_id, "revenue": f.revenue, "status": f.status, "completed_at": f.completed_at}
            for f in db.execute(select(VisaFile).order_by(desc(VisaFile.id))).scalars()]


class VisaIn(BaseModel):
    customer_name: str
    market: str
    method: str = "tu_xu_ly"
    handler_id: int
    office: str = "hcm"
    alliance: bool = False
    tour_id: int | None = None
    revenue: float = 0


@router.post("/visa", status_code=201)
def visa_create(data: VisaIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    if data.method not in ("tu_xu_ly", "gui_doi_tac"): raise HTTPException(422, "Cách xử lý: tu_xu_ly / gui_doi_tac")
    f = VisaFile(code=H.next_code(db, VisaFile, "VS"), **data.model_dump())
    db.add(f); db.flush()
    R.audit(db, u.username, u.role, "tao_ho_so_visa", f"visa:{f.code}", after=data.model_dump(mode="json"))
    db.commit()
    return {"message": f"Đã tạo hồ sơ {f.code}"}


@router.post("/visa/{vid}/complete")
def visa_complete(vid: int, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    f = db.get(VisaFile, vid)
    if not f: raise HTTPException(404, "Không có hồ sơ")
    if f.status == "hoan_thanh": raise HTTPException(422, "Hồ sơ đã hoàn thành")
    f.status, f.completed_at = "hoan_thanh", date.today()
    R.audit(db, u.username, u.role, "hoan_thanh_visa", f"visa:{f.code}", after={"thang": f"{f.completed_at:%Y-%m}", "cach": f.method})
    db.commit()
    return {"message": f"{f.code} hoàn thành – tính quỹ visa tháng {f.completed_at:%m/%Y}"}


# ---------- HDV & phân chuyến (cổng 13) ----------
@router.get("/guide-assignments")
def assignments(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    out = []
    for a in db.execute(select(GuideAssignment).order_by(desc(GuideAssignment.id))).scalars():
        t = db.get(Tour, a.tour_id)
        out.append({"id": a.id, "tour_id": a.tour_id, "tour_code": t.code if t else "", "tour_name": t.name if t else "", "guide_id": a.guide_id, "guide": emps.get(a.guide_id, ""),
                    "days": a.days, "rate_per_day": a.rate_per_day, "holiday": a.holiday, "amount": a.rate_per_day * a.days * (2 if a.holiday else 1),
                    "assigned_by": a.assigned_by, "assigned_at": a.assigned_at, "confirmed_at": a.confirmed_at, "report_submitted": a.report_submitted,
                    "advance_settled": a.advance_settled, "status": a.status})
    return out


class AssignIn(BaseModel):
    tour_id: int
    guide_id: int
    days: int
    rate_per_day: float
    holiday: bool = False


@router.post("/guide-assignments", status_code=201)
def assign(data: AssignIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    e = db.get(Employee, data.guide_id); t = db.get(Tour, data.tour_id)
    if not e or not t: raise HTTPException(404, "Không có HDV hoặc tour")
    ok, why = H.guide_eligible(e, t.start_date)
    if not ok: raise HTTPException(422, {"gate": "CONG_13", "message": f"Không phân chuyến: {why}"})
    a = GuideAssignment(**data.model_dump(), assigned_by=u.username)
    db.add(a); db.flush()
    R.audit(db, u.username, u.role, "phan_cong_hdv", f"tour:{t.code}", after={"hdv": e.full_name, "ngay": data.days, "don_gia": data.rate_per_day})
    db.commit()
    return {"message": f"Đã lập văn bản phân công {e.full_name} dẫn {t.code} – HDV xác nhận trong 24 giờ"}


class AssignUpdate(BaseModel):
    confirm: bool | None = None
    report_submitted: bool | None = None
    advance_settled: bool | None = None


@router.post("/guide-assignments/{aid}/update")
def assign_update(aid: int, data: AssignUpdate, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt", "ketoan")), db: Session = Depends(get_db)):
    a = db.get(GuideAssignment, aid)
    if not a: raise HTTPException(404, "Không có phân công")
    if data.confirm: a.status, a.confirmed_at = "da_xac_nhan", datetime.now()
    if data.report_submitted is not None: a.report_submitted = data.report_submitted
    if data.advance_settled is not None: a.advance_settled = data.advance_settled
    R.audit(db, u.username, u.role, "cap_nhat_phan_cong_hdv", f"assign:{a.id}", after=data.model_dump(exclude_none=True, mode="json"))
    db.commit()
    return {"message": "Đã cập nhật"}


# ---------- Đội xe ----------
@router.get("/vehicles")
def vehicles(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [{"id": v.id, "plate": v.plate, "seats": v.seats, "driver_id": v.driver_id, "driver": emps.get(v.driver_id, ""), "internal_rate_per_day": v.internal_rate_per_day, "active": v.active}
            for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars()]


class VehicleIn(BaseModel):
    plate: str
    seats: int = 45
    driver_id: int | None = None
    internal_rate_per_day: float = 0


@router.post("/vehicles", status_code=201)
def vehicle_create(data: VehicleIn, u: User = Depends(require_roles("cntt", "hcns")), db: Session = Depends(get_db)):
    v = Vehicle(**data.model_dump()); db.add(v); db.flush()
    R.audit(db, u.username, u.role, "tao_xe", f"vehicle:{v.plate}", after=data.model_dump(mode="json")); db.commit()
    return {"message": f"Đã thêm xe {v.plate}"}


@router.get("/dispatch")
def dispatch_list(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    out = []
    for d in db.execute(select(DispatchOrder).order_by(desc(DispatchOrder.id))).scalars():
        t = db.get(Tour, d.tour_id)
        out.append({"id": d.id, "tour_code": t.code if t else "", "vehicle": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "date_from": d.date_from, "date_to": d.date_to,
                    "days": (d.date_to - d.date_from).days + 1, "internal_price": d.internal_price, "status": d.status, "created_by": d.created_by, "confirmed_at": d.confirmed_at, "incident_note": d.incident_note})
    return out


class DispatchIn(BaseModel):
    tour_id: int
    vehicle_id: int
    date_from: date
    date_to: date
    internal_price: float = 0


@router.post("/dispatch", status_code=201)
def dispatch_create(data: DispatchIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    v = db.get(Vehicle, data.vehicle_id); t = db.get(Tour, data.tour_id)
    if not v or not t: raise HTTPException(404, "Không có xe hoặc tour")
    if not v.driver_id: raise HTTPException(422, "Xe chưa gán tài xế")
    if data.date_to < data.date_from: raise HTTPException(422, "Ngày không hợp lệ")
    price = data.internal_price or v.internal_rate_per_day * ((data.date_to - data.date_from).days + 1)
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=v.driver_id, date_from=data.date_from, date_to=data.date_to, internal_price=price, created_by=u.username)
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "lenh_dieu_xe", f"tour:{t.code}", after={"xe": v.plate, "tu": str(data.date_from), "den": str(data.date_to), "gia_noi_bo": price})
    db.commit()
    return {"message": f"Đã lập lệnh điều xe {v.plate} cho {t.code} – Đội xe xác nhận trong 4 giờ"}


class DispatchUpdate(BaseModel):
    status: str
    incident_note: str = ""


@router.post("/dispatch/{did}/update")
def dispatch_update(did: int, data: DispatchUpdate, u: User = Depends(require_roles("cntt", "tp_dh", "nv_dh", "hcns")), db: Session = Depends(get_db)):
    d = db.get(DispatchOrder, did)
    if not d: raise HTTPException(404, "Không có lệnh")
    if data.status not in ("da_xac_nhan", "hoan_thanh", "huy"): raise HTTPException(422, "Trạng thái không hợp lệ")
    if data.status == "da_xac_nhan": d.confirmed_at = datetime.now()
    d.status = data.status; d.incident_note = data.incident_note or d.incident_note
    R.audit(db, u.username, u.role, "cap_nhat_lenh_dieu_xe", f"dispatch:{d.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã cập nhật lệnh điều xe"}


@router.get("/fleet/summary")
def fleet_summary(period: str, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    """Trung tâm lợi nhuận Đội xe: doanh thu nội bộ và số ngày tour tài xế trong tháng (CNTT quyết toán)."""
    y, m = map(int, period.split("-"))
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    rows = {}
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.status.in_(["da_xac_nhan", "hoan_thanh"]))).scalars():
        if d.date_to.year == y and d.date_to.month == m:
            r = rows.setdefault(d.vehicle_id, {"vehicle": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "trips": 0, "days": 0, "revenue": 0.0})
            r["trips"] += 1; r["days"] += (d.date_to - d.date_from).days + 1; r["revenue"] += d.internal_price
    ctp = R.get_param(db, "tai_xe_cong_tac_phi")
    for r in rows.values(): r["driver_allowance"] = r["days"] * ctp
    return {"period": period, "rows": list(rows.values()), "total_revenue": sum(r["revenue"] for r in rows.values())}


# ---------- Sự vụ ----------
@router.get("/incidents")
def incidents(u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [{"id": i.id, "employee_id": i.employee_id, "employee": emps.get(i.employee_id, ""), "tour_id": i.tour_id, "level": i.level, "description": i.description,
             "occurred_on": i.occurred_on, "confirmed_by": i.confirmed_by, "created_by": i.created_by} for i in db.execute(select(Incident).order_by(desc(Incident.id))).scalars()]


class IncidentIn(BaseModel):
    employee_id: int
    level: int
    description: str
    occurred_on: date
    tour_id: int | None = None


@router.post("/incidents", status_code=201)
def incident_create(data: IncidentIn, u: User = Depends(require_roles("hcns", "tp_dh", "gd_kd", "ptgd_doan", "tgd", "cntt")), db: Session = Depends(get_db)):
    if not 1 <= data.level <= 4: raise HTTPException(422, "Mức sự vụ 1–4")
    i = Incident(**data.model_dump(), created_by=u.username, confirmed_by=u.username if u.role == "hcns" else "")
    db.add(i); db.flush()
    R.audit(db, u.username, u.role, "ghi_nhan_su_vu", f"incident:{i.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã ghi nhận sự vụ" + ("" if i.confirmed_by else " – chờ HCNS xác nhận")}


@router.post("/incidents/{iid}/confirm")
def incident_confirm(iid: int, u: User = Depends(require_roles("hcns")), db: Session = Depends(get_db)):
    i = db.get(Incident, iid)
    if not i: raise HTTPException(404, "Không có sự vụ")
    i.confirmed_by = u.username
    R.audit(db, u.username, u.role, "hcns_xac_nhan_su_vu", f"incident:{i.id}", after={"muc": i.level}); db.commit()
    return {"message": "HCNS đã xác nhận sự vụ"}


# ---------- Bảng lương ----------
def run_out(r: PayrollRun) -> dict:
    return {"id": r.id, "period": r.period, "status": r.status, "rows": r.rows, "totals": r.totals, "kt_confirmed_by": r.kt_confirmed_by, "kt_confirmed_at": r.kt_confirmed_at,
            "hcns_by": r.hcns_by, "hcns_at": r.hcns_at, "tgd_by": r.tgd_by, "tgd_at": r.tgd_at, "entry_ids": r.entry_ids, "updated_at": r.updated_at}


@router.get("/payroll-runs/{period}")
def payroll_run(period: str, refresh: bool = False, u: User = Depends(require_roles("ketoan", "hcns", "tgd", "chutich", "cntt", "bks")), db: Session = Depends(get_db)):
    try:
        return run_out(H.get_or_draft(db, period, refresh=refresh))
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/payroll-runs/{period}/advance")
def payroll_advance(period: str, u: User = Depends(require_roles("ketoan", "hcns", "tgd")), db: Session = Depends(get_db)):
    run = H.get_or_draft(db, period)
    try:
        msg = H.advance(db, u, run)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg, "run": run_out(run)}
