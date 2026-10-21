"""Sổ kế toán chuẩn theo chế độ kế toán doanh nghiệp – bố cục như bản in của MISA.

Gồm các sổ Kế toán phải xuất trình khi quyết toán thuế / kiểm toán, mà VTOS trước đây mới chỉ có Nhật ký chung:
  - Sổ Nhật ký chung (S03a-DN), Nhật ký thu tiền / chi tiền (S03a1, S03a2-DN)
  - Sổ Cái tài khoản (S03b-DN)                 – có cột TK ĐỐI ỨNG, đây là cột MISA luôn in
  - Sổ chi tiết tài khoản (S38-DN)             – thêm cột đối tượng / công trình
  - Bảng cân đối tài khoản (S06-DN)
  - Sổ quỹ tiền mặt (S07-DN), Sổ tiền gửi ngân hàng (S08-DN)
  - Sổ chi tiết và tổng hợp công nợ theo đối tượng (S31-DN, S51-DN)
  - Sổ chi tiết và tổng hợp lãi lỗ theo công trình (tour/đoàn)

Ba quy ước quan trọng, giống MISA:
  1. Sổ của một tài khoản TỔNG (ví dụ 112) gồm phát sinh của TẤT CẢ tài khoản con (1121, 11211…).
     Kế toán mở "Sổ cái 112" là muốn xem cả cây, không phải chỉ dòng ghi thẳng vào 112.
  2. TK đối ứng của một dòng là các tài khoản ở VẾ NGƯỢC LẠI trong cùng chứng từ: dòng ghi Nợ thì đối ứng
     là các tài khoản ghi Có của chứng từ đó và ngược lại. Chứng từ nhiều vế thì liệt kê, phân cách dấu phẩy.
  3. Chỉ lấy chứng từ ĐÃ GHI SỔ (status = "da_ghi_so"); chứng từ nháp không lên sổ.

GIỚI HẠN BỘ NHỚ – bắt buộc tôn trọng: máy chủ chỉ có 512 MB mà sổ thật đã hơn 100.000 dòng, nên
  - MỌI điều kiện lọc (tài khoản, đối tượng, công trình, khoảng ngày) phải đẩy xuống SQL, tuyệt đối không
    nạp cả sổ lên rồi lọc bằng Python;
  - số dư đầu kỳ và các dòng tổng cộng tính bằng hàm tổng hợp SQL, KHÔNG cộng từ danh sách dòng trả về,
    nhờ vậy tổng vẫn đúng kể cả khi danh sách bị cắt bớt;
  - danh sách dòng luôn có trần (limit) và trả kèm total_rows / truncated để giao diện biết còn dữ liệu;
  - chỉ chọn đúng các CỘT cần dùng, không nạp đối tượng ORM đầy đủ.
"""
from datetime import date
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.accounting import Account, JournalEntry, JournalLine, Partner
from app.services import chung_tu_loai as CTL
from app.core.config import settings

CASH_ACCOUNT, BANK_ACCOUNT = "111", "112"
AR_ACCOUNT, AP_ACCOUNT = "131", "331"
PAGE_LIMIT = 2000        # trần số dòng trả về cho giao diện
XLSX_LIMIT = 50000       # trần số dòng đưa vào tệp Excel
POSTED = "da_ghi_so"


# ---------- Nền chung ----------

def _accounts(db: Session) -> dict[str, Account]:
    return {a.code: a for a in db.execute(select(Account)).scalars()}


def _children_map(accs: dict) -> dict[str, list[str]]:
    ch: dict[str, list[str]] = {}
    for a in accs.values():
        if a.parent:
            ch.setdefault(a.parent, []).append(a.code)
    return ch


def _subtree(code: str, children: dict[str, list[str]]) -> list[str]:
    out, stack = [], [code]
    while stack:
        c = stack.pop()
        out.append(c)
        stack.extend(children.get(c, []))
    return out


def account_subtree(db: Session, code: str) -> list[str]:
    """Mã tài khoản và toàn bộ tài khoản con (đi theo cây parent, không dựa vào tiền tố chuỗi)."""
    accs = _accounts(db)
    if code not in accs:
        raise ValueError(f"Tài khoản {code} không có trong danh mục")
    return sorted(_subtree(code, _children_map(accs)))


# Chỉ lấy đúng cột cần dùng – nạp đối tượng ORM đầy đủ sẽ vỡ bộ nhớ với sổ hơn 100.000 dòng.
_COLS = (JournalLine.entry_id, JournalLine.account_code, JournalLine.debit, JournalLine.credit,
         JournalLine.partner, JournalLine.partner_code, JournalLine.project_code, JournalLine.doc_no,
         JournalEntry.entry_date, JournalEntry.code.label("entry_code"), JournalEntry.description,
         JournalEntry.source_type)


def _filtered(stmt, upto: date, since: date | None, codes=None, partner_code: str = "",
              project_code: str = "", side: str = ""):
    """Gắn mọi điều kiện lọc vào câu SQL (không lọc bằng Python)."""
    stmt = stmt.join(JournalEntry, JournalLine.entry_id == JournalEntry.id).where(
        JournalEntry.status == POSTED, JournalEntry.entry_date <= upto)
    if since is not None:
        stmt = stmt.where(JournalEntry.entry_date >= since)
    if codes is not None:
        stmt = stmt.where(JournalLine.account_code.in_(list(codes)))
    if partner_code:
        stmt = stmt.where(JournalLine.partner_code == partner_code)
    if project_code:
        stmt = stmt.where(JournalLine.project_code == project_code)
    if side == "debit":
        stmt = stmt.where(JournalLine.debit > 0)
    elif side == "credit":
        stmt = stmt.where(JournalLine.credit > 0)
    return stmt


