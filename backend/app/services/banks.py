"""Tài khoản ngân hàng: mở tiểu khoản 112 cho từng ngân hàng và gán lại sổ cũ về đúng tiểu khoản.

Ba việc, làm theo đúng thứ tự an toàn:
  1. gợi ý (suggest_from_ledger)  – đọc sổ 112 hiện có, thống kê tiền tố số chứng từ để Kế toán biết trên sổ
     đang có những tài khoản ngân hàng nào, khỏi phải tự mò.
  2. mở tài khoản (create)        – tạo bản ghi danh mục + TỰ SINH tiểu khoản 112 dưới 1121/1122. Tiểu khoản
     không đặt ánh xạ chỉ tiêu BCTC nên báo cáo tự lấy theo tài khoản cha ⇒ BCTC không đổi một đồng.
  3. gán lại sổ cũ (preview → apply) – chuyển dòng đang nằm ở tài khoản cha sang tiểu khoản đúng ngân hàng.

Nguyên tắc an toàn của bước 3 – đây là thao tác động vào sổ đã ghi nên phải chặt:
  - CHỈ đổi mã tài khoản trong cùng một cây 112, không đổi số tiền, không đổi ngày, không đổi chứng từ ⇒ tổng
    phát sinh và số dư 112 phải y nguyên. Hàm apply tự KIỂM CHỨNG điều này trước/sau; lệch một đồng là hoàn tác.
  - Chỉ đổi dòng đang ở tài khoản CHA (1121/1122); dòng đã gán tiểu khoản rồi thì không đụng vào.
  - Dòng nào không quy tắc nào khớp thì để nguyên, và báo rõ còn bao nhiêu dòng chưa nhận diện được – thà để
    trống còn hơn gán sai làm sai sổ tiền gửi.
  - Ghi nhật ký kiểm toán và trả về đủ thông tin để hoàn tác (revert) nếu Kế toán thấy sai.
"""
import csv
import io
import re
from collections import Counter, defaultdict
from datetime import date
from openpyxl import load_workbook
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import Session
from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.banks import BankAccount, BankDocMap, CURRENCIES
from app.models.core import User
from app.services import rules as R

BANK_ROOT = "112"
POSTED = "da_ghi_so"
# Tên ngân hàng hay gặp trên diễn giải sao kê – dùng để GỢI Ý, không dùng để tự gán.
BANK_HINTS = ["TPBANK", "TPB", "VIETCOMBANK", "VCB", "MBBANK", "MB", "BIDV", "ACB", "TECHCOMBANK", "TCB",
              "VIETINBANK", "SACOMBANK", "AGRIBANK", "VPBANK", "HDBANK", "SHB", "OCB", "EXIMBANK", "MSB", "VIB"]


def _parent_of(currency: str) -> str:
    return CURRENCIES.get(currency, CURRENCIES["VND"])["tk_cha"]


def bank_subaccounts(db: Session) -> dict[str, BankAccount]:
    """{mã tiểu khoản 112: tài khoản ngân hàng}."""
    return {b.account_code: b for b in db.execute(select(BankAccount).where(BankAccount.account_code != "")).scalars()}


def _next_sub_code(db: Session, parent: str) -> str:
    """Mã tiểu khoản kế tiếp dưới 1121/1122: 11211, 11212… (bỏ qua mã đã có)."""
    used = {a.code for a in db.execute(select(Account).where(Account.parent == parent)).scalars()}
    for i in range(1, 100):
        code = f"{parent}{i}" if i < 10 else f"{parent}{i}"
        if code not in used and not db.get(Account, code):
            return code
    raise ValueError(f"Không còn mã tiểu khoản trống dưới {parent}")


