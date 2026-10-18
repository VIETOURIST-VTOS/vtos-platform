"""API Hồ sơ nhân sự – Hợp đồng – Chấm công – Người phụ thuộc (phân hệ Nhân sự kiểu MISA AMIS)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User
from app.models.hr import Employee, PayrollRun
from app.models.hrm import (EmployeeProfile, LaborContract, Dependent, LeaveRequest,
                            CONTRACT_KINDS, CONTRACT_STATUS, RELATIONS, LEAVE_KINDS, LEAVE_STATUS, ATT_KINDS)
from app.services import hrm as H
from app.services import rules as R
from app.services.ho_so_nhan_vien import (VAI_CO_NHOM_CHE as _HSNV_VAI_HIEN,
                                          VAI_CO_TRONG_BANG as _HSNV_VAI_XEM,
                                          VAI_DUNG_DAU as _HSNV_VAI_QUAN_LY)

router = APIRouter(prefix="/api/v1", tags=["nhan-su-ho-so"])
HR_ADMIN = ("hcns", "cntt", "tgd", "chutich")
HR_READ = ("hcns", "cntt", "tgd", "chutich", "bks", "ketoan")
# Danh sách LỆCH HỒ SƠ (HS-11) là việc của HCNS — KHÔNG mở cho Kế toán. Bỏ `ketoan` ra khỏi HR_READ
# ở riêng cửa này vì Kế toán trưởng kế thừa Kế toán, và cửa nào mở cho KTT trong nhóm /hrm phải nằm
# trong `CUA_LUONG_DA_KY` (test_lg5). Chủ tịch chốt 18/10/2026: đóng, không ghi thêm vào danh sách ký.
HR_LECH_READ = ("hcns", "cntt", "tgd", "chutich", "bks")
# Chữ ký cửa duyệt đơn: HỢP của mọi vai ký được, SUY RA từ bảng luật chứ không khai tay lần thứ hai.
# Khai tay hai chỗ thì sớm muộn cũng lệch, và lúc lệch thì hoặc một người ký được thứ không phải của
# mình, hoặc một người đúng luật lại bị cửa chặn mà không ai hiểu vì sao.
KY_DON = tuple(sorted({v for vais in H.TUYEN_KY_DON.values() for v in vais} | set(H.KY_MAC_DINH)))


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


def leave_out(r: LeaveRequest, e: Employee | None = None, u: User | None = None) -> dict:
    """`co_the_ky` do MÁY CHỦ trả lời, không để màn hình tự suy.

    Màn hình mà tự khai "vai nào ký được đơn nào" là khai luật lần thứ hai, ở chỗ không ai chạy
    phép thử. Trả thẳng câu trả lời ra đây thì nút Duyệt chỉ hiện đúng chỗ nó bấm được, và lúc luật
    đổi thì màn hình đổi theo mà không phải sửa một dòng nào.
    """
    ky = bool(u and e and u.role in H.nguoi_ky_don(e.department)
              and e.user_id != u.id and r.status == "cho_duyet")
    return {"id": r.id, "employee_id": r.employee_id, "employee_code": e.code if e else "",
            "co_the_ky": ky, "nguoi_ky": list(H.nguoi_ky_don(e.department)) if e else [],
            "employee_name": e.full_name if e else "", "department": e.department if e else "",
            "kind": r.kind, "kind_name": LEAVE_KINDS.get(r.kind, {}).get("ten", r.kind),
            "date_from": r.date_from, "date_to": r.date_to, "days": r.days, "ot_hours": r.ot_hours,
            "reason": r.reason, "status": r.status, "status_name": LEAVE_STATUS.get(r.status, r.status),
            "approved_by": r.approved_by, "approved_at": r.approved_at, "decision_note": r.decision_note,
            "created_by": r.created_by, "created_at": r.created_at}


@router.get("/hrm/meta")
def meta(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Thêm 08/10/2026: tuyến ký đơn, và hai chỗ thiếu ĐẾM ĐƯỢC của chính tuyến ấy.

    `phong_thieu_nguoi_giu_vai` là mặt sau của lần siết hôm nay: mỗi phòng nay đúng MỘT vai ký, nên
    một vai không tài khoản nào giữ thì đơn của cả phòng ấy nằm im trong hàng đợi mà không dòng nào
    báo. Trả ra đây để màn hình Nhân sự in lên, thay vì để HCNS phát hiện bằng một người đi hỏi."""
    return {"contract_kinds": CONTRACT_KINDS, "contract_status": CONTRACT_STATUS, "relations": RELATIONS,
            "leave_kinds": LEAVE_KINDS, "leave_status": LEAVE_STATUS, "attendance_kinds": ATT_KINDS,
            "tuyen_ky_don": {k: list(v) for k, v in H.TUYEN_KY_DON.items()},
            "phong_chua_chot_nguoi_ky": list(H.phong_chua_chot_nguoi_ky()),
            "phong_thieu_nguoi_giu_vai": H.phong_khong_ai_giu_vai_ky(db)}


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


