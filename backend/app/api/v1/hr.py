"""API nhân sự – lương: hồ sơ, visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương (robot R6)."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Tour, User, Company
from app.models.hr import SALES_GROUPS, Employee, VisaFile, GuideAssignment, Vehicle, VehicleRate, DispatchOrder, Incident, PayrollRun, GuideRate, INCIDENT_LEVELS, INCIDENT_STATUS, DEPARTMENTS, POSITIONS, OFFICES
from app.services import hr as H
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["nhan-su"])
HR_WRITE = ("hcns", "cntt")
HR_READ = ("hcns", "cntt", "ketoan", "tgd", "chutich", "bks", "tp_dh", "gd_kd", "tp_kd", "ptgd_doan")


def emp_out(e: Employee) -> dict:
    return {"id": e.id, "code": e.code, "user_id": e.user_id, "full_name": e.full_name, "department": e.department, "department_name": DEPARTMENTS.get(e.department, e.department),
            "position": e.position, "position_name": POSITIONS.get(e.position, e.position), "title": e.title, "sales_group": e.sales_group, "office": e.office, "office_name": OFFICES.get(e.office, e.office),
            "contract_type": e.contract_type, "base_salary": e.base_salary, "start_date": e.start_date, "probation": e.probation, "transition_list": e.transition_list,
            "card_no": e.card_no, "card_type": e.card_type, "card_expiry": e.card_expiry, "member_org": e.member_org, "ctv_contract": e.ctv_contract,
            "advance_limit": e.advance_limit, "active": e.active, "company_id": e.company_id,
            "guide_ok": H.guide_eligible(e, date.today())[0] if e.department == "huong_dan" else None}


@router.get("/hr/meta")
def hr_meta(u: User = Depends(current_user)):
    return {"departments": DEPARTMENTS, "positions": POSITIONS, "offices": OFFICES}


# ---------- Hồ sơ nhân sự ----------
@router.get("/employees")
def employees(department: str | None = None, u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
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


@router.get("/staff")
def staff_directory(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh bạ nhân viên (mã NV, họ tên, phòng, nhóm) – mọi người đăng nhập đều xem được để chọn người/ghi báo cáo."""
    from app.services import staff as STF
    return {"rows": STF.staff_directory(db), "departments": DEPARTMENTS, "groups": SALES_GROUPS}