def ensure_sub_account(db: Session, b: BankAccount) -> Account:
    """Tạo (hoặc lấy) tiểu khoản 112 cho một tài khoản ngân hàng, kế thừa chỉ tiêu BCTC từ tài khoản cha."""
    parent = db.get(Account, b.parent_account)
    if not parent:
        raise ValueError(f"Không có tài khoản cha {b.parent_account} trong danh mục")
    if b.account_code:
        acc = db.get(Account, b.account_code)
        if acc:
            return acc
    code = b.account_code or _next_sub_code(db, b.parent_account)
    acc = db.get(Account, code)
    if not acc:
        acc = Account(code=code, name=f"{b.bank_name} – {b.account_number}"[:200], kind=parent.kind,
                      parent=parent.code, level=parent.level + 1, is_detail=True,
                      bs_debit="", bs_credit="", pl_code="", misa=False)   # để trống ⇒ BCTC lấy theo TK cha
        db.add(acc)
        parent.is_detail = False
    b.account_code = code
    return acc


def create_bank_account(db: Session, u: User, data: dict) -> BankAccount:
    cur = (data.get("currency") or "VND").upper()
    if cur not in CURRENCIES:
        raise ValueError(f"Loại tiền {cur} chưa hỗ trợ")
    code = (data.get("code") or "").strip().upper()[:20]
    if not code:
        raise ValueError("Thiếu mã tài khoản ngân hàng")
    if db.execute(select(BankAccount).where(BankAccount.code == code)).scalar_one_or_none():
        raise ValueError(f"Mã {code} đã tồn tại")
    if not (data.get("bank_name") or "").strip():
        raise ValueError("Thiếu tên ngân hàng")
    b = BankAccount(code=code, bank_name=data["bank_name"].strip()[:120],
                    account_number=(data.get("account_number") or "").strip()[:40],
                    account_name=(data.get("account_name") or "")[:200], branch=(data.get("branch") or "")[:120],
                    currency=cur, parent_account=_parent_of(cur),
                    match_prefixes=[str(x).strip().upper() for x in (data.get("match_prefixes") or []) if str(x).strip()],
                    match_keywords=[str(x).strip().upper() for x in (data.get("match_keywords") or []) if str(x).strip()],
                    sepay_account_number=(data.get("sepay_account_number") or "")[:40],
                    opening_balance=float(data.get("opening_balance") or 0),
                    note=(data.get("note") or "")[:300], created_by=u.username)
    db.add(b); db.flush()
    ensure_sub_account(db, b)
    R.audit(db, u.username, u.role, "mo_tai_khoan_ngan_hang", f"nh:{b.code}",
            after={"ngan_hang": b.bank_name, "so_tk": b.account_number, "tieu_khoan": b.account_code})
    db.commit()
    return b


# ---------- Gợi ý từ sổ hiện có ----------

SCAN_LIMIT = 20000       # trần số dòng quét khi thống kê tiền tố / dò tên ngân hàng


def suggest_from_ledger(db: Session, since: date, upto: date, top: int = 25,
                        scan_limit: int = SCAN_LIMIT) -> dict:
    """Thống kê tiền tố số chứng từ và tên ngân hàng xuất hiện trên sổ 112, để Kế toán biết cần mở những
    tài khoản ngân hàng nào. Sổ MISA đánh số chứng từ theo tài khoản ngân hàng nên tiền tố là căn cứ tốt nhất.

    Đây là công cụ dùng MỘT LẦN lúc khai báo, không phải báo cáo chạy hằng ngày, nên chỉ quét tối đa
    scan_limit dòng: thống kê tiền tố chỉ cần đủ đại diện để Kế toán chọn, còn tổng số dòng vẫn đếm chính xác
    bằng một câu COUNT. Trường "scanned" cho biết đã quét bao nhiêu dòng trong tổng số, "sampled" cho biết
    thống kê tiền tố là ước lượng hay đã quét hết – không giấu chuyện đây là mẫu."""
    codes = _subtree_codes(db, BANK_ROOT)
    base = (JournalEntry.status == POSTED, JournalEntry.entry_date >= since,
            JournalEntry.entry_date <= upto, JournalLine.account_code.in_(codes))
    total = int(db.execute(select(func.count(JournalLine.id))
                           .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
                           .where(*base)).scalar() or 0)
    rows = db.execute(
        select(JournalEntry.code, JournalEntry.description)
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(*base).limit(scan_limit)).all()
    pre, hints = Counter(), Counter()
    for code, desc in rows:
        head = re.sub(r"^MISA-", "", (code or "").upper()).split("-")[0]
        head = re.sub(r"\d{4,}.*$", "#", head)                   # gộp dãy số dài thành #
        if head:
            pre[head] += 1
        text = f"{code or ''} {desc or ''}".upper()
        for b in BANK_HINTS:
            if re.search(rf"\b{re.escape(b)}", text):
                hints[b] += 1
                break
    scanned = len(rows)
    taken = {p for b in db.execute(select(BankAccount)).scalars() for p in (b.match_prefixes or [])}
    return {"since": since, "upto": upto, "total_lines": total, "scanned": scanned,
            "sampled": scanned < total,
            "prefixes": [{"prefix": k, "lines": v, "share": round(100 * v / scanned, 1) if scanned else 0,
                          "da_gan": k in taken} for k, v in pre.most_common(top)],
            "bank_hints": [{"bank": k, "lines_in_scan": v} for k, v in hints.most_common(top)]}


