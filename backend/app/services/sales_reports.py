"""Báo cáo bán hàng (theo danh mục báo cáo Vietrip: bán tour lẻ, nhắc thu tiền khách, hủy chỗ của sale, kinh doanh) + xuất Excel,
và robot R9 giám sát bất thường (số liệu lệch, hành vi rủi ro) cho Chủ tịch/TGĐ/BKS.

Từ 07/9/2026 mỗi báo cáo nhận thêm tham số `mang` (le / doan) để hai phòng Kinh doanh xem đúng doanh số của
mình. Không truyền `mang` thì báo cáo giữ nguyên phạm vi toàn hệ thống như trước – Ban Giám đốc, Kế toán và
BKS vẫn có một con số hợp nhất để đối chiếu, chứ không phải cộng tay hai bản.

Điều kiện lọc lấy từ app.services.segments – CÙNG một chỗ với bộ lọc trên màn hình danh sách. Nếu báo cáo tự
định nghĩa lại "thế nào là tour đoàn" thì sẽ có ngày màn hình đếm 12 tour còn báo cáo đếm 11, và không ai
biết bên nào đúng."""
from datetime import datetime, date, timedelta
from io import BytesIO
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User, Alert, AuditLog
from app.models.payments import Receipt, Retention, BankTransaction
from app.models.ops import PaymentRequest
from app.models.hr import Employee
from app.services import rules as R
from app.services import bookings as BK
from app.services import segments as SEG

REPORTS = {
    "ban_tour_le": {"name": "Báo cáo bán tour lẻ", "kind": "Ngày", "params": ["from", "to"], "desc": "Booking tạo trong kỳ theo từng sale: số booking, khách, doanh thu, đã thu, còn phải thu, hủy, đủ 4 trường"},
    "nhac_thu": {"name": "Báo cáo nhắc thu tiền khách", "kind": "Tất cả", "params": [], "desc": "Booking còn phải thu của tour sắp khởi hành: hạn thu, quá hạn, sale phụ trách"},
    "huy_cho": {"name": "Báo cáo hủy chỗ của sale", "kind": "Ngày", "params": ["from", "to"], "desc": "Booking hủy trong kỳ theo sale: lý do, phí hủy, bảo lưu / hoàn tiền, hủy sau deadline"},
    "kinh_doanh": {"name": "Báo cáo kinh doanh", "kind": "Tháng", "params": ["month"], "desc": "Doanh thu tính chỉ tiêu theo sale so mốc văn phòng → bậc thang f, hoa hồng ước (tháng tạo booking)"},
    "tour_le": {"name": "Báo cáo tour lẻ", "kind": "Ngày", "params": ["from", "to"], "desc": "Tour lẻ khởi hành trong kỳ: chỗ mở/bán, doanh thu, đã thu, chi phí quyết toán, lợi nhuận, trạng thái"},
}


MANG_LABEL = SEG.MANG                                   # {"le": "Kinh doanh Lẻ", "doan": "Kinh doanh Đoàn"}


def _sales_name(b: Booking) -> str: return b.sales.full_name if b.sales else ""


def _office_of(db: Session) -> dict[int, str]:
    return {e.user_id: e.office for e in db.execute(select(Employee).where(Employee.user_id != None)).scalars()}


