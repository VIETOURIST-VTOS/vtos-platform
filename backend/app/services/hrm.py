"""Nghiệp vụ hồ sơ nhân sự – hợp đồng – chấm công – người phụ thuộc (phân hệ Nhân sự kiểu MISA AMIS).

Ba việc HCNS làm hằng tháng mà VTOS chưa có, nay làm được ngay trên hệ thống:
  1. Hồ sơ & hợp đồng: hợp đồng nào sắp hết hạn, ai chưa có hợp đồng hiệu lực, ai thiếu hồ sơ định danh.
  2. Đơn từ & phép năm: nhân viên gửi đơn, quản lý duyệt; phép năm trừ tự động, không cho vượt quỹ phép.
  3. Bảng chấm công tháng: sinh từ đơn đã duyệt, HCNS chỉnh tay phần còn lại; ra số công để tính lương.

Phép năm theo Bộ luật Lao động 2019 (Điều 113, 114): 12 ngày/năm với điều kiện làm việc bình thường,
cứ đủ 5 năm làm việc cho một người sử dụng lao động thì cộng thêm 1 ngày; năm đầu chưa đủ 12 tháng thì
tính theo tỷ lệ số tháng làm việc. Số ngày gốc lấy theo hợp đồng (annual_leave_days) nếu có ghi khác 12.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.hr import Employee
from app.models.hrm import (EmployeeProfile, LaborContract, Dependent, LeaveRequest, AttendanceDay,
                            CONTRACT_KINDS, CONTRACT_STATUS, LEAVE_KINDS, LEAVE_STATUS, ATT_KINDS)
from app.services import rules as R

# Giảm trừ gia cảnh – để ở tham số để Kế toán chỉnh khi Nhà nước thay đổi mức, không chôn cứng trong mã.
PIT_SELF_KEY, PIT_DEP_KEY = "giam_tru_ban_than", "giam_tru_nguoi_phu_thuoc"
PIT_SELF_DEFAULT, PIT_DEP_DEFAULT = 11_000_000.0, 4_400_000.0


def _param(db: Session, key: str, default: float) -> float:
    try:
        return R.get_param(db, key)
    except KeyError:
        return default


def _period_of(d: date) -> str:
    return f"{d:%Y-%m}"


def month_days(period: str) -> list[date]:
    y, m = int(period[:4]), int(period[5:7])
    first = date(y, m, 1)
    last = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


# ---------- Hợp đồng lao động ----------

def active_contract(db: Session, employee_id: int, on: date | None = None) -> LaborContract | None:
    """Hợp đồng đang hiệu lực tại một ngày (bản ký gần nhất còn hiệu lực)."""
    on = on or date.today()
    rows = db.execute(select(LaborContract).where(LaborContract.employee_id == employee_id,
                                                  LaborContract.status == "hieu_luc",
                                                  LaborContract.effective_from <= on)
                      .order_by(LaborContract.effective_from.desc(), LaborContract.id.desc())).scalars().all()
    for c in rows:
        if c.effective_to is None or c.effective_to >= on:
            return c
    return None


def contract_alerts(db: Session, within_days: int = 45, on: date | None = None) -> dict:
    """Cảnh báo hợp đồng: sắp hết hạn trong N ngày, đã hết hạn mà chưa ký lại, nhân sự chưa có hợp đồng."""
    on = on or date.today()
    limit = on + timedelta(days=within_days)
    emps = {e.id: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    expiring, expired, missing = [], [], []
    for eid, e in emps.items():
        c = active_contract(db, eid, on)
        if c is None:
            last = db.execute(select(LaborContract).where(LaborContract.employee_id == eid)
                              .order_by(LaborContract.effective_from.desc(), LaborContract.id.desc())).scalars().first()
            item = {"employee_id": eid, "code": e.code, "full_name": e.full_name, "department": e.department,
                    "contract_code": last.code if last else "", "effective_to": last.effective_to if last else None}
            (expired if last else missing).append(item)
            continue
        if c.effective_to and c.effective_to <= limit:
            expiring.append({"employee_id": eid, "code": e.code, "full_name": e.full_name, "department": e.department,
                             "contract_code": c.code, "kind": c.kind, "kind_name": CONTRACT_KINDS.get(c.kind, {}).get("ten", c.kind),
                             "effective_to": c.effective_to, "days_left": (c.effective_to - on).days})
    expiring.sort(key=lambda x: x["days_left"])
    return {"on": on, "within_days": within_days, "expiring": expiring, "expired": expired, "no_contract": missing,
            "counts": {"expiring": len(expiring), "expired": len(expired), "no_contract": len(missing)}}


def close_expired_contracts(db: Session, on: date | None = None) -> int:
    """Chuyển hợp đồng quá hạn sang trạng thái 'het_han' (chạy hằng ngày hoặc khi mở màn hình hợp đồng)."""
    on = on or date.today()
    n = 0
    for c in db.execute(select(LaborContract).where(LaborContract.status == "hieu_luc",
                                                    LaborContract.effective_to.isnot(None),
                                                    LaborContract.effective_to < on)).scalars():
        c.status, n = "het_han", n + 1
    if n:
        db.commit()
    return n


# ---------- Phép năm ----------

def annual_leave_entitlement(db: Session, e: Employee, year: int) -> float:
    """Quỹ phép năm: số ngày gốc theo hợp đồng (mặc định 12) + thâm niên mỗi đủ 5 năm 1 ngày;
    năm vào làm tính theo tỷ lệ số tháng còn lại của năm đó."""
    c = active_contract(db, e.id, date(year, 12, 31)) or active_contract(db, e.id, date(year, 1, 1))
    base = float(c.annual_leave_days) if c and c.annual_leave_days else 12.0
    start = e.start_date or (c.effective_from if c else None)
    if not start:
        return base
    seniority = max((date(year, 12, 31) - start).days // 365, 0)
    base += seniority // 5
    if start.year == year:                                   # năm đầu: theo tỷ lệ tháng làm việc
        months = 12 - start.month + 1
        return round(base * months / 12, 1)
    if start.year > year:
        return 0.0
    return base


def leave_used(db: Session, employee_id: int, year: int) -> float:
    """Số ngày phép năm đã dùng (đơn đã duyệt) trong năm."""
    got = db.execute(select(func.coalesce(func.sum(LeaveRequest.days), 0.0))
                     .where(LeaveRequest.employee_id == employee_id, LeaveRequest.kind == "phep_nam",
                            LeaveRequest.status == "duyet",
                            LeaveRequest.date_from >= date(year, 1, 1),
                            LeaveRequest.date_from <= date(year, 12, 31))).scalar() or 0.0
    return round(float(got), 1)


def leave_balance(db: Session, e: Employee, year: int) -> dict:
    ent = annual_leave_entitlement(db, e, year)
    used = leave_used(db, e.id, year)
    pending = db.execute(select(func.coalesce(func.sum(LeaveRequest.days), 0.0))
                         .where(LeaveRequest.employee_id == e.id, LeaveRequest.kind == "phep_nam",
                                LeaveRequest.status == "cho_duyet",
                                LeaveRequest.date_from >= date(year, 1, 1),
                                LeaveRequest.date_from <= date(year, 12, 31))).scalar() or 0.0
    return {"employee_id": e.id, "code": e.code, "full_name": e.full_name, "year": year,
            "entitlement": ent, "used": used, "pending": round(float(pending), 1), "remaining": round(ent - used, 1)}


# ---------- Đơn từ ----------

def create_leave(db: Session, u: User, e: Employee, data: dict) -> LeaveRequest:
    kind = data.get("kind") or "phep_nam"
    if kind not in LEAVE_KINDS:
        raise ValueError(f"Loại đơn {kind} không hợp lệ")
    d1, d2 = data["date_from"], data.get("date_to") or data["date_from"]
    if d2 < d1:
        raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
    days = float(data.get("days") or ((d2 - d1).days + 1))
    if kind != "tang_ca" and days <= 0:
        raise ValueError("Số ngày nghỉ phải lớn hơn 0")
    if kind == "phep_nam":
        bal = leave_balance(db, e, d1.year)
        if days > bal["remaining"] - bal["pending"]:
            raise ValueError(f"Vượt quỹ phép năm {d1.year}: còn {bal['remaining']:.1f} ngày "
                             f"(đang chờ duyệt {bal['pending']:.1f}), xin {days:.1f} ngày")
    r = LeaveRequest(employee_id=e.id, kind=kind, date_from=d1, date_to=d2, days=days,
                     ot_hours=float(data.get("ot_hours") or 0), reason=(data.get("reason") or "")[:300],
                     created_by=u.username)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "gui_don_nhan_su", f"don:{r.id}",
            after={"nhan_vien": e.code, "loai": kind, "tu": str(d1), "den": str(d2), "so_ngay": days})
    db.commit()
    return r


def decide_leave(db: Session, u: User, r: LeaveRequest, approve: bool, note: str = "") -> LeaveRequest:
    """Duyệt / từ chối đơn. Đơn đã duyệt sẽ tự ghi vào bảng chấm công những ngày tương ứng."""
    if r.status != "cho_duyet":
        raise ValueError(f"Đơn đã ở trạng thái '{LEAVE_STATUS.get(r.status, r.status)}'")
    e = db.get(Employee, r.employee_id)
    if approve and r.kind == "phep_nam":
        bal = leave_balance(db, e, r.date_from.year)
        if r.days > bal["remaining"]:
            raise ValueError(f"Không đủ phép năm: còn {bal['remaining']:.1f} ngày, đơn xin {r.days:.1f} ngày")
    r.status = "duyet" if approve else "tu_choi"
    r.approved_by, r.approved_at, r.decision_note = u.username, datetime.now(), note[:300]
    if approve and r.kind != "tang_ca":
        _apply_leave_to_attendance(db, r)
    R.audit(db, u.username, u.role, "duyet_don_nhan_su" if approve else "tu_choi_don_nhan_su", f"don:{r.id}",
            after={"nhan_vien": e.code if e else "", "loai": r.kind, "so_ngay": r.days, "ghi_chu": note})
    db.commit()
    return r


def _apply_leave_to_attendance(db: Session, r: LeaveRequest) -> None:
    """Ghi các ngày nghỉ đã duyệt vào bảng chấm công (nửa ngày thì công = 0,5)."""
    total_days = (r.date_to - r.date_from).days + 1
    half = r.days < total_days                              # xin ít ngày hơn khoảng ngày → coi là nghỉ nửa ngày
    work = 0.5 if half and total_days == 1 else 0.0
    kind = r.kind if r.kind in ATT_KINDS else "lam_viec"
    if r.kind == "cong_tac":
        kind, work = "cong_tac", 1.0                        # đi công tác vẫn tính đủ công
    for i in range(total_days):
        day = r.date_from + timedelta(days=i)
        row = db.execute(select(AttendanceDay).where(AttendanceDay.employee_id == r.employee_id,
                                                     AttendanceDay.day == day)).scalar_one_or_none()
        if row is None:
            row = AttendanceDay(employee_id=r.employee_id, day=day)
            db.add(row)
        row.kind, row.work, row.leave_id = kind, work, r.id
        row.note = (LEAVE_KINDS.get(r.kind, {}).get("ten", r.kind))[:200]


# ---------- Bảng chấm công ----------

def attendance_sheet(db: Session, period: str, department: str = "") -> dict:
    """Bảng chấm công tháng: mỗi nhân viên một dòng, ngày nào có bản ghi thì lấy, còn lại mặc định đi làm
    (trừ thứ Bảy/Chủ nhật) – giống cách MISA hiển thị lưới chấm công để HCNS soát và sửa tay."""
    days = month_days(period)
    q = select(Employee).where(Employee.active == True)
    if department:
        q = q.where(Employee.department == department)
    emps = list(db.execute(q.order_by(Employee.code)).scalars())
    ids = [e.id for e in emps]
    recs: dict[tuple[int, date], AttendanceDay] = {}
    if ids:
        for a in db.execute(select(AttendanceDay).where(AttendanceDay.employee_id.in_(ids),
                                                        AttendanceDay.day >= days[0], AttendanceDay.day <= days[-1])).scalars():
            recs[(a.employee_id, a.day)] = a
    rows = []
    for e in emps:
        cells, work, leave, unpaid, ot = [], 0.0, 0.0, 0.0, 0.0
        for d in days:
            a = recs.get((e.id, d))
            if a:
                k, w, o = a.kind, a.work, a.ot_hours
            elif d.weekday() >= 5:
                k, w, o = "le", 0.0, 0.0                     # cuối tuần: không tính công, HCNS sửa nếu có trực
            else:
                k, w, o = "lam_viec", 1.0, 0.0
            cells.append({"day": d.day, "kind": k, "work": w, "ot_hours": o})
            work += w; ot += o
            if k == "phep_nam":
                leave += 1
            elif k in ("khong_luong", "vang"):
                unpaid += 1
        rows.append({"employee_id": e.id, "code": e.code, "full_name": e.full_name, "department": e.department,
                     "cells": cells, "work_days": round(work, 1), "leave_days": leave, "unpaid_days": unpaid,
                     "ot_hours": round(ot, 1)})
    standard = sum(1 for d in days if d.weekday() < 5)
    return {"period": period, "days": [{"day": d.day, "weekday": d.weekday(), "weekend": d.weekday() >= 5} for d in days],
            "standard_days": standard, "rows": rows, "kinds": ATT_KINDS}


def set_attendance(db: Session, u: User, employee_id: int, day: date, kind: str, work: float, ot_hours: float, note: str) -> AttendanceDay:
    if kind not in ATT_KINDS:
        raise ValueError(f"Loại chấm công {kind} không hợp lệ")
    row = db.execute(select(AttendanceDay).where(AttendanceDay.employee_id == employee_id,
                                                 AttendanceDay.day == day)).scalar_one_or_none()
    if row is None:
        row = AttendanceDay(employee_id=employee_id, day=day)
        db.add(row)
    row.kind, row.work, row.ot_hours, row.note, row.updated_by = kind, float(work), float(ot_hours), note[:200], u.username
    db.commit()
    return row


# ---------- Người phụ thuộc & giảm trừ gia cảnh ----------

def dependents_of(db: Session, employee_id: int, period: str | None = None) -> list[Dependent]:
    rows = db.execute(select(Dependent).where(Dependent.employee_id == employee_id, Dependent.active == True)
                      .order_by(Dependent.id)).scalars().all()
    if not period:
        return rows
    return [d for d in rows
            if (not d.from_period or d.from_period <= period) and (not d.to_period or d.to_period >= period)]


def pit_deduction(db: Session, employee_id: int, period: str) -> dict:
    """Giảm trừ gia cảnh của một người trong kỳ: bản thân + số người phụ thuộc đang hiệu lực."""
    self_amt = _param(db, PIT_SELF_KEY, PIT_SELF_DEFAULT)
    dep_amt = _param(db, PIT_DEP_KEY, PIT_DEP_DEFAULT)
    deps = dependents_of(db, employee_id, period)
    return {"period": period, "self": self_amt, "dependent_rate": dep_amt, "dependents": len(deps),
            "dependent_total": round(dep_amt * len(deps), 0), "total": round(self_amt + dep_amt * len(deps), 0),
            "names": [d.full_name for d in deps]}


# ---------- Hồ sơ ----------

def profile_of(db: Session, employee_id: int) -> EmployeeProfile | None:
    return db.execute(select(EmployeeProfile).where(EmployeeProfile.employee_id == employee_id)).scalar_one_or_none()


PROFILE_REQUIRED = ("id_number", "dob", "permanent_address", "phone", "tax_code", "bank_account")


def save_profile(db: Session, u: User, employee_id: int, data: dict) -> EmployeeProfile:
    p = profile_of(db, employee_id)
    if p is None:
        p = EmployeeProfile(employee_id=employee_id)
        db.add(p)
    for k, v in data.items():
        if v is None or not hasattr(p, k) or k in ("id", "employee_id"):
            continue
        setattr(p, k, v)
    p.updated_by = u.username
    R.audit(db, u.username, u.role, "cap_nhat_ho_so_nhan_su", f"nv:{employee_id}", after={"truong": sorted(data.keys())})
    db.commit()
    return p


def profile_completeness(db: Session, employee_id: int) -> dict:
    """Mức độ đầy đủ hồ sơ – MISA có thanh '% hoàn thiện hồ sơ', ở đây liệt kê thẳng trường còn thiếu."""
    p = profile_of(db, employee_id)
    missing = [f for f in PROFILE_REQUIRED if not getattr(p, f, None)] if p else list(PROFILE_REQUIRED)
    return {"employee_id": employee_id, "has_profile": p is not None, "missing": missing,
            "percent": round(100 * (len(PROFILE_REQUIRED) - len(missing)) / len(PROFILE_REQUIRED))}
