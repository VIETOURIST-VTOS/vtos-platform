"""Robot R2 – Kế toán tự động theo TT99/2025.

Nguyên tắc: mọi bút toán sinh từ nghiệp vụ đã được Kế toán xác nhận (phiếu thu, hóa đơn phát hành, quyết toán tour);
chứng từ đã ghi sổ là bất biến – sai thì lập chứng từ đảo. Kỳ đã khóa không ghi sổ.
"""
from datetime import date, datetime
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User
from app.models.payments import Receipt
from app.models.accounting import Account, JournalEntry, JournalLine, Invoice, PeriodLock
from app.services import rules as R

# Hệ thống tài khoản rút gọn cho công ty lữ hành (TT99/2025, Phụ lục I) – bổ sung dần
CHART = [
    ("111", "Tiền mặt", "TS", ""), ("112", "Tiền gửi ngân hàng", "TS", ""),
    ("131", "Phải thu của khách hàng", "TS", ""), ("133", "Thuế GTGT được khấu trừ", "TS", ""),
    ("138", "Phải thu khác", "TS", ""), ("141", "Tạm ứng", "TS", ""),
    ("154", "Chi phí SXKD dở dang (chi phí tour)", "TS", ""), ("211", "Tài sản cố định hữu hình", "TS", ""),
    ("214", "Hao mòn TSCĐ", "TS", ""), ("242", "Chi phí trả trước", "TS", ""),
    ("331", "Phải trả người bán (NCC dịch vụ)", "NV", ""), ("333", "Thuế và các khoản phải nộp", "NV", ""),
    ("3331", "Thuế GTGT phải nộp", "NV", "333"), ("3334", "Thuế TNDN", "NV", "333"), ("3335", "Thuế TNCN", "NV", "333"),
    ("334", "Phải trả người lao động", "NV", ""), ("335", "Chi phí phải trả (NCC chưa có hóa đơn)", "NV", ""),
    ("338", "Phải trả, phải nộp khác", "NV", ""), ("3387", "Doanh thu chưa thực hiện / đặt cọc", "NV", "338"),
    ("341", "Vay và nợ thuê tài chính", "NV", ""), ("411", "Vốn đầu tư của chủ sở hữu", "NV", ""),
    ("421", "Lợi nhuận sau thuế chưa phân phối", "NV", ""),
    ("511", "Doanh thu bán hàng và cung cấp dịch vụ", "DT", ""), ("515", "Doanh thu hoạt động tài chính", "DT", ""),
    ("632", "Giá vốn hàng bán (giá vốn tour)", "CP", ""), ("635", "Chi phí tài chính", "CP", ""),
    ("641", "Chi phí bán hàng", "CP", ""), ("642", "Chi phí quản lý doanh nghiệp", "CP", ""),
    ("711", "Thu nhập khác", "DT", ""), ("811", "Chi phí khác", "CP", ""),
    ("821", "Chi phí thuế TNDN", "CP", ""), ("911", "Xác định kết quả kinh doanh", "XD", ""),
]


def seed_accounts(db: Session):
    if db.get(Account, "111"):
        return
    for c, n, k, p in CHART:
        db.add(Account(code=c, name=n, kind=k, parent=p))
    db.commit()


def period_of(d: date) -> str:
    return f"{d:%Y-%m}"


def is_locked(db: Session, period: str) -> bool:
    return db.get(PeriodLock, period) is not None


def _next_code(db: Session, prefix: str, d: date) -> str:
    n = db.execute(select(func.count()).select_from(JournalEntry)).scalar() + 1
    return f"{prefix}{d:%y%m}-{n:04d}"


