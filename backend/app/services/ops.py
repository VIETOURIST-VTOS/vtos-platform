"""Vận hành: báo cáo ngày (Điều 12), ca trực page (cổng 11), đề nghị chi – lệnh chi NCC (robot R3, cổng 14/15).

R3 chỉ tính toán, gắn cảnh báo và xếp cấp duyệt; quyết định duyệt là người. Không robot nào chuyển tiền.
"""
from datetime import date, datetime, timedelta, time
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User, Alert
from app.models.hr import Employee
from app.models.ops import DailyReport, PageShift, PaymentRequest
from app.models.payments import Receipt
from app.services import rules as R
from app.services import accounting as ACC

REPORT_DEADLINE = time(20, 0)
NO_TIMESHEET_DEPTS = ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt")   # khối bỏ chấm công → báo cáo ngày bắt buộc
CATEGORY_ACCOUNT = {"chi_tour": "154", "marketing": "641", "hanh_chinh": "642"}   # tam_ung: ghi 141 khi chi, hoàn ứng vào 154 khi Kế toán xác nhận quyết toán
CATEGORY_CONFIRMER = {"chi_tour": ("tp_dh",), "marketing": ("ptgd_mkt",), "hanh_chinh": ("hcns",), "hoan_tien": ("gd_kd", "tp_dh"), "tam_ung": ("tp_dh",)}


# ====================== BÁO CÁO NGÀY ======================
def robot_score(r: DailyReport) -> tuple[float, str]:
    """Điểm nháp 0–10: mỗi phần có nội dung ≥ 20 ký tự = 2 điểm (8), nộp trước 20h = 2 điểm."""
    parts = [r.part1_done, r.part2_numbers, r.part3_issues, r.part4_plan]
    filled = sum(1 for p in parts if len((p or "").strip()) >= 20)
    score = filled * 2 + (2 if r.on_time else 0)
    notes = []
    if filled < 4: notes.append(f"thiếu/quá ngắn {4 - filled} phần")
    if not r.on_time: notes.append("nộp sau 20:00")
    return float(score), "; ".join(notes) or "Đủ 4 phần, đúng giờ"


def submit_report(db: Session, u: User, d: date, p1: str, p2: str, p3: str, p4: str) -> DailyReport:
    if d > date.today():
        raise ValueError("Không nộp báo cáo cho ngày tương lai")
    r = db.execute(select(DailyReport).where(DailyReport.user_id == u.id, DailyReport.report_date == d)).scalars().first()
    if r and r.reviewed_by:
        raise ValueError("Báo cáo đã được trưởng phòng chấm – không sửa")
    now = datetime.now()
    if r is None:
        r = DailyReport(user_id=u.id, report_date=d); db.add(r)
    r.part1_done, r.part2_numbers, r.part3_issues, r.part4_plan = p1, p2, p3, p4
    r.submitted_at = now
    r.on_time = d == now.date() and now.time() <= REPORT_DEADLINE   # nộp bù ngày trước = trễ
    r.robot_score, r.robot_note = robot_score(r)
    db.flush()
    R.audit(db, u.username, u.role, "nop_bao_cao_ngay", f"report:{u.username}:{d}", after={"diem_robot": r.robot_score, "dung_gio": r.on_time})
    db.commit(); db.refresh(r)
    return r


def review_report(db: Session, u: User, r: DailyReport, score: float, note: str) -> DailyReport:
    if not 0 <= score <= 10: raise ValueError("Điểm 0–10")
    r.manager_score, r.manager_note, r.reviewed_by, r.reviewed_at = score, note, u.username, datetime.now()
    R.audit(db, u.username, u.role, "tp_cham_bao_cao_ngay", f"report:{r.user_id}:{r.report_date}", after={"diem": score, "ghi_chu": note})
    db.commit()
    return r


def monthly_grade(reports: list[DailyReport], work_days: int) -> tuple[str, float]:
    """Xếp loại A/B/C/D: điểm bình quân (điểm TP nếu có, không thì điểm robot) × tỷ lệ ngày nộp."""
    if not work_days: return "-", 0.0
    pts = [(r.manager_score if r.manager_score is not None else r.robot_score) for r in reports]
    avg = (sum(pts) / work_days) if pts else 0.0
    grade = "A" if avg >= 8.5 else "B" if avg >= 7 else "C" if avg >= 5 else "D"
    return grade, round(avg, 2)


