"""Cầu nối MISA AMIS ↔ VTOS (định hướng 06/9/2026 – một cấu trúc dữ liệu với MISA).

- Đọc các tệp Excel MISA xuất ra (không cần API): Bảng cân đối tài khoản (mẫu quản trị), Tổng hợp công nợ theo đối tượng,
  Danh sách khách hàng / nhà cung cấp / công trình, Sổ nhật ký chung, DataNCC.
- Nạp số dư đầu kỳ (chứng từ SDDK, nguồn so_du_dau_ky), nạp chứng từ lịch sử (nguồn misa), đối chiếu số dư VTOS – MISA.
- Xuất ngược sang MISA theo đúng mẫu Import (Mua dịch vụ 57 cột, Bút toán tổng hợp, Danh mục công trình).
"""
import io, re, unicodedata
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from openpyxl import load_workbook, Workbook
from app.models.core import Tour, User
from app.models.accounting import Account, JournalEntry, JournalLine, Partner, Project
from app.models.ops import PaymentRequest
from app.services import accounting as ACC
from app.services import rules as R

TECHNICAL_PROJECTS = ("0000", "CHUA RO", "CHUARO", "CPXD", "CPCD", "CPBH", "CPQL", "CHOTHUEMATBANG", "DLPTLUHANH")
PROJECT_STD = re.compile(r"^[A-Z]{2,8}\d{3,4}\.\d{2}\.?\d{6}$")   # mã công trình chuẩn SP.NHÓM.DDMMYY (vd EU0014.09.170626)


def _num(x) -> float:
    if x is None or x == "": return 0.0
    if isinstance(x, (int, float)): return float(x)
    try: return float(str(x).replace(".", "").replace(",", "."))
    except ValueError: return 0.0


def _date(x) -> date | None:
    if isinstance(x, datetime): return x.date()
    if isinstance(x, date): return x
    if not x: return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime(str(x).strip()[:10], fmt).date()
        except ValueError: pass
    return None


def _rows(data: bytes, sheet: int | str = 0) -> list[tuple]:
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
    return [r for r in ws.iter_rows(values_only=True) if any(c is not None and c != "" for c in r)]


def _find_header(rows: list[tuple], *keys: str) -> int:
    for i, r in enumerate(rows):
        cells = [str(c).strip().lower() for c in r if c is not None]
        if all(any(k in c for c in cells) for k in keys):
            return i
    raise ValueError(f"Không tìm thấy dòng tiêu đề có {keys} – đúng tệp MISA chưa?")


# ---------- 1. Bảng cân đối tài khoản (mẫu quản trị / BCDPS) ----------
def parse_trial_balance(data: bytes) -> dict:
    """→ {"period": "...", "rows": [{code, name, open_d, open_c, ps_d, ps_c, close_d, close_c}]}"""
    rows = _rows(data)
    h = _find_header(rows, "tài khoản", "tên tài khoản")
    period = next((str(c) for r in rows[:h] for c in r if c and re.search(r"\d{2}/\d{4}|năm \d{4}|tháng \d", str(c), re.I)), "")
    out = []
    for r in rows[h + 1:]:
        code = str(r[0]).strip() if r[0] is not None else ""
        if not code.isdigit(): continue
        v = [_num(x) for x in r[2:8]]
        while len(v) < 6: v.append(0.0)
        out.append({"code": code, "name": str(r[1] or "").strip(), "open_d": v[0], "open_c": v[1], "ps_d": v[2], "ps_c": v[3], "close_d": v[4], "close_c": v[5]})
    if not out: raise ValueError("Tệp không có dòng tài khoản")
    return {"period": period, "rows": out}


def leaf_rows(rows: list[dict]) -> list[dict]:
    codes = {r["code"] for r in rows}
    return [r for r in rows if not any(c != r["code"] and c.startswith(r["code"]) for c in codes)]