def _subtree_codes(db: Session, root: str) -> list[str]:
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    if root not in accs:
        raise ValueError(f"Không có tài khoản {root}")
    children: dict[str, list[str]] = {}
    for a in accs.values():
        if a.parent:
            children.setdefault(a.parent, []).append(a.code)
    out, stack = [], [root]
    while stack:
        c = stack.pop()
        out.append(c)
        stack.extend(children.get(c, []))
    return out


# ---------- Gán lại sổ cũ về đúng tiểu khoản ----------

def _match(banks: list[BankAccount], entry_code: str, description: str, parent: str,
           amount: float = 0.0, side: str = "", exact: dict | None = None, single: dict | None = None
           ) -> tuple[BankAccount | None, str]:
    """Tìm tài khoản ngân hàng của một dòng sổ, theo thứ tự tin cậy giảm dần:

    1. BẢN ĐỒ từ Sổ tiền gửi MISA khớp đủ (số chứng từ, số tiền, chiều thu/chi) – chính xác tuyệt đối, kể cả
       chứng từ chuyển tiền nội bộ có mặt ở hai ngân hàng.
    2. Bản đồ chỉ theo số chứng từ, khi chứng từ đó chỉ thuộc MỘT ngân hàng (số tiền có thể lệch do ghi sổ
       tách dòng) – vẫn chắc chắn vì không có ngân hàng nào khác dùng số chứng từ này.
    3. Tiền tố số chứng từ / từ khóa diễn giải do Kế toán khai – CHỈ dùng khi không có bản đồ, và phải hiểu
       đây là suy đoán: đo trên sổ thật, tiền tố "FT…" xuất hiện ở 6 ngân hàng khác nhau nên tuyệt đối không
       nên dựa vào nếu đã có file Sổ tiền gửi.
    """
    by_code = {b.code: b for b in banks}
    doc = _doc_of(entry_code)
    if exact and side:
        bc = exact.get((doc, round(amount, 0), side))
        if bc and bc in by_code:
            return by_code[bc], "khớp Sổ tiền gửi MISA (chứng từ + số tiền + thu/chi)"
    if single:
        bc = single.get(doc)
        if bc and bc in by_code:
            return by_code[bc], "khớp Sổ tiền gửi MISA (số chứng từ chỉ thuộc 1 ngân hàng)"
    code_u = re.sub(r"^MISA-", "", (entry_code or "").upper())
    for b in banks:
        if b.parent_account != parent:
            continue
        for p in (b.match_prefixes or []):
            if code_u.startswith(p):
                return b, f"suy đoán theo tiền tố {p}"
    text = f"{entry_code or ''} {description or ''}".upper()
    for b in banks:
        if b.parent_account != parent:
            continue
        for k in (b.match_keywords or []):
            if re.search(rf"\b{re.escape(k)}", text):
                return b, f"suy đoán theo diễn giải chứa {k}"
    return None, ""