def _rows(db: Session, upto: date, since: date | None = None, codes=None, partner_code: str = "",
          project_code: str = "", side: str = "", limit: int = PAGE_LIMIT):
    q = _filtered(select(*_COLS), upto, since, codes, partner_code, project_code, side)
    return db.execute(q.order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id).limit(limit)).all()


def _totals(db: Session, upto: date, since: date | None = None, codes=None, partner_code: str = "",
            project_code: str = "", side: str = "") -> dict:
    """Tổng phát sinh và số dòng – tính bằng SQL nên vẫn đúng khi danh sách trả về bị cắt bớt."""
    q = _filtered(select(func.count(JournalLine.id),
                         func.coalesce(func.sum(JournalLine.debit), 0.0),
                         func.coalesce(func.sum(JournalLine.credit), 0.0)),
                  upto, since, codes, partner_code, project_code, side)
    n, d, c = db.execute(q).one()
    return {"count": int(n or 0), "debit": round(float(d or 0), 0), "credit": round(float(c or 0), 0)}


def _opening(db: Session, codes, since: date, partner_code: str = "", project_code: str = "") -> float:
    """Số dư đầu kỳ (thuần Nợ − Có) trước ngày bắt đầu – một câu SUM, không nạp dòng nào lên bộ nhớ."""
    q = _filtered(select(func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0)),
                  since, None, codes, partner_code, project_code)
    # _filtered dùng entry_date <= upto, ở đây cần < since nên siết thêm một điều kiện
    q = q.where(JournalEntry.entry_date < since)
    return round(float(db.execute(q).scalar() or 0.0), 0)


def _contra_map(db: Session, entry_ids: set[int]) -> dict[int, tuple[list[str], list[str]]]:
    """Với mỗi chứng từ: (danh sách TK ghi Nợ, danh sách TK ghi Có) – dùng để suy ra TK đối ứng.
    Chỉ tra đúng các chứng từ có mặt trong trang đang trả về."""
    if not entry_ids:
        return {}
    out: dict[int, tuple[list[str], list[str]]] = {}
    ids = list(entry_ids)
    for i in range(0, len(ids), 900):                       # tránh câu IN quá dài
        rows = db.execute(select(JournalLine.entry_id, JournalLine.account_code, JournalLine.debit, JournalLine.credit)
                          .where(JournalLine.entry_id.in_(ids[i:i + 900]))).all()
        for eid, acc, d, c in rows:
            dr, cr = out.setdefault(eid, ([], []))
            if d and d > 0 and acc not in dr:
                dr.append(acc)
            if c and c > 0 and acc not in cr:
                cr.append(acc)
    return out


def _contra_of(contra: dict, entry_id: int, account: str, is_debit: bool) -> str:
    dr, cr = contra.get(entry_id, ([], []))
    other = cr if is_debit else dr
    return ", ".join(a for a in other if a != account)


def _row_out(r, contra: dict) -> dict:
    return {"date": r.entry_date, "code": r.entry_code, "doc_no": r.doc_no, "description": r.description,
            "account": r.account_code, "contra": _contra_of(contra, r.entry_id, r.account_code, (r.debit or 0) > 0),
            "partner": r.partner, "partner_code": r.partner_code, "project_code": r.project_code,
            "debit": r.debit or 0, "credit": r.credit or 0, "entry_id": r.entry_id}


def _page(rows_raw, total: dict, limit: int) -> dict:
    return {"total_rows": total["count"], "shown_rows": len(rows_raw),
            "truncated": total["count"] > len(rows_raw), "limit": limit}


def _head(title: str, since: date, upto: date, extra: str = "") -> list[list]:
    rows = [[settings.COMPANY_NAME], [f"Mã số thuế: {settings.COMPANY_TAX_CODE}"], [title],
            [f"Từ ngày {since:%d/%m/%Y} đến ngày {upto:%d/%m/%Y}"]]
    if extra:
        rows.append([extra])
    rows.append(["Đơn vị tính: VND"])
    return rows


def _book(name: str, head_rows, columns, widths, data, total=None, note: str = "") -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = name[:31]
    bold = Font(bold=True, name="Times New Roman")
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(ord("A") + i)].width = w
    for r in head_rows:
        ws.append(r)
    if note:
        ws.append([note])
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
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


def _cut_note(rep: dict) -> str:
    if rep.get("truncated"):
        return (f"* Tệp chỉ in {rep['shown_rows']:,} dòng đầu trong tổng số {rep['total_rows']:,} dòng; "
                f"các dòng TỔNG CỘNG bên dưới vẫn là tổng của TOÀN BỘ kỳ. Thu hẹp khoảng ngày để in đủ chi tiết.")
    return ""


# ---------- S03a: Sổ Nhật ký chung ----------

def journal_book(db: Session, since: date, upto: date, limit: int = PAGE_LIMIT) -> dict:
    total = _totals(db, upto, since)
    raw = _rows(db, upto, since, limit=limit)
    contra = _contra_map(db, {r.entry_id for r in raw})
    accs = {a.code: a.name for a in db.execute(select(Account.code, Account.name)).all()}
    rows = []
    for r in raw:
        d = _row_out(r, contra)
        d["account_name"] = accs.get(r.account_code, "")
        d["source_type"] = r.source_type
        rows.append(d)
    rep = {"since": since, "upto": upto, "rows": rows,
           "total": {"debit": total["debit"], "credit": total["credit"]},
           "balanced": abs((total["debit"] or 0) - (total["credit"] or 0)) < 1}
    rep.update(_page(raw, total, limit))
    return rep


