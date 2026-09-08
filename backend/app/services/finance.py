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
    # V12 – KHOẢN VAY đi qua bảng quy ước hạch toán, không tự dựng cặp tài khoản ở đây.
    #
    # Ba lý do, và lý do thứ ba là lý do thật:
    #   · cặp tài khoản dựng tay ở đây là 341/112, còn quy ước là 3411/1121 – hai chỗ đã lệch sẵn;
    #   · kế toán sửa quy ước trên màn hình thì bản sửa không tới được chỗ này;
    #   · và quan trọng nhất: nhánh dưới NUỐT lỗi ghi sổ (bắt ValueError rồi vẫn đánh dấu đã thực
    #     hiện). Kỳ được đánh dấu xong mà sổ không có bút toán nào – đó chính là cách "dư nợ vay trên
    #     sổ" và "lịch trả nợ" trở thành hai con số sống riêng.
    #
    # Nhánh V12 để lỗi NỔI LÊN. Ghi sổ hỏng thì kỳ KHÔNG được đánh dấu đã thực hiện.
    if c.kind == "vay" and s.kind in ("tra_goc", "tra_lai", "nhan_vay", "giai_ngan"):
        from app.services import vay_but_toan as VBT
        s.amount, s.bank_ref, s.done_on = amt, bank_ref, done_on
        VBT.ghi_so(db, s, u.username, u.role, done_on)
        # Chỉ GỐC chạm dư nợ. Trả LÃI không làm dư nợ đổi – lãi là chi phí, không phải khoản vay.
        # Viết ba nhánh rõ ràng thay vì "if trả gốc … else cộng vào": nhánh else nuốt luôn tra_lai và
        # cộng tiền lãi vào dư nợ gốc, làm dư nợ phình lên đúng bằng số lãi vừa trả.
        if s.kind == "tra_goc":
            c.outstanding = max(0.0, c.outstanding - amt)
        elif s.kind in ("nhan_vay", "giai_ngan"):
            c.outstanding += amt
        if c.outstanding <= 0 and all(x.status == "da_thuc_hien" for x in c.schedule):
            c.status = "tat_toan"
        R.audit(db, u.username, u.role, "thuc_hien_lich_tai_chinh", f"fin:{c.code}",
                after={"loai": s.kind, "so_tien": amt, "du_no": c.outstanding, "qua_quy_uoc": True})
        db.commit()
        return s
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

    # Thu booking: phần còn phải thu, dự kiến thu trước khởi hành 7 ngày (D-7).
    # Nối bảng và lọc ngay trong SQL, chỉ lấy 3 cột. Bản cũ nạp TOÀN BỘ booking (10.303 dòng trên dữ
    # liệu thật) rồi mỗi dòng lại nạp thêm tour của nó – vừa chậm vừa là một trong những chỗ ngốn hết
    # 512 MB bộ nhớ máy chủ khi mở trang Tổng quan.
    con_thu = (Booking.amount - Booking.discount - Booking.paid)
    for start_date, due in db.execute(
            select(Tour.start_date, con_thu)
            .join(Tour, Booking.tour_id == Tour.id)
            .where(Booking.cancelled == False, con_thu > 0,
                   Tour.status.not_in(["huy", "khoa", "kt_xac_nhan", "da_dong_so"]))).all():
        put(max(date.today(), start_date - timedelta(days=7)), "in", "thu_booking", float(due))
    # Chi tour: lệnh chi chờ (tuần này) và đề nghị đang trình (tuần sau); chi dự toán còn lại của tour sắp chạy
    for pr in db.execute(select(PaymentRequest).where(PaymentRequest.status.in_(["cho_chi", "cho_tp", "cho_kt", "cho_duyet"]))).scalars():
        put(date.today() if pr.status == "cho_chi" else date.today() + timedelta(days=7), "out", "chi_ncc", pr.amount)
    # Chi dự toán còn lại của tour sắp chạy. Bản cũ gọi tour_cashflow() cho TỪNG tour đã duyệt: mỗi lần
    # là ba chuyến đi–về tới cơ sở dữ liệu ở Singapore cộng một lần nạp lười danh sách booking. Với vài
    # trăm tour đang mở, riêng vòng lặp này đã là hàng nghìn chuyến đi–về, mà kết quả chỉ cần đúng MỘT
    # con số mỗi tour. Nay cộng đề nghị chi theo tour bằng một câu lệnh GROUP BY, và số khách cũng lấy
    # sẵn theo tour thay vì đi qua quan hệ.
    tours_dd = list(db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars())
    if tours_dd:
        ids = [t.id for t in tours_dd]
        da_dung: dict[int, float] = {}
        for tid, amt in db.execute(
                select(PaymentRequest.tour_id, func.coalesce(func.sum(PaymentRequest.amount), 0.0))
                .where(PaymentRequest.tour_id.in_(ids),
                       PaymentRequest.status.in_(["da_chi", "cho_chi", "cho_tp", "cho_kt", "cho_duyet"]))
                .group_by(PaymentRequest.tour_id)).all():
            da_dung[tid] = float(amt)
        khach: dict[int, int] = {}
        for tid, n in db.execute(select(Booking.tour_id, func.coalesce(func.sum(Booking.pax), 0))
                                 .where(Booking.tour_id.in_(ids), Booking.cancelled == False)
                                 .group_by(Booking.tour_id)).all():
            khach[tid] = int(n)
        for t in tours_dd:
            budget = t.fixed_cost + t.var_cost_per_pax * max(t.planned_pax, khach.get(t.id, 0))
            rest = budget - da_dung.get(t.id, 0.0)
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


