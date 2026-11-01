"""Robot R1 – Thu tiền: nhận giao dịch SePay, khớp booking, sinh phiếu thu.

Quy tắc (mục 7.1 VTOS): robot chỉ tự động khi khớp TUYỆT ĐỐI mã booking + số tiền còn phải thu;
mọi trường hợp khác đưa vào hàng chờ Kế toán. Giao dịch ngân hàng là bản ghi bất biến.
"""
import re
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Booking, Tour, User
from app.models.payments import BankTransaction, Receipt
from app.services import rules as R
from app.services import accounting as ACC

BOOKING_RE = re.compile(r"BK\s?(\d{8})", re.IGNORECASE)


def paid_amount(db: Session, booking_id: int) -> float:
    return db.execute(select(func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id == booking_id, Receipt.status != "huy")).scalar() or 0.0


def paid_amount_map(db: Session, booking_ids: list[int] | None = None) -> dict[int, float]:
    """Số đã thu của NHIỀU booking trong một câu truy vấn: {booking_id: tiền}.

    Cùng một phép cộng với `paid_amount` ở trên – cùng điều kiện `status != "huy"`, cùng `sum(amount)` –
    chỉ khác là gom theo booking thay vì hỏi từng cái một. Chỗ nào duyệt một danh sách booking thì dùng
    hàm này; gọi `paid_amount` trong vòng lặp là mỗi booking một vòng đi–về tới cơ sở dữ liệu, và đó
    chính là thứ làm màn hình Thu tiền mất 106 giây trên bản chạy thật ngày 10/9/2026.

    Booking chưa có phiếu thu nào thì KHÔNG có khóa trong từ điển. Người gọi dùng `.get(id, 0.0)` –
    không phiếu thu thì đã thu bằng 0, chuyện này khác với cột tiền bỏ trống của đợt K2.
    """
    q = select(Receipt.booking_id, func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.status != "huy")
    if booking_ids is not None:
        if not booking_ids: return {}
        q = q.where(Receipt.booking_id.in_(booking_ids))
    return {bid: float(t or 0) for bid, t in db.execute(q.group_by(Receipt.booking_id)) if bid is not None}


def _next_receipt_code(db: Session) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, Receipt, f"PT{date.today():%y%m}-", 4)


def _make_receipt(db: Session, booking: Booking, txn: BankTransaction | None, amount: float, actor: str, status: str, payer: str = "", note: str = "") -> Receipt:
    r = Receipt(code=_next_receipt_code(db), booking_id=booking.id, bank_txn_id=txn.id if txn else None, amount=amount,
                method="chuyen_khoan" if txn else "tien_mat", payer=payer or booking.customer_name, note=note,
                status=status, created_by=actor, company_id=booking.company_id)
    db.add(r); db.flush()
    booking.paid = paid_amount(db, booking.id)
    from app.services.bookings import refresh_status
    refresh_status(booking)
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
        from app.services import ops as OPS
        pr = OPS.match_outgoing(db, txn.content, txn.amount)
        if pr:
            pr.status, pr.paid_at, pr.paid_ref, pr.paid_method = "da_chi", txn.transaction_date, f"SePay {sid}", "chuyen_khoan"
            OPS._post_payment(db, pr)
            txn.match_status, txn.match_note = "da_khop", f"Tiền ra khớp lệnh chi {pr.code}"
            R.audit(db, "robot", "robot", "khop_lenh_chi_tu_dong", f"dc:{pr.code}", after={"so_tien": txn.amount, "sepay": sid})
        else:
            txn.match_status, txn.match_note = "bo_qua", "Tiền ra – không khớp lệnh chi nào (Kế toán theo dõi)"
    db.commit()
    return txn, True


def match_transaction(db: Session, txn: BankTransaction) -> None:
    """R1: tìm mã BKxxxxxxxx trong nội dung; khớp tuyệt đối số tiền còn phải thu → phiếu thu tự động."""
    from app.services import don_ks_vtd as KV   # KS-14: nội dung có mã đặt phòng KS… → đơn khách sạn VTD nhận
    if KV.tu_khop(db, txn):
        return
    from app.services import tour_online as TRO  # TR-1: đơn tour online — khớp cả số cọc lẫn số còn lại, rồi gửi email
    if TRO.tu_khop(db, txn):
        return
    m = BOOKING_RE.search(txn.content.replace(" ", "") if txn.content else "")
    if not m:
        return _match_by_tour_code(db, txn)
    code = "BK" + m.group(1)
    b = db.execute(select(Booking).where(Booking.code == code)).scalars().first()
    if not b:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Mã {code} không tồn tại"
        return
    due = ((b.amount or 0) - (b.discount or 0)) - paid_amount(db, b.id)
    if abs((txn.amount or 0) - due) < 1 or (due > 0 and abs((txn.amount or 0) - ((b.amount or 0) - (b.discount or 0))) < 1 and paid_amount(db, b.id) == 0):
        r = _make_receipt(db, b, txn, (txn.amount or 0), "robot", "tu_dong", note="Khớp tuyệt đối mã + số tiền")
        txn.match_status, txn.booking_id, txn.match_note = "da_khop", b.id, f"Tự động: {r.code}"
        R.audit(db, "robot", "robot", "sinh_phieu_thu_tu_dong", f"receipt:{r.code}", after={"booking": b.code, "so_tien": txn.amount})
    else:
        txn.match_status, txn.booking_id = "cho_ke_toan", b.id
        txn.match_note = f"Số tiền {txn.amount:,.0f} ≠ còn phải thu {due:,.0f} của {code} – Kế toán quyết định"


