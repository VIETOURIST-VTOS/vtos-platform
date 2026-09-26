"""Vòng đời booking sau khi tạo (theo vận hành Vietrip): % cọc & trạng thái thanh toán, deadline hủy chỗ, khóa/mở khóa booking,
hủy booking có phí, tiền bảo lưu (dùng cho booking mới / hoàn tiền / hủy bảo lưu), robot R4 cảnh báo cọc – deadline – bảo lưu hết hạn."""
from datetime import datetime, date, timedelta, time
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Tour, Booking, Alert
from app.models.payments import Receipt, Retention
from app.models.ops import PaymentRequest
from app.services import rules as R
from app.services import accounting as ACC
from app.services import payments as PAY
from app.api.deps import toan_quyen   # Chủ tịch toàn quyền – MỘT luật, xem deps.toan_quyen

# MỞ KHOÁ BOOKING — Chủ tịch quyết lại 25/9/2026: "tp dh, sale admin".
#
# GỠ `gd_kd` và `tp_kd`. Hai vai ấy mở khoá được từ bản cũ, thừa kế chứ chưa ai xác nhận lại. Mở
# khoá không phải xem — nó là quyền SỬA SỐ SAU KHI ĐÃ CHỐT, và người bán không nên tự mở lại con
# số doanh thu của chính mình. Đây là một lần SIẾT, ghi ra để ai đọc sau cũng thấy là cố ý.
#
# THÊM `sales_admin`: đúng vai giữ hồ sơ phòng Đoàn, và Phần V bản mô tả cấm chị ấy ba việc —
# nhận khách, chốt đoàn, duyệt dự toán — mở khoá một booking để sửa hồ sơ không nằm trong ba việc ấy.
#
# GIỮ `cntt` và `tgd`: một bên vận hành hệ thống, một bên là cấp trên của cả hai phòng. Chủ tịch đi
# qua bằng luật toàn quyền, không cần có tên ở đây.
UNLOCK_ROLES = ("tp_dh", "sales_admin", "cntt", "tgd")
CANCEL_ROLES = ("nv_dh", "tp_dh")


class Gate(HTTPException):
    def __init__(self, code: str, msg: str): super().__init__(422, {"gate": code, "message": msg})


# ---------- cọc, trạng thái thanh toán, deadline ----------
def net(b: Booking) -> float: return max(0.0, (b.amount or 0) - (b.discount or 0))
def deposit_due(b: Booking) -> float: return round(net(b) * (b.deposit_pct or 0) / 100)


def pmt_status_of(b: Booking) -> str:
    if b.cancelled: return "CANCEL"
    if (b.paid or 0) >= net(b) - 1 and net(b) > 0: return "PAID"
    if (b.paid or 0) >= deposit_due(b) and (b.paid or 0) > 0: return "DEPO"
    return "UNPAID"


def refresh_status(b: Booking) -> None:
    b.pmt_status = pmt_status_of(b)


def init_terms(db: Session, b: Booking, t: Tour) -> None:
    """Gán % cọc và deadline hủy chỗ khi tạo booking: theo sản phẩm, không có thì theo tham số."""
    from app.models.core import Product
    p = db.get(Product, t.product_id) if t.product_id else None
    pct = float(p.deposit_pct) if p and p.deposit_pct else R.get_param(db, "coc_mac_dinh_pct")
    days = int(p.days_to_close) if p and p.days_to_close is not None else int(R.get_param(db, "han_huy_cho_ngay"))
    b.deposit_pct = pct
    b.cancel_deadline = datetime.combine(t.start_date - timedelta(days=days), time(17, 0))
    refresh_status(b)
    # VPM-7 – đặt hạn giữ chỗ ngay từ đây. Đặt muộn hơn (để robot lo) nghĩa là trong khoảng thời gian
    # ấy booking giữ chỗ không có hạn, và không ai nhìn màn hình biết được nó sẽ hết hạn lúc nào.
    from app.services import giu_cho as GC
    if b.id:
        GC.dat_han(db, b, t)
    else:
        b.giu_cho_den = GC.han_mac_dinh(db, b, t)