def journal_book_xlsx(rep: dict) -> bytes:
    data = [[r["date"], r["code"], r["doc_no"], r["description"], r["account"], r["contra"],
             r["partner"], r["project_code"], r["debit"], r["credit"]] for r in rep["rows"]]
    total = ["", "", "", "TỔNG CỘNG", "", "", "", "", rep["total"]["debit"], rep["total"]["credit"]]
    return _book("SO NHAT KY CHUNG", _head("SỔ NHẬT KÝ CHUNG (Mẫu số S03a-DN)", rep["since"], rep["upto"]),
                 ["Ngày hạch toán", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK", "TK đối ứng",
                  "Đối tượng", "Công trình", "Phát sinh Nợ", "Phát sinh Có"],
                 [15, 16, 14, 46, 10, 14, 30, 16, 16, 16], data, total, _cut_note(rep))


# ---------- S03b / S38: Sổ Cái và Sổ chi tiết tài khoản ----------

def account_book(db: Session, account: str, since: date, upto: date, partner_code: str = "",
                 project_code: str = "", detail: bool = False, limit: int = PAGE_LIMIT) -> dict:
    """Sổ Cái (detail=False) hoặc Sổ chi tiết tài khoản (detail=True, có cột đối tượng/công trình).
    Gồm cả tài khoản con; số dư luỹ kế chạy theo thứ tự ngày."""
    accs = _accounts(db)
    acc = accs.get(account)
    if not acc:
        raise ValueError(f"Tài khoản {account} không có trong danh mục")
    codes = sorted(_subtree(account, _children_map(accs)))
    opening = _opening(db, codes, since, partner_code, project_code)
    total = _totals(db, upto, since, codes, partner_code, project_code)
    raw = _rows(db, upto, since, codes, partner_code, project_code, limit=limit)
    contra = _contra_map(db, {r.entry_id for r in raw})
    bal, rows = opening, []
    for r in raw:
        bal += (r.debit or 0) - (r.credit or 0)
        d = _row_out(r, contra)
        d["balance"] = round(bal, 0)
        # ĐỢT R4b 21/10/2026 — TÁCH DƯ NỢ / DƯ CÓ.
        # Trước đây chỉ có MỘT cột `balance` mang dấu. Mẫu S38-DN in hai cột, và hai cột ấy đọc
        # khác nhau: bên không có số thì BỎ TRỐNG, không ghi 0. Số 0 đọc là "đã tính và bằng
        # không"; bỏ trống đọc là "dư không nằm ở bên này". Nên hai khoá dưới đây dùng None chứ
        # không dùng 0.0, và `balance` giữ nguyên để màn hình cũ không hỏng.
        d["balance_debit"] = round(bal, 0) if bal > 0 else None
        d["balance_credit"] = round(-bal, 0) if bal < 0 else None
        rows.append(d)
    rep = {"account": account, "name": acc.name, "kind": acc.kind, "accounts": codes,
           "since": since, "upto": upto, "partner_code": partner_code, "project_code": project_code,
           "opening": opening, "rows": rows, "detail": detail,
           "total": {"debit": total["debit"], "credit": total["credit"]},
           "closing": round(opening + (total["debit"] or 0) - (total["credit"] or 0), 0)}
    rep.update(_page(raw, total, limit))
    return rep


def account_book_xlsx(rep: dict) -> bytes:
    title = ("SỔ CHI TIẾT TÀI KHOẢN (Mẫu số S38-DN)" if rep["detail"] else "SỔ CÁI (Mẫu số S03b-DN)")
    extra = f"Tài khoản {rep['account']} – {rep['name']}"
    if rep["partner_code"]:
        extra += f" | Đối tượng: {rep['partner_code']}"
    if rep["project_code"]:
        extra += f" | Công trình: {rep['project_code']}"
    head = _head(title, rep["since"], rep["upto"], extra)
    if rep["detail"]:
        cols = ["Ngày hạch toán", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK", "TK đối ứng",
                "Đối tượng", "Công trình", "Phát sinh Nợ", "Phát sinh Có", "Dư Nợ", "Dư Có"]
        widths = [15, 16, 14, 42, 10, 14, 28, 16, 16, 16, 16, 16]
        op = rep["opening"]
        data = [["", "", "", "Số dư đầu kỳ", "", "", "", "", "", "",
                 op if op > 0 else None, -op if op < 0 else None]]
        for r in rep["rows"]:
            data.append([r["date"], r["code"], r["doc_no"], r["description"], r["account"], r["contra"],
                         r["partner"], r["project_code"], r["debit"], r["credit"],
                         r.get("balance_debit"), r.get("balance_credit")])
        cl = rep["closing"]
        total = ["", "", "", "Cộng phát sinh / Số dư cuối kỳ", "", "", "", "",
                 rep["total"]["debit"], rep["total"]["credit"],
                 cl if cl > 0 else None, -cl if cl < 0 else None]
    else:
        cols = ["Ngày hạch toán", "Số chứng từ", "Diễn giải", "TK", "TK đối ứng",
                "Phát sinh Nợ", "Phát sinh Có", "Số dư"]
        widths = [15, 16, 50, 10, 14, 16, 16, 18]
        data = [["", "", "Số dư đầu kỳ", "", "", "", "", rep["opening"]]]
        for r in rep["rows"]:
            data.append([r["date"], r["code"], r["description"], r["account"], r["contra"],
                         r["debit"], r["credit"], r["balance"]])
        total = ["", "", "Cộng phát sinh / Số dư cuối kỳ", "", "",
                 rep["total"]["debit"], rep["total"]["credit"], rep["closing"]]
    return _book("SO CHI TIET TK" if rep["detail"] else "SO CAI", head, cols, widths, data, total, _cut_note(rep))


# ---------- S07 / S08: Sổ quỹ tiền mặt và Sổ tiền gửi ngân hàng ----------

