"""Mô hình dữ liệu VTOS (SQLAlchemy 2.0)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

# ---------- Pháp nhân trong tập đoàn ----------
COMPANY_KINDS = {"me": "Công ty mẹ", "con": "Công ty con", "lien_ket": "Công ty liên kết", "chi_nhanh": "Chi nhánh / đơn vị trực thuộc"}


class Company(Base):
    """Danh mục pháp nhân (Ý kiến thẩm định 06/9/2026, mục C1 và Đợt 2).

    Đội xe thuộc Công ty TNHH Vận tải Vietrip – một pháp nhân riêng trong phạm vi hợp nhất – nên xe và
    hướng dẫn viên phải ghi rõ công ty chủ quản; giao dịch thuê xe giữa hai pháp nhân trong tập đoàn là
    giao dịch nội bộ, phải nhận diện để loại trừ khi lập báo cáo hợp nhất.
    """
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    tax_code: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(12), default="con")           # me / con / lien_ket / chi_nhanh
    ownership_pct: Mapped[float] = mapped_column(Float, default=0)         # tỷ lệ sở hữu của công ty mẹ
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)   # quan hệ sở hữu có thời gian hiệu lực
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")

    def in_group(self) -> bool:
        """Nằm trong phạm vi hợp nhất (mẹ, con, chi nhánh) – liên kết áp dụng phương pháp vốn chủ sở hữu."""
        return self.kind in ("me", "con", "chi_nhanh")


# ---------- Nhân sự & phân quyền ----------
ROLES = {
    "chutich": "Chủ tịch HĐQT",
    "tgd": "Tổng giám đốc",
    "ptgd_doan": "Phó TGĐ tour đoàn",
    "ptgd_mkt": "Phó TGĐ Marketing",
    "tp_dh": "Trưởng phòng Điều hành",
    "nv_dh": "Nhân viên điều hành",
    "nv_kd": "Nhân viên kinh doanh",
    "tn_kd": "Trưởng nhóm Kinh doanh",
    "tp_kd": "Trưởng phòng Kinh doanh",
    "gd_kd": "Giám đốc Kinh doanh",
    "nv_mkt": "Nhân viên Marketing",
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
    sales_group: Mapped[str] = mapped_column(String(20), default="")   # nhóm kinh doanh KD1–KD5 / VPCT / VPHN / VPBD / DOAN_OB / DOAN_ND
    staff_code: Mapped[str] = mapped_column(String(20), default="")    # mã nhân viên HCNS (bảng lương), vd 114
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
    "non_package": "Dịch vụ lẻ (Non-package)",
}
SERVICE_KINDS = {"VISA": "Visa", "FLIGHT": "Vé máy bay", "HOTEL": "Khách sạn", "VEHICLE": "Xe", "RESTAURANT": "Nhà hàng", "LAND": "Land", "GUIDE": "Hướng dẫn viên", "OTHER": "Khác"}
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


COST_ITEMS = [("ve_may_bay", "Vé máy bay"), ("land", "Land"), ("phi_lsq", "Phí LSQ"), ("bao_hiem", "Bảo hiểm"), ("qua_tang", "Quà tặng"), ("phi_tl", "Phí TL"),
              ("hop_doan", "Họp đoàn"), ("dieu_hanh", "Điều hành"), ("dich_thuat", "Dịch thuật"), ("hoa_hong_ve", "Hoa hồng vé"), ("phi_ck", "Phí CK"), ("khac", "Khác")]


class Product(Base):
    """Sản phẩm tour (tour cha) theo mẫu Vietrip: thông tin cơ bản + cơ cấu chi phí 11 khoản + dòng chi phí theo NCC (cố định / theo khách) + chương trình giá.
    Mở tour (chuyến) từ sản phẩm → dự toán 3 con số tự sinh."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    vietrip_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tour_type: Mapped[str] = mapped_column(String(20), default="le_noi_dia")     # le_noi_dia / le_nuoc_ngoai / doan_noi_dia / doan_nuoc_ngoai
    departure_point: Mapped[str] = mapped_column(String(80), default="TP HCM")
    region: Mapped[str] = mapped_column(String(80), default="")
    country: Mapped[str] = mapped_column(String(60), default="")
    sale_point: Mapped[str] = mapped_column(String(80), default="TP HCM")
    transport: Mapped[str] = mapped_column(String(40), default="Xe")
    vehicle_type: Mapped[str] = mapped_column(String(40), default="")
    length_text: Mapped[str] = mapped_column(String(20), default="")            # 3N2Đ
    days: Mapped[int] = mapped_column(Integer, default=1)
    reference_price: Mapped[float] = mapped_column(Float, default=0)
    deposit_pct: Mapped[float] = mapped_column(Float, default=30)
    days_to_close: Mapped[int] = mapped_column(Integer, default=3)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_structure: Mapped[dict] = mapped_column(JSON, default=dict)             # {ve_may_bay: 0, land: 0, …} – đồng/khách (cơ cấu tham khảo)
    cost_lines: Mapped[list] = mapped_column(JSON, default=list)                 # [{loai, ncc, mst, kind: co_dinh|theo_khach, mo_ta, don_gia, sl, so_tien}]
    program: Mapped[str] = mapped_column(Text, default="")                       # chương trình / thông tin giá (văn bản)
    services: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")            # active / inactive
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)   # NV điều hành phụ trách sản phẩm
    source: Mapped[str] = mapped_column(String(20), default="vtos")              # vtos / vietrip
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def fixed_cost(self) -> float:
        return sum(float(l.get("so_tien") or (float(l.get("don_gia") or 0) * float(l.get("sl") or 1))) for l in (self.cost_lines or []) if l.get("kind") == "co_dinh")

    def var_cost_per_pax(self) -> float:
        lines = sum(float(l.get("don_gia") or 0) * float(l.get("sl") or 1) for l in (self.cost_lines or []) if l.get("kind") == "theo_khach")
        struct = sum(float(v or 0) for v in (self.cost_structure or {}).values())
        return lines or struct


