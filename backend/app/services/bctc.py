"""Báo cáo tài chính theo Thông tư 99/2025/TT-BTC – đúng cấu trúc bộ đã nộp UBCK (H1/2026).

- Báo cáo tình hình tài chính (B01-DN / B01a-DN giữa niên độ): mã chỉ tiêu 100–440, mỗi tài khoản chi tiết ánh xạ theo
  Account.bs_debit (khi dư Nợ) / bs_credit (khi dư Có); 131/331/1388/3388/141 xét dư theo từng đối tượng.
- Báo cáo KQKD (B02-DN): mã 01–71 theo Account.pl_code; phát sinh trong kỳ, không tính bút toán kết chuyển 911.
- Lãi/lỗ chưa kết chuyển của kỳ được cộng vào chỉ tiêu 420 để bảng cân.
- Xuất Excel 2 sheet (THTC, KQKD) cùng bố cục tệp BCTC_H1_2026_VTD_NOP_UBCK.xlsx.
"""
import io, json
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from app.models.accounting import Account, JournalEntry, JournalLine
from app.core.config import settings

MAU = json.loads((Path(__file__).resolve().parent.parent / "data" / "bctc_tt99_mau.json").read_text(encoding="utf-8"))
BY_PARTNER = ("131", "331", "1388", "3388", "141", "1281", "1283", "136")   # xét dư Nợ/Có theo từng đối tượng
PL_PREFIX = ("5", "6", "7", "8", "9")


def _lines(db: Session, upto: date, since: date | None = None, exclude_closing: bool = False):
    q = select(JournalLine, JournalEntry.entry_date, JournalEntry.source_type, JournalEntry.id).join(JournalEntry).where(JournalEntry.status == "da_ghi_so", JournalEntry.entry_date <= upto)
    if since: q = q.where(JournalEntry.entry_date >= since)
    rows = db.execute(q).all()
    if exclude_closing:
        closing_ids = {eid for l, d, st, eid in rows if l.account_code.startswith("911") or st == "ket_chuyen"}
        rows = [r for r in rows if r[3] not in closing_ids]
    return rows


def account_balances(db: Session, upto: date) -> dict:
    """{account: {"net": Nợ−Có, "by_partner": {code: net}}} cho tài khoản chi tiết đã ghi sổ."""
    out: dict[str, dict] = {}
    for l, d, st, eid in _lines(db, upto):
        a = out.setdefault(l.account_code, {"net": 0.0, "by_partner": {}})
        a["net"] += l.debit - l.credit
        if l.account_code.startswith(BY_PARTNER):
            k = l.partner_code or l.partner or ""
            a["by_partner"][k] = a["by_partner"].get(k, 0.0) + l.debit - l.credit
    return out


def balance_sheet_tt99(db: Session, upto: date) -> dict:
    """Trả về {code: value} cho mọi chỉ tiêu THTC + chi tiết tài khoản → chỉ tiêu (để thuyết minh)."""
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    bal = account_balances(db, upto)
    v: dict[str, float] = {}
    detail: dict[str, list] = {}
    pl_open = 0.0
    for code, b in bal.items():
        a = accs.get(code)
        if code.startswith(PL_PREFIX):   # doanh thu/chi phí chưa kết chuyển → lãi/lỗ kỳ
            pl_open += -b["net"]
            continue
        if not a: continue
        # tìm ánh xạ gần nhất theo cây tài khoản
        bd, bc = a.bs_debit, a.bs_credit
        p = a
        while (not bd and not bc) and p and p.parent:
            p = accs.get(p.parent); bd, bc = (p.bs_debit, p.bs_credit) if p else ("", "")
        parts = b["by_partner"] if b["by_partner"] and code.startswith(BY_PARTNER) else {"": b["net"]}
        for k, net in parts.items():
            if abs(net) < 0.5: continue
            if net > 0:
                line = bd or bc
                amt = net if bd else -net   # dư Nợ ở TK nguồn vốn (vd 214 dư Nợ) → giảm chỉ tiêu Có
            else:
                line = bc or bd
                amt = -net if bc else net   # dư Có ở TK tài sản (vd 214, 229) → giảm chỉ tiêu tài sản (ghi âm)
            if not line: continue
            v[line] = v.get(line, 0.0) + amt
            detail.setdefault(line, []).append({"account": code, "partner": k, "amount": amt})
    v["420"] = v.get("420", 0.0) + pl_open
    # chỉ tiêu tổng hợp theo công thức (tính từ dưới lên: lặp đến khi ổn định)
    formulas = {m["code"]: m["formula"] for m in MAU["thtc"] if m["formula"]}
    for _ in range(6):
        for c, f in formulas.items():
            v[c] = sum(v.get(x, 0.0) for x in f.split("+"))
    return {"as_of": upto, "values": v, "detail": detail, "unposted_pl": pl_open, "balanced": abs(v.get("280", 0) - v.get("440", 0)) < 1}


