"""Nghiệp vụ tour: dự toán, cổng chặn, phê duyệt, quyết toán. Mọi hàm nhận user đã xác thực."""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, User, ServiceRequest, Booking, Alert, AuditLog, ROLES
from app.services import rules as R
from app.services import accounting as ACC
from app.services.products import event as EV
from app.api.deps import Gate
from fastapi import HTTPException


def snap(t: Tour) -> dict:
    return {"code": t.code, "status": t.status, "price": t.price_per_pax, "fixed": t.fixed_cost, "var": t.var_cost_per_pax,
            "pax": t.planned_pax, "below_margin": t.below_margin, "actual_revenue": t.actual_revenue,
            "actual_cost": t.actual_cost, "promo": t.promo_value}


def tour_view(db: Session, t: Tour, user: User | None = None) -> dict:
    thr = R.get_param(db, "nguong_bien", t.start_date)
    c = R.calc(t, thr)
    s = R.settlement_summary(db, t) if t.status in ("da_dong_so", "kt_xac_nhan", "khoa") else None
    bk = R.booked_pax(t)
    days_left = (t.start_date - date.today()).days
    out = {
        "id": t.id, "code": t.code, "name": t.name, "tour_type": t.tour_type, "start_date": t.start_date, "end_date": t.end_date,
        "operator_id": t.operator_id, "operator_name": t.operator.full_name if t.operator else "",
        "price_per_pax": t.price_per_pax, "fixed_cost": t.fixed_cost, "var_cost_per_pax": t.var_cost_per_pax, "planned_pax": t.planned_pax,
        "rest_stops": t.rest_stops, "strategic": t.strategic, "below_margin": t.below_margin, "justification": t.justification,
        "status": t.status, "confirmed_by": t.confirmed_by, "approved_by": t.approved_by,
        "signed_chutich": t.signed_chutich, "signed_tgd": t.signed_tgd, "chairman_run_decision": t.chairman_run_decision,
        "actual_revenue": t.actual_revenue, "actual_cost": t.actual_cost, "promo_value": t.promo_value,
        "closed_at": t.closed_at, "kt_confirmed_at": t.kt_confirmed_at, "cntt_checked_at": t.cntt_checked_at,
        "calc": c, "booked_pax": bk, "days_left": days_left, "settlement_deadline": R.settlement_deadline(db, t),
        "approver_role": R.approver_role(t), "settlement": s, "is_doan": R.is_doan(t),
        "imported": t.imported, "product_code": t.product_code, "product_id": t.product_id, "days": t.days, "transport": t.transport, "vehicle_type": t.vehicle_type, "departure_point": t.departure_point,
        "d7_flag": bool(c["breakeven_pax"] and bk < c["breakeven_pax"] and 0 <= days_left <= int(R.get_param(db, "moc_d7")) and t.status == "da_duyet"),
        "bookings": [{"id": b.id, "code": b.code, "sales_id": b.sales_id, "customer_name": b.customer_name, "customer_phone": b.customer_phone, "source": b.source,
                      "pax": b.pax, "amount": b.amount, "discount": b.discount, "promo_code": b.promo_code, "sales_name": b.sales.full_name if b.sales else "",
                      "sla_minutes": b.sla_minutes, "sla_ok": b.sla_ok, "counts_for_target": b.counts_for_target, "created_at": b.created_at} for b in t.bookings],
    }
    if user:
        out["actions"] = allowed_actions(db, t, user)
    return out


def allowed_actions(db: Session, t: Tour, u: User) -> list[str]:
    a = []
    if t.status == "nhap" and (u.id == t.operator_id or u.role == "tp_dh"): a += ["edit", "submit"]
    if t.status == "cho_xac_nhan" and u.role == "tp_dh": a.append("confirm")
    if t.status == "cho_duyet":
        if t.below_margin and u.role in ("chutich", "tgd") and not getattr(t, f"signed_{u.role}"): a.append("sign")
        if not t.below_margin and u.role == R.approver_role(t): a.append("approve")
    if t.status in ("ket_thuc", "da_duyet") and u.id == t.operator_id and date.today() >= t.end_date: a.append("close")
    if t.status == "da_dong_so" and u.role == "ketoan": a += ["kt_confirm", "kt_return"]
    if t.status in ("da_duyet", "ket_thuc") and u.id == t.operator_id: a.append("edit_settlement")
    if t.status == "kt_xac_nhan" and u.role == "cntt": a.append("cntt_check")
    if t.status == "da_duyet" and u.role in ("chutich", "tp_dh") and not t.chairman_run_decision: a.append("d7")
    return a