# ---------- 2. Tổng hợp công nợ theo đối tượng ----------
def parse_object_balances(data: bytes) -> list[dict]:
    """MISA 'Tổng hợp công nợ theo đối tượng' hoặc sheet 131/331 trong hồ sơ hạn mức → [{partner_code, name, account, open_d, open_c, ps_d, ps_c, close_d, close_c}]"""
    rows = _rows(data)
    h = _find_header(rows, "đối tượng", "tk")
    out = []
    for r in rows[h + 1:]:
        if r[0] is None or r[2] is None: continue
        acc = str(r[2]).strip()
        if not acc.isdigit(): continue
        v = [_num(x) for x in r[3:9]]
        while len(v) < 6: v.append(0.0)
        out.append({"partner_code": str(r[0]).strip(), "name": str(r[1] or "").strip(), "account": acc, "open_d": v[0], "open_c": v[1], "ps_d": v[2], "ps_c": v[3], "close_d": v[4], "close_c": v[5]})
    return out


# ---------- 3. Danh mục ----------
def import_partners(db: Session, data: bytes, kind: str = "auto") -> dict:
    """Danh sách khách hàng / nhà cung cấp MISA, hoặc DataNCC (Tên NCC, MST, Tên pháp nhân, Địa chỉ)."""
    rows = _rows(data)
    stat = {"created": 0, "updated": 0}
    have = {p.code: p for p in db.execute(select(Partner)).scalars()}
    hdr = [str(c or "").strip().lower() for c in rows[0]] if rows else []
    if "tên ncc" in hdr and "mst" in hdr:   # DataNCC của Điều hành
        ci = {k: hdr.index(k) for k in ("tên ncc", "mst") if k in hdr}
        legal = next((i for i, c in enumerate(hdr) if "pháp nhân" in c), None); addr = next((i for i, c in enumerate(hdr) if "địa chỉ" in c), None)
        for r in rows[1:]:
            code = str(r[ci["mst"]] or "").strip()[:60]; trade = str(r[ci["tên ncc"]] or "").strip()
            if not code or not trade: continue
            p = have.get(code)
            if p is None: p = Partner(code=code, name=trade, kind="ncc", source="data_ncc"); db.add(p); have[code] = p; stat["created"] += 1
            else: stat["updated"] += 1
            p.is_supplier, p.trade_name, p.tax_code = True, trade[:200], code[:20]
            if legal is not None and r[legal]: p.name = str(r[legal]).strip()[:300]
            if addr is not None and r[addr]: p.address = str(r[addr]).strip()[:300]
        db.commit(); return stat
    h = _find_header(rows, "mã", "tên")
    hdr = [str(c or "").strip().lower() for c in rows[h]]
    ic = next(i for i, c in enumerate(hdr) if c.startswith("mã khách") or c.startswith("mã nhà") or c == "mã")
    iname = ic + 1
    iaddr = next((i for i, c in enumerate(hdr) if "địa chỉ" in c), None)
    itax = next((i for i, c in enumerate(hdr) if "mã số thuế" in c), None)
    iphone = next((i for i, c in enumerate(hdr) if "điện thoại" in c), None)
    iint = next((i for i, c in enumerate(hdr) if "nội bộ" in c), None)
    k = kind if kind != "auto" else ("ncc" if "nhà cung cấp" in hdr[ic] else "kh")
    for r in rows[h + 1:]:
        code = str(r[ic] or "").strip()[:60]; name = str(r[iname] or "").strip()
        if not code or not name or code.lower() == "stt": continue
        p = have.get(code)
        if p is None: p = Partner(code=code, name=name, kind=k); db.add(p); have[code] = p; stat["created"] += 1
        else: stat["updated"] += 1
        p.name = name[:300]
        if k == "kh": p.is_customer = True
        else: p.is_supplier = True
        if iaddr is not None and r[iaddr]: p.address = str(r[iaddr]).strip()[:300]
        if itax is not None and r[itax]: p.tax_code = str(r[itax]).strip()[:20]
        if iphone is not None and r[iphone]: p.phone = str(r[iphone]).strip()[:40]
        if iint is not None and r[iint]: p.internal = str(r[iint]).strip().lower() in ("có", "x", "true", "1")
    db.commit()
    return stat