def classify(db: Session, since: date, upto: date, apply: bool = False, u: User | None = None) -> dict:
    """Xem trước (apply=False) hoặc thực hiện (apply=True) việc gán dòng sổ 112 về đúng tiểu khoản ngân hàng.

    Chỉ xử lý dòng đang nằm ở tài khoản CHA (1121/1122); dòng đã có tiểu khoản thì bỏ qua."""
    banks = list(db.execute(select(BankAccount).where(BankAccount.active == True)).scalars())
    if not banks:
        raise ValueError("Chưa khai báo tài khoản ngân hàng nào – mở danh mục trước khi gán sổ")
    for b in banks:
        if not b.account_code:
            ensure_sub_account(db, b)
    parents = sorted({b.parent_account for b in banks})
    before = _balance(db, _subtree_codes(db, BANK_ROOT), upto)

    exact, single = load_doc_map(db)
    q = (select(JournalLine.id, JournalLine.account_code, JournalEntry.code, JournalEntry.description,
                JournalLine.debit, JournalLine.credit)
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since, JournalEntry.entry_date <= upto,
                JournalLine.account_code.in_(parents)))
    hit: dict[str, list[int]] = {}
    reasons: Counter = Counter()
    samples: dict[str, list] = {}
    unmatched, scanned = 0, 0
    unmatched_prefix: Counter = Counter()
    for lid, acc, ecode, desc, dr, cr in db.execute(q).all():
        scanned += 1
        amount = float(dr or 0) if (dr or 0) > 0 else float(cr or 0)
        side = "thu" if (dr or 0) > 0 else "chi"
        b, why = _match(banks, ecode, desc, acc, amount, side, exact, single)
        if not b:
            unmatched += 1
            head = re.sub(r"^MISA-", "", (ecode or "").upper()).split("-")[0]
            unmatched_prefix[re.sub(r"\d{4,}.*$", "#", head)] += 1
            continue
        hit.setdefault(b.code, []).append(lid)
        reasons[f"{b.code}: {why}"] += 1
        samples.setdefault(b.code, [])
        if len(samples[b.code]) < 3:
            samples[b.code].append({"entry_code": ecode, "description": (desc or "")[:80], "ly_do": why})

    by_bank = [{"code": c, "bank": next(b.bank_name for b in banks if b.code == c),
                "account_code": next(b.account_code for b in banks if b.code == c),
                "lines": len(ids), "samples": samples.get(c, [])} for c, ids in sorted(hit.items())]
    out = {"since": since, "upto": upto, "applied": False, "scanned": scanned,
           "co_ban_do_misa": len(exact) > 0, "so_dong_ban_do": len(exact),
           "matched": sum(len(v) for v in hit.values()), "unmatched": unmatched,
           "by_bank": by_bank, "reasons": dict(reasons.most_common(20)),
           "unmatched_prefixes": [{"prefix": k, "lines": v} for k, v in unmatched_prefix.most_common(15)],
           "balance_before": before}
    if not apply:
        out["ghi_chu"] = ("Đây mới là bản xem trước, chưa đụng vào sổ. Dòng không nhận diện được vẫn nằm ở tài "
                          "khoản cha." + ("" if exact else " CHƯA nạp Sổ tiền gửi ngân hàng của MISA nên đang phải "
                          "suy đoán theo tiền tố – nạp file đó vào sẽ gán chính xác gần như tuyệt đối."))
        return out

    if not u:
        raise ValueError("Thiếu người thực hiện")
    changed = 0
    for bank_code, ids in hit.items():
        target = next(b.account_code for b in banks if b.code == bank_code)
        for i in range(0, len(ids), 500):
            db.execute(update(JournalLine).where(JournalLine.id.in_(ids[i:i + 500]))
                       .values(account_code=target))
            changed += len(ids[i:i + 500])
    db.flush()
    after = _balance(db, _subtree_codes(db, BANK_ROOT), upto)
    if abs(after - before) >= 1:                                  # chốt chặn: chỉ đổi mã TK, số dư phải y nguyên
        db.rollback()
        raise ValueError(f"Đã hoàn tác: số dư 112 thay đổi sau khi gán ({before:,.0f} → {after:,.0f}) – "
                         f"đây là lỗi nghiêm trọng, không được phép xảy ra khi chỉ đổi mã tài khoản")
    R.audit(db, u.username, u.role, "gan_tieu_khoan_ngan_hang", f"nh:{since}:{upto}",
            after={"so_dong_doi": changed, "theo_ngan_hang": {b["code"]: b["lines"] for b in by_bank},
                   "chua_nhan_dien": unmatched, "so_du_112_truoc": before, "so_du_112_sau": after})
    db.commit()
    out.update({"applied": True, "changed": changed, "balance_after": after})
    return out


