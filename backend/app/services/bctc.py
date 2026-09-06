"""Báo cáo tài chính theo Thông tư 99/2025/TT-BTC – đúng cấu trúc bộ đã nộp UBCK (H1/2026).

- Báo cáo tình hình tài chính (B01-DN / B01a-DN giữa niên độ): mã chỉ tiêu 100–440, mỗi tài khoản chi tiết ánh xạ theo
  Account.bs_debit (khi dư Nợ) / bs_credit (khi dư Có); 131/331/1388/3388/141 xét dư theo từng đối tượng.
- Báo cáo KQKD (B02-DN): mã 01–71 theo Account.pl_code; phát sinh trong kỳ, không tính bút toán kết chuyển 911.
- Lãi/lỗ chưa kết chuyển của kỳ được cộng vào chỉ tiêu 420 để bảng cân.
- Xuất Excel 2 sheet (THTC, KQKD) cùng bố cục tệp BCTC_H1_2026_VTD_NOP_UBCK.xlsx.
"""
import io, json
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from app.models.accounting import Account, JournalEntry, JournalLine, Partner
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
    cf = cash_flow_indirect_tt99(db, since, upto)
    GROUP_LCTT = {"08", "20", "30", "40", "50", "70"}
    lctt = [{"code": m["code"], "name": m["name"], "note": m["note"], "now": cf["values"].get(m["code"], 0.0), "group": m["code"] in GROUP_LCTT} for m in MAU["lctt"]]
    return {"company": settings.COMPANY_NAME, "tax_code": settings.COMPANY_TAX_CODE, "since": since, "upto": upto, "compare_upto": compare_upto,
            "thtc": thtc, "kqkd": kqkd, "lctt": lctt, "lctt_residual_plug": cf["residual_plug"], "balanced": bs["balanced"], "unposted_pl": bs["unposted_pl"], "detail": bs["detail"]}


# ---------- Báo cáo lưu chuyển tiền tệ gián tiếp (B03-DN, mẫu MAU["lctt"] 37 chỉ tiêu) ----------
def _net_by_prefix(bal: dict, prefixes: tuple) -> float:
    return sum(v["net"] for c, v in bal.items() if c.startswith(prefixes))


