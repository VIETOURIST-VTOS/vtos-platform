"""API nhân sự – lương: hồ sơ, visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương (robot R6)."""
import json
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, ConfigDict
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
            "position": e.position, "position_name": POSITIONS.get(e.position, e.position), "title": e.title, "duties": e.duties, "sales_group": e.sales_group, "office": e.office, "office_name": OFFICES.get(e.office, e.office),
            "contract_type": e.contract_type, "base_salary": e.base_salary, "start_date": e.start_date, "probation": e.probation, "transition_list": e.transition_list,
            "card_no": e.card_no, "card_type": e.card_type, "card_expiry": e.card_expiry, "member_org": e.member_org, "ctv_contract": e.ctv_contract,
            "advance_limit": e.advance_limit, "active": e.active, "company_id": e.company_id, "birth_date": e.birth_date, "phone": e.phone,
            "bhxh_base": e.bhxh_base, "member_org": e.member_org,
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
    """Sửa hồ sơ chỉ ghi đè những trường được gửi lên (exclude_unset), nên màn hình cũ gửi thiếu
    trường mới sẽ không xóa mất dữ liệu đã nạp (ngày sinh, điện thoại, pháp nhân, chức danh)."""
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
    title: str | None = None
    duties: str | None = None
    sales_group: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    company_id: int | None = None
    active: bool | None = None