# ---------- Bản đồ vay – tài sản thế chấp là xe (hồ sơ khế ước 12 xe, 07/9/2026) ----------
# Ba câu hỏi phải trả lời được ngay, vì mỗi câu là một rủi ro có thật trong hồ sơ hiện tại:
#   1. Chiếc xe đã bán/đã giao có còn nằm trong tài sản bảo đảm của khế ước nào không?
#   2. Khế ước nào sắp đáo hạn, khế ước nào hồ sơ không ghi ngày đáo hạn?
#   3. Xe đang khai thác nào không xuất hiện trong bất kỳ tài sản bảo đảm nào – đã giải chấp hay thiếu hồ sơ?
# Câu 3 cố tình KHÔNG kết luận "đã giải chấp": không thấy trong danh sách không có nghĩa là đã được rút ra.
def _muc_do(con_ngay):
    if con_ngay is None: return "thieu_du_lieu"
    if con_ngay < 0: return "qua_han"
    if con_ngay <= 30: return "gap"
    if con_ngay <= 120: return "theo_doi"
    return "binh_thuong"


def vay_xe(db: Session, hom_nay: date | None = None) -> dict:
    from app.models.fleet import Collateral, SaleCase
    from app.models.hr import Vehicle
    from app.models.core import Company
    today = hom_nay or date.today()
    cty = {c.id: c.name for c in db.execute(select(Company)).scalars()}
    xe = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    tc = list(db.execute(select(Collateral)).scalars())
    # Loại khoản vay KHÔNG thuộc đội xe. Sao kê ngân hàng gộp chung vay bất động sản và vay vốn lưu động;
    # kéo hết vào đây thì "nợ của đội xe" thành một con số không ai dùng được.
    #
    # Quy tắc là LOẠI TRỪ chứ không phải chọn vào: chỉ khế ước được xếp rõ là bất động sản / vốn lưu động /
    # khác mới bị bỏ ra. Khế ước chưa ai xếp nhóm vẫn hiện. Làm ngược lại – chỉ hiện khi đã xếp nhóm – thì
    # một khoản vay quên xếp nhóm sẽ biến mất khỏi màn hình cùng với mọi cảnh báo của nó, và không ai biết.
    NGOAI_DOI_XE = {"von_luu_dong", "bds", "khac"}
    loans = [c for c in db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars()
             if (c.loan_group or "").strip() not in NGOAI_DOI_XE]
    theo_ke_uoc: dict[int, list] = {}
    for c in tc: theo_ke_uoc.setdefault(c.contract_id, []).append(c)

    ke_uoc, canh_bao, gan_xe = [], [], {}
    for c in loans:
        rows = [t for t in theo_ke_uoc.get(c.id, []) if t.den_ngay is None]
        da_giai = [t for t in theo_ke_uoc.get(c.id, []) if t.den_ngay is not None]
        lai_thang = round(c.outstanding * (c.interest_rate / 100) / 12) if c.interest_rate else 0
        con = (c.maturity - today).days if c.maturity else None
        # Dư nợ phân bổ cho từng xe chỉ để tham khảo: ngân hàng nắm CẢ GÓI, giải chấp một xe
        # phải thoả thuận riêng, nên con số này không phải nghĩa vụ riêng của chiếc xe đó.
        pb = round(c.outstanding / len(rows)) if rows else 0
        for t in rows:
            gan_xe.setdefault(t.vehicle_id, []).append({"contract_id": c.id, "code": c.code, "contract_no": c.contract_no, "partner": c.partner,
                                                        "du_no": c.outstanding, "so_xe_trong_goi": len(rows), "du_no_phan_bo": pb,
                                                        "lai_thang_phan_bo": round(lai_thang / len(rows)) if rows else 0,
                                                        "collateral_id": t.id, "maturity": c.maturity})
        ke_uoc.append({"id": c.id, "code": c.code, "contract_no": c.contract_no, "partner": c.partner, "entity": c.entity,
                       "nhom": (c.loan_group or "").strip(),
                       "company": cty.get(c.company_id, "") if getattr(c, "company_id", None) else c.entity,
                       "du_no": c.outstanding, "lai_suat": c.interest_rate, "lai_thang": lai_thang,
                       "maturity": c.maturity, "con_ngay": con, "muc_do": _muc_do(con),
                       "xe_the_chap": [xe[t.vehicle_id].plate for t in rows if t.vehicle_id in xe],
                       "xe_da_giai_chap": [xe[t.vehicle_id].plate for t in da_giai if t.vehicle_id in xe],
                       "collateral": c.collateral, "status": c.status})
        if con is not None and con <= 30:
            canh_bao.append({"muc": "gap", "loai": "dao_han", "khe_uoc": c.code,
                             "noi_dung": f"Khế ước {c.contract_no or c.code} ({c.partner}) dư nợ {c.outstanding:,.0f}đ đáo hạn {c.maturity:%d/%m/%Y}"
                                         + (f" – còn {con} ngày" if con >= 0 else f" – ĐÃ QUÁ HẠN {-con} ngày"),
                             "viec": "Chuẩn bị nguồn tất toán hoặc hồ sơ gia hạn"})
        if not c.maturity:
            canh_bao.append({"muc": "thieu_du_lieu", "loai": "thieu_ngay_dao_han", "khe_uoc": c.code,
                             "noi_dung": f"Khế ước {c.contract_no or c.code} ({c.partner}) dư nợ {c.outstanding:,.0f}đ không có ngày đáo hạn trong hồ sơ",
                             "viec": "Đề nghị ngân hàng xác nhận lịch trả nợ và ngày đáo hạn"})

    # Xe đã bán / thanh lý / dừng khai thác mà vẫn còn là tài sản bảo đảm – rủi ro cao nhất.
    for vid, ds in gan_xe.items():
        v = xe.get(vid)
        if v is None: continue
        # Xét CẢ hai dấu hiệu. Một chiếc xe bị ngưng khai thác mà vòng đời chưa ai cập nhật vẫn là xe
        # đã ra khỏi đội trên thực tế – 50F-034.37 đã giao ngày 10/08 chính là trường hợp đó, và nếu chỉ
        # nhìn vòng đời thì cảnh báo quan trọng nhất lại im lặng đúng lúc cần kêu.
        ra_khoi_doi = (v.lifecycle and v.lifecycle != "dang_khai_thac") or not v.active
        if ra_khoi_doi:
            trang_thai = v.lifecycle if v.lifecycle and v.lifecycle != "dang_khai_thac" else "đã ngưng khai thác, vòng đời chưa cập nhật"
            # Hồ sơ bán xe đi kèm: tiền còn phải thu và hạn thu đủ thuộc CÙNG một câu chuyện với việc
            # xe còn nằm trong tài sản bảo đảm. Tách ra hai chỗ thì người đọc phải tự ghép, và thường là không ghép.
            sc = db.execute(select(SaleCase).where(SaleCase.vehicle_id == vid).order_by(SaleCase.id.desc())).scalars().first()
            them, ban = "", None
            if sc is not None:
                con_thu = (sc.gia_ban or 0) - (sc.da_thu or 0)
                ban = {"nguoi_mua": sc.nguoi_mua, "gia_ban": sc.gia_ban, "da_thu": sc.da_thu, "con_phai_thu": con_thu,
                       "han_thu_du": sc.han_thu_du, "da_giai_chap": sc.da_giai_chap, "da_sang_ten": sc.da_sang_ten,
                       "qua_han_thu": bool(sc.han_thu_du and con_thu > 0 and sc.han_thu_du < today)}
                if con_thu > 0:
                    them = (f". Người mua {sc.nguoi_mua or 'chưa ghi tên'} còn phải thu {con_thu:,.0f}đ"
                            + (f", cam kết trả đủ {sc.han_thu_du:%d/%m/%Y}" if sc.han_thu_du else ", chưa có mốc cam kết trả đủ")
                            + (" – ĐÃ QUÁ HẠN" if ban["qua_han_thu"] else ""))
            for g in ds:
                canh_bao.append({"muc": "gap", "loai": "xe_da_ra_khoi_doi_van_the_chap", "khe_uoc": g["code"], "xe": v.plate, "ban_xe": ban,
                                 "collateral_id": g["collateral_id"],
                                 "noi_dung": f"Xe {v.plate} trạng thái '{trang_thai}' nhưng vẫn là tài sản bảo đảm của khế ước {g['contract_no'] or g['code']} ({g['partner']}, dư nợ {g['du_no']:,.0f}đ)" + them,
                                 "viec": "Xin văn bản giải chấp riêng của ngân hàng trước khi sang tên, hoặc tất toán khế ước"})

    # Xe đang khai thác không gắn khế ước nào.
    thieu_ho_so = [{"xe": v.plate, "id": v.id, "phap_nhan": cty.get(v.company_id, ""), "doi_xe": getattr(v, "code", "")}
                   for v in xe.values() if v.active and (not v.lifecycle or v.lifecycle == "dang_khai_thac") and v.id not in gan_xe]
    if thieu_ho_so:
        canh_bao.append({"muc": "som", "loai": "xe_khong_thuoc_khe_uoc_nao",
                         "noi_dung": f"{len(thieu_ho_so)} xe đang khai thác không xuất hiện trong tài sản bảo đảm của bất kỳ khế ước nào: "
                                     + ", ".join(x["xe"] for x in thieu_ho_so[:12]),
                         "viec": "Rà soát: đã giải chấp thật (có văn bản) hay chỉ là thiếu hồ sơ. Không thấy trong danh sách KHÔNG có nghĩa là đã được rút khỏi tài sản bảo đảm"})

    thu_tu = {"qua_han": 0, "gap": 1, "thieu_du_lieu": 2, "som": 3, "theo_doi": 4}
    canh_bao.sort(key=lambda x: thu_tu.get(x["muc"], 9))
    # Xe ngoài đội 45 chỗ (Ford, Transit, KIA…) là vay xe thật nhưng không thuộc 12 xe khách đang
    # theo dõi. Không giấu đi – giấu thì mất dấu một khoản nợ có tài sản là xe – nhưng để riêng, và
    # TỔNG ở đầu màn hình chỉ cộng nhóm 12 xe, đúng con số lãnh đạo hỏi.
    def _sap(ds): return sorted(ds, key=lambda k: (k["con_ngay"] is None, k["con_ngay"] if k["con_ngay"] is not None else 0))
    nhom_chinh = [k for k in ke_uoc if k["nhom"] != "vay_xe_khac"]
    nhom_khac = [k for k in ke_uoc if k["nhom"] == "vay_xe_khac"]
    theo_phap_nhan = {}
    for k in nhom_chinh:
        t = theo_phap_nhan.setdefault(k["company"] or k["entity"] or "Chưa gán pháp nhân", {"so_khe_uoc": 0, "du_no": 0.0, "lai_thang": 0.0})
        t["so_khe_uoc"] += 1; t["du_no"] += k["du_no"]; t["lai_thang"] += k["lai_thang"]
    return {"as_of": today,
            "ke_uoc": _sap(nhom_chinh),
            "ke_uoc_xe_ngoai_doi": _sap(nhom_khac),
            "tong_du_no_xe_ngoai_doi": sum(k["du_no"] for k in nhom_khac),
            "tong_lai_thang_xe_ngoai_doi": sum(k["lai_thang"] for k in nhom_khac),
            "xe": sorted(([{"id": v.id, "plate": v.plate, "phap_nhan": cty.get(v.company_id, ""), "lifecycle": v.lifecycle,
                            "active": v.active, "khe_uoc": gan_xe.get(v.id, [])} for v in xe.values()]), key=lambda r: r["plate"]),
            "canh_bao": canh_bao, "thieu_ho_so": thieu_ho_so,
            "tong_du_no": sum(k["du_no"] for k in nhom_chinh), "tong_lai_thang": sum(k["lai_thang"] for k in nhom_chinh),
            "theo_phap_nhan": theo_phap_nhan}