def cash_flow_indirect_tt99(db: Session, since: date, upto: date) -> dict:
    """LCTT gián tiếp theo mẫu B03-DN (TT99), tính tự động từ sổ VTOS.

    QUAN TRỌNG: phân loại theo CHỈ TIÊU BCTC (kết quả balance_sheet_tt99, đi qua đúng cây tài khoản
    Account.bs_debit/bs_credit – GIỐNG HỆT cách THTC tính), KHÔNG dùng tiền tố mã tài khoản cứng. Lý do:
    bộ mã tài khoản MISA có thể đổi qua các thời kỳ (ví dụ vay ngân hàng ghi ở "3411" (2025) rồi tách thành
    "34111/34112/34113" từ mốc chốt kiểm toán 30/06/2026) – nếu so sánh theo tiền tố mã tài khoản cố định,
    một khoản mục chỉ đổi TÊN MÃ (không thực sự phát sinh) sẽ bị hiểu nhầm thành dòng tiền phát sinh mới,
    làm sai lệch nghiêm trọng cả phần HĐKD lẫn HĐ tài chính (đã phát hiện khi so với dữ liệu thật: TK vay
    3411 (2025) không khớp tiền tố với 34111/34112/34113 (2026) dù CÙNG một khoản dư nợ). Đi qua chỉ tiêu
    BCTC tránh được lỗi này vì bản đồ tài khoản → chỉ tiêu áp dụng nhất quán cho MỌI kỳ.

    - Mục 1 (01-08): LNTT (KQKD mã 50) + cộng lại khấu hao/dự phòng (biến động chỉ tiêu 223/229/122/124/126/
      142/216 trong THTC) + lãi vay (KQKD mã 24) − lãi/lỗ HĐ tài chính (KQKD mã 22, chuyển sang mục đầu tư
      dòng 27 cho khớp).
    - Mục 09-15: biến động chỉ tiêu phải thu (130+162+210), tồn kho (140), phải trả HĐKD (310+330 trừ phần
      vay 321/339), trả trước (161+271); lãi vay/thuế TNDN đã trả bằng tiền thực tế (trừ phần còn treo trên
      tài khoản 3352/3334 nếu sổ có tách riêng).
    - Mục 21-27 (đầu tư): biến động NGUYÊN GIÁ TSCĐ (chỉ tiêu 222+225+228, không dùng giá trị còn lại để
      tránh trùng với khấu hao ở dòng 02), đầu tư tài chính ngắn hạn (chỉ tiêu 120 – gồm tiền gửi có kỳ hạn),
      đầu tư dài hạn (chỉ tiêu 261+262+263).
    - Mục 31-36 (tài chính): biến động vốn góp (chỉ tiêu 411+412), dư nợ vay (chỉ tiêu 321+339), và phần LNST
      kỳ này không giữ lại trong chỉ tiêu 420 (coi là cổ tức/lợi nhuận đã chia – ước tính).
    - Dòng 16/17 (thu/chi khác từ HĐKD) là phần CHÊNH LỆCH TỰ ĐỘNG để dòng 70 (tiền cuối kỳ) LUÔN khớp đúng
      chỉ tiêu 110 (tiền và tương đương tiền) THTC cuối kỳ – khoản mục nào chưa được phân loại rõ ở trên (nếu
      có) sẽ rơi vào đây; "residual_plug" trong kết quả trả về cho biết độ lớn phần chênh lệch này để Kế toán
      trưởng rà soát thêm nếu cần.
    """
    end0 = since - timedelta(days=1)
    bs0, bs1 = balance_sheet_tt99(db, end0), balance_sheet_tt99(db, upto)
    v0, v1 = bs0["values"], bs1["values"]
    pl = income_statement_tt99(db, since, upto)["values"]
    lntt = pl.get("50", 0.0)
    interest_expense = pl.get("24", 0.0)
    cit_expense = pl.get("51", 0.0) + pl.get("52", 0.0)
    fin_income = pl.get("22", 0.0)          # doanh thu HĐ tài chính (lãi tiền gửi, cổ tức…) – chuyển sang mục đầu tư dòng 27
    lnst = pl.get("60", 0.0)

    def g(vals: dict, *codes: str) -> float:
        return sum(vals.get(c, 0.0) for c in codes)

    def d(*codes: str) -> float:
        """Biến động chỉ tiêu BCTC 'tăng thì dương' giữa đầu kỳ và cuối kỳ (đúng chiều Nợ/Có của v["x"])."""
        return g(v1, *codes) - g(v0, *codes)

    # Tài khoản cụ thể (không qua chỉ tiêu BCTC dùng chung) chỉ dùng cho lãi vay/thuế TNDN đã trả bằng tiền –
    # nếu sổ không tách riêng tài khoản lãi vay phải trả (3352) thì coi như đã trả hết bằng tiền trong kỳ.
    bal0_raw, bal1_raw = account_balances(db, end0), account_balances(db, upto)
    accrued_interest_up = _net_by_prefix(bal0_raw, ("3352",)) - _net_by_prefix(bal1_raw, ("3352",))
    accrued_cit_up = _net_by_prefix(bal0_raw, ("3334",)) - _net_by_prefix(bal1_raw, ("3334",))

    v: dict[str, float] = {}
    v["01"] = lntt
    # 223/226/229 = giá trị hao mòn lũy kế (chỉ tiêu âm) của TSCĐ hữu hình/thuê TC/vô hình – tăng khấu hao
    # trong kỳ làm các chỉ tiêu này ÂM HƠN (giảm thêm) nên cộng lại bằng -d(...)
    v["02"] = -d("223") - d("226") - d("229")
    v["03"] = -d("122") - d("124") - d("126") - d("142") - d("216") - d("264")  # tăng các khoản dự phòng (đều là chỉ tiêu âm "(*)")
    v["04"] = 0.0
    v["05"] = -fin_income                                      # trừ lãi HĐ tài chính ra khỏi LN kỳ, đưa sang dòng 27
    v["06"] = interest_expense
    v["07"] = 0.0                                               # dành làm dự phòng, không dùng làm số dư tự động (xem dòng 16/17)
    v["08"] = sum(v[c] for c in ("01", "02", "03", "04", "05", "06", "07"))
    v["09"] = d("130", "162", "210")                            # phải thu ngắn hạn + thuế GTGT khấu trừ + phải thu dài hạn (gồm ký quỹ dài hạn)
    v["10"] = d("140")
    v["11"] = d("310", "330") - d("321", "339")                 # phải trả ngắn+dài hạn, TRỪ vay (321/339 → mục tài chính)
    v["12"] = d("161", "271")
    v["13"] = 0.0
    v["14"] = -(interest_expense - accrued_interest_up)
    v["15"] = -(cit_expense - accrued_cit_up)
    v["16"] = 0.0
    v["17"] = 0.0
    v["20"] = v["08"] + sum(v[c] for c in ("09", "10", "11", "12", "13", "14", "15", "16", "17"))

    d_fa = d("222", "225", "228")                               # nguyên giá TSCĐ hữu hình + thuê TC + vô hình
    v["21"] = -d_fa if d_fa > 0 else 0.0
    v["22"] = -d_fa if d_fa < 0 else 0.0
    d_stinv = d("120")                                          # đầu tư tài chính NH (gồm tiền gửi có kỳ hạn, KHÔNG phải tiền)
    v["23"] = -d_stinv if d_stinv > 0 else 0.0
    v["24"] = -d_stinv if d_stinv < 0 else 0.0
    d_inv = d("261", "262", "263")                              # đầu tư công ty con/liên kết/góp vốn khác
    v["25"] = -d_inv if d_inv > 0 else 0.0
    v["26"] = -d_inv if d_inv < 0 else 0.0
    v["27"] = fin_income                                        # ước tính đã thu bằng đúng phần ghi nhận trong kỳ
    v["30"] = sum(v[c] for c in ("21", "22", "23", "24", "25", "26", "27"))

    d_equity = d("411", "412")
    v["31"] = d_equity if d_equity > 0 else 0.0
    v["32"] = d_equity if d_equity < 0 else 0.0
    d_loan = d("321", "339")
    v["33"] = d_loan if d_loan > 0 else 0.0
    v["34"] = d_loan if d_loan < 0 else 0.0
    v["35"] = 0.0
    d_420 = d("420")
    v["36"] = d_420 - lnst                                       # phần 420 tăng KHÔNG đến từ LNST kỳ này → coi là đã chia/điều chỉnh
    v["40"] = sum(v[c] for c in ("31", "32", "33", "34", "35", "36"))

    v["60"] = v0.get("110", 0.0)
    v["61"] = 0.0
    v["50"] = v["20"] + v["30"] + v["40"]
    cash_end_actual = v1.get("110", 0.0)
    residual = (cash_end_actual - v["60"] - v["61"]) - v["50"]   # phần chưa được các mục trên phản ánh hết
    if residual >= 0: v["16"] += residual
    else: v["17"] += residual
    v["20"] = v["08"] + sum(v[c] for c in ("09", "10", "11", "12", "13", "14", "15", "16", "17"))
    v["50"] = v["20"] + v["30"] + v["40"]
    v["70"] = v["50"] + v["60"] + v["61"]
    return {"since": since, "upto": upto, "values": v, "residual_plug": residual, "cash_begin": v["60"], "cash_end": v["70"], "cash_end_actual": cash_end_actual}