def booking_view(b: Booking) -> dict:
    return {"deposit_pct": b.deposit_pct, "deposit_due": deposit_due(b), "pmt_status": pmt_status_of(b), "cancel_deadline": b.cancel_deadline,
            "locked": b.locked, "lock_reason": b.lock_reason, "cancelled": b.cancelled, "cancel_reason": b.cancel_reason, "cancelled_at": b.cancelled_at, "cancel_charge": b.cancel_charge,
            "past_deadline": bool(b.cancel_deadline and datetime.now() > b.cancel_deadline and not b.cancelled),
            # VPM-7 – giữ chỗ có thời hạn. `giu_cho_het` là "chỗ đã trả về tour", KHÔNG phải "booking đã huỷ".
            "giu_cho_den": b.giu_cho_den, "giu_cho_het": b.giu_cho_het, "giu_cho_het_luc": b.giu_cho_het_luc,
            "gia_han_lan": b.gia_han_lan,
            "qua_han_giu_cho": bool(b.giu_cho_den and datetime.now() > b.giu_cho_den and not b.giu_cho_het and not b.cancelled)}


# ---------- cập nhật thông tin khách, khóa / mở khóa ----------
def update_customer(db: Session, u: User, b: Booking, d: dict) -> Booking:
    if u.role not in ("nv_dh", "tp_dh") and u.id != b.sales_id and not toan_quyen(u): raise HTTPException(403, "Chỉ Điều hành hoặc sale phụ trách sửa thông tin khách")
    if b.cancelled: raise Gate("TRANG_THAI", "Booking đã hủy")
    if b.locked: raise Gate("KHOA_BOOKING", f"Booking đã khóa ({b.lock_reason}) – TP Điều hành / GĐ KD mở khóa mới sửa được")
    before = {"khach": b.customer_name, "sdt": b.customer_phone, "adl": b.adl, "chd": b.chd, "inf": b.inf}
    # VPM-8 – đây đúng là trường hợp mà V10 lấy làm ví dụ: "sale sửa khách, kế toán sửa số tiền".
    # Cột phiên bản có từ V10 nhưng cửa này chưa bao giờ đọc nó, nên hai người vẫn đè lên nhau lặng lẽ.
    from app.services import ghi_mot_lan as GML
    GML.kiem_phien_ban(b, d.get("phien_ban"), f"Booking {b.code}",
                       lambda: {**before, "phien_ban": b.phien_ban, "pax": b.pax})
    for k in ("customer_name", "customer_phone", "care_note", "services_note"):
        if d.get(k) is not None: setattr(b, k, str(d[k]).strip()[:200])
    for k in ("adl", "chd", "inf"):
        if d.get(k) is not None: setattr(b, k, max(0, int(d[k])))
    if any(d.get(k) is not None for k in ("adl", "chd", "inf")) and (b.adl + b.chd + b.inf) > 0:
        b.pax = b.adl + b.chd + b.inf   # số khách theo cơ cấu; tiền không tự tính lại (giữ giá đã chốt)
    GML.tang_phien_ban(b)
    R.audit(db, u.username, u.role, "sua_thong_tin_khach", f"booking:{b.code}", before=before, after={"khach": b.customer_name, "sdt": b.customer_phone, "adl": b.adl, "chd": b.chd, "inf": b.inf})
    db.commit(); db.refresh(b); return b


def lock(db: Session, b: Booking, reason: str, actor: str = "robot", audit: bool = True) -> None:
    if b.locked or b.cancelled: return
    b.locked, b.lock_reason = True, reason[:120]
    if audit: R.audit(db, actor, "robot" if actor == "robot" else actor, "khoa_booking", f"booking:{b.code}", after={"ly_do": reason})


def unlock(db: Session, u: User, b: Booking, note: str) -> str:
    if u.role not in UNLOCK_ROLES and not toan_quyen(u): raise HTTPException(403, "Chỉ TP Điều hành / Sale Admin / CNTT mở khóa booking")
    if not b.locked: raise Gate("TRANG_THAI", "Booking chưa khóa")
    if not (note or "").strip(): raise Gate("KHOA_BOOKING", "Mở khóa phải ghi lý do")
    b.locked, b.lock_reason = False, ""
    R.audit(db, u.username, u.role, "mo_khoa_booking", f"booking:{b.code}", after={"ly_do": note[:200]}); db.commit()
    return f"Đã mở khóa {b.code} – nhớ khóa lại sau khi sửa (robot sẽ khóa lại khi đóng tour)"