def revert(db: Session, u: User, bank_code: str, since: date, upto: date) -> dict:
    """Trả các dòng của một tài khoản ngân hàng về lại tài khoản cha (dùng khi gán nhầm)."""
    b = db.execute(select(BankAccount).where(BankAccount.code == bank_code.upper())).scalar_one_or_none()
    if not b or not b.account_code:
        raise ValueError(f"Không có tài khoản ngân hàng {bank_code}")
    before = _balance(db, _subtree_codes(db, BANK_ROOT), upto)
    ids = [r[0] for r in db.execute(
        select(JournalLine.id).join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since, JournalEntry.entry_date <= upto,
               JournalLine.account_code == b.account_code)).all()]
    for i in range(0, len(ids), 500):
        db.execute(update(JournalLine).where(JournalLine.id.in_(ids[i:i + 500])).values(account_code=b.parent_account))
    db.flush()
    after = _balance(db, _subtree_codes(db, BANK_ROOT), upto)
    if abs(after - before) >= 1:
        db.rollback()
        raise ValueError("Đã hoàn tác: số dư 112 thay đổi khi trả về tài khoản cha")
    R.audit(db, u.username, u.role, "huy_gan_tieu_khoan_ngan_hang", f"nh:{b.code}",
            after={"so_dong": len(ids), "ve_tai_khoan": b.parent_account})
    db.commit()
    return {"bank_code": b.code, "reverted": len(ids), "to_account": b.parent_account}


def _balance(db: Session, codes: list[str], upto: date) -> float:
    q = (select(func.coalesce(func.sum(func.coalesce(JournalLine.debit, 0) - func.coalesce(JournalLine.credit, 0)), 0.0))
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == POSTED, JournalEntry.entry_date <= upto,
                JournalLine.account_code.in_(codes)))
    return round(float(db.execute(q).scalar() or 0.0), 0)


# ---------- Số dư từng ngân hàng ----------

def balances(db: Session, since: date, upto: date) -> dict:
    """Số dư đầu – phát sinh – số dư cuối của TỪNG tài khoản ngân hàng (theo tiểu khoản 112),
    kèm phần còn nằm ở tài khoản cha (chưa nhận diện được ngân hàng)."""
    banks = list(db.execute(select(BankAccount).order_by(BankAccount.code)).scalars())
    rows = []
    for b in banks:
        if not b.account_code:
            continue
        codes = [b.account_code]
        op = _balance(db, codes, since_minus(since))
        q = (select(func.coalesce(func.sum(JournalLine.debit), 0.0), func.coalesce(func.sum(JournalLine.credit), 0.0))
             .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
             .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since,
                    JournalEntry.entry_date <= upto, JournalLine.account_code.in_(codes)))
        d, c = db.execute(q).one()
        rows.append({"code": b.code, "bank_name": b.bank_name, "account_number": b.account_number,
                     "currency": b.currency, "account_code": b.account_code,
                     "opening": op, "debit": round(float(d or 0), 0), "credit": round(float(c or 0), 0),
                     "closing": round(op + float(d or 0) - float(c or 0), 0)})
    parents = sorted({b.parent_account for b in banks}) or ["1121", "1122"]
    un_open = _balance(db, parents, since_minus(since))
    q = (select(func.coalesce(func.sum(JournalLine.debit), 0.0), func.coalesce(func.sum(JournalLine.credit), 0.0))
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since,
                JournalEntry.entry_date <= upto, JournalLine.account_code.in_(parents)))
    ud, uc = db.execute(q).one()
    unassigned = {"accounts": parents, "opening": un_open, "debit": round(float(ud or 0), 0),
                  "credit": round(float(uc or 0), 0),
                  "closing": round(un_open + float(ud or 0) - float(uc or 0), 0)}
    total_close = round(sum(r["closing"] for r in rows) + unassigned["closing"], 0)
    return {"since": since, "upto": upto, "rows": rows, "unassigned": unassigned,
            "total_closing": total_close,
            "check_112": _balance(db, _subtree_codes(db, BANK_ROOT), upto)}