# ---------- Chi tiết vay và nợ thuê tài chính theo ngân hàng – TK 341 (đúng bố cục MISA xuất) ----------
LOAN_KIND_NAME = {"34111": "Vay ngắn hạn ngân hàng", "34112": "Vay dài hạn", "34113": "Vay dài hạn đến hạn trả"}
LOAN_KIND_BS = {"34111": "320", "34112": "339", "34113": "321"}   # chỉ tiêu BCTC tương ứng (321 gộp vào 320 - nợ ngắn hạn)


def loan_bank_detail_341(db: Session, since: date, upto: date) -> dict:
    """Chi tiết vay/nợ thuê tài chính theo TỪNG NGÂN HÀNG + tiểu khoản, đúng bố cục báo cáo MISA 'CHI TIẾT
    VAY VÀ NỢ THUÊ TÀI CHÍNH THEO NGÂN HÀNG – TÀI KHOẢN 341': dư đầu kỳ (Có), trả nợ trong kỳ (Nợ), vay thêm
    trong kỳ (Có), dư cuối kỳ (Có) – theo từng (ngân hàng, tiểu khoản).

    Tài khoản vay được xác định ĐỘNG theo Account.bs_credit ∈ {"321" (vay/nợ thuê TC ngắn hạn – gồm cả nợ dài
    hạn đến hạn trả), "339" (vay/nợ thuê TC dài hạn)} thay vì liệt kê cứng mã tài khoản – vì bộ mã MISA có thể
    đổi qua các thời kỳ (vd "3411" gộp chung trước 30/06/2026 → tách "34111/34112/34113" từ mốc chốt kiểm toán)
    nhưng ánh xạ chỉ tiêu BCTC luôn nhất quán."""
    names = {p.code: (p.trade_name or p.name) for p in db.execute(select(Partner)).scalars()}
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    loan_codes = [c for c, a in accs.items() if a.bs_credit in ("321", "339")]
    if not loan_codes:
        return {"since": since, "upto": upto, "rows": [], "by_kind": {}, "total": {"open": 0.0, "debit_in_period": 0.0, "credit_in_period": 0.0, "close": 0.0}}
    end0 = since - timedelta(days=1)
    q = (select(JournalLine, JournalEntry.entry_date).join(JournalEntry)
         .where(JournalEntry.status == "da_ghi_so", JournalEntry.entry_date <= upto, JournalLine.account_code.in_(loan_codes)))
    groups: dict[tuple, dict] = {}
    for l, dt in db.execute(q).all():
        pcode = l.partner_code or ""
        key = (pcode, l.account_code)
        g = groups.setdefault(key, {"bank": names.get(pcode) or l.partner or "Đối tượng nội bộ chưa phân loại ngân hàng",
                                     "account": l.account_code, "open": 0.0, "debit": 0.0, "credit": 0.0})
        if dt <= end0:
            g["open"] += l.debit - l.credit
        elif since <= dt <= upto:
            g["debit"] += l.debit; g["credit"] += l.credit
    rows = []
    for (pcode, acc), g in sorted(groups.items(), key=lambda x: (x[1]["bank"], x[0][1])):
        open_c = -g["open"]                       # dư Có = -(Nợ-Có)
        close_c = -(g["open"] + g["debit"] - g["credit"])
        if abs(open_c) < 1 and abs(close_c) < 1 and abs(g["debit"]) < 1 and abs(g["credit"]) < 1: continue
        a = accs.get(acc)
        kind = LOAN_KIND_NAME.get(acc) or (a.name if a else acc) or ("Vay và nợ thuê tài chính dài hạn" if a and a.bs_credit == "339" else "Vay và nợ thuê tài chính ngắn hạn")
        rows.append({"bank": g["bank"], "partner_code": pcode, "account": acc, "kind": kind,
                     "open": open_c, "debit_in_period": g["debit"], "credit_in_period": g["credit"], "close": close_c})
    by_kind: dict[str, dict] = {}
    for r in rows:
        k = by_kind.setdefault(r["account"], {"name": r["kind"], "open": 0.0, "close": 0.0})
        k["open"] += r["open"]; k["close"] += r["close"]
    total = {"open": sum(r["open"] for r in rows), "debit_in_period": sum(r["debit_in_period"] for r in rows),
             "credit_in_period": sum(r["credit_in_period"] for r in rows), "close": sum(r["close"] for r in rows)}
    return {"since": since, "upto": upto, "rows": rows, "by_kind": by_kind, "total": total}