def post_entry(db: Session, actor: str, role: str, entry_date: date, description: str, lines: list[dict],
               source_type: str = "thu_cong", source_ref: str = "", tour_id: int | None = None, post: bool = True) -> JournalEntry:
    """lines: [{account, debit, credit, partner?, booking_id?, tour_id?, note?}]. Kiểm tra cân đối và kỳ khóa."""
    period = period_of(entry_date)
    if is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa – không ghi sổ được")
    td = round(sum(float(l.get("debit") or 0) for l in lines), 0)
    tc = round(sum(float(l.get("credit") or 0) for l in lines), 0)
    if td <= 0 or abs(td - tc) >= 1:
        raise ValueError(f"Bút toán không cân: Nợ {td:,.0f} ≠ Có {tc:,.0f}")
    for l in lines:
        if not db.get(Account, str(l["account"])):
            raise ValueError(f"Tài khoản {l['account']} không có trong danh mục")
    e = JournalEntry(code=_next_code(db, "CT", entry_date), entry_date=entry_date, period=period, description=description[:300],
                     source_type=source_type, source_ref=source_ref, tour_id=tour_id, created_by=actor,
                     status="da_ghi_so" if post else "nhap", posted_by=actor if post else "", posted_at=datetime.now() if post else None)
    for l in lines:
        e.lines.append(JournalLine(account_code=str(l["account"]), debit=float(l.get("debit") or 0), credit=float(l.get("credit") or 0),
                                   partner=l.get("partner") or "", booking_id=l.get("booking_id"), tour_id=l.get("tour_id") or tour_id, note=l.get("note") or ""))
    db.add(e); db.flush()
    R.audit(db, actor, role, "ghi_so" if post else "lap_chung_tu", f"entry:{e.code}",
            after={"nguon": source_type, "ref": source_ref, "so_tien": td, "dong": [(l["account"], l.get("debit") or 0, l.get("credit") or 0) for l in lines]})
    return e


def post_draft(db: Session, u: User, e: JournalEntry) -> JournalEntry:
    if e.status != "nhap":
        raise ValueError("Chứng từ không ở trạng thái nháp")
    if is_locked(db, e.period):
        raise ValueError(f"Kỳ {e.period} đã khóa")
    e.status, e.posted_by, e.posted_at = "da_ghi_so", u.username, datetime.now()
    R.audit(db, u.username, u.role, "ghi_so", f"entry:{e.code}", after={"so_tien": sum(l.debit for l in e.lines)})
    db.commit()
    return e


def reverse_entry(db: Session, u: User, e: JournalEntry, reason: str) -> JournalEntry:
    """Bút toán đảo: ghi ngược Nợ/Có cùng số tiền vào ngày hôm nay (chứng từ gốc giữ nguyên)."""
    if e.status != "da_ghi_so":
        raise ValueError("Chỉ đảo chứng từ đã ghi sổ")
    if e.reversed_by_id:
        raise ValueError("Chứng từ đã được đảo")
    lines = [{"account": l.account_code, "debit": l.credit, "credit": l.debit, "partner": l.partner, "booking_id": l.booking_id,
              "tour_id": l.tour_id, "note": f"Đảo {e.code}"} for l in e.lines]
    r = post_entry(db, u.username, u.role, date.today(), f"Đảo {e.code}: {reason}", lines, "dao", f"entry:{e.code}", e.tour_id)
    e.reversed_by_id = r.id
    db.commit()
    return r


# ---------- Bút toán tự động từ nghiệp vụ ----------
def on_receipt_confirmed(db: Session, r: Receipt, actor: str, role: str) -> JournalEntry | None:
    """Phiếu thu được Kế toán xác nhận → Nợ 111/112 – Có 131 (khách, booking)."""
    if db.execute(select(JournalEntry).where(JournalEntry.source_ref == f"receipt:{r.code}")).scalars().first():
        return None
    b = db.get(Booking, r.booking_id)
    cash = "111" if r.method == "tien_mat" else "112"
    d = (r.confirmed_at or r.created_at or datetime.now()).date()
    try:
        return post_entry(db, "robot", "robot", d, f"Thu tiền {b.code if b else ''} – {r.payer}",
                          [{"account": cash, "debit": r.amount, "partner": r.payer, "booking_id": r.booking_id},
                           {"account": "131", "credit": r.amount, "partner": b.customer_name if b else r.payer, "booking_id": r.booking_id}],
                          "thu_tien", f"receipt:{r.code}", b.tour_id if b else None)
    except ValueError as ex:  # kỳ khóa → cảnh báo, không chặn nghiệp vụ thu tiền
        R.audit(db, actor, role, "ghi_so_that_bai", f"receipt:{r.code}", after={"ly_do": str(ex)})
        return None


def on_invoice_issued(db: Session, inv: Invoice) -> JournalEntry:
    """Phát hành hóa đơn → Nợ 131 – Có 511 (doanh thu chưa thuế), Có 3331 (thuế GTGT)."""
    lines = [{"account": "131", "debit": inv.total, "partner": inv.customer_name, "booking_id": inv.booking_id},
             {"account": "511", "credit": inv.pre_tax, "partner": inv.customer_name, "booking_id": inv.booking_id}]
    if inv.vat > 0:
        lines.append({"account": "3331", "credit": inv.vat, "partner": inv.customer_name})
    return post_entry(db, "robot", "robot", inv.issue_date, f"Hóa đơn {inv.series}-{inv.number:07d} – {inv.customer_name}", lines,
                      "hoa_don", f"invoice:{inv.series}-{inv.number}", inv.tour_id)