def cash_book(db: Session, since: date, upto: date, account: str = CASH_ACCOUNT,
              partner_code: str = "", limit: int = PAGE_LIMIT) -> dict:
    """Sổ quỹ tiền mặt (S07-DN) / Sổ tiền gửi ngân hàng (S08-DN): Thu – Chi – Tồn."""
    rep = account_book(db, account, since, upto, partner_code=partner_code, limit=limit)
    bal, rows = rep["opening"], []
    for r in rep["rows"]:
        bal += (r["debit"] or 0) - (r["credit"] or 0)
        rows.append({"date": r["date"], "code": r["code"], "doc_no": r["doc_no"], "description": r["description"],
                     "contra": r["contra"], "partner": r["partner"], "partner_code": r["partner_code"],
                     "project_code": r["project_code"], "amount_in": r["debit"], "amount_out": r["credit"],
                     "balance": round(bal, 0), "entry_id": r["entry_id"]})
    return {"account": account, "name": rep["name"], "since": since, "upto": upto, "partner_code": partner_code,
            "opening": rep["opening"], "rows": rows,
            "total": {"in": rep["total"]["debit"], "out": rep["total"]["credit"]}, "closing": rep["closing"],
            "total_rows": rep["total_rows"], "shown_rows": rep["shown_rows"],
            "truncated": rep["truncated"], "limit": rep["limit"]}


def cash_book_xlsx(rep: dict) -> bytes:
    is_bank = rep["account"].startswith(BANK_ACCOUNT)
    title = ("SỔ TIỀN GỬI NGÂN HÀNG (Mẫu số S08-DN)" if is_bank else "SỔ QUỸ TIỀN MẶT (Mẫu số S07-DN)")
    extra = f"Tài khoản {rep['account']} – {rep['name']}" + (f" | Đối tượng: {rep['partner_code']}" if rep["partner_code"] else "")
    data = [["", "", "", "Số dư đầu kỳ", "", "", "", rep["opening"]]]
    for r in rep["rows"]:
        data.append([r["date"], r["code"], r["doc_no"], r["description"], r["contra"],
                     r["amount_in"], r["amount_out"], r["balance"]])
    total = ["", "", "", "Cộng phát sinh / Tồn cuối kỳ", "", (rep["total"] or 0)["in"], (rep["total"] or 0)["out"], rep["closing"]]
    return _book("SO TIEN GUI" if is_bank else "SO QUY TIEN MAT",
                 _head(title, rep["since"], rep["upto"], extra),
                 ["Ngày", "Số chứng từ", "Số CT gốc", "Diễn giải", "TK đối ứng",
                  "Gửi vào (Nợ)" if is_bank else "Thu (Nợ)", "Rút ra (Có)" if is_bank else "Chi (Có)", "Tồn"],
                 [14, 16, 14, 48, 14, 16, 16, 18], data, total, _cut_note(rep))


def bank_accounts(db: Session, since: date, upto: date) -> list[dict]:
    """Các đối tượng có phát sinh trên TK 112 trong kỳ, kèm dư đầu – phát sinh – dư cuối.
    LƯU Ý nghiệp vụ: sổ nạp từ MISA đang ghi đối tượng trên TK 112 là người nộp/nhận tiền, KHÔNG phải ngân hàng.
    Muốn in sổ tiền gửi theo từng ngân hàng đúng kiểu MISA thì phải mở tiểu khoản 112 cho từng ngân hàng."""
    codes = account_subtree(db, BANK_ACCOUNT)
    names = dict(db.execute(select(Partner.code, Partner.name)).all())
    q_open = _filtered(select(JournalLine.partner_code,
                              func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0)),
                       since, None, codes).where(JournalEntry.entry_date < since).group_by(JournalLine.partner_code)
    opening = {k or "": round(float(v or 0), 0) for k, v in db.execute(q_open).all()}
    q_move = _filtered(select(JournalLine.partner_code,
                              func.coalesce(func.sum(JournalLine.debit), 0.0),
                              func.coalesce(func.sum(JournalLine.credit), 0.0)),
                       upto, since, codes).group_by(JournalLine.partner_code)
    out = []
    for k, d, c in db.execute(q_move).all():
        k = k or ""
        op = opening.get(k, 0.0)
        out.append({"partner_code": k, "partner": names.get(k, "(không ghi đối tượng)" if not k else k),
                    "opening": op, "debit": round(float(d or 0), 0), "credit": round(float(c or 0), 0),
                    "closing": round(op + float(d or 0) - float(c or 0), 0)})
    return sorted(out, key=lambda x: -abs(x["closing"]))


# ---------- S31 / S51: Sổ công nợ theo đối tượng ----------

def partner_ledger(db: Session, account: str, partner_code: str, since: date, upto: date,
                   limit: int = PAGE_LIMIT) -> dict:
    """Sổ chi tiết công nợ phải thu (131) / phải trả (331) theo từng đối tượng."""
    rep = account_book(db, account, since, upto, partner_code=partner_code, detail=True, limit=limit)
    name = db.execute(select(Partner.name).where(Partner.code == partner_code)).scalar_one_or_none()
    rep["partner_name"] = name or (rep["rows"][0]["partner"] if rep["rows"] else "")
    return rep