def auto_lock(db: Session) -> int:
    """Robot: khóa booking khi tour đã đóng (qua deadline hủy chỗ) hoặc đã thu đủ."""
    n = 0; now = datetime.now(); codes = []
    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.locked == False, Booking.cancelled == False, Tour.start_date >= date.today() - timedelta(days=60))
    for b in db.execute(q).scalars():
        st = pmt_status_of(b)
        if b.cancel_deadline and now > b.cancel_deadline:
            lock(db, b, f"Đóng tour {b.cancel_deadline:%d/%m} – không sửa khách", audit=False); n += 1; codes.append(b.code)
        elif st == "PAID":
            lock(db, b, "Đã thu đủ tiền – khóa cập nhật khách", audit=False); n += 1; codes.append(b.code)
        if b.pmt_status != st: b.pmt_status = st
    if n: R.audit(db, "robot", "robot", "khoa_booking_tu_dong", "robot", after={"so_luong": n, "booking": codes[:50]})
    db.commit(); return n


# ---------- hủy booking, tiền bảo lưu ----------
def _next_bl(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(Retention)).scalar() + 1
    return f"BL{date.today():%y%m}-{n:04d}"


def cancel(db: Session, u: User, b: Booking, reason: str, charge: float = 0, retain: bool = True, expires_days: int | None = None) -> dict:
    """Điều hành hủy booking (một cửa). Tiền đã nộp − phí hủy → bảo lưu (mặc định) hoặc đề nghị chi hoàn tiền."""
    if u.role not in CANCEL_ROLES and not toan_quyen(u): raise HTTPException(403, "Chỉ Phòng Điều hành hủy booking (một cửa)")
    if b.cancelled: raise Gate("TRANG_THAI", "Booking đã hủy")
    if not (reason or "").strip(): raise Gate("HUY_BOOKING", "Hủy booking phải ghi lý do (hiển thị ở Tiền bảo lưu)")
    if b.tour and b.tour.status in ("da_dong_so", "kt_xac_nhan", "khoa"): raise Gate("TRANG_THAI", "Tour đã đóng số quyết toán – không hủy booking; xử lý qua hoàn tiền")
    b.paid = PAY.paid_amount(db, b.id)
    charge = max(0.0, min(float(charge or 0), (b.paid or 0)))
    late = bool(b.cancel_deadline and datetime.now() > b.cancel_deadline)
    before = {"amount": b.amount, "paid": b.paid}
    b.cancelled, b.cancelled_at, b.cancel_reason, b.cancel_charge = True, datetime.now(), reason.strip()[:200], charge
    b.amount, b.discount = charge, 0.0     # doanh thu còn lại của booking = phí hủy giữ lại
    b.pmt_status = "CANCEL"
    for a in db.execute(select(Alert).where(Alert.ref == f"booking:{b.code}", Alert.resolved == False)).scalars(): a.resolved = True
    out = {"booking": b.code, "paid": b.paid, "charge": charge, "late": late, "retention": None, "refund": None}
    left = round((b.paid or 0) - charge)
    if left > 0:
        if retain:
            days = expires_days if expires_days is not None else int(R.get_param(db, "bao_luu_han_ngay"))
            rt = Retention(code=_next_bl(db), booking_id=b.id, tour_code=b.tour.code if b.tour else "", customer_name=b.customer_name, customer_phone=b.customer_phone,
                           amount=left, remaining=left, note=reason.strip()[:300], expires_on=date.today() + timedelta(days=days) if days > 0 else None, created_by=u.username)
            db.add(rt); db.flush(); out["retention"] = rt.code
        else:
            from app.services import ops as OPS
            pr = OPS.create_request(db, u, {"category": "hoan_tien", "tour_id": b.tour_id, "supplier_name": b.customer_name, "supplier_tax_code": "", "amount": left,
                                            "description": f"Hoàn tiền khách hủy booking {b.code}: {reason.strip()[:120]}", "has_document": True, "document_ref": f"booking:{b.code}", "has_invoice": False})
            out["refund"] = pr.code
    R.audit(db, u.username, u.role, "huy_booking", f"booking:{b.code}", before=before, after={"ly_do": reason[:200], "phi_huy": charge, "sau_deadline": late, "bao_luu": out["retention"], "hoan_tien": out["refund"]})
    db.commit()
    out["message"] = f"Đã hủy {b.code}" + (f" – giữ phí hủy {charge:,.0f} đ" if charge else "") + (f" – bảo lưu {left:,.0f} đ ({out['retention']})" if out["retention"] else "") + (f" – đề nghị hoàn {left:,.0f} đ ({out['refund']})" if out["refund"] else "") + (" – SAU deadline hủy chỗ" if late else "")
    return out


