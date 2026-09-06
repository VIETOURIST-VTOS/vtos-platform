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
import re
from collections import Counter
from datetime import date
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.banks import BankAccount, CURRENCIES
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

def suggest_from_ledger(db: Session, since: date, upto: date, top: int = 25) -> dict:
    """Thống kê tiền tố số chứng từ và tên ngân hàng xuất hiện trên sổ 112, để Kế toán biết cần mở những
    tài khoản ngân hàng nào. Sổ MISA đánh số chứng từ theo tài khoản ngân hàng nên tiền tố là căn cứ tốt nhất."""
    codes = _subtree_codes(db, BANK_ROOT)
    rows = db.execute(
        select(JournalEntry.code, JournalEntry.description, func.count(JournalLine.id))
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since, JournalEntry.entry_date <= upto,
               JournalLine.account_code.in_(codes))
        .group_by(JournalEntry.code, JournalEntry.description)).all()
    pre, hints, total = Counter(), Counter(), 0
    for code, desc, n in rows:
        total += n
        head = re.sub(r"^MISA-", "", (code or "").upper()).split("-")[0]
        head = re.sub(r"\d{4,}.*$", "#", head)                   # gộp dãy số dài thành #
        if head:
            pre[head] += n
        text = f"{code or ''} {desc or ''}".upper()
        for b in BANK_HINTS:
            if re.search(rf"\b{re.escape(b)}", text):
                hints[b] += n
                break
    taken = {p for b in db.execute(select(BankAccount)).scalars() for p in (b.match_prefixes or [])}
    return {"since": since, "upto": upto, "total_lines": total,
            "prefixes": [{"prefix": k, "lines": v, "share": round(100 * v / total, 1) if total else 0,
                          "da_gan": k in taken} for k, v in pre.most_common(top)],
            "bank_hints": [{"bank": k, "lines": v} for k, v in hints.most_common(top)]}


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

def _match(banks: list[BankAccount], entry_code: str, description: str, parent: str) -> tuple[BankAccount | None, str]:
    """Tìm tài khoản ngân hàng khớp. Ưu tiên tiền tố số chứng từ (đáng tin), sau mới tới từ khóa diễn giải."""
    code_u = re.sub(r"^MISA-", "", (entry_code or "").upper())
    for b in banks:
        if b.parent_account != parent:
            continue
        for p in (b.match_prefixes or []):
            if code_u.startswith(p):
                return b, f"số chứng từ bắt đầu bằng {p}"
    text = f"{entry_code or ''} {description or ''}".upper()
    for b in banks:
        if b.parent_account != parent:
            continue
        for k in (b.match_keywords or []):
            if re.search(rf"\b{re.escape(k)}", text):
                return b, f"diễn giải chứa {k}"
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

    q = (select(JournalLine.id, JournalLine.account_code, JournalEntry.code, JournalEntry.description)
         .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
         .where(JournalEntry.status == POSTED, JournalEntry.entry_date >= since, JournalEntry.entry_date <= upto,
                JournalLine.account_code.in_(parents)))
    hit: dict[str, list[int]] = {}
    reasons: Counter = Counter()
    samples: dict[str, list] = {}
    unmatched, scanned = 0, 0
    unmatched_prefix: Counter = Counter()
    for lid, acc, ecode, desc in db.execute(q).all():
        scanned += 1
        b, why = _match(banks, ecode, desc, acc)
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
           "matched": sum(len(v) for v in hit.values()), "unmatched": unmatched,
           "by_bank": by_bank, "reasons": dict(reasons.most_common(20)),
           "unmatched_prefixes": [{"prefix": k, "lines": v} for k, v in unmatched_prefix.most_common(15)],
           "balance_before": before}
    if not apply:
        out["ghi_chu"] = ("Đây mới là bản xem trước, chưa đụng vào sổ. Dòng không nhận diện được vẫn nằm ở tài "
                          "khoản cha – bổ sung tiền tố/từ khóa cho tài khoản ngân hàng rồi xem lại.")
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
    q = (select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0.0))
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