def on_settlement_confirmed(db: Session, t: Tour, actor: str, role: str) -> list[JournalEntry]:
    """Kế toán xác nhận quyết toán tour → tập hợp chi phí tour và kết chuyển giá vốn:
       Nợ 154 – Có 331 (chi phí NCC theo quyết toán, chưa gồm mã KM – mã KM là dòng giá vốn quản trị nội bộ)
       Nợ 632 – Có 154 (kết chuyển khi chuyến hoàn thành)."""
    if db.execute(select(JournalEntry).where(JournalEntry.source_ref == f"tour:{t.code}", JournalEntry.source_type == "quyet_toan")).scalars().first():
        return []
    d = (t.kt_confirmed_at or datetime.now()).date()
    out = []
    if t.actual_cost > 0:
        try:
            out.append(post_entry(db, "robot", "robot", d, f"Chi phí tour {t.code} theo quyết toán",
                                  [{"account": "154", "debit": t.actual_cost, "tour_id": t.id}, {"account": "331", "credit": t.actual_cost, "partner": "NCC dịch vụ tour", "tour_id": t.id}],
                                  "quyet_toan", f"tour:{t.code}", t.id))
            out.append(post_entry(db, "robot", "robot", d, f"Kết chuyển giá vốn tour {t.code}",
                                  [{"account": "632", "debit": t.actual_cost, "tour_id": t.id}, {"account": "154", "credit": t.actual_cost, "tour_id": t.id}],
                                  "quyet_toan", f"tour:{t.code}", t.id))
        except ValueError as ex:
            R.audit(db, actor, role, "ghi_so_that_bai", f"tour:{t.code}", after={"ly_do": str(ex)})
    return out


# ---------- Hóa đơn điện tử ----------
class LocalInvoiceProvider:
    """Adapter mặc định: cấp số nội bộ. Khi ký hợp đồng HĐĐT (Viettel/VNPT/MISA meInvoice…) thay bằng adapter gọi API nhà cung cấp."""
    name = "noi_bo"

    def issue(self, db: Session, inv: Invoice) -> tuple[int, str]:
        last = db.execute(select(func.max(Invoice.number)).where(Invoice.series == inv.series)).scalar() or 0
        n = last + 1
        return n, f"LOCAL-{inv.series}-{n:07d}"


PROVIDER = LocalInvoiceProvider()


def create_invoice(db: Session, u: User, b: Booking, vat_rate: float | None, tax_code: str, address: str, description: str) -> Invoice:
    if db.execute(select(Invoice).where(Invoice.booking_id == b.id, Invoice.status != "huy")).scalars().first():
        raise ValueError(f"Booking {b.code} đã có hóa đơn")
    rate = R.get_param(db, "thue_gtgt") if vat_rate is None else float(vat_rate)
    total = b.amount - b.discount                      # giá bán đã gồm thuế
    pre = round(total / (1 + rate)) if rate > 0 else total
    inv = Invoice(booking_id=b.id, tour_id=b.tour_id, customer_name=b.customer_name, customer_tax_code=tax_code, customer_address=address,
                  description=description or f"Dịch vụ du lịch – {b.tour.name if b.tour else ''} ({b.pax} khách)",
                  pre_tax=pre, vat_rate=rate, vat=total - pre, total=total, created_by=u.username)
    db.add(inv); db.flush()
    R.audit(db, u.username, u.role, "lap_hoa_don_nhap", f"invoice_draft:{inv.id}", after={"booking": b.code, "tong": total, "thue": rate})
    db.commit(); db.refresh(inv)
    return inv


def issue_invoice(db: Session, u: User, inv: Invoice) -> Invoice:
    if inv.status != "nhap":
        raise ValueError("Hóa đơn không ở trạng thái nháp")
    if is_locked(db, period_of(date.today())):
        raise ValueError("Kỳ hiện tại đã khóa")
    inv.number, inv.provider_ref = PROVIDER.issue(db, inv)
    inv.provider, inv.issue_date, inv.status = PROVIDER.name, date.today(), "da_phat_hanh"
    inv.issued_by, inv.issued_at = u.username, datetime.now()
    db.flush()
    e = on_invoice_issued(db, inv)
    inv.entry_id = e.id
    R.audit(db, u.username, u.role, "phat_hanh_hoa_don", f"invoice:{inv.series}-{inv.number}", after={"tong": inv.total, "ma_tra_cuu": inv.provider_ref, "chung_tu": e.code})
    db.commit(); db.refresh(inv)
    return inv