class TourEvent(Base):
    """Lịch sử quy trình tour (bước, hành động, người, lời giải trình) – hiển thị như 'Quy trình & Lịch sử' của Vietrip; nguồn vtos / vietrip."""
    __tablename__ = "tour_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    step: Mapped[str] = mapped_column(String(40))                                # khoi_tao / trinh_du_toan / tp_xac_nhan / duyet / ky / d7 / dong_so / kt_xac_nhan / cntt_khoa / vietrip
    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(20), default="vtos")
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


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
    settlement_version: Mapped[int] = mapped_column(Integer, default=1)    # V.01, V.02… mỗi lần Kế toán trả lại
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Bổ sung theo cấu trúc Vietrip (05/9/2026)
    vietrip_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    product_code: Mapped[str] = mapped_column(String(30), default="")      # mã sản phẩm (PT001, MICEVH…)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(40), default="")
    departure_point: Mapped[str] = mapped_column(String(80), default="")
    transport: Mapped[str] = mapped_column(String(40), default="")
    days: Mapped[int] = mapped_column(Integer, default=0)
    seats_open: Mapped[int] = mapped_column(Integer, default=0)            # số chỗ mở bán
    seats_promo: Mapped[int] = mapped_column(Integer, default=0)           # số chỗ khuyến mãi
    price_chd: Mapped[float] = mapped_column(Float, default=0)
    price_inf: Mapped[float] = mapped_column(Float, default=0)
    price_promo: Mapped[float] = mapped_column(Float, default=0)
    country: Mapped[str] = mapped_column(String(60), default="")
    settled_vietrip: Mapped[bool] = mapped_column(Boolean, default=False)  # Vietrip: quyết toán / duyệt chi
    imported: Mapped[bool] = mapped_column(Boolean, default=False)         # nhập từ Vietrip – không qua cổng duyệt VTOS

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
    # Bổ sung theo cấu trúc Vietrip
    vietrip_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    adl: Mapped[int] = mapped_column(Integer, default=0)
    chd: Mapped[int] = mapped_column(Integer, default=0)
    inf: Mapped[int] = mapped_column(Integer, default=0)
    pmt_status: Mapped[str] = mapped_column(String(10), default="")        # UNPAID / DEPO / PAID
    cancel_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    services_note: Mapped[str] = mapped_column(String(200), default="")    # dịch vụ lẻ
    deposit_pct: Mapped[float] = mapped_column(Float, default=30)           # % cọc theo sản phẩm
    locked: Mapped[bool] = mapped_column(Boolean, default=False)            # khóa cập nhật thông tin khách (đóng tour / thu đủ)
    lock_reason: Mapped[str] = mapped_column(String(120), default="")
    cancel_reason: Mapped[str] = mapped_column(String(200), default="")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_charge: Mapped[float] = mapped_column(Float, default=0)          # phí hủy giữ lại làm doanh thu
    service_type: Mapped[str] = mapped_column(String(20), default="")       # non-package: VISA/FLIGHT/HOTEL/VEHICLE/RESTAURANT/LAND/GUIDE/OTHER
    country: Mapped[str] = mapped_column(String(60), default="")
    customer_email: Mapped[str] = mapped_column(String(120), default="")
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost_amount: Mapped[float] = mapped_column(Float, default=0)            # giá vốn NCC của dịch vụ lẻ
    supplier_name: Mapped[str] = mapped_column(String(160), default="")
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