# GỠ CỘT "QUÁ SLA 2H" KHỎI BẢNG NÀY — Chủ tịch quyết 25/9/2026.
#
# Đồng hồ SLA chạy từ lúc KINH DOANH gửi yêu cầu tới lúc ĐIỀU HÀNH bấm tạo booking
# (`tours.create_booking`), và cảnh báo quá hạn bắn về `tp_dh, nv_dh`. Tức là nó đo Điều hành.
# Nhưng cột ấy lại nằm ở đây, trên bảng điểm gom THEO TÊN SALE.
#
# Một nhân viên Kinh doanh vì thế mang trên bảng điểm của mình một con số họ không làm gì để đổi
# được. Một thước đo như vậy không đo ai cả — nó chỉ dạy người bị đo rằng bảng điểm không đáng
# tin, và bài học ấy lan sang mọi cột khác trên cùng bảng.
#
# `booking.sla_ok` VẪN ĐƯỢC GHI như cũ, không mất dữ liệu; nó chuyển sang bảng điểm Điều hành ở
# `bao_cao_phong._dieu_hanh` (dòng "Booking quá hạn 2 giờ"). Cột "Đủ 4 trường" thì Ở LẠI: bốn
# trường ấy do chính sale điền lúc gửi yêu cầu.
def ban_tour_le(db: Session, d1: date, d2: date, mang: str = "") -> dict:
    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.created_at >= datetime.combine(d1, datetime.min.time()), Booking.created_at < datetime.combine(d2 + timedelta(days=1), datetime.min.time()), Tour.tour_type != "non_package")
    cond = SEG.tour_cond(mang)
    if cond is not None: q = q.where(cond)
    rows = list(db.execute(q.order_by(Booking.created_at)).scalars())
    by: dict[str, dict] = {}
    for b in rows:
        s = by.setdefault(_sales_name(b) or "(không có sale)", {"sale": _sales_name(b) or "(không có sale)", "bookings": 0, "pax": 0, "revenue": 0.0, "paid": 0.0, "due": 0.0, "cancelled": 0, "du_4_truong": 0})
        if b.cancelled: s["cancelled"] += 1; continue
        s["bookings"] += 1; s["pax"] += b.pax; s["revenue"] += (b.amount or 0) - (b.discount or 0); s["paid"] += (b.paid or 0); s["due"] += max(0.0, (b.amount or 0) - (b.discount or 0) - (b.paid or 0))
        s["du_4_truong"] += 1 if b.counts_for_target else 0
    summary = sorted(by.values(), key=lambda x: -(x["revenue"] or 0))
    detail = [{"created_at": b.created_at, "code": b.code, "tour_code": b.tour.code, "start_date": b.tour.start_date, "customer": b.customer_name, "phone": b.customer_phone, "source": b.source, "pax": b.pax,
               "revenue": (b.amount or 0) - (b.discount or 0), "paid": (b.paid or 0), "due": max(0.0, (b.amount or 0) - (b.discount or 0) - (b.paid or 0)), "status": BK.pmt_status_of(b), "sale": _sales_name(b), "counts": b.counts_for_target, "sla_ok": b.sla_ok, "cancelled": b.cancelled} for b in rows]
    tot = {"bookings": sum(s["bookings"] for s in summary), "pax": sum(s["pax"] for s in summary), "revenue": sum((s["revenue"] or 0) for s in summary), "paid": sum((s["paid"] or 0) for s in summary), "due": sum(s["due"] for s in summary), "cancelled": sum(s["cancelled"] for s in summary)}
    return {"report": "ban_tour_le", "from": d1, "to": d2, "mang": SEG.valid(mang), "summary": summary, "total": tot, "detail": detail,
            "columns": {"summary": [("sale", "Sale"), ("bookings", "Booking"), ("pax", "Khách"), ("revenue", "Doanh thu"), ("paid", "Đã thu"), ("due", "Còn phải thu"), ("cancelled", "Hủy"), ("du_4_truong", "Đủ 4 trường")],
                        "detail": [("created_at", "Ngày tạo"), ("code", "Booking"), ("tour_code", "Tour"), ("start_date", "Khởi hành"), ("customer", "Khách"), ("phone", "SĐT"), ("source", "Nguồn"), ("pax", "Khách"), ("revenue", "Doanh thu"), ("paid", "Đã thu"), ("due", "Còn lại"), ("status", "TT"), ("sale", "Sale")]}}