def import_projects(db: Session, data: bytes) -> dict:
    """Danh sách công trình MISA → bảng projects; gắn tour VTOS có cùng mã (hoặc mã Vietrip trùng)."""
    rows = _rows(data)
    h = _find_header(rows, "mã công trình", "tên công trình")
    hdr = [str(c or "").strip().lower() for c in rows[h]]
    ic = next(i for i, c in enumerate(hdr) if c.startswith("mã công trình")); iname = ic + 1
    istart = next((i for i, c in enumerate(hdr) if "bắt đầu" in c), None); iend = next((i for i, c in enumerate(hdr) if "kết thúc" in c), None)
    istat = next((i for i, c in enumerate(hdr) if "tình trạng" in c), None)
    have = {p.code: p for p in db.execute(select(Project)).scalars()}
    tours = {t.code: t.id for t in db.execute(select(Tour)).scalars()}
    stat = {"created": 0, "updated": 0, "linked": 0, "standard": 0, "technical": 0}
    for r in rows[h + 1:]:
        code = str(r[ic] or "").strip(); name = str(r[iname] or "").strip()
        if not code or not name: continue
        p = have.get(code)
        if p is None: p = Project(code=code, name=name); db.add(p); have[code] = p; stat["created"] += 1
        else: stat["updated"] += 1
        p.name = name[:300]
        if istart is not None: p.start_date = _date(r[istart])
        if iend is not None: p.end_date = _date(r[iend])
        if istat is not None and r[istat]: p.status = "hoan_thanh" if "hoàn" in str(r[istat]).lower() else "dang_thuc_hien"
        p.technical = code.upper().startswith(TECHNICAL_PROJECTS) or code.upper().startswith("CHUA")
        if p.technical: stat["technical"] += 1
        if PROJECT_STD.match(code): stat["standard"] += 1
        if code in tours and p.tour_id != tours[code]: p.tour_id = tours[code]; stat["linked"] += 1
    db.commit()
    return stat


def ensure_project_for_tour(db: Session, t: Tour) -> Project:
    """Mỗi tour VTOS là một công trình; mã công trình = mã tour."""
    p = db.execute(select(Project).where(Project.code == t.code)).scalars().first()
    if p is None:
        p = Project(code=t.code, name=t.name[:300], start_date=t.start_date, end_date=t.end_date, tour_id=t.id, source="vtos"); db.add(p); db.flush()
    elif p.tour_id is None: p.tour_id = t.id
    return p


