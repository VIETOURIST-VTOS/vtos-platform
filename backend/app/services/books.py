"""Sổ kế toán chuẩn theo chế độ kế toán doanh nghiệp – bố cục như bản in của MISA.

Gồm các sổ Kế toán phải xuất trình khi quyết toán thuế / kiểm toán, mà VTOS trước đây mới chỉ có Nhật ký chung:
  - Sổ Nhật ký chung (S03a-DN)
  - Sổ Cái tài khoản (S03b-DN)                 – có cột TK ĐỐI ỨNG, đây là cột MISA luôn in
  - Sổ chi tiết tài khoản (S38-DN)             – thêm cột đối tượng / công trình
  - Sổ quỹ tiền mặt (S07-DN)                   – Thu / Chi / Tồn
  - Sổ tiền gửi ngân hàng (S08-DN)             – theo từng ngân hàng (đối tượng)
  - Sổ chi tiết công nợ phải thu / phải trả (S31-DN, S51-DN) – theo từng đối tượng

Hai quy ước quan trọng, giống MISA:
  1. Sổ của một tài khoản TỔNG (ví dụ 112) gồm phát sinh của TẤT CẢ tài khoản con (1121, 11211…).
     Kế toán mở "Sổ cái 112" là muốn xem cả cây, không phải chỉ dòng ghi thẳng vào 112.
  2. TK đối ứng của một dòng là các tài khoản ở VẾ NGƯỢC LẠI trong cùng chứng từ: dòng ghi Nợ thì đối ứng
     là các tài khoản ghi Có của chứng từ đó và ngược lại. Chứng từ nhiều vế thì liệt kê, phân cách dấu phẩy.

Chỉ lấy chứng từ ĐÃ GHI SỔ (status = "da_ghi_so"); chứng từ nháp không lên sổ.
"""
from datetime import date
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.accounting import Account, JournalEntry, JournalLine, Partner
from app.core.config import settings

CASH_ACCOUNT, BANK_ACCOUNT = "111", "112"
AR_ACCOUNT, AP_ACCOUNT = "131", "331"


# ---------- Nền chung ----------

def account_subtree(db: Session, code: str) -> list[str]:
    """Mã tài khoản và toàn bộ tài khoản con (đi theo cây parent, không dựa vào tiền tố chuỗi)."""
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    if code not in accs:
        raise ValueError(f"Tài khoản {code} không có trong danh mục")
    children: dict[str, list[str]] = {}
    for a in accs.values():
        if a.parent:
            children.setdefault(a.parent, []).append(a.code)
    out, stack = [], [code]
    while stack:
        c = stack.pop()
        out.append(c)
        stack.extend(children.get(c, []))
    return sorted(out)


def _entry_rows(db: Session, upto: date, since: date | None = None):
    """Các dòng đã ghi sổ trong khoảng ngày, kèm chứng từ, sắp theo ngày rồi số chứng từ."""
    q = (select(JournalLine, JournalEntry)
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == "da_ghi_so", JournalEntry.entry_date <= upto))
    if since:
        q = q.where(JournalEntry.entry_date >= since)
    return db.execute(q.order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)).all()


def _contra_map(db: Session, entry_ids: set[int]) -> dict[int, tuple[list[str], list[str]]]:
    """Với mỗi chứng từ: (danh sách TK ghi Nợ, danh sách TK ghi Có) – dùng để suy ra TK đối ứng."""
    if not entry_ids:
        return {}
    out: dict[int, tuple[list[str], list[str]]] = {}
    rows = db.execute(select(JournalLine.entry_id, JournalLine.account_code, JournalLine.debit, JournalLine.credit)
                      .where(JournalLine.entry_id.in_(entry_ids))).all()
    for eid, acc, d, c in rows:
        dr, cr = out.setdefault(eid, ([], []))
        if d and d > 0 and acc not in dr:
            dr.append(acc)
        if c and c > 0 and acc not in cr:
            cr.append(acc)
    return out


def _contra_of(contra: dict, entry_id: int, line: JournalLine) -> str:
    dr, cr = contra.get(entry_id, ([], []))
    other = cr if (line.debit or 0) > 0 else dr
    return ", ".join(a for a in other if a != line.account_code)


