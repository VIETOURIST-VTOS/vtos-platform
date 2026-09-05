"""Đồng bộ Vietrip → VTOS (robot chuyển đổi dữ liệu, mục 11.3 Thiết kế).

Bước 1 – nạp thô: mọi bản ghi Vietrip lưu vào vt_records (idempotent theo entity + vietrip_id).
Bước 2 – ánh xạ: tour → tours (+ dòng chi phí), booking → bookings, phiếu thu → receipts, chi NCC → payment_requests (đã chi),
         user → users + employees, xe → vehicles. Giữ mã Vietrip trong trường tham chiếu để tra ngược. Không sinh bút toán
         (số dư đầu kỳ lấy từ MISA/BCTC khi cắt chuyển) – các bản ghi nhập đánh dấu imported/source=vietrip.
"""
import re, secrets
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User
from app.models.payments import Receipt
from app.models.ops import PaymentRequest
from app.models.hr import Employee, Vehicle
from app.models.vietrip import VtRecord, TourCostLine
from app.core.security import hash_password
from app.services import rules as R

ENTITIES = ("tour", "booking", "receipt", "supplier_payment", "user", "vehicle", "proposal", "settlement")
DEPT_MAP = {"Kế toán": ("ketoan", "ketoan"), "Điều hành": ("dieu_hanh", "nv_dh"), "Tour": ("kd_le", "nv_kd"), "Tour MICE": ("kd_doan", "nv_kd"), "Hướng dẫn": ("huong_dan", "nv_kd"),
            "CSKH": ("marketing", "nv_kd"), "IT": ("cntt", "cntt"), "Giám đốc": ("ban_tgd", "tgd"), "Kinh doanh": ("kd_le", "nv_kd"), "Marketing": ("marketing", "nv_kd"), "ĐỐI TÁC": ("kd_le", "nv_kd")}
STATUS_TEXT = {"KC": "đã xác nhận", "QQ": "chờ duyệt", "XX": "từ chối/hủy", "GD": "GĐ duyệt"}


def _dt(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s)[:19])
    except ValueError: return None


def _d(s):
    x = _dt(s); return x.date() if x else None


def upsert(db: Session, entity: str, rows: list[dict]) -> tuple[int, int]:
    """Nạp thô. Trả về (mới, cập nhật)."""
    if entity not in ENTITIES: raise ValueError("entity không hợp lệ")
    key = {"tour": "recID", "booking": "recID", "receipt": "RecID", "supplier_payment": "RecID", "user": "recID", "vehicle": "recID", "proposal": "proposalId", "settlement": "tourId"}[entity]
    new = upd = 0
    existing = {r.vietrip_id: r for r in db.execute(select(VtRecord).where(VtRecord.entity == entity)).scalars()}
    for raw in rows:
        vid = str(raw.get(key) or "")
        if not vid: continue
        ref = str(raw.get("tourcode") or raw.get("Tourcode") or raw.get("BookingID") or raw.get("licensePlate") or "")
        on = _d(raw.get("fstUpdate") or raw.get("FstUpdate") or raw.get("ngayKhoiHanh") or raw.get("submittedAt") or raw.get("lstUpdate"))
        amt = float(raw.get("totalDue") or raw.get("SoTien") or raw.get("Amount") or raw.get("amount") or raw.get("doanhThu") or 0)
        r = existing.get(vid)
        if r:
            if r.raw != raw:
                r.raw, r.ref, r.on_date, r.amount, r.applied = raw, ref, on, amt, False; upd += 1
        else:
            db.add(VtRecord(entity=entity, vietrip_id=vid, ref=ref, on_date=on, amount=amt, raw=raw)); new += 1
    db.commit()
    return new, upd


def status_counts(db: Session) -> dict:
    out = {}
    for e in ENTITIES:
        tot = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.entity == e)).scalar()
        ap = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.entity == e, VtRecord.applied == True)).scalar()
        mn = db.execute(select(func.min(VtRecord.on_date)).where(VtRecord.entity == e)).scalar()
        mx = db.execute(select(func.max(VtRecord.on_date)).where(VtRecord.entity == e)).scalar()
        out[e] = {"total": tot, "applied": ap, "from": mn, "to": mx}
    return out