def partner_summary(db: Session, account: str, since: date, upto: date, min_amount: float = 0) -> dict:
    """Tổng hợp công nợ theo đối tượng: dư đầu – phát sinh – dư cuối (bảng MISA hay dùng để đối chiếu).
    Gộp bằng SQL GROUP BY, không nạp dòng sổ lên bộ nhớ."""
    codes = account_subtree(db, account)
    names = dict(db.execute(select(Partner.code, Partner.name)).all())
    q_open = _filtered(select(JournalLine.partner_code,
                              func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0)),
                       since, None, codes).where(JournalEntry.entry_date < since).group_by(JournalLine.partner_code)
    opening = {k or "": round(float(v or 0), 0) for k, v in db.execute(q_open).all()}
    q_move = _filtered(select(JournalLine.partner_code,
                              func.coalesce(func.sum(JournalLine.debit), 0.0),
                              func.coalesce(func.sum(JournalLine.credit), 0.0)),
                       upto, since, codes).group_by(JournalLine.partner_code)
    moves = {(k or ""): (round(float(d or 0), 0), round(float(c or 0), 0)) for k, d, c in db.execute(q_move).all()}
    rows = []
    for k in set(opening) | set(moves):
        op = opening.get(k, 0.0)
        d, c = moves.get(k, (0.0, 0.0))
        s = {"partner_code": k, "partner": names.get(k, "(không ghi đối tượng)" if not k else k),
             "opening": op, "debit": d, "credit": c, "closing": round(op + d - c, 0)}
        if any(abs(s[f]) > min_amount for f in ("opening", "debit", "credit", "closing")):
            rows.append(s)
    rows.sort(key=lambda x: -abs(x["closing"]))
    return {"account": account, "since": since, "upto": upto, "rows": rows,
            "total": {"opening": round(sum(r["opening"] for r in rows), 0),
                      "debit": round(sum((r["debit"] or 0) for r in rows), 0),
                      "credit": round(sum((r["credit"] or 0) for r in rows), 0),
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


# ---------- S06: Bảng cân đối tài khoản ----------

def _open_by_account(db: Session, since: date) -> dict[str, float]:
    """Số dư đầu kỳ của từng tài khoản, ĐÃ BÙ TRỪ trong nội bộ tài khoản ấy."""
    q = _filtered(select(JournalLine.account_code,
                         func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0)),
                  since, None).where(JournalEntry.entry_date < since).group_by(JournalLine.account_code)
    return {k: float(v or 0) for k, v in db.execute(q).all()}


def _open_hai_ben(db: Session, since: date) -> dict[str, tuple[float, float]]:
    """ĐỢT R4b 21/10/2026 — SỐ DƯ ĐẦU KỲ KHÔNG BÙ TRỪ, cộng riêng TỪNG ĐỐI TƯỢNG.

    VÌ SAO KHÔNG PHẢI MỘT THAM SỐ HIỂN THỊ. Bù trừ hay không là HAI PHÉP TÍNH khác nhau, không
    phải hai cách bày cùng một con số:

        131 có khách A nợ ta 79,96 tỷ và khách B ta đang giữ thừa 9,86 tỷ.
        Bù trừ   -> MỘT số:  dư Nợ 70,10 tỷ.
        Không bù -> HAI số:  dư Nợ 79,96 tỷ VÀ dư Có 9,86 tỷ.

    Con số 9,86 tỷ ấy KHÔNG đọc ra được từ bảng đã bù trừ — nó đã biến mất trong phép trừ. Mà nó
    chính là con số kế toán cần khi đối chiếu công nợ: tiền khách nộp thừa là một khoản PHẢI TRẢ,
    không phải một khoản phải thu âm.

    Gom theo cặp (tài khoản, đối tượng) ở CƠ SỞ DỮ LIỆU, không kéo dòng sổ về — bài học Đợt E18.
    Dòng không có mã đối tượng gom vào một khoá rỗng và vẫn được tính, không bỏ ra.
    """
    q = _filtered(select(JournalLine.account_code, JournalLine.partner_code,
                         func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0)),
                  since, None).where(JournalEntry.entry_date < since).group_by(JournalLine.account_code, JournalLine.partner_code)
    out: dict[str, tuple[float, float]] = {}
    for acc, _dt, v in db.execute(q).all():
        n = float(v or 0)
        d, c = out.get(acc, (0.0, 0.0))
        out[acc] = (d + n, c) if n > 0 else (d, c - n)
    return out


def _luy_ke(db: Session, tu: date, upto: date) -> dict[str, tuple[float, float]]:
    """Phát sinh luỹ kế từ một mốc do người xem chọn tới ngày cuối kỳ xem."""
    q = _filtered(select(JournalLine.account_code,
                         func.coalesce(func.sum(JournalLine.debit), 0.0),
                         func.coalesce(func.sum(JournalLine.credit), 0.0)),
                  upto, tu).group_by(JournalLine.account_code)
    return {k: (float(d or 0), float(c or 0)) for k, d, c in db.execute(q).all()}


