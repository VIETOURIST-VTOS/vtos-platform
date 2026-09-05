"""Dịch vụ lẻ – Non-package (theo màn hình Vietrip /operations/non-package): bán visa, vé máy bay, khách sạn, xe, nhà hàng, land, HDV, khác
không gắn tour trọn gói. Mỗi dịch vụ = một 'tour' loại non_package mã KLEddmmyy[_n] (như Vietrip) + một booking (thu tiền, SePay, bảo lưu dùng chung)
+ dòng chi phí NCC (quyết toán dùng chung). Chốt tháng: Kế toán đóng số – xác nhận hàng loạt các KLE đã hoàn thành."""
from datetime import datetime, date, timedelta, time
from fastapi import HTTPException
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session
from app.models.core import User, Tour, Booking, SERVICE_KINDS
from app.models.vietrip import TourCostLine
from app.services import rules as R
from app.services import bookings as BK
from app.services.products import event as EV

CREATE_ROLES = ("nv_kd", "gd_kd", "nv_dh", "tp_dh")


class Gate(HTTPException):
    def __init__(self, code: str, msg: str): super().__init__(422, {"gate": code, "message": msg})


def next_code(db: Session, d: date) -> str:
    base = f"KLE{d:%d%m%y}"
    codes = {c for (c,) in db.execute(select(Tour.code).where(Tour.code.like(base + "%"))).all()}
    if base not in codes: return base
    n = 2
    while f"{base}_{n}" in codes: n += 1
    return f"{base}_{n}"


def create(db: Session, u: User, d: dict) -> tuple[Tour, Booking]:
    if u.role not in CREATE_ROLES: raise HTTPException(403, "Chỉ Kinh doanh / Điều hành tạo dịch vụ lẻ")
    st = (d.get("service_type") or "OTHER").upper()
    if st not in SERVICE_KINDS: raise Gate("NP_NHAP", "Loại dịch vụ không hợp lệ")
    name, phone = (d.get("customer_name") or "").strip(), (d.get("customer_phone") or "").strip()
    if not name or not phone: raise Gate("CONG_4", "Thiếu tên khách / số điện thoại")
    if not (d.get("source") or "").strip(): raise Gate("CONG_4", "Thiếu nguồn khách (4 trường bắt buộc)")
    amount = float(d.get("amount") or 0)
    if amount <= 0: raise Gate("NP_NHAP", "Giá dịch vụ phải > 0")
    cost = max(0.0, float(d.get("cost_amount") or 0))
    sd = date.fromisoformat(d["service_date"]) if d.get("service_date") else date.today()
    desc = (d.get("description") or SERVICE_KINDS[st]).strip()[:200]
    sales_id = d.get("sales_id") or u.id
    code = next_code(db, date.today())
    t = Tour(code=code, name=f"{SERVICE_KINDS[st]}: {desc}"[:200], tour_type="non_package", start_date=sd, end_date=sd, operator_id=u.id if u.role in ("nv_dh", "tp_dh") else sales_id,
             price_per_pax=amount, fixed_cost=cost, var_cost_per_pax=0, planned_pax=1, seats_open=1, rest_stops="–", status="da_duyet", confirmed_by="non_package", approved_by="non_package", days=1,
             departure_point=(d.get("country") or "")[:80])
    db.add(t); db.flush()
    n = db.execute(select(func.count()).select_from(Booking)).scalar() + 1
    b = Booking(code=f"BK{date.today():%y%m}{n:04d}", tour_id=t.id, request_id=0, sales_id=sales_id, created_by=u.id, customer_name=name[:120], customer_phone=phone[:30],
                source=(d.get("source") or "")[:60], care_note=(d.get("note") or "")[:2000], pax=int(d.get("pax") or 1), adl=int(d.get("pax") or 1), amount=amount, discount=float(d.get("discount") or 0),
                counts_for_target=bool(d.get("counts_for_target", True)), sla_minutes=0, sla_ok=True, service_type=st, country=(d.get("country") or "")[:60], customer_email=(d.get("customer_email") or "")[:120],
                service_date=sd, cost_amount=cost, supplier_name=(d.get("supplier_name") or "")[:160], services_note=desc)
    db.add(b); db.flush()
    BK.init_terms(db, b, t)
    b.cancel_deadline = datetime.combine(sd, time(17, 0))   # deadline = ngày sử dụng dịch vụ
    if cost > 0:
        db.add(TourCostLine(tour_id=t.id, line_no=1, description=desc, cost_kind="co_dinh", service_type=st, supplier_name=b.supplier_name or "NCC", unit_price=cost, qty=b.pax, coef=1,
                            budget=cost, actual=cost, paid=0, source="vtos", version=1, updated_by=u.username))
    EV(db, t, "khoi_tao", u.username, f"Dịch vụ lẻ {SERVICE_KINDS[st]} – {name} – {amount:,.0f} đ" + (f" – giá vốn {cost:,.0f} đ" if cost else ""), title="Tạo dịch vụ lẻ (Non-package)")
    R.audit(db, u.username, u.role, "tao_dich_vu_le", f"booking:{b.code}", after={"ma": code, "loai": st, "khach": name, "gia": amount, "gia_von": cost})
    db.commit(); db.refresh(t); db.refresh(b)
    return t, b