@router.get("/staff")
def staff_directory(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh bạ nhân viên (mã NV, họ tên, phòng, nhóm) – mọi người đăng nhập đều xem được để chọn người/ghi báo cáo."""
    from app.services import staff as STF
    return {"rows": STF.staff_directory(db), "departments": DEPARTMENTS, "groups": SALES_GROUPS}


@router.post("/employees/import-master")
def import_master(reset_passwords: bool = False, close_accounts: bool = True, dry_run: bool = False,
                  u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """Nạp danh sách nhân viên chính thức từ bảng lương HCNS (app/data/nhan_su_*.json): mã NV, phòng, nhóm, chức vụ; ghép/tạo tài khoản.
    reset_passwords=true: đặt lại mật khẩu mọi tài khoản trong danh sách = mã NV (trừ Chủ tịch/TGĐ/CNTT) – dùng khi cấp tài khoản lần đầu."""
    from app.services import staff as STF
    st = STF.import_master(db, u, reset_passwords=reset_passwords, close_accounts=close_accounts, dry_run=dry_run)
    return {"message": f"Đã nạp: cập nhật {st['updated']}, tạo mới {st['created']} hồ sơ; ghép {st['users_linked']} tài khoản, tạo {st['users_created']} tài khoản mới" + (f", đặt lại {st['passwords_reset']} mật khẩu = mã NV" if reset_passwords else ""), **st}


class TaiKhoanIn(BaseModel):
    active: bool | None = None
    role: str | None = None


@router.get("/users/khoa")
def users_locked(u: User = Depends(require_roles(*HR_WRITE, "tgd", "chutich", "bks")), db: Session = Depends(get_db)):
    """Tài khoản đang bị khóa. GET /users chỉ trả tài khoản đang hoạt động nên khóa xong là không còn nhìn
    thấy ở đâu – không mở lại được người bị khóa nhầm, cũng không rà được ai đã bị khóa."""
    from app.models.core import ROLES as R_
    rows = db.execute(select(User).where(User.active == False).order_by(User.username)).scalars()
    return [{"id": x.id, "username": x.username, "full_name": x.full_name, "role": x.role,
             "role_name": R_.get(x.role, x.role), "staff_code": x.staff_code, "department": x.department} for x in rows]


@router.put("/users/{uid}")
def update_user(uid: int, data: TaiKhoanIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """Khóa / mở khóa tài khoản và đổi vai trò. Khóa chứ không xóa: nhật ký và chứng từ cũ vẫn phải truy ra
    được người thực hiện."""
    from app.models.core import ROLES as R_
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if t.id == u.id: raise HTTPException(422, "Không tự đổi vai trò hoặc tự khóa tài khoản của mình")
    if t.role in ("chutich", "tgd") and u.role != "cntt": raise HTTPException(403, "Chỉ CNTT thao tác trên tài khoản lãnh đạo")
    if data.role is not None and data.role not in R_: raise HTTPException(422, f"Vai trò không hợp lệ: {data.role}")
    before = {"vai_tro": t.role, "hoat_dong": t.active}
    if data.role is not None: t.role = data.role
    if data.active is not None: t.active = data.active
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"vai_tro": t.role, "hoat_dong": t.active})
    db.commit()
    return {"message": f"Đã cập nhật tài khoản {t.username}" + ("" if t.active else " – đã khóa đăng nhập"),
            "user": {"id": t.id, "username": t.username, "role": t.role, "role_name": R_.get(t.role, t.role), "active": t.active}}


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
    e = Employee(code=H.next_code(db, Employee, "NS"), **data.model_dump(exclude_none=True))
    db.add(e); db.flush()
    R.audit(db, u.username, u.role, "tao_ho_so_nhan_su", f"emp:{e.code}", after={"ten": e.full_name, "phong": e.department, "luong": e.base_salary})
    db.commit(); db.refresh(e)
    return {"employee": emp_out(e), "message": f"Đã tạo hồ sơ {e.code}"}


@router.put("/employees/{eid}")
def update_employee(eid: int, data: EmployeeIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    e = db.get(Employee, eid)
    if not e: raise HTTPException(404, "Không có hồ sơ")
    fields = data.model_dump(exclude_unset=True)
    if fields.get("active") is False and e.active:
        xe = db.execute(select(Vehicle).where(Vehicle.driver_id == e.id, Vehicle.active == True)).scalars().all()
        if xe: raise HTTPException(422, f"{e.full_name} đang là tài xế của xe {', '.join(v.plate for v in xe)} – giao xe cho người khác trước khi ngưng hồ sơ")
    before = {"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department, "dang_lam": e.active}
    for k, v in fields.items(): setattr(e, k, v)
    R.audit(db, u.username, u.role, "sua_ho_so_nhan_su", f"emp:{e.code}", before=before,
            after={"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department, "dang_lam": e.active})
    db.commit()
    ngung = " – hồ sơ đã chuyển sang Ngưng làm việc" if e.active is False else ""
    return {"employee": emp_out(e), "message": "Đã cập nhật (tăng lương/điều chỉnh nhân sự cần Chủ tịch duyệt theo Điều 9 – ghi nhật ký)" + ngung}


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


# ---------- Xe Vietrip & HDV: màn hình của chính người ở hiện trường ----------
@router.get("/xe-hdv/cua-toi")
def xe_hdv_cua_toi(u: User = Depends(require_roles("xe_hdv", "nv_dh", "tp_dh", "hcns", "cntt", "tgd", "chutich", "ketoan", "bks", "ptgd_doan", "ptgd_mkt")),
                   db: Session = Depends(get_db)):
    """Tài xế thấy xe mình đứng tên và lệnh điều xe của mình; HDV thấy phân chuyến và hạn thẻ của mình.

    Chỉ trả về việc của CHÍNH người đăng nhập – không phải bản rút gọn của màn hình Điều hành. Người ở hiện
    trường không có lý do gì phải nhìn thấy hàng đợi của cả đội, và cũng không được thấy giá xe nội bộ.
    """
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is None and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    if e is None:
        raise HTTPException(404, "Tài khoản này chưa gắn với hồ sơ nhân sự – báo HCNS ghép mã nhân viên")

    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    ho_so = {"code": e.code, "full_name": e.full_name, "department": e.department,
             "department_name": DEPARTMENTS.get(e.department, e.department),
             "position_name": POSITIONS.get(e.position, e.position), "phone": e.phone, "birth_date": e.birth_date}

    xe = [{"id": v.id, "plate": v.plate, "seats": v.seats, "active": v.active,
           "company": (cos[v.company_id].name if v.company_id in cos else ""),
           "kind": "Xe nội bộ" if v.kind != "hop_tac" else "Xe hợp tác"}
          for v in db.execute(select(Vehicle).where(Vehicle.driver_id == e.id)).scalars()]

    lenh = []
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.driver_id == e.id).order_by(desc(DispatchOrder.id)).limit(50)).scalars():
        t = db.get(Tour, d.tour_id); v = db.get(Vehicle, d.vehicle_id)
        lenh.append({"id": d.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                     "vehicle": v.plate if v else "", "date_from": d.date_from, "date_to": d.date_to,
                     "days": (d.date_to - d.date_from).days + 1, "status": d.status,
                     "confirmed_at": d.confirmed_at, "incident_note": d.incident_note})

    chuyen = []
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.guide_id == e.id).order_by(desc(GuideAssignment.id)).limit(50)).scalars():
        t = db.get(Tour, a.tour_id)
        chuyen.append({"id": a.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                       "start_date": t.start_date if t else None, "days": a.days, "holiday": a.holiday,
                       "amount": a.rate_per_day * a.days * (2 if a.holiday else 1), "status": a.status,
                       "confirmed_at": a.confirmed_at, "report_submitted": a.report_submitted,
                       "advance_settled": a.advance_settled})

    the = None
    if e.department == "huong_dan":
        ok, vi_sao = H.guide_eligible(e, date.today())
        the = {"card_no": e.card_no, "card_expiry": e.card_expiry, "du_dieu_kien": ok, "vi_sao": vi_sao}

    return {"ho_so": ho_so, "xe": xe, "lenh_dieu_xe": lenh, "phan_chuyen": chuyen, "the_hdv": the}


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


class VehicleUpdate(BaseModel):
    # extra="forbid": gửi một trường không nhận ở đây (lifecycle, company_id, source_note… – những trường
    # thuộc hồ sơ đội xe, sửa qua PUT /fleet/xe/{id}) sẽ báo 422 chứ không trả 200 rồi lặng lẽ bỏ qua.
    # Một lần "Đã cập nhật xe" mà thực ra không sửa gì là cách chắc chắn nhất để người dùng tin nhầm.
    model_config = ConfigDict(extra="forbid")
    plate: str | None = None
    seats: int | None = None
    kind: str | None = None
    driver_id: int | None = None
    internal_rate_per_day: float | None = None
    active: bool | None = None


@router.put("/vehicles/{vid}")
def vehicle_update(vid: int, data: VehicleUpdate, u: User = Depends(require_roles("cntt", "hcns", "tp_dh")), db: Session = Depends(get_db)):
    """Sửa hồ sơ xe – dùng để bổ sung số chỗ cho xe mới nạp và sửa loại xe nội bộ / hợp tác.
    Đổi loại sang xe hợp tác thì gỡ luôn pháp nhân sở hữu: xe thuê ngoài không phải tài sản của tập đoàn."""
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    before = {"plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "company_id": v.company_id}
    # exclude_unset: gửi driver_id = null là GỠ tài xế khỏi xe; trường không gửi thì giữ nguyên.
    # (exclude_none trước đây khiến không bao giờ gỡ được tài xế đã gán nhầm.)
    for k, val in data.model_dump(exclude_unset=True).items(): setattr(v, k, val)
    if v.kind == "hop_tac": v.company_id = None
    R.audit(db, u.username, u.role, "sua_ho_so_xe", f"vehicle:{v.plate}", before=before,
            after={"plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "company_id": v.company_id}); db.commit()
    return {"message": f"Đã cập nhật xe {v.plate}"}


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
    from app.services import chu_ky as CK
    r = db.get(GuideRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    CK.kiem_tra_nguoi_ky(u, ("chutich", "tgd"), nguoi_trinh=r.proposed_by,
                         da_ky={"chutich": "x" if r.signed_chutich else "", "tgd": "x" if r.signed_tgd else ""})
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
    from app.services import chu_ky as CK
    r = db.get(VehicleRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    CK.kiem_tra_nguoi_ky(u, ("chutich", "tgd"), nguoi_trinh=r.proposed_by,
                         da_ky={"chutich": "x" if r.signed_chutich else "", "tgd": "x" if r.signed_tgd else ""})
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
    # Đợt 4: chọn xe ngoài top gợi ý thì phải ghi lý do TRƯỚC khi lưu. Đây là dữ liệu duy nhất để sau mỗi quý
    # biết thuật toán gợi ý có tốt lên không – không có nó thì chỉ còn tranh luận bằng cảm nhận.
    ly_do_khac_goi_y: str = ""
    km_du_kien: int = 0
    so_khach: int = 0


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
    # Bộ điều kiện phát lệnh (Đợt 1 đội xe, đặc tả §7). Mức BLOCK chặn thật, không có nút vượt chung; các mức
    # còn lại đi kèm lệnh để người điều hành thấy, và được ghi vào nhật ký cùng lệnh.
    from app.services import fleet as FL
    # Chỉ đạo Chủ tịch 07/9/2026: GĐ điều hành đội xe là người DUY NHẤT được tạo và chốt lệnh điều xe.
    ai, ly_do = FL.nguoi_duoc_lap_lenh(db)
    if ai and u.id not in {x.id for x in ai}:
        ten = ", ".join(f"{x.full_name} ({x.username})" for x in ai)
        raise HTTPException(403, f"Chỉ {ten} được tạo lệnh điều xe (chỉ đạo 07/9/2026). "
                                 "Đổi người phụ trách thì sửa tham số chính sách xe_nguoi_lap_lenh.")
    # Truyền tài xế THẬT của xe, không truyền người thay thế ở trên. Với xe hợp tác do đối tác tự lái, hệ
    # thống đang tạm gắn một nhân sự đội xe chỉ để có chỗ ghi – gọi đó là "tài xế" khi kiểm trùng lịch thì
    # hai xe hợp tác chạy cùng ngày sẽ báo tài xế trùng lịch, trong khi ngoài đời là hai người khác nhau.
    # Bộ kiểm tra vẫn nêu "chưa gán tài xế" ở mức chưa đủ dữ liệu, nên vấn đề không bị giấu đi.
    kt = FL.kiem_tra_dieu_xe(db, v, data.date_from, data.date_to, v.driver_id,
                             chan_khi_thieu_giay=bool(R.get_param(db, "xe_chan_khi_thieu_giay")))
    if kt["muc"] == FL.BLOCK:
        raise HTTPException(422, {"message": "Không đủ điều kiện phát lệnh điều xe",
                                  "vi_pham": [i for i in kt["items"] if i["level"] == FL.BLOCK]})
    # Ghi vết gợi ý điều xe (đặc tả A1): chọn phương án hệ thống đánh giá THẤP HƠN nhóm đề xuất thì phải ghi
    # lý do trước khi lưu.
    #
    # Chữ "thấp hơn" ở đây là có chủ đích, không phải chỉ "nằm ngoài top 3". Với đội xe nhỏ, hoặc khi các xe
    # chưa có số liệu vận hành, điểm của chúng BẰNG NHAU – lúc đó bắt người chốt lệnh giải trình vì sao chọn
    # xe này thay vì xe kia là bắt họ giải thích một khác biệt mà chính hệ thống không nhìn thấy. Kết quả chỉ
    # là một ô lý do điền cho xong, và ít lâu sau là một tính năng bị tắt. Chỉ hỏi khi hệ thống thật sự có ý
    # kiến khác: xe được chọn có điểm THẤP HƠN phương án thấp nhất trong nhóm đề xuất.
    from app.services import fleet_ai as AI
    gy = AI.goi_y_dieu_xe(db, data.date_from, data.date_to, data.so_khach, data.km_du_kien)
    top_ids = [p["vehicle_id"] for p in gy["phuong_an"]]
    pa_chon = next((p for p in gy.get("tat_ca", []) if p["vehicle_id"] == v.id), None)
    diem_chon = pa_chon["diem"] if pa_chon else None
    diem_thap_nhat_trong_top = min((p["diem"] for p in gy["phuong_an"]), default=None)
    kem_hon = (top_ids and v.id not in top_ids and diem_chon is not None
               and diem_thap_nhat_trong_top is not None and diem_chon < diem_thap_nhat_trong_top)
    if kem_hon and not (data.ly_do_khac_goi_y or "").strip():
        raise HTTPException(422, {"message": "Xe được chọn được hệ thống đánh giá thấp hơn nhóm đề xuất – "
                                             "phải ghi lý do trước khi lưu",
                                  "diem_xe_chon": diem_chon,
                                  "diem_thap_nhat_trong_nhom_de_xuat": diem_thap_nhat_trong_top,
                                  # Nói ra hệ thống chê điểm gì, chứ không chỉ đưa hai con số điểm: người
                                  # chốt lệnh cần biết mình đang bác lại nhận xét nào để viết lý do cho đúng.
                                  "he_thong_nhan_xet": pa_chon["ly_do"] if pa_chon else [],
                                  "goi_y": gy["phuong_an"]})
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=driver_id, date_from=data.date_from, date_to=data.date_to, rate_id=rt.id if rt else None, internal_price=price, created_by=u.username,
                      phuong_an_ai_goi_y=json.dumps(gy["phuong_an"], ensure_ascii=False, default=str)[:8000],
                      phuong_an_da_chon=v.code or v.plate, ly_do_khac_goi_y=data.ly_do_khac_goi_y.strip())
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "lenh_dieu_xe", f"tour:{t.code}", after={"xe": v.plate, "tuyen": rt.route if rt else "", "tu": str(data.date_from), "den": str(data.date_to), "gia_noi_bo": price, "kiem_tra": kt["muc"]})
    db.commit()
    canh_bao = [i["msg"] for i in kt["items"]]
    if ly_do: canh_bao.append(ly_do)      # cấu hình người lập lệnh sai thì nói ra, không im lặng bỏ qua
    return {"message": f"Đã lập lệnh điều xe {v.plate} cho {t.code} – Đội xe xác nhận trong 4 giờ",
            "kiem_tra": {"muc": kt["muc"], "muc_ten": kt["muc_ten"], "canh_bao": canh_bao},
            "theo_goi_y": v.id in top_ids, "kem_hon_de_xuat": bool(kem_hon), "goi_y": gy["phuong_an"]}


class DispatchUpdate(BaseModel):
    status: str
    incident_note: str = ""


@router.post("/dispatch/{did}/update")
def dispatch_update(did: int, data: DispatchUpdate, u: User = Depends(require_roles("cntt", "tp_dh", "nv_dh", "hcns")), db: Session = Depends(get_db)):
    d = db.get(DispatchOrder, did)
    if not d: raise HTTPException(404, "Không có lệnh")
    if data.status not in ("da_xac_nhan", "hoan_thanh", "huy"): raise HTTPException(422, "Trạng thái không hợp lệ")
    if data.status == "da_xac_nhan":
        # "Tạo VÀ CHỐT" – chốt lệnh cũng chỉ một người, nếu không thì siết cửa vào mà bỏ ngỏ cửa ra.
        from app.services import fleet as FL
        ai, _ = FL.nguoi_duoc_lap_lenh(db)
        if ai and u.id not in {x.id for x in ai}:
            ten = ", ".join(f"{x.full_name} ({x.username})" for x in ai)
            raise HTTPException(403, f"Chỉ {ten} được chốt lệnh điều xe (chỉ đạo 07/9/2026)")
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
    from app.services import chu_ky as CK
    allowed = INCIDENT_LEVELS[i.level]["duyet"]
    signers = [x for x in i.approved_by.split(",") if x]
    da_ky = {}
    for x in signers:
        usr = db.execute(select(User).where(User.username == x)).scalars().first()
        if usr: da_ky[usr.role] = usr.username
    # Mức 3 cần đủ chữ ký Chủ tịch + TGĐ; người lập biên bản không được nằm trong tập người ký.
    CK.kiem_tra_nguoi_ky(u, tuple(allowed), nguoi_trinh=i.created_by, da_ky=da_ky)
    signers.append(u.username); da_ky[u.role] = u.username
    i.approved_by = ",".join(signers)
    can = ("chutich", "tgd") if i.level >= 3 else tuple(allowed)
    du = CK.du_chu_ky(da_ky, can) if i.level >= 3 else True
    if du:
        i.status, i.approved_at = "cho_khieu_nai", datetime.now()
    R.audit(db, u.username, u.role, "duyet_su_vu", f"incident:{i.id}", after={"trang_thai": i.status}); db.commit()
    return {"message": "Đã duyệt – người bị lập biên bản có 3 ngày làm việc để khiếu nại" if i.status == "cho_khieu_nai"
            else "Đã ký, còn chờ chữ ký của " + ", ".join(CK.con_thieu(da_ky, ("chutich", "tgd")))}


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
    return {"id": r.id, "period": r.period, "status": r.status, "rows": r.rows, "totals": r.totals, "inputs": r.inputs or {},
            "kt_confirmed_by": r.kt_confirmed_by, "kt_confirmed_at": r.kt_confirmed_at,
            "hcns_by": r.hcns_by, "hcns_at": r.hcns_at, "tgd_by": r.tgd_by, "tgd_at": r.tgd_at, "entry_ids": r.entry_ids, "updated_at": r.updated_at}


@router.get("/payroll-runs/{period}")
def payroll_run(period: str, refresh: bool = False, u: User = Depends(require_roles("ketoan", "hcns", "tgd", "chutich", "cntt", "bks")), db: Session = Depends(get_db)):
    try:
        return run_out(H.get_or_draft(db, period, refresh=refresh))
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class ChamCongIn(BaseModel):
    cong_chuan: float | None = None
    cong_thuc_te: dict[str, float] = {}      # mã NV → công thực tế


@router.put("/payroll-runs/{period}/cham-cong")
def payroll_attendance(period: str, data: ChamCongIn, u: User = Depends(require_roles("hcns", "cntt")), db: Session = Depends(get_db)):
    """Công thực tế của Kế toán và Nhân sự Hành chính – hai bộ phận duy nhất còn chấm công theo ngày.

    Năm phòng còn lại đã chuyển sang căn cứ báo cáo công việc trước 20 giờ (Điều 12), nên KHÔNG nhận
    và cũng không cảnh báo thiếu công cho họ."""
    run = H.get_or_draft(db, period)
    if run.status != "nhap": raise HTTPException(422, "Bảng lương đã qua bước xác nhận – sửa công phải qua điều chỉnh")
    from app.services import luong as L
    emps = {e.code: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    sai = [ma for ma in data.cong_thuc_te if ma not in emps or L.che_do_cong(emps[ma]) != L.CHAM_CONG]
    if sai: raise HTTPException(422, f"Những mã này không thuộc chế độ chấm công theo ngày: {', '.join(sorted(sai))}")
    cur = dict(run.inputs or {})
    if data.cong_chuan is not None: cur["cong_chuan"] = data.cong_chuan
    cur["cong_thuc_te"] = {**(cur.get("cong_thuc_te") or {}), **data.cong_thuc_te}
    run.inputs = cur
    R.audit(db, u.username, u.role, "nhap_cong_bang_luong", f"payroll:{period}", after={"so_nguoi": len(data.cong_thuc_te)})
    db.commit()
    run = H.get_or_draft(db, period, refresh=True)
    return {"message": f"Đã nhập công cho {len(data.cong_thuc_te)} người kỳ {period}", "run": run_out(run)}


@router.get("/payroll/khoan-treo")
def khoan_treo(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Hoa hồng và thưởng chuyến đang treo vì chuyến chưa chốt quyết toán.

    Người lao động xem được phần của chính mình: đây là chỗ dễ mất tiền nhất mà không ai phát hiện, vì
    khoản treo không hiện trên phiếu lương nào."""
    from app.services import luong as L
    kq = L.khoan_treo(db)
    if u.role not in ("ketoan", "hcns", "tgd", "chutich", "cntt", "bks", "gd_kd", "tp_kd", "tp_dh", "ptgd_doan"):
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        ma = e.code if e else "\u0000"
        kq["rows"] = [r for r in kq["rows"] if r["ma"] == ma]
        kq["theo_nguoi"] = [r for r in kq["theo_nguoi"] if r["ma"] == ma]
        kq["chi_cua_toi"] = True
    return kq


@router.get("/payroll/xung-dot-ho-so")
def payroll_conflicts(u: User = Depends(require_roles("hcns", "cntt", "ketoan", "tgd", "chutich", "bks")), db: Session = Depends(get_db)):
    """Xung đột hồ sơ chặn chạy kỳ lương: một mã dùng cho hai người, một tài khoản gắn hai hồ sơ."""
    from app.services import luong as L
    ds = L.xung_dot_ho_so(db)
    return {"rows": ds, "so_luong": len(ds),
            "ghi_chu": "Còn xung đột thì kỳ lương không chạy được – hệ thống không tự chọn hồ sơ nào." if ds else "Không còn xung đột."}


@router.delete("/payroll-runs/{period}")
def payroll_delete(period: str, u: User = Depends(require_roles("cntt", "chutich")), db: Session = Depends(get_db)):
    """Xóa bảng lương – chặn trong thời hạn lưu trữ tối thiểu."""
    from app.services import luong as L
    ok, vi_sao = L.duoc_xoa_bang_luong(period)
    if not ok: raise HTTPException(422, vi_sao)
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run is None: raise HTTPException(404, "Không có bảng lương kỳ này")
    R.audit(db, u.username, u.role, "xoa_bang_luong", f"payroll:{period}", before={"tong": run.totals})
    db.delete(run); db.commit()
    return {"message": f"Đã xóa bảng lương {period}"}


class BhxhRow(BaseModel):
    ma: str = ""
    ten: str = ""
    muc: float


class BhxhBatch(BaseModel):
    rows: list[BhxhRow]
    ky: str = ""            # 2026-08 – chỉ để ghi nhật ký, mức áp dụng từ kỳ nạp trở đi


@router.post("/bhxh/nap")
def nap_muc_bhxh(data: BhxhBatch, u: User = Depends(require_roles("hcns", "ketoan", "cntt", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp tiền lương làm căn cứ đóng BHXH bắt buộc từ danh sách đóng BHXH của kỳ.

    Ghép theo mã nhân viên trước, không có mã thì theo họ tên không dấu. Người không ghép được KHÔNG bị bỏ
    qua im lặng mà trả về để HCNS xử lý – bỏ sót một người là kỳ lương đó không trừ bảo hiểm của họ.
    """
    from app.services.staff import name_key
    emps = list(db.execute(select(Employee).where(Employee.active == True)).scalars())
    by_code = {e.code: e for e in emps}
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(name_key(e.full_name), []).append(e)
    da_nap, khong_ghep, trung_ten = 0, [], []
    for r in data.rows:
        e = by_code.get(r.ma.strip()) if r.ma.strip() else None
        if e is None and r.ten.strip():
            nhom = by_name.get(name_key(r.ten), [])
            if len(nhom) == 1: e = nhom[0]
            elif len(nhom) > 1: trung_ten.append(f"{r.ten} ({', '.join(x.code for x in nhom)})"); continue
        if e is None:
            khong_ghep.append(f"{r.ma} {r.ten}".strip()); continue
        e.bhxh_base = float(r.muc); da_nap += 1
    R.audit(db, u.username, u.role, "nap_muc_dong_bhxh", f"bhxh:{data.ky or 'khong_ghi_ky'}",
            after={"da_nap": da_nap, "khong_ghep": len(khong_ghep), "trung_ten": len(trung_ten)})
    db.commit()
    con_thieu = [f"{e.code} {e.full_name}" for e in emps if e.contract_type == "hdld" and not e.bhxh_base]
    return {"da_nap": da_nap, "khong_ghep_duoc": khong_ghep, "trung_ten_can_chi_dinh_ma": trung_ten,
            "hdld_chua_co_muc_dong": con_thieu,
            "message": f"Đã nạp mức đóng BHXH cho {da_nap} người" +
                       (f"; {len(khong_ghep)} dòng chưa ghép được" if khong_ghep else "") +
                       (f"; còn {len(con_thieu)} người HĐLĐ chưa có mức đóng" if con_thieu else "")}


class DoanVienBatch(BaseModel):
    ho_ten: list[str]
    thay_the: bool = True    # True: danh sách này là toàn bộ đoàn viên hiện tại


@router.post("/doan-vien/nap")
def nap_doan_vien(data: DoanVienBatch, u: User = Depends(require_roles("hcns", "ketoan", "cntt", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp danh sách đoàn viên đã ký thỏa thuận khấu trừ đoàn phí.

    Chỉ nhận HỌ TÊN. Bản thỏa thuận có số căn cước và số điện thoại nhưng phân hệ lương không cần tới, nên
    không đưa vào hệ thống: dữ liệu không cần thì không lưu.
    """
    from app.services.staff import name_key
    emps = list(db.execute(select(Employee).where(Employee.active == True)).scalars())
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(name_key(e.full_name), []).append(e)
    danh_sach, khong_ghep, trung_ten = set(), [], []
    for ten in data.ho_ten:
        nhom = by_name.get(name_key(ten), [])
        if len(nhom) == 1: danh_sach.add(nhom[0].id)
        elif len(nhom) > 1: trung_ten.append(f"{ten} ({', '.join(x.code for x in nhom)})")
        else: khong_ghep.append(ten)
    n_bat, n_tat = 0, 0
    for e in emps:
        if e.id in danh_sach and not e.member_org: e.member_org = True; n_bat += 1
        elif data.thay_the and e.id not in danh_sach and e.member_org: e.member_org = False; n_tat += 1
    R.audit(db, u.username, u.role, "nap_danh_sach_doan_vien", "doan_phi",
            after={"doan_vien": len(danh_sach), "bat_them": n_bat, "go": n_tat, "khong_ghep": len(khong_ghep)})
    db.commit()
    return {"doan_vien": len(danh_sach), "bat_them": n_bat, "go_khoi_danh_sach": n_tat,
            "khong_ghep_duoc": khong_ghep, "trung_ten_can_chi_dinh_ma": trung_ten,
            "message": f"Đã ghi nhận {len(danh_sach)} đoàn viên" + (f"; {len(khong_ghep)} tên chưa ghép được" if khong_ghep else "")}


@router.get("/payroll-runs/{period}/phieu-luong")
def phieu_luong(period: str, ma: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Phiếu lương của CHÍNH người đăng nhập (hoặc của một mã NV, với Kế toán / HCNS / lãnh đạo).

    Người lao động phải tự xem được lương của mình. Phiếu ghi đủ ba khối theo bộ tính lương: thu nhập,
    khoản trừ, phải trả – kèm căn cứ xác định mức lương của kỳ và các khoản đang TREO của chính người đó.
    Khoản treo không nằm trong phiếu lương nào là chỗ dễ mất tiền nhất mà không ai phát hiện, nên phiếu
    lương ở đây hiển thị luôn phần treo bên cạnh phần được trả.
    """
    from app.services import luong as L
    quan_tri = u.role in ("ketoan", "hcns", "tgd", "chutich", "cntt", "bks")
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if not e and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    ma_can = (ma or "").strip() or (e.code if e else "")
    if not ma_can: raise HTTPException(404, "Tài khoản chưa gắn hồ sơ nhân sự – báo HCNS ghép mã nhân viên")
    if ma and not quan_tri and (not e or ma != e.code):
        raise HTTPException(403, "Chỉ xem được phiếu lương của chính mình")

    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run is None: raise HTTPException(404, f"Chưa có bảng lương kỳ {period}")
    if run.status == "nhap" and not quan_tri:
        raise HTTPException(422, "Bảng lương kỳ này còn là bản nháp của robot – chờ Kế toán xác nhận cơ sở tính")
    row = next((r for r in run.rows if r["ma"] == ma_can), None)
    if row is None: raise HTTPException(404, f"Không có dòng lương của mã {ma_can} trong kỳ {period}")

    emp = db.execute(select(Employee).where(Employee.code == ma_can)).scalars().first()
    cty = db.get(Company, emp.company_id) if emp and emp.company_id else None
    treo = [x for x in L.khoan_treo(db)["rows"] if x["ma"] == ma_can]
    return {"period": period, "trang_thai_bang_luong": run.status, "da_ky": bool(run.tgd_by),
            "nhan_su": {"ma": ma_can, "ten": row["ten"], "phong": DEPARTMENTS.get(row["phong"], row["phong"]),
                        "chuc_vu": row.get("chuc_vu"), "hop_dong": row["hop_dong"],
                        "phap_nhan_tra_luong": cty.name if cty else "", "che_do_cong": row.get("che_do_cong_ten")},
            "xac_dinh_luong": row.get("xac_dinh_luong"), "muc_dong_bhxh": row.get("bhxh_base", 0),
            "thu_nhap": {"luong_co_ban_ky": row["luong_cb"],
                         "cac_khoan": [k for k in row["khoan"] if k["tien"] > 0],
                         "tong": row.get("thu_nhap", row["luong_cb"] + row["bien_doi"])},
            "khoan_tru": {"che_tai_su_vu": row.get("tru_su_vu", 0), "chi_tiet_che_tai": [k for k in row["khoan"] if k["tien"] < 0],
                          "bhxh_nguoi_lao_dong": row.get("bhxh", 0), "doan_phi_cong_doan": row.get("doan_phi", 0),
                          "tncn_khau_tru": row.get("tncn", 0), "tong": row.get("khoan_tru", 0)},
            "thuc_nhan": row["thuc_nhan"], "ghi_chu": row.get("ghi_chu", ""),
            "khoan_dang_treo": treo,
            "luu_y": ("Khoản treo là hoa hồng và thưởng chuyến CHƯA phát sinh vì chuyến chưa chốt quyết toán. "
                      "Đây là cơ chế hoãn, không phải cắt: chốt quyết toán xong thì kỳ lương tương ứng trả đủ.")
            if treo else ""}


@router.get("/payroll-runs/{period}/theo-phap-nhan")
def payroll_by_company(period: str, u: User = Depends(require_roles("ketoan", "hcns", "tgd", "chutich", "cntt", "bks")), db: Session = Depends(get_db)):
    """Bảng lương chia theo pháp nhân trả lương – đối chiếu trước khi TGĐ ký lô và ghi sổ."""
    run = H.get_or_draft(db, period)
    return {"period": period, "rows": H.but_toan_theo_phap_nhan(db, run),
            "ghi_chu": "Mỗi pháp nhân là một bộ chứng từ lương riêng. Người chưa xác định pháp nhân được tách "
                       "thành một dòng riêng, không dồn vào công ty mẹ."}


@router.post("/payroll-runs/{period}/advance")
def payroll_advance(period: str, u: User = Depends(require_roles("ketoan", "hcns", "tgd")), db: Session = Depends(get_db)):
    run = H.get_or_draft(db, period)
    try:
        msg = H.advance(db, u, run)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg, "run": run_out(run)}