def work_days_in(y: int, m: int, until: date | None = None) -> list[date]:
    """Thứ Hai – Thứ Bảy (Chủ nhật nghỉ)."""
    d = date(y, m, 1); out = []
    while d.month == m and (until is None or d <= until):
        if d.weekday() != 6: out.append(d)
        d += timedelta(days=1)
    return out


def check_missing_reports(db: Session) -> int:
    """Robot: thiếu 1 ngày → nhắc nhở; 2 ngày liên tiếp → chuyển HCNS (cảnh báo đỏ). Chạy sau 20h hoặc sáng hôm sau."""
    today = date.today()
    now = datetime.now()
    last = today if now.time() > REPORT_DEADLINE else today - timedelta(days=1)
    days = [d for d in (last - timedelta(days=1), last) if d.weekday() != 6]
    created = 0
    emps = db.execute(select(Employee).where(Employee.active == True, Employee.department.in_(NO_TIMESHEET_DEPTS), Employee.user_id != None)).scalars().all()
    for e in emps:
        missing = [d for d in days if not db.execute(select(DailyReport).where(DailyReport.user_id == e.user_id, DailyReport.report_date == d)).scalars().first()]
        if not missing: continue
        kind, level, roles, msg = ("bc_ngay_2", "red", "hcns,tgd", f"{e.full_name} thiếu báo cáo ngày 2 ngày liên tiếp ({', '.join(f'{d:%d/%m}' for d in missing)}) – chuyển HCNS") \
            if len(missing) >= 2 else ("bc_ngay_1", "warn", "tp_dh,gd_kd,ptgd_doan,ptgd_mkt,hcns", f"{e.full_name} chưa nộp báo cáo ngày {missing[0]:%d/%m} – nhắc nhở")
        ref = f"{e.code}:{last}"
        if not db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref)).scalars().first():
            db.add(Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles)); created += 1
    db.commit()
    return created


# ====================== CA TRỰC PAGE (cổng 11) ======================
def shift_penalty(missed: int) -> tuple[float, bool]:
    """1–3 lượt: −100.000/lượt; 4–5: −200.000/lượt; ≥ 6: loại khỏi ca tháng sau (và −200.000/lượt). Chỉ trừ hoa hồng."""
    if missed <= 0: return 0.0, False
    if missed <= 3: return missed * 100_000, False
    if missed <= 5: return missed * 200_000, False
    return missed * 200_000, True


def shift_penalties_for_month(db: Session, y: int, m: int) -> dict[int, tuple[float, int, bool]]:
    """{employee_id: (tiền phạt, tổng lượt sót, bị loại ca)} theo tháng."""
    out: dict[int, tuple[float, int, bool]] = {}
    for s in db.execute(select(PageShift)).scalars():
        if s.shift_date.year == y and s.shift_date.month == m and s.missed:
            pen, out_flag = shift_penalty(s.missed)
            p, n, f = out.get(s.employee_id, (0.0, 0, False))
            out[s.employee_id] = (p + pen, n + s.missed, f or out_flag)
    return out


# ====================== ĐỀ NGHỊ CHI – LỆNH CHI (R3) ======================
def tour_budget(db: Session, t: Tour) -> float:
    pax = max(t.planned_pax, R.booked_pax(t))
    return t.fixed_cost + t.var_cost_per_pax * pax


def tour_cashflow(db: Session, t: Tour) -> dict:
    """Bảng dòng tiền tour: đã thu, đã chi, còn phải chi, tiền còn lại, lợi nhuận dự kiến; cảnh báo đỏ khi chi vượt thu."""
    revenue = sum(b.amount - b.discount for b in t.bookings)
    collected = sum(r.amount for r in db.execute(select(Receipt).join(Booking).where(Booking.tour_id == t.id, Receipt.status != "huy")).scalars())
    reqs = db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status != "tu_choi")).scalars().all()
    paid = sum(r.amount for r in reqs if r.status == "da_chi")
    committed = sum(r.amount for r in reqs if r.status in ("cho_chi",))
    pending = sum(r.amount for r in reqs if r.status in ("cho_tp", "cho_kt", "cho_duyet"))
    budget = tour_budget(db, t)
    total_cost = paid + committed + pending
    return {"tour_id": t.id, "code": t.code, "name": t.name, "status": t.status, "revenue": revenue, "collected": collected, "paid": paid, "committed": committed,
            "pending": pending, "cash_left": collected - paid - committed, "budget": budget, "over_budget": total_cost > budget + 1,
            "expected_profit": revenue - total_cost, "red": paid + committed > collected, "requests": len(reqs)}


