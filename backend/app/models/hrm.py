"""Hồ sơ nhân sự – hợp đồng – chấm công – người phụ thuộc (theo phân hệ Hồ sơ / Chấm công / Bảo hiểm của MISA AMIS Nhân sự).

Employee (models/hr.py) giữ phần dùng cho vận hành và tính lương (mã NV, phòng, nhóm KD, chức vụ, lương công việc).
Các bảng ở đây bổ sung phần HỒ SƠ và HỢP ĐỒNG mà MISA tách riêng: thông tin cá nhân đầy đủ, hợp đồng lao động
theo từng lần ký, người phụ thuộc giảm trừ gia cảnh, đơn từ và bảng chấm công.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

CONTRACT_KINDS = {
    "thu_viec": {"ten": "Hợp đồng thử việc", "bhxh": False},
    "xac_dinh_12": {"ten": "HĐLĐ xác định thời hạn 12 tháng", "bhxh": True},
    "xac_dinh_36": {"ten": "HĐLĐ xác định thời hạn 36 tháng", "bhxh": True},
    "khong_xac_dinh": {"ten": "HĐLĐ không xác định thời hạn", "bhxh": True},
    "ctv": {"ten": "Hợp đồng cộng tác viên", "bhxh": False},
    "khoan": {"ten": "Hợp đồng khoán việc", "bhxh": False},
}
CONTRACT_STATUS = {"hieu_luc": "Đang hiệu lực", "het_han": "Đã hết hạn", "cham_dut": "Đã chấm dứt", "nhap": "Nháp – chưa ký"}
RELATIONS = {"con": "Con", "cha": "Cha", "me": "Mẹ", "vo_chong": "Vợ/chồng", "khac": "Người phụ thuộc khác"}
LEAVE_KINDS = {
    "phep_nam": {"ten": "Nghỉ phép năm", "tru_phep": True, "huong_luong": True},
    "khong_luong": {"ten": "Nghỉ không lương", "tru_phep": False, "huong_luong": False},
    "om_dau": {"ten": "Nghỉ ốm (BHXH chi trả)", "tru_phep": False, "huong_luong": False},
    "thai_san": {"ten": "Nghỉ thai sản", "tru_phep": False, "huong_luong": False},
    "cong_tac": {"ten": "Đi công tác", "tru_phep": False, "huong_luong": True},
    "tang_ca": {"ten": "Đăng ký làm thêm giờ", "tru_phep": False, "huong_luong": True},
}
LEAVE_STATUS = {"cho_duyet": "Chờ duyệt", "duyet": "Đã duyệt", "tu_choi": "Từ chối", "huy": "Đã hủy"}
ATT_KINDS = {"lam_viec": "Đi làm", "phep_nam": "Nghỉ phép năm", "khong_luong": "Nghỉ không lương",
             "om_dau": "Nghỉ ốm", "thai_san": "Nghỉ thai sản", "cong_tac": "Đi công tác", "le": "Nghỉ lễ", "vang": "Nghỉ không phép"}


class EmployeeProfile(Base):
    """Hồ sơ chi tiết của nhân viên (1–1 với Employee). Tách riêng vì chứa thông tin định danh, ít thay đổi."""
    __tablename__ = "employee_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True, index=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(10), default="")               # nam / nu / khac
    id_number: Mapped[str] = mapped_column(String(20), default="")            # số CCCD
    id_issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_issued_by: Mapped[str] = mapped_column(String(120), default="")
    permanent_address: Mapped[str] = mapped_column(String(300), default="")   # hộ khẩu thường trú
    current_address: Mapped[str] = mapped_column(String(300), default="")     # chỗ ở hiện tại
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    tax_code: Mapped[str] = mapped_column(String(20), default="")             # MST cá nhân
    social_insurance_no: Mapped[str] = mapped_column(String(20), default="")  # số sổ BHXH
    bank_account: Mapped[str] = mapped_column(String(40), default="")
    bank_name: Mapped[str] = mapped_column(String(120), default="")
    marital_status: Mapped[str] = mapped_column(String(20), default="")
    education: Mapped[str] = mapped_column(String(120), default="")
    emergency_contact: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class LaborContract(Base):
    """Hợp đồng lao động – mỗi lần ký là một bản ghi, giữ đủ lịch sử như MISA."""
    __tablename__ = "labor_contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)     # số hợp đồng
    kind: Mapped[str] = mapped_column(String(20), default="xac_dinh_12")
    signed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)     # None = không xác định thời hạn
    salary: Mapped[float] = mapped_column(Float, default=0)                    # lương chính theo hợp đồng
    si_salary: Mapped[float] = mapped_column(Float, default=0)                 # mức lương đóng BHXH
    allowance: Mapped[float] = mapped_column(Float, default=0)                 # phụ cấp
    annual_leave_days: Mapped[float] = mapped_column(Float, default=12)        # số ngày phép năm theo hợp đồng
    status: Mapped[str] = mapped_column(String(20), default="hieu_luc")
    terminated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    terminate_reason: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Dependent(Base):
    """Người phụ thuộc giảm trừ gia cảnh thuế TNCN (MISA: Thuế TNCN ▸ Người phụ thuộc)."""
    __tablename__ = "dependents"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    relation: Mapped[str] = mapped_column(String(20), default="con")
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_code: Mapped[str] = mapped_column(String(20), default="")              # MST người phụ thuộc
    id_number: Mapped[str] = mapped_column(String(20), default="")
    from_period: Mapped[str] = mapped_column(String(7), default="")            # kỳ bắt đầu giảm trừ YYYY-MM
    to_period: Mapped[str] = mapped_column(String(7), default="")              # kỳ kết thúc (rỗng = còn hiệu lực)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LeaveRequest(Base):
    """Đơn từ: nghỉ phép, nghỉ không lương, ốm, thai sản, công tác, làm thêm giờ (MISA: Chấm công ▸ Đơn từ)."""
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="phep_nam")
    date_from: Mapped[date] = mapped_column(Date, index=True)
    date_to: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float, default=1)                      # số ngày (0.5 = nửa ngày)
    ot_hours: Mapped[float] = mapped_column(Float, default=0)                  # số giờ làm thêm (đơn tăng ca)
    reason: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="cho_duyet")
    approved_by: Mapped[str] = mapped_column(String(50), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AttendanceDay(Base):
    """Bảng chấm công theo ngày (MISA: Chấm công ▸ Bảng chấm công). Một dòng cho mỗi nhân viên mỗi ngày."""
    __tablename__ = "attendance_days"
    __table_args__ = (UniqueConstraint("employee_id", "day", name="uq_attendance_emp_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="lam_viec")
    work: Mapped[float] = mapped_column(Float, default=1)                      # số công (1 / 0.5 / 0)
    ot_hours: Mapped[float] = mapped_column(Float, default=0)
    leave_id: Mapped[int | None] = mapped_column(ForeignKey("leave_requests.id"), nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