def _opening(db: Session, codes: list[str], since: date, partner_code: str = "", project_code: str = "") -> float:
    """Số dư đầu kỳ (thuần Nợ − Có) trước ngày bắt đầu."""
    q = (select(JournalLine, JournalEntry)
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == "da_ghi_so", JournalEntry.entry_date < since,
                JournalLine.account_code.in_(codes)))
    if partner_code:
        q = q.where(JournalLine.partner_code == partner_code)
    if project_code:
        q = q.where(JournalLine.project_code == project_code)
    return round(sum((l.debit or 0) - (l.credit or 0) for l, _ in db.execute(q).all()), 0)


def _head(title: str, since: date, upto: date, extra: str = "") -> list[list]:
    rows = [[settings.COMPANY_NAME], [f"Mã số thuế: {settings.COMPANY_TAX_CODE}"], [title],
            [f"Từ ngày {since:%d/%m/%Y} đến ngày {upto:%d/%m/%Y}"]]
    if extra:
        rows.append([extra])
    rows.append(["Đơn vị tính: VND"])
    return rows


def _write(ws, head_rows: list[list], columns: list[str], widths: list[int], data: list[list], total: list | None = None):
    bold = Font(bold=True, name="Times New Roman")
    for r in head_rows:
        ws.append(r)
    ws.append([])
    ws.append(columns)
    for c in ws[ws.max_row]:
        c.font = bold
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in data:
        ws.append(row)
    if total:
        ws.append(total)
        for c in ws[ws.max_row]:
            c.font = bold
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(ord("A") + i)].width = w


def _book(name: str, head_rows, columns, widths, data, total=None) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = name[:31]
    _write(ws, head_rows, columns, widths, data, total)
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


# ---------- S03a: Sổ Nhật ký chung ----------

def journal_book(db: Session, since: date, upto: date) -> dict:
    rows_raw = _entry_rows(db, upto, since)
    contra = _contra_map(db, {e.id for _, e in rows_raw})
    accs = {a.code: a.name for a in db.execute(select(Account)).scalars()}
    rows, td, tc = [], 0.0, 0.0
    for l, e in rows_raw:
        rows.append({"date": e.entry_date, "code": e.code, "doc_no": l.doc_no, "description": e.description,
                     "account": l.account_code, "account_name": accs.get(l.account_code, ""),
                     "contra": _contra_of(contra, e.id, l), "partner": l.partner, "partner_code": l.partner_code,
                     "project_code": l.project_code, "debit": l.debit, "credit": l.credit,
                     "entry_id": e.id, "source_type": e.source_type})
        td += l.debit or 0; tc += l.credit or 0
    return {"since": since, "upto": upto, "rows": rows,
            "total": {"debit": round(td, 0), "credit": round(tc, 0)},
            "balanced": abs(td - tc) < 1}


def journal_book_xlsx(rep: dict) -> bytes:
    data = [[r["date"], r["code"], r["doc_no"], r["description"], r["account"], r["contra"],
             r["partner"], r["project_code"], r["debit"], r["credit"]] for r in rep["rows"]]
    total = ["", "", "", "TỔNG CỘNG", "", "", "", "", rep["total"]["debit"], rep["total"]["credit"]]
    return _book("SO NHAT KY CHUNG", _head("SỔ NHẬT KÝ CHUNG (Mẫu số S03a-DN)", rep["since"], rep["upto"]),
                 ["Ngày hạch toán", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK", "TK đối ứng",
                  "Đối tượng", "Công trình", "Phát sinh Nợ", "Phát sinh Có"],
                 [15, 16, 14, 46, 10, 14, 30, 16, 16, 16], data, total)


# ---------- S03b / S38: Sổ Cái và Sổ chi tiết tài khoản ----------

