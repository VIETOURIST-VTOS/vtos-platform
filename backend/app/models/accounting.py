"""Kế toán theo Thông tư 99/2025/TT-BTC: hệ thống tài khoản, chứng từ ghi sổ, hóa đơn điện tử, khóa kỳ."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Account(Base):
    """Danh mục tài khoản (Phụ lục hệ thống TK theo TT99)."""
    __tablename__ = "accounts"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)      # 111, 1121, 131…
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))                        # TS (tài sản) / NV (nguồn vốn) / DT / CP / XD
    parent: Mapped[str] = mapped_column(String(10), default="")


class JournalEntry(Base):
    """Chứng từ ghi sổ. Sinh tự động từ nghiệp vụ (robot R2) hoặc Kế toán lập tay. Đã ghi sổ thì không sửa – chỉ lập bút toán đảo."""
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)            # CT2609-0001
    entry_date: Mapped[date] = mapped_column(Date)
    period: Mapped[str] = mapped_column(String(7), index=True)            # 2026-09
    description: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(30), default="thu_cong")  # thu_tien / hoa_don / quyet_toan / thu_cong / dao
    source_ref: Mapped[str] = mapped_column(String(60), default="")       # receipt:PT…, invoice:…, tour:…
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="nhap")       # nhap / da_ghi_so / huy
    created_by: Mapped[str] = mapped_column(String(50), default="robot")
    posted_by: Mapped[str] = mapped_column(String(50), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id chứng từ đảo
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.id")


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_code: Mapped[str] = mapped_column(ForeignKey("accounts.code"), index=True)
    debit: Mapped[float] = mapped_column(Float, default=0)
    credit: Mapped[float] = mapped_column(Float, default=0)
    partner: Mapped[str] = mapped_column(String(160), default="")         # đối tượng: khách / NCC
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")


class Invoice(Base):
    """Hóa đơn điện tử GTGT (mẫu 01/GTGT). Phát hành qua nhà cung cấp HĐĐT – bản pilot dùng adapter nội bộ."""
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    series: Mapped[str] = mapped_column(String(20), default="1C26TVT")    # ký hiệu
    number: Mapped[int] = mapped_column(Integer, default=0)                # số hóa đơn (cấp khi phát hành)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(160))
    customer_tax_code: Mapped[str] = mapped_column(String(20), default="")
    customer_address: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(String(300), default="")
    pre_tax: Mapped[float] = mapped_column(Float, default=0)
    vat_rate: Mapped[float] = mapped_column(Float, default=0.1)
    vat: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="nhap")       # nhap / da_phat_hanh / huy
    provider: Mapped[str] = mapped_column(String(30), default="noi_bo")   # noi_bo / viettel / vnpt / misa…
    provider_ref: Mapped[str] = mapped_column(String(80), default="")     # mã tra cứu / mã CQT
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    issued_by: Mapped[str] = mapped_column(String(50), default="")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PeriodLock(Base):
    """Khóa kỳ kế toán: sau khi khóa không ghi sổ vào kỳ đó."""
    __tablename__ = "period_locks"
    period: Mapped[str] = mapped_column(String(7), primary_key=True)
    locked_by: Mapped[str] = mapped_column(String(50))
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    note: Mapped[str] = mapped_column(String(200), default="")