# ---------- HS-11 · Một người, một ngày sinh ----------
# Hai cửa dưới đây đứng cạnh `profile-gaps` là có chủ ý: cùng một việc của HCNS — đi dọn hồ sơ —
# nên chúng nằm cùng một chỗ trên màn hình và cùng một chỗ trong mã.

@router.get("/hrm/lech-ho-so")
def lech_ho_so(gom_ca_khop: bool = False, u: User = Depends(require_roles(*HR_LECH_READ)),
               db: Session = Depends(get_db)):
    """CHỈ ĐỌC — kê những người đang mang hai giá trị khác nhau cho cùng một thông tin.

    Vai đọc rộng hơn vai sửa (`HR_READ` chứ không `HR_ADMIN`): Ban kiểm soát và Kế toán cần nhìn
    thấy chỗ lệch để biết con số họ đang đọc đến từ đâu, nhưng không ai trong hai vai ấy được
    sửa hồ sơ nhân sự.
    """
    from app.services import gop_ho_so_nv as GOP
    return GOP.soat_lech(db, gom_ca_khop)


class ChepOTrongIn(BaseModel):
    xac_nhan: bool = False


@router.post("/hrm/lech-ho-so/chep-o-trong")
def chep_o_trong(data: ChepOTrongIn, u: User = Depends(require_roles(*HR_ADMIN)),
                 db: Session = Depends(get_db)):
    """Chép sang hồ sơ CHỈ ở ô còn trống. `xac_nhan=false` là bản xem trước, không ghi gì.

    Cửa này KHÔNG giải quyết được dòng «hai bên khác nhau», và cố ý không giải quyết: chọn hộ
    một ngày sinh là xoá mất ngày kia mà không còn dấu vết nào để lần lại.
    """
    from app.services import gop_ho_so_nv as GOP
    return GOP.chuyen_cho_trong(db, u, data.xac_nhan)


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
    """Ba tầng, và tầng giữa là tầng mới (30/9/2026).

    HCNS và nhóm đọc toàn công ty thấy tất cả. NGƯỜI KÝ của một phòng thấy đơn của phòng ấy cộng
    đơn của chính mình — không có tầng này thì Giám đốc đội xe mở màn hình ra chỉ thấy đơn của
    riêng ông, tức là có nút ký mà không có đơn nào để ký. Còn lại chỉ thấy đơn của chính mình.
    """
    q = select(LeaveRequest).order_by(LeaveRequest.date_from.desc(), LeaveRequest.id.desc())
    if u.role not in HR_READ:
        me = _self_employee(db, u)
        phong = H.phong_minh_ky(u.role)
        if phong:
            cua_phong = select(Employee.id).where(Employee.department.in_(phong))
            dieu = LeaveRequest.employee_id.in_(cua_phong)
            if me:
                dieu = or_(dieu, LeaveRequest.employee_id == me.id)
            q = q.where(dieu)
        elif me:
            q = q.where(LeaveRequest.employee_id == me.id)
        else:
            return []
    elif employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    if status:
        q = q.where(LeaveRequest.status == status)
    if kind:
        q = q.where(LeaveRequest.kind == kind)
    emps = {e.id: e for e in db.execute(select(Employee)).scalars()}
    return [leave_out(r, emps.get(r.employee_id), u) for r in db.execute(q).scalars()]


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
    return leave_out(r, e, u)


class DecisionIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/leaves/{lid}/decide")
def decide_leave(lid: int, data: DecisionIn, u: User = Depends(require_roles(*KY_DON)),
                 db: Session = Depends(get_db)):
    """Chữ ký cửa là HỢP của mọi người ký; ai ký được đơn của phòng nào thì `H.decide_leave` canh."""
    r = db.get(LeaveRequest, lid)
    if not r:
        raise HTTPException(404, "Không tìm thấy đơn")
    if not data.approve and not (data.note or "").strip():
        raise HTTPException(422, "Từ chối đơn phải ghi lý do – người làm đơn cần biết sửa gì để gửi lại")
    try:
        H.decide_leave(db, u, r, data.approve, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return leave_out(r, db.get(Employee, r.employee_id), u)


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


# ---------- Bảng chấm công đối chiếu bảng lương ----------

@router.get("/payroll-runs/{period}/lech-cong")
def lech_cong(period: str, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    """Chỗ lệch giữa bảng chấm công và số công đã nhập vào bảng lương kỳ này.

    Đặt dưới `/payroll-runs/` chứ không dưới `/attendance/` là có chủ ý: câu hỏi ở đây không phải "bảng
    chấm công nói gì" mà "bảng lương kỳ này còn chỗ nào chưa khớp bảng chấm công" – nó thuộc hồ sơ KỲ
    LƯƠNG, và màn hình Lương đã khai sẵn tiền tố `/api/v1/payroll-runs` nên không phải nới phạm vi vai nào.

    Kỳ chưa có bảng lương thì KHÔNG phải lỗi: vẫn soi được bảng chấm công, chỉ là chưa ai gõ số công nào.
    Trả về rỗng ở đây sẽ là trả lời "không có chỗ lệch" cho một câu chưa ai hỏi.
    """
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    kq = H.lech_cong(db, period, (run.inputs or {}) if run is not None else {})
    kq["co_bang_luong"] = run is not None
    return kq


@router.get("/payroll-runs/{period}/tncn-con-thieu")
def tncn_con_thieu(period: str, u: User = Depends(require_roles(*HR_READ)), db: Session = Depends(get_db)):
    """Cột TNCN của kỳ này KHÔNG gồm những ai — và nền dữ liệu để tính đang ở đâu.

    Đặt dưới `/payroll-runs/` như cửa lệch công: câu hỏi thuộc hồ sơ KỲ LƯƠNG, và màn hình Lương đã
    khai sẵn tiền tố ấy nên không phải nới phạm vi vai nào.
    """
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    kq = H.tncn_chua_tinh(db, period, (run.rows or []) if run is not None else [])
    kq["co_bang_luong"] = run is not None
    return kq


# =================================================================================================
# HS-2 · HỒ SƠ MỘT NGƯỜI, CẮT VÀ CHE THEO VAI CỦA NGƯỜI ĐANG XEM
# =================================================================================================
# VÌ SAO CỬA NÀY NẰM Ở ĐÂY — `hrm.py` — chứ không ở `access.py` cùng các cửa quản trị tài khoản.
#
# ĐÚNG CHỖ VỀ NỘI DUNG: nhóm 4 (hồ sơ cá nhân), nhóm 5 (hợp đồng và lương) và nhóm 7 (chấm công,
# đơn nghỉ) đọc thẳng từ `employee_profiles`, `labor_contracts`, `dependents`, `leave_requests`,
# `attendance_days` — đúng bộ bảng tệp này giữ.
#
# ĐÚNG CHỖ VỀ HÀNG RÀO: `check_restricted_scope` chạy trong `current_user` cho MỌI đường dẫn và
# chỉ cho một vai chạm nhóm API nằm sau MÀN HÌNH của vai ấy. Đo 15/10/2026: `/api/v1/access` có
# trong bản đồ màn hình của `chutich`, `hcns`, `cntt` và KHÔNG có ở một vai đứng đầu nào;
# `/api/v1/employees` thì có ở cả tám vai. Chủ tịch chốt 15/10: mở "Hồ sơ nhân viên" cho trưởng
# phòng, KHÔNG mở cả màn quản trị Tài khoản. Hai điều ấy gặp nhau đúng ở tiền tố này — nên cửa về
# đây, không nới bản đồ màn hình, không thêm ngoại lệ, không đụng `main.py`.
#
# `tai-khoan/{uid}` chứ không phải `{eid}`: các cửa `/employees/{eid}/...` quanh đây nhận MÃ HỒ SƠ,
# cửa này nhận MÃ TÀI KHOẢN — con số màn hình Tài khoản đang cầm khi người dùng bấm vào một dòng.
# Hai loại số đi chung một khuôn đường dẫn là chỗ sớm muộn có người truyền nhầm, và truyền nhầm ở
# đây nghĩa là mở hồ sơ của người khác.
@router.get("/employees/tai-khoan/{uid}/ho-so-theo-vai")
def ho_so_theo_vai(uid: int,
                   u: User = Depends(require_roles(*_HSNV_VAI_XEM,
                                                   mo_ta="hồ sơ nhân viên")),
                   db: Session = Depends(get_db)):
    """Hồ sơ một người, ĐÃ CẮT và ĐÃ CHE ở máy chủ theo vai của người đang xem.

    KHÔNG dùng `require_roles`: hàng rào thật là bảng quyền trong `ho_so_nhan_vien`, nơi mặc định
    là TỪ CHỐI, và cửa trả 403 khi vai ấy không thấy một nhóm nào. Thêm một danh sách vai ở đây
    nữa là hai chỗ phải sửa cùng lúc, và quên một chỗ là hở.

    Giá trị thật của nhóm che KHÔNG BAO GIỜ đi ra khỏi cửa này. Cửa trả bản đã che; màn hình không
    bao giờ cầm giá trị thật rồi tự giấu — giấu ở màn hình thì giá trị thật đã nằm trong phản hồi
    mạng, và ai mở tab Network cũng đọc được.

    `thieu_nguon` kê những trường đã khai mà hệ thống chưa có cửa nhập. Đó là việc còn thiếu, không
    phải người này không có số liệu — hai câu khác nhau, và chỉ câu đầu dẫn tới một việc phải làm.
    """
    from app.models.core import ROLES
    from app.services import ho_so_nhan_vien as HSNV
    t = db.get(User, uid)
    if not t:
        raise HTTPException(404, "Không có tài khoản")
    kq = HSNV.doc_ho_so(db, u, t)
    if not kq["nhom_thay"]:
        raise HTTPException(403, f"Vai {ROLES.get(u.role, u.role)} không đọc được hồ sơ nhân viên này")

    # VẾT CHO MỌI LƯỢT ĐỌC THẬT MỘT NHÓM NHẠY CẢM — kể cả khi người đọc là Chủ tịch. Quyền toàn
    # diện nghĩa là không có gì chặn, không nghĩa là không để lại dấu; vết bảo vệ chính người có
    # quyền. Nhật ký ghi TÊN NHÓM, không ghi một giá trị nào: một bản ghi kiểm toán chứa CCCD thì
    # chính nó thành chỗ rò thứ hai, và chỗ ấy ai đọc được nhật ký cũng đọc được.
    if kq["nhom_nhay_cam_da_doc"]:
        R.audit(db, u.username, u.role, "doc_ho_so_nhan_vien", f"user:{t.username}",
                after={"nhom": kq["nhom_nhay_cam_da_doc"], "luat_pham_vi": kq["luat_pham_vi"]})
        db.commit()
    return kq


class HienTruongIn(BaseModel):
    truong: str
    muc_dich: str


# DANH SÁCH VAI Ở CHỮ KÝ, nhưng SUY RA TỪ BẢNG QUYỀN chứ không gõ tay — xem `VAI_CO_NHOM_CHE`.
# Đường GHI phải khai quyền ở chỗ máy đọc được (`test_ks2_khai_quyen_may_doc_duoc`), và lời khai
# ấy không được là bản sao thứ hai của bảng quyền, vì hai bản sẽ lệch nhau. Nó lọc sớm; hàng rào
# thật vẫn là `HSNV.hien_truong`, chặt hơn — nó còn kiểm từng NHÓM và phạm vi quản lý.
@router.post("/employees/tai-khoan/{uid}/hien-truong")
def hien_truong_ho_so(uid: int, data: HienTruongIn,
                      u: User = Depends(require_roles(*_HSNV_VAI_HIEN,
                                                      mo_ta="hiện trường hồ sơ nhân viên")),
                      db: Session = Depends(get_db)):
    """HS-3 · Hiện giá trị thật của MỘT trường đang bị che, đổi lấy MỘT dòng nhật ký.

    Che không phải là cấm: HCNS làm hợp đồng thì phải đọc được số CCCD thật. Cái họ không được
    có là đọc nó mà không ai biết. Cửa này ghi vết TRƯỚC khi trả giá trị — ghi sau thì một lỗi
    giữa chừng để lại lượt đọc không có vết, mà đó đúng là lượt đọc đáng ngờ nhất.

    Nhật ký ghi TÊN TRƯỜNG và MỤC ĐÍCH, KHÔNG BAO GIỜ ghi giá trị: một bản ghi kiểm toán chứa
    CCCD là chỗ rò thứ hai, và nó rộng hơn chỗ thứ nhất — ai đọc được nhật ký cũng đọc được,
    kể cả người không được xem nhóm 4.
    """
    from app.services import ho_so_nhan_vien as HSNV
    t = db.get(User, uid)
    if not t:
        raise HTTPException(404, "Không có tài khoản")

    muc_dich = (data.muc_dich or "").strip()
    if len(muc_dich) < HSNV.MUC_DICH_TOI_THIEU:
        raise HTTPException(422, "Phải ghi mục đích bằng một câu — ví dụ «làm hợp đồng lao "
                                 "động», «khai báo BHXH». Một nhật ký đầy dòng «x» là một nhật "
                                 "ký không ai đọc.")

    kq = HSNV.hien_truong(db, u, t, (data.truong or "").strip())
    if not kq["duoc"]:
        ma = {"khong_co_truong": 404, "khong_duoc_xem": 403,
              "khong_bi_che": 422, "chua_co_so_lieu": 404}
        raise HTTPException(ma.get(kq["ma_loi"], 422), kq["ly_do"])

    R.audit(db, u.username, u.role, "hien_truong_ho_so", f"user:{t.username}",
            after={"truong": kq["truong"], "nhom": kq["ma_nhom"], "muc_dich": muc_dich[:300],
                   "luat_pham_vi": kq["luat_pham_vi"]})
    db.commit()
    return {"truong": kq["truong"], "gia_tri": kq["gia_tri"],
            "nhom": kq["ma_nhom"], "ten_nhom": kq["ten_nhom"],
            "message": f"Lượt xem này đã vào nhật ký hồ sơ mang tên {u.username}."}


@router.get("/employees/phong-toi")
def nhan_vien_phong_toi(u: User = Depends(require_roles(*_HSNV_VAI_QUAN_LY,
                                                        mo_ta="nhân viên phòng tôi")),
                        db: Session = Depends(get_db)):
    """HS-4 · Những người tôi quản lý — câu đứng TRƯỚC câu "người này tôi xem được gì".

    Thiếu cửa này thì trưởng phòng chỉ mở được hồ sơ khi đã biết sẵn mã tài khoản, tức là trên
    thực tế họ không mở được. Mỗi dòng chỉ mang phần nhóm 1 mà vai ấy được thấy, cắt qua đúng
    `cat_ho_so_theo_vai` như mọi chỗ khác — danh sách KHÔNG có bảng cột riêng, vì bảng riêng bao
    giờ cũng là bảng rộng hơn.

    Phản hồi mang `luat_pham_vi` để màn hình nói thẳng danh sách này dựa vào đâu: cây tổ chức
    Kinh doanh (có ngày hiệu lực) hay chỉ so tên phòng (luật yếu).
    """
    from app.services import ho_so_nhan_vien as HSNV
    kq = HSNV.nhan_vien_trong_pham_vi(db, u)
    if not kq["duoc"]:
        raise HTTPException(403, kq["ly_do"])
    return kq