def account_book(db: Session, account: str, since: date, upto: date,
                 partner_code: str = "", project_code: str = "", detail: bool = False) -> dict:
    """Sổ Cái (detail=False) hoặc Sổ chi tiết tài khoản (detail=True, có cột đối tượng/công trình).
    Gồm cả tài khoản con; số dư luỹ kế chạy theo thứ tự ngày."""
    acc = db.get(Account, account)
    if not acc:
        raise ValueError(f"Tài khoản {account} không có trong danh mục")
    codes = account_subtree(db, account)
    opening = _opening(db, codes, since, partner_code, project_code)
    rows_raw = [(l, e) for l, e in _entry_rows(db, upto, since)
                if l.account_code in codes
                and (not partner_code or l.partner_code == partner_code)
                and (not project_code or l.project_code == project_code)]
    contra = _contra_map(db, {e.id for _, e in rows_raw})
    bal, rows, td, tc = opening, [], 0.0, 0.0
    for l, e in rows_raw:
        bal += (l.debit or 0) - (l.credit or 0)
        td += l.debit or 0; tc += l.credit or 0
        rows.append({"date": e.entry_date, "code": e.code, "doc_no": l.doc_no, "description": e.description,
                     "account": l.account_code, "contra": _contra_of(contra, e.id, l),
                     "partner": l.partner, "partner_code": l.partner_code, "project_code": l.project_code,
                     "debit": l.debit, "credit": l.credit, "balance": round(bal, 0), "entry_id": e.id})
    return {"account": account, "name": acc.name, "kind": acc.kind, "accounts": codes,
            "since": since, "upto": upto, "partner_code": partner_code, "project_code": project_code,
            "opening": opening, "rows": rows, "detail": detail,
            "total": {"debit": round(td, 0), "credit": round(tc, 0)}, "closing": round(bal, 0)}


def account_book_xlsx(rep: dict) -> bytes:
    title = ("SỔ CHI TIẾT TÀI KHOẢN (Mẫu số S38-DN)" if rep["detail"] else "SỔ CÁI (Mẫu số S03b-DN)")
    extra = f"Tài khoản {rep['account']} – {rep['name']}"
    if rep["partner_code"]:
        extra += f" | Đối tượng: {rep['partner_code']}"
    if rep["project_code"]:
        extra += f" | Công trình: {rep['project_code']}"
    head = _head(title, rep["since"], rep["upto"], extra)
    data = [["", "", "", "Số dư đầu kỳ", "", "", "", "", "", rep["opening"]]] if rep["detail"] else \
           [["", "", "", "Số dư đầu kỳ", "", "", "", rep["opening"]]]
    for r in rep["rows"]:
        if rep["detail"]:
            data.append([r["date"], r["code"], r["doc_no"], r["description"], r["account"], r["contra"],
                         r["partner"], r["project_code"], r["debit"], r["credit"], r["balance"]])
        else:
            data.append([r["date"], r["code"], r["description"], r["account"], r["contra"],
                         r["debit"], r["credit"], r["balance"]])
    if rep["detail"]:
        cols = ["Ngày hạch toán", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK", "TK đối ứng",
                "Đối tượng", "Công trình", "Phát sinh Nợ", "Phát sinh Có", "Số dư"]
        widths = [15, 16, 14, 44, 10, 14, 30, 16, 16, 16, 18]
        total = ["", "", "", "Cộng phát sinh / Số dư cuối kỳ", "", "", "", "",
                 rep["total"]["debit"], rep["total"]["credit"], rep["closing"]]
        data[0] = ["", "", "", "Số dư đầu kỳ", "", "", "", "", "", "", rep["opening"]]
    else:
        cols = ["Ngày hạch toán", "Số chứng từ", "Diễn giải", "TK", "TK đối ứng",
                "Phát sinh Nợ", "Phát sinh Có", "Số dư"]
        widths = [15, 16, 50, 10, 14, 16, 16, 18]
        total = ["", "", "Cộng phát sinh / Số dư cuối kỳ", "", "",
                 rep["total"]["debit"], rep["total"]["credit"], rep["closing"]]
        data[0] = ["", "", "Số dư đầu kỳ", "", "", "", "", rep["opening"]]
    return _book("SO CAI" if not rep["detail"] else "SO CHI TIET TK", head, cols, widths, data, total)


# ---------- S07 / S08: Sổ quỹ tiền mặt và Sổ tiền gửi ngân hàng ----------

