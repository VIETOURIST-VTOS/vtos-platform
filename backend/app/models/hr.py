"""Nhân sự – lương (robot R6): hồ sơ nhân sự, hồ sơ visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

DEPARTMENTS = {"kd_le": "Kinh doanh Lẻ", "kd_doan": "Kinh doanh Đoàn", "dieu_hanh": "Điều hành", "visa": "Ban Visa", "marketing": "Marketing",
               "cntt": "CNTT", "ketoan": "Kế toán", "hcns": "HCNS", "huong_dan": "Hướng dẫn", "doi_xe": "Đội xe", "ban_tgd": "Ban TGĐ"}
POSITIONS = {"nv": "Nhân viên", "tl": "Team Leader", "tp": "Trưởng phòng", "gd_kd": "Giám đốc Kinh doanh", "ptgd_doan": "Phó TGĐ tour đoàn",
             "sale_admin": "Sale Admin", "visa": "Chuyên viên visa", "hdv": "Hướng dẫn viên", "tai_xe": "Tài xế", "khac": "Khác"}
OFFICES = {"hcm": "TP.HCM", "cantho": "Cần Thơ", "binhduong": "Bình Dương", "hanoi": "Hà Nội"}


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)                 # NS0001
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(20))
    position: Mapped[str] = mapped_column(String(20), default="nv")
    office: Mapped[str] = mapped_column(String(20), default="hcm")
    contract_type: Mapped[str] = mapped_column(String(10), default="hdld")   # hdld / ctv / doi_tac
    base_salary: Mapped[float] = mapped_column(Float, default=0)             # lương công việc (gắn chức vụ)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    probation: Mapped[bool] = mapped_column(Boolean, default=False)          # thử việc 85%
    transition_list: Mapped[bool] = mapped_column(Boolean, default=False)    # danh sách chuyển tiếp (chính sách cũ)
    # HDV
    card_no: Mapped[str] = mapped_column(String(30), default="")
    card_type: Mapped[str] = mapped_column(String(20), default="")            # noi_dia / quoc_te
    card_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    member_org: Mapped[bool] = mapped_column(Boolean, default=False)          # hội viên tổ chức XH-NN
    ctv_contract: Mapped[bool] = mapped_column(Boolean, default=False)        # hợp đồng cộng tác đã ký
    advance_limit: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaFile(Base):
    """Hồ sơ visa – quỹ visa tính theo tháng hoàn thành."""
    __tablename__ = "visa_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    market: Mapped[str] = mapped_column(String(40))                           # Schengen, Anh, Úc…
    method: Mapped[str] = mapped_column(String(20), default="tu_xu_ly")      # tu_xu_ly / gui_doi_tac
    handler_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    office: Mapped[str] = mapped_column(String(20), default="hcm")            # hcm / hanoi
    alliance: Mapped[bool] = mapped_column(Boolean, default=False)            # khách liên minh (+300.000)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    revenue: Mapped[float] = mapped_column(Float, default=0)                  # doanh thu visa
    status: Mapped[str] = mapped_column(String(20), default="dang_lam")       # dang_lam / hoan_thanh / tu_choi
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GuideAssignment(Base):
    """Lệnh phân công HDV theo chuyến (cổng 13) – thù lao = đơn giá tuyến × ngày (lễ Tết ×2)."""
    __tablename__ = "guide_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    guide_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    days: Mapped[int] = mapped_column(Integer, default=1)
    rate_per_day: Mapped[float] = mapped_column(Float, default=0)
    holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_by: Mapped[str] = mapped_column(String(50), default="")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # HDV xác nhận trong 24 giờ
    report_submitted: Mapped[bool] = mapped_column(Boolean, default=False)          # báo cáo tour 4 phần
    advance_settled: Mapped[bool] = mapped_column(Boolean, default=True)            # hoàn ứng xong
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")         # cho_xac_nhan / da_xac_nhan / huy


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True)
    seats: Mapped[int] = mapped_column(Integer, default=45)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    internal_rate_per_day: Mapped[float] = mapped_column(Float, default=0)   # bảng giá xe nội bộ (chờ duyệt)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DispatchOrder(Base):
    """Lệnh điều xe theo lịch khởi hành (xác nhận trong 4 giờ); số ngày → công tác phí tài xế; doanh thu nội bộ Đội xe."""
    __tablename__ = "dispatch_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    internal_price: Mapped[float] = mapped_column(Float, default=0)         # giá thuê nội bộ cả chuyến
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")  # cho_xac_nhan / da_xac_nhan / hoan_thanh / huy
    incident_note: Mapped[str] = mapped_column(String(300), default="")


class Incident(Base):
    """Sự vụ khách hàng (mức 1–4) – HCNS xác nhận; mức ≥ 2 chế tài vào thưởng/hoa hồng."""
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(String(300), default="")
    occurred_on: Mapped[date] = mapped_column(Date)
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")     # HCNS
    created_by: Mapped[str] = mapped_column(String(50), default="")


class PayrollRun(Base):
    """Bảng lương tháng: robot nháp → Kế toán xác nhận cơ sở → HCNS lập → TGĐ ký lô → bút toán 642/334, 632/338."""
    __tablename__ = "payroll_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="nhap")       # nhap / kt_xac_nhan / hcns_lap / tgd_ky
    rows: Mapped[list] = mapped_column(JSON, default=list)
    totals: Mapped[dict] = mapped_column(JSON, default=dict)
    kt_confirmed_by: Mapped[str] = mapped_column(String(50), default="")
    kt_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hcns_by: Mapped[str] = mapped_column(String(50), default="")
    hcns_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tgd_by: Mapped[str] = mapped_column(String(50), default="")
    tgd_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    entry_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