# ---------- 4. Số dư đầu kỳ ----------
def import_opening_balance(db: Session, u: User, tb: bytes, as_of: date, column: str = "close", objects: bytes | None = None, replace: bool = False) -> dict:
    """Nhập số dư từ Bảng cân đối tài khoản MISA vào ngày as_of (cột 'close' = số cuối kỳ, 'open' = số đầu kỳ của tệp).
    Chỉ ghi tài khoản chi tiết (không có TK con). Nếu có tệp Tổng hợp công nợ theo đối tượng → tách 131/331/1388/141/3388/341… theo từng đối tượng.
    Chứng từ nguồn so_du_dau_ky, mã SDDK-yyyymmdd; đã có thì phải replace=True (đảo chứng từ cũ rồi ghi mới)."""
    parsed = parse_trial_balance(tb)
    leafs = leaf_rows(parsed["rows"])
    key_d, key_c = ("close_d", "close_c") if column == "close" else ("open_d", "open_c")
    ref = f"sddk:{as_of:%Y%m%d}"
    old = db.execute(select(JournalEntry).where(JournalEntry.source_ref == ref, JournalEntry.status == "da_ghi_so")).scalars().all()
    if old and not replace:
        raise ValueError(f"Đã có số dư đầu kỳ ngày {as_of:%d/%m/%Y} ({old[0].code}) – chọn 'thay thế' để nhập lại")
    for e in old:   # đảo đúng ngày số dư (không phải hôm nay) để số dư tại as_of không bị nhân đôi
        rl = [{"account": l.account_code, "debit": l.credit, "credit": l.debit, "partner": l.partner, "partner_code": l.partner_code, "note": f"Đảo {e.code} – nhập lại số dư"} for l in e.lines]
        r = ACC.post_entry(db, u.username, u.role, as_of, f"Đảo {e.code}: nhập lại số dư đầu kỳ", rl, "dao", f"entry:{e.code}")
        e.reversed_by_id = r.id; e.source_ref = f"{ref}:old"
    obj = {}
    if objects:
        for o in parse_object_balances(objects):
            d, c = (o["close_d"], o["close_c"]) if column == "close" else (o["open_d"], o["open_c"])
            if d or c: obj.setdefault(o["account"], []).append((o["partner_code"], o["name"], d, c))
    names = {p.code: p.name for p in db.execute(select(Partner)).scalars()}
    lines, missing, stat = [], [], {"accounts": 0, "object_lines": 0, "created_accounts": 0}
    for r in leafs:
        d, c = r[key_d], r[key_c]
        if not d and not c: continue
        if not db.get(Account, r["code"]):
            k = ACC_KIND(r["code"]); db.add(Account(code=r["code"], name=r["name"], kind=k, parent=r["code"][:-1] if len(r["code"]) > 3 else "", level=len(r["code"]) - 2, misa=True)); db.flush(); stat["created_accounts"] += 1
        stat["accounts"] += 1
        parts = obj.get(r["code"], [])
        if parts:
            sd = sum(x[2] for x in parts); sc = sum(x[3] for x in parts)
            for pc, pn, pd_, pc_ in parts:
                lines.append({"account": r["code"], "debit": pd_, "credit": pc_, "partner_code": pc, "partner": pn or names.get(pc, ""), "note": "Số dư theo đối tượng (MISA)"}); stat["object_lines"] += 1
            gap = (d - c) - (sd - sc)   # bảng cân đối MISA ghi số dư ròng theo TK, công nợ ghi theo từng đối tượng (Nợ và Có riêng)
            if abs(gap) >= 1:            # phần chênh lệch không có đối tượng
                lines.append({"account": r["code"], "debit": max(gap, 0), "credit": max(-gap, 0), "note": "Chênh lệch tổng TK − tổng đối tượng"})
                missing.append(f"{r['code']}: TK {d - c:,.0f} – đối tượng {sd - sc:,.0f} (lệch {gap:,.0f})")
        else:
            lines.append({"account": r["code"], "debit": d, "credit": c, "note": "Số dư (MISA)"})
    td = sum(l["debit"] for l in lines); tc = sum(l["credit"] for l in lines)
    if abs(td - tc) >= 1:
        raise ValueError(f"Bảng cân đối MISA không cân ở tài khoản chi tiết: Nợ {td:,.0f} ≠ Có {tc:,.0f}")
    e = ACC.post_entry(db, u.username, u.role, as_of, f"Số dư đầu kỳ {as_of:%d/%m/%Y} nhập từ MISA ({parsed['period']})", lines, "so_du_dau_ky", ref)
    db.commit()
    return {"entry": e.code, "total": td, "lines": len(lines), "warnings": missing, **stat}


def ACC_KIND(code: str) -> str:
    return {"1": "TS", "2": "TS", "3": "NV", "4": "NV", "5": "DT", "6": "CP", "7": "DT", "8": "CP", "9": "XD"}[code[0]]