def update(db: Session, u: User, b: Booking, d: dict) -> Booking:
    t = b.tour
    if t.tour_type != "non_package": raise Gate("NP", "Không phải dịch vụ lẻ")
    if b.cancelled: raise Gate("TRANG_THAI", "Dịch vụ đã hủy")
    if t.status not in ("da_duyet", "ket_thuc"): raise Gate("TRANG_THAI", "Dịch vụ đã chốt – không sửa")
    if u.role not in ("nv_dh", "tp_dh", "gd_kd") and u.id != b.sales_id: raise HTTPException(403, "Chỉ sale phụ trách / Điều hành sửa")
    before = {"gia": b.amount, "gia_von": b.cost_amount, "loai": b.service_type}
    if d.get("service_type"):
        st = d["service_type"].upper()
        if st not in SERVICE_KINDS: raise Gate("NP_NHAP", "Loại dịch vụ không hợp lệ")
        b.service_type = st
    for k in ("country", "customer_email", "supplier_name", "customer_name", "customer_phone"):
        if d.get(k) is not None: setattr(b, k, str(d[k]).strip()[:120])
    if d.get("description") is not None: b.services_note = str(d["description"])[:200]; t.name = f"{SERVICE_KINDS[b.service_type]}: {b.services_note}"[:200]
    if d.get("service_date"): b.service_date = date.fromisoformat(d["service_date"]); t.start_date = t.end_date = b.service_date; b.cancel_deadline = datetime.combine(b.service_date, time(17, 0))
    if d.get("amount") is not None:
        if b.locked: raise Gate("KHOA_BOOKING", "Dịch vụ đã khóa (thu đủ / quá ngày) – mở khóa trước khi đổi giá")
        b.amount = float(d["amount"]); t.price_per_pax = b.amount
    if d.get("cost_amount") is not None:
        b.cost_amount = max(0.0, float(d["cost_amount"])); t.fixed_cost = b.cost_amount
        l = db.execute(select(TourCostLine).where(TourCostLine.tour_id == t.id, TourCostLine.status == "hd")).scalars().first()
        if l: l.unit_price = l.actual = l.budget = b.cost_amount; l.supplier_name = b.supplier_name or l.supplier_name; l.updated_by = u.username
        elif b.cost_amount > 0:
            db.add(TourCostLine(tour_id=t.id, line_no=1, description=b.services_note, cost_kind="co_dinh", service_type=b.service_type, supplier_name=b.supplier_name or "NCC", unit_price=b.cost_amount, qty=b.pax, coef=1,
                                budget=b.cost_amount, actual=b.cost_amount, source="vtos", updated_by=u.username))
    BK.refresh_status(b)
    R.audit(db, u.username, u.role, "sua_dich_vu_le", f"booking:{b.code}", before=before, after={"gia": b.amount, "gia_von": b.cost_amount, "loai": b.service_type})
    db.commit(); db.refresh(b); return b


