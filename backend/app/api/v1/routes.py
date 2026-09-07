"""API v1 – toàn bộ endpoint JSON cho web/app/n8n."""
from datetime import timedelta, date, datetime
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
from app.services import bookings as BK
from app.services import access as AC

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
    return {"access_token": create_token(u.username, u.role), "token_type": "bearer", "user": me(u)}


@router.get("/auth/me", tags=["auth"])
def me(u: User = Depends(current_user)):
    return {**user_out(u), "hidden_menus": AC.hidden_menus_for(u), "can_see_cost": AC.can_see_cost(u), "read_only": u.role in AC.READ_ONLY_ROLES,
            "can_create_request": u.role in AC.REQUEST_CREATE_ROLES, "can_create_booking": u.role in AC.OPERATIONS}


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
_DASH_CACHE: dict = {}   # role → (ts, payload) – bảng điều khiển tính nặng (10.000+ booking), giữ 5 phút


@router.get("/dashboard", tags=["dashboard"])
def dashboard(refresh: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db)):
    import time
    key = (u.role, u.id if u.role in ("nv_dh", "tp_dh", "nv_kd") else 0)
    hit = _DASH_CACHE.get(key)
    if hit and not refresh and time.time() - hit[0] < 300:
        return {**hit[1], "cached": True}
    # việc chờ tôi xử lý: chỉ xét tour đang trong luồng (không quét tour đã kết thúc / đã duyệt hàng loạt)
    active = db.execute(select(Tour).where(Tour.status.in_(["nhap", "cho_xac_nhan", "cho_duyet", "da_dong_so", "kt_xac_nhan"]))).scalars().all()
    if u.role in ("chutich", "tp_dh"):
        active += db.execute(select(Tour).where(Tour.status == "da_duyet", Tour.chairman_run_decision == False, Tour.start_date >= date.today(), Tour.start_date <= date.today() + timedelta(days=7))).scalars().all()
    if u.role in ("nv_dh", "tp_dh"):
        active += db.execute(select(Tour).where(Tour.status.in_(["ket_thuc", "da_duyet"]), Tour.operator_id == u.id, Tour.end_date <= date.today())).scalars().all()
    todo = []
    for t in active:
        for a in T.allowed_actions(db, t, u):
            if a in ("confirm", "sign", "approve", "close", "kt_confirm", "cntt_check"):
                todo.append({"tour_id": t.id, "code": t.code, "name": t.name, "action": a})
    counts = {st: n for st, n in db.execute(select(Tour.status, func.count()).group_by(Tour.status)).all()}
    alerts = [a for a in db.execute(select(Alert).where(Alert.resolved == False).order_by(desc(Alert.created_at)).limit(300)).scalars()
              if u.role in a.to_roles.split(",") or u.role in ("chutich", "tgd", "cntt", "bks")][:60]
    from app.services import dashboard as DB_
    extra = DB_.build(db, u)
    payload = {"counts": counts, "n_tours": sum(counts.values()), "todo": todo[:100],
               "pending_requests": db.execute(select(func.count()).select_from(ServiceRequest).where(ServiceRequest.booking_id == None)).scalar(),
               "pending_params": db.execute(select(func.count()).select_from(Param).where(Param.status == "pending")).scalar(),
               "alerts": [alert_out(a) for a in alerts], "threshold": R.get_param(db, "nguong_bien"), **extra}
    _DASH_CACHE[key] = (time.time(), payload)
    return payload