# ---------- 5. Sổ nhật ký chung ----------
def import_journal(db: Session, u: User, data: bytes, date_from: date | None = None, date_to: date | None = None, dry_run: bool = False, limit: int | None = None) -> dict:
    """Sổ nhật ký chung MISA (Ngày hạch toán, Ngày CT, Số CT, Diễn giải, Tài khoản, TK đối ứng, PS Nợ, PS Có, Mã đối tượng, Tên đối tượng)
    → mỗi số chứng từ + ngày = một chứng từ VTOS (nguồn misa, ref misa:<số CT>). Bỏ qua chứng từ đã nạp. Tài khoản chưa có → tạo."""
    # đọc luồng (không giữ toàn bộ 80.000 dòng trong bộ nhớ – máy chủ 512 MB) và lọc theo khoảng ngày ngay khi đọc
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True); ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True); hdr = None
    for r in it:
        cells = [str(c).strip().lower() for c in r if c is not None]
        if any("số chứng từ" in c for c in cells) and any("tài khoản" in c for c in cells):
            hdr = [str(c or "").strip().lower() for c in r]; break
    if hdr is None: raise ValueError("Không tìm thấy dòng tiêu đề Sổ nhật ký chung – đúng tệp MISA chưa?")
    ix = {k: next((i for i, c in enumerate(hdr) if c.startswith(k)), None) for k in ("ngày hạch toán", "ngày chứng từ", "số chứng từ", "diễn giải", "tài khoản", "tk đối ứng", "phát sinh nợ", "phát sinh có", "mã đối tượng", "tên đối tượng", "mã công trình")}
    docs: dict[tuple, dict] = {}
    for r in it:
        if r is None or len(r) <= ix["tài khoản"]: continue
        no = str(r[ix["số chứng từ"]] or "").strip(); d = _date(r[ix["ngày hạch toán"]])
        if not no or not d: continue
        if date_from and d < date_from: continue
        if date_to and d > date_to: continue
        acc = str(r[ix["tài khoản"]] or "").strip()
        if not acc.isdigit(): continue
        k = (no, d)
        doc = docs.setdefault(k, {"desc": str(r[ix["diễn giải"]] or "")[:300], "lines": []})
        doc["lines"].append({"account": acc, "debit": _num(r[ix["phát sinh nợ"]]), "credit": _num(r[ix["phát sinh có"]]),
                             "partner_code": str(r[ix["mã đối tượng"]] or "").strip() if ix["mã đối tượng"] is not None else "",
                             "partner": str(r[ix["tên đối tượng"]] or "").strip() if ix["tên đối tượng"] is not None else "",
                             "project_code": str(r[ix["mã công trình"]] or "").strip() if ix["mã công trình"] is not None else "",
                             "note": (str(r[ix["diễn giải"]] or "")[:200])})
    have = set(x for x in db.execute(select(JournalEntry.source_ref).where(JournalEntry.source_type == "misa")).scalars())
    used = set(x for x in db.execute(select(JournalEntry.code)).scalars())
    accs = {a.code for a in db.execute(select(Account)).scalars()}
    stat = {"docs": len(docs), "imported": 0, "skipped_existing": 0, "unbalanced": 0, "created_accounts": 0, "amount": 0.0, "from": None, "to": None}
    n = 0
    for (no, d), doc in sorted(docs.items(), key=lambda x: (x[0][1], x[0][0])):
        ref = f"misa:{no}:{d:%Y%m%d}"
        if ref in have: stat["skipped_existing"] += 1; continue
        td = sum(l["debit"] for l in doc["lines"]); tc = sum(l["credit"] for l in doc["lines"])
        if td <= 0 or abs(td - tc) >= 1: stat["unbalanced"] += 1; continue
        stat["imported"] += 1; stat["amount"] += td
        stat["from"] = min(stat["from"] or d, d); stat["to"] = max(stat["to"] or d, d)
        if dry_run: continue
        for l in doc["lines"]:
            if l["account"] not in accs:
                db.add(Account(code=l["account"], name=f"TK {l['account']} (MISA – chưa có tên)", kind=ACC_KIND(l["account"]), parent=l["account"][:-1] if len(l["account"]) > 3 else "", level=len(l["account"]) - 2, misa=True)); db.flush(); accs.add(l["account"]); stat["created_accounts"] += 1
        code = f"MISA-{no}"[:30]; k2 = 0
        while code in used:
            k2 += 1; code = f"MISA-{no}"[:22] + f"-{d:%m%d}" + (str(k2) if k2 > 1 else "")
        used.add(code)
        e = JournalEntry(code=code, entry_date=d, period=ACC.period_of(d), description=doc["desc"] or f"Chứng từ MISA {no}", source_type="misa", source_ref=ref,
                         status="da_ghi_so", created_by="misa", posted_by=u.username, posted_at=datetime.now())
        for l in doc["lines"]:
            e.lines.append(JournalLine(account_code=l["account"], debit=l["debit"], credit=l["credit"], partner=l["partner"][:160], partner_code=l["partner_code"][:60], project_code=l["project_code"][:40], note=l["note"]))
        db.add(e); n += 1
        if n % 500 == 0: db.flush()
        if limit and n >= limit: break
    if not dry_run:
        R.audit(db, u.username, u.role, "nap_so_nhat_ky_misa", "journal", after={k: (str(v) if isinstance(v, date) else v) for k, v in stat.items()})
        db.commit()
    wb.close(); del docs
    import gc; gc.collect()
    return stat