def retention_out(r: Retention, db: Session | None = None) -> dict:
    ob = db.get(Booking, r.booking_id) if db else None
    return {"id": r.id, "code": r.code, "booking_id": r.booking_id, "booking_code": ob.code if ob else "", "tour_code": r.tour_code, "start_date": ob.tour.start_date if ob and ob.tour else None,
            "customer_name": r.customer_name, "customer_phone": r.customer_phone, "amount": r.amount, "remaining": r.remaining, "note": r.note, "status": r.status, "expires_on": r.expires_on,
            "refund_request_id": r.refund_request_id, "applied_booking_id": r.applied_booking_id, "created_by": r.created_by, "created_at": r.created_at, "resolved_by": r.resolved_by,
            "resolved_at": r.resolved_at, "resolve_note": r.resolve_note}


def apply_retention(db: Session, u: User, rt: Retention, nb: Booking, amount: float | None = None) -> Receipt:
    """Dùng tiền bảo lưu cho booking mới: lập phiếu thu phương thức 'bao_luu' (Kế toán xác nhận ngay), bút toán Nợ 131 booking cũ – Có 131 booking mới."""
    if u.role not in ("nv_dh", "tp_dh", "ketoan") and not toan_quyen(u): raise HTTPException(403, "Chỉ Điều hành / Kế toán tất toán bảo lưu")
    if rt.status != "hieu_luc": raise Gate("BAO_LUU", "Khoản bảo lưu không còn hiệu lực")
    if nb.cancelled: raise Gate("BAO_LUU", "Booking mới đã hủy")
    if nb.id == rt.booking_id: raise Gate("BAO_LUU", "Không dùng bảo lưu cho chính booking gốc")
    nb.paid = PAY.paid_amount(db, nb.id)
    due = max(0.0, net(nb) - (nb.paid or 0))
    amt = round(min((rt.remaining or 0), due if amount is None else float(amount)))
    if amt <= 0: raise Gate("BAO_LUU", "Số tiền dùng phải > 0 và không vượt số còn lại / số còn phải thu")
    if amt > (rt.remaining or 0) + 1: raise Gate("BAO_LUU", f"Vượt số bảo lưu còn lại {(rt.remaining or 0):,.0f} đ")
    if amt > due + 1: raise Gate("BAO_LUU", f"Vượt số còn phải thu của booking {due:,.0f} đ")
    rc = Receipt(code=PAY._next_receipt_code(db), booking_id=nb.id, amount=amt, method="bao_luu", payer=rt.customer_name, note=f"Dùng bảo lưu {rt.code} (booking gốc {rt.tour_code})",
                 status="ke_toan_xac_nhan", created_by=u.username, confirmed_by=u.username, confirmed_at=datetime.now(),
                 company_id=nb.company_id)
    db.add(rc); db.flush()
    nb.paid = PAY.paid_amount(db, nb.id); refresh_status(nb)
    try:
        ACC.post_entry(db, "robot", "robot", date.today(), f"Chuyển tiền bảo lưu {rt.code} sang booking {nb.code}",
                       [{"account": "131", "debit": amt, "partner": rt.customer_name, "booking_id": rt.booking_id, "note": "giảm ứng trước booking cũ"},
                        {"account": "131", "credit": amt, "partner": nb.customer_name, "booking_id": nb.id, "note": "ứng trước booking mới"}], "thu_tien", f"receipt:{rc.code}", nb.tour_id)
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"receipt:{rc.code}", after={"ly_do": str(ex)})
    rt.remaining = round((rt.remaining or 0) - amt); rt.applied_booking_id = nb.id
    if rt.remaining <= 0: rt.status, rt.resolved_by, rt.resolved_at, rt.resolve_note = "tat_toan", u.username, datetime.now(), f"Dùng hết cho {nb.code}"
    R.audit(db, u.username, u.role, "tat_toan_bao_luu", f"baoluu:{rt.code}", after={"booking_moi": nb.code, "so_tien": amt, "con_lai": rt.remaining})
    db.commit(); db.refresh(rc); return rc


