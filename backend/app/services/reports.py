"""Báo cáo tài chính (TT99/2025) và tờ khai thuế – robot R5/R7.

- Số dư theo tài khoản tính từ chứng từ đã ghi sổ (không dùng số nháp).
- BCĐKT (B01-DN), KQKD (B02-DN), LCTT trực tiếp (B03-DN) dạng rút gọn theo nhóm tài khoản cấp 1 – Kế toán trưởng
  đối chiếu mẫu đầy đủ của Thông tư trước khi nộp. Kết chuyển cuối kỳ (911) do robot lập NHÁP, KTT ghi sổ.
- Tờ khai GTGT (01/GTGT) và TNCN từ sổ; xuất XML cấu trúc đơn giản để nạp HTKK/eTax – KTT kiểm tra, ký số, nộp.
"""
from datetime import date
from xml.sax.saxutils import escape
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.accounting import Account, JournalEntry, JournalLine, Invoice
from app.services import accounting as ACC
from app.services import rules as R

CASH = ("111", "112")
PL_REVENUE = ("511", "515", "711")
PL_EXPENSE = ("632", "635", "641", "642", "811", "821")


def _lines(db: Session, upto_period: str | None = None, period: str | None = None):
    q = select(JournalLine, JournalEntry).join(JournalEntry).where(JournalEntry.status == "da_ghi_so")
    rows = db.execute(q).all()
    if period:
        rows = [(l, e) for l, e in rows if e.period == period]
    elif upto_period:
        rows = [(l, e) for l, e in rows if e.period <= upto_period]
    return rows


def _cong_theo_tk(db: Session, upto_period: str | None = None, period: str | None = None):
    """Cộng Nợ/Có theo tài khoản cấp 1 BẰNG SQL, không nạp bút toán vào bộ nhớ.

    Bản cũ dùng _lines(): nạp TOÀN BỘ JournalLine + JournalEntry thành đối tượng Python rồi mới lọc kỳ.
    Trên dữ liệu thật (25.728 chứng từ, hàng chục nghìn dòng) việc đó ngốn hết 512 MB của máy chủ và
    tiến trình bị hệ điều hành kết liễu giữa chừng – bảng điều khiển gọi hàm này HAI lần (số dư và
    kết quả kinh doanh), nên mỗi lần ai đó mở trang Tổng quan là một lần cả hệ thống khởi động lại.
    Nay cơ sở dữ liệu cộng sẵn, trả về vài chục dòng.
    """
    q = (select(func.substr(JournalLine.account_code, 1, 3),
                func.coalesce(func.sum(JournalLine.debit), 0.0),
                func.coalesce(func.sum(JournalLine.credit), 0.0))
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == "da_ghi_so"))
    if period: q = q.where(JournalEntry.period == period)
    elif upto_period: q = q.where(JournalEntry.period <= upto_period)
    return db.execute(q.group_by(func.substr(JournalLine.account_code, 1, 3))).all()


def balances(db: Session, upto_period: str) -> dict[str, float]:
    """Số dư (Nợ − Có) lũy kế đến hết kỳ theo tài khoản cấp 1 (gộp tiểu khoản 3331→333, 3387→338)."""
    return {k: float(d) - float(c) for k, d, c in _cong_theo_tk(db, upto_period=upto_period)}


def movements(db: Session, period: str) -> dict[str, dict]:
    return {k: {"debit": float(d), "credit": float(c)} for k, d, c in _cong_theo_tk(db, period=period)}


