"""Dashboard theo cấp (HĐQT / BĐH / phòng ban – mục 11 MHQT) và robot R7 báo cáo tự động (ngày / tuần / tháng) kèm nhận xét."""
import json, os
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session, selectinload
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
    """Chuyến Kế toán xác nhận trong THÁNG y-m. Lọc mốc thời gian ngay trong SQL: bản cũ nạp toàn bộ
    chuyến đã xác nhận (hàng nghìn chuyến, kèm booking nạp lười theo sau) rồi mới bỏ đi hầu hết."""
    dau = datetime(y, m, 1)
    cuoi = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1)
    # selectinload: các bảng phía dưới duyệt t.bookings của từng chuyến. Không nạp sẵn thì mỗi chuyến
    # là một câu truy vấn riêng – vài trăm chuyến thành vài trăm chuyến đi–về tới Singapore.
    return list(db.execute(select(Tour).options(selectinload(Tour.bookings))
                           .where(Tour.status.in_(["kt_xac_nhan", "khoa"]),
                                  Tour.kt_confirmed_at >= dau, Tour.kt_confirmed_at < cuoi)).scalars())


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
    if role in ("tp_dh", "ptgd_mkt", "gd_kd", "tp_kd", "tn_kd"):
        conf = [k for k, v in OPS.CATEGORY_CONFIRMER.items() if role in v]
        n = db.execute(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status == "cho_tp", PaymentRequest.category.in_(conf))).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ bộ phận xác nhận", "href": "/expenses"})
    if role in ("tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "ptgd_mkt", "hcns"):
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
    k["doanh_thu_thang"] = sum((s["revenue"] or 0) for s in sett); k["loi_nhuan_thang"] = sum(s["profit"] for s in sett); k["so_chuyen_thang"] = len(tours_m)
    _nguong = R.get_param(db, "nguong_bien")
    k["chuyen_duoi_10"] = sum(1 for s in sett if s["margin"] < _nguong)
    m0 = datetime(today.year, today.month, 1)
    row = db.execute(select(func.count(), func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)), 0)).where(Booking.created_at >= m0, Booking.cancelled == False)).one()
    k["booking_thang"] = int(row[0]); k["doanh_thu_booking_thang"] = float(row[1])
    k["canh_bao_do"] = db.execute(select(func.count()).select_from(Alert).where(Alert.resolved == False, Alert.level == "red")).scalar()
    if role in ("chutich", "tgd", "ketoan", "bks", "cntt"):
        b = RP.balances(db, p)
        k["tien"] = sum(b.get(c, 0.0) for c in ("111", "112"))
        from app.models.finance import FinContract
        k["no_vay"] = sum((c.outstanding or 0) for c in db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars())
        k["phai_thu"] = float(db.execute(select(func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0) - func.coalesce(Booking.paid, 0)), 0)).where(Booking.cancelled == False, (func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0) - func.coalesce(Booking.paid, 0)) > 0)).scalar() or 0)
        fc = FIN.forecast_13w(db); k["du_bao_canh_bao"] = len(fc["alerts"]); k["so_du_tuan_13"] = fc["closing"]
        pl = RP.income_statement(db, p); k["ln_ke_toan_thang"] = dict((r[0], r[2]) for r in pl["rows"])["50"]
    # --- phần theo phòng ---
    sec = out["sections"]
    # Hai phòng Kinh doanh được đo bằng hai thước đo khác nhau, nên màn hình phải hiện hai bảng khác nhau
    # (chỉ đạo 07/9/2026). Phòng Lẻ: doanh thu tính chỉ tiêu so mốc → bậc thang hoa hồng. Phòng Đoàn: chia
    # LỢI NHUẬN quyết toán, không có mốc doanh thu. Trước đây chỉ có bảng của phòng Lẻ, nên người phòng Đoàn
    # mở trang chủ ra không thấy gì về phần việc của mình – đúng cách tính lương của họ cũng không thấy.
    if role in ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "ptgd_doan", "chutich", "tgd"):
        moc = R.get_param(db, "moc_chi_tieu_hcm")
        le: dict[int, float] = {}; doan: dict[int, float] = {}; doan_tours = 0
        for t, s in zip(tours_m, sett):                  # dùng lại `sett` đã tính, không gọi quyết toán lần hai
            if R.is_doan(t):
                doan_tours += 1
                rev = s["revenue"]
                for b in t.bookings:
                    if b.cancelled: continue
                    # Chia lợi nhuận theo tỷ trọng doanh thu booking – cùng công thức bảng lương (services/hr.py),
                    # để con số trên trang chủ và con số trả lương không nói khác nhau.
                    doan[b.sales_id] = doan.get(b.sales_id, 0.0) + s["profit"] * ((b.amount or 0) / rev if rev else 0)
                continue
            for b in t.bookings:
                if b.counts_for_target: le[b.sales_id] = le.get(b.sales_id, 0) + (b.amount or 0) - (b.discount or 0)
        users = {x.id: x.full_name for x in db.execute(select(User)).scalars()}
        sec["kd_le"] = sorted([{"sales": users.get(i, i), "revenue": v, "pct": v / moc if moc else 0} for i, v in le.items()], key=lambda r: -(r["revenue"] or 0))
        sec["kd_doan"] = {"so_chuyen": doan_tours,
                          "rows": sorted([{"sales": users.get(i, i), "profit_share": v} for i, v in doan.items()], key=lambda r: -r["profit_share"])}
    if role in ("tp_dh", "nv_dh", "chutich", "tgd"):
        d7 = int(R.get_param(db, "moc_d7")); rows = []
        for t in db.execute(select(Tour).options(selectinload(Tour.bookings))
                            .where(Tour.status == "da_duyet", Tour.start_date >= today,
                                   Tour.start_date <= today + timedelta(days=21))).scalars():
            c = R.calc_db(db, t, R.get_param(db, "nguong_bien", t.start_date)); left = (t.start_date - today).days
            pax = R.booked_pax(t)
            rows.append({"code": t.code, "start": t.start_date, "days_left": left, "booked": pax,
                         "breakeven": c["breakeven_pax"], "below": pax < (c["breakeven_pax"] or 0)})
        sec["sap_khoi_hanh"] = sorted(rows, key=lambda r: r["days_left"])
        # Quá hạn quyết toán. Hạn = ngày kết thúc + số ngày theo tham số (đoàn và lẻ khác nhau), nên
        # lọc luôn bằng ngày kết thúc: chuyến kết thúc SAU today − hạn dài nhất thì chắc chắn chưa quá
        # hạn, không cần nạp về. Bản cũ nạp 400 chuyến gần nhất rồi bỏ đi phần lớn.
        han_le = int(R.get_param(db, "han_qt_le")); han_doan = int(R.get_param(db, "han_qt_doan"))
        moc = today - timedelta(days=min(han_le, han_doan))
        sec["qua_han_qt"] = [{"code": t.code, "deadline": R.settlement_deadline(db, t)}
                             for t in db.execute(select(Tour).where(Tour.status == "ket_thuc", Tour.end_date < moc)
                                                 .order_by(desc(Tour.end_date)).limit(300)).scalars()
                             if today > R.settlement_deadline(db, t)][:100]
    if role in ("hcns", "chutich", "tgd"):
        s = OPS.work_days_in(today.year, today.month, until=today)
        emps = db.execute(select(Employee).where(Employee.active == True, Employee.department.in_(OPS.NO_TIMESHEET_DEPTS), Employee.user_id != None)).scalars().all()
        # Chỉ cần ĐẾM báo cáo trong tháng – đếm bằng SQL thay vì nạp toàn bộ bảng báo cáo ngày rồi lọc.
        so_bao_cao = db.execute(select(func.count()).select_from(DailyReport)
                                .where(DailyReport.report_date >= date(today.year, today.month, 1),
                                       DailyReport.report_date <= today)).scalar() or 0
        sec["bao_cao_ngay"] = {"nhan_su": len(emps), "ngay_lam_viec": len(s), "ty_le_nop": (so_bao_cao / (len(emps) * len(s))) if emps and s else 0,
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
        data.update({"alerts_red": sum(1 for a in alerts if a.level == "red"), "alerts": len(alerts), "sepay_in": sum((t.amount or 0) for t in txns if t.transfer_type == "in"), "sepay_cho": len(cho),
                     "yc_cho_booking": len(reqs), "tien": fc["opening"], "canh_bao_dong_tien": fc["alerts"][:3]})
        lines += [f"# Báo cáo ngày {today:%d/%m/%Y} (robot R7)", "",
                  f"- Tiền hiện có: **{_fmt(fc['opening'])} đ**; dự báo 13 tuần: {len(fc['alerts'])} tuần cảnh báo" + (f" – {fc['alerts'][0]}" if fc["alerts"] else ""),
                  f"- SePay hôm nay: tiền vào {_fmt(data['sepay_in'])} đ; {len(cho)} giao dịch chờ Kế toán khớp",
                  f"- Yêu cầu chưa tạo booking: {len(reqs)}",
                  f"- Cảnh báo mở: {len(alerts)} (đỏ: {data['alerts_red']})"] + [f"  - [{a.level}] {a.message}" for a in alerts[:8]]
    elif kind == "tuan":
        w = FIN.weekly_finance(db); fc = FIN.forecast_13w(db)
        d7 = [t for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars() if 0 <= (t.start_date - today).days <= 7 and R.booked_pax(t) < (R.calc_db(db, t, R.get_param(db, "nguong_bien"))["breakeven_pax"] or 0)]
        qh = [t for t in db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars() if today > R.settlement_deadline(db, t)]
        bk = [b for b in db.execute(select(Booking)).scalars() if (today - b.created_at.date()).days < 7]
        data.update({"tien": w["cash"], "no_vay": w["total_loans"], "phai_thu": w["receivables_total"], "dau_tu": w["investments_total"], "wip_154": w["wip_154"], "accrued_335": w["accrued_335"],
                     "han_4_tuan": sum((x["amount"] or 0) for x in w["due_4w"]), "d7": [t.code for t in d7], "qua_han_qt": [t.code for t in qh], "booking_tuan": len(bk), "dt_booking_tuan": sum((b.amount or 0) - (b.discount or 0) for b in bk),
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
        data.update({"so_chuyen": len(tours_m), "doanh_thu_qt": sum((s["revenue"] or 0) for _, s in sett), "loi_nhuan_qt": sum(s["profit"] for _, s in sett),
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


def claude_comment(md: str, data: dict, db=None) -> str:
    """Nhận xét ngắn bằng tiếng Việt qua Anthropic API nếu có khóa; không có khóa → nhận xét theo quy tắc.

    Nhận xét này đi thẳng lên bàn Chủ tịch và TGĐ, nên phải để lại vết như mọi việc AI làm: truyền db vào
    thì ghi nhật ký AI (chỉ đạo 07/9/2026). Để db=None thì vẫn chạy như cũ – hàm này còn được gọi từ chỗ
    không có phiên cơ sở dữ liệu.
    """
    prompt = ("Bạn là robot báo cáo quản trị của Vietourist Holdings (công ty lữ hành). Đọc số liệu dưới đây và viết 3–5 câu nhận xét ngắn gọn bằng tiếng Việt cho Ban Điều hành: điểm cần chú ý, rủi ro, việc nên làm trong tuần. Không bịa số.\n\n" + md)

    def _ghi(ket_qua: str, nguon: str, mo_hinh: str = "", t_in: int = 0, t_ra: int = 0, loi: str = ""):
        if db is None: return
        try:
            from app.services import ai_log as AL
            AL.ghi(db, tac_vu="vb_noi_bo", muc=1, dau_vao=prompt, ket_qua=ket_qua, nguon=nguon,
                   mo_hinh=mo_hinh, ref="bao_cao_quan_tri", tokens_vao=t_in, tokens_ra=t_ra, loi=loi)
        except Exception:  # noqa – nhật ký hỏng không được làm hỏng báo cáo
            pass

    key = settings.ANTHROPIC_API_KEY
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(model=settings.ANTHROPIC_MODEL, max_tokens=400, messages=[{"role": "user", "content": prompt}])
            out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            u = getattr(msg, "usage", None)
            _ghi(out, "claude", settings.ANTHROPIC_MODEL,
                 int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0))
            return out
        except Exception as ex:  # noqa
            out = f"(Không gọi được Claude API: {type(ex).__name__}) " + rule_comment(data)
            _ghi(out, "quy_tac", loi=f"{type(ex).__name__}: {ex}")
            return out
    out = rule_comment(data)
    _ghi(out, "quy_tac", loi="chưa cấu hình ANTHROPIC_API_KEY")
    return out


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
    comment = claude_comment(md, data, db)
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
