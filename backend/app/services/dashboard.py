"""Dashboard theo cấp (HĐQT / BĐH / phòng ban – mục 11 MHQT) và robot R7 báo cáo tự động (ngày / tuần / tháng) kèm nhận xét."""
import json, os
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, ServiceRequest, Alert, Param, User
from app.models.payments import BankTransaction, Receipt
from app.models.accounting import JournalEntry, Invoice
from app.models.ops import PaymentRequest, DailyReport, PageShift
from app.models.hr import PayrollRun, Employee, VehicleRate
from app.models.finance import FinSchedule
from app.models.reports_auto import AutoReport
from app.services import rules as R
from app.services import reports as RP
from app.services import finance as FIN
from app.services import ops as OPS
from app.core.config import settings


def _month_tours(db: Session, y: int, m: int) -> list[Tour]:
    return [t for t in db.execute(select(Tour).where(Tour.status.in_(["kt_xac_nhan", "khoa"]))).scalars() if t.kt_confirmed_at and (t.kt_confirmed_at.year, t.kt_confirmed_at.month) == (y, m)]


def build(db: Session, u: User) -> dict:
    """Số liệu dashboard theo vai trò – chỉ đọc, tính từ dữ liệu hiện có."""
    today = date.today(); p = f"{today:%Y-%m}"
    role = u.role
    out: dict = {"role": role, "as_of": datetime.now(), "approvals": [], "kpis": {}, "sections": {}}
    # --- việc chờ duyệt của tôi (mọi phân hệ) ---
    ap = out["approvals"]
    if role in ("chutich", "tgd"):
        n = db.execute(select(func.count()).select_from(Param).where(Param.status == "pending")).scalar()
        if n: ap.append({"label": f"{n} tham số chính sách chờ ký", "href": "/params"})
        n = db.execute(select(func.count()).select_from(VehicleRate).where(VehicleRate.status == "pending")).scalar()
        if n: ap.append({"label": f"{n} giá xe chờ ký", "href": "/hr"})
        q = select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status == "cho_duyet")
        if role == "chutich": q = q.where(PaymentRequest.two_signatures == True)
        n = db.execute(q).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ duyệt", "href": "/expenses"})
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "cho_duyet")).scalars())
        if n: ap.append({"label": f"{n} dự toán tour chờ duyệt", "href": "/tours"})
    if role == "tgd":
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "hcns_lap")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ TGĐ ký lô", "href": "/hr"})
    if role == "ketoan":
        n = db.execute(select(func.count()).select_from(BankTransaction).where(BankTransaction.match_status == "cho_ke_toan")).scalar()
        if n: ap.append({"label": f"{n} giao dịch SePay chờ khớp", "href": "/collections"})
        n = db.execute(select(func.count()).select_from(Receipt).where(Receipt.status == "tu_dong")).scalar()
        if n: ap.append({"label": f"{n} phiếu thu robot chờ xác nhận", "href": "/collections"})
        n = db.execute(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status.in_(["cho_kt", "cho_chi"]))).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ Kế toán kiểm tra / chi", "href": "/expenses"})
        n = db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.status == "nhap")).scalar()
        if n: ap.append({"label": f"{n} chứng từ nháp chờ ghi sổ", "href": "/accounting"})
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars())
        if n: ap.append({"label": f"{n} quyết toán tour chờ Kế toán xác nhận (3 ngày)", "href": "/tours"})
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "nhap")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ xác nhận cơ sở", "href": "/hr"})
    if role == "hcns":
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "kt_xac_nhan")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ HCNS lập", "href": "/hr"})
        n = db.execute(select(func.count()).select_from(Alert).where(Alert.kind == "bc_ngay_2", Alert.resolved == False)).scalar()
        if n: ap.append({"label": f"{n} nhân sự thiếu báo cáo 2 ngày liên tiếp", "href": "/reports"})
    if role in ("tp_dh", "ptgd_mkt", "gd_kd"):
        conf = [k for k, v in OPS.CATEGORY_CONFIRMER.items() if role in v]
        n = db.execute(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status == "cho_tp", PaymentRequest.category.in_(conf))).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ bộ phận xác nhận", "href": "/expenses"})
    if role in ("tp_dh", "gd_kd", "ptgd_doan", "ptgd_mkt", "hcns"):
        n = sum(1 for r in db.execute(select(DailyReport).where(DailyReport.reviewed_by == "")).scalars())
        if n: ap.append({"label": f"{n} báo cáo ngày chưa chấm", "href": "/reports"})
    if role == "cntt":
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "kt_xac_nhan")).scalars())
        if n: ap.append({"label": f"{n} quyết toán chờ CNTT đối chiếu & khóa", "href": "/tours"})
    if role == "nv_dh":
        n = db.execute(select(func.count()).select_from(ServiceRequest).where(ServiceRequest.booking_id == None)).scalar()
        if n: ap.append({"label": f"{n} yêu cầu chờ tạo booking (≤ 2 giờ)", "href": "/requests"})

    # --- KPI theo cấp ---
    k = out["kpis"]
    tours_m = _month_tours(db, today.year, today.month)
    sett = [R.settlement_summary(db, t) for t in tours_m]
    k["doanh_thu_thang"] = sum(s["revenue"] for s in sett); k["loi_nhuan_thang"] = sum(s["profit"] for s in sett); k["so_chuyen_thang"] = len(tours_m)
    k["chuyen_duoi_10"] = sum(1 for s in sett if s["margin"] < R.get_param(db, "nguong_bien"))
    m0 = datetime(today.year, today.month, 1)
    row = db.execute(select(func.count(), func.coalesce(func.sum(Booking.amount - Booking.discount), 0)).where(Booking.created_at >= m0, Booking.cancelled == False)).one()
    k["booking_thang"] = int(row[0]); k["doanh_thu_booking_thang"] = float(row[1])
    k["canh_bao_do"] = db.execute(select(func.count()).select_from(Alert).where(Alert.resolved == False, Alert.level == "red")).scalar()
    if role in ("chutich", "tgd", "ketoan", "bks", "cntt"):
        b = RP.balances(db, p)
        k["tien"] = sum(b.get(c, 0.0) for c in ("111", "112"))
        from app.models.finance import FinContract
        k["no_vay"] = sum(c.outstanding for c in db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars())
        k["phai_thu"] = float(db.execute(select(func.coalesce(func.sum(Booking.amount - Booking.discount - Booking.paid), 0)).where(Booking.cancelled == False, (Booking.amount - Booking.discount - Booking.paid) > 0)).scalar() or 0)
        fc = FIN.forecast_13w(db); k["du_bao_canh_bao"] = len(fc["alerts"]); k["so_du_tuan_13"] = fc["closing"]
        pl = RP.income_statement(db, p); k["ln_ke_toan_thang"] = dict((r[0], r[2]) for r in pl["rows"])["50"]
    # --- phần theo phòng ---
    sec = out["sections"]
    if role in ("gd_kd", "nv_kd", "chutich", "tgd"):
        moc = R.get_param(db, "moc_chi_tieu_hcm"); by = {}
        for t in tours_m:
            if R.is_doan(t): continue
            for b in t.bookings:
                if b.counts_for_target: by[b.sales_id] = by.get(b.sales_id, 0) + b.amount - b.discount
        users = {x.id: x.full_name for x in db.execute(select(User)).scalars()}
        sec["kd_le"] = sorted([{"sales": users.get(i, i), "revenue": v, "pct": v / moc if moc else 0} for i, v in by.items()], key=lambda r: -r["revenue"])
    if role in ("tp_dh", "nv_dh", "chutich", "tgd"):
        d7 = int(R.get_param(db, "moc_d7")); rows = []
        for t in db.execute(select(Tour).where(Tour.status == "da_duyet", Tour.start_date >= today, Tour.start_date <= today + timedelta(days=21))).scalars():
            c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date)); left = (t.start_date - today).days
            rows.append({"code": t.code, "start": t.start_date, "days_left": left, "booked": R.booked_pax(t), "breakeven": c["breakeven_pax"], "below": R.booked_pax(t) < (c["breakeven_pax"] or 0)})
        sec["sap_khoi_hanh"] = sorted(rows, key=lambda r: r["days_left"])
        sec["qua_han_qt"] = [{"code": t.code, "deadline": R.settlement_deadline(db, t)} for t in db.execute(select(Tour).where(Tour.status == "ket_thuc", Tour.end_date < today).order_by(desc(Tour.end_date)).limit(400)).scalars() if today > R.settlement_deadline(db, t)][:100]
    if role in ("hcns", "chutich", "tgd"):
        s = OPS.work_days_in(today.year, today.month, until=today)
        emps = db.execute(select(Employee).where(Employee.active == True, Employee.department.in_(OPS.NO_TIMESHEET_DEPTS), Employee.user_id != None)).scalars().all()
        reps = [r for r in db.execute(select(DailyReport)).scalars() if f"{r.report_date:%Y-%m}" == p]
        sec["bao_cao_ngay"] = {"nhan_su": len(emps), "ngay_lam_viec": len(s), "ty_le_nop": (len(reps) / (len(emps) * len(s))) if emps and s else 0,
                              "thieu_2_ngay": db.execute(select(func.count()).select_from(Alert).where(Alert.kind == "bc_ngay_2", Alert.resolved == False)).scalar()}
    return out