def balance_sheet(db: Session, period: str) -> dict:
    """B01-DN rút gọn. Lãi/lỗ chưa kết chuyển của các kỳ chưa khóa sổ được cộng vào 421 để bảng cân."""
    b = balances(db, period)
    g = lambda *codes: sum(b.get(c, 0.0) for c in codes)
    pl_open = sum(-b.get(c, 0.0) for c in PL_REVENUE) - sum(b.get(c, 0.0) for c in PL_EXPENSE)   # lãi chưa kết chuyển (dư 5xx Có, 6xx Nợ)
    assets = [
        ("110", "Tiền và tương đương tiền", g("111", "112")),
        ("131", "Phải thu ngắn hạn của khách hàng", max(0.0, g("131"))),
        ("133", "Thuế GTGT được khấu trừ", g("133")),
        ("138", "Phải thu khác, tạm ứng", g("138", "141")),
        ("154", "Chi phí SXKD dở dang (tour)", g("154")),
        ("242", "Chi phí trả trước", g("242")),
        ("211", "Tài sản cố định (nguyên giá − hao mòn)", g("211") + g("214")),
    ]
    liabilities = [
        ("331", "Phải trả người bán", max(0.0, -g("331"))),
        ("131b", "Người mua trả tiền trước", max(0.0, -g("131"))),
        ("333", "Thuế và các khoản phải nộp Nhà nước", -g("333")),
        ("334", "Phải trả người lao động", -g("334")),
        ("335", "Chi phí phải trả", -g("335")),
        ("338", "Phải trả khác, doanh thu chưa thực hiện", -g("338")),
        ("341", "Vay và nợ thuê tài chính", -g("341")),
    ]
    equity = [
        ("411", "Vốn góp của chủ sở hữu", -g("411")),
        ("421", "Lợi nhuận sau thuế chưa phân phối (gồm lãi/lỗ kỳ chưa kết chuyển)", -g("421") + pl_open),
    ]
    ta = sum(x[2] for x in assets); tl = sum(x[2] for x in liabilities); te = sum(x[2] for x in equity)
    return {"period": period, "assets": assets, "liabilities": liabilities, "equity": equity, "total_assets": ta, "total_liabilities": tl, "total_equity": te,
            "balanced": abs(ta - tl - te) < 1, "unposted_pl": pl_open}


def income_statement(db: Session, period: str) -> dict:
    """B02-DN rút gọn theo kỳ (tháng). Lãi vay và khấu hao tách riêng theo yêu cầu BCKQKD tháng (Điều 5 KT-HCNS)."""
    m = movements(db, period)
    rev = lambda c: m.get(c, {}).get("credit", 0.0) - m.get(c, {}).get("debit", 0.0)
    exp = lambda c: m.get(c, {}).get("debit", 0.0) - m.get(c, {}).get("credit", 0.0)
    revenue, cogs = rev("511"), exp("632")
    gross = revenue - cogs
    fin_in, fin_exp = rev("515"), exp("635")
    selling, admin = exp("641"), exp("642")
    op = gross + fin_in - fin_exp - selling - admin
    other = rev("711") - exp("811")
    ebt = op + other
    tax = exp("821")
    # khấu hao trong kỳ = phát sinh Có 214
    dep = m.get("214", {}).get("credit", 0.0)
    return {"period": period, "rows": [
        ("01", "Doanh thu bán hàng và cung cấp dịch vụ", revenue), ("11", "Giá vốn hàng bán", cogs), ("20", "Lợi nhuận gộp", gross),
        ("21", "Doanh thu hoạt động tài chính", fin_in), ("22", "Chi phí tài chính (trong đó lãi vay)", fin_exp), ("25", "Chi phí bán hàng", selling),
        ("26", "Chi phí quản lý doanh nghiệp", admin), ("30", "Lợi nhuận thuần từ HĐKD", op), ("40", "Lợi nhuận khác", other),
        ("50", "Tổng lợi nhuận kế toán trước thuế", ebt), ("51", "Chi phí thuế TNDN", tax), ("60", "Lợi nhuận sau thuế", ebt - tax)],
        "management": {"interest": fin_exp, "depreciation": dep, "profit_after_interest_before_dep": ebt + dep,
                       "note": "Lợi nhuận Công ty dùng tính thưởng GĐ KD = sau lãi vay, trước khấu hao (BCKQKD tháng TGĐ duyệt)"}}