def _next_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(PaymentRequest)).scalar() + 1
    return f"DC{date.today():%y%m}-{n:04d}"


def create_request(db: Session, u: User, data: dict) -> PaymentRequest:
    cat = data["category"]
    if cat not in CATEGORY_CONFIRMER: raise ValueError("Loại chi không hợp lệ")
    t = db.get(Tour, data.get("tour_id")) if data.get("tour_id") else None
    if cat in ("chi_tour", "hoan_tien", "tam_ung") and not t:
        raise ValueError("Chi phí tour / hoàn tiền / tạm ứng bắt buộc gắn mã tour (cổng 14)")
    if cat == "tam_ung" and t and t.status in ("da_dong_so", "kt_xac_nhan", "khoa"):
        raise ValueError("Tour đã đóng số quyết toán – không tạm ứng thêm")
    if data["amount"] <= 0: raise ValueError("Số tiền phải > 0")
    if not data.get("supplier_name"): raise ValueError("Thiếu nhà cung cấp / người thụ hưởng")
    r = PaymentRequest(code=_next_code(db), category=cat, tour_id=t.id if t else None, supplier_name=data["supplier_name"], supplier_tax_code=data.get("supplier_tax_code", ""),
                       supplier_bank=data.get("supplier_bank", ""), amount=float(data["amount"]), description=data["description"], has_document=bool(data.get("has_document")),
                       document_ref=data.get("document_ref", ""), has_invoice=bool(data.get("has_invoice")), created_by=u.username)
    # R3: xếp cấp duyệt
    if cat == "marketing" and r.amount >= R.get_param(db, "han_muc_mkt"):
        r.two_signatures = True
    if t and cat in ("chi_tour", "tam_ung"):
        cf = tour_cashflow(db, t)
        if cf["paid"] + cf["committed"] + cf["pending"] + r.amount > cf["budget"] + 1:
            r.over_budget, r.two_signatures = True, True
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "lap_de_nghi_chi", f"dc:{r.code}", after={"loai": cat, "tour": t.code if t else "", "ncc": r.supplier_name, "so_tien": r.amount,
                                                                              "ngoai_du_toan": r.over_budget, "hai_chu_ky": r.two_signatures})
    db.commit(); db.refresh(r)
    return r


def step(db: Session, u: User, r: PaymentRequest, action: str, reason: str = "") -> str:
    """confirm (người phụ trách bộ phận) → check (Kế toán) → approve (TGĐ; +Chủ tịch nếu 2 chữ ký) → pay (Kế toán) | reject."""
    if action == "reject":
        if r.status in ("da_chi", "tu_choi"): raise ValueError("Không từ chối được")
        if not reason.strip(): raise ValueError("Từ chối phải có lý do")
        r.status, r.reject_reason = "tu_choi", reason
        msg = f"Đã từ chối {r.code}: {reason}"
    elif action == "confirm":
        if r.status != "cho_tp": raise ValueError("Không ở bước xác nhận bộ phận")
        if u.role not in CATEGORY_CONFIRMER[r.category] and u.role not in ("tgd",): raise ValueError("Không đúng người phụ trách bộ phận")
        r.status, r.tp_by = "cho_kt", u.username
        msg = f"{r.code}: bộ phận đã xác nhận, chuyển Kế toán kiểm tra"
    elif action == "check":
        if r.status != "cho_kt": raise ValueError("Không ở bước Kế toán kiểm tra")
        if u.role != "ketoan": raise ValueError("Chỉ Kế toán kiểm tra")
        if not r.has_document: raise ValueError("Thiếu chứng từ đính kèm (hợp đồng/hóa đơn/báo giá) – không chuyển duyệt")
        if r.category not in ("hoan_tien", "tam_ung") and not r.supplier_tax_code: raise ValueError("NCC chưa có MST – phải xác nhận trước khi thanh toán")
        r.status, r.kt_by = "cho_duyet", u.username
        msg = f"{r.code}: Kế toán đã kiểm tra, trình {'Chủ tịch + TGĐ' if r.two_signatures else 'TGĐ'} duyệt"
    elif action == "approve":
        if r.status != "cho_duyet": raise ValueError("Không ở bước duyệt")
        if u.role == "tgd": r.signed_tgd = True
        elif u.role == "chutich" and r.two_signatures: r.signed_chutich = True
        else: raise ValueError("Chỉ TGĐ (và Chủ tịch khi cần 2 chữ ký) duyệt chi")
        done = r.signed_tgd and (r.signed_chutich or not r.two_signatures)
        if done:
            r.status, r.approved_by, r.approved_at = "cho_chi", u.username, datetime.now()
            _post_liability(db, r)
            msg = f"{r.code} đã duyệt – lập lệnh chi chờ Kế toán thực hiện trên ngân hàng"
        else:
            msg = f"{r.code}: đã ký {'TGĐ' if r.signed_tgd else 'Chủ tịch'}, chờ chữ ký còn lại"
    elif action == "pay":
        if r.status != "cho_chi": raise ValueError("Chưa có lệnh chi được duyệt")
        if u.role != "ketoan": raise ValueError("Chỉ Kế toán ghi nhận đã chi")
        r.status, r.paid_at, r.paid_ref = "da_chi", datetime.now(), reason
        r.paid_method = "tien_mat" if reason.lower().startswith("tm") else "chuyen_khoan"
        _post_payment(db, r)
        if r.category == "hoan_tien":
            from app.services import bookings as BK
            BK.on_refund_paid(db, r)
        msg = f"{r.code} đã chi ({r.paid_ref or 'không có mã GD'})"
    else:
        raise ValueError("Hành động không hợp lệ")
    R.audit(db, u.username, u.role, f"de_nghi_chi_{action}", f"dc:{r.code}", after={"trang_thai": r.status, "ly_do": reason})
    db.commit()
    return msg