# ---------- tours ----------
@router.get("/tours", tags=["tours"])
def list_tours(status: str | None = None, q: str = "", month: str = "", limit: int = 300, offset: int = 0, tour_type: str = "", mang: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh sách tour có phân trang/tìm kiếm (mặc định 300 chuyến mới nhất) – 1.200+ tour nhập từ Vietrip. Mặc định ẩn dịch vụ lẻ (KLE) trừ khi tìm theo mã hoặc chọn tour_type."""
    from sqlalchemy import or_
    qs = select(Tour).order_by(desc(Tour.start_date))
    from app.services import segments as SEG
    try:
        cond = SEG.tour_cond(mang)          # mang=le / doan – lọc theo mảng kinh doanh
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if cond is not None: qs = qs.where(cond)
    if tour_type: qs = qs.where(Tour.tour_type == tour_type)
    elif not (q and q.upper().startswith("KLE")): qs = qs.where(Tour.tour_type != "non_package")
    if status: qs = qs.where(Tour.status.in_(status.split(",")))
    if q: qs = qs.where(or_(Tour.code.ilike(f"%{q}%"), Tour.name.ilike(f"%{q}%"), Tour.product_code.ilike(f"%{q}%")))
    if month:
        y, m = map(int, month.split("-")); qs = qs.where(func.extract("year", Tour.start_date) == y, func.extract("month", Tour.start_date) == m)
    out = []
    for t in db.execute(qs.offset(offset).limit(min(limit, 1000))).scalars():
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
    if not AC.can_see_cost(u):   # Kinh doanh / HCNS: không xem cơ cấu chi phí, quyết toán, bút toán
        for k in ("settlement", "fixed_cost", "var_cost_per_pax", "actual_cost", "promo_value", "calc", "justification"): v[k] = None
        vis = AC.sales_ids_visible(db, u)
        if vis is not None: v["bookings"] = [b for b in v.get("bookings", []) if b.get("sales_id") in vis]
    else:
        v["audit"] = [audit_out(l) for l in db.execute(select(AuditLog).where(AuditLog.entity == f"tour:{t.code}").order_by(desc(AuditLog.id))).scalars()]
    return v


@router.put("/tours/{tid}", tags=["tours"])
def edit_tour(tid: int, data: S.TourEdit, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return T.tour_view(db, T.edit(db, u, _tour(db, tid), data), u)


@router.post("/tours/{tid}/submit", tags=["tours"])
def submit_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.submit(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/confirm", tags=["tours"])
def confirm_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.confirm(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/approve", tags=["tours"])
def approve_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.approve(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/d7", tags=["tours"])
def d7_tour(tid: int, data: S.D7Decision, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.d7(db, u, _tour(db, tid), data.decision, getattr(data, "note", "") or "")}


@router.post("/tours/{tid}/close", tags=["tours"])
def close_tour(tid: int, data: S.TourClose, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.close(db, u, _tour(db, tid), data, getattr(data, "note", "") or "")}


@router.post("/tours/{tid}/kt-confirm", tags=["tours"])
def kt_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.kt_confirm(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/cntt-check", tags=["tours"])
def cntt_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.cntt_check(db, u, _tour(db, tid), (data.note if data else ""))}


# ---------- requests & bookings ----------
def req_out(r: ServiceRequest, sla: int = 120, db: Session | None = None) -> dict:
    """Một yêu cầu luôn phải trả về: ai chịu trách nhiệm nhận việc, hạn xử lý và bước tiếp theo –
    không chỉ hiển thị thời gian chờ (Đề xuất 06/9 mục 4)."""
    t = r.tour
    waited = int((datetime.now() - r.created_at).total_seconds() / 60)
    deadline = r.created_at + timedelta(minutes=sla)
    op = t.operator if t and t.operator else None
    bk = db.get(Booking, r.booking_id) if (db and r.booking_id) else None
    if r.booking_id:
        view, sla_state = "hoan_tat", "hoan_tat"
        used = bk.sla_minutes if bk else None
        next_step = f"Đã tạo booking {bk.code}" + (f" sau {used} phút" if used is not None else "") if bk else "Đã tạo booking"
    else:
        ratio = waited / sla if sla else 0
        view = sla_state = "qua_han" if ratio >= 1 else "sap_qua_han" if ratio >= 0.75 else "cho_phan_cong"
        next_step = f"Điều hành tạo booking – phụ trách {op.full_name}" if op else "Điều hành tạo booking – chưa xác định người phụ trách"
    return {"id": r.id, "tour_id": r.tour_id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
            "tour_start": t.start_date if t else None, "sales_id": r.sales_id, "sales_name": r.sales.full_name if r.sales else "",
            "operator_id": op.id if op else None, "operator_name": op.full_name if op else "",
            "customer_name": r.customer_name, "customer_phone": r.customer_phone, "source": r.source, "care_note": r.care_note, "pax": r.pax,
            "campaign_code": r.campaign_code, "promo_code": r.promo_code, "discount": r.discount, "created_at": r.created_at, "booking_id": r.booking_id,
            "booking_code": bk.code if bk else "", "amount": max(0.0, (t.price_per_pax * r.pax - r.discount) if t else 0.0),
            "waited_minutes": waited, "deadline": deadline, "sla_minutes": sla, "sla_state": sla_state, "view": view, "next_step": next_step}


def booking_out(b: Booking) -> dict:
    """sla_known=False: booking nhập từ hệ thống khác (Vietrip) không mang mốc tiếp nhận yêu cầu
    → giao diện ghi 'Chưa đủ dữ liệu', không hiển thị là xử lý trong 0 phút."""
    return {"id": b.id, "code": b.code, "tour_id": b.tour_id, "sales_id": b.sales_id, "tour_code": b.tour.code if b.tour else "", "customer_name": b.customer_name,
            "customer_phone": b.customer_phone, "source": b.source, "pax": b.pax, "amount": b.amount, "discount": b.discount, "promo_code": b.promo_code,
            "sales_name": b.sales.full_name if b.sales else "", "sla_minutes": b.sla_minutes, "sla_ok": b.sla_ok,
            "sla_known": bool(b.request_id),
            "counts_for_target": b.counts_for_target, "created_at": b.created_at, "paid": b.paid, "due": b.amount - b.discount - b.paid,
            "adl": b.adl, "chd": b.chd, "inf": b.inf, "vietrip_id": b.vietrip_id, "tour_start": b.tour.start_date if b.tour else None, **BK.booking_view(b)}


@router.get("/mang", tags=["bookings"])
def mang_catalog(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh mục mảng kinh doanh + đối chiếu hai quy tắc xác định mảng Đoàn.

    Mảng Đoàn được nhận theo HỢP của hai quy tắc (loại chuyến là đoàn, HOẶC mã tour bắt đầu bằng MICE) nên
    không tour nào bị rơi khỏi màn hình phòng Đoàn. Phần đối chiếu chỉ đích danh tour mà hai quy tắc bất đồng
    để Kinh doanh sửa dữ liệu gốc."""
    from app.services import segments as SEG
    AC.require(u, AC.BOOKING_ROLES, "danh mục mảng kinh doanh")
    return {"mang": SEG.MANG, "quy_tac_doan": {"loai_chuyen": list(SEG.DOAN_TYPES), "tien_to_ma": SEG.MICE_PREFIX},
            "doi_chieu": SEG.lech_quy_tac(db)}


@router.get("/requests", tags=["bookings"])
def list_requests(open_only: bool = False, view: str = "", mang: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """view: cho_phan_cong / sap_qua_han / qua_han / hoan_tat / cua_toi (rỗng = tất cả)."""
    AC.require(u, AC.BOOKING_ROLES, "yêu cầu đặt dịch vụ")
    q = select(ServiceRequest).order_by(desc(ServiceRequest.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: q = q.where(ServiceRequest.sales_id.in_(vis))
    if open_only: q = q.where(ServiceRequest.booking_id == None)
    from app.services import segments as SEG
    try:
        cond = SEG.tour_cond(mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if cond is not None: q = q.join(Tour, Tour.id == ServiceRequest.tour_id).where(cond)
    sla = int(R.get_param(db, "sla_booking_phut"))
    rows = [req_out(r, sla, db) for r in db.execute(q).scalars()]
    if view == "cua_toi": rows = [r for r in rows if u.id in (r["sales_id"], r["operator_id"])]
    elif view: rows = [r for r in rows if r["view"] == view]
    return rows


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


def _bookings_query(db: Session, u: User, q: str, status: str, tour_id: int | None, mang: str = ""):
    from app.services import segments as SEG
    qs = select(Booking).order_by(desc(Booking.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qs = qs.where(Booking.sales_id.in_(vis))   # NV KD: của mình; trưởng nhóm: của nhóm
    if tour_id: qs = qs.where(Booking.tour_id == tour_id)
    cond = SEG.tour_cond(mang)                       # mảng nằm ở TOUR nên phải nối bảng tours
    if cond is not None or q:
        qs = qs.join(Tour, Tour.id == Booking.tour_id)   # nối MỘT lần, kể cả khi vừa lọc mảng vừa tìm kiếm
    if cond is not None: qs = qs.where(cond)
    if q:
        like = f"%{q.strip()}%"
        qs = qs.where((Booking.code.ilike(like)) | (Booking.customer_name.ilike(like)) | (Booking.customer_phone.ilike(like)) | (Tour.code.ilike(like)))
    if status == "cancelled": qs = qs.where(Booking.cancelled == True)
    elif status == "locked": qs = qs.where(Booking.locked == True, Booking.cancelled == False)
    elif status in ("unpaid", "depo", "paid"): qs = qs.where(Booking.pmt_status == status.upper(), Booking.cancelled == False)
    elif status == "due": qs = qs.where(Booking.cancelled == False, Booking.pmt_status != "PAID")
    return qs


@router.get("/bookings", tags=["bookings"])
def list_bookings(limit: int = 100, offset: int = 0, q: str = "", status: str = "", tour_id: int | None = None, mang: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """status: unpaid / depo / paid / cancelled / locked / due (còn phải thu, chưa hủy).
    Danh sách có phân trang – tổng số lấy ở /bookings/count, KHÔNG suy từ số dòng đang hiển thị (B7)."""
    AC.require(u, AC.BOOKING_ROLES, "danh sách booking")
    try:
        qs = _bookings_query(db, u, q, status, tour_id, mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return [booking_out(b) for b in db.execute(qs.offset(offset).limit(min(limit, 1000))).scalars()]


@router.get("/bookings/count", tags=["bookings"])
def count_bookings(q: str = "", status: str = "", tour_id: int | None = None, mang: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Tổng số booking trong phạm vi người dùng được xem và số thỏa bộ lọc – để giao diện không lấy
    số dòng đang tải làm tổng toàn hệ thống (Ý kiến thẩm định 06/9/2026, B7)."""
    AC.require(u, AC.BOOKING_ROLES, "danh sách booking")
    def n(query):
        return db.execute(select(func.count()).select_from(query.order_by(None).subquery())).scalar() or 0
    try:
        # "total" giữ nguyên phạm vi MẢNG đang xem, chỉ bỏ bộ lọc tìm kiếm/trạng thái – nếu không thì phòng Đoàn
        # thấy "12 / 10.074" và tưởng mình đang bị giấu dữ liệu.
        return {"total": n(_bookings_query(db, u, "", "", None, mang)),
                "filtered": n(_bookings_query(db, u, q, status, tour_id, mang))}
    except ValueError as ex:
        raise HTTPException(422, str(ex))


def _booking(db: Session, bid: int) -> Booking:
    b = db.get(Booking, bid)
    if not b: raise HTTPException(404, "Không có booking")
    return b


@router.get("/bookings/{bid}", tags=["bookings"])
def get_booking(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = _booking(db, bid)
    AC.require(u, AC.BOOKING_ROLES, "booking")
    vis = AC.sales_ids_visible(db, u)
    if vis is not None and b.sales_id not in vis: raise HTTPException(403, "Chỉ xem được booking do mình / nhóm mình phụ trách")
    v = booking_out(b)
    from app.models.payments import Receipt, Retention
    v["receipts"] = [{"id": r.id, "code": r.code, "amount": r.amount, "method": r.method, "status": r.status, "payer": r.payer, "note": r.note, "created_at": r.created_at} for r in db.execute(select(Receipt).where(Receipt.booking_id == b.id).order_by(Receipt.id)).scalars()]
    v["retentions"] = [BK.retention_out(r, db) for r in db.execute(select(Retention).where(Retention.booking_id == b.id)).scalars()]
    return v


@router.put("/bookings/{bid}", tags=["bookings"])
def update_booking(bid: int, data: S.BookingCustomerIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return booking_out(BK.update_customer(db, u, _booking(db, bid), data.model_dump(exclude_none=True)))


@router.post("/bookings/{bid}/cancel", tags=["bookings"])
def cancel_booking(bid: int, data: S.BookingCancelIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return BK.cancel(db, u, _booking(db, bid), data.reason, data.charge, data.retain, data.expires_days)


@router.post("/bookings/{bid}/unlock", tags=["bookings"])
def unlock_booking(bid: int, data: S.ActionNote, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": BK.unlock(db, u, _booking(db, bid), data.note)}


@router.post("/bookings/{bid}/lock", tags=["bookings"])
def lock_booking(bid: int, data: S.ActionNote, u: User = Depends(require_roles("nv_dh", "tp_dh", "gd_kd", "tp_kd", "cntt")), db: Session = Depends(get_db)):
    b = _booking(db, bid); BK.lock(db, b, data.note or f"Khóa bởi {u.username}", u.username); db.commit()
    return {"message": f"Đã khóa {b.code}"}


@router.post("/bookings/check", tags=["bookings"])
def bookings_check(u: User = Depends(require_roles("tp_dh", "nv_dh", "gd_kd", "tp_kd", "ketoan", "cntt", "tgd")), db: Session = Depends(get_db)):
    return BK.robot_check(db)


@router.post("/robot/bookings/check", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_bookings_check(db: Session = Depends(get_db)):
    return BK.robot_check(db)


# ---------- tiền bảo lưu ----------
@router.get("/retentions", tags=["bookings"])
def list_retentions(status: str = "hieu_luc", q: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.models.payments import Retention
    AC.require(u, AC.BOOKING_ROLES, "tiền bảo lưu")
    qs = select(Retention).order_by(desc(Retention.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qs = qs.join(Booking, Booking.id == Retention.booking_id).where(Booking.sales_id.in_(vis))
    if status and status != "all": qs = qs.where(Retention.status == status)
    if q:
        like = f"%{q.strip()}%"; qs = qs.where((Retention.code.ilike(like)) | (Retention.customer_name.ilike(like)) | (Retention.customer_phone.ilike(like)) | (Retention.tour_code.ilike(like)))
    return {"summary": BK.retention_summary(db), "rows": [BK.retention_out(r, db) for r in db.execute(qs.limit(500)).scalars()]}


def _ret(db: Session, rid: int):
    from app.models.payments import Retention
    r = db.get(Retention, rid)
    if not r: raise HTTPException(404, "Không có khoản bảo lưu")
    return r


@router.post("/retentions/{rid}/apply", tags=["bookings"])
def apply_retention(rid: int, data: S.RetentionApplyIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    rc = BK.apply_retention(db, u, _ret(db, rid), _booking(db, data.booking_id), data.amount)
    return {"message": f"Đã dùng {rc.amount:,.0f} đ bảo lưu cho booking – phiếu thu {rc.code}", "receipt": rc.code}


@router.post("/retentions/{rid}/refund", tags=["bookings"])
def refund_retention(rid: int, data: S.RetentionRefundIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    pr = BK.refund_retention(db, u, _ret(db, rid), data.amount, data.note)
    return {"message": f"Đã lập đề nghị hoàn tiền {pr.code} ({pr.amount:,.0f} đ) – chờ xác nhận/duyệt/chi", "request": pr.code}


@router.post("/retentions/{rid}/cancel", tags=["bookings"])
def cancel_retention(rid: int, data: S.ActionNote, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": BK.cancel_retention(db, u, _ret(db, rid), data.note)}


# ---------- params ----------
def param_out(p: Param) -> dict:
    return {"id": p.id, "key": p.key, "value": p.value, "label": p.label, "unit": p.unit, "effective_from": p.effective_from, "source": p.source,
            "status": p.status, "signed_chutich": p.signed_chutich, "signed_tgd": p.signed_tgd, "proposed_by": p.proposed_by, "created_at": p.created_at}


@router.get("/params", tags=["params"])
def list_params(u: User = Depends(current_user), db: Session = Depends(get_db)):
    AC.require(u, AC.PARAM_ROLES, "bảng tham số chính sách")
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
    from app.services import chu_ky as CK
    p = db.get(Param, pid)
    if not p or p.status != "pending": raise Gate("TRANG_THAI", "Không ở trạng thái chờ ký")
    # Người trình đề xuất không được tự ký duyệt đề xuất của chính mình (Phụ lục đối chiếu mục 3.2).
    CK.kiem_tra_nguoi_ky(u, ("chutich", "tgd"), nguoi_trinh=p.proposed_by,
                         da_ky={"chutich": "x" if p.signed_chutich else "", "tgd": "x" if p.signed_tgd else ""})
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
    rows = db.execute(select(Alert).order_by(Alert.resolved, desc(Alert.created_at))).scalars()
    if u.role in AC.ALL_SEEING: return [alert_out(a) for a in rows]
    return [alert_out(a) for a in rows if u.role in (a.to_roles or "").split(",")]   # chỉ cảnh báo gửi tới vai trò của mình


@router.post("/alerts/{aid}/resolve", tags=["alerts"])
def resolve_alert(aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.get(Alert, aid)
    if not a: raise HTTPException(404, "Không có cảnh báo")
    a.resolved = True
    R.audit(db, u.username, u.role, "dong_canh_bao", f"alert:{aid}", after={"kind": a.kind, "ref": a.ref}); db.commit()
    return {"message": "Đã đóng cảnh báo"}


@router.post("/robots/run", tags=["alerts"])
def run_robots(u: User = Depends(require_roles("cntt", "tgd", "chutich")), db: Session = Depends(get_db)):
    from app.services import ops as OPS
    n = R.run_robots(db) + OPS.check_missing_reports(db)
    R.audit(db, u.username, u.role, "chay_robot", "robot", after={"canh_bao_moi": n}); db.commit()
    return {"new_alerts": n, "message": f"Robot đã chạy, {n} cảnh báo mới"}


# ---------- audit / payroll ----------
def audit_out(l: AuditLog) -> dict:
    return {"id": l.id, "ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action, "entity": l.entity, "before": l.before, "after": l.after, "hash": l.hash}


@router.get("/audit", tags=["audit"])
def list_audit(limit: int = 300, u: User = Depends(current_user), db: Session = Depends(get_db)):
    AC.require(u, AC.AUDIT_ROLES, "nhật ký kiểm toán")
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


# ---------- Robot R7 – báo cáo tự động ----------
from app.models.reports_auto import AutoReport


def _rep_out(r: AutoReport) -> dict:
    return {"id": r.id, "kind": r.kind, "period": r.period, "content": r.content, "comment": r.comment, "data": r.data, "created_by": r.created_by, "created_at": r.created_at}


@router.get("/auto-reports", tags=["robot"])
def auto_reports(kind: str | None = None, limit: int = 30, u: User = Depends(require_roles("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "ketoan", "cntt", "bks", "hcns", "tp_dh", "gd_kd", "tp_kd")), db: Session = Depends(get_db)):
    q = select(AutoReport).order_by(desc(AutoReport.created_at))
    if kind: q = q.where(AutoReport.kind == kind)
    return [_rep_out(r) for r in db.execute(q.limit(limit)).scalars()]


@router.post("/auto-reports/{kind}", tags=["robot"])
def auto_report_run(kind: str, u: User = Depends(require_roles("cntt", "tgd", "chutich", "ketoan")), db: Session = Depends(get_db)):
    from app.services import dashboard as DB_
    try:
        r = DB_.run_report(db, kind, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Robot đã lập báo cáo {kind} {r.period}", "report": _rep_out(r)}


@router.post("/robot/report/{kind}", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_report(kind: str, db: Session = Depends(get_db)):
    """n8n gọi theo lịch: 20:30 hằng ngày (ngay), thứ Bảy (tuan), ngày 10 (thang). Trả markdown để gửi Zalo/Email."""
    from app.services import dashboard as DB_
    try:
        r = DB_.run_report(db, kind)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"period": r.period, "markdown": r.content, "comment": r.comment}
