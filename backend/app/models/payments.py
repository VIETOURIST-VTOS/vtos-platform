"""Thu tiền: giao dịch ngân hàng (SePay) và phiếu thu."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class BankTransaction(Base):
    """Một giao dịch tiền vào/ra do SePay đẩy về qua webhook. Không bao giờ sửa/xóa."""
    __tablename__ = "bank_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    sepay_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)   # id giao dịch phía SePay – chống trùng
    gateway: Mapped[str] = mapped_column(String(40), default="")                  # TPBank, MBBank…
    account_number: Mapped[str] = mapped_column(String(40), default="")
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    transfer_type: Mapped[str] = mapped_column(String(10))                       # in / out
    amount: Mapped[float] = mapped_column(Float)
    content: Mapped[str] = mapped_column(Text, default="")                       # nội dung chuyển khoản
    reference_code: Mapped[str] = mapped_column(String(80), default="")
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Kết quả khớp của robot R1
    match_status: Mapped[str] = mapped_column(String(20), default="chua_khop")    # da_khop / cho_ke_toan / chua_khop / bo_qua
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    match_note: Mapped[str] = mapped_column(String(200), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Receipt(Base):
    """Phiếu thu (mẫu 01-TT theo TT99/2025). Sinh từ giao dịch ngân hàng hoặc thu tiền mặt."""
    __tablename__ = "receipts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)                   # PT2609-0001
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    bank_txn_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transactions.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(20), default="chuyen_khoan")      # chuyen_khoan / tien_mat
    payer: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="tu_dong")           # tu_dong (robot) / ke_toan_xac_nhan / huy
    created_by: Mapped[str] = mapped_column(String(50), default="robot")
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