def _post_liability(db: Session, r: PaymentRequest):
    """Duyệt đề nghị chi có hóa đơn/hợp đồng NCC → ghi nhận công nợ: Nợ 154/641/642 – Có 331 (hoàn tiền khách: không ghi tại bước này)."""
    acc = CATEGORY_ACCOUNT.get(r.category)
    if not acc: return
    t = db.get(Tour, r.tour_id) if r.tour_id else None
    try:
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Đề nghị chi {r.code} – {r.supplier_name}: {r.description[:80]}",
                           [{"account": acc, "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id, "note": "" if r.has_invoice else "Không hóa đơn – không được trừ TNDN"},
                            {"account": "331", "credit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}], "de_nghi_chi", f"dc:{r.code}", r.tour_id)
        r.entry_ids = list(r.entry_ids or []) + [e.id]
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def _post_payment(db: Session, r: PaymentRequest):
    cash = "111" if r.paid_method == "tien_mat" else "112"
    if r.category == "hoan_tien":
        lines = [{"account": "131", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    elif r.category == "tam_ung":   # tạm ứng HDV/NCC trước tour: Nợ 141 – Có 111/112; hoàn ứng khi Kế toán xác nhận quyết toán
        lines = [{"account": "141", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    else:
        lines = [{"account": "331", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    try:
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Chi {r.code} – {r.supplier_name}" + (f" (GD {r.paid_ref})" if r.paid_ref else ""), lines, "lenh_chi", f"dc:{r.code}", r.tour_id)
        r.entry_ids = list(r.entry_ids or []) + [e.id]
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def posted_tour_cost(db: Session, tour_id: int) -> float:
    """Chi phí tour đã ghi 154 qua đề nghị chi đã duyệt (để quyết toán chỉ ghi phần chênh lệch vào 335)."""
    return sum(r.amount for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == tour_id, PaymentRequest.category.in_(["chi_tour", "tam_ung"]),
                                                                          PaymentRequest.status.in_(["cho_chi", "da_chi"]))).scalars())


def match_outgoing(db: Session, content: str, amount: float) -> PaymentRequest | None:
    """R1/R2: giao dịch tiền ra có mã DCyymm-nnnn và đúng số tiền → tự ghi 'đã chi' cho lệnh chi đang chờ."""
    import re
    m = re.search(r"DC\s?(\d{4})-?(\d{4})", content.replace(" ", ""), re.IGNORECASE)
    if not m: return None
    code = f"DC{m.group(1)}-{m.group(2)}"
    r = db.execute(select(PaymentRequest).where(PaymentRequest.code == code, PaymentRequest.status == "cho_chi")).scalars().first()
    if r and abs(r.amount - amount) < 1:
        return r
    return None