def nhac_thu(db: Session, mang: str = "") -> dict:
    today = date.today(); now = datetime.now()
    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.cancelled == False, Tour.start_date >= today - timedelta(days=1), Tour.status.in_(["da_duyet", "cho_duyet", "cho_xac_nhan", "ket_thuc"]))
    cond = SEG.tour_cond(mang)
    if cond is not None: q = q.where(cond)
    rows = []
    for b in db.execute(q).scalars():
        due = (b.amount or 0) - (b.discount or 0) - (b.paid or 0)
        if due <= 1000: continue
        dl = b.cancel_deadline
        rows.append({"code": b.code, "tour_code": b.tour.code, "start_date": b.tour.start_date, "days_left": (b.tour.start_date - today).days, "customer": b.customer_name, "phone": b.customer_phone, "revenue": (b.amount or 0) - (b.discount or 0),
                     "deposit_due": BK.deposit_due(b), "paid": (b.paid or 0), "due": due, "status": BK.pmt_status_of(b), "deadline": dl, "overdue": bool(dl and now > dl), "sale": _sales_name(b), "locked": b.locked})
    rows.sort(key=lambda r: (r["deadline"] or datetime.max, r["start_date"]))
    by: dict[str, dict] = {}
    for r in rows:
        s = by.setdefault(r["sale"] or "(không có sale)", {"sale": r["sale"] or "(không có sale)", "bookings": 0, "due": 0.0, "overdue": 0, "unpaid": 0})
        s["bookings"] += 1; s["due"] += r["due"]; s["overdue"] += 1 if r["overdue"] else 0; s["unpaid"] += 1 if r["status"] == "UNPAID" else 0
    return {"report": "nhac_thu", "as_of": now, "mang": SEG.valid(mang), "summary": sorted(by.values(), key=lambda x: -x["due"]), "total": {"bookings": len(rows), "due": sum(r["due"] for r in rows), "overdue": sum(1 for r in rows if r["overdue"])}, "detail": rows,
            "columns": {"summary": [("sale", "Sale"), ("bookings", "Booking còn nợ"), ("due", "Còn phải thu"), ("overdue", "Quá deadline"), ("unpaid", "Chưa cọc")],
                        "detail": [("deadline", "Deadline"), ("code", "Booking"), ("tour_code", "Tour"), ("start_date", "Khởi hành"), ("days_left", "Còn (ngày)"), ("customer", "Khách"), ("phone", "SĐT"), ("revenue", "Tiền tour"), ("deposit_due", "Cọc"), ("paid", "Đã thu"), ("due", "Còn lại"), ("status", "TT"), ("sale", "Sale")]}}