@router.post("/employees/import-master")
def import_master(reset_passwords: bool = False, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """Nạp danh sách nhân viên chính thức từ bảng lương HCNS (app/data/nhan_su_*.json): mã NV, phòng, nhóm, chức vụ; ghép/tạo tài khoản.
    reset_passwords=true: đặt lại mật khẩu mọi tài khoản trong danh sách = mã NV (trừ Chủ tịch/TGĐ/CNTT) – dùng khi cấp tài khoản lần đầu."""
    from app.services import staff as STF
    st = STF.import_master(db, u, reset_passwords=reset_passwords)
    return {"message": f"Đã nạp: cập nhật {st['updated']}, tạo mới {st['created']} hồ sơ; ghép {st['users_linked']} tài khoản, tạo {st['users_created']} tài khoản mới" + (f", đặt lại {st['passwords_reset']} mật khẩu = mã NV" if reset_passwords else ""), **st}


class ResetPwIn(BaseModel):
    new_password: str = ""      # trống = mã NV


@router.post("/users/{uid}/reset-password")
def reset_password(uid: int, data: ResetPwIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """HCNS/CNTT đặt lại mật khẩu cho một tài khoản (mặc định = mã NV)."""
    from app.core.security import hash_password
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if t.role in ("chutich", "tgd") and u.role != "cntt": raise HTTPException(403, "Chỉ CNTT đặt lại mật khẩu lãnh đạo")
    pw = data.new_password.strip() or t.staff_code
    if not pw or len(pw) < 3: raise HTTPException(422, "Chưa có mã NV – nhập mật khẩu mới")
    t.password_hash = hash_password(pw)
    R.audit(db, u.username, u.role, "dat_lai_mat_khau", f"user:{t.username}"); db.commit()
    return {"message": f"Đã đặt lại mật khẩu cho {t.full_name} ({t.username})" + (" = mã NV" if not data.new_password.strip() else "")}


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
    rate_id: int | None = None
    tour_id: int
    guide_id: int
    days: int
    rate_per_day: float
    holiday: bool = False
    rate_id: int | None = None


@router.post("/guide-assignments", status_code=201)
def assign(data: AssignIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    e = db.get(Employee, data.guide_id); t = db.get(Tour, data.tour_id)
    if not e or not t: raise HTTPException(404, "Không có HDV hoặc tour")
    ok, why = H.guide_eligible(e, t.start_date)
    if not ok: raise HTTPException(422, {"gate": "CONG_13", "message": f"Không phân chuyến: {why}"})
    a = GuideAssignment(**data.model_dump(), assigned_by=u.username)
    if data.rate_id:
        gr = db.get(GuideRate, data.rate_id)
        if not gr or gr.status != "active": raise HTTPException(422, "Tuyến không có trong bảng giá HDV hiệu lực")
        a.rate_per_day = gr.rate_per_day
        if not data.days or data.days <= 0: a.days = max(1, int(round(gr.days)))
    if a.rate_per_day <= 0: raise HTTPException(422, "Chọn tuyến trong bảng giá HDV hoặc nhập đơn giá/ngày")
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
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    return [{"id": v.id, "plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "driver": emps.get(v.driver_id, ""),
             "internal_rate_per_day": v.internal_rate_per_day, "active": v.active, "company_id": v.company_id,
             "company": cos[v.company_id].name if v.company_id in cos else "", "company_code": cos[v.company_id].code if v.company_id in cos else ""}
            for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars()]


class VehicleIn(BaseModel):
    plate: str
    seats: int = 45
    kind: str = "noi_bo"
    driver_id: int | None = None
    internal_rate_per_day: float = 0


@router.post("/vehicles", status_code=201)
def vehicle_create(data: VehicleIn, u: User = Depends(require_roles("cntt", "hcns")), db: Session = Depends(get_db)):
    v = Vehicle(**data.model_dump()); db.add(v); db.flush()
    R.audit(db, u.username, u.role, "tao_xe", f"vehicle:{v.plate}", after=data.model_dump(mode="json")); db.commit()
    return {"message": f"Đã thêm xe {v.plate}"}


# ---------- Bảng giá xe nội bộ (master data, Chủ tịch + TGĐ duyệt) ----------
def rate_out(r: VehicleRate) -> dict:
    return {"id": r.id, "route": r.route, "days": r.days, "internal_price": r.internal_price, "partner_price": r.partner_price, "effective_from": r.effective_from,
            "status": r.status, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "note": r.note, "proposed_by": r.proposed_by}


# ---------- Bảng giá HDV theo tuyến ----------
def grate_out(r: GuideRate) -> dict:
    return {"id": r.id, "route": r.route, "days": r.days, "rate_per_day": r.rate_per_day, "old_rate_per_day": r.old_rate_per_day, "effective_from": r.effective_from,
            "status": r.status, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "note": r.note, "proposed_by": r.proposed_by}


@router.get("/guide-rates")
def guide_rates(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [grate_out(r) for r in db.execute(select(GuideRate).order_by(GuideRate.status.desc(), GuideRate.id)).scalars()]


class GuideRateIn(BaseModel):
    route: str
    days: float = 0
    rate_per_day: float
    old_rate_per_day: float = 0
    effective_from: date
    note: str = ""


@router.post("/guide-rates", status_code=201)
def guide_rate_propose(data: GuideRateIn, u: User = Depends(require_roles("cntt", "hcns", "tp_dh")), db: Session = Depends(get_db)):
    r = GuideRate(**data.model_dump(), proposed_by=u.username); db.add(r); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_gia_hdv", f"grate:{r.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": f"Đã trình đơn giá HDV tuyến {r.route} – chờ Chủ tịch + TGĐ ký"}


@router.post("/guide-rates/{rid}/sign")
def guide_rate_sign(rid: int, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    r = db.get(GuideRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    if u.role == "chutich": r.signed_chutich = True
    else: r.signed_tgd = True
    if r.signed_chutich and r.signed_tgd:
        for old in db.execute(select(GuideRate).where(GuideRate.route == r.route, GuideRate.status == "active", GuideRate.id != r.id)).scalars():
            if old.effective_from <= r.effective_from: old.status = "rejected"; old.note = (old.note + f" | thay bởi #{r.id}")[:200]
        r.status = "active"
    R.audit(db, u.username, u.role, "ky_gia_hdv", f"grate:{r.id}", after={"trang_thai": r.status}); db.commit()
    return {"message": "Đã ký" + (" – đơn giá có hiệu lực" if r.status == "active" else ", chờ chữ ký còn lại")}


@router.get("/vehicle-rates")
def vehicle_rates(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [rate_out(r) for r in db.execute(select(VehicleRate).order_by(VehicleRate.status.desc(), VehicleRate.id)).scalars()]


class RateIn(BaseModel):
    route: str
    days: int = 0
    internal_price: float
    partner_price: float = 0
    effective_from: date
    note: str = ""


@router.post("/vehicle-rates", status_code=201)
def rate_propose(data: RateIn, u: User = Depends(require_roles("cntt", "hcns", "tp_dh")), db: Session = Depends(get_db)):
    r = VehicleRate(**data.model_dump(), proposed_by=u.username); db.add(r); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_gia_xe", f"rate:{r.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": f"Đã trình giá tuyến {r.route} – chờ Chủ tịch + TGĐ ký"}


@router.post("/vehicle-rates/{rid}/sign")
def rate_sign(rid: int, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    r = db.get(VehicleRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    if u.role == "chutich": r.signed_chutich = True
    else: r.signed_tgd = True
    if r.signed_chutich and r.signed_tgd:
        for old in db.execute(select(VehicleRate).where(VehicleRate.route == r.route, VehicleRate.status == "active", VehicleRate.id != r.id)).scalars():
            if old.effective_from <= r.effective_from: old.status = "rejected"; old.note = (old.note + f" | thay bởi #{r.id}")[:200]
        r.status = "active"
    R.audit(db, u.username, u.role, "ky_gia_xe", f"rate:{r.id}", after={"trang_thai": r.status}); db.commit()
    return {"message": "Đã ký" + (" – bảng giá có hiệu lực" if r.status == "active" else ", chờ chữ ký còn lại")}


def _owner(v, cos: dict) -> dict:
    """Xe của một pháp nhân trong phạm vi hợp nhất → lệnh điều xe là giao dịch nội bộ, phải loại trừ khi hợp nhất."""
    c = cos.get(v.company_id) if v is not None and v.company_id else None
    return {"company": c.name if c else "", "company_code": c.code if c else "",
            "noi_bo": bool(c and c.in_group()),
            "canh_bao": "" if c else "Xe chưa gán công ty chủ quản – chưa xác định được đây có phải giao dịch nội bộ hay không"}


@router.get("/dispatch")
def dispatch_list(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    vobj = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    veh = {i: v.plate for i, v in vobj.items()}
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    out = []
    for d in db.execute(select(DispatchOrder).order_by(desc(DispatchOrder.id))).scalars():
        t = db.get(Tour, d.tour_id)
        rt = db.get(VehicleRate, d.rate_id) if d.rate_id else None
        out.append({"id": d.id, "tour_code": t.code if t else "", "vehicle": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "date_from": d.date_from, "date_to": d.date_to, "route": rt.route if rt else "",
                    "days": (d.date_to - d.date_from).days + 1, "internal_price": d.internal_price, "status": d.status, "created_by": d.created_by, "confirmed_at": d.confirmed_at, "incident_note": d.incident_note,
                    **_owner(vobj.get(d.vehicle_id), cos)})
    return out


class DispatchIn(BaseModel):
    tour_id: int
    vehicle_id: int
    date_from: date
    date_to: date
    rate_id: int | None = None
    internal_price: float = 0


@router.post("/dispatch", status_code=201)
def dispatch_create(data: DispatchIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    v = db.get(Vehicle, data.vehicle_id); t = db.get(Tour, data.tour_id)
    if not v or not t: raise HTTPException(404, "Không có xe hoặc tour")
    if data.date_to < data.date_from: raise HTTPException(422, "Ngày không hợp lệ")
    rt = db.get(VehicleRate, data.rate_id) if data.rate_id else None
    if rt and rt.status != "active": raise HTTPException(422, "Tuyến trong bảng giá chưa được Chủ tịch + TGĐ duyệt")
    if rt:
        price = rt.partner_price if v.kind == "hop_tac" else rt.internal_price
        if price <= 0: raise HTTPException(422, f"Tuyến {rt.route} không có giá cho loại xe {v.kind}")
    else:
        price = data.internal_price or v.internal_rate_per_day * ((data.date_to - data.date_from).days + 1)
    if v.kind != "hop_tac" and not v.driver_id: raise HTTPException(422, "Xe chưa gán tài xế")
    driver_id = v.driver_id
    if not driver_id:   # xe hợp tác: tài xế của đối tác – ghi vào hồ sơ xe khi có; tạm gắn người lập lệnh để theo dõi
        drv = db.execute(select(Employee).where(Employee.department == "doi_xe").order_by(Employee.id)).scalars().first()
        if not drv: raise HTTPException(422, "Chưa có hồ sơ tài xế")
        driver_id = drv.id
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=driver_id, date_from=data.date_from, date_to=data.date_to, rate_id=rt.id if rt else None, internal_price=price, created_by=u.username)
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "lenh_dieu_xe", f"tour:{t.code}", after={"xe": v.plate, "tuyen": rt.route if rt else "", "tu": str(data.date_from), "den": str(data.date_to), "gia_noi_bo": price})
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
def fleet_summary(period: str, u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
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
@router.get("/incident-levels")
def incident_levels(u: User = Depends(current_user)):
    return {"levels": INCIDENT_LEVELS, "status": INCIDENT_STATUS, "quy_trinh": "Trưởng bộ phận lập biên bản → HCNS xác nhận (≥ mức 2) → duyệt (mức 2: GĐ KD/PTGĐ; mức 3: Chủ tịch + TGĐ) → 3 ngày làm việc khiếu nại (treo chế tài) → hiệu lực"}


def inc_out(i: Incident, emps: dict, my_emp_ids: set | None = None) -> dict:
    return {"id": i.id, "is_mine": bool(my_emp_ids and i.employee_id in my_emp_ids), "employee_id": i.employee_id, "employee": emps.get(i.employee_id, ""), "tour_id": i.tour_id, "level": i.level, "level_name": INCIDENT_LEVELS.get(i.level, {}).get("ten", f"Mức {i.level}"),
            "description": i.description, "occurred_on": i.occurred_on, "confirmed_by": i.confirmed_by, "created_by": i.created_by, "status": i.status, "status_name": INCIDENT_STATUS.get(i.status, i.status),
            "approved_by": i.approved_by, "approved_at": i.approved_at, "employee_opinion": i.employee_opinion, "appeal_note": i.appeal_note, "appeal_result": i.appeal_result, "effective_at": i.effective_at,
            "appeal_deadline": (H.add_working_days(i.approved_at.date(), 3) if i.approved_at else None)}


@router.get("/incidents")
def incidents(u: User = Depends(require_roles(*HR_READ, "nv_kd", "nv_dh", "hdv")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows = db.execute(select(Incident).order_by(desc(Incident.id))).scalars().all()
    mine = {e.id for e in db.execute(select(Employee).where(Employee.user_id == u.id)).scalars()}
    if u.role in ("nv_kd", "nv_dh", "hdv"):   # nhân viên chỉ xem sự vụ của mình
        rows = [i for i in rows if i.employee_id in mine]
    return [inc_out(i, emps, mine) for i in rows]


class IncidentIn(BaseModel):
    employee_id: int
    level: int
    description: str
    occurred_on: date
    tour_id: int | None = None


@router.post("/incidents", status_code=201)
def incident_create(data: IncidentIn, u: User = Depends(require_roles("hcns", "tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "tgd", "cntt", "tp")), db: Session = Depends(get_db)):
    """Trưởng bộ phận nơi phát sinh lập biên bản (TP KD với tour lẻ, PTGĐ đoàn với Phòng Đoàn, TP ĐH với Điều hành, phụ trách Phòng HD với HDV)."""
    if data.level not in INCIDENT_LEVELS: raise HTTPException(422, "Mức sự vụ 1–3 theo bảng phân mức")
    i = Incident(**data.model_dump(), created_by=u.username)
    if data.level == 1: i.status, i.effective_at = "hieu_luc", datetime.now()     # mức 1: nhắc nhở, ghi hồ sơ – không chế tài
    elif u.role == "hcns": i.confirmed_by, i.status = u.username, "hcns_xac_nhan"
    db.add(i); db.flush()
    R.audit(db, u.username, u.role, "lap_bien_ban_su_vu", f"incident:{i.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã lập biên bản sự vụ" + ("" if i.status != "lap" else " – chờ HCNS xác nhận")}


@router.post("/incidents/{iid}/confirm")
def incident_confirm(iid: int, u: User = Depends(require_roles("hcns")), db: Session = Depends(get_db)):
    i = db.get(Incident, iid)
    if not i or i.status != "lap": raise HTTPException(404, "Không có sự vụ chờ HCNS xác nhận")
    i.confirmed_by, i.status = u.username, "hcns_xac_nhan"
    R.audit(db, u.username, u.role, "hcns_xac_nhan_su_vu", f"incident:{i.id}"); db.commit()
    return {"message": "HCNS đã xác nhận – chờ cấp có thẩm quyền duyệt"}


@router.post("/incidents/{iid}/approve")
def incident_approve(iid: int, u: User = Depends(require_roles("gd_kd", "ptgd_doan", "tgd", "chutich")), db: Session = Depends(get_db)):
    i = db.get(Incident, iid)
    if not i or i.status != "hcns_xac_nhan": raise HTTPException(404, "Sự vụ chưa được HCNS xác nhận hoặc đã duyệt")
    allowed = INCIDENT_LEVELS[i.level]["duyet"]
    if u.role not in allowed: raise HTTPException(403, f"Mức {i.level} do {', '.join(allowed)} duyệt")
    signers = [x for x in i.approved_by.split(",") if x]
    if u.username not in signers: signers.append(u.username)
    i.approved_by = ",".join(signers)
    need2 = i.level >= 3
    roles_signed = {db.execute(select(User).where(User.username == x)).scalars().first().role for x in signers}
    if not need2 or ({"chutich", "tgd"} <= roles_signed):
        i.status, i.approved_at = "cho_khieu_nai", datetime.now()
    R.audit(db, u.username, u.role, "duyet_su_vu", f"incident:{i.id}", after={"trang_thai": i.status}); db.commit()
    return {"message": "Đã duyệt – người bị lập biên bản có 3 ngày làm việc để khiếu nại" if i.status == "cho_khieu_nai" else "Đã ký, chờ chữ ký còn lại (mức 3 cần Chủ tịch + TGĐ)"}


class OpinionIn(BaseModel):
    opinion: str = ""
    appeal: str = ""


@router.post("/incidents/{iid}/opinion")
def incident_opinion(iid: int, data: OpinionIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Người bị lập biên bản ghi ý kiến; khiếu nại trong 3 ngày làm việc kể từ khi duyệt → treo chế tài."""
    i = db.get(Incident, iid)
    if not i: raise HTTPException(404, "Không có sự vụ")
    e = db.get(Employee, i.employee_id)
    if not e or e.user_id != u.id: raise HTTPException(403, "Chỉ người bị lập biên bản được ghi ý kiến")
    if data.opinion: i.employee_opinion = data.opinion[:300]
    if data.appeal:
        if i.status not in ("lap", "hcns_xac_nhan", "cho_khieu_nai"): raise HTTPException(422, "Đã hết thời hạn khiếu nại hoặc sự vụ đã kết thúc")
        if i.status == "cho_khieu_nai" and i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3): raise HTTPException(422, "Quá 3 ngày làm việc kể từ khi duyệt")
        i.appeal_note = data.appeal[:300]
        if i.status == "cho_khieu_nai": i.status = "khieu_nai"
    R.audit(db, u.username, u.role, "y_kien_su_vu", f"incident:{i.id}", after=data.model_dump()); db.commit()
    return {"message": "Đã ghi nhận" + (" – chế tài treo cho tới khi cấp trên kết luận" if i.status == "khieu_nai" else "")}


class ResolveIn(BaseModel):
    accept: bool          # true = chấp nhận khiếu nại (hủy chế tài)
    result: str = ""


@router.post("/incidents/{iid}/resolve")
def incident_resolve(iid: int, data: ResolveIn, u: User = Depends(require_roles("gd_kd", "ptgd_doan", "tgd", "chutich")), db: Session = Depends(get_db)):
    """Cấp trên một bậc kết luận khiếu nại; hoặc chốt hiệu lực khi hết hạn khiếu nại."""
    i = db.get(Incident, iid)
    if not i or i.status not in ("khieu_nai", "cho_khieu_nai"): raise HTTPException(404, "Sự vụ không ở trạng thái chờ kết luận")
    if i.status == "cho_khieu_nai" and data.accept: raise HTTPException(422, "Không có khiếu nại để chấp nhận")
    i.appeal_result = data.result[:300]
    if data.accept: i.status = "huy"
    else: i.status, i.effective_at = "hieu_luc", datetime.now()
    R.audit(db, u.username, u.role, "ket_luan_su_vu", f"incident:{i.id}", after={"chap_nhan": data.accept, "ket_luan": data.result}); db.commit()
    return {"message": "Khiếu nại được chấp nhận – hủy chế tài" if data.accept else "Sự vụ có hiệu lực – chế tài áp dụng kỳ lương tháng phát sinh"}


@router.post("/robot/incidents/finalize")
def robot_incidents_finalize(x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    from app.core.config import settings
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    n = 0
    for i in db.execute(select(Incident).where(Incident.status == "cho_khieu_nai")).scalars():
        if i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3): i.status, i.effective_at = "hieu_luc", datetime.now(); n += 1
    R.audit(db, "robot", "robot", "chot_su_vu_het_han_khieu_nai", "incidents", after={"so_luong": n}); db.commit()
    return {"count": n}


@router.post("/incidents/finalize-expired")
def incidents_finalize(u: User = Depends(require_roles("hcns", "cntt")), db: Session = Depends(get_db)):
    """Robot/HCNS: sự vụ đã duyệt, quá 3 ngày làm việc không khiếu nại → hiệu lực."""
    n = 0
    for i in db.execute(select(Incident).where(Incident.status == "cho_khieu_nai")).scalars():
        if i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3):
            i.status, i.effective_at = "hieu_luc", datetime.now(); n += 1
    R.audit(db, u.username, u.role, "chot_su_vu_het_han_khieu_nai", "incidents", after={"so_luong": n}); db.commit()
    return {"message": f"Đã chốt hiệu lực {n} sự vụ", "count": n}


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