def cash_book(db: Session, since: date, upto: date, account: str = CASH_ACCOUNT, partner_code: str = "") -> dict:
    """Sổ quỹ tiền mặt (S07-DN) / Sổ tiền gửi ngân hàng (S08-DN): Thu – Chi – Tồn.
    Với tiền gửi, lọc theo partner_code để ra sổ của TỪNG ngân hàng như MISA in."""
    rep = account_book(db, account, since, upto, partner_code=partner_code)
    bal, rows, tin, tout = rep["opening"], [], 0.0, 0.0
    for r in rep["rows"]:
        amount_in, amount_out = r["debit"] or 0, r["credit"] or 0
        bal += amount_in - amount_out
        tin += amount_in; tout += amount_out
        rows.append({"date": r["date"], "code": r["code"], "doc_no": r["doc_no"], "description": r["description"],
                     "contra": r["contra"], "partner": r["partner"], "partner_code": r["partner_code"],
                     "project_code": r["project_code"], "amount_in": amount_in, "amount_out": amount_out,
                     "balance": round(bal, 0), "entry_id": r["entry_id"]})
    return {"account": account, "name": rep["name"], "since": since, "upto": upto, "partner_code": partner_code,
            "opening": rep["opening"], "rows": rows,
            "total": {"in": round(tin, 0), "out": round(tout, 0)}, "closing": round(bal, 0)}


def cash_book_xlsx(rep: dict) -> bytes:
    is_bank = rep["account"].startswith(BANK_ACCOUNT)
    title = ("SỔ TIỀN GỬI NGÂN HÀNG (Mẫu số S08-DN)" if is_bank else "SỔ QUỸ TIỀN MẶT (Mẫu số S07-DN)")
    extra = f"Tài khoản {rep['account']} – {rep['name']}" + (f" | Ngân hàng: {rep['partner_code']}" if rep["partner_code"] else "")
    data = [["", "", "", "Số dư đầu kỳ", "", "", "", rep["opening"]]]
    for r in rep["rows"]:
        data.append([r["date"], r["code"], r["doc_no"], r["description"], r["contra"],
                     r["amount_in"], r["amount_out"], r["balance"]])
    total = ["", "", "", "Cộng phát sinh / Tồn cuối kỳ", "", rep["total"]["in"], rep["total"]["out"], rep["closing"]]
    return _book("SO TIEN GUI" if is_bank else "SO QUY TIEN MAT",
                 _head(title, rep["since"], rep["upto"], extra),
                 ["Ngày", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK đối ứng",
                  "Thu (Nợ)" if not is_bank else "Gửi vào (Nợ)", "Chi (Có)" if not is_bank else "Rút ra (Có)", "Tồn"],
                 [14, 16, 14, 48, 14, 16, 16, 18], data, total)


def bank_accounts(db: Session, since: date, upto: date) -> list[dict]:
    """Danh sách ngân hàng có phát sinh trên TK 112 trong kỳ – để Kế toán chọn in sổ từng ngân hàng."""
    codes = account_subtree(db, BANK_ACCOUNT)
    names = {p.code: p.name for p in db.execute(select(Partner)).scalars()}
    seen: dict[str, dict] = {}
    for l, e in _entry_rows(db, upto, since):
        if l.account_code not in codes:
            continue
        k = l.partner_code or ""
        s = seen.setdefault(k, {"partner_code": k, "partner": names.get(k, l.partner or "(không ghi đối tượng)"),
                                "debit": 0.0, "credit": 0.0})
        s["debit"] += l.debit or 0; s["credit"] += l.credit or 0
    for k, s in seen.items():
        s["opening"] = _opening(db, codes, since, partner_code=k)
        s["closing"] = round(s["opening"] + s["debit"] - s["credit"], 0)
    return sorted(seen.values(), key=lambda x: -abs(x["closing"]))


# ---------- S31 / S51: Sổ chi tiết công nợ ----------

def partner_ledger(db: Session, account: str, partner_code: str, since: date, upto: date) -> dict:
    """Sổ chi tiết công nợ phải thu (131) / phải trả (331) theo từng đối tượng."""
    rep = account_book(db, account, since, upto, partner_code=partner_code, detail=True)
    p = db.execute(select(Partner).where(Partner.code == partner_code)).scalar_one_or_none()
    rep["partner_name"] = p.name if p else (rep["rows"][0]["partner"] if rep["rows"] else "")
    return rep