def huy_cho(db: Session, d1: date, d2: date, mang: str = "") -> dict:
    q = select(Booking).where(Booking.cancelled == True, Booking.cancelled_at >= datetime.combine(d1, datetime.min.time()), Booking.cancelled_at < datetime.combine(d2 + timedelta(days=1), datetime.min.time()))
    cond = SEG.tour_cond(mang)
    # Chỉ nối bảng tours khi thật sự lọc theo mảng: nối vô điều kiện sẽ đánh rơi booking không gắn tour
    # khỏi báo cáo hủy toàn hệ thống – mà đó lại đúng là loại booking cần soi khi rà hủy chỗ.
    if cond is not None: q = q.join(Tour, Tour.id == Booking.tour_id).where(cond)
    rows = list(db.execute(q.order_by(Booking.cancelled_at)).scalars())
    rts = {r.booking_id: r for r in db.execute(select(Retention).where(Retention.booking_id.in_([b.id for b in rows] or [0]))).scalars()}
    detail, by = [], {}
    for b in rows:
        rt = rts.get(b.id); late = bool(b.cancel_deadline and b.cancelled_at and b.cancelled_at > b.cancel_deadline)
        detail.append({"cancelled_at": b.cancelled_at, "code": b.code, "tour_code": b.tour.code if b.tour else "", "start_date": b.tour.start_date if b.tour else None, "customer": b.customer_name, "phone": b.customer_phone, "paid": b.paid, "charge": b.cancel_charge,
                       "retention": rt.code if rt else "", "retention_amt": (rt.amount or 0) if rt else 0.0, "refund": max(0.0, (b.paid or 0) - (b.cancel_charge or 0)) if not rt else 0.0, "reason": b.cancel_reason, "late": late, "sale": _sales_name(b)})
        s = by.setdefault(_sales_name(b) or "(không có sale)", {"sale": _sales_name(b) or "(không có sale)", "cancelled": 0, "paid": 0.0, "charge": 0.0, "retained": 0.0, "late": 0})
        s["cancelled"] += 1; s["paid"] += (b.paid or 0); s["charge"] += (b.cancel_charge or 0); s["retained"] += (rt.amount or 0) if rt else 0; s["late"] += 1 if late else 0
    return {"report": "huy_cho", "from": d1, "to": d2, "mang": SEG.valid(mang), "summary": sorted(by.values(), key=lambda x: -x["cancelled"]), "total": {"cancelled": len(rows), "charge": sum((b.cancel_charge or 0) for b in rows), "retained": sum((r.amount or 0) for r in rts.values())}, "detail": detail,
            "columns": {"summary": [("sale", "Sale"), ("cancelled", "Số hủy"), ("paid", "Đã thu trước hủy"), ("charge", "Phí hủy giữ lại"), ("retained", "Bảo lưu"), ("late", "Hủy sau deadline")],
                        "detail": [("cancelled_at", "Ngày hủy"), ("code", "Booking"), ("tour_code", "Tour"), ("start_date", "Khởi hành"), ("customer", "Khách"), ("phone", "SĐT"), ("paid", "Đã thu"), ("charge", "Phí hủy"), ("retention", "Bảo lưu"), ("retention_amt", "Tiền BL"), ("refund", "Hoàn"), ("reason", "Lý do"), ("late", "Sau deadline"), ("sale", "Sale")]}}