def refund_retention(db: Session, u: User, rt: Retention, amount: float | None, note: str) -> PaymentRequest:
    """Đề xuất hoàn tiền cho khách (đi luồng đề nghị chi hoàn tiền: GĐ KD/TP ĐH xác nhận → Kế toán → TGĐ → chi)."""
    if u.role not in ("nv_dh", "tp_dh", "nv_kd", "tn_kd", "tp_kd", "gd_kd", "ketoan") and not toan_quyen(u): raise HTTPException(403, "Không có quyền đề xuất hoàn tiền")
    if rt.status != "hieu_luc": raise Gate("BAO_LUU", "Khoản bảo lưu không còn hiệu lực")
    if rt.refund_request_id:
        pr = db.get(PaymentRequest, rt.refund_request_id)
        if pr and pr.status not in ("tu_choi",): raise Gate("BAO_LUU", f"Đã có đề nghị hoàn {pr.code} ({pr.status})")
    amt = round((rt.remaining or 0) if amount is None else min(float(amount), (rt.remaining or 0)))
    if amt <= 0: raise Gate("BAO_LUU", "Số tiền hoàn phải > 0")
    ob = db.get(Booking, rt.booking_id)
    from app.services import ops as OPS
    pr = OPS.create_request(db, u, {"category": "hoan_tien", "tour_id": ob.tour_id if ob else None, "supplier_name": rt.customer_name, "supplier_tax_code": "", "amount": amt,
                                    "description": f"Hoàn tiền bảo lưu {rt.code} – {rt.customer_name} ({rt.customer_phone}): {(note or rt.note)[:120]}", "has_document": True, "document_ref": f"baoluu:{rt.code}", "has_invoice": False})
    rt.refund_request_id = pr.id
    R.audit(db, u.username, u.role, "de_xuat_hoan_bao_luu", f"baoluu:{rt.code}", after={"de_nghi_chi": pr.code, "so_tien": amt}); db.commit()
    return pr


def on_refund_paid(db: Session, pr: PaymentRequest) -> None:
    """Gọi khi đề nghị chi hoàn tiền đã chi: tất toán khoản bảo lưu tương ứng."""
    rt = db.execute(select(Retention).where(Retention.refund_request_id == pr.id)).scalars().first()
    if not rt or rt.status != "hieu_luc": return
    rt.remaining = round(max(0.0, (rt.remaining or 0) - (pr.amount or 0)))
    if rt.remaining <= 0: rt.status, rt.resolved_by, rt.resolved_at, rt.resolve_note = "tat_toan", "robot", datetime.now(), f"Đã hoàn tiền {pr.code}"


def cancel_retention(db: Session, u: User, rt: Retention, note: str) -> str:
    """Hủy bảo lưu (khách bỏ / hết hạn): số còn lại ghi thu nhập khác (Nợ 131 – Có 711)."""
    if u.role not in ("tp_dh", "gd_kd", "tp_kd", "tgd", "ketoan") and not toan_quyen(u): raise HTTPException(403, "Chỉ TP ĐH / GĐ KD / Kế toán / TGĐ hủy bảo lưu")
    if rt.status != "hieu_luc": raise Gate("BAO_LUU", "Khoản bảo lưu không còn hiệu lực")
    if not (note or "").strip(): raise Gate("BAO_LUU", "Hủy bảo lưu phải ghi lý do")
    amt = round((rt.remaining or 0))
    if amt > 0:
        try:
            ACC.post_entry(db, u.username, u.role, date.today(), f"Hủy bảo lưu {rt.code} – {rt.customer_name}: {note[:80]}",
                           [{"account": "131", "debit": amt, "partner": rt.customer_name, "booking_id": rt.booking_id}, {"account": "711", "credit": amt, "partner": rt.customer_name, "booking_id": rt.booking_id}],
                           "bao_luu", f"baoluu:{rt.code}")
        except ValueError as ex:
            R.audit(db, u.username, u.role, "ghi_so_that_bai", f"baoluu:{rt.code}", after={"ly_do": str(ex)})
    rt.status, rt.resolved_by, rt.resolved_at, rt.resolve_note, rt.remaining = "huy", u.username, datetime.now(), note[:300], 0
    R.audit(db, u.username, u.role, "huy_bao_luu", f"baoluu:{rt.code}", after={"so_tien": amt, "ly_do": note[:200]}); db.commit()
    return f"Đã hủy bảo lưu {rt.code}" + (f", ghi thu nhập khác {amt:,.0f} đ" if amt > 0 else "")