def cash_flow(db: Session, period: str) -> dict:
    """B03-DN phương pháp trực tiếp: phân loại dòng tiền theo tài khoản đối ứng của 111/112 trong từng chứng từ."""
    rows = _lines(db, period=period)
    by_entry: dict[int, list] = {}
    for l, e in rows:
        by_entry.setdefault(e.id, []).append(l)
    buckets = {"thu_khach": 0.0, "chi_ncc": 0.0, "chi_nld": 0.0, "chi_thue": 0.0, "chi_khac": 0.0, "thu_khac": 0.0, "dau_tu": 0.0, "vay": 0.0, "tra_no": 0.0}
    for lines in by_entry.values():
        cash_net = sum((l.debit or 0) - (l.credit or 0) for l in lines if l.account_code[:3] in CASH)
        if abs(cash_net) < 1: continue
        others = [l.account_code[:3] for l in lines if l.account_code[:3] not in CASH]
        a = others[0] if others else ""
        if cash_net > 0:
            if a == "131": buckets["thu_khach"] += cash_net
            elif a == "341": buckets["vay"] += cash_net
            elif a in ("211", "222", "128"): buckets["dau_tu"] += cash_net
            else: buckets["thu_khac"] += cash_net
        else:
            v = -cash_net
            if a in ("331", "154", "335"): buckets["chi_ncc"] += v
            elif a in ("334", "338"): buckets["chi_nld"] += v
            elif a == "333": buckets["chi_thue"] += v
            elif a == "341": buckets["tra_no"] += v
            elif a in ("211", "222", "128"): buckets["dau_tu"] += v
            else: buckets["chi_khac"] += v
    op = buckets["thu_khach"] + buckets["thu_khac"] - buckets["chi_ncc"] - buckets["chi_nld"] - buckets["chi_thue"] - buckets["chi_khac"]
    inv = -buckets["dau_tu"]
    fin = buckets["vay"] - buckets["tra_no"]
    b_prev = balances(db, prev_period(period)); b_now = balances(db, period)
    open_cash = sum(b_prev.get(c, 0.0) for c in CASH); close_cash = sum(b_now.get(c, 0.0) for c in CASH)
    return {"period": period, "rows": [
        ("01", "Tiền thu từ bán hàng, cung cấp dịch vụ", buckets["thu_khach"]), ("02", "Tiền chi trả cho người cung cấp", -buckets["chi_ncc"]),
        ("03", "Tiền chi trả cho người lao động", -buckets["chi_nld"]), ("05", "Thuế đã nộp", -buckets["chi_thue"]), ("06", "Tiền thu khác", buckets["thu_khac"]),
        ("07", "Tiền chi khác", -buckets["chi_khac"]), ("20", "Lưu chuyển tiền thuần từ HĐKD", op), ("30", "Lưu chuyển tiền thuần từ hoạt động đầu tư", inv),
        ("33", "Tiền thu từ đi vay", buckets["vay"]), ("34", "Tiền trả nợ gốc vay", -buckets["tra_no"]), ("40", "Lưu chuyển tiền thuần từ hoạt động tài chính", fin),
        ("50", "Lưu chuyển tiền thuần trong kỳ", op + inv + fin), ("60", "Tiền đầu kỳ", open_cash), ("70", "Tiền cuối kỳ", close_cash)],
        "reconciled": abs(open_cash + op + inv + fin - close_cash) < 1}


def prev_period(p: str) -> str:
    y, m = map(int, p.split("-"))
    return f"{y-1}-12" if m == 1 else f"{y}-{m-1:02d}"


# ---------- Kết chuyển cuối kỳ (911) – robot lập nháp ----------
def closing_entries_draft(db: Session, u: User, period: str) -> list[JournalEntry]:
    if db.execute(select(JournalEntry).where(JournalEntry.period == period, JournalEntry.source_type == "ket_chuyen")).scalars().first():
        raise ValueError(f"Kỳ {period} đã có chứng từ kết chuyển")
    m = movements(db, period)
    y, mm = map(int, period.split("-"))
    last = date(y + (mm == 12), (mm % 12) + 1, 1)
    from datetime import timedelta
    d = last - timedelta(days=1)
    out = []
    lines_rev = []; lines_exp = []
    for c in PL_REVENUE:
        v = m.get(c, {}).get("credit", 0.0) - m.get(c, {}).get("debit", 0.0)
        if v: lines_rev.append({"account": c, "debit": v})
    for c in PL_EXPENSE:
        v = m.get(c, {}).get("debit", 0.0) - m.get(c, {}).get("credit", 0.0)
        if v: lines_exp.append({"account": c, "credit": v})
    tr = sum((l["debit"] or 0) for l in lines_rev); te = sum((l["credit"] or 0) for l in lines_exp)
    if tr: out.append(ACC.post_entry(db, u.username, u.role, d, f"Kết chuyển doanh thu kỳ {period} sang 911", lines_rev + [{"account": "911", "credit": tr}], "ket_chuyen", f"period:{period}", post=False))
    if te: out.append(ACC.post_entry(db, u.username, u.role, d, f"Kết chuyển chi phí kỳ {period} sang 911", [{"account": "911", "debit": te}] + lines_exp, "ket_chuyen", f"period:{period}", post=False))
    net = tr - te
    if abs(net) >= 1:
        ln = [{"account": "911", "debit": net}, {"account": "421", "credit": net}] if net > 0 else [{"account": "421", "debit": -net}, {"account": "911", "credit": -net}]
        out.append(ACC.post_entry(db, u.username, u.role, d, f"Kết chuyển lãi/lỗ kỳ {period}: {net:,.0f}", ln, "ket_chuyen", f"period:{period}", post=False))
    db.commit()
    return out