def trial_balance_range(db: Session, since: date, upto: date, level: int = 0, non_zero: bool = True,
                        bu_tru: bool = True, luy_ke_tu: date | None = None) -> dict:
    """Bảng cân đối tài khoản (S06-DN) theo KHOẢNG NGÀY bất kỳ.
    Tài khoản cha cộng dồn số của tài khoản con nên xem ở bậc nào tổng Nợ vẫn bằng tổng Có; tổng cộng chỉ lấy
    tài khoản bậc 1 để không cộng trùng cha với con. Số liệu lấy bằng hai câu GROUP BY, không nạp dòng sổ.

    ĐỢT R4b 21/10/2026 — hai tham số mới:
      · `bu_tru=False` : số dư đầu/cuối cộng riêng từng đối tượng rồi mới gộp (xem `_open_hai_ben`).
      · `luy_ke_tu`    : thêm hai cột phát sinh luỹ kế kể từ một mốc do người xem chọn.
    Cả hai là THAM SỐ chứ không phải luật cứng — đúng bài học 2 đọc từ MISA ngày 15/10.
    """
    accs = _accounts(db)
    children = _children_map(accs)
    hai_ben = None if bu_tru else _open_hai_ben(db, since)
    lk = _luy_ke(db, luy_ke_tu, upto) if luy_ke_tu else {}
    open_by = _open_by_account(db, since)
    q_move = _filtered(select(JournalLine.account_code,
                              func.coalesce(func.sum(JournalLine.debit), 0.0),
                              func.coalesce(func.sum(JournalLine.credit), 0.0)),
                       upto, since).group_by(JournalLine.account_code)
    move_by = {k: (float(d or 0), float(c or 0)) for k, d, c in db.execute(q_move).all()}

    rows = []
    for code, a in sorted(accs.items()):
        if level and a.level > level:
            continue
        op = mv_d = mv_c = op_d = op_c = lk_d = lk_c = 0.0
        for c in _subtree(code, children):                  # cây dựng MỘT lần, không tra lại danh mục
            op += open_by.get(c, 0.0)
            d, cr = move_by.get(c, (0.0, 0.0))
            mv_d += d; mv_c += cr
            if hai_ben is not None:
                hd, hc = hai_ben.get(c, (0.0, 0.0))
                op_d += hd; op_c += hc
            if lk:
                ld, lc = lk.get(c, (0.0, 0.0))
                lk_d += ld; lk_c += lc
        open_net, close_net = round(op, 0), round(op + mv_d - mv_c, 0)
        if hai_ben is None:
            o_d, o_c = max(open_net, 0.0), max(-open_net, 0.0)
            # Dư cuối KHÔNG bù trừ không suy ra được từ dư đầu không bù trừ cộng phát sinh: một
            # đối tượng có thể đổi bên trong kỳ. Nên khi bù trừ thì dùng số đã bù trừ như cũ.
            c_d, c_c = max(close_net, 0.0), max(-close_net, 0.0)
        else:
            o_d, o_c = round(op_d, 0), round(op_c, 0)
            c_d, c_c = max(close_net, 0.0), max(-close_net, 0.0)
        r = {"account": code, "name": a.name, "kind": a.kind, "level": a.level, "parent": a.parent,
             "open_debit": o_d, "open_credit": o_c,
             "debit": round(mv_d, 0), "credit": round(mv_c, 0),
             "close_debit": c_d, "close_credit": c_c}
        if lk:
            r["luy_ke_debit"] = round(lk_d, 0); r["luy_ke_credit"] = round(lk_c, 0)
        if non_zero and not any(abs(r[k]) > 0 for k in ("open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit")):
            continue
        rows.append(r)
    tops = [r for r in rows if not r["parent"]]
    khoa = ["open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit"]
    if lk:
        khoa += ["luy_ke_debit", "luy_ke_credit"]
    total = {k: round(sum(r.get(k, 0.0) for r in tops), 0) for k in khoa}
    # KHÔNG BÙ TRỪ THÌ TỔNG NỢ KHÔNG CÒN BẰNG TỔNG CÓ Ở CỘT DƯ ĐẦU, và đó không phải lỗi: hai cột
    # ấy nay là hai con số khác nhau chứ không phải hai nửa của một con số. Nên phép "cân" chỉ xét
    # PHÁT SINH và DƯ CUỐI — hai thứ vẫn phải cân dù xem kiểu nào.
    return {"since": since, "upto": upto, "level": level, "rows": rows, "total": total,
            "bu_tru": bu_tru, "luy_ke_tu": luy_ke_tu,
            "balanced": abs((total["debit"] or 0) - (total["credit"] or 0)) < 1 and abs(total["close_debit"] - total["close_credit"]) < 1}


def trial_balance_xlsx(rep: dict) -> bytes:
    lk = "luy_ke_debit" in rep["total"]                          # ĐỢT R4b: hai cột chỉ in khi có hỏi
    cols = ["Số hiệu TK", "Tên tài khoản", "Dư đầu Nợ", "Dư đầu Có", "Phát sinh Nợ", "Phát sinh Có",
            "Dư cuối Nợ", "Dư cuối Có"] + (["Luỹ kế Nợ", "Luỹ kế Có"] if lk else [])
    widths = [12, 46, 18, 18, 18, 18, 18, 18] + ([18, 18] if lk else [])
    data = [[r["account"], r["name"], r["open_debit"], r["open_credit"], r["debit"], r["credit"],
             r["close_debit"], r["close_credit"]] + ([r.get("luy_ke_debit", 0.0), r.get("luy_ke_credit", 0.0)] if lk else [])
            for r in rep["rows"]]
    t = rep["total"]
    total = ["", "TỔNG CỘNG", t["open_debit"], t["open_credit"], t["debit"], t["credit"],
             t["close_debit"], t["close_credit"]] + ([t["luy_ke_debit"], t["luy_ke_credit"]] if lk else [])
    # Tệp in ra PHẢI tự nói mình được tính kiểu nào. Hai bản in cùng một kỳ mà ra hai con số khác
    # nhau, không bản nào ghi lý do, là cách chắc chắn nhất để người đọc nghĩ có bản sai.
    chu = ""
    if not rep.get("bu_tru", True):
        chu = ("* Số dư đầu/cuối KHÔNG bù trừ: cộng riêng từng đối tượng rồi mới gộp, nên một tài khoản "
               "có thể có số ở cả hai bên. Cột Dư đầu Nợ và Dư đầu Có vì vậy KHÔNG còn phải bằng nhau.")
    if rep.get("luy_ke_tu"):
        chu += ("\n" if chu else "") + f"* Luỹ kế phát sinh tính từ {rep['luy_ke_tu']:%d/%m/%Y}."
    return _book("BANG CAN DOI TAI KHOAN",
                 _head("BẢNG CÂN ĐỐI TÀI KHOẢN (Mẫu số S06-DN)", rep["since"], rep["upto"]),
                 cols, widths, data, total, chu)


# ---------- S03a1 / S03a2: Nhật ký thu tiền, chi tiền ----------