def partner_summary(db: Session, account: str, since: date, upto: date, min_amount: float = 0) -> dict:
    """Tổng hợp công nợ theo đối tượng: dư đầu – phát sinh – dư cuối (bảng MISA hay dùng để đối chiếu)."""
    codes = account_subtree(db, account)
    names = {p.code: p.name for p in db.execute(select(Partner)).scalars()}
    agg: dict[str, dict] = {}
    for l, e in _entry_rows(db, upto):
        if l.account_code not in codes:
            continue
        k = l.partner_code or ""
        s = agg.setdefault(k, {"partner_code": k, "partner": names.get(k, l.partner or "(không ghi đối tượng)"),
                               "opening": 0.0, "debit": 0.0, "credit": 0.0})
        if e.entry_date < since:
            s["opening"] += (l.debit or 0) - (l.credit or 0)
        else:
            s["debit"] += l.debit or 0; s["credit"] += l.credit or 0
    rows = []
    for s in agg.values():
        s["opening"] = round(s["opening"], 0)
        s["closing"] = round(s["opening"] + s["debit"] - s["credit"], 0)
        if abs(s["opening"]) > min_amount or abs(s["debit"]) > min_amount or abs(s["credit"]) > min_amount or abs(s["closing"]) > min_amount:
            rows.append(s)
    rows.sort(key=lambda x: -abs(x["closing"]))
    return {"account": account, "since": since, "upto": upto, "rows": rows,
            "total": {"opening": round(sum(r["opening"] for r in rows), 0),
                      "debit": round(sum(r["debit"] for r in rows), 0),
                      "credit": round(sum(r["credit"] for r in rows), 0),
                      "closing": round(sum(r["closing"] for r in rows), 0)}}


def partner_summary_xlsx(rep: dict) -> bytes:
    title = ("SỔ TỔNG HỢP CÔNG NỢ PHẢI THU KHÁCH HÀNG" if rep["account"].startswith(AR_ACCOUNT)
             else "SỔ TỔNG HỢP CÔNG NỢ PHẢI TRẢ NGƯỜI BÁN" if rep["account"].startswith(AP_ACCOUNT)
             else f"SỔ TỔNG HỢP THEO ĐỐI TƯỢNG – TÀI KHOẢN {rep['account']}")
    data = [[i, r["partner_code"], r["partner"], r["opening"], r["debit"], r["credit"], r["closing"]]
            for i, r in enumerate(rep["rows"], 1)]
    t = rep["total"]
    total = ["", "", "TỔNG CỘNG", t["opening"], t["debit"], t["credit"], t["closing"]]
    return _book("TONG HOP CONG NO",
                 _head(title, rep["since"], rep["upto"], f"Tài khoản {rep['account']}"),
                 ["STT", "Mã đối tượng", "Tên đối tượng", "Dư đầu kỳ", "Phát sinh Nợ", "Phát sinh Có", "Dư cuối kỳ"],
                 [6, 22, 46, 18, 18, 18, 18], data, total)


# ---------- S06: Bảng cân đối tài khoản theo khoảng ngày ----------

def trial_balance_range(db: Session, since: date, upto: date, level: int = 0, non_zero: bool = True) -> dict:
    """Bảng cân đối tài khoản (S06-DN) theo KHOẢNG NGÀY bất kỳ, không bó theo tháng như hàm cũ.
    level > 0 thì chỉ lấy tài khoản tới bậc đó (MISA cho chọn xem bậc 1/2/3) và cộng dồn số của tài khoản con
    lên tài khoản cha, để tổng Nợ = tổng Có ở mọi bậc."""
    accs = {a.code: a for a in db.execute(select(Account).order_by(Account.code)).scalars()}
    agg = {c: {"open": 0.0, "debit": 0.0, "credit": 0.0} for c in accs}
    for l, e in _entry_rows(db, upto):
        code = l.account_code
        if code not in agg:
            continue
        if e.entry_date < since:
            agg[code]["open"] += (l.debit or 0) - (l.credit or 0)
        else:
            agg[code]["debit"] += l.debit or 0
            agg[code]["credit"] += l.credit or 0

    def roll_up(code: str) -> dict:
        """Số của một tài khoản gồm cả tài khoản con (để tài khoản cha có số như MISA in)."""
        tot = {"open": 0.0, "debit": 0.0, "credit": 0.0}
        for c in account_subtree(db, code):
            for k in tot:
                tot[k] += agg[c][k]
        return tot

    rows = []
    for code, a in sorted(accs.items()):
        if level and a.level > level:
            continue
        t = roll_up(code)
        open_net = round(t["open"], 0)
        close_net = round(open_net + t["debit"] - t["credit"], 0)
        r = {"account": code, "name": a.name, "kind": a.kind, "level": a.level, "parent": a.parent,
             "open_debit": max(open_net, 0.0), "open_credit": max(-open_net, 0.0),
             "debit": round(t["debit"], 0), "credit": round(t["credit"], 0),
             "close_debit": max(close_net, 0.0), "close_credit": max(-close_net, 0.0)}
        if non_zero and not any(abs(r[k]) > 0 for k in ("open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit")):
            continue
        rows.append(r)
    # Tổng cộng chỉ lấy tài khoản bậc 1 để không cộng trùng tài khoản cha với tài khoản con
    tops = [r for r in rows if not r["parent"]]
    total = {k: round(sum(r[k] for r in tops), 0)
             for k in ("open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit")}
    return {"since": since, "upto": upto, "level": level, "rows": rows, "total": total,
            "balanced": abs(total["debit"] - total["credit"]) < 1 and abs(total["close_debit"] - total["close_credit"]) < 1}


