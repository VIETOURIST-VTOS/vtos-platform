"""Quyết toán tour soạn trên VTOS (theo bố cục bảng quyết toán Vietrip):
dòng chi phí theo NCC (mô tả, loại DV, NCC–MST, cách tính, đơn giá, SL, hệ số, dự toán, thực chi, đã thanh toán, chứng từ),
kiểm tra nhập theo dòng, phiên bản V.01/V.02, khớp 'đã thanh toán' với lệnh chi NCC / tạm ứng, so dự toán – thực chi, chấm thiếu chứng từ."""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Tour
from app.models.vietrip import TourCostLine
from app.models.ops import PaymentRequest
from app.services import rules as R
from app.services.vietrip import _strip_accents


def _norm(s: str) -> str:
    return " ".join(_strip_accents((s or "").upper()).split())[:80]

SERVICE_TYPES = {"GUIDE": "Hướng dẫn viên", "HOTEL": "Khách sạn", "RESTAURANT": "Nhà hàng", "LAND": "Tham quan / landtour", "VEHICLE": "Xe", "FLIGHT": "Vé máy bay",
                 "INSURANCE": "Bảo hiểm", "TICKET": "Vé tàu / vé tham quan", "VISA": "Visa", "GIFT": "Quà tặng / nón / nước", "OTHER": "Khác"}
COST_KINDS = ("co_dinh", "theo_khach")
EDITABLE = ("da_duyet", "ket_thuc")          # Điều hành soạn quyết toán cho tới khi đóng số; Kế toán trả lại → quay về ket_thuc
MAX_DOC = 1_500_000 * 4 // 3                 # ~1,5 MB nhị phân dưới dạng data URL


class Gate(HTTPException):
    def __init__(self, code: str, msg: str): super().__init__(422, {"gate": code, "message": msg})


def calc_actual(kind: str, unit_price: float, qty: float, coef: float) -> float:
    """Theo khách: đơn giá × số khách × hệ số. Cố định: đơn giá × hệ số (SL chỉ để ghi nhận số khách)."""
    return round(unit_price * qty * coef if kind == "theo_khach" else unit_price * coef)


def can_edit(u: User, t: Tour) -> bool:
    return u.id == t.operator_id and t.status in EDITABLE


def _assert_edit(u: User, t: Tour):
    if u.id != t.operator_id: raise Gate("CONG_6", f"Một cửa: chỉ người điều hành chuyến ({t.operator.full_name}) soạn quyết toán")
    if t.status not in EDITABLE:
        raise Gate("TRANG_THAI", "Quyết toán đã đóng số / Kế toán đã xác nhận – chỉ sửa khi Kế toán trả lại" if t.status in ("da_dong_so", "kt_xac_nhan", "khoa") else "Tour chưa được duyệt")


def validate(d: dict) -> dict:
    out = {"description": (d.get("description") or "").strip()[:200], "service_type": (d.get("service_type") or "OTHER").upper()[:30], "cost_kind": d.get("cost_kind") or "co_dinh",
           "supplier_name": (d.get("supplier_name") or "").strip()[:200], "supplier_tax_code": (d.get("supplier_tax_code") or "").strip()[:20],
           "unit_price": float(d.get("unit_price") or 0), "qty": float(d.get("qty") or 0), "coef": float(d.get("coef") or 1), "budget": float(d.get("budget") or 0),
           "note": (d.get("note") or "").strip()[:200]}
    if not out["description"]: raise Gate("QT_NHAP", "Vui lòng nhập Mô tả chi tiết")
    if out["service_type"] not in SERVICE_TYPES: raise Gate("QT_NHAP", "Loại dịch vụ không hợp lệ")
    if not out["supplier_name"]: raise Gate("QT_NHAP", "Vui lòng nhập Nhà cung cấp")
    if out["cost_kind"] not in COST_KINDS: raise Gate("QT_NHAP", "Vui lòng chọn Cách tính chi (cố định / theo khách)")
    if out["unit_price"] < 0: raise Gate("QT_NHAP", "Đơn giá thực tế không được âm")
    if out["coef"] <= 0: raise Gate("QT_NHAP", "Hệ số phải lớn hơn 0")
    if out["cost_kind"] == "theo_khach" and out["qty"] <= 0: raise Gate("QT_NHAP", "Số khách (Pax) phải lớn hơn 0")
    out["actual"] = calc_actual(out["cost_kind"], out["unit_price"], out["qty"], out["coef"])
    if out["actual"] < 0: raise Gate("QT_NHAP", "Tổng thực chi không được âm")
    if d.get("paid") is not None: out["paid"] = max(0.0, float(d.get("paid") or 0))
    return out


def lines_of(db: Session, t: Tour, active_only: bool = False) -> list[TourCostLine]:
    q = select(TourCostLine).where(TourCostLine.tour_id == t.id)
    if active_only: q = q.where(TourCostLine.status == "hd")
    return list(db.execute(q.order_by(TourCostLine.line_no, TourCostLine.id)).scalars())