def create(db: Session, u: User, data) -> Tour:
    if u.role not in ("nv_dh", "tp_dh"):
        raise HTTPException(403, "Chỉ Phòng Điều hành tạo tour và lập dự toán (ĐH Điều 2)")
    code = data.code.strip().upper()
    if db.execute(select(Tour).where(Tour.code == code)).scalars().first():
        raise Gate("MA_TOUR", "Mã tour đã tồn tại")
    t = Tour(code=code, name=data.name, tour_type=data.tour_type, start_date=data.start_date, end_date=data.end_date,
             operator_id=data.operator_id, price_per_pax=data.price_per_pax, fixed_cost=data.fixed_cost,
             var_cost_per_pax=data.var_cost_per_pax, planned_pax=data.planned_pax, rest_stops=data.rest_stops)
    db.add(t); db.flush()
    from app.services.misa import ensure_project_for_tour
    ensure_project_for_tour(db, t)   # mỗi tour = một công trình (mã công trình = mã tour)
    EV(db, t, "khoi_tao", u.username, getattr(data, "note", "") or "")
    R.audit(db, u.username, u.role, "tao_tour", f"tour:{t.code}", after=snap(t)); db.commit(); db.refresh(t)
    return t


def edit(db: Session, u: User, t: Tour, data) -> Tour:
    if t.status != "nhap":
        raise Gate("KHOA_DU_TOAN", "Dự toán đã trình, không sửa được (muốn sửa phải rút về nháp, có ghi nhật ký)")
    if not (u.id == t.operator_id or u.role == "tp_dh"):
        raise HTTPException(403, "Chỉ người điều hành chuyến hoặc TP Điều hành sửa dự toán")
    before = snap(t)
    t.price_per_pax, t.fixed_cost, t.var_cost_per_pax, t.planned_pax = data.price_per_pax, data.fixed_cost, data.var_cost_per_pax, data.planned_pax
    t.rest_stops, t.justification = data.rest_stops, data.justification
    EV(db, t, "sua_du_toan", u.username, "")
    R.audit(db, u.username, u.role, "sua_du_toan", f"tour:{t.code}", before=before, after=snap(t)); db.commit()
    return t