def row(b: Booking) -> dict:
    t = b.tour
    return {"id": b.id, "code": b.code, "tour_id": t.id, "tour_code": t.code, "tour_status": t.status, "service_type": b.service_type, "service_name": SERVICE_KINDS.get(b.service_type, b.service_type or "–"),
            "description": b.services_note, "country": b.country, "customer_name": b.customer_name, "customer_phone": b.customer_phone, "customer_email": b.customer_email, "source": b.source,
            "pax": b.pax, "amount": b.amount, "discount": b.discount, "net": max(0.0, b.amount - b.discount), "paid": b.paid, "due": max(0.0, b.amount - b.discount - b.paid), "pmt_status": BK.pmt_status_of(b),
            "cost_amount": b.cost_amount, "supplier_name": b.supplier_name, "profit": max(0.0, b.amount - b.discount) - b.cost_amount, "service_date": b.service_date, "cancel_deadline": b.cancel_deadline,
            "sales_name": b.sales.full_name if b.sales else "", "created_at": b.created_at, "cancelled": b.cancelled, "cancel_reason": b.cancel_reason, "locked": b.locked, "note": b.care_note, "imported": b.vietrip_id is not None}


def list_rows(db: Session, month: str = "", service_type: str = "", paid: str = "", q: str = "", limit: int = 500) -> list[Booking]:
    qs = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Tour.tour_type == "non_package").order_by(Booking.created_at.desc())
    if month:
        y, m = month.split("-"); qs = qs.where(extract("year", Booking.created_at) == int(y), extract("month", Booking.created_at) == int(m))
    if service_type: qs = qs.where(Booking.service_type == service_type.upper())
    if paid == "paid": qs = qs.where(Booking.pmt_status == "PAID", Booking.cancelled == False)
    elif paid == "due": qs = qs.where(Booking.pmt_status != "PAID", Booking.cancelled == False)
    elif paid == "cancelled": qs = qs.where(Booking.cancelled == True)
    if q:
        like = f"%{q.strip()}%"; qs = qs.where((Booking.code.ilike(like)) | (Booking.customer_name.ilike(like)) | (Booking.customer_phone.ilike(like)) | (Tour.code.ilike(like)) | (Booking.services_note.ilike(like)))
    return list(db.execute(qs.limit(limit)).scalars())


def summary(rows: list[Booking]) -> dict:
    by = {}
    for b in rows:
        if b.cancelled: continue
        k = b.service_type or "OTHER"; d = by.setdefault(k, {"service_type": k, "service_name": SERVICE_KINDS.get(k, k), "n": 0, "revenue": 0.0, "paid": 0.0, "cost": 0.0})
        d["n"] += 1; d["revenue"] += b.amount - b.discount; d["paid"] += b.paid; d["cost"] += b.cost_amount
    out = sorted(by.values(), key=lambda x: -x["revenue"])
    for d in out: d["profit"] = d["revenue"] - d["cost"]; d["margin"] = d["profit"] / d["revenue"] if d["revenue"] else 0
    tot = {"n": sum(d["n"] for d in out), "revenue": sum(d["revenue"] for d in out), "paid": sum(d["paid"] for d in out), "cost": sum(d["cost"] for d in out)}
    tot["profit"] = tot["revenue"] - tot["cost"]; tot["due"] = tot["revenue"] - tot["paid"]; tot["cancelled"] = sum(1 for b in rows if b.cancelled)
    return {"by_type": out, "total": tot}