def line_out(l: TourCostLine) -> dict:
    over = (l.actual - l.budget) / l.budget if l.budget else 0
    return {"id": l.id, "line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "service_name": SERVICE_TYPES.get(l.service_type, l.service_type),
            "supplier_name": l.supplier_name, "supplier_tax_code": l.supplier_tax_code, "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "budget": l.budget, "actual": l.actual, "paid": l.paid,
            "remaining": max(0.0, l.actual - l.paid), "over_pct": over, "note": l.note, "source": l.source, "status": l.status, "version": l.version, "has_doc": bool(l.doc_data), "doc_name": l.doc_name,
            "updated_by": l.updated_by, "updated_at": l.updated_at}


def add_line(db: Session, u: User, t: Tour, d: dict) -> TourCostLine:
    _assert_edit(u, t); v = validate(d)
    n = (db.execute(select(func.max(TourCostLine.line_no)).where(TourCostLine.tour_id == t.id)).scalar() or 0) + 1
    l = TourCostLine(tour_id=t.id, line_no=n, source="vtos", version=t.settlement_version, updated_by=u.username, paid=v.pop("paid", 0.0), **v)
    db.add(l); db.flush()
    R.audit(db, u.username, u.role, "qt_them_dong", f"tour:{t.code}", after={"dong": n, "mo_ta": l.description, "ncc": l.supplier_name, "thuc_chi": l.actual, "v": t.settlement_version})
    db.commit(); db.refresh(l); return l


def update_line(db: Session, u: User, t: Tour, l: TourCostLine, d: dict) -> TourCostLine:
    _assert_edit(u, t)
    if l.status != "hd": raise Gate("QT_NHAP", "Dòng đã hủy – không sửa")
    v = validate(d); before = {"thuc_chi": l.actual, "don_gia": l.unit_price, "sl": l.qty, "hs": l.coef, "da_tt": l.paid}
    for k, x in v.items(): setattr(l, k, x)
    l.version, l.updated_by, l.source = t.settlement_version, u.username, "vtos" if l.source != "vietrip" else "vietrip+vtos"
    R.audit(db, u.username, u.role, "qt_sua_dong", f"tour:{t.code}", before=before, after={"dong": l.line_no, "thuc_chi": l.actual, "da_tt": l.paid, "v": t.settlement_version})
    db.commit(); db.refresh(l); return l


def cancel_line(db: Session, u: User, t: Tour, l: TourCostLine, reason: str) -> None:
    _assert_edit(u, t)
    if not (reason or "").strip(): raise Gate("QT_NHAP", "Hủy dòng phải có lý do")
    l.status, l.note, l.updated_by, l.version = "huy", (f"[HỦY] {reason.strip()} | " + l.note)[:200], u.username, t.settlement_version
    R.audit(db, u.username, u.role, "qt_huy_dong", f"tour:{t.code}", after={"dong": l.line_no, "mo_ta": l.description, "ly_do": reason.strip()[:120]})
    db.commit()


def set_doc(db: Session, u: User, t: Tour, l: TourCostLine, name: str, data: str) -> None:
    """Gắn chứng từ (ảnh/PDF data URL) cho dòng. Sau đóng số vẫn cho bổ sung chứng từ (không đổi số)."""
    if u.id != t.operator_id and u.role not in ("ketoan", "cntt"): raise Gate("CONG_6", "Chỉ người điều hành chuyến hoặc Kế toán gắn chứng từ")
    if t.status in ("kt_xac_nhan", "khoa"): raise Gate("TRANG_THAI", "Tour đã xác nhận/khóa – không thay chứng từ")
    if data and not data.startswith(("data:image/", "data:application/pdf")): raise Gate("QT_NHAP", "Chứng từ phải là ảnh hoặc PDF")
    if len(data) > MAX_DOC: raise Gate("QT_NHAP", "Tệp quá lớn (tối đa ~1,5 MB) – vui lòng nén ảnh")
    l.doc_name, l.doc_data, l.updated_by = (name or "")[:160], data, u.username
    R.audit(db, u.username, u.role, "qt_gan_chung_tu" if data else "qt_go_chung_tu", f"tour:{t.code}", after={"dong": l.line_no, "tep": l.doc_name}); db.commit()


def match_paid(db: Session, t: Tour) -> dict:
    """Khớp cột 'Đã thanh toán' với lệnh chi NCC đã chi (chi_tour) và tạm ứng đã chi (tam_ung) của tour: ưu tiên trùng MST, sau đó trùng tên NCC (bỏ dấu);
    mỗi lệnh chi chỉ dùng một lần, phân bổ tuần tự theo thứ tự dòng."""
    prs = list(db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status == "da_chi", PaymentRequest.category.in_(["chi_tour", "tam_ung"]))).scalars())
    pool = [{"id": p.id, "mst": (p.supplier_tax_code or "").strip(), "name": _norm(p.supplier_name), "left": p.amount} for p in prs]
    matched, unmatched = 0, 0
    for l in lines_of(db, t, active_only=True):
        if l.source == "vietrip" and l.paid > 0 and not prs: continue
        mst, name = (l.supplier_tax_code or "").strip(), _norm(l.supplier_name)
        cands = [p for p in pool if p["left"] > 0 and ((mst and p["mst"] == mst) or (name and p["name"] == name))]
        paid = 0.0
        for p in cands:
            take = min(p["left"], max(0.0, l.actual - paid))
            if take <= 0: break
            p["left"] -= take; paid += take
        if cands:
            l.paid = round(paid); matched += 1
        else:
            unmatched += 1
    leftover = round(sum(p["left"] for p in pool))
    db.commit()
    return {"matched": matched, "unmatched": unmatched, "payments": len(prs), "leftover": leftover,
            "message": f"Đã khớp {matched} dòng với {len(prs)} lệnh chi/tạm ứng đã chi" + (f"; {unmatched} dòng chưa có lệnh chi" if unmatched else "") + (f"; còn {leftover:,.0f} đ lệnh chi chưa gắn dòng" if leftover > 0 else "")}