# ---------- 6. Đối chiếu ----------
def reconcile(db: Session, tb: bytes, column: str = "close") -> dict:
    """So số dư VTOS (chứng từ đã ghi sổ đến hết ngày cuối kỳ của tệp) với Bảng cân đối MISA theo từng tài khoản."""
    parsed = parse_trial_balance(tb)
    m = re.findall(r"(\d{2})/(\d{2})/(\d{4})", parsed["period"])
    upto = None
    if m:
        dd, mm, yy = m[-1] if column == "close" else m[0]
        upto = date(int(yy), int(mm), int(dd)) if column == "close" else date(int(yy), int(mm), int(dd))
    q = select(JournalLine.account_code, func.sum(JournalLine.debit), func.sum(JournalLine.credit)).join(JournalEntry).where(JournalEntry.status == "da_ghi_so")
    if upto: q = q.where(JournalEntry.entry_date <= upto)
    v = {}
    for code, d, c in db.execute(q.group_by(JournalLine.account_code)).all():
        v[code] = (d or 0) - (c or 0)
    # gộp lên tài khoản cha
    tot = {}
    for code, net in v.items():
        for n in range(3, len(code) + 1): tot[code[:n]] = tot.get(code[:n], 0.0) + net
    key_d, key_c = ("close_d", "close_c") if column == "close" else ("open_d", "open_c")
    out, diff_total = [], 0.0
    for r in parsed["rows"]:
        misa = r[key_d] - r[key_c]; vt = tot.get(r["code"], 0.0)
        if abs(misa - vt) >= 1:
            out.append({"account": r["code"], "name": r["name"], "misa": misa, "vtos": vt, "diff": vt - misa}); diff_total += abs(vt - misa)
    return {"period": parsed["period"], "as_of": upto, "accounts": len(parsed["rows"]), "diff_count": len(out), "diff_total": diff_total, "rows": out}


