"""Robot R1 – Thu tiền: nhận giao dịch SePay, khớp booking, sinh phiếu thu.

Quy tắc (mục 7.1 VTOS): robot chỉ tự động khi khớp TUYỆT ĐỐI mã booking + số tiền còn phải thu;
mọi trường hợp khác đưa vào hàng chờ Kế toán. Giao dịch ngân hàng là bản ghi bất biến.
"""
import re
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Booking, User
from app.models.payments import BankTransaction, Receipt
from app.services import rules as R

BOOKING_RE = re.compile(r"BK\s?(\d{8})", re.IGNORECASE)


def paid_amount(db: Session, booking_id: int) -> float:
    return db.execute(select(func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id == booking_id, Receipt.status != "huy")).scalar() or 0.0


def _next_receipt_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(Receipt)).scalar() + 1
    return f"PT{date.today():%y%m}-{n:04d}"


def _make_receipt(db: Session, booking: Booking, txn: BankTransaction | None, amount: float, actor: str, status: str, payer: str = "", note: str = "") -> Receipt:
    r = Receipt(code=_next_receipt_code(db), booking_id=booking.id, bank_txn_id=txn.id if txn else None, amount=amount,
                method="chuyen_khoan" if txn else "tien_mat", payer=payer or booking.customer_name, note=note,
                status=status, created_by=actor)
    db.add(r); db.flush()
    booking.paid = paid_amount(db, booking.id)
    return r


def ingest_sepay(db: Session, payload: dict) -> tuple[BankTransaction, bool]:
    """Ghi nhận webhook SePay. Trả về (giao dịch, mới_hay_không). Idempotent theo sepay_id."""
    sid = str(payload.get("id") or payload.get("sepay_id") or "")
    if not sid:
        raise ValueError("Thiếu id giao dịch")
    existing = db.execute(select(BankTransaction).where(BankTransaction.sepay_id == sid)).scalars().first()
    if existing:
        return existing, False
    amt_in = float(payload.get("transferAmount") or payload.get("amount_in") or 0)
    amt_out = float(payload.get("amount_out") or 0)
    ttype = (payload.get("transferType") or ("in" if amt_in > 0 else "out")).lower()
    amount = amt_in if ttype == "in" else (amt_out or amt_in)
    tdate = payload.get("transactionDate") or payload.get("transaction_date")
    try:
        tdt = datetime.fromisoformat(str(tdate).replace("Z", "")) if tdate else datetime.now()
    except ValueError:
        tdt = datetime.now()
    txn = BankTransaction(sepay_id=sid, gateway=str(payload.get("gateway") or ""), account_number=str(payload.get("accountNumber") or payload.get("account_number") or ""),
                          transaction_date=tdt, transfer_type=ttype, amount=amount,
                          content=str(payload.get("content") or payload.get("description") or ""),
                          reference_code=str(payload.get("referenceCode") or payload.get("reference_number") or ""), raw=payload)
    db.add(txn); db.flush()
    R.audit(db, "sepay", "robot", "nhan_giao_dich_ngan_hang", f"bank:{sid}", after={"loai": ttype, "so_tien": amount, "noi_dung": txn.content[:80]})
    if ttype == "in":
        match_transaction(db, txn)
    else:
        txn.match_status, txn.match_note = "bo_qua", "Tiền ra – theo dõi ở phân hệ chi"
    db.commit()
    return txn, True


def match_transaction(db: Session, txn: BankTransaction) -> None:
    """R1: tìm mã BKxxxxxxxx trong nội dung; khớp tuyệt đối số tiền còn phải thu → phiếu thu tự động."""
    m = BOOKING_RE.search(txn.content.replace(" ", "") if txn.content else "")
    if not m:
        txn.match_status, txn.match_note = "cho_ke_toan", "Không thấy mã booking trong nội dung chuyển khoản"
        return
    code = "BK" + m.group(1)
    b = db.execute(select(Booking).where(Booking.code == code)).scalars().first()
    if not b:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Mã {code} không tồn tại"
        return
    due = (b.amount - b.discount) - paid_amount(db, b.id)
    if abs(txn.amount - due) < 1 or (due > 0 and abs(txn.amount - (b.amount - b.discount)) < 1 and paid_amount(db, b.id) == 0):
        r = _make_receipt(db, b, txn, txn.amount, "robot", "tu_dong", note="Khớp tuyệt đối mã + số tiền")
        txn.match_status, txn.booking_id, txn.match_note = "da_khop", b.id, f"Tự động: {r.code}"
        R.audit(db, "robot", "robot", "sinh_phieu_thu_tu_dong", f"receipt:{r.code}", after={"booking": b.code, "so_tien": txn.amount})
    else:
        txn.match_status, txn.booking_id = "cho_ke_toan", b.id
        txn.match_note = f"Số tiền {txn.amount:,.0f} ≠ còn phải thu {due:,.0f} của {code} – Kế toán quyết định"


def accountant_assign(db: Session, u: User, txn: BankTransaction, booking: Booking, note: str = "") -> Receipt:
    """Kế toán gán giao dịch chờ vào booking (thu một phần / thu dư / sai nội dung)."""
    if txn.match_status == "da_khop":
        raise ValueError("Giao dịch đã khớp tự động")
    r = _make_receipt(db, booking, txn, txn.amount, u.username, "ke_toan_xac_nhan", note=note or "Kế toán gán tay")
    r.confirmed_by, r.confirmed_at = u.username, datetime.now()
    txn.match_status, txn.booking_id, txn.match_note = "da_khop", booking.id, f"Kế toán gán: {r.code}"
    R.audit(db, u.username, u.role, "ke_toan_gan_giao_dich", f"receipt:{r.code}", after={"booking": booking.code, "so_tien": txn.amount, "ghi_chu": note})
    db.commit(); db.refresh(r)
    return r


def accountant_confirm(db: Session, u: User, r: Receipt) -> Receipt:
    if r.status != "tu_dong":
        raise ValueError("Phiếu thu không ở trạng thái chờ xác nhận")
    r.status, r.confirmed_by, r.confirmed_at = "ke_toan_xac_nhan", u.username, datetime.now()
    R.audit(db, u.username, u.role, "ke_toan_xac_nhan_phieu_thu", f"receipt:{r.code}", after={"so_tien": r.amount})
    db.commit()
    return r


def cash_receipt(db: Session, u: User, booking: Booking, amount: float, payer: str, note: str) -> Receipt:
    """Thu tiền mặt do Kế toán lập (không qua robot)."""
    r = _make_receipt(db, booking, None, amount, u.username, "ke_toan_xac_nhan", payer=payer, note=note)
    r.confirmed_by, r.confirmed_at = u.username, datetime.now()
    R.audit(db, u.username, u.role, "lap_phieu_thu_tien_mat", f"receipt:{r.code}", after={"booking": booking.code, "so_tien": amount})
    db.commit(); db.refresh(r)
    return r


def ignore_transaction(db: Session, u: User, txn: BankTransaction, note: str) -> None:
    txn.match_status, txn.match_note = "bo_qua", note or "Kế toán bỏ qua"
    R.audit(db, u.username, u.role, "bo_qua_giao_dich", f"bank:{txn.sepay_id}", after={"ly_do": note})
    db.commit()
