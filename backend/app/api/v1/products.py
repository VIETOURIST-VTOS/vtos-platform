"""API sản phẩm tour (tour cha), mở chuyến từ sản phẩm, và trang chi tiết tour tổng hợp theo tab."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, or_, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.api import schemas as S
from app.models.core import User, Tour, Product, TourEvent, Booking
from app.models.payments import Receipt
from app.models.ops import PaymentRequest
from app.models.hr import GuideAssignment, DispatchOrder, Employee, Vehicle
from app.models.vietrip import TourCostLine
from app.services import products as PS
from app.services import access as AC
from app.services import tours as T
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["san-pham"])


@router.get("/products")
def list_products(q: str = "", status: str = "", limit: int = 500, u: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = select(Product).order_by(Product.code)
    if q: qs = qs.where(or_(Product.code.ilike(f"%{q}%"), Product.name.ilike(f"%{q}%")))
    if status: qs = qs.where(Product.status == status)
    rows = db.execute(qs.limit(limit)).scalars().all()
    n_tours = dict(db.execute(select(Tour.product_code, func.count()).group_by(Tour.product_code)).all())
    return [AC.mask_product({**PS.product_out(p, db), "n_tours": n_tours.get(p.code, 0)}, u) for p in rows]


@router.get("/products/{pid}")
def get_product(pid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    out = AC.mask_product(PS.product_out(p, db), u)
    out["tours"] = [{"id": t.id, "code": t.code, "start_date": t.start_date, "end_date": t.end_date, "status": t.status, "seats_open": t.seats_open, "booked": R.booked_pax(t), "price": t.price_per_pax}
                    for t in db.execute(select(Tour).where(Tour.product_code == p.code).order_by(desc(Tour.start_date)).limit(60)).scalars()]
    return out


@router.post("/products", status_code=201)
def create_product(data: S.ProductIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    p = PS.upsert_product(db, data.model_dump(), u); db.commit()
    return PS.product_out(p, db)


@router.put("/products/{pid}")
def edit_product(pid: int, data: S.ProductIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    d = data.model_dump(); d["code"] = p.code
    PS.upsert_product(db, d, u); db.commit()
    return PS.product_out(p, db)


@router.post("/products/{pid}/open-tour", status_code=201)
def open_tour(pid: int, data: S.OpenTourIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    kw = dict(price_adl=data.price_adl, price_chd=data.price_chd, price_inf=data.price_inf, seats_promo=data.seats_promo, price_promo=data.price_promo, operator_id=data.operator_id, note=data.note)
    if data.date_to and data.weekdays:
        tours = PS.open_series(db, u, p, data.start_date, data.date_to, data.weekdays, data.seats, **kw)
    else:
        tours = [PS.open_tour(db, u, p, data.start_date, data.seats, **kw)]
    db.commit()
    return {"message": f"Đã mở {len(tours)} chuyến từ sản phẩm {p.code} (nháp – kiểm tra 3 con số rồi trình Trưởng phòng)", "tours": [{"id": t.id, "code": t.code, "start_date": t.start_date} for t in tours]}


# ---------- Chi tiết tour tổng hợp (tab) ----------
@router.get("/tours/{tid}/detail")
def tour_detail(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    v = T.tour_view(db, t, u)
    if not AC.can_see_cost(u):
        for k in ("settlement", "fixed_cost", "var_cost_per_pax", "actual_cost", "promo_value", "calc", "justification"): v[k] = None
        vis = AC.sales_ids_visible(db, u)
        if vis is not None: v["bookings"] = [b for b in v.get("bookings", []) if b.get("sales_id") in vis]
    p = db.get(Product, t.product_id) if t.product_id else db.execute(select(Product).where(Product.code == t.product_code)).scalars().first() if t.product_code else None
    v["product"] = AC.mask_product(PS.product_out(p), u) if p else None
    v["seats"] = {"open": t.seats_open, "promo": (t.seats_promo or 0), "booked": R.booked_pax(t), "left": max(0, (t.seats_open or t.planned_pax) - R.booked_pax(t))}
    v["prices"] = {"adl": t.price_per_pax, "chd": t.price_chd, "inf": t.price_inf, "promo": t.price_promo}
    # booking + đã thu
    bks = t.bookings
    paid = dict(db.execute(select(Receipt.booking_id, func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id.in_([b.id for b in bks] or [0]), Receipt.status != "huy").group_by(Receipt.booking_id)).all())
    for b in v["bookings"]:
        bo = next((x for x in bks if x.id == b["id"]), None)
        b["paid"] = float(paid.get(b["id"], 0) or 0); b["due"] = max(0.0, (b["amount"] or 0) - (b["discount"] or 0) - (b["paid"] or 0))
        b["adl"], b["chd"], b["inf"], b["pmt_status"], b["cancelled"], b["cancel_deadline"] = (bo.adl, bo.chd, bo.inf, bo.pmt_status, bo.cancelled, bo.cancel_deadline) if bo else (0, 0, 0, "", False, None)
    v["receipts"] = [{"id": r.id, "code": r.code, "booking_code": next((b.code for b in bks if b.id == r.booking_id), ""), "amount": r.amount, "method": r.method, "payer": r.payer, "status": r.status, "created_at": r.created_at, "confirmed_by": r.confirmed_by}
                     for r in db.execute(select(Receipt).where(Receipt.booking_id.in_([b.id for b in bks] or [0])).order_by(desc(Receipt.created_at))).scalars()]
    v["payment_requests"] = [{"id": r.id, "code": r.code, "category": r.category, "supplier_name": r.supplier_name, "amount": r.amount, "status": r.status, "description": r.description, "created_at": r.created_at, "paid_at": r.paid_at}
                             for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id).order_by(desc(PaymentRequest.id))).scalars()]
    lines = db.execute(select(TourCostLine).where(TourCostLine.tour_id == t.id).order_by(TourCostLine.line_no)).scalars().all()
    v["cost_lines"] = [{"line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "supplier_name": l.supplier_name, "supplier_tax_code": l.supplier_tax_code,
                        "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "actual": l.actual, "paid": l.paid, "note": l.note} for l in lines]
    from app.services import settlement as ST
    lines = [l for l in lines if l.status == "hd"]
    v["cost_lines"] = [ST.line_out(l) for l in ST.lines_of(db, t)]
    v["cost_total"] = {"actual": sum((l.actual or 0) for l in lines), "paid": sum((l.paid or 0) for l in lines)}
    v["settlement_edit"] = {"can_edit": ST.can_edit(u, t), "version": t.settlement_version, "service_types": ST.SERVICE_TYPES, "summary": ST.summary(db, t), "checks": ST.checks(db, t)}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    # Như trên: đơn giá hiển thị giữ nguyên rỗng, chỉ thù lao mới xử rỗng thành 0.
    v["guides"] = [{"id": a.id, "guide": emps.get(a.guide_id, ""), "days": a.days,
                    "rate_per_day": a.rate_per_day, "holiday": a.holiday, "status": a.status,
                    "amount": (a.rate_per_day or 0) * a.days * (2 if a.holiday else 1)}
                   for a in db.execute(select(GuideAssignment).where(GuideAssignment.tour_id == t.id)).scalars()]
    veh = {x.id: x.plate for x in db.execute(select(Vehicle)).scalars()}
    v["dispatch"] = [{"id": d.id, "plate": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "date_from": d.date_from, "date_to": d.date_to, "internal_price": d.internal_price, "status": d.status}
                     for d in db.execute(select(DispatchOrder).where(DispatchOrder.tour_id == t.id)).scalars()]
    v["events"] = [{"id": e.id, "step": e.step, "title": e.title, "note": e.note, "actor": e.actor, "source": e.source, "at": e.at}
                   for e in db.execute(select(TourEvent).where(TourEvent.tour_id == t.id).order_by(desc(TourEvent.at), desc(TourEvent.id))).scalars()]
    # B3 – Ý kiến thẩm định 06/9/2026: chi phí trên đầu trang là chi phí ĐÃ GHI NHẬN, không phải giá vốn
    # đầy đủ của chuyến. Với tour đang bán chưa có dòng quyết toán, số này gần 0 nên "lợi nhuận" xấp xỉ
    # toàn bộ doanh thu – phải ghi rõ là TẠM TÍNH và cảnh báo ngay cạnh chỉ tiêu.
    v["summary"] = {"revenue_booking": sum((b["amount"] or 0) - (b["discount"] or 0) for b in v["bookings"] if not b["cancelled"]), "collected": sum((b["paid"] or 0) for b in v["bookings"]),
                    "cost_actual": v["cost_total"]["actual"] or (t.actual_cost or 0), "cost_paid": sum((r.amount or 0) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status == "da_chi")).scalars())}
    v["summary"]["profit"] = ((t.actual_revenue or 0) or v["summary"]["revenue_booking"]) - v["summary"]["cost_actual"]
    confirmed = t.status in ("kt_xac_nhan", "khoa")
    n_lines = len(lines)
    v["summary"]["cost_lines"] = n_lines
    v["summary"]["profit_state"] = "xac_nhan" if confirmed else "tam_tinh"
    v["summary"]["cost_basis"] = ("quyet_toan" if n_lines else ("tong_hop_vietrip" if t.actual_cost else "chua_co"))
    if confirmed:
        v["summary"]["warning"] = ""
    elif not n_lines and not t.actual_cost:
        v["summary"]["warning"] = "Chuyến chưa có dòng chi phí quyết toán – lợi nhuận chỉ là chênh lệch doanh thu trừ chi phí đã ghi nhận, KHÔNG phải lợi nhuận của chuyến"
    elif t.end_date >= date.today():
        v["summary"]["warning"] = "Chuyến chưa kết thúc – chi phí còn phát sinh, lợi nhuận là số tạm tính"
    else:
        v["summary"]["warning"] = "Quyết toán chưa được Kế toán xác nhận – lợi nhuận là số tạm tính"
    from app.models.core import AuditLog
    v["audit"] = [{"id": l.id, "ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action, "before": l.before, "after": l.after}
                  for l in db.execute(select(AuditLog).where(AuditLog.entity == f"tour:{t.code}").order_by(desc(AuditLog.id)).limit(100)).scalars()]
    return v