# ====================== ROBOT R7 – BÁO CÁO TỰ ĐỘNG ======================
def _fmt(v): return f"{v:,.0f}"


def compose(db: Session, kind: str) -> tuple[str, dict]:
    """Gom số liệu báo cáo ngày/tuần/tháng thành markdown + dict số liệu."""
    today = date.today(); p = f"{today:%Y-%m}"
    data: dict = {"kind": kind, "date": str(today)}
    lines = []
    if kind == "ngay":
        alerts = db.execute(select(Alert).where(Alert.resolved == False).order_by(desc(Alert.created_at))).scalars().all()
        txns = [t for t in db.execute(select(BankTransaction)).scalars() if t.received_at.date() == today]
        cho = [t for t in txns if t.match_status == "cho_ke_toan"]
        reqs = [r for r in db.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)).scalars()]
        fc = FIN.forecast_13w(db)
        data.update({"alerts_red": sum(1 for a in alerts if a.level == "red"), "alerts": len(alerts), "sepay_in": sum(t.amount for t in txns if t.transfer_type == "in"), "sepay_cho": len(cho),
                     "yc_cho_booking": len(reqs), "tien": fc["opening"], "canh_bao_dong_tien": fc["alerts"][:3]})
        lines += [f"# Báo cáo ngày {today:%d/%m/%Y} (robot R7)", "",
                  f"- Tiền hiện có: **{_fmt(fc['opening'])} đ**; dự báo 13 tuần: {len(fc['alerts'])} tuần cảnh báo" + (f" – {fc['alerts'][0]}" if fc["alerts"] else ""),
                  f"- SePay hôm nay: tiền vào {_fmt(data['sepay_in'])} đ; {len(cho)} giao dịch chờ Kế toán khớp",
                  f"- Yêu cầu chưa tạo booking: {len(reqs)}",
                  f"- Cảnh báo mở: {len(alerts)} (đỏ: {data['alerts_red']})"] + [f"  - [{a.level}] {a.message}" for a in alerts[:8]]
    elif kind == "tuan":
        w = FIN.weekly_finance(db); fc = FIN.forecast_13w(db)
        d7 = [t for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars() if 0 <= (t.start_date - today).days <= 7 and R.booked_pax(t) < (R.calc(t, R.get_param(db, "nguong_bien"))["breakeven_pax"] or 0)]
        qh = [t for t in db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars() if today > R.settlement_deadline(db, t)]
        bk = [b for b in db.execute(select(Booking)).scalars() if (today - b.created_at.date()).days < 7]
        data.update({"tien": w["cash"], "no_vay": w["total_loans"], "phai_thu": w["receivables_total"], "dau_tu": w["investments_total"], "wip_154": w["wip_154"], "accrued_335": w["accrued_335"],
                     "han_4_tuan": sum(x["amount"] for x in w["due_4w"]), "d7": [t.code for t in d7], "qua_han_qt": [t.code for t in qh], "booking_tuan": len(bk), "dt_booking_tuan": sum(b.amount - b.discount for b in bk),
                     "canh_bao_dong_tien": fc["alerts"][:5], "qua_han_tai_chinh": w["overdue"]})
        lines += [f"# Báo cáo tuần – đến {today:%d/%m/%Y} (robot R7)", "", "## Tài chính (Chủ tịch, TGĐ, KTT, BKS)",
                  f"- Tiền: **{_fmt(w['cash'])} đ** · Dư nợ vay: {_fmt(w['total_loans'])} đ · Phải thu khách: {_fmt(w['receivables_total'])} đ",
                  f"- Đầu tư, hợp tác, ký quỹ, cọc, cho vay còn lại: {_fmt(w['investments_total'])} đ; quá hạn thu hồi: {len(w['overdue'])} khoản",
                  f"- Hạn trả gốc/lãi/thu hồi 4 tuần tới: {_fmt(data['han_4_tuan'])} đ ({len(w['due_4w'])} dòng)",
                  f"- 154 tồn đọng: {_fmt(w['wip_154'])} đ · 335 chưa hóa đơn: {_fmt(w['accrued_335'])} đ",
                  f"- Dự báo 13 tuần: {len(fc['alerts'])} tuần cảnh báo" + ("; " + "; ".join(fc["alerts"][:2]) if fc["alerts"] else ""),
                  "", "## Kinh doanh – Điều hành", f"- Booking tuần: {len(bk)} · doanh thu booking {_fmt(data['dt_booking_tuan'])} đ",
                  f"- Chuyến D-7 dưới hòa vốn: {', '.join(data['d7']) or 'không'}", f"- Tour quá hạn quyết toán: {', '.join(data['qua_han_qt']) or 'không'}"]
    else:  # thang
        y, m = today.year, today.month
        tours_m = _month_tours(db, y, m); sett = [(t, R.settlement_summary(db, t)) for t in tours_m]
        pl = RP.income_statement(db, p); plr = dict((r[0], r[2]) for r in pl["rows"])
        run = db.execute(select(PayrollRun).where(PayrollRun.period == p)).scalars().first()
        by_op = {}
        for t, s in sett:
            o = by_op.setdefault(t.operator.full_name if t.operator else "?", {"chuyen": 0, "ln": 0.0, "dat": 0})
            o["chuyen"] += 1; o["ln"] += s["profit"]; o["dat"] += 1 if s["margin"] >= R.get_param(db, "nguong_bien") else 0
        data.update({"so_chuyen": len(tours_m), "doanh_thu_qt": sum(s["revenue"] for _, s in sett), "loi_nhuan_qt": sum(s["profit"] for _, s in sett),
                     "chuyen_duoi_10": sum(1 for _, s in sett if s["margin"] < R.get_param(db, "nguong_bien")), "quy_thuong_dh": sum(s["fund"] for _, s in sett),
                     "kqkd": plr, "lai_vay": pl["management"]["interest"], "khau_hao": pl["management"]["depreciation"], "theo_dieu_hanh": by_op,
                     "bang_luong": run.status if run else "chưa lập", "thuc_nhan": run.totals.get("thuc_nhan") if run else 0})
        lines += [f"# Báo cáo tháng {m:02d}/{y} (robot R7)", "", "## Kết quả kinh doanh (BCKQKD tách lãi vay, khấu hao – Kế toán ngày 10)",
                  f"- Doanh thu kế toán: **{_fmt(plr['01'])} đ** · Giá vốn: {_fmt(plr['11'])} đ · LN trước thuế: **{_fmt(plr['50'])} đ**",
                  f"- Lãi vay: {_fmt(pl['management']['interest'])} đ · Khấu hao: {_fmt(pl['management']['depreciation'])} đ · LN sau lãi vay trước khấu hao: {_fmt(pl['management']['profit_after_interest_before_dep'])} đ",
                  "", "## Quyết toán chuyến (căn cứ thưởng)", f"- {len(tours_m)} chuyến Kế toán xác nhận · doanh thu {_fmt(data['doanh_thu_qt'])} đ · lợi nhuận {_fmt(data['loi_nhuan_qt'])} đ · {data['chuyen_duoi_10']} chuyến dưới 10% · quỹ thưởng ĐH {_fmt(data['quy_thuong_dh'])} đ"]
        lines += [f"  - {n}: {o['chuyen']} chuyến, LN {_fmt(o['ln'])} đ, đạt 10%: {o['dat']}/{o['chuyen']}" for n, o in by_op.items()]
        lines += ["", "## Nhân sự", f"- Bảng lương {p}: {data['bang_luong']}; thực nhận {_fmt(data['thuc_nhan'] or 0)} đ"]
    return "\n".join(lines), data