def submit(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role not in ("nv_dh", "tp_dh"): raise HTTPException(403, "Chỉ Điều hành trình dự toán")
    if t.status != "nhap": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
    if not c["complete"]:
        raise Gate("CONG_5", "Thiếu 3 con số dự toán: giá bán, số khách, chi phí cố định/theo khách phải > 0 và giá bán > chi phí theo khách")
    if not t.rest_stops.strip():
        raise Gate("CONG_5", "Dự toán phải ghi điểm dừng nghỉ (ĐH Điều 11)")
    if not c["pass_gate"] and len(t.justification.strip()) < 30:
        raise Gate("CONG_1_2", f"Biên kế hoạch {c['margin']*100:.1f}% dưới {c['threshold']*100:.0f}%: phải có giải trình 4 mục (lý do · khoản làm mỏng biên · phương án bù · lỗ tối đa) mới trình được")
    t.below_margin = not c["pass_gate"]; t.status = "cho_xac_nhan"
    EV(db, t, "trinh_du_toan", u.username, note or (t.justification if not c["pass_gate"] else ""))
    R.audit(db, u.username, u.role, "trinh_du_toan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã trình Trưởng phòng Điều hành xác nhận"


def confirm(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "tp_dh": raise HTTPException(403, "Chỉ Trưởng phòng Điều hành xác nhận dự toán")
    if t.status != "cho_xac_nhan": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    t.status, t.confirmed_by = "cho_duyet", u.username
    EV(db, t, "tp_xac_nhan", u.username, note)
    R.audit(db, u.username, u.role, "tp_xac_nhan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã xác nhận, chuyển " + ("Chủ tịch + TGĐ (2 chữ ký)" if t.below_margin else ROLES[R.approver_role(t)]) + " duyệt"


def approve(db: Session, u: User, t: Tour, note: str = "") -> str:
    if t.status != "cho_duyet": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    if t.below_margin:
        if u.role not in ("chutich", "tgd"):
            raise Gate("CONG_1", "Chuyến dưới biên 10% chỉ Chủ tịch và Tổng giám đốc được ký")
        if getattr(t, f"signed_{u.role}"): raise Gate("DA_KY", "Đã ký rồi")
        setattr(t, f"signed_{u.role}", True)
        EV(db, t, "ky", u.username, note, title=f"Ký duyệt chuyến dưới biên ({ROLES[u.role]})")
        R.audit(db, u.username, u.role, "ky_duyet_duoi_bien", f"tour:{t.code}", after=snap(t))
        if t.signed_chutich and t.signed_tgd:
            t.status, t.approved_by = "da_duyet", "chutich+tgd"
            R.audit(db, u.username, u.role, "duyet_du_toan_2_chu_ky", f"tour:{t.code}", after=snap(t)); db.commit()
            return "Đủ 2 chữ ký – chuyến được duyệt với cờ 'dưới biên' (không thưởng lẻ, không tính chỉ tiêu)"
        db.commit(); return f"Đã ký ({ROLES[u.role]}). Chờ chữ ký còn lại"
    need = R.approver_role(t)
    if u.role != need: raise Gate("PHAN_QUYEN", f"Dự toán này do {ROLES[need]} duyệt (Văn bản đính chính Điều 4)")
    t.status, t.approved_by = "da_duyet", u.username
    EV(db, t, "duyet", u.username, note)
    R.audit(db, u.username, u.role, "duyet_du_toan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã duyệt – Kinh doanh có thể chốt khách; 3 con số công bố trên lịch khởi hành"


def d7(db: Session, u: User, t: Tour, decision: str, note: str = "") -> str:
    if u.role not in ("chutich", "tp_dh"): raise HTTPException(403, "Chỉ TP Điều hành (ghép/dời/hủy) hoặc Chủ tịch")
    if decision == "chay":
        if u.role != "chutich": raise Gate("CONG_8", "Chuyến dưới hòa vốn muốn chạy tiếp phải do Chủ tịch duyệt")
        t.chairman_run_decision = f"Chủ tịch duyệt chạy {date.today():%d/%m/%Y}"
    elif decision in ("ghep", "doi", "huy"):
        t.status, t.chairman_run_decision = "huy", f"{decision} bởi {u.username} {date.today():%d/%m/%Y}"
    else:
        raise Gate("D7", "Quyết định không hợp lệ")
    for a in db.execute(select(Alert).where(Alert.kind == "d7", Alert.ref == t.code)).scalars(): a.resolved = True
    EV(db, t, "d7", u.username, note, title=f"Quyết định mốc D-7: {decision}")
    R.audit(db, u.username, u.role, f"d7_{decision}", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã ghi quyết định D-7"


def close(db: Session, u: User, t: Tour, data, note: str = "") -> str:
    if t.status not in ("ket_thuc", "da_duyet"): raise Gate("TRANG_THAI", "Chưa đến bước quyết toán")
    if u.id != t.operator_id: raise Gate("CONG_6", f"Một cửa: chỉ người điều hành chuyến ({t.operator.full_name}) mới được nhập quyết toán")
    if date.today() < t.end_date: raise Gate("CONG_6", "Chuyến chưa kết thúc")
    from app.services import settlement as ST
    blocks = [c["msg"] for c in ST.checks(db, t) if c["level"] == "block"]
    if blocks: raise Gate("QT_NHAP", blocks[0])
    before = snap(t)
    sm = ST.summary(db, t)
    t.actual_revenue, t.promo_value = data.actual_revenue, data.promo_value
    t.actual_cost = sm["actual"] if sm["lines"] else data.actual_cost   # có bảng dòng NCC → tổng dòng là giá vốn thực tế (không nhập tay)
    t.closed_at, t.status = datetime.now(), "da_dong_so"
    tag = f"Quyết toán V.{t.settlement_version:02d}: {sm['lines']} dòng NCC, thực chi {t.actual_cost:,.0f} đ, đã trả {sm['paid']:,.0f} đ, dự toán {sm['budget']:,.0f} đ ({sm['variance_pct'] * 100:+.0f}%), {sm['with_doc']}/{sm['lines']} dòng có chứng từ"
    EV(db, t, "dong_so", u.username, (note + " | " if note else "") + tag)
    R.audit(db, u.username, u.role, "dong_so_quyet_toan", f"tour:{t.code}", before=before, after=snap(t)); db.commit()
    late = date.today() > R.settlement_deadline(db, t)
    return "Đã đóng số, chuyển Kế toán xác nhận" + (" – QUÁ HẠN quyết toán, mất thưởng chuyến" if late else "")


def kt_confirm(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "ketoan": raise HTTPException(403, "Chỉ Kế toán xác nhận quyết toán")
    if t.status != "da_dong_so": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    t.status, t.kt_confirmed_at = "kt_xac_nhan", datetime.now()
    EV(db, t, "kt_xac_nhan", u.username, note)
    R.audit(db, u.username, u.role, "ke_toan_xac_nhan", f"tour:{t.code}", after=snap(t))
    ACC.on_settlement_confirmed(db, t, u.username, u.role); db.commit()
    return "Kế toán đã xác nhận – số liệu này là căn cứ duy nhất tính thưởng"


def cntt_check(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "cntt": raise HTTPException(403, "Chỉ CNTT đối chiếu độc lập")
    if t.status != "kt_xac_nhan": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    bk = sum(b.amount - b.discount for b in t.bookings)
    chk = {"doanh_thu_booking": bk, "doanh_thu_quyet_toan": t.actual_revenue, "lech": round(t.actual_revenue - bk)}
    t.status, t.cntt_checked_at = "khoa", datetime.now()
    EV(db, t, "cntt_khoa", u.username, (note + " | " if note else "") + f"Lệch doanh thu booking/quyết toán: {chk['lech']:,.0f} đ")
    R.audit(db, u.username, u.role, "cntt_doi_chieu_khoa", f"tour:{t.code}", after=chk); db.commit()
    return f"Đã đối chiếu và khóa. Lệch doanh thu booking/quyết toán: {chk['lech']:,.0f} đ" + (" → đã ghi nhật ký trình TGĐ" if abs(chk["lech"]) > 1000 else "")


# ---------- yêu cầu & booking ----------
def create_request(db: Session, u: User, data) -> ServiceRequest:
    from app.services import access as AC
    if u.role not in AC.REQUEST_CREATE_ROLES: raise HTTPException(403, "Vai trò này không gửi yêu cầu đặt dịch vụ")
    missing = [n for n, v in (("số điện thoại khách", data.customer_phone), ("nguồn khách", data.source), ("ghi chú chăm sóc", data.care_note)) if not v.strip()]
    if missing:
        raise Gate("CONG_4", "Thiếu trường bắt buộc: " + ", ".join(missing) + " (booking sẽ không tính chỉ tiêu, không hoa hồng)")
    t = db.get(Tour, data.tour_id)
    if not t: raise Gate("TOUR", "Không có tour")
    r = ServiceRequest(tour_id=t.id, sales_id=u.id, customer_name=data.customer_name, customer_phone=data.customer_phone,
                       source=data.source, care_note=data.care_note, pax=data.pax, campaign_code=data.campaign_code,
                       promo_code=data.promo_code, discount=data.discount)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "gui_yeu_cau_dat_dich_vu", f"yeucau:{r.id}", after={"tour": t.code, "pax": r.pax, "khach": r.customer_name}); db.commit(); db.refresh(r)
    return r


def create_booking(db: Session, u: User, r: ServiceRequest) -> tuple[Booking, str]:
    if u.role not in ("nv_dh", "tp_dh"): raise Gate("CONG_12", "Chỉ Phòng Điều hành tạo booking")
    if r.booking_id: raise Gate("TRANG_THAI", "Yêu cầu đã có booking")
    t = db.get(Tour, r.tour_id)
    if t.status != "da_duyet": raise Gate("CONG_1", "Tour chưa được duyệt dự toán, không thể tạo booking")
    thr = R.get_param(db, "nguong_bien", t.start_date)
    if r.discount > 0:
        c = R.calc(t, thr)
        nr = c["revenue"] - r.discount
        nm = (nr - c["cost"]) / nr if nr > 0 else 0
        if nm < thr:
            raise Gate("CONG_3", f"Mã KM/giảm giá {r.discount:,.0f} đ làm biên chuyến tụt còn {nm*100:.1f}% (< {thr*100:.0f}%): treo, cần TGĐ duyệt")
    mins = int((datetime.now() - r.created_at).total_seconds() / 60)
    sla = int(R.get_param(db, "sla_booking_phut"))
    n = db.execute(select(func.count()).select_from(Booking)).scalar() + 1
    b = Booking(code=f"BK{date.today():%y%m}{n:04d}", tour_id=t.id, request_id=r.id, sales_id=r.sales_id, created_by=u.id,
                customer_name=r.customer_name, customer_phone=r.customer_phone, source=r.source, care_note=r.care_note,
                pax=r.pax, amount=t.price_per_pax * r.pax, discount=r.discount, promo_code=r.promo_code, campaign_code=r.campaign_code,
                counts_for_target=not t.below_margin, sla_minutes=mins, sla_ok=mins <= sla)
    db.add(b); db.flush(); r.booking_id = b.id
    from app.services import bookings as BK
    BK.init_terms(db, b, t)
    for a in db.execute(select(Alert).where(Alert.kind == "sla_booking", Alert.ref == f"YC-{r.id}")).scalars(): a.resolved = True
    R.audit(db, u.username, u.role, "tao_booking", f"booking:{b.code}", after={"tour": t.code, "pax": b.pax, "amount": b.amount, "sla_phut": mins, "sla_ok": b.sla_ok, "tinh_chi_tieu": b.counts_for_target}); db.commit(); db.refresh(b)
    return b, f"Đã tạo {b.code} sau {mins} phút" + ("" if b.sla_ok else " – QUÁ 2 GIỜ, ghi vào tiêu chí đánh giá")