def close_month(db: Session, u: User, month: str) -> dict:
    """Kế toán chốt dịch vụ lẻ đã hoàn thành trong tháng: đóng số (doanh thu = booking, giá vốn = dòng NCC) → Kế toán xác nhận → bút toán 154/335/632.
    Chỉ chốt dịch vụ đã thu đủ hoặc đã hủy có phí; dịch vụ còn nợ để lại (báo danh sách)."""
    if u.role not in ("ketoan", "tp_dh", "tgd"): raise HTTPException(403, "Chỉ Kế toán / TP Điều hành chốt dịch vụ lẻ tháng")
    from app.services import accounting as ACC
    y, m = [int(x) for x in month.split("-")]
    first = date(y, m, 1); last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    if last >= date.today(): raise Gate("NP_CHOT", "Chỉ chốt tháng đã kết thúc")
    ts = list(db.execute(select(Tour).where(Tour.tour_type == "non_package", Tour.status.in_(["da_duyet", "ket_thuc"]), Tour.end_date >= first, Tour.end_date <= last)).scalars())
    done, skipped = [], []
    for t in ts:
        bs = [b for b in t.bookings if not b.cancelled]
        rev = sum(b.amount - b.discount for b in bs) + sum(b.cancel_charge for b in t.bookings if b.cancelled)
        paid = sum(b.paid for b in bs)
        if bs and paid < rev - 1:
            skipped.append({"code": t.code, "due": rev - paid}); continue
        lines = list(db.execute(select(TourCostLine).where(TourCostLine.tour_id == t.id, TourCostLine.status == "hd")).scalars())
        cost = sum(l.actual for l in lines) if lines else sum(b.cost_amount for b in bs)
        t.actual_revenue, t.actual_cost, t.closed_at, t.status, t.kt_confirmed_at = rev, cost, datetime.now(), "kt_xac_nhan", datetime.now()
        EV(db, t, "dong_so", u.username, f"Chốt dịch vụ lẻ tháng {month}: doanh thu {rev:,.0f}, giá vốn {cost:,.0f}", title="Chốt dịch vụ lẻ (Kế toán)")
        EV(db, t, "kt_xac_nhan", u.username, "Xác nhận theo lô dịch vụ lẻ")
        ACC.on_settlement_confirmed(db, t, u.username, u.role)
        done.append(t.code)
    R.audit(db, u.username, u.role, "chot_dich_vu_le_thang", f"non_package:{month}", after={"chot": len(done), "de_lai": len(skipped)}); db.commit()
    return {"month": month, "closed": done, "skipped": skipped, "message": f"Đã chốt {len(done)} dịch vụ lẻ tháng {month}" + (f"; để lại {len(skipped)} dịch vụ còn nợ" if skipped else "")}


def print_html(b: Booking, company: str = "CÔNG TY CỔ PHẦN DU LỊCH VIETOURIST") -> str:
    t = b.tour
    rows = [("Mã dịch vụ", t.code), ("Loại dịch vụ", SERVICE_KINDS.get(b.service_type, b.service_type)), ("Nội dung", b.services_note or t.name), ("Quốc gia", b.country or "–"), ("Ngày sử dụng", f"{b.service_date:%d/%m/%Y}" if b.service_date else "–"),
            ("Khách hàng", f"{b.customer_name} – {b.customer_phone}" + (f" – {b.customer_email}" if b.customer_email else "")), ("Số khách", str(b.pax)), ("Giá dịch vụ", f"{b.amount - b.discount:,.0f} đ"),
            ("Đã thanh toán", f"{b.paid:,.0f} đ"), ("Còn lại", f"{max(0.0, b.amount - b.discount - b.paid):,.0f} đ"), ("Nhân viên", b.sales.full_name if b.sales else ""), ("Ghi chú", b.care_note or "–")]
    trs = "".join(f"<tr><td style='padding:6px 10px;border:1px solid #999;width:32%'><b>{k}</b></td><td style='padding:6px 10px;border:1px solid #999'>{v}</td></tr>" for k, v in rows)
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Phiếu xác nhận dịch vụ {t.code}</title></head>
<body style="font-family:'Times New Roman',serif;max-width:720px;margin:24px auto;color:#000">
<div style="text-align:center"><b>{company}</b><br><span style="font-size:12px">Phiếu xác nhận dịch vụ lẻ (Non-package) – in từ VTOS {datetime.now():%d/%m/%Y %H:%M}</span></div>
<h2 style="text-align:center;margin:18px 0">PHIẾU XÁC NHẬN DỊCH VỤ – {t.code}</h2>
<table style="border-collapse:collapse;width:100%">{trs}</table>
<table style="width:100%;margin-top:40px;text-align:center"><tr><td><b>Khách hàng</b><br><br><br><br>{b.customer_name}</td><td><b>Nhân viên lập</b><br><br><br><br>{b.sales.full_name if b.sales else ''}</td><td><b>Kế toán</b><br><br><br><br></td></tr></table>
<script>window.onload=()=>window.print()</script></body></html>"""
