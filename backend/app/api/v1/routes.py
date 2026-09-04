"""API v1 – toàn bộ endpoint JSON cho web/app/n8n."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth, Gate
from app.api import schemas as S
from app.core.security import verify_password, create_token, hash_password
from app.models.core import User, Tour, ServiceRequest, Booking, Param, Alert, AuditLog, ROLES, TOUR_TYPES, TOUR_STATUS
from app.services import rules as R
from app.services import tours as T

router = APIRouter(prefix="/api/v1")


def user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "role_name": ROLES.get(u.role, u.role), "department": u.department}


# ---------- auth ----------
@router.post("/auth/login", response_model=S.Token, tags=["auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.username == form.username, User.active == True)).scalars().first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    R.audit(db, u.username, u.role, "dang_nhap", "user"); db.commit()
    return {"access_token": create_token(u.username, u.role), "token_type": "bearer", "user": user_out(u)}


@router.get("/auth/me", tags=["auth"])
def me(u: User = Depends(current_user)):
    return user_out(u)


@router.post("/auth/password", tags=["auth"])
def change_password(data: S.PasswordChange, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, u.password_hash): raise HTTPException(400, "Mật khẩu cũ không đúng")
    u.password_hash = hash_password(data.new_password)
    R.audit(db, u.username, u.role, "doi_mat_khau", "user"); db.commit()
    return {"ok": True}


@router.get("/meta", tags=["meta"])
def meta(db: Session = Depends(get_db)):
    return {"roles": ROLES, "tour_types": TOUR_TYPES, "tour_status": TOUR_STATUS,
            "params": {k: R.get_param(db, k) for k, *_ in R.DEFAULT_PARAMS}}


@router.get("/users", tags=["users"])
def users(role: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(User).where(User.active == True)
    if role: q = q.where(User.role.in_(role.split(",")))
    return [user_out(x) for x in db.execute(q.order_by(User.id)).scalars()]


# ---------- dashboard ----------
@router.get("/dashboard", tags=["dashboard"])
def dashboard(u: User = Depends(current_user), db: Session = Depends(get_db)):
    tours = db.execute(select(Tour)).scalars().all()
    alerts = [a for a in db.execute(select(Alert).where(Alert.resolved == False).order_by(desc(Alert.created_at))).scalars()
              if u.role in a.to_roles.split(",") or u.role in ("chutich", "tgd", "cntt", "bks")]
    todo = []
    for t in tours:
        for a in T.allowed_actions(db, t, u):
            if a in ("confirm", "sign", "approve", "close", "kt_confirm", "cntt_check"):
                todo.append({"tour_id": t.id, "code": t.code, "name": t.name, "action": a})
    counts = {}
    for t in tours: counts[t.status] = counts.get(t.status, 0) + 1
    return {"counts": counts, "n_tours": len(tours), "todo": todo,
            "pending_requests": db.execute(select(func.count()).select_from(ServiceRequest).where(ServiceRequest.booking_id == None)).scalar(),
            "pending_params": db.execute(select(func.count()).select_from(Param).where(Param.status == "pending")).scalar(),
            "alerts": [alert_out(a) for a in alerts], "threshold": R.get_param(db, "nguong_bien")}


# ---------- tours ----------
@router.get("/tours", tags=["tours"])
def list_tours(status: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Tour).order_by(desc(Tour.start_date))
    if status: q = q.where(Tour.status.in_(status.split(",")))
    out = []
    for t in db.execute(q).scalars():
        v = T.tour_view(db, t)
        v.pop("bookings", None)
        out.append(v)
    return out


@router.post("/tours", tags=["tours"], status_code=201)
def create_tour(data: S.TourCreate, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return T.tour_view(db, T.create(db, u, data), u)


def _tour(db: Session, tid: int) -> Tour:
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    return t


@router.get("/tours/{tid}", tags=["tours"])
def get_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid)
    v = T.tour_view(db, t, u)
    v["audit"] = [audit_out(l) for l in db.execute(select(AuditLog).where(AuditLog.entity == f"tour:{t.code}").order_by(desc(AuditLog.id))).scalars()]
    return v


@router.put("/tours/{tid}", tags=["tours"])
def edit_tour(tid: int, data: S.TourEdit, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return T.tour_view(db, T.edit(db, u, _tour(db, tid), data), u)


@router.post("/tours/{tid}/submit", tags=["tours"])
def submit_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.submit(db, u, _tour(db, tid))}


@router.post("/tours/{tid}/confirm", tags=["tours"])
def confirm_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.confirm(db, u, _tour(db, tid))}


@router.post("/tours/{tid}/approve", tags=["tours"])
def approve_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.approve(db, u, _tour(db, tid))}


@router.post("/tours/{tid}/d7", tags=["tours"])
def d7_tour(tid: int, data: S.D7Decision, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.d7(db, u, _tour(db, tid), data.decision)}


@router.post("/tours/{tid}/close", tags=["tours"])
def close_tour(tid: int, data: S.TourClose, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.close(db, u, _tour(db, tid), data)}


@router.post("/tours/{tid}/kt-confirm", tags=["tours"])
def kt_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.kt_confirm(db, u, _tour(db, tid))}


@router.post("/tours/{tid}/cntt-check", tags=["tours"])
def cntt_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.cntt_check(db, u, _tour(db, tid))}


# ---------- requests & bookings ----------
def req_out(r: ServiceRequest) -> dict:
    return {"id": r.id, "tour_id": r.tour_id, "tour_code": r.tour.code if r.tour else "", "sales_name": r.sales.full_name if r.sales else "",
            "customer_name": r.customer_name, "customer_phone": r.customer_phone, "source": r.source, "care_note": r.care_note, "pax": r.pax,
            "campaign_code": r.campaign_code, "promo_code": r.promo_code, "discount": r.discount, "created_at": r.created_at, "booking_id": r.booking_id,
            "waited_minutes": int((datetime.now() - r.created_at).total_seconds() / 60)}


def booking_out(b: Booking) -> dict:
    return {"id": b.id, "code": b.code, "tour_id": b.tour_id, "tour_code": b.tour.code if b.tour else "", "customer_name": b.customer_name,
            "customer_phone": b.customer_phone, "source": b.source, "pax": b.pax, "amount": b.amount, "discount": b.discount, "promo_code": b.promo_code,
            "sales_name": b.sales.full_name if b.sales else "", "sla_minutes": b.sla_minutes, "sla_ok": b.sla_ok, "counts_for_target": b.counts_for_target, "created_at": b.created_at}


@router.get("/requests", tags=["bookings"])
def list_requests(open_only: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(ServiceRequest).order_by(desc(ServiceRequest.created_at))
    if open_only: q = q.where(ServiceRequest.booking_id == None)
    return [req_out(r) for r in db.execute(q).scalars()]


@router.post("/requests", tags=["bookings"], status_code=201)
def create_request(data: S.RequestCreate, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = T.create_request(db, u, data)
    return {"request": req_out(r), "message": f"Đã gửi yêu cầu #{r.id} sang Điều hành (đồng hồ {R.get_param(db, 'sla_booking_phut'):.0f} phút bắt đầu)"}


@router.post("/requests/{rid}/booking", tags=["bookings"], status_code=201)
def create_booking(rid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(ServiceRequest, rid)
    if not r: raise HTTPException(404, "Không có yêu cầu")
    b, msg = T.create_booking(db, u, r)
    return {"booking": booking_out(b), "message": msg}


@router.get("/bookings", tags=["bookings"])
def list_bookings(limit: int = 100, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [booking_out(b) for b in db.execute(select(Booking).order_by(desc(Booking.created_at)).limit(limit)).scalars()]


# ---------- params ----------
def param_out(p: Param) -> dict:
    return {"id": p.id, "key": p.key, "value": p.value, "label": p.label, "unit": p.unit, "effective_from": p.effective_from, "source": p.source,
            "status": p.status, "signed_chutich": p.signed_chutich, "signed_tgd": p.signed_tgd, "proposed_by": p.proposed_by, "created_at": p.created_at}


@router.get("/params", tags=["params"])
def list_params(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [param_out(p) for p in db.execute(select(Param).order_by(Param.key, desc(Param.effective_from), desc(Param.id))).scalars()]


@router.post("/params", tags=["params"], status_code=201)
def propose_param(data: S.ParamPropose, u: User = Depends(require_roles("tp_dh", "gd_kd", "ptgd_doan", "ptgd_mkt", "ketoan", "hcns", "cntt", "tgd", "chutich")), db: Session = Depends(get_db)):
    ref = db.execute(select(Param).where(Param.key == data.key).order_by(desc(Param.id))).scalars().first()
    if not ref: raise Gate("THAM_SO", "Không có tham số này")
    try: float(data.value)
    except ValueError: raise Gate("THAM_SO", "Giá trị phải là số")
    p = Param(key=data.key, value=data.value, label=ref.label, unit=ref.unit, effective_from=data.effective_from,
              source=data.source or ref.source, status="pending", proposed_by=u.username)
    db.add(p); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_tham_so", f"param:{data.key}", before={"value": ref.value}, after={"value": data.value, "hieu_luc": str(data.effective_from)}); db.commit()
    return {"param": param_out(p), "message": "Đã trình đề xuất – chờ Chủ tịch và TGĐ ký (Điều 1 MHQT)"}


@router.post("/params/{pid}/sign", tags=["params"])
def sign_param(pid: int, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    p = db.get(Param, pid)
    if not p or p.status != "pending": raise Gate("TRANG_THAI", "Không ở trạng thái chờ ký")
    setattr(p, f"signed_{u.role}", True)
    R.audit(db, u.username, u.role, "ky_tham_so", f"param:{p.key}", after={"id": p.id, "value": p.value})
    if p.signed_chutich and p.signed_tgd:
        p.status = "active"
        R.audit(db, u.username, u.role, "tham_so_hieu_luc", f"param:{p.key}", after={"value": p.value, "hieu_luc": str(p.effective_from)})
    db.commit()
    return {"param": param_out(p), "message": "Đã ký" + (" – tham số có hiệu lực theo ngày đã ghi" if p.status == "active" else ", chờ chữ ký còn lại")}


# ---------- alerts / robots ----------
def alert_out(a: Alert) -> dict:
    return {"id": a.id, "kind": a.kind, "level": a.level, "ref": a.ref, "message": a.message, "to_roles": a.to_roles, "created_at": a.created_at, "resolved": a.resolved}


@router.get("/alerts", tags=["alerts"])
def list_alerts(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [alert_out(a) for a in db.execute(select(Alert).order_by(Alert.resolved, desc(Alert.created_at))).scalars()]


@router.post("/alerts/{aid}/resolve", tags=["alerts"])
def resolve_alert(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.get(Alert, aid)
    if not a: raise HTTPException(404, "Không có cảnh báo")
    a.resolved = True
    R.audit(db, u.username, u.role, "dong_canh_bao", f"alert:{aid}", after={"kind": a.kind, "ref": a.ref}); db.commit()
    return {"message": "Đã đóng cảnh báo"}


@router.post("/robots/run", tags=["alerts"])
def run_robots(u: User = Depends(require_roles("cntt", "tgd", "chutich")), db: Session = Depends(get_db)):
    n = R.run_robots(db)
    R.audit(db, u.username, u.role, "chay_robot", "robot", after={"canh_bao_moi": n}); db.commit()
    return {"new_alerts": n, "message": f"Robot đã chạy, {n} cảnh báo mới"}


# ---------- audit / payroll ----------
def audit_out(l: AuditLog) -> dict:
    return {"id": l.id, "ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action, "entity": l.entity, "before": l.before, "after": l.after, "hash": l.hash}


@router.get("/audit", tags=["audit"])
def list_audit(limit: int = 300, u: User = Depends(current_user), db: Session = Depends(get_db)):
    ok, n, msg = R.verify_chain(db)
    return {"chain_ok": ok, "records": n, "chain_message": msg,
            "rows": [audit_out(l) for l in db.execute(select(AuditLog).order_by(desc(AuditLog.id)).limit(limit)).scalars()]}


@router.get("/payroll", tags=["payroll"])
def payroll(ym: str | None = None, u: User = Depends(require_roles("ketoan", "hcns", "tgd", "chutich", "cntt", "tp_dh")), db: Session = Depends(get_db)):
    ym = ym or date.today().strftime("%Y-%m")
    y, m = map(int, ym.split("-"))
    rows = R.monthly_payroll_draft(db, y, m)
    return {"ym": ym, "rows": rows, "total": sum(r["tien"] for r in rows)}


# ---------- robot API (n8n) ----------
@router.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    ok, n, msg = R.verify_chain(db)
    return {"status": "ok", "audit_chain_ok": ok, "audit_records": n, "time": datetime.now().isoformat()}


@router.post("/robot/run", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_run(db: Session = Depends(get_db)):
    n = R.run_robots(db)
    R.audit(db, "robot", "robot", "chay_robot_api", "robot", after={"canh_bao_moi": n}); db.commit()
    return {"new_alerts": n}


@router.get("/robot/alerts", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_alerts(db: Session = Depends(get_db)):
    return [alert_out(a) for a in db.execute(select(Alert).where(Alert.resolved == False)).scalars()]


@router.get("/robot/tours", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_tours(db: Session = Depends(get_db)):
    out = []
    for t in db.execute(select(Tour)).scalars():
        v = T.tour_view(db, t); v.pop("bookings", None); out.append(v)
    return out