def kinh_doanh(db: Session, month: str, mang: str = "") -> dict:
    from app.services import hr as HR
    y, m = map(int, month.split("-")); d1 = date(y, m, 1); d2 = date(y + (m == 12), m % 12 + 1, 1)
    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.created_at >= datetime.combine(d1, datetime.min.time()), Booking.created_at < datetime.combine(d2, datetime.min.time()), Booking.cancelled == False, Tour.tour_type != "non_package")
    cond = SEG.tour_cond(mang)
    if cond is not None: q = q.where(cond)
    emps = {e.user_id: e for e in db.execute(select(Employee).where(Employee.user_id != None)).scalars()}
    moc_hcm = R.get_param(db, "moc_chi_tieu_hcm"); moc_ct = R.get_param(db, "moc_chi_tieu_cantho"); table = HR.parse_f_table(R.get_param_text(db, "thang_f_bang"))
    by: dict[int, dict] = {}
    for b in db.execute(q).scalars():
        e = emps.get(b.sales_id)
        s = by.setdefault(b.sales_id, {"sale": _sales_name(b), "office": e.office if e else "", "department": e.department if e else "", "bookings": 0, "pax": 0, "revenue": 0.0, "revenue_target": 0.0, "paid": 0.0, "moc": HR.moc_of(e, moc_hcm, moc_ct) if e else moc_hcm})
        s["bookings"] += 1; s["pax"] += b.pax; s["revenue"] += (b.amount or 0) - (b.discount or 0); s["paid"] += (b.paid or 0)
        if b.counts_for_target and (not R.is_doan(b.tour)): s["revenue_target"] += (b.amount or 0) - (b.discount or 0)
    out = []
    for s in by.values():
        lvl, rate = HR.f_rate(s["revenue_target"], s["moc"], table)
        s["pct_moc"] = s["revenue_target"] / s["moc"] if s["moc"] else 0; s["f"] = f"f{lvl}"; s["rate"] = rate; s["commission_est"] = round(rate * max(0.0, s["revenue_target"] - s["moc"]))
        out.append(s)
    out.sort(key=lambda x: -x["revenue_target"])
    # Cột "DT tính chỉ tiêu" và hoa hồng bậc thang là cơ chế của mảng LẺ. Tour đoàn ăn theo chia lợi nhuận
    # quyết toán (app/services/hr.py), nên khi xem mảng Đoàn hai cột này bằng 0 – phải nói ra, nếu không
    # phòng Đoàn nhìn bảng trắng lại tưởng phần mềm quên tính hoa hồng cho họ.
    note = "Hoa hồng ước theo tháng tạo booking; hoa hồng chính thức tính theo tháng quyết toán (số Kế toán xác nhận) ở bảng lương."
    if SEG.valid(mang) == "doan":
        note = ("Mảng Đoàn không hưởng hoa hồng theo bậc thang doanh thu mà theo chia lợi nhuận quyết toán, "
                "nên hai cột \"DT tính chỉ tiêu\" và \"Hoa hồng ước\" ở đây bằng 0 – xem số chính thức ở bảng lương.")
    return {"report": "kinh_doanh", "month": month, "mang": SEG.valid(mang), "summary": out, "total": {"bookings": sum(s["bookings"] for s in out), "revenue": sum((s["revenue"] or 0) for s in out), "revenue_target": sum(s["revenue_target"] for s in out), "commission_est": sum(s["commission_est"] for s in out)}, "detail": [],
            "note": note,
            "columns": {"summary": [("sale", "Sale"), ("office", "VP"), ("bookings", "Booking"), ("pax", "Khách"), ("revenue", "Doanh thu"), ("revenue_target", "DT tính chỉ tiêu"), ("moc", "Mốc"), ("pct_moc", "% mốc"), ("f", "Bậc"), ("rate", "Hệ số"), ("commission_est", "Hoa hồng ước"), ("paid", "Đã thu")], "detail": []}}


def tour_le(db: Session, d1: date, d2: date, mang: str = "") -> dict:
    """Hiệu quả từng chuyến khởi hành trong kỳ.

    Không chọn mảng thì giữ nguyên phạm vi cũ (tour lẻ) để số liệu lịch sử không đổi. Chọn mảng thì dùng đúng
    quy tắc của bộ lọc chung: mảng Lẻ loại luôn tour mã MICE bị ghi nhầm loại chuyến – nếu không, tour đó vừa
    nằm ở màn hình phòng Đoàn vừa nằm trong báo cáo hiệu quả của phòng Lẻ."""
    from app.services import settlement as ST
    cond = SEG.tour_cond(mang)
    if cond is None: cond = Tour.tour_type.in_(SEG.LE_TYPES)
    ts = list(db.execute(select(Tour).where(Tour.start_date >= d1, Tour.start_date <= d2, cond).order_by(Tour.start_date)).scalars())
    rows = []
    for t in ts:
        bs = [b for b in t.bookings if not b.cancelled]; rev = sum((b.amount or 0) - (b.discount or 0) for b in bs); paid = sum((b.paid or 0) for b in bs)
        sm = ST.summary(db, t); cost = (sm["actual"] or 0) if sm["lines"] else ((t.actual_cost or 0) or ((t.fixed_cost or 0) + (t.var_cost_per_pax or 0) * len(bs)))
        rows.append({"tour_code": t.code, "name": t.name, "start_date": t.start_date, "end_date": t.end_date, "seats_open": t.seats_open or t.planned_pax, "pax": sum(b.pax for b in bs), "bookings": len(bs), "revenue": rev, "paid": paid, "due": rev - paid,
                     "cost": cost, "profit": rev - cost, "margin": (rev - cost) / rev if rev else 0, "status": t.status, "operator": t.operator.full_name if t.operator else "", "version": t.settlement_version})
    tot = {"tours": len(rows), "pax": sum(r["pax"] for r in rows), "revenue": sum((r["revenue"] or 0) for r in rows), "paid": sum((r["paid"] or 0) for r in rows), "cost": sum((r["cost"] or 0) for r in rows)}; tot["profit"] = (tot["revenue"] or 0) - (tot["cost"] or 0)
    return {"report": "tour_le", "from": d1, "to": d2, "mang": SEG.valid(mang), "summary": rows, "total": tot, "detail": [],
            "columns": {"summary": [("tour_code", "Tour"), ("name", "Tên"), ("start_date", "Khởi hành"), ("seats_open", "Mở bán"), ("pax", "Khách"), ("bookings", "Booking"), ("revenue", "Doanh thu"), ("paid", "Đã thu"), ("due", "Còn lại"), ("cost", "Chi phí"), ("profit", "Lợi nhuận"), ("margin", "Biên"), ("status", "Trạng thái"), ("operator", "Điều hành")], "detail": []}}