def summary(db: Session, t: Tour) -> dict:
    ls = lines_of(db, t, active_only=True)
    actual = sum(l.actual for l in ls); paid = sum(l.paid for l in ls)
    budget_lines = sum(l.budget for l in ls)
    budget_tour = t.fixed_cost + t.var_cost_per_pax * R.booked_pax(t)
    budget = budget_lines or budget_tour
    rev = sum(b.amount - b.discount for b in t.bookings if not b.cancelled)
    profit = rev - actual - t.promo_value
    return {"lines": len(ls), "cancelled": sum(1 for l in lines_of(db, t) if l.status != "hd"), "actual": actual, "paid": paid, "remaining": max(0.0, actual - paid),
            "budget": budget, "budget_source": "dong" if budget_lines else "du_toan_tour", "variance": actual - budget, "variance_pct": (actual - budget) / budget if budget else 0,
            "revenue": rev, "profit": profit, "margin": profit / rev if rev else 0, "version": t.settlement_version, "with_doc": sum(1 for l in ls if l.doc_data)}


def checks(db: Session, t: Tour) -> list[dict]:
    """Chấm quyết toán trước khi đóng số: block = chặn đóng số; warn = cảnh báo (Kế toán xem)."""
    ls = lines_of(db, t, active_only=True); out = []
    thr = R.get_param(db, "nguong_bien", t.end_date) or 0.1
    for l in ls:
        if l.budget and l.actual > l.budget * (1 + thr) and not l.note.strip():
            out.append({"level": "block", "line": l.line_no, "msg": f"Dòng {l.line_no} {l.description}: thực chi vượt dự toán {((l.actual - l.budget) / l.budget) * 100:.0f}% – phải ghi lời giải trình ở Ghi chú"})
        if not l.supplier_tax_code and l.service_type in ("HOTEL", "RESTAURANT", "VEHICLE", "FLIGHT", "LAND", "INSURANCE") and l.actual >= 5_000_000:
            out.append({"level": "warn", "line": l.line_no, "msg": f"Dòng {l.line_no}: NCC {l.supplier_name} chưa có MST (chi ≥ 5 triệu cần hóa đơn)"})
        if not l.doc_data and l.actual > 0:
            out.append({"level": "warn", "line": l.line_no, "msg": f"Dòng {l.line_no}: chưa gắn chứng từ"})
        if l.paid > l.actual + 1:
            out.append({"level": "warn", "line": l.line_no, "msg": f"Dòng {l.line_no}: đã thanh toán {l.paid:,.0f} lớn hơn thực chi {l.actual:,.0f}"})
    s = summary(db, t)
    if s["budget"] and s["variance_pct"] > thr:
        out.append({"level": "warn", "line": 0, "msg": f"Tổng thực chi vượt dự toán {s['variance_pct'] * 100:.0f}% (> {thr * 100:.0f}%) – TGĐ xem khi Kế toán xác nhận"})
    if s["remaining"] > 0:
        out.append({"level": "info", "line": 0, "msg": f"Còn lại cần thanh toán NCC: {s['remaining']:,.0f} đ"})
    return out


def kt_return(db: Session, u: User, t: Tour, note: str) -> str:
    """Kế toán trả lại quyết toán để Điều hành sửa: trạng thái về ket_thuc, tăng phiên bản, ghi lịch sử."""
    from app.services.products import event as EV
    if u.role != "ketoan": raise HTTPException(403, "Chỉ Kế toán trả lại quyết toán")
    if t.status != "da_dong_so": raise Gate("TRANG_THAI", "Chỉ trả lại quyết toán đang chờ Kế toán xác nhận")
    if not (note or "").strip(): raise Gate("QT_NHAP", "Trả lại phải ghi rõ lý do")
    t.status, t.closed_at, t.settlement_version = "ket_thuc", None, t.settlement_version + 1
    EV(db, t, "kt_tra_lai", u.username, note, title=f"Kế toán trả lại quyết toán → soạn lại V.{t.settlement_version:02d}")
    R.audit(db, u.username, u.role, "ke_toan_tra_lai_quyet_toan", f"tour:{t.code}", after={"v": t.settlement_version, "ly_do": note[:200]}); db.commit()
    return f"Đã trả lại – Điều hành soạn lại quyết toán V.{t.settlement_version:02d}"