def since_minus(d: date) -> date:
    from datetime import timedelta
    return d - timedelta(days=1)


# ---------- Nạp bản đồ chứng từ → ngân hàng từ "Sổ tiền gửi ngân hàng" của MISA ----------

SECTION = "tài khoản ngân hàng:"



def _sheet_rows(data: bytes):
    """Duyệt từng dòng của file Excel (.xlsx) hoặc CSV. Nhận cả hai vì bảng 22.000 dòng ở dạng CSV nhẹ hơn
    nhiều lần, mà MISA xuất được cả hai định dạng."""
    if data[:2] == b"PK":                                  # .xlsx là tệp nén, luôn bắt đầu bằng "PK"
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        yield from wb.worksheets[0].iter_rows(values_only=True)
        return
    for enc in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Không đọc được nội dung tệp – hãy xuất lại dạng Excel (.xlsx) hoặc CSV UTF-8")
    sample = text[:4000]
    delim = max([",", ";", "\t"], key=sample.count)
    for row in csv.reader(io.StringIO(text), delimiter=delim):
        yield tuple(row)


def parse_bank_book(data: bytes) -> dict:
    """Đọc file "Sổ tiền gửi ngân hàng" xuất từ MISA.

    Nhận cả .xlsx lẫn .csv.
    Bố cục: các dòng phát sinh được chia thành từng đoạn, mở đầu mỗi đoạn là ô "Tài khoản ngân hàng:
    <số tài khoản> - <tên ngân hàng>". Các cột: Ngày hạch toán, Ngày chứng từ, Số chứng từ, Diễn giải,
    TK đối ứng, Thu, Chi, Tồn. Dòng không có số chứng từ là dòng số dư đầu kỳ / cộng phát sinh – bỏ qua.
    """
    accounts: dict[str, str] = {}
    entries: list[dict] = []
    cur = ""
    for row in _sheet_rows(data):
        if not row:
            continue
        a0 = str(row[0] or "").strip()
        if a0.lower().startswith(SECTION):
            label = a0.split(":", 1)[1].strip()
            no, _, name = label.partition("-")
            cur = no.strip()[:20]
            if cur:
                accounts.setdefault(cur, name.strip()[:120] or "Ngân hàng")
            continue
        if not cur or len(row) < 7 or not row[2]:
            continue
        doc = str(row[2]).strip()
        if not doc or doc.lower().startswith(("số dư", "cộng", "tổng")):
            continue

        def num(x):
            try:
                return round(float(x or 0), 0)
            except (TypeError, ValueError):
                return 0.0
        thu, chi = num(row[5]), num(row[6])
        if thu > 0:
            entries.append({"bank_code": cur, "doc_no": doc[:60], "amount": thu, "side": "thu"})
        if chi > 0:
            entries.append({"bank_code": cur, "doc_no": doc[:60], "amount": chi, "side": "chi"})
    if not accounts:
        raise ValueError('Không thấy dòng "Tài khoản ngân hàng:" nào – đây có phải file Sổ tiền gửi ngân hàng '
                         'xuất từ MISA không? Cần bản in THEO TỪNG TÀI KHOẢN NGÂN HÀNG.')
    by_doc: dict[str, set] = defaultdict(set)
    for e in entries:
        by_doc[e["doc_no"]].add(e["bank_code"])
    return {"accounts": accounts, "entries": entries,
            "docs": len(by_doc), "multi_bank_docs": sum(1 for v in by_doc.values() if len(v) > 1)}