# ---------- Đối chiếu sao kê khoản vay của ngân hàng với khế ước đang theo dõi ----------
# Ba câu trả lời, không gộp làm một, vì ba câu đó dẫn tới ba việc khác nhau:
#   khớp nhưng LỆCH SỐ   → cập nhật dư nợ (hồ sơ nội bộ trễ so với ngân hàng là bình thường)
#   hệ thống CÓ, sao kê KHÔNG → nghi đã tất toán hoặc khoản vay nằm ở pháp nhân/CIF khác. KHÔNG tự đóng.
#   sao kê CÓ, hệ thống KHÔNG → khoản vay ngân hàng đang cho vay mà mình chưa theo dõi
def doi_chieu_sao_ke(db: Session, dong: list[dict], ngan_hang: str = "", den_ngay: date | None = None,
                     phap_nhan: str = "") -> dict:
    """`dong`: mỗi dòng {ke_uoc, du_no, lai_suat?, dao_han?, giai_ngan?, muc_dich?, loai?}.

    Chỉ SO SÁNH và báo cáo, không sửa gì – cập nhật là một bước riêng có người bấm, vì một dòng sao kê
    đọc sai định dạng mà tự ghi đè dư nợ thì sổ sách sai theo mà không ai biết.
    """
    loans = {c.contract_no.strip(): c for c in
             db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars()
             if (c.contract_no or "").strip()}
    khop, lech, chua_theo_doi, ngoai_pham_vi = [], [], [], []
    thay = set()
    for r in dong:
        ma = str(r.get("ke_uoc") or "").strip()
        if not ma: continue
        c = loans.get(ma)
        sk_du_no = float(r.get("du_no") or 0)
        if c is None:
            # Dòng sao kê không có trong hệ thống có hai nghĩa rất khác nhau: khoản vay mua xe bị bỏ sót
            # (phải nạp), hay khoản vay bất động sản / vốn lưu động vốn không thuộc phạm vi theo dõi vay xe
            # (không phải nạp). Gộp làm một thì việc thật chìm trong danh sách 51 dòng không phải việc.
            muc = {"ke_uoc": ma, "du_no": sk_du_no, "lai_suat": r.get("lai_suat"),
                   "dao_han": r.get("dao_han"), "muc_dich": r.get("muc_dich", ""), "loai": r.get("loai", "")}
            (ngoai_pham_vi if str(r.get("nhom") or "").strip() in ("von_luu_dong", "bds", "khac") else chua_theo_doi).append(muc)
            continue
        thay.add(ma)
        sai = []
        if abs(c.outstanding - sk_du_no) >= 1:
            sai.append({"truong": "du_no", "he_thong": c.outstanding, "sao_ke": sk_du_no, "chenh": sk_du_no - c.outstanding})
        ls = r.get("lai_suat")
        if ls is not None and abs(float(ls) - c.interest_rate) >= 0.01:
            sai.append({"truong": "lai_suat", "he_thong": c.interest_rate, "sao_ke": float(ls)})
        dh = r.get("dao_han")
        if dh and str(c.maturity or "") != str(dh):
            sai.append({"truong": "dao_han", "he_thong": str(c.maturity or "chưa có"), "sao_ke": str(dh)})
        (lech if sai else khop).append({"ke_uoc": ma, "code": c.code, "partner": c.partner, "entity": c.entity,
                                        "du_no_he_thong": c.outstanding, "du_no_sao_ke": sk_du_no, "sai_lech": sai})
    # Khế ước hệ thống đang theo dõi ở ngân hàng NÀY mà sao kê không có dòng nào.
    nh = (ngan_hang or "").strip().lower()
    khong_thay = [{"ke_uoc": ma, "code": c.code, "partner": c.partner, "entity": c.entity, "du_no_he_thong": c.outstanding,
                   "the_chap": c.collateral,
                   "y_nghia": "Không có trên sao kê – có thể đã tất toán, hoặc khoản vay thuộc pháp nhân/CIF khác. "
                              "Phải có xác nhận của ngân hàng mới được đóng khế ước và giải chấp xe."}
                  for ma, c in loans.items()
                  if ma not in thay and (not nh or nh in (c.partner or "").lower())]
    return {"ngan_hang": ngan_hang, "phap_nhan": phap_nhan, "den_ngay": den_ngay or date.today(),
            "so_dong_sao_ke": len([r for r in dong if str(r.get("ke_uoc") or "").strip()]),
            "tong_sao_ke": sum(float(r.get("du_no") or 0) for r in dong),
            "khop": khop, "lech": lech, "khong_thay_tren_sao_ke": khong_thay, "chua_theo_doi": chua_theo_doi,
            "tong_chua_theo_doi": sum(x["du_no"] for x in chua_theo_doi),
            "ngoai_pham_vi": ngoai_pham_vi, "tong_ngoai_pham_vi": sum(x["du_no"] for x in ngoai_pham_vi),
            "tom_tat": f"{len(khop)} khế ước khớp, {len(lech)} lệch số, {len(khong_thay)} khế ước hệ thống có mà sao kê không có, "
                       f"{len(chua_theo_doi)} khoản vay chưa theo dõi"
                       + (f", {len(ngoai_pham_vi)} khoản ngoài phạm vi theo dõi vay xe (cộng {sum(x['du_no'] for x in ngoai_pham_vi):,.0f}đ)" if ngoai_pham_vi else "")}