TOUR_RE = re.compile(r"([A-Z]{2,8}\d{3})\.?(\d{8})")   # mã tour Vietrip: MÃSP+3 số . NNddmmyy (khách thường bỏ dấu chấm)


def _match_by_tour_code(db: Session, txn: BankTransaction) -> None:
    """Giai đoạn chạy song song: khách ghi mã tour Vietrip (vd NT00103110926) → tìm booking của tour còn phải thu đúng số tiền."""
    m = TOUR_RE.search((txn.content or "").upper().replace(" ", ""))
    if not m:
        txn.match_status, txn.match_note = "cho_ke_toan", "Không thấy mã booking trong nội dung chuyển khoản"
        return
    tcode = f"{m.group(1)}.{m.group(2)}"
    t = db.execute(select(Tour).where(Tour.code == tcode)).scalars().first()
    if not t:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Mã tour {tcode} không có trong VTOS"
        return
    cands = []
    for b in db.execute(select(Booking).where(Booking.tour_id == t.id, Booking.cancelled == False)).scalars():
        due = ((b.amount or 0) - (b.discount or 0)) - paid_amount(db, b.id)
        if due > 0 and abs((txn.amount or 0) - due) < 1: cands.append(b)
    if len(cands) == 1:
        b = cands[0]
        r = _make_receipt(db, b, txn, (txn.amount or 0), "robot", "tu_dong", note=f"Khớp mã tour {tcode} + đúng số tiền còn phải thu")
        txn.match_status, txn.booking_id, txn.match_note = "da_khop", b.id, f"Tự động theo mã tour: {r.code} ({b.code})"
        R.audit(db, "robot", "robot", "sinh_phieu_thu_tu_dong", f"receipt:{r.code}", after={"booking": b.code, "tour": tcode, "so_tien": txn.amount})
    elif cands:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Tour {tcode}: {len(cands)} booking cùng còn phải thu {txn.amount:,.0f} – Kế toán chọn"
    else:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Tour {tcode}: không booking nào còn phải thu đúng {txn.amount:,.0f}"


def accountant_assign(db: Session, u: User, txn: BankTransaction, booking: Booking, note: str = "") -> Receipt:
    """Kế toán gán giao dịch chờ vào booking (thu một phần / thu dư / sai nội dung)."""
    if txn.match_status == "da_khop":
        raise ValueError("Giao dịch đã khớp tự động")
    r = _make_receipt(db, booking, txn, txn.amount, u.username, "ke_toan_xac_nhan", note=note or "Kế toán gán tay")
    r.confirmed_by, r.confirmed_at = u.username, datetime.now()
    txn.match_status, txn.booking_id, txn.match_note = "da_khop", booking.id, f"Kế toán gán: {r.code}"
    R.audit(db, u.username, u.role, "ke_toan_gan_giao_dich", f"receipt:{r.code}", after={"booking": booking.code, "so_tien": txn.amount, "ghi_chu": note})
    ACC.on_receipt_confirmed(db, r, u.username, u.role)
    db.commit(); db.refresh(r)
    return r


def accountant_confirm(db: Session, u: User, r: Receipt) -> Receipt:
    if r.status != "tu_dong":
        raise ValueError("Phiếu thu không ở trạng thái chờ xác nhận")
    r.status, r.confirmed_by, r.confirmed_at = "ke_toan_xac_nhan", u.username, datetime.now()
    R.audit(db, u.username, u.role, "ke_toan_xac_nhan_phieu_thu", f"receipt:{r.code}", after={"so_tien": r.amount})
    ACC.on_receipt_confirmed(db, r, u.username, u.role)
    db.commit()
    return r


def cash_receipt(db: Session, u: User, booking: Booking, amount: float, payer: str, note: str) -> Receipt:
    """Thu tiền mặt do Kế toán lập (không qua robot)."""
    r = _make_receipt(db, booking, None, amount, u.username, "ke_toan_xac_nhan", payer=payer, note=note)
    r.confirmed_by, r.confirmed_at = u.username, datetime.now()
    R.audit(db, u.username, u.role, "lap_phieu_thu_tien_mat", f"receipt:{r.code}", after={"booking": booking.code, "so_tien": amount})
    ACC.on_receipt_confirmed(db, r, u.username, u.role)
    db.commit(); db.refresh(r)
    return r


def ignore_transaction(db: Session, u: User, txn: BankTransaction, note: str) -> None:
    txn.match_status, txn.match_note = "bo_qua", note or "Kế toán bỏ qua"
    R.audit(db, u.username, u.role, "bo_qua_giao_dich", f"bank:{txn.sepay_id}", after={"ly_do": note})
    db.commit()