def run(db: Session, key: str, params: dict) -> dict:
    today = date.today()
    d1 = date.fromisoformat(params.get("from")) if params.get("from") else today.replace(day=1)
    d2 = date.fromisoformat(params.get("to")) if params.get("to") else today
    mang = SEG.valid(params.get("mang") or "")          # ValueError → API trả 422, không âm thầm bỏ qua
    if key == "ban_tour_le": return ban_tour_le(db, d1, d2, mang)
    if key == "nhac_thu": return nhac_thu(db, mang)
    if key == "huy_cho": return huy_cho(db, d1, d2, mang)
    if key == "kinh_doanh": return kinh_doanh(db, params.get("month") or f"{today:%Y-%m}", mang)
    if key == "tour_le": return tour_le(db, d1, d2, mang)
    raise KeyError(key)


def to_xlsx(rep: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook(); meta = REPORTS[rep["report"]]
    def sheet(ws, title, cols, rows):
        ws.title = title[:30]; ws.append([meta["name"]]); ws["A1"].font = Font(bold=True, size=13)
        ky = f"Kỳ: {rep.get('from', '')} → {rep.get('to', '')}" if rep.get("from") else (f"Tháng {rep.get('month')}" if rep.get("month") else f"Tính đến {rep.get('as_of', datetime.now()):%d/%m/%Y %H:%M}")
        # Phạm vi phải in ngay trên file: một bản Excel rời khỏi phần mềm mà không ghi đang xem phòng nào thì
        # người nhận không có cách nào biết, và hai bản của hai phòng nhìn giống hệt nhau.
        ky += f" – {MANG_LABEL[rep['mang']]}" if rep.get("mang") else " – Toàn hệ thống"
        ws.append([ky]); ws.append([])
        ws.append([c[1] for c in cols])
        for cell in ws[4]: cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9E2F3"); cell.alignment = Alignment(horizontal="center", wrap_text=True)
        for r in rows:
            vals = []
            for k, _ in cols:
                v = r.get(k)
                if isinstance(v, datetime): v = v.strftime("%d/%m/%Y %H:%M")
                elif isinstance(v, date): v = v.strftime("%d/%m/%Y")
                elif isinstance(v, bool): v = "x" if v else ""
                elif isinstance(v, float) and k in ("margin", "pct_moc", "rate"): v = round(v * 100, 1)
                elif isinstance(v, float): v = round(v)
                vals.append(v)
            ws.append(vals)
        for col in ws.columns:
            w = max((len(str(c.value)) for c in col if c.value is not None), default=8); ws.column_dimensions[col[0].column_letter].width = min(max(10, w + 2), 50)
        for row in ws.iter_rows(min_row=5):
            for c in row:
                if isinstance(c.value, (int, float)): c.number_format = "#,##0"
    sheet(wb.active, "Tổng hợp", rep["columns"]["summary"], rep["summary"])
    if rep.get("detail"): sheet(wb.create_sheet(), "Chi tiết", rep["columns"]["detail"], rep["detail"])
    bio = BytesIO(); wb.save(bio); return bio.getvalue()


# ====================== ROBOT R9 – GIÁM SÁT BẤT THƯỜNG ======================
def r9_anomalies(db: Session) -> list[dict]:
    """Phát hiện bất thường để cảnh báo Chủ tịch/TGĐ/BKS (không sửa số liệu). Mỗi mục: kind, level, ref, msg."""
    out = []; today = date.today(); now = datetime.now(); m0 = today.replace(day=1)
    def add(kind, level, ref, msg): out.append({"kind": kind, "level": level, "ref": ref, "msg": msg})
    # 1. Booking tạo mà không có yêu cầu (request_id=0) ngoài dịch vụ lẻ
    for b in db.execute(select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.request_id == 0, Tour.tour_type != "non_package", Booking.vietrip_id == None, Booking.created_at >= datetime.combine(m0, datetime.min.time()))).scalars():
        add("r9_booking_khong_yeu_cau", "warn", f"booking:{b.code}", f"{b.code} tạo trực tiếp không qua yêu cầu đặt dịch vụ (cổng 12) – kiểm tra")
    # 2. Giảm giá lớn > 15% hoặc booking không đủ 4 trường trong tháng, theo sale
    q = select(Booking).where(Booking.created_at >= datetime.combine(m0, datetime.min.time()), Booking.cancelled == False)
    miss: dict[str, int] = {}; big = 0
    for b in db.execute(q).scalars():
        if (b.amount or 0) and (b.discount or 0) / (b.amount or 0) > 0.15: big += 1; add("r9_giam_gia_lon", "warn", f"booking:{b.code}", f"{b.code} giảm giá {(b.discount or 0) / (b.amount or 0) * 100:.0f}% ({(b.discount or 0):,.0f} đ) – cần mã KM có duyệt")
        if not b.counts_for_target: miss[_sales_name(b)] = miss.get(_sales_name(b), 0) + 1
    for s, n in miss.items():
        if n >= 3: add("r9_thieu_4_truong", "warn", f"sale:{s}", f"Sale {s} có {n} booking thiếu 4 trường trong tháng – không tính chỉ tiêu, cần chấn chỉnh")
    # 3. Tour chạy dưới hòa vốn không có quyết định D-7 (đã khởi hành)
    for t in db.execute(select(Tour).where(Tour.status.in_(["da_duyet", "ket_thuc"]), Tour.start_date <= today, Tour.start_date >= today - timedelta(days=30), Tour.tour_type.in_(["le_noi_dia", "le_nuoc_ngoai"]))).scalars():
        c = R.calc_db(db, t, R.get_param(db, "nguong_bien", t.start_date))
        if c["breakeven_pax"] and R.booked_pax(t) < c["breakeven_pax"] and not t.chairman_run_decision and not t.vietrip_id:
            add("r9_chay_duoi_hoa_von", "red", f"tour:{t.code}", f"{t.code} khởi hành {t.start_date:%d/%m} với {R.booked_pax(t)}/{c['breakeven_pax']} khách hòa vốn mà không có quyết định D-7")
    # 4. Lệnh chi cho NCC lạ (lần đầu xuất hiện) ≥ 20 triệu, hoặc chi vượt dự toán tour > 10%
    seen: dict[str, int] = {}
    for pr in db.execute(select(PaymentRequest).order_by(PaymentRequest.created_at)).scalars():
        key = (pr.supplier_tax_code or pr.supplier_name.strip().upper())
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 1 and (pr.amount or 0) >= 20_000_000 and pr.created_at >= datetime.combine(m0, datetime.min.time()) and pr.status not in ("tu_choi",) and not pr.code.startswith("VTDC"):
            add("r9_ncc_moi_chi_lon", "warn", f"dc:{pr.code}", f"{pr.code}: NCC mới {pr.supplier_name} ({(pr.amount or 0):,.0f} đ) – lần đầu giao dịch, kiểm tra hồ sơ NCC/tài khoản")
    # 5. Phiếu thu tiền mặt lớn ≥ 30 triệu trong tháng
    for r in db.execute(select(Receipt).where(Receipt.method == "tien_mat", Receipt.amount >= 30_000_000, Receipt.created_at >= datetime.combine(m0, datetime.min.time()))).scalars():
        add("r9_tien_mat_lon", "warn", f"receipt:{r.code}", f"Phiếu thu tiền mặt {r.code} {r.amount:,.0f} đ – khuyến khích chuyển khoản, Kế toán kiểm biên lai")
    # 6. Giao dịch ngân hàng chờ khớp > 3 ngày
    n_wait = db.execute(select(func.count()).select_from(BankTransaction).where(BankTransaction.match_status == "cho_ke_toan", BankTransaction.received_at < now - timedelta(days=3))).scalar() or 0
    if n_wait: add("r9_gd_cho_khop", "warn", "sepay", f"{n_wait} giao dịch SePay chờ Kế toán khớp quá 3 ngày – tiền vào chưa gắn booking")
    # 7. Booking thu đủ nhưng bị mở khóa nhiều lần / sửa khách sau khóa (nhật ký)
    cnt: dict[str, int] = {}
    for a in db.execute(select(AuditLog).where(AuditLog.action == "mo_khoa_booking", AuditLog.ts >= datetime.combine(m0, datetime.min.time()))).scalars():
        cnt[a.entity] = cnt.get(a.entity, 0) + 1
    for ref, n in cnt.items():
        if n >= 2: add("r9_mo_khoa_nhieu", "warn", ref, f"{ref} bị mở khóa {n} lần trong tháng – rủi ro đổi tên khách/chuyển nhượng chỗ")
    # 8. Bảo lưu tồn lâu (> hạn) hoặc hủy bảo lưu giá trị lớn
    for rt in db.execute(select(Retention).where(Retention.status == "huy", Retention.resolved_at >= datetime.combine(m0, datetime.min.time()), Retention.amount >= 10_000_000)).scalars():
        add("r9_huy_bao_luu_lon", "warn", f"baoluu:{rt.code}", f"Hủy bảo lưu {rt.code} {rt.amount:,.0f} đ ({rt.customer_name}) – ghi thu nhập khác, BKS rà lý do: {rt.resolve_note[:80]}")
    # 9. Quyết toán lệch lớn so booking (đã đóng số tháng này)
    for t in db.execute(select(Tour).where(Tour.status.in_(["da_dong_so", "kt_xac_nhan", "khoa"]), Tour.closed_at >= datetime.combine(m0, datetime.min.time()))).scalars():
        bk = sum((b.amount or 0) - (b.discount or 0) for b in t.bookings if not b.cancelled)
        if bk and abs((t.actual_revenue or 0) - bk) / bk > 0.05:
            add("r9_lech_doanh_thu", "red", f"tour:{t.code}", f"{t.code}: doanh thu quyết toán {(t.actual_revenue or 0):,.0f} lệch {abs((t.actual_revenue or 0) - bk) / bk * 100:.0f}% so booking {bk:,.0f}")
    return out


def r9_run(db: Session) -> dict:
    items = r9_anomalies(db); made = 0
    for it in items:
        if not db.execute(select(Alert).where(Alert.kind == it["kind"], Alert.ref == it["ref"], Alert.resolved == False)).scalars().first():
            db.add(Alert(kind=it["kind"], level=it["level"], ref=it["ref"], message=it["msg"], to_roles="chutich,tgd,bks,ketoan,cntt")); made += 1
    R.audit(db, "robot", "robot", "robot_r9_giam_sat", "robot", after={"phat_hien": len(items), "canh_bao_moi": made}); db.commit()
    return {"found": len(items), "new_alerts": made, "items": items}