def loan_bank_detail_xlsx(rep: dict) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "TONG HOP THEO NGAN HANG"
    bold = Font(bold=True, name="Times New Roman"); nf = "#,##0;(#,##0);-"
    for h in ["CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS", "CHI TIẾT VAY VÀ NỢ THUÊ TÀI CHÍNH THEO NGÂN HÀNG – TÀI KHOẢN 341",
              f"Từ ngày {rep['since']:%d/%m/%Y} đến ngày {rep['upto']:%d/%m/%Y}"]: ws.append([h])
    ws.append([])
    ws.append(["STT", "Ngân hàng", "Tiểu khoản", "Phân loại", f"Dư đầu kỳ {rep['since']:%d/%m/%Y} (Có)", "Trả nợ trong kỳ (Nợ)", "Vay thêm trong kỳ (Có)", f"Dư cuối kỳ {rep['upto']:%d/%m/%Y} (Có)"])
    for c in ws[ws.max_row]: c.font = bold
    for i, r in enumerate(rep["rows"], 1):
        ws.append([i, r["bank"], r["account"], r["kind"], r["open"], r["debit_in_period"], r["credit_in_period"], r["close"]])
    t = rep["total"]
    ws.append([None, "TỔNG CỘNG", None, None, t["open"], t["debit_in_period"], t["credit_in_period"], t["close"]])
    for c in ws[ws.max_row]: c.font = bold
    ws.append([]); ws.append([None, f"TỔNG HỢP THEO PHÂN LOẠI TẠI {rep['upto']:%d/%m/%Y}"])
    for c in ws[ws.max_row]: c.font = bold
    for acc, k in sorted(rep["by_kind"].items()):
        ws.append([acc, k["name"], None, None, k["open"], None, None, k["close"]])
    ws.column_dimensions["B"].width = 55
    for col in "EFGH": ws.column_dimensions[col].width = 20
    for row in ws.iter_rows(min_row=6):
        for c in row[4:8]:
            if isinstance(c.value, (int, float)): c.number_format = nf
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


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
    ws4 = wb.create_sheet("LCTT GIAN TIEP - RIENG")
    for h in [rep["company"], f"Mã số thuế: {rep['tax_code']}", "BÁO CÁO LƯU CHUYỂN TIỀN TỆ (Theo phương pháp gián tiếp) – lập từ sổ VTOS",
              f"Từ {rep['since']:%d/%m/%Y} đến {rep['upto']:%d/%m/%Y} – Đơn vị tính: VND"]: ws4.append([h])
    if rep.get("lctt_residual_plug", 0):
        ws4.append([f"* Ghi chú: dòng 16/17 gồm phần chênh lệch tự động {rep['lctt_residual_plug']:,.0f} đ chưa phân loại chi tiết – Kế toán trưởng rà soát thêm"])
    ws4.append(["Chỉ tiêu", "Mã chỉ tiêu", "Thuyết minh", "Kỳ này"])
    for r in rep.get("lctt", []):
        ws4.append([r["name"], r["code"], r["note"], r["now"]])
        if r["group"]:
            for c in ws4[ws4.max_row]: c.font = bold
    ws3 = wb.create_sheet("CHI TIET TK - CHI TIEU")
    ws3.append(["Mã chỉ tiêu", "Tài khoản", "Đối tượng", "Số tiền"])
    for line, items in sorted(rep["detail"].items()):
        for it in items: ws3.append([line, it["account"], it["partner"], it["amount"]])
    for w in (ws, ws2, ws3, ws4):
        w.column_dimensions["A"].width = 70; w.column_dimensions["D"].width = 20; w.column_dimensions["E"].width = 20
        for row in w.iter_rows(min_row=6):
            for c in row[3:5]:
                c.number_format = nf
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