def retention_summary(db: Session) -> dict:
    rows = db.execute(select(Retention.status, func.count(), func.coalesce(func.sum(Retention.remaining), 0), func.coalesce(func.sum(Retention.amount), 0)).group_by(Retention.status)).all()
    d = {s: {"n": n, "remaining": float(r), "amount": float(a)} for s, n, r, a in rows}
    refunded = sum((pr.amount or 0) for pr in db.execute(select(PaymentRequest).where(PaymentRequest.category == "hoan_tien", PaymentRequest.status == "da_chi", PaymentRequest.document_ref.like("baoluu:%"))).scalars())
    return {"hieu_luc": d.get("hieu_luc", {"n": 0, "remaining": 0, "amount": 0}), "tat_toan": d.get("tat_toan", {"n": 0, "remaining": 0, "amount": 0}), "huy": d.get("huy", {"n": 0, "remaining": 0, "amount": 0}), "refunded": refunded}


# ---------- robot R4: cọc – deadline – bảo lưu ----------
def robot_check(db: Session) -> dict:
    now = datetime.now(); today = date.today(); made = 0

    def add(kind, level, ref, msg, roles):
        nonlocal made
        if not db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref, Alert.resolved == False)).scalars().first():
            db.add(Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles)); made += 1

    locked = auto_lock(db)
    from app.services import giu_cho as GC
    gc = GC.het_han_giu_cho(db)
    han_coc = int(R.get_param(db, "han_coc_gio"))
    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.cancelled == False, Tour.start_date >= today - timedelta(days=1), Tour.status.in_(["da_duyet", "cho_duyet", "cho_xac_nhan"]))
    for b in db.execute(q).scalars():
        st = pmt_status_of(b); ref = f"booking:{b.code}"
        if st == "UNPAID" and (now - b.created_at).total_seconds() / 3600 > han_coc and net(b) > 0:
            add("chua_coc", "warn", ref, f"{b.code} ({b.customer_name}, {b.tour.code}) chưa đặt cọc {deposit_due(b):,.0f} đ sau {han_coc} giờ – sale nhắc khách hoặc Điều hành hủy chỗ", "nv_kd,gd_kd,nv_dh,tp_dh")
        if st != "PAID" and b.cancel_deadline and now > b.cancel_deadline and net(b) > 0:
            add("qua_deadline_thu", "red", ref, f"{b.code} ({b.customer_name}, {b.tour.code}) quá deadline hủy chỗ {b.cancel_deadline:%d/%m %H:%M} còn thiếu {net(b) - (b.paid or 0):,.0f} đ – thu đủ hoặc hủy/bảo lưu", "nv_kd,gd_kd,tp_dh,ketoan")
        elif st != "PAID" and b.cancel_deadline and 0 <= (b.cancel_deadline - now).total_seconds() <= 48 * 3600 and net(b) > 0:
            add("sap_deadline_thu", "warn", ref, f"{b.code} ({b.customer_name}, {b.tour.code}) còn thiếu {net(b) - (b.paid or 0):,.0f} đ, deadline {b.cancel_deadline:%d/%m %H:%M}", "nv_kd,tp_dh")
    for rt in db.execute(select(Retention).where(Retention.status == "hieu_luc", Retention.expires_on != None)).scalars():
        left = (rt.expires_on - today).days
        if left < 0: add("bao_luu_het_han", "red", f"baoluu:{rt.code}", f"Bảo lưu {rt.code} ({rt.customer_name}, {(rt.remaining or 0):,.0f} đ) đã hết hạn {rt.expires_on:%d/%m} – hoàn tiền hoặc hủy bảo lưu", "tp_dh,gd_kd,ketoan")
        elif left <= 7: add("bao_luu_sap_het_han", "warn", f"baoluu:{rt.code}", f"Bảo lưu {rt.code} ({rt.customer_name}, {(rt.remaining or 0):,.0f} đ) hết hạn {rt.expires_on:%d/%m} – liên hệ khách chọn tour", "nv_kd,tp_dh")
    db.commit()
    return {"locked": locked, "new_alerts": made,
            "giu_cho_dat_han": gc["dat_han"], "giu_cho_het_han": gc["het_han"]}
