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
    # Cấu trúc MISA + ánh xạ Báo cáo tình hình tài chính / KQKD theo TT99 (mẫu nộp UBCK)
    level: Mapped[int] = mapped_column(Integer, default=1)                # bậc 1–5 (số chữ số − 2)
    is_detail: Mapped[bool] = mapped_column(Boolean, default=True)        # TK chi tiết (không có TK con) – chỉ TK chi tiết được ghi sổ
    bs_debit: Mapped[str] = mapped_column(String(6), default="")          # mã chỉ tiêu THTC khi dư Nợ (vd 131, 132, 135…)
    bs_credit: Mapped[str] = mapped_column(String(6), default="")         # mã chỉ tiêu THTC khi dư Có (vd 311, 312, 320…)
    pl_code: Mapped[str] = mapped_column(String(6), default="")           # mã chỉ tiêu KQKD (01, 11, 22, 23, 25, 26, 31, 32, 51)
    misa: Mapped[bool] = mapped_column(Boolean, default=False)            # có trên sổ MISA của Vietourist


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
    partner: Mapped[str] = mapped_column(String(160), default="")         # tên đối tượng: khách / NCC
    partner_code: Mapped[str] = mapped_column(String(40), default="", index=True)   # mã đối tượng MISA (MST/CCCD/mã NV/mã ngân hàng)
    project_code: Mapped[str] = mapped_column(String(40), default="", index=True)   # mã công trình MISA = mã tour
    item_code: Mapped[str] = mapped_column(String(40), default="")        # mã khoản mục chi phí / mã hàng hóa dịch vụ
    doc_no: Mapped[str] = mapped_column(String(40), default="")           # số hóa đơn / số chứng từ gốc
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


class Partner(Base):
    """Đối tượng kế toán (danh mục khách hàng / nhà cung cấp / nhân viên / ngân hàng) – cùng mã với MISA (MST, CCCD…)."""
    __tablename__ = "partners"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(10), default="kh")          # kh / ncc / nv / nh / khac
    is_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_supplier: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_code: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    trade_name: Mapped[str] = mapped_column(String(200), default="")     # tên thương mại (DataNCC: "RESORT VĨNH HY")
    internal: Mapped[bool] = mapped_column(Boolean, default=False)       # đối tượng nội bộ / bên liên quan
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(20), default="misa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Project(Base):
    """Công trình MISA = tour/đoàn (chiều tập hợp chi phí – doanh thu). Mã chuẩn SP.NHÓM.DDMMYY; mã cũ giữ để đọc lịch sử."""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="dang_thuc_hien")
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    technical: Mapped[bool] = mapped_column(Boolean, default=False)      # mã kỹ thuật (0000, CHUA RO, CPXD…) – không phải tour
    source: Mapped[str] = mapped_column(String(20), default="misa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
