"""Ngân quỹ – tài chính: khế ước vay, hợp đồng đầu tư/hợp tác (mục 3.9), dự báo dòng tiền 13 tuần, báo cáo tài chính tuần (mục 6.6)."""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User
from app.models.finance import FinContract, FinSchedule, CashPlanItem, KIND_ACCOUNT, CONTRACT_KINDS
from app.models.ops import PaymentRequest
from app.models.hr import PayrollRun
from app.services import rules as R
from app.services import accounting as ACC
from app.services import reports as RP


def next_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(FinContract)).scalar() + 1
    return f"HD{date.today():%y%m}-{n:04d}"


def add_months(d: date, n: int) -> date:
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def build_loan_schedule(c: FinContract, months: int, first_due: date) -> list[FinSchedule]:
    """Trả gốc đều hằng tháng + lãi trên dư nợ giảm dần (tham khảo; ngân hàng cung cấp lịch chính thức thì nhập đè)."""
    out = []; principal = c.outstanding or c.principal; per = round(principal / months) if months else principal; bal = principal
    for i in range(months):
        d = add_months(first_due, i)
        interest = round(bal * (c.interest_rate / 100) / 12)
        out.append(FinSchedule(contract_id=c.id, due_date=d, kind="tra_lai", amount=interest))
        pay = per if i < months - 1 else bal
        out.append(FinSchedule(contract_id=c.id, due_date=d, kind="tra_goc", amount=pay)); bal -= pay
    return out


def create_contract(db: Session, u: User, data: dict, months: int = 0, first_due: date | None = None) -> FinContract:
    if data["kind"] not in CONTRACT_KINDS: raise ValueError("Loại hợp đồng không hợp lệ")
    if data["principal"] <= 0: raise ValueError("Giá trị phải > 0")
    if data["kind"] != "vay" and not data.get("approval_ref"): raise ValueError("Khoản đầu tư/hợp tác/cho vay/cọc phải có nghị quyết phê duyệt HĐQT")
    c = FinContract(code=next_code(db), created_by=u.username, **data)
    if not c.outstanding: c.outstanding = c.principal
    db.add(c); db.flush()
    if c.kind == "vay" and months and first_due:
        for s in build_loan_schedule(c, months, first_due): db.add(s)
    elif c.kind != "vay" and c.maturity:
        db.add(FinSchedule(contract_id=c.id, due_date=c.maturity, kind="thu_hoi", amount=c.outstanding))
    R.audit(db, u.username, u.role, "tao_hop_dong_tai_chinh", f"fin:{c.code}", after={"loai": c.kind, "doi_tac": c.partner, "gia_tri": c.principal, "nq": c.approval_ref, "ben_lien_quan": c.related_party})
    db.commit(); db.refresh(c)
    return c


def settle(db: Session, u: User, s: FinSchedule, done_on: date, bank_ref: str, amount: float | None = None) -> FinSchedule:
    """Ghi nhận đã thực hiện một dòng lịch (đối chiếu giao dịch ngân hàng) → bút toán + cập nhật dư nợ."""
    if s.status == "da_thuc_hien": raise ValueError("Đã thực hiện")
    c = s.contract; amt = float(amount or s.amount)
    acc = KIND_ACCOUNT[c.kind]
    lines = {"tra_goc": [{"account": "341", "debit": amt}, {"account": "112", "credit": amt}],
             "tra_lai": [{"account": "635", "debit": amt}, {"account": "112", "credit": amt}],
             "nhan_vay": [{"account": "112", "debit": amt}, {"account": "341", "credit": amt}],
             "giai_ngan": [{"account": acc, "debit": amt}, {"account": "112", "credit": amt}],
             "thu_hoi": [{"account": "112", "debit": amt}, {"account": acc, "credit": amt}]}[s.kind]
    for l in lines: l["partner"] = c.partner
    try:
        e = ACC.post_entry(db, u.username, u.role, done_on, f"{c.code} {c.partner}: {s.kind.replace('_', ' ')} {amt:,.0f}" + (f" (GD {bank_ref})" if bank_ref else ""), lines, "tai_chinh", f"fin:{c.code}")
        s.entry_id = e.id
    except ValueError as ex:
        R.audit(db, u.username, u.role, "ghi_so_that_bai", f"fin:{c.code}", after={"ly_do": str(ex)})
    s.status, s.done_on, s.bank_ref, s.amount = "da_thuc_hien", done_on, bank_ref, amt
    if s.kind in ("tra_goc", "thu_hoi"): c.outstanding = max(0.0, c.outstanding - amt)
    if s.kind in ("nhan_vay", "giai_ngan"): c.outstanding += amt
    if c.outstanding <= 0 and all(x.status == "da_thuc_hien" for x in c.schedule): c.status = "tat_toan"
    R.audit(db, u.username, u.role, "thuc_hien_lich_tai_chinh", f"fin:{c.code}", after={"loai": s.kind, "so_tien": amt, "du_no": c.outstanding})
    db.commit()
    return s