def cancel_invoice(db: Session, u: User, inv: Invoice, reason: str) -> Invoice:
    if inv.status == "huy":
        raise ValueError("Hóa đơn đã hủy")
    if inv.status == "da_phat_hanh" and inv.entry_id:
        e = db.get(JournalEntry, inv.entry_id)
        if e and not e.reversed_by_id:
            reverse_entry(db, u, e, f"Hủy hóa đơn {inv.series}-{inv.number}: {reason}")
    inv.status = "huy"
    R.audit(db, u.username, u.role, "huy_hoa_don", f"invoice:{inv.series}-{inv.number or inv.id}", after={"ly_do": reason})
    db.commit()
    return inv


# ---------- Sổ sách & khóa kỳ ----------
def ledger(db: Session, account: str, period: str | None) -> dict:
    """Sổ cái tài khoản (S03b): số dư đầu kỳ, phát sinh, số dư cuối."""
    acc = db.get(Account, account)
    if not acc:
        raise ValueError("Không có tài khoản")
    q = select(JournalLine, JournalEntry).join(JournalEntry).where(JournalLine.account_code == account, JournalEntry.status == "da_ghi_so").order_by(JournalEntry.entry_date, JournalEntry.id)
    rows = db.execute(q).all()
    debit_side = acc.kind in ("TS", "CP")
    opening = sum((l.debit - l.credit) for l, e in rows if period and e.period < period)
    bal = opening
    out = []
    for l, e in rows:
        if period and e.period != period:
            continue
        bal += l.debit - l.credit
        out.append({"date": e.entry_date, "code": e.code, "description": e.description, "partner": l.partner, "debit": l.debit, "credit": l.credit,
                    "balance": bal if debit_side else -bal, "entry_id": e.id})
    return {"account": account, "name": acc.name, "kind": acc.kind, "opening": opening if debit_side else -opening,
            "total_debit": sum(r["debit"] for r in out), "total_credit": sum(r["credit"] for r in out), "closing": bal if debit_side else -bal, "rows": out}


def trial_balance(db: Session, period: str) -> list[dict]:
    """Bảng cân đối số phát sinh (S06) theo kỳ."""
    res = {}
    for acc in db.execute(select(Account).order_by(Account.code)).scalars():
        res[acc.code] = {"account": acc.code, "name": acc.name, "kind": acc.kind, "open_debit": 0.0, "open_credit": 0.0, "debit": 0.0, "credit": 0.0}
    for l, e in db.execute(select(JournalLine, JournalEntry).join(JournalEntry).where(JournalEntry.status == "da_ghi_so")).all():
        r = res.get(l.account_code)
        if not r: continue
        if e.period < period:
            r["open_debit"] += l.debit; r["open_credit"] += l.credit
        elif e.period == period:
            r["debit"] += l.debit; r["credit"] += l.credit
    out = []
    for r in res.values():
        net_open = r["open_debit"] - r["open_credit"]
        r["open_debit"], r["open_credit"] = (net_open, 0.0) if net_open >= 0 else (0.0, -net_open)
        net_close = net_open + r["debit"] - r["credit"]
        r["close_debit"], r["close_credit"] = (net_close, 0.0) if net_close >= 0 else (0.0, -net_close)
        if any(abs(r[k]) > 0 for k in ("open_debit", "open_credit", "debit", "credit")):
            out.append(r)
    return out


def lock_period(db: Session, u: User, period: str, note: str) -> PeriodLock:
    if is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa")
    drafts = db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.period == period, JournalEntry.status == "nhap")).scalar()
    if drafts:
        raise ValueError(f"Còn {drafts} chứng từ nháp trong kỳ {period} – ghi sổ hoặc hủy trước khi khóa")
    pl = PeriodLock(period=period, locked_by=u.username, note=note)
    db.add(pl)
    R.audit(db, u.username, u.role, "khoa_ky_ke_toan", f"period:{period}", after={"ghi_chu": note})
    db.commit()
    return pl
