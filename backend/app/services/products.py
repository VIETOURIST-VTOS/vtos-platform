"""Sản phẩm tour (tour cha) và mở chuyến từ sản phẩm – theo cấu trúc Vietrip, bọc cổng kiểm soát VTOS."""
import re
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.core import Product, Tour, TourEvent, User, COST_ITEMS
from app.services import rules as R

STEP_TITLES = {"khoi_tao": "Khởi tạo tour / dự toán", "trinh_du_toan": "Đề nghị phê duyệt dự toán", "tp_xac_nhan": "Trưởng phòng Điều hành xác nhận",
               "duyet": "Phê duyệt dự toán", "ky": "Ký duyệt chuyến dưới biên", "d7": "Quyết định mốc D-7", "dong_so": "Đóng số quyết toán",
               "kt_xac_nhan": "Kế toán xác nhận quyết toán", "cntt_khoa": "CNTT đối chiếu & khóa tour", "kt_tra_lai": "Kế toán trả lại quyết toán", "sua_du_toan": "Sửa dự toán", "vietrip": "Vietrip"}


def event(db: Session, t: Tour, step: str, actor: str, note: str = "", source: str = "vtos", at: datetime | None = None, title: str | None = None):
    db.add(TourEvent(tour_id=t.id, step=step, title=title or STEP_TITLES.get(step, step), note=(note or "")[:2000], actor=actor[:120], source=source, at=at or datetime.now()))


def product_out(p: Product, db: Session | None = None) -> dict:
    op = db.get(User, p.operator_id) if (db and p.operator_id) else None
    return {"id": p.id, "code": p.code, "name": p.name, "vietrip_id": p.vietrip_id, "tour_type": p.tour_type, "departure_point": p.departure_point, "region": p.region, "country": p.country,
            "sale_point": p.sale_point, "transport": p.transport, "vehicle_type": p.vehicle_type, "length_text": p.length_text, "days": p.days, "reference_price": p.reference_price,
            "deposit_pct": p.deposit_pct, "days_to_close": p.days_to_close, "requires_confirmation": p.requires_confirmation, "cost_structure": p.cost_structure or {},
            "cost_lines": p.cost_lines or [], "program": p.program, "services": p.services, "status": p.status, "operator_id": p.operator_id, "operator_name": op.full_name if op else "",
            "source": p.source, "fixed_cost": p.fixed_cost(), "var_cost_per_pax": p.var_cost_per_pax(), "updated_at": p.updated_at, "cost_items": COST_ITEMS}


def upsert_product(db: Session, data: dict, u: User | None, source: str = "vtos") -> Product:
    code = (data.get("code") or "").strip().upper()
    if not code: raise HTTPException(422, "Thiếu mã sản phẩm")
    p = db.execute(select(Product).where(Product.code == code)).scalars().first()
    if not p:
        p = Product(code=code, name=data.get("name") or code, source=source); db.add(p)
    for k in ("name", "tour_type", "departure_point", "region", "country", "sale_point", "transport", "vehicle_type", "length_text", "program", "services", "status"):
        if data.get(k) is not None: setattr(p, k, str(data[k])[:300] if k != "program" else str(data[k]))
    for k in ("days", "days_to_close"):
        if data.get(k) is not None: setattr(p, k, int(data[k] or 0))
    for k in ("reference_price", "deposit_pct"):
        if data.get(k) is not None: setattr(p, k, float(data[k] or 0))
    if data.get("requires_confirmation") is not None: p.requires_confirmation = bool(data["requires_confirmation"])
    if data.get("cost_structure") is not None: p.cost_structure = {k: float(v or 0) for k, v in dict(data["cost_structure"]).items()}
    if data.get("cost_lines") is not None: p.cost_lines = list(data["cost_lines"])[:200]
    if data.get("operator_id") is not None: p.operator_id = data["operator_id"]
    if data.get("vietrip_id") is not None: p.vietrip_id = int(data["vietrip_id"])
    db.flush()
    if u: R.audit(db, u.username, u.role, "cap_nhat_san_pham", f"product:{p.code}", after={k: data.get(k) for k in ("name", "reference_price", "days") if k in data})
    return p


def next_tour_code(db: Session, p: Product, start: date) -> str:
    """Mã chuyến theo quy ước Vietrip: MÃSP.NNddmmyy với NN = số ngày (2 chữ số)."""
    base = f"{p.code}.{max(1, p.days or 1):02d}{start:%d%m%y}"
    code, n = base, 1
    while db.execute(select(Tour).where(Tour.code == code)).scalars().first():
        n += 1; code = f"{base}_{n}"
    return code


def open_tour(db: Session, u: User, p: Product, start: date, seats: int, price_adl: float | None = None, price_chd: float = 0, price_inf: float = 0,
              seats_promo: int = 0, price_promo: float = 0, operator_id: int | None = None, note: str = "") -> Tour:
    if u.role not in ("nv_dh", "tp_dh", "cntt"): raise HTTPException(403, "Chỉ Phòng Điều hành mở tour từ sản phẩm (ĐH Điều 2)")
    days = max(1, p.days or 1)
    t = Tour(code=next_tour_code(db, p, start), name=p.name, tour_type=p.tour_type, start_date=start, end_date=start + timedelta(days=days - 1),
             operator_id=operator_id or p.operator_id or u.id, price_per_pax=float(price_adl if price_adl is not None else p.reference_price),
             fixed_cost=p.fixed_cost(), var_cost_per_pax=p.var_cost_per_pax(), planned_pax=int(seats or 0), rest_stops="",
             product_id=p.id, product_code=p.code, vehicle_type=p.vehicle_type, departure_point=p.departure_point, transport=p.transport, days=days,
             seats_open=int(seats or 0), seats_promo=int(seats_promo or 0), price_chd=float(price_chd or 0), price_inf=float(price_inf or 0), price_promo=float(price_promo or 0), country=p.country)
    db.add(t); db.flush()
    event(db, t, "khoi_tao", u.username, note or f"Mở chuyến từ sản phẩm {p.code} – {p.name}; dự toán lấy từ cơ cấu chi phí sản phẩm")
    R.audit(db, u.username, u.role, "mo_tour_tu_san_pham", f"tour:{t.code}", after={"san_pham": p.code, "khoi_hanh": str(start), "cho": seats, "gia": t.price_per_pax})
    return t


def open_series(db: Session, u: User, p: Product, date_from: date, date_to: date, weekdays: list[int], seats: int, **kw) -> list[Tour]:
    """Mở chuyến theo lịch lặp (thứ trong tuần, 0 = Thứ Hai) như Vietrip."""
    out = []; d = date_from
    while d <= date_to and len(out) < 120:
        if d.weekday() in weekdays: out.append(open_tour(db, u, p, d, seats, **kw))
        d += timedelta(days=1)
    return out


def guess_type(code: str, tour_type_text: str, name: str = "") -> str:
    intl = "quốc tế" in (tour_type_text or "").lower() or "quoc te" in (tour_type_text or "").lower()
    doan = code.upper().startswith("MICE") or "MICE" in (name or "").upper()
    return ("doan_" if doan else "le_") + ("nuoc_ngoai" if intl else "noi_dia")