def mark_overdue(db: Session) -> int:
    n = 0
    for s in db.execute(select(FinSchedule).where(FinSchedule.status == "ke_hoach", FinSchedule.due_date < date.today())).scalars():
        s.status = "qua_han"; n += 1
        if s.kind == "thu_hoi": s.contract.status = "qua_han"
    db.commit()
    return n


# ---------- Dự báo dòng tiền 13 tuần ----------
def forecast_13w(db: Session, start: date | None = None) -> dict:
    start = start or date.today()
    start = start - timedelta(days=start.weekday())            # đầu tuần (Thứ Hai)
    weeks = [(start + timedelta(days=7 * i), start + timedelta(days=7 * i + 6)) for i in range(13)]
    b = RP.balances(db, f"{date.today():%Y-%m}")
    opening = sum(b.get(c, 0.0) for c in ("111", "112"))
    rows = [{"week": i + 1, "from": w0, "to": w1, "in": {}, "out": {}} for i, (w0, w1) in enumerate(weeks)]

    def put(d: date, side: str, key: str, amt: float):
        if amt <= 0 or d > weeks[-1][1]: return
        d = max(d, weeks[0][0])
        i = min(12, (d - weeks[0][0]).days // 7)
        rows[i][side][key] = rows[i][side].get(key, 0.0) + amt

    # Thu booking: phần còn phải thu, dự kiến thu trước khởi hành 7 ngày (D-7)
    for bk in db.execute(select(Booking)).scalars():
        t = bk.tour
        if not t or t.status in ("huy", "khoa", "kt_xac_nhan", "da_dong_so"): continue
        due = (bk.amount - bk.discount) - bk.paid
        if due > 0: put(max(date.today(), t.start_date - timedelta(days=7)), "in", "thu_booking", due)
    # Chi tour: lệnh chi chờ (tuần này) và đề nghị đang trình (tuần sau); chi dự toán còn lại của tour sắp chạy
    from app.services.ops import tour_cashflow
    for pr in db.execute(select(PaymentRequest).where(PaymentRequest.status.in_(["cho_chi", "cho_tp", "cho_kt", "cho_duyet"]))).scalars():
        put(date.today() if pr.status == "cho_chi" else date.today() + timedelta(days=7), "out", "chi_ncc", pr.amount)
    for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars():
        cf = tour_cashflow(db, t)
        rest = cf["budget"] - cf["paid"] - cf["committed"] - cf["pending"]
        if rest > 0: put(max(date.today(), t.start_date - timedelta(days=3)), "out", "chi_tour_du_toan", rest)
    # Lịch vay / đầu tư
    for s in db.execute(select(FinSchedule).where(FinSchedule.status.in_(["ke_hoach", "qua_han"]))).scalars():
        key = {"tra_goc": "tra_goc_vay", "tra_lai": "lai_vay", "nhan_vay": "nhan_vay", "giai_ngan": "giai_ngan_dau_tu", "thu_hoi": "thu_hoi_dau_tu"}[s.kind]
        put(max(date.today(), s.due_date), "in" if s.kind in ("nhan_vay", "thu_hoi") else "out", key, s.amount)
    # Kế hoạch thu/chi khác (lương, thuế, thuê văn phòng…) – lặp hằng tháng nếu đánh dấu
    for it in db.execute(select(CashPlanItem)).scalars():
        d = it.due_date
        for k in range(0, 4 if it.recurring_monthly else 1):
            dd = add_months(d, k)
            if dd >= weeks[0][0]: put(dd, it.direction, it.category, it.amount)
    # Lương: nếu chưa có kế hoạch lương thì lấy bảng lương gần nhất, chi ngày 10 hằng tháng
    if not any("luong" in r["out"] for r in rows):
        last = db.execute(select(PayrollRun).order_by(PayrollRun.period.desc())).scalars().first()
        if last and last.totals.get("thuc_nhan"):
            for k in range(0, 4):
                d = add_months(date(date.today().year, date.today().month, 10), k)
                if d >= date.today(): put(d, "out", "luong", last.totals["thuc_nhan"])
    min_cash = R.get_param(db, "so_du_tien_toi_thieu")
    bal = opening; alerts = []
    for r in rows:
        r["total_in"] = sum(r["in"].values()); r["total_out"] = sum(r["out"].values())
        r["net"] = r["total_in"] - r["total_out"]; bal += r["net"]; r["closing"] = bal
        if bal < 0: alerts.append(f"Tuần {r['week']} ({r['from']:%d/%m}): số dư dự kiến ÂM {bal:,.0f} đ")
        elif bal < min_cash: alerts.append(f"Tuần {r['week']} ({r['from']:%d/%m}): dưới ngưỡng tối thiểu {min_cash:,.0f} đ")
    return {"start": weeks[0][0], "opening": opening, "min_cash": min_cash, "weeks": rows, "alerts": alerts, "closing": bal}


# ---------- Báo cáo tài chính tuần cho Chủ tịch/TGĐ/KTT/BKS (mục 6.6) ----------
def weekly_finance(db: Session) -> dict:
    today = date.today(); p = f"{today:%Y-%m}"
    b = RP.balances(db, p)
    cash = sum(b.get(c, 0.0) for c in ("111", "112"))
    loans = [c for c in db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars()]
    invest = [c for c in db.execute(select(FinContract).where(FinContract.kind != "vay")).scalars()]
    d4 = today + timedelta(days=28)
    due4 = [s for s in db.execute(select(FinSchedule).where(FinSchedule.status.in_(["ke_hoach", "qua_han"]), FinSchedule.due_date <= d4)).scalars()]
    # tuổi nợ phải thu: booking chưa thu đủ theo tour đã kết thúc
    recv = []
    for bk in db.execute(select(Booking)).scalars():
        due = (bk.amount - bk.discount) - bk.paid
        if due > 0 and bk.tour:
            age = (today - bk.tour.end_date).days if bk.tour.end_date < today else 0
            recv.append({"booking": bk.code, "customer": bk.customer_name, "tour": bk.tour.code, "due": due, "age_days": age})
    recv.sort(key=lambda r: -r["due"])
    return {"as_of": today, "cash": cash, "loans": [{"code": c.code, "partner": c.partner, "outstanding": c.outstanding, "rate": c.interest_rate, "maturity": c.maturity, "collateral": c.collateral} for c in loans],
            "total_loans": sum(c.outstanding for c in loans),
            "due_4w": [{"contract": s.contract.code, "partner": s.contract.partner, "kind": s.kind, "date": s.due_date, "amount": s.amount, "status": s.status} for s in due4],
            "receivables_top10": recv[:10], "receivables_total": sum(r["due"] for r in recv),
            "investments": [{"code": c.code, "kind": CONTRACT_KINDS.get(c.kind, c.kind), "partner": c.partner, "principal": c.principal, "outstanding": c.outstanding, "maturity": c.maturity, "status": c.status,
                             "related_party": c.related_party, "owner": c.owner, "approval_ref": c.approval_ref} for c in invest],
            "investments_total": sum(c.outstanding for c in invest),
            "wip_154": b.get("154", 0.0), "accrued_335": -b.get("335", 0.0),
            "overdue": [{"contract": s.contract.code, "partner": s.contract.partner, "kind": s.kind, "date": s.due_date, "amount": s.amount} for s in db.execute(select(FinSchedule).where(FinSchedule.status == "qua_han")).scalars()]}