def cash_journal(db: Session, since: date, upto: date, direction: str = "thu", limit: int = PAGE_LIMIT) -> dict:
    """Nhật ký thu tiền (S03a1) / chi tiền (S03a2): các chứng từ có động vào tiền, kèm TK đối ứng."""
    if direction not in ("thu", "chi"):
        raise ValueError("direction chỉ nhận 'thu' hoặc 'chi'")
    codes = set(account_subtree(db, CASH_ACCOUNT)) | set(account_subtree(db, BANK_ACCOUNT))
    side = "debit" if direction == "thu" else "credit"
    total = _totals(db, upto, since, codes, side=side)
    raw = _rows(db, upto, since, codes, side=side, limit=limit)
    contra = _contra_map(db, {r.entry_id for r in raw})
    rows = []
    for r in raw:
        d = _row_out(r, contra)
        d["amount"] = d["debit"] if direction == "thu" else d["credit"]
        rows.append(d)
    rep = {"direction": direction, "since": since, "upto": upto, "rows": rows,
           "total": total["debit"] if direction == "thu" else total["credit"]}
    rep.update(_page(raw, total, limit))
    return rep


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
                 [14, 16, 14, 46, 12, 14, 30, 16, 18], data, total, _cut_note(rep))


# ---------- Sổ theo công trình (tour/đoàn) ----------

def project_book(db: Session, project_code: str, since: date, upto: date, limit: int = PAGE_LIMIT) -> dict:
    """Sổ chi tiết theo công trình: mọi phát sinh gắn mã công trình (mã tour), tách doanh thu – chi phí."""
    kinds = dict(db.execute(select(Account.code, Account.kind)).all())
    names = dict(db.execute(select(Account.code, Account.name)).all())
    dt = [c for c, k in kinds.items() if k == "DT"]
    cp = [c for c, k in kinds.items() if k == "CP"]
    rev = _totals(db, upto, since, dt, project_code=project_code)
    cost = _totals(db, upto, since, cp, project_code=project_code)
    total = _totals(db, upto, since, project_code=project_code)
    raw = _rows(db, upto, since, project_code=project_code, limit=limit)
    contra = _contra_map(db, {r.entry_id for r in raw})
    rows = []
    for r in raw:
        d = _row_out(r, contra)
        d["account_name"] = names.get(r.account_code, "")
        d["account_kind"] = kinds.get(r.account_code, "")
        rows.append(d)
    revenue = round((rev["credit"] or 0) - (rev["debit"] or 0), 0)
    cost_amt = round((cost["debit"] or 0) - (cost["credit"] or 0), 0)
    rep = {"project_code": project_code, "since": since, "upto": upto, "rows": rows,
           "revenue": revenue, "cost": cost_amt, "profit": round(revenue - cost_amt, 0)}
    rep.update(_page(raw, total, limit))
    return rep


def project_summary(db: Session, since: date, upto: date, min_amount: float = 0) -> dict:
    """Tổng hợp doanh thu – chi phí – lãi lỗ theo từng công trình (tour/đoàn) trong kỳ, gộp bằng SQL.
    Đây là bảng cho biết tour nào thực sự có lãi trên SỔ, không phải trên bảng tính tay."""
    kinds = dict(db.execute(select(Account.code, Account.kind)).all())
    dt = [c for c, k in kinds.items() if k == "DT"]
    cp = [c for c, k in kinds.items() if k == "CP"]
    agg: dict[str, dict] = {}

    def collect(codes, field):
        q = _filtered(select(JournalLine.project_code,
                             func.coalesce(func.sum(JournalLine.debit), 0.0),
                             func.coalesce(func.sum(JournalLine.credit), 0.0)),
                      upto, since, codes).where(JournalLine.project_code != "").group_by(JournalLine.project_code)
        for k, d, c in db.execute(q).all():
            s = agg.setdefault(k, {"project_code": k, "revenue": 0.0, "cost": 0.0})
            s[field] += (float(c or 0) - float(d or 0)) if field == "revenue" else (float(d or 0) - float(c or 0))

    collect(dt, "revenue")
    collect(cp, "cost")
    rows = []
    for s in agg.values():
        s["revenue"], s["cost"] = round((s["revenue"] or 0), 0), round((s["cost"] or 0), 0)
        s["profit"] = round((s["revenue"] or 0) - (s["cost"] or 0), 0)
        s["margin"] = round(100 * s["profit"] / (s["revenue"] or 0), 1) if (s["revenue"] or 0) else 0.0
        if abs((s["revenue"] or 0)) > min_amount or abs((s["cost"] or 0)) > min_amount:
            rows.append(s)
    rows.sort(key=lambda x: -(x["revenue"] or 0))
    return {"since": since, "upto": upto, "rows": rows,
            "total": {"revenue": round(sum((r["revenue"] or 0) for r in rows), 0),
                      "cost": round(sum((r["cost"] or 0) for r in rows), 0),
                      "profit": round(sum(r["profit"] for r in rows), 0)}}


def project_summary_xlsx(rep: dict) -> bytes:
    data = [[i, r["project_code"], r["revenue"], r["cost"], r["profit"], r["margin"]]
            for i, r in enumerate(rep["rows"], 1)]
    t = rep["total"]
    total = ["", "TỔNG CỘNG", t["revenue"], t["cost"], t["profit"],
             round(100 * t["profit"] / (t["revenue"] or 0), 1) if (t["revenue"] or 0) else 0.0]
    return _book("TONG HOP THEO CONG TRINH",
                 _head("TỔNG HỢP DOANH THU – CHI PHÍ – LÃI LỖ THEO CÔNG TRÌNH (TOUR)", rep["since"], rep["upto"]),
                 ["STT", "Mã công trình", "Doanh thu", "Chi phí", "Lãi/lỗ", "Tỷ suất %"],
                 [6, 28, 20, 20, 20, 12], data, total)