# ---------- ánh xạ ----------
def _user_for(db: Session, name: str, cache: dict) -> User:
    """Tìm/tạo tài khoản VTOS cho người dùng Vietrip theo họ tên (mật khẩu ngẫu nhiên – HCNS cấp lại)."""
    key = (name or "").strip().upper()
    if not key: key = "VIETRIP"
    if key in cache: return cache[key]
    u = db.execute(select(User).where(func.upper(User.full_name) == key)).scalars().first()
    if not u:
        base = re.sub(r"[^a-z0-9]", "", _strip_accents(key).lower())[:20] or "vt"
        uname = base; n = 1
        while db.execute(select(User).where(User.username == uname)).scalars().first():
            n += 1; uname = f"{base}{n}"
        u = User(username=uname, full_name=name or "Vietrip", role="nv_kd", department="Vietrip", password_hash=hash_password(secrets.token_urlsafe(12)), active=True)
        db.add(u); db.flush()
    cache[key] = u
    return u


def _strip_accents(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tour_type_of(raw: dict) -> str:
    code = (raw.get("tourcode") or "").upper(); nuoc = (raw.get("nuoc") or "").strip()
    doan = code.startswith("MICE") or "MICE" in (raw.get("tenSanPham") or "").upper()
    if doan: return "doan_nuoc_ngoai" if nuoc else "doan_noi_dia"
    return "le_nuoc_ngoai" if nuoc else "le_noi_dia"


def apply_users(db: Session, limit: int = 400) -> int:
    n = 0; cache = {}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "user", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; name = raw.get("hoTen") or ""
        dept, role = DEPT_MAP.get(raw.get("phongBan") or "", ("kd_le", "nv_kd"))
        cv = raw.get("chucVu") or ""
        u = _user_for(db, name, cache)
        if u.department == "Vietrip":
            u.department = raw.get("phongBan") or "Vietrip"
            u.role = "tp_dh" if (cv == "Trưởng phòng" and dept == "dieu_hanh") else "gd_kd" if (cv == "Giám đốc" and dept == "kd_le") else role
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        if not e:
            code = f"VT{int(raw['recID']):04d}"
            if not db.execute(select(Employee).where(Employee.code == code)).scalars().first():
                pos = "tp" if cv == "Trưởng phòng" else "gd_kd" if cv == "Giám đốc" and dept == "kd_le" else "hdv" if dept == "huong_dan" else "nv"
                db.add(Employee(code=code, user_id=u.id, full_name=name, department=dept, position=pos, contract_type="ctv" if dept == "huong_dan" else "hdld"))
        r.applied, r.apply_note = True, f"user:{u.username}"; n += 1
    db.commit()
    return n


def apply_vehicles(db: Session, limit: int = 400) -> int:
    n = 0
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "vehicle", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; plate = (raw.get("licensePlate") or "").replace(" ", "-")
        v = db.execute(select(Vehicle).where(Vehicle.plate == plate)).scalars().first()
        if not v:
            v = Vehicle(plate=plate, seats=45, kind="noi_bo"); db.add(v); db.flush()
        drv = raw.get("driverName") or ""
        if drv:
            e = db.execute(select(Employee).where(func.upper(Employee.full_name) == drv.upper())).scalars().first()
            if not e:
                code = f"TX{int(raw['recID']):03d}"
                if not db.execute(select(Employee).where(Employee.code == code)).scalars().first():
                    e = Employee(code=code, full_name=drv, department="doi_xe", position="tai_xe", contract_type="hdld", base_salary=7_000_000); db.add(e); db.flush()
            if e: v.driver_id = e.id
        r.applied, r.apply_note = True, f"vehicle:{plate}"; n += 1
    db.commit()
    return n


def apply_tours(db: Session, only_from: date | None = None, limit: int = 400) -> int:
    n = 0; cache = {}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "tour", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; code = raw.get("tourcode") or ""
        start, end = _d(raw.get("ngayKhoiHanh")), _d(raw.get("ngayKetThuc"))
        if not code or not start: r.applied, r.apply_note = True, "bỏ qua: thiếu mã/ngày"; continue
        if only_from and start < only_from: r.applied, r.apply_note = True, "ngoài phạm vi"; continue
        t = db.execute(select(Tour).where(Tour.code == code)).scalars().first()
        op = _user_for(db, raw.get("fstUser") if not str(raw.get("fstUser") or "").isdigit() else "Điều hành Vietrip", cache)
        if not t:
            t = Tour(code=code, operator_id=op.id); db.add(t)
        t.name = raw.get("tenSanPham") or raw.get("ghiChu") or code
        t.tour_type = tour_type_of(raw); t.start_date, t.end_date = start, end or start
        t.price_per_pax = float(raw.get("adl") or 0); t.price_chd = float(raw.get("chd") or 0); t.price_inf = float(raw.get("inf") or 0); t.price_promo = float(raw.get("adl_KM") or 0)
        t.planned_pax = int(raw.get("soChoMoBan") or 0); t.seats_open = int(raw.get("soChoMoBan") or 0); t.seats_promo = int(raw.get("soChoMoBan_KM") or 0)
        t.product_code = code.split(".")[0]; t.vehicle_type = raw.get("loaiXe") or ""; t.departure_point = raw.get("diemKhoiHanh") or ""; t.transport = raw.get("phuongTien") or ""
        t.days = int(raw.get("soNgay") or 0); t.country = raw.get("nuoc") or ""; t.vietrip_id = int(raw["recID"]); t.imported = True
        t.actual_revenue = float(raw.get("doanhThu") or 0); t.actual_cost = float(raw.get("tongChiPhi") or 0)
        t.settled_vietrip = bool(raw.get("quyetToan")) or bool(raw.get("duyetChi"))
        t.confirmed_by, t.approved_by = "vietrip", "vietrip"
        today = date.today()
        if raw.get("duyetChi"): t.status = "khoa"; t.closed_at = t.closed_at or _dt(raw.get("ngayDuyetChi")) or datetime.combine(t.end_date, datetime.min.time()); t.kt_confirmed_at = t.kt_confirmed_at or _dt(raw.get("ngayDuyetChi")); t.cntt_checked_at = t.cntt_checked_at or _dt(raw.get("ngayDuyetChi"))
        elif raw.get("quyetToan"): t.status = "kt_xac_nhan"; t.closed_at = t.closed_at or datetime.combine(t.end_date, datetime.min.time()); t.kt_confirmed_at = t.kt_confirmed_at or datetime.combine(t.end_date, datetime.min.time())
        elif t.end_date < today: t.status = "ket_thuc"
        else: t.status = "da_duyet"
        r.applied, r.apply_note = True, f"tour:{code}"; n += 1
    db.commit()
    return n


def apply_settlements(db: Session, limit: int = 400) -> int:
    """Dòng chi phí quyết toán theo tour → tour_cost_lines; suy ra chi phí cố định / theo khách cho dự toán VTOS."""
    n = 0
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "settlement", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; t = db.execute(select(Tour).where(Tour.code == raw.get("tourcode"))).scalars().first()
        if not t: r.apply_note = "chưa có tour"; continue
        db.execute(TourCostLine.__table__.delete().where(TourCostLine.tour_id == t.id, TourCostLine.source == "vietrip"))
        fixed = var = 0.0
        for i, l in enumerate(raw.get("lines") or [], 1):
            sup = l.get("ncc") or ""; m = re.search(r"\((\d{10,14})\)\s*$", sup)
            kind = "theo_khach" if "theo khách" in (l.get("mo_ta") or "").lower() else "co_dinh"
            actual = float(l.get("thuc_chi") or 0)
            db.add(TourCostLine(tour_id=t.id, line_no=i, description=(l.get("mo_ta") or "").split("|")[0].strip()[:200], cost_kind=kind, service_type=l.get("loai") or "",
                                supplier_name=re.sub(r"\s*\(\d{10,14}\)\s*$", "", sup)[:200], supplier_tax_code=m.group(1) if m else "", unit_price=float(l.get("don_gia") or 0),
                                qty=float(l.get("sl") or 0), coef=float(l.get("hs") or 1), actual=actual, paid=float(l.get("da_tt") or 0), note=(l.get("ghi_chu") or "")[:200]))
            if kind == "theo_khach": var += float(l.get("don_gia") or 0) * float(l.get("hs") or 1)
            else: fixed += actual
        if fixed or var:
            t.fixed_cost, t.var_cost_per_pax = fixed, var
        if raw.get("tong_thu"): t.actual_revenue = float(raw["tong_thu"])
        if raw.get("tong_chi"): t.actual_cost = float(raw["tong_chi"])
        r.applied, r.apply_note = True, f"{len(raw.get('lines') or [])} dòng"; n += 1
    db.commit()
    return n


def apply_bookings(db: Session, limit: int = 400) -> int:
    n = 0; cache = {}
    tours = {t.code: t for t in db.execute(select(Tour)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "booking", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; t = tours.get(raw.get("tourcode") or "")
        if not t: r.apply_note = "chưa có tour"; continue
        code = f"VT{int(raw['recID'])}"
        b = db.execute(select(Booking).where(Booking.code == code)).scalars().first()
        sales = _user_for(db, raw.get("fstUser") or "", cache)
        if not b:
            b = Booking(code=code, tour_id=t.id, request_id=0, sales_id=sales.id, created_by=sales.id, sla_minutes=0, sla_ok=True); db.add(b)
        b.tour_id = t.id; b.customer_name = (raw.get("tenNguoiBook") or "")[:120]; b.customer_phone = (raw.get("phone") or "")[:30]; b.source = "Vietrip"
        b.adl, b.chd, b.inf = int(raw.get("adl") or 0), int(raw.get("chd") or 0), int(raw.get("inf") or 0)
        b.pax = b.adl + b.chd + b.inf; b.amount = float(raw.get("totalDue") or 0); b.pmt_status = raw.get("pmtStatus") or ""
        b.cancel_deadline = _dt(raw.get("deadlineHuyCho")); b.cancelled = (raw.get("status") or "OK") != "OK"; b.services_note = (raw.get("dichVuLe") or "")[:200]
        b.created_at = _dt(raw.get("fstUpdate")) or b.created_at or datetime.now(); b.vietrip_id = int(raw["recID"])
        b.counts_for_target = bool(b.customer_phone) and not b.cancelled
        if b.cancelled: b.amount = 0
        r.applied, r.apply_note = True, f"booking:{code}"; n += 1
    db.commit()
    return n


def apply_receipts(db: Session, limit: int = 400) -> int:
    n = 0
    bk = {b.vietrip_id: b for b in db.execute(select(Booking).where(Booking.vietrip_id != None)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "receipt", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw
        if raw.get("Status") != "KC": r.applied, r.apply_note = True, "chưa xác nhận – bỏ qua"; continue
        b = bk.get(int(raw.get("BookingID") or 0))
        if not b: r.apply_note = "chưa có booking"; continue
        if raw.get("LoaiPhieu") == "PhieuChi":   # phiếu chi trả khách (hoàn tiền) → đề nghị chi hoàn tiền đã chi
            code = f"VTPC{int(raw['RecID'])}"
            pr = db.execute(select(PaymentRequest).where(PaymentRequest.code == code)).scalars().first()
            if not pr:
                pr = PaymentRequest(code=code, category="hoan_tien", supplier_name="", amount=0, description="", created_by="vietrip"); db.add(pr)
            pr.tour_id = b.tour_id; pr.supplier_name = (raw.get("NguoiThanhToan") or b.customer_name)[:160]; pr.amount = float(raw.get("SoTien") or 0)
            pr.description = f"Hoàn tiền khách {b.code} – {raw.get('GhiChu') or ''} [Vietrip]"[:300]; pr.status = "da_chi"; pr.approved_by = "vietrip"; pr.signed_tgd = True
            pr.created_at = _dt(raw.get("FstUpdate")) or datetime.now(); pr.paid_at = pr.created_at; pr.paid_method = "tien_mat" if "mặt" in (raw.get("HinhThuc") or "").lower() else "chuyen_khoan"
            r.applied, r.apply_note = True, code; n += 1; continue
        code = f"VTPT{int(raw['RecID'])}"
        rc = db.execute(select(Receipt).where(Receipt.code == code)).scalars().first()
        if not rc:
            rc = Receipt(code=code, booking_id=b.id); db.add(rc)
        rc.amount = float(raw.get("SoTien") or 0); rc.method = "tien_mat" if "mặt" in (raw.get("HinhThuc") or "").lower() else "chuyen_khoan"
        rc.payer = (raw.get("NguoiThanhToan") or b.customer_name)[:120]; rc.note = f"Vietrip {raw.get('TaiKhoanCongTy') or ''} {raw.get('GhiChu') or ''}".strip()[:200]
        rc.status = "ke_toan_xac_nhan"; rc.created_by = "vietrip"; rc.confirmed_by = (raw.get("FstUser") or "vietrip")[:50]
        rc.created_at = _dt(raw.get("FstUpdate")) or datetime.now(); rc.confirmed_at = rc.created_at
        r.applied, r.apply_note = True, code; n += 1
    db.flush()
    # cập nhật đã thu theo booking
    for b in bk.values():
        b.paid = db.execute(select(func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id == b.id, Receipt.status != "huy")).scalar() or 0.0
    db.commit()
    return n


def apply_supplier_payments(db: Session, limit: int = 400) -> int:
    n = 0
    tours = {t.code: t for t in db.execute(select(Tour)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "supplier_payment", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; code = f"VTDC{int(raw['RecID'])}"
        if raw.get("Status") == "XX": r.applied, r.apply_note = True, "từ chối – bỏ qua"; continue
        pr = db.execute(select(PaymentRequest).where(PaymentRequest.code == code)).scalars().first()
        t = tours.get(raw.get("Tourcode") or "")
        if not pr:
            pr = PaymentRequest(code=code, category="chi_tour" if t else "hanh_chinh", supplier_name="", amount=0, description="", created_by="vietrip"); db.add(pr)
        pr.tour_id = t.id if t else None; pr.supplier_name = (raw.get("TenNCC") or f"NCC Vietrip #{raw.get('OrgID')}")[:160]; pr.supplier_bank = (raw.get("TaiKhoanNCC") or "")[:120]
        pr.amount = float(raw.get("Amount") or 0); pr.description = ((raw.get("MoTa") or raw.get("GhiChu") or "") + f" [Vietrip {raw.get('FOP') or ''}]").strip()[:300]
        pr.has_document = bool(raw.get("File")); pr.document_ref = (raw.get("File") or "")[:120]
        pr.created_at = _dt(raw.get("FstUpdate")) or datetime.now()
        st = raw.get("Status")
        if st == "KC": pr.status, pr.paid_at, pr.paid_method, pr.approved_by, pr.signed_tgd = "da_chi", pr.created_at, "tien_mat" if raw.get("FOP") == "CSH" else "chuyen_khoan", "vietrip", True
        elif st == "GD": pr.status, pr.approved_by, pr.signed_tgd = "cho_chi", "vietrip", True
        else: pr.status = "cho_duyet"
        r.applied, r.apply_note = True, code; n += 1
    db.commit()
    return n


def apply_all(db: Session, actor: str, limit: int = 400) -> dict:
    """Ánh xạ theo lô (mỗi lần tối đa `limit` bản ghi mỗi loại) để không quá thời gian request; gọi lặp tới khi remaining = 0."""
    out = {"users": apply_users(db, limit), "vehicles": apply_vehicles(db, limit), "tours": apply_tours(db, limit=limit), "settlements": apply_settlements(db, limit),
           "bookings": apply_bookings(db, limit), "receipts": apply_receipts(db, limit), "supplier_payments": apply_supplier_payments(db, limit)}
    out["remaining"] = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.applied == False, VtRecord.entity != "proposal",
                                                                                  ~VtRecord.apply_note.in_(["chưa có tour", "chưa có booking"]))).scalar()
    out["blocked"] = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.applied == False, VtRecord.apply_note.in_(["chưa có tour", "chưa có booking"]))).scalar()
    R.audit(db, actor, "cntt", "dong_bo_vietrip_ap_dung", "vietrip", after=out); db.commit()
    return out