def trial_balance_xlsx(rep: dict) -> bytes:
    data = [[r["account"], r["name"], r["open_debit"], r["open_credit"], r["debit"], r["credit"],
             r["close_debit"], r["close_credit"]] for r in rep["rows"]]
    t = rep["total"]
    total = ["", "TỔNG CỘNG", t["open_debit"], t["open_credit"], t["debit"], t["credit"], t["close_debit"], t["close_credit"]]
    return _book("BANG CAN DOI TAI KHOAN",
                 _head("BẢNG CÂN ĐỐI TÀI KHOẢN (Mẫu số S06-DN)", rep["since"], rep["upto"]),
                 ["Số hiệu TK", "Tên tài khoản", "Dư đầu Nợ", "Dư đầu Có", "Phát sinh Nợ", "Phát sinh Có",
                  "Dư cuối Nợ", "Dư cuối Có"],
                 [12, 46, 18, 18, 18, 18, 18, 18], data, total)


# ---------- S03a1 / S03a2: Nhật ký thu tiền, chi tiền ----------

def cash_journal(db: Session, since: date, upto: date, direction: str = "thu") -> dict:
    """Nhật ký thu tiền (S03a1) / chi tiền (S03a2): các chứng từ có động vào tiền, kèm TK đối ứng.
    direction='thu' lấy dòng ghi Nợ tiền (tiền vào), 'chi' lấy dòng ghi Có tiền (tiền ra)."""
    if direction not in ("thu", "chi"):
        raise ValueError("direction chỉ nhận 'thu' hoặc 'chi'")
    codes = set(account_subtree(db, CASH_ACCOUNT)) | set(account_subtree(db, BANK_ACCOUNT))
    rows_raw = [(l, e) for l, e in _entry_rows(db, upto, since)
                if l.account_code in codes and ((l.debit or 0) > 0 if direction == "thu" else (l.credit or 0) > 0)]
    contra = _contra_map(db, {e.id for _, e in rows_raw})
    rows, total = [], 0.0
    for l, e in rows_raw:
        amount = (l.debit or 0) if direction == "thu" else (l.credit or 0)
        total += amount
        rows.append({"date": e.entry_date, "code": e.code, "doc_no": l.doc_no, "description": e.description,
                     "account": l.account_code, "contra": _contra_of(contra, e.id, l),
                     "partner": l.partner, "partner_code": l.partner_code, "project_code": l.project_code,
                     "amount": amount, "entry_id": e.id})
    return {"direction": direction, "since": since, "upto": upto, "rows": rows, "total": round(total, 0)}


def cash_journal_xlsx(rep: dict) -> bytes:
    thu = rep["direction"] == "thu"
    title = ("SỔ NHẬT KÝ THU TIỀN (Mẫu số S03a1-DN)" if thu else "SỔ NHẬT KÝ CHI TIỀN (Mẫu số S03a2-DN)")
    data = [[r["date"], r["code"], r["doc_no"], r["description"], r["account"], r["contra"],
             r["partner"], r["project_code"], r["amount"]] for r in rep["rows"]]
    total = ["", "", "", "TỔNG CỘNG", "", "", "", "", rep["total"]]
    return _book("NHAT KY THU TIEN" if thu else "NHAT KY CHI TIEN",
                 _head(title, rep["since"], rep["upto"]),
                 ["Ngày", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK tiền", "TK đối ứng",
                  "Đối tượng", "Công trình", "Số tiền thu" if thu else "Số tiền chi"],
                 [14, 16, 14, 46, 12, 14, 30, 16, 18], data, total)