def income_statement_tt99(db: Session, since: date, upto: date) -> dict:
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    v: dict[str, float] = {}
    for l, d, st, eid in _lines(db, upto, since, exclude_closing=True):
        a = accs.get(l.account_code)
        if not a or not l.account_code.startswith(PL_PREFIX) or l.account_code.startswith("911"): continue
        code = a.pl_code; p = a
        while not code and p and p.parent:
            p = accs.get(p.parent); code = p.pl_code if p else ""
        if not code: continue
        amt = (l.credit - l.debit) if a.kind == "DT" else (l.debit - l.credit)
        v[code] = v.get(code, 0.0) + amt
        if l.account_code.startswith("6351"): v["24"] = v.get("24", 0.0) + amt
    for c, f in {m["code"]: m["formula"] for m in MAU["kqkd"] if m["formula"]}.items():
        tot, sign, tok = 0.0, 1, ""
        for ch in f + "+":
            if ch in "+-":
                if tok: tot += sign * v.get(tok, 0.0)
                sign, tok = (1 if ch == "+" else -1), ""
            else: tok += ch
        v[c] = tot
    return {"since": since, "upto": upto, "values": v}


def bctc(db: Session, upto: date, since: date | None = None, compare_upto: date | None = None) -> dict:
    """Bộ báo cáo TT99 kỳ [since, upto] kèm cột so sánh (số đầu năm / cùng kỳ năm trước)."""
    since = since or date(upto.year, 1, 1)
    compare_upto = compare_upto or date(upto.year - 1, 12, 31)
    bs, bs0 = balance_sheet_tt99(db, upto), balance_sheet_tt99(db, compare_upto)
    pl = income_statement_tt99(db, since, upto)
    pl0 = income_statement_tt99(db, date(since.year - 1, since.month, since.day), date(upto.year - 1, upto.month, min(upto.day, 28)))
    thtc = [{"code": m["code"], "name": m["name"], "note": m["note"], "now": bs["values"].get(m["code"], 0.0) if m["code"] else None, "prev": bs0["values"].get(m["code"], 0.0) if m["code"] else None, "group": bool(m["formula"]) or not m["code"]} for m in MAU["thtc"]]
    kqkd = [{"code": m["code"], "name": m["name"], "note": m["note"], "now": pl["values"].get(m["code"], 0.0), "prev": pl0["values"].get(m["code"], 0.0), "group": bool(m["formula"])} for m in MAU["kqkd"]]
    return {"company": settings.COMPANY_NAME, "tax_code": settings.COMPANY_TAX_CODE, "since": since, "upto": upto, "compare_upto": compare_upto,
            "thtc": thtc, "kqkd": kqkd, "balanced": bs["balanced"], "unposted_pl": bs["unposted_pl"], "detail": bs["detail"]}


def bctc_xlsx(rep: dict) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "THTC - RIENG"
    bold = Font(bold=True, name="Times New Roman"); nf = "#,##0;(#,##0);-"
    hdr = [rep["company"], f"Mã số thuế: {rep['tax_code']}", "BÁO CÁO TÌNH HÌNH TÀI CHÍNH (Dạng đầy đủ) – lập từ sổ VTOS", f"Tại ngày {rep['upto']:%d/%m/%Y} – Đơn vị tính: VND"]
    for h in hdr: ws.append([h])
    ws.append(["Chỉ tiêu", "Mã chỉ tiêu", "Thuyết minh", "Số cuối kỳ", f"Số tại {rep['compare_upto']:%d/%m/%Y}"])
    for r in rep["thtc"]:
        ws.append([r["name"], r["code"], r["note"], r["now"], r["prev"]])
        if r["group"]:
            for c in ws[ws.max_row]: c.font = bold
    ws2 = wb.create_sheet("KQKD - RIENG")
    for h in [rep["company"], f"Mã số thuế: {rep['tax_code']}", "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH – lập từ sổ VTOS", f"Từ {rep['since']:%d/%m/%Y} đến {rep['upto']:%d/%m/%Y} – Đơn vị tính: VND"]: ws2.append([h])
    ws2.append(["Chỉ tiêu", "Mã chỉ tiêu", "Thuyết minh", "Kỳ này", "Cùng kỳ năm trước"])
    for r in rep["kqkd"]:
        ws2.append([r["name"], r["code"], r["note"], r["now"], r["prev"]])
        if r["group"]:
            for c in ws2[ws2.max_row]: c.font = bold
    ws3 = wb.create_sheet("CHI TIET TK - CHI TIEU")
    ws3.append(["Mã chỉ tiêu", "Tài khoản", "Đối tượng", "Số tiền"])
    for line, items in sorted(rep["detail"].items()):
        for it in items: ws3.append([line, it["account"], it["partner"], it["amount"]])
    for w in (ws, ws2, ws3):
        w.column_dimensions["A"].width = 70; w.column_dimensions["D"].width = 20; w.column_dimensions["E"].width = 20
        for row in w.iter_rows(min_row=6):
            for c in row[3:5]:
                c.number_format = nf
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