# ---------- Tờ khai thuế ----------
def vat_return(db: Session, period: str) -> dict:
    """01/GTGT theo tháng: đầu ra từ hóa đơn phát hành, đầu vào từ 133 (đề nghị chi có hóa đơn – nhập bổ sung khi có hóa đơn đầu vào)."""
    invs = [i for i in db.execute(select(Invoice).where(Invoice.status == "da_phat_hanh")).scalars() if i.issue_date and f"{i.issue_date:%Y-%m}" == period]
    out_pre = sum((i.pre_tax or 0) for i in invs); out_vat = sum((i.vat or 0) for i in invs)
    m = movements(db, period)
    in_vat = m.get("133", {}).get("debit", 0.0) - m.get("133", {}).get("credit", 0.0)
    b_prev = balances(db, prev_period(period))
    carry = max(0.0, b_prev.get("133", 0.0))          # thuế đầu vào còn được khấu trừ kỳ trước chuyển sang
    payable = out_vat - in_vat - carry
    return {"period": period, "form": "01/GTGT", "invoices": len(invs),
            "rows": [("[22]", "Thuế GTGT còn được khấu trừ kỳ trước chuyển sang", carry), ("[23]", "Giá trị HHDV mua vào", 0.0), ("[24]", "Thuế GTGT mua vào", in_vat),
                     ("[29]", "HHDV bán ra chịu thuế – doanh thu chưa thuế", out_pre), ("[33]", "Thuế GTGT của HHDV bán ra", out_vat),
                     ("[36]", "Thuế GTGT phát sinh trong kỳ", out_vat - in_vat), ("[40]", "Thuế GTGT còn phải nộp trong kỳ", max(0.0, payable)),
                     ("[43]", "Thuế GTGT còn được khấu trừ chuyển kỳ sau", max(0.0, -payable))],
            "note": "Doanh thu bán ra lấy từ hóa đơn điện tử đã phát hành; thuế đầu vào lấy từ TK 133 – Kế toán nhập hóa đơn đầu vào (robot R5 đọc XML) trước khi lập tờ khai."}


def pit_return(db: Session, period: str) -> dict:
    """05/KK-TNCN rút gọn: thuế TNCN khấu trừ trong kỳ từ TK 3335 (10% thù lao CTV/HDV; lương theo biểu lũy tiến – HCNS bổ sung)."""
    m = movements(db, period)
    withheld = m.get("333", {}).get("credit", 0.0)  # cấp 1 gộp; tách 3335
    w3335 = float(db.execute(
        select(func.coalesce(func.sum(func.coalesce(JournalLine.credit, 0) - func.coalesce(JournalLine.debit, 0)), 0.0))
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .where(JournalEntry.status == "da_ghi_so", JournalEntry.period == period,
               JournalLine.account_code == "3335")).scalar() or 0)
    return {"period": period, "form": "05/KK-TNCN", "rows": [("[27]", "Tổng số thuế TNCN đã khấu trừ (thu nhập từ tiền lương, tiền công; CTV 10%)", w3335)],
            "note": "Thuế TNCN của người lao động theo biểu lũy tiến chưa tính tự động – HCNS/Kế toán bổ sung trước khi nộp."}


def to_xml(ret: dict, tax_code: str = "", company: str = "CÔNG TY CỔ PHẦN DU LỊCH VIETOURIST") -> str:
    """XML cấu trúc đơn giản (mã chỉ tiêu → giá trị) để nhập HTKK/eTax; KTT kiểm tra cấu trúc theo phiên bản HTKK hiện hành trước khi nộp."""
    y, m = ret["period"].split("-")
    rows = "".join(f'    <ChiTieu ma="{escape(code.strip("[]"))}" ten="{escape(name)}">{round(val)}</ChiTieu>\n' for code, name, val in ret["rows"])
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">\n  <TTinChung>\n    <maSoThue>{escape(tax_code)}</maSoThue>\n'
            f'    <tenNNT>{escape(company)}</tenNNT>\n    <maTKhai>{escape(ret["form"])}</maTKhai>\n    <kyKKhai>{m}/{y}</kyKKhai>\n    <loaiTKhai>C</loaiTKhai>\n  </TTinChung>\n'
            f'  <CTieuTKhaiChinh>\n{rows}  </CTieuTKhaiChinh>\n</HSoThueDTu>\n')