def import_bank_book(db: Session, u: User, data: bytes, filename: str = "") -> dict:
    """Nạp file Sổ tiền gửi: tự mở tài khoản ngân hàng còn thiếu (kèm tiểu khoản 112) và ghi bản đồ chứng từ.

    Nạp lại cùng một ngân hàng thì THAY THẾ bản đồ cũ của ngân hàng đó, để chạy lại nhiều lần vẫn ra một kết
    quả. Việc này KHÔNG đụng vào sổ – chỉ dựng bản đồ; muốn đổi sổ phải chạy tiếp bước gán và có xem trước."""
    parsed = parse_bank_book(data)
    created = []
    for code, name in parsed["accounts"].items():
        b = db.execute(select(BankAccount).where(BankAccount.code == code)).scalar_one_or_none()
        if b is None:
            b = BankAccount(code=code, bank_name=name, account_number=code, currency="VND",
                            parent_account=_parent_of("VND"), match_prefixes=[], match_keywords=[],
                            created_by=u.username, note="Tự mở khi nạp Sổ tiền gửi ngân hàng từ MISA")
            db.add(b); db.flush()
            created.append(code)
        elif not b.bank_name:
            b.bank_name = name
        ensure_sub_account(db, b)
    db.execute(delete(BankDocMap).where(BankDocMap.bank_code.in_(list(parsed["accounts"]))))
    db.flush()
    for e in parsed["entries"]:
        db.add(BankDocMap(bank_code=e["bank_code"], doc_no=e["doc_no"], amount=e["amount"],
                          side=e["side"], source_file=filename[:120]))
    R.audit(db, u.username, u.role, "nap_so_tien_gui_misa", f"nh:{filename[:40]}",
            after={"so_tai_khoan": len(parsed["accounts"]), "moi_mo": created,
                   "so_dong_ban_do": len(parsed["entries"]), "so_chung_tu": parsed["docs"]})
    db.commit()
    banks = {b.code: b for b in db.execute(select(BankAccount)).scalars()}
    return {"accounts": [{"code": c, "bank_name": parsed["accounts"][c],
                          "account_code": banks[c].account_code if c in banks else "",
                          "moi_mo": c in created,
                          "lines": sum(1 for e in parsed["entries"] if e["bank_code"] == c)}
                         for c in sorted(parsed["accounts"], key=lambda c: -sum(1 for e in parsed["entries"] if e["bank_code"] == c))],
            "map_rows": len(parsed["entries"]), "docs": parsed["docs"],
            "multi_bank_docs": parsed["multi_bank_docs"], "created": created}


def _doc_of(entry_code: str) -> str:
    """Số chứng từ MISA nằm trong mã chứng từ VTOS dưới dạng "MISA-<số chứng từ>"."""
    return re.sub(r"^MISA-", "", (entry_code or "").strip())


def load_doc_map(db: Session) -> tuple[dict, dict]:
    """(bản đồ khớp đủ 3 yếu tố, bản đồ chỉ theo số chứng từ khi chứng từ đó chỉ thuộc 1 ngân hàng)."""
    exact: dict[tuple, str] = {}
    by_doc: dict[str, set] = defaultdict(set)
    for m in db.execute(select(BankDocMap)).scalars():
        exact[(m.doc_no, round((m.amount or 0), 0), m.side)] = m.bank_code
        by_doc[m.doc_no].add(m.bank_code)
    single = {d: next(iter(v)) for d, v in by_doc.items() if len(v) == 1}
    return exact, single
