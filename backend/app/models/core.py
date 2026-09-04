"""Mô hình dữ liệu VTOS (SQLAlchemy 2.0)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

# ---------- Nhân sự & phân quyền ----------
ROLES = {
    "chutich": "Chủ tịch HĐQT",
    "tgd": "Tổng giám đốc",
    "ptgd_doan": "Phó TGĐ tour đoàn",
    "ptgd_mkt": "Phó TGĐ Marketing",
    "tp_dh": "Trưởng phòng Điều hành",
    "nv_dh": "Nhân viên điều hành",
    "nv_kd": "Nhân viên kinh doanh",
    "gd_kd": "Giám đốc Kinh doanh",
    "ketoan": "Kế toán",
    "hcns": "Nhân sự Hành chính",
    "cntt": "Công nghệ thông tin",
    "bks": "Ban Kiểm soát (chỉ đọc)",
}


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(60), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------- Tham số chính sách (rules engine) ----------
class Param(Base):
    """Tham số có hiệu lực theo ngày. Bản ghi mới chỉ có hiệu lực khi đủ 2 chữ ký."""
    __tablename__ = "params"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(30), default="")
    effective_from: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(200), default="")   # văn bản, điều khoản
    status: Mapped[str] = mapped_column(String(20), default="active")  # pending / active / rejected
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------- Tour / chuyến ----------
TOUR_TYPES = {
    "le_noi_dia": "Tour lẻ nội địa",
    "le_nuoc_ngoai": "Tour lẻ nước ngoài",
    "doan_noi_dia": "Tour đoàn nội địa",
    "doan_nuoc_ngoai": "Tour đoàn nước ngoài",
}
TOUR_STATUS = {
    "nhap": "Nháp (Điều hành đang lập dự toán)",
    "cho_xac_nhan": "Chờ Trưởng phòng ĐH xác nhận",
    "cho_duyet": "Chờ duyệt",
    "da_duyet": "Đã duyệt – đang bán",
    "ket_thuc": "Đã kết thúc – chờ quyết toán",
    "da_dong_so": "Điều hành đã đóng số – chờ Kế toán",
    "kt_xac_nhan": "Kế toán đã xác nhận – chờ CNTT đối chiếu",
    "khoa": "Đã khóa",
    "huy": "Hủy / ghép / dời",
}


class Tour(Base):
    __tablename__ = "tours"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    tour_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))      # người điều hành duy nhất
    # Dự toán
    price_per_pax: Mapped[float] = mapped_column(Float, default=0)
    fixed_cost: Mapped[float] = mapped_column(Float, default=0)
    var_cost_per_pax: Mapped[float] = mapped_column(Float, default=0)
    planned_pax: Mapped[int] = mapped_column(Integer, default=0)
    rest_stops: Mapped[str] = mapped_column(Text, default="")             # điểm dừng nghỉ
    strategic: Mapped[bool] = mapped_column(Boolean, default=False)       # tour chiến lược (Chủ tịch công bố)
    # Cổng biên
    below_margin: Mapped[bool] = mapped_column(Boolean, default=False)    # cờ 'dưới biên'
    justification: Mapped[str] = mapped_column(Text, default="")          # giải trình 4 mục
    # Phê duyệt
    status: Mapped[str] = mapped_column(String(20), default="nhap")
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")     # TP ĐH
    approved_by: Mapped[str] = mapped_column(String(50), default="")      # TGĐ / PTGĐ
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    chairman_run_decision: Mapped[str] = mapped_column(String(200), default="")  # quyết định D-7
    # Quyết toán
    actual_revenue: Mapped[float] = mapped_column(Float, default=0)
    actual_cost: Mapped[float] = mapped_column(Float, default=0)
    promo_value: Mapped[float] = mapped_column(Float, default=0)          # giảm giá/mã KM → dòng giá vốn
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    kt_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cntt_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    operator: Mapped["User"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="tour")


# ---------- Yêu cầu đặt dịch vụ & booking ----------
class ServiceRequest(Base):
    """Kinh doanh gửi yêu cầu; Điều hành phải tạo booking trong 2 giờ làm việc."""
    __tablename__ = "service_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    sales_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(60))            # nguồn khách
    care_note: Mapped[str] = mapped_column(Text, default="")   # ghi chú chăm sóc
    pax: Mapped[int] = mapped_column(Integer, default=1)
    campaign_code: Mapped[str] = mapped_column(String(40), default="")
    promo_code: Mapped[str] = mapped_column(String(40), default="")
    discount: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour: Mapped["Tour"] = relationship()
    sales: Mapped["User"] = relationship()


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    request_id: Mapped[int] = mapped_column(Integer)
    sales_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(60))
    care_note: Mapped[str] = mapped_column(Text, default="")
    pax: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Float, default=0)
    discount: Mapped[float] = mapped_column(Float, default=0)
    promo_code: Mapped[str] = mapped_column(String(40), default="")
    campaign_code: Mapped[str] = mapped_column(String(40), default="")
    counts_for_target: Mapped[bool] = mapped_column(Boolean, default=True)  # cờ tính chỉ tiêu
    sla_minutes: Mapped[int] = mapped_column(Integer, default=0)            # phút từ yêu cầu → booking
    sla_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    paid: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    tour: Mapped["Tour"] = relationship(back_populates="bookings")
    sales: Mapped["User"] = relationship(foreign_keys=[sales_id])


# ---------- Cảnh báo (robot) ----------
class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))       # d7, qua_han_qt, sla_booking, duoi_bien
    level: Mapped[str] = mapped_column(String(10))      # info / warn / red
    ref: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    to_roles: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------- Nhật ký bất biến ----------
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actor: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(60))
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