# ---------- Sổ theo công trình (tour/đoàn) ----------

def project_book(db: Session, project_code: str, since: date, upto: date) -> dict:
    """Sổ chi tiết theo công trình: mọi phát sinh gắn mã công trình (mã tour), tách doanh thu – chi phí."""
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    rows_raw = [(l, e) for l, e in _entry_rows(db, upto, since) if l.project_code == project_code]
    contra = _contra_map(db, {e.id for _, e in rows_raw})
    rows, revenue, cost = [], 0.0, 0.0
    for l, e in rows_raw:
        a = accs.get(l.account_code)
        kind = a.kind if a else ""
        if kind == "DT":
            revenue += (l.credit or 0) - (l.debit or 0)
        elif kind == "CP":
            cost += (l.debit or 0) - (l.credit or 0)
        rows.append({"date": e.entry_date, "code": e.code, "doc_no": l.doc_no, "description": e.description,
                     "account": l.account_code, "account_name": a.name if a else "", "account_kind": kind,
                     "contra": _contra_of(contra, e.id, l), "partner": l.partner, "partner_code": l.partner_code,
                     "debit": l.debit, "credit": l.credit, "entry_id": e.id})
    revenue, cost = round(revenue, 0), round(cost, 0)
    return {"project_code": project_code, "since": since, "upto": upto, "rows": rows,
            "revenue": revenue, "cost": cost, "profit": round(revenue - cost, 0)}


def project_summary(db: Session, since: date, upto: date, min_amount: float = 0) -> dict:
    """Tổng hợp doanh thu – chi phí – lãi lỗ theo từng công trình (tour/đoàn) trong kỳ.
    Đây là bảng Kế toán và Điều hành cần để biết tour nào thực sự có lãi trên SỔ, không phải trên bảng tính tay."""
    accs = {a.code: a.kind for a in db.execute(select(Account)).scalars()}
    agg: dict[str, dict] = {}
    for l, e in _entry_rows(db, upto, since):
        code = l.project_code or ""
        if not code:
            continue
        kind = accs.get(l.account_code, "")
        if kind not in ("DT", "CP"):
            continue
        s = agg.setdefault(code, {"project_code": code, "revenue": 0.0, "cost": 0.0})
        if kind == "DT":
            s["revenue"] += (l.credit or 0) - (l.debit or 0)
        else:
            s["cost"] += (l.debit or 0) - (l.credit or 0)
    rows = []
    for s in agg.values():
        s["revenue"], s["cost"] = round(s["revenue"], 0), round(s["cost"], 0)
        s["profit"] = round(s["revenue"] - s["cost"], 0)
        s["margin"] = round(100 * s["profit"] / s["revenue"], 1) if s["revenue"] else 0.0
        if abs(s["revenue"]) > min_amount or abs(s["cost"]) > min_amount:
            rows.append(s)
    rows.sort(key=lambda x: -x["revenue"])
    return {"since": since, "upto": upto, "rows": rows,
            "total": {"revenue": round(sum(r["revenue"] for r in rows), 0),
                      "cost": round(sum(r["cost"] for r in rows), 0),
                      "profit": round(sum(r["profit"] for r in rows), 0)}}


def project_summary_xlsx(rep: dict) -> bytes:
    data = [[i, r["project_code"], r["revenue"], r["cost"], r["profit"], r["margin"]]
            for i, r in enumerate(rep["rows"], 1)]
    t = rep["total"]
    total = ["", "TỔNG CỘNG", t["revenue"], t["cost"], t["profit"],
             round(100 * t["profit"] / t["revenue"], 1) if t["revenue"] else 0.0]
    return _book("TONG HOP THEO CONG TRINH",
                 _head("TỔNG HỢP DOANH THU – CHI PHÍ – LÃI LỖ THEO CÔNG TRÌNH (TOUR)", rep["since"], rep["upto"]),
                 ["STT", "Mã công trình", "Doanh thu", "Chi phí", "Lãi/lỗ", "Tỷ suất %"],
                 [6, 28, 20, 20, 20, 12], data, total)