def claude_comment(md: str, data: dict) -> str:
    """Nhận xét ngắn bằng tiếng Việt qua Anthropic API nếu có khóa; không có khóa → nhận xét theo quy tắc."""
    key = settings.ANTHROPIC_API_KEY
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(model=settings.ANTHROPIC_MODEL, max_tokens=400, messages=[{"role": "user", "content":
                "Bạn là robot báo cáo quản trị của Vietourist Holdings (công ty lữ hành). Đọc số liệu dưới đây và viết 3–5 câu nhận xét ngắn gọn bằng tiếng Việt cho Ban Điều hành: điểm cần chú ý, rủi ro, việc nên làm trong tuần. Không bịa số.\n\n" + md}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        except Exception as ex:  # noqa
            return f"(Không gọi được Claude API: {type(ex).__name__}) " + rule_comment(data)
    return rule_comment(data)


def rule_comment(d: dict) -> str:
    notes = []
    if d.get("canh_bao_dong_tien"): notes.append("Dòng tiền dự báo có tuần dưới ngưỡng/âm – cần đẩy thu booking trước D-7 và giãn lệnh chi chưa cấp thiết.")
    if d.get("qua_han_qt"): notes.append(f"Có {len(d['qua_han_qt'])} tour quá hạn quyết toán – người điều hành mất thưởng chuyến, Kế toán cần danh sách hằng tuần.")
    if d.get("d7"): notes.append(f"{len(d['d7'])} chuyến D-7 dưới hòa vốn chưa có quyết định ghép/dời/hủy.")
    if d.get("sepay_cho"): notes.append(f"{d['sepay_cho']} giao dịch ngân hàng chờ Kế toán khớp – nên xử lý trong ngày để công nợ khách chính xác.")
    if d.get("chuyen_duoi_10"): notes.append(f"{d['chuyen_duoi_10']} chuyến quyết toán dưới biên 10% – rà giá vốn định mức và mã khuyến mãi.")
    if d.get("qua_han_tai_chinh"): notes.append(f"{len(d['qua_han_tai_chinh'])} khoản thu hồi đầu tư/hợp tác quá hạn – trình HĐQT phương án.")
    return " ".join(notes) or "Không có điểm bất thường theo quy tắc; số liệu trong ngưỡng."


def run_report(db: Session, kind: str, actor: str = "robot") -> AutoReport:
    if kind not in ("ngay", "tuan", "thang"): raise ValueError("kind: ngay / tuan / thang")
    md, data = compose(db, kind)
    comment = claude_comment(md, data)
    md += "\n\n## Nhận xét của robot\n" + comment
    today = date.today()
    period = str(today) if kind == "ngay" else f"{today:%Y}-W{today.isocalendar()[1]:02d}" if kind == "tuan" else f"{today:%Y-%m}"
    rep = db.execute(select(AutoReport).where(AutoReport.kind == kind, AutoReport.period == period)).scalars().first()
    if rep is None:
        rep = AutoReport(kind=kind, period=period); db.add(rep)
    rep.content, rep.data, rep.comment, rep.created_by, rep.created_at = md, data, comment, actor, datetime.now()
    R.audit(db, actor, "robot", "robot_bao_cao", f"report:{kind}:{period}", after={"dai": len(md)})
    db.commit(); db.refresh(rep)
    return rep