# ---------- Bảng tổng hợp chứng từ gốc cùng loại — ĐỢT R4b 21/10/2026 ----------

CHUA_KHAI = "(chưa khai loại)"

# Bảy mã loại chứng từ VTOS đang có — ĐO ĐƯỢC, không ước: `chung_tu_loai.LOAI_CHUNG_TU` ngày
# 21/10/2026 có đúng bảy dòng (PT · PC · BC · BN · HDB · HDM · PKT). MISA có 36. Khoảng cách ấy là
# phần còn dang dở của Đợt R2, và chính nó bảo đảm bảng này sẽ CÓ dòng "chưa khai loại" — nên dòng
# ấy không phải trường hợp hiếm để bỏ qua.
CT_TEN = dict(CTL.LOAI_CHUNG_TU)


def chung_tu_goc(db: Session, since: date, upto: date) -> dict:
    """Gom chứng từ theo `loai_chung_tu`: mỗi loại bao nhiêu chứng từ, ghi Nợ bao nhiêu, ghi Có bao nhiêu.

    VÌ SAO GOM THEO LOẠI CHỨNG TỪ chứ không theo cặp định khoản: cặp định khoản đã có ma trận
    riêng ở Đợt R4a, và hai bảng trả lời gần cùng một câu thì sớm muộn lệch nhau. Bảng này trả lời
    câu khác: "tháng này phòng kế toán đã lập bao nhiêu phiếu thu, bao nhiêu ủy nhiệm chi".

    DÒNG "CHƯA KHAI LOẠI" LÀ CHỦ Ý, KHÔNG PHẢI RÁC. VTOS đang có 17 mã loại chứng từ, MISA có 36,
    nên chắc chắn còn bút toán không rơi vào mã nào. Bỏ chúng ra ngoài thì tổng của bảng không
    bằng sổ, và một bảng tổng hợp không khớp sổ thì không dùng để đối chiếu được. Đếm riêng, nói
    ra — cùng lối nghĩ với dòng "không chia được" của ma trận cặp định khoản.

    Gom ở CƠ SỞ DỮ LIỆU, qua CHÍNH `_filtered` mà mọi sổ khác dùng — nhờ vậy điều kiện "chỉ lấy
    chứng từ đã ghi sổ" không phải chép lại lần thứ hai, và không có chỗ cho hai nơi lệch nhau.
    Không nối chuỗi trong SQL: `concat` khác phương ngữ giữa SQLite (phép thử) và Postgres (máy chủ).
    """
    q = _filtered(select(JournalEntry.loai_chung_tu,
                         func.count(func.distinct(JournalLine.entry_id)),
                         func.coalesce(func.sum(JournalLine.debit), 0.0),
                         func.coalesce(func.sum(JournalLine.credit), 0.0)),
                  upto, since).group_by(JournalEntry.loai_chung_tu)

    # Tài khoản hay gặp của mỗi loại — một câu gom nữa, vẫn ở cơ sở dữ liệu.
    q_tk = _filtered(select(JournalEntry.loai_chung_tu, JournalLine.account_code,
                            func.coalesce(func.sum(JournalLine.debit), 0.0),
                            func.coalesce(func.sum(JournalLine.credit), 0.0)),
                     upto, since).group_by(JournalEntry.loai_chung_tu, JournalLine.account_code)
    hay_gap: dict[str, list[str]] = {}
    gom: dict[str, list[tuple[str, float, float]]] = {}
    for loai, acc, d, c in db.execute(q_tk).all():
        gom.setdefault(loai or "", []).append((acc, float(d or 0), float(c or 0)))
    for loai, ds in gom.items():
        no = sorted((x for x in ds if x[1] > 0), key=lambda x: -x[1])[:2]
        co = sorted((x for x in ds if x[2] > 0), key=lambda x: -x[2])[:2]
        hay_gap[loai] = [f"{a}" for a, _, _ in no] + ["/"] + [f"{a}" for a, _, _ in co] if (no and co) \
            else [a for a, _, _ in (no or co)]

    rows = []
    for loai, so_ct, d, c in db.execute(q).all():
        ma = (loai or "").strip()
        rows.append({"ma": ma, "ten": CT_TEN.get(ma, "") if ma else CHUA_KHAI,
                     "chua_khai": not ma, "so_chung_tu": int(so_ct or 0),
                     "debit": round(float(d or 0), 0), "credit": round(float(c or 0), 0),
                     "tk_hay_gap": " ".join(hay_gap.get(loai or "", []))})
    rows.sort(key=lambda r: (r["chua_khai"], -r["so_chung_tu"]))
    total = {k: round(sum(r[k] for r in rows), 0) for k in ("debit", "credit")}
    total["so_chung_tu"] = sum(r["so_chung_tu"] for r in rows)
    return {"since": since, "upto": upto, "rows": rows, "total": total,
            "so_chua_khai": sum(r["so_chung_tu"] for r in rows if r["chua_khai"])}


def chung_tu_goc_xlsx(rep: dict) -> bytes:
    data = [[r["ma"] or "—", r["ten"], r["so_chung_tu"], r["debit"], r["credit"], r["tk_hay_gap"]]
            for r in rep["rows"]]
    t = rep["total"]
    total = ["", "TỔNG CỘNG", t["so_chung_tu"], t["debit"], t["credit"], ""]
    return _book("TONG HOP CHUNG TU GOC",
                 _head("BẢNG TỔNG HỢP CHỨNG TỪ GỐC CÙNG LOẠI", rep["since"], rep["upto"]),
                 ["Mã loại", "Tên loại chứng từ", "Số chứng từ", "Ghi Nợ", "Ghi Có", "TK hay gặp"],
                 [14, 42, 14, 20, 20, 24], data, total)
