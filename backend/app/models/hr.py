"""Nhân sự – lương (robot R6): hồ sơ nhân sự, hồ sơ visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

DEPARTMENTS = {"kd_le": "Kinh doanh Lẻ", "kd_doan": "Kinh doanh Đoàn", "dieu_hanh": "Điều hành", "visa": "Ban Visa", "marketing": "Marketing",
               "cntt": "CNTT", "ketoan": "Kế toán", "hcns": "HCNS", "huong_dan": "Hướng dẫn", "doi_xe": "Đội xe", "ban_tgd": "Ban TGĐ"}
POSITIONS = {"nv": "Nhân viên", "tl": "Team Leader", "tp": "Trưởng phòng", "gd_kd": "Giám đốc Kinh doanh", "ptgd_doan": "Phó TGĐ tour đoàn",
             "sale_admin": "Sale Admin", "visa": "Chuyên viên visa", "hdv": "Hướng dẫn viên", "tai_xe": "Tài xế", "khac": "Khác"}
OFFICES = {"hcm": "TP.HCM", "cantho": "Cần Thơ", "binhduong": "Bình Dương", "hanoi": "Hà Nội", "haiphong": "Hải Phòng"}
SALES_GROUPS = {"KD1": "Nhóm KD 1", "KD2": "Nhóm KD 2", "KD3": "Nhóm KD 3", "KD4": "Nhóm KD 4", "KD5": "Nhóm KD 5", "VPCT": "VP Cần Thơ", "VPHN": "VP Hà Nội", "VPHP": "VP Hải Phòng", "VPBD": "VP Bình Dương", "DOAN_OB": "Đoàn Outbound", "DOAN_ND": "Đoàn Nội địa"}


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)                 # NS0001
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(20))
    position: Mapped[str] = mapped_column(String(20), default="nv")
    title: Mapped[str] = mapped_column(String(60), default="")             # chức vụ ghi trên bảng lương (NVKD 2, TL Team KD 1, ĐH…)
    duties: Mapped[str] = mapped_column(Text, default="")                 # công việc chính: tuyến/thị trường người này phụ trách
    sales_group: Mapped[str] = mapped_column(String(20), default="")      # KD1–KD5, VPCT, VPHN, VPBD, VPHP, DOAN_OB, DOAN_ND
    office: Mapped[str] = mapped_column(String(20), default="hcm")
    contract_type: Mapped[str] = mapped_column(String(10), default="hdld")   # hdld / ctv / doi_tac
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)   # pháp nhân chủ quản (HDV cộng tác viên ghi theo công ty ký hợp đồng)
    base_salary: Mapped[float] = mapped_column(Float, default=0)             # lương công việc (gắn chức vụ)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
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
    rate_id: Mapped[int | None] = mapped_column(ForeignKey("guide_rates.id"), nullable=True)   # tuyến trong bảng giá HDV
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
    kind: Mapped[str] = mapped_column(String(10), default="noi_bo")            # noi_bo (Vietrip) / hop_tac (xe hợp tác hỗ trợ)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)   # pháp nhân sở hữu xe
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    internal_rate_per_day: Mapped[float] = mapped_column(Float, default=0)   # dùng khi tuyến không có trong bảng giá
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # --- Đợt 1 đội xe (đặc tả 06/9/2026). Xem app/models/fleet.py để hiểu vì sao tách làm ba trục. ---
    code: Mapped[str] = mapped_column(String(20), default="")                # mã xe cố định suốt vòng đời
    vin: Mapped[str] = mapped_column(String(40), default="")                 # số khung – dùng để nhận ra xe cũ khi đổi biển
    lifecycle: Mapped[str] = mapped_column(String(20), default="dang_khai_thac")   # vòng đời TÀI SẢN
    op_right: Mapped[str] = mapped_column(String(20), default="so_huu")      # quyền KHAI THÁC (khác vòng đời)
    operator_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    partner_name: Mapped[str] = mapped_column(String(120), default="")       # đối tác khai thác/chủ xe ngoài
    contract_ref: Mapped[str] = mapped_column(String(60), default="")        # số hợp đồng hợp tác
    contract_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    odo_km: Mapped[int] = mapped_column(Integer, default=0)                   # số km đồng hồ đã xác nhận
    odo_at: Mapped[date | None] = mapped_column(Date, nullable=True)          # thời điểm của số km đó
    source_note: Mapped[str] = mapped_column(String(200), default="")


class VehicleRate(Base):
    """Bảng giá xe nội bộ theo tuyến (giá trọn chuyến): cột xe Vietrip – VTD và cột xe hợp tác. Master data, Chủ tịch + TGĐ duyệt, hiệu lực theo ngày."""
    __tablename__ = "vehicle_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    route: Mapped[str] = mapped_column(String(80))
    days: Mapped[int] = mapped_column(Integer, default=0)
    internal_price: Mapped[float] = mapped_column(Float, default=0)          # xe nội bộ Vietrip – VTD
    partner_price: Mapped[float] = mapped_column(Float, default=0)           # xe hợp tác hỗ trợ (0 = không áp dụng)
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")       # pending / active / rejected
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GuideRate(Base):
    """Bảng giá thù lao HDV theo tuyến (đồng/ngày) – master data, Chủ tịch + TGĐ ký, hiệu lực theo ngày; lễ Tết ×2."""
    __tablename__ = "guide_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    route: Mapped[str] = mapped_column(String(80))
    days: Mapped[float] = mapped_column(Float, default=0)
    rate_per_day: Mapped[float] = mapped_column(Float, default=0)
    old_rate_per_day: Mapped[float] = mapped_column(Float, default=0)
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")       # pending / active / rejected
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DispatchOrder(Base):
    """Lệnh điều xe theo lịch khởi hành (xác nhận trong 4 giờ); số ngày → công tác phí tài xế; doanh thu nội bộ Đội xe."""
    __tablename__ = "dispatch_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    rate_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_rates.id"), nullable=True)   # tuyến trong bảng giá
    internal_price: Mapped[float] = mapped_column(Float, default=0)         # giá thuê nội bộ cả chuyến
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")  # cho_xac_nhan / da_xac_nhan / hoan_thanh / huy
    incident_note: Mapped[str] = mapped_column(String(300), default="")


INCIDENT_LEVELS = {
    1: {"ten": "Mức 1 – Sai sót nội bộ", "mo_ta": "Khách chưa bị ảnh hưởng hoặc đã xử lý xong trong ngày: nhập thiếu thông tin booking rồi tự sửa, sai sót giấy tờ sửa được trước khởi hành không phát sinh chi phí, thiếu báo cáo một ngày, trả lời khách trễ trong ca trực",
        "che_tai": "Nhắc nhở, ghi hồ sơ đánh giá 3 tháng; không trừ tiền", "duyet": []},
    2: {"ten": "Mức 2 – Khách bị ảnh hưởng / phát sinh chi phí", "mo_ta": "Chuyến vẫn chạy: tư vấn sai khiến khách khiếu nại bằng văn bản, báo giá sai phải bù chi phí, sai tên/ngày trên vé và voucher phải đổi có phí, quên đặt hoặc đặt trùng dịch vụ, bỏ sót khách trong danh sách đoàn, không đôn đốc khiến khách nợ quá hạn",
        "che_tai": "Trừ 1.000.000 đ vào hoa hồng mỗi vụ (có biên bản); quản lý liên đới −0,5 điểm % phần thưởng theo lợi nhuận", "duyet": ["gd_kd", "ptgd_doan", "tgd"]},
    3: {"ten": "Mức 3 – Khách mất chuyến / mất tiền lớn / gian dối", "mo_ta": "Khách không đi được do lỗi nhân viên (quên đặt vé, không kiểm hộ chiếu–visa), Công ty phải hoàn tiền/bồi thường, khiếu nại tới cơ quan quản lý hoặc đăng công khai, thu tiền ngoài hệ thống, khai khống chi phí hoặc sửa số quyết toán, chuyển khách/data cho đơn vị ngoài",
        "che_tai": "Không phát sinh hoa hồng của chính booking/đoàn đó; kỷ luật lao động theo nội quy; bồi thường theo Điều 129 BLLĐ; dấu hiệu gian dối chuyển Pháp chế", "duyet": ["chutich", "tgd"]},
}
INCIDENT_STATUS = {"lap": "Đã lập biên bản", "hcns_xac_nhan": "HCNS đã xác nhận – chờ duyệt", "cho_khieu_nai": "Đã duyệt – trong 3 ngày khiếu nại", "khieu_nai": "Đang khiếu nại – treo chế tài",
                   "hieu_luc": "Có hiệu lực", "huy": "Hủy / khiếu nại được chấp nhận"}


class Incident(Base):
    """Sự vụ (mức 1–3, bảng phân mức 05/9/2026): trưởng bộ phận lập biên bản → HCNS xác nhận (≥ mức 2) → cấp có thẩm quyền duyệt
    (mức 2: GĐ KD / PTGĐ; mức 3: Chủ tịch + TGĐ) → người bị lập được ghi ý kiến, khiếu nại lên cấp trên 1 bậc trong 3 ngày làm việc (treo chế tài) → hiệu lực."""
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(String(300), default="")
    occurred_on: Mapped[date] = mapped_column(Date)
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")     # HCNS
    created_by: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="lap")
    approved_by: Mapped[str] = mapped_column(String(120), default="")     # người duyệt (mức 3: 2 chữ ký, cách nhau dấu phẩy)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    employee_opinion: Mapped[str] = mapped_column(String(300), default="")   # ý kiến người bị lập biên bản
    appeal_note: Mapped[str] = mapped_column(String(300), default="")        # nội dung khiếu nại
    appeal_result: Mapped[str] = mapped_column(String(300), default="")      # kết luận cấp trên
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