# ---------- 7. Xuất ngược sang MISA ----------
MISA_PURCHASE_COLS = ["Phương thức thanh toán", "Nhận kèm hóa đơn", "Là CP mua hàng", "Ngày hạch toán (*)", "Ngày chứng từ (*)", "Số chứng từ (*)", "Số tài khoản chi", "Tên ngân hàng chi", "Nhà cung cấp", "Tên nhà cung cấp", "Địa chỉ", "Diễn giải/Lý do chi/Nội dung thanh toán", "Số tài khoản nhận", "Tên ngân hàng nhận", "Mã nhân viên mua hàng", "Hạn thanh toán", "Loại tiền", "Tỷ giá", "Mã dịch vụ (*)", "Tên dịch vụ", "Là dòng ghi chú", "TK kho/TK chi phí (*)", "TK công nợ/TK tiền (*)", "Mã đối tượng", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Thành tiền quy đổi", "Tỷ lệ CK (%)", "Tiền chiết khấu", "Tiền chiết khấu quy đổi", "Mã khoản mục chi phí", "Mã đơn vị", "Mã đối tượng THCP", "Mã công trình", "Số đơn đặt hàng", "Số hợp đồng mua", "Số hợp đồng bán", "Mã thống kê", "Số khế ước đi vay", "Số khế ước cho vay", "CP không hợp lý", "% thuế GTGT", "% thuế suất KHAC", "Tiền thuế GTGT", "Tiền thuế GTGT quy đổi", "TK thuế GTGT", "Ngày hóa đơn", "Số hóa đơn", "Mẫu số HĐ", "Ký hiệu HĐ", "Nhóm HHDV mua vào", "Mã NCC", "Tên NCC", "Mã số thuế NCC", "Địa chỉ NCC"]
CATEGORY_ACCOUNT = {"chi_tour": "1541", "marketing": "6417", "hanh_chinh": "6428", "hoan_tien": "131", "tam_ung": "141"}


def export_purchases(db: Session, date_from: date, date_to: date) -> bytes:
    """Đề nghị chi đã duyệt/đã chi trong khoảng ngày → mẫu Import 'Mua dịch vụ' MISA (57 cột) – Kế toán nhập vào MISA khi chạy song song."""
    wb = Workbook(); ws = wb.active; ws.title = "Mua dich vu"; ws.append(MISA_PURCHASE_COLS)
    q = select(PaymentRequest).where(PaymentRequest.status.in_(["cho_chi", "da_chi"]), PaymentRequest.category.in_(list(CATEGORY_ACCOUNT)))
    for r in db.execute(q.order_by(PaymentRequest.id)).scalars():
        d = (r.approved_at or r.created_at).date()
        if d < date_from or d > date_to: continue
        t = db.get(Tour, r.tour_id) if r.tour_id else None
        row = {c: None for c in MISA_PURCHASE_COLS}
        row.update({"Phương thức thanh toán": "Chưa thanh toán" if r.status == "cho_chi" else ("Tiền mặt" if r.paid_method == "tien_mat" else "Ủy nhiệm chi"),
                    "Nhận kèm hóa đơn": "Nhận kèm hóa đơn" if r.has_invoice else "Không kèm hóa đơn", "Là CP mua hàng": "Không",
                    "Ngày hạch toán (*)": f"{d:%d/%m/%Y}", "Ngày chứng từ (*)": f"{d:%d/%m/%Y}", "Số chứng từ (*)": r.code,
                    "Nhà cung cấp": r.supplier_tax_code or "NCCLE", "Tên nhà cung cấp": r.supplier_name, "Diễn giải/Lý do chi/Nội dung thanh toán": r.description,
                    "Loại tiền": "VND", "Mã dịch vụ (*)": "Landtour" if r.category == "chi_tour" else "CPQL", "Tên dịch vụ": r.description[:100],
                    "TK kho/TK chi phí (*)": CATEGORY_ACCOUNT[r.category], "TK công nợ/TK tiền (*)": "331" if r.status == "cho_chi" else ("1111" if r.paid_method == "tien_mat" else "1121"),
                    "Mã đối tượng": r.supplier_tax_code or "NCCLE", "Số lượng": 1, "Đơn giá": r.amount, "Thành tiền": r.amount, "Thành tiền quy đổi": r.amount,
                    "Mã công trình": t.code if t else "", "Số hóa đơn": r.document_ref if r.has_invoice else None,
                    "Mã NCC": r.supplier_tax_code or "NCCLE", "Tên NCC": r.supplier_name, "Mã số thuế NCC": r.supplier_tax_code})
        ws.append([row[c] for c in MISA_PURCHASE_COLS])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def export_projects(db: Session, date_from: date | None = None) -> bytes:
    """Tour VTOS → mẫu Import 'Danh mục công trình' MISA (9 cột)."""
    wb = Workbook(); ws = wb.active; ws.title = "CongTrinh"
    ws.append(["Mã công trình (*)", "Tên công trình (*)", "Công trình phụ thuộc", "Loại công trình", "Ngày bắt đầu", "Ngày kết thúc", "Dự toán", "Chủ đầu tư", "Ghi chú"])
    q = select(Tour).where(Tour.tour_type != "non_package").order_by(Tour.start_date)
    for t in db.execute(q).scalars():
        if date_from and t.start_date < date_from: continue
        ws.append([t.code, t.name[:200], None, None, f"{t.start_date:%d/%m/%Y}", f"{t.end_date:%d/%m/%Y}", t.fixed_cost + t.var_cost_per_pax * t.planned_pax, None, "VTOS"])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def export_general_entries(db: Session, date_from: date, date_to: date, sources: tuple = ("thu_tien", "hoa_don", "quyet_toan", "thu_cong", "luong")) -> bytes:
    """Chứng từ VTOS đã ghi sổ → mẫu 'Bút toán tổng hợp' MISA (Số CT, Ngày CT, Ngày HT, Diễn giải, TK Nợ, TK Có, Số tiền, Mã công trình Nợ/Có)."""
    wb = Workbook(); ws = wb.active; ws.title = "IMPORT_DATA"
    ws.append(["Số chứng từ", "Ngày chứng từ", "Ngày hạch toán", "Diễn giải", "Tài khoản Nợ", "Tài khoản Có", "Số tiền", "Mã công trình (Ghi TK nợ)", "Mã công trình (Ghi TK có)", "Mã đối tượng"])
    q = select(JournalEntry).where(JournalEntry.status == "da_ghi_so", JournalEntry.entry_date >= date_from, JournalEntry.entry_date <= date_to, JournalEntry.source_type.in_(sources)).order_by(JournalEntry.entry_date, JournalEntry.id)
    for e in db.execute(q).scalars():
        debits = [l for l in e.lines if l.debit]; credits = [l for l in e.lines if l.credit]
        if len(debits) == 1 or len(credits) == 1:   # 1 Nợ – nhiều Có hoặc ngược lại
            for dl in debits:
                for cl in credits:
                    amt = cl.credit if len(debits) == 1 else dl.debit
                    ws.append([e.code, f"{e.entry_date:%d/%m/%Y}", f"{e.entry_date:%d/%m/%Y}", e.description, dl.account_code, cl.account_code, amt, dl.project_code, cl.project_code, dl.partner_code or cl.partner_code])
        else:
            for l in e.lines:
                ws.append([e.code, f"{e.entry_date:%d/%m/%Y}", f"{e.entry_date:%d/%m/%Y}", e.description, l.account_code if l.debit else "", l.account_code if l.credit else "", l.debit or l.credit, l.project_code if l.debit else "", l.project_code if l.credit else "", l.partner_code])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def partner_lookup(db: Session, q: str, kind: str | None = None, limit: int = 30) -> list[dict]:
    s = select(Partner).where(Partner.active == True)
    if kind == "kh": s = s.where(Partner.is_customer == True)
    if kind == "ncc": s = s.where(Partner.is_supplier == True)
    if q: s = s.where((Partner.name.ilike(f"%{q}%")) | (Partner.code.ilike(f"%{q}%")) | (Partner.trade_name.ilike(f"%{q}%")))
    return [{"code": p.code, "name": p.name, "trade_name": p.trade_name, "tax_code": p.tax_code, "kind": p.kind, "is_customer": p.is_customer, "is_supplier": p.is_supplier, "address": p.address} for p in db.execute(s.order_by(Partner.name).limit(limit)).scalars()]
