"""Phân hệ Visa – hồ sơ xin thị thực theo tour và visa dịch vụ lẻ (Đặc tả Visa v1.0).

Nguyên tắc kế thừa (mục 2 của đặc tả): KHÔNG dựng lại khách hàng, tour, booking, người dùng, chứng từ thu chi.
  - Khách/chuyến đi   : trỏ về bookings / tours có sẵn của VTOS (booking dịch vụ lẻ service_type="VISA").
  - Nhật ký nghiệp vụ : dùng chung bảng audit_log bất biến (app.services.rules.audit) – không có bảng riêng.
  - Thu – chi          : không có sổ riêng ở đây; tiền bạc đọc từ phân hệ Tài chính & Kế toán qua booking.

Điểm khác biệt bắt buộc so với Visa Portal cũ:
  - Đương đơn là MỘT CON NGƯỜI, không phải người liên hệ của booking. Một booking gia đình 4 người sinh 4 hồ sơ
    độc lập: form riêng, checklist riêng, lịch hẹn riêng, kết quả riêng (tiêu chí nghiệm thu 2, 10).
  - Trạng thái không sửa trực tiếp: mọi bước đi qua hành động nghiệp vụ có điều kiện (xem services/visa.py).
  - "Khách không nộp" KHÔNG tự thành đã miễn – phải có đề nghị và người có thẩm quyền duyệt (nghiệm thu 4).
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Pháp nhân chủ quản trỏ về danh mục companies mà VTOS đã có (Company – app/models/core.py), KHÔNG dựng
# danh mục riêng. Hồ sơ Visa có thể do công ty mẹ hoặc một công ty thành viên đứng ra làm, nên phải ghi rõ:
# dịch vụ giữa hai pháp nhân trong tập đoàn là giao dịch nội bộ, phải nhận diện được khi hợp nhất.
DEFAULT_COMPANY = "VTD"      # mã công ty mẹ trong danh mục pháp nhân

# ---------- Quy trình ----------
# Thứ tự bước theo mục 5.1. Mỗi bước chỉ đi tiếp bằng một hành động nghiệp vụ có điều kiện riêng.
STAGES = {
    "tiep_nhan": "Tiếp nhận",
    "phan_cong": "Phân công",
    "khai_thong_tin": "Khai thông tin",
    "khach_xac_nhan": "Khách xác nhận",
    "thu_thap_tai_lieu": "Thu thập tài liệu",
    "kiem_tra": "Kiểm tra trước khai/nộp",
    "khai_ho_so": "Khai hồ sơ chính thức",
    "lich_hen": "Lịch hẹn",
    "sinh_trac_hoc": "Sinh trắc học",
    "theo_doi_ket_qua": "Theo dõi kết quả",
    "ban_giao": "Bàn giao",
    "dong_ho_so": "Đóng hồ sơ",
}
STAGE_ORDER = list(STAGES)

LIFECYCLE = {"DRAFT": "Nháp", "ACTIVE": "Đang xử lý", "ON_HOLD": "Tạm dừng",
             "CANCELLED": "Đã hủy", "CLOSED": "Đã đóng"}
RESULTS = {"NOT_AVAILABLE": "Chưa có kết quả", "GRANTED": "Được cấp", "REFUSED": "Bị từ chối"}
SERVICE_MODES = {"TOUR_LINKED": "Visa theo tour", "STANDALONE": "Visa dịch vụ lẻ"}

# Trạng thái mục checklist (mục 6.2). Dấu ✓ trên giao diện CHỈ dùng cho ACCEPTED.
DOC_STATUS = {
    "MISSING": "Chưa nộp",
    "UPLOADED": "Đã nộp, chờ kiểm tra",
    "UNDER_REVIEW": "Đang kiểm tra",
    "ACCEPTED": "Đã chấp nhận",
    "NEEDS_REPLACEMENT": "Cần nộp lại",
    "WAIVER_REQUESTED": "Đang đề nghị miễn nộp",
    "WAIVED": "Đã được miễn nộp",
    "NOT_APPLICABLE": "Không áp dụng",
}
# Chỉ hai trạng thái này coi như mục bắt buộc đã xong.
DOC_SATISFIED = ("ACCEPTED", "WAIVED", "NOT_APPLICABLE")

TASK_STATUS = {"open": "Mở", "doing": "Đang làm", "waiting": "Chờ bên ngoài",
               "done": "Hoàn thành", "cancelled": "Đã hủy"}


class VisaMarket(Base):
    """Cấu hình thị trường (UK, SCHENGEN, KOREA…). Bổ sung thị trường mới là thêm dòng, không sửa mã nguồn."""
    __tablename__ = "visa_markets"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)     # UK, SCHENGEN…
    name: Mapped[str] = mapped_column(String(120))
    visa_types: Mapped[list] = mapped_column(JSON, default=list)               # [{"code":"UK_STANDARD_VISITOR","ten":...}]
    requires_biometrics: Mapped[bool] = mapped_column(Boolean, default=True)   # thị trường không lấy sinh trắc học thì bỏ bước
    requires_appointment: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_stages: Mapped[list] = mapped_column(JSON, default=list)              # bước bỏ qua ngoài hai cờ trên
    sla_hours: Mapped[dict] = mapped_column(JSON, default=dict)                # {"kiem_tra": 24, ...} hạn theo loại bước
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class VisaFamilyGroup(Base):
    """Nhóm gia đình. Booking chung chỉ là giá trị MẶC ĐỊNH khi tạo, không ghi đè liên kết riêng của thành viên."""
    __tablename__ = "visa_family_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    contact_phone: Mapped[str] = mapped_column(String(30), default="")
    contact_email: Mapped[str] = mapped_column(String(120), default="")
    main_case_id: Mapped[int | None] = mapped_column(Integer, nullable=True)   # hồ sơ đương đơn chính
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    # Người liên hệ KHÔNG mặc định xem được hồ sơ thành viên đã thành niên (mục 13).
    contact_sees_members: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaCase(Base):
    """Hồ sơ Visa của MỘT đương đơn."""
    __tablename__ = "visa_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Tiền tố HSV để không lẫn với mã "VS…" của bảng visa_files (quỹ visa – phân hệ Nhân sự).
    case_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)   # mã hiển thị, không đổi khi đổi chuyến
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    # Đương đơn – là con người, tách khỏi người liên hệ của booking
    applicant_name: Mapped[str] = mapped_column(String(120))
    applicant_dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicant_phone: Mapped[str] = mapped_column(String(30), default="")
    applicant_email: Mapped[str] = mapped_column(String(120), default="")
    # Số hộ chiếu KHÔNG bao giờ đi vào đường dẫn API (mục 12); chỉ lưu 4 ký tự cuối để đối chiếu nhanh,
    # bản đầy đủ nằm trong tài liệu hộ chiếu đã tải lên và chỉ người có quyền mới tải được.
    passport_last4: Mapped[str] = mapped_column(String(8), default="")
    passport_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Liên kết dữ liệu sẵn có của VTOS
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    family_group_id: Mapped[int | None] = mapped_column(ForeignKey("visa_family_groups.id"), nullable=True, index=True)
    family_role: Mapped[str] = mapped_column(String(40), default="")            # đương đơn chính / vợ / con…
    # Dịch vụ
    market_code: Mapped[str] = mapped_column(String(20), index=True)
    visa_type: Mapped[str] = mapped_column(String(60), default="")
    service_mode: Mapped[str] = mapped_column(String(20), default="TOUR_LINKED")
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Người phụ trách
    sales_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    visa_owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    supervisor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Quy trình
    current_stage: Mapped[str] = mapped_column(String(30), default="tiep_nhan", index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    result_status: Mapped[str] = mapped_column(String(20), default="NOT_AVAILABLE", index=True)
    hold_reason: Mapped[str] = mapped_column(String(200), default="")
    cancellation_reason: Mapped[str] = mapped_column(String(200), default="")
    # Nộp lại / thay thế – không xóa hồ sơ cũ
    previous_case_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(20), default="")      # RESUBMIT / REPLACEMENT
    # Truy vết nguồn khi chuyển từ Visa Portal
    source_system: Mapped[str] = mapped_column(String(30), default="")
    source_record_id: Mapped[str] = mapped_column(String(60), default="")
    # VTOS đã có bảng visa_files (phân hệ Nhân sự) dùng để tính quỹ visa / hoa hồng người xử lý. Đó là bản ghi
    # THÙ LAO, không phải bản ghi nghiệp vụ – nên không gộp làm một, mà nối lại để khỏi nhập số liệu hai lần.
    hr_visa_file_id: Mapped[int | None] = mapped_column(ForeignKey("visa_files.id"), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1)                # chống ghi đè âm thầm
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class VisaFormVersion(Base):
    """Phiên bản form khai. Bản đã được khách xác nhận là bất biến – sửa là sinh phiên bản mới."""
    __tablename__ = "visa_form_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default="DRAFT")   # DRAFT / SENT / CONFIRMED / USED
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    changed_fields: Mapped[list] = mapped_column(JSON, default=list)  # khác biệt so với phiên bản trước
    critical_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaConfirmation(Base):
    """Bằng chứng khách xác nhận ĐÚNG một phiên bản form."""
    __tablename__ = "visa_customer_confirmations"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    form_version_id: Mapped[int] = mapped_column(ForeignKey("visa_form_versions.id"))
    confirmed_by_name: Mapped[str] = mapped_column(String(120), default="")
    channel: Mapped[str] = mapped_column(String(30), default="link")   # link / zalo / email / giay
    evidence: Mapped[str] = mapped_column(String(300), default="")
    access_link_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaChecklistTemplate(Base):
    """Mẫu checklist theo thị trường và điều kiện áp dụng."""
    __tablename__ = "visa_checklist_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    market_code: Mapped[str] = mapped_column(String(20), index=True)
    visa_type: Mapped[str] = mapped_column(String(60), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    items: Mapped[list] = mapped_column(JSON, default=list)
    # [{"key","ten","mo_ta","bat_buoc":bool,"dieu_kien":{"tuoi_duoi":18} }]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaChecklistItem(Base):
    """Mục checklist cụ thể của một hồ sơ."""
    __tablename__ = "visa_checklist_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_version: Mapped[int] = mapped_column(Integer, default=1)
    key: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(25), default="MISSING", index=True)
    current_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(50), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    needs_recheck: Mapped[bool] = mapped_column(Boolean, default=False)   # mẫu đổi phiên bản → phải kiểm lại


class VisaDocument(Base):
    """Một phiên bản tệp tài liệu. Nộp lại KHÔNG ghi đè – sinh phiên bản mới, bản cũ vẫn truy được."""
    __tablename__ = "visa_document_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    checklist_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_name: Mapped[str] = mapped_column(String(255), default="")      # KHÔNG dùng làm định danh
    content_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="", index=True)  # sha256 nội dung
    storage_path: Mapped[str] = mapped_column(String(400), default="")
    uploaded_by: Mapped[str] = mapped_column(String(50), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    superseded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class VisaDocumentReview(Base):
    """Kết quả kiểm tra một phiên bản tài liệu. Khách xác nhận form KHÔNG thay cho việc này."""
    __tablename__ = "visa_document_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("visa_document_versions.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    decision: Mapped[str] = mapped_column(String(25))     # ACCEPTED / NEEDS_REPLACEMENT
    reason: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(50))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaWaiver(Base):
    """Đề nghị chấp nhận không nộp một mục bắt buộc, và quyết định của người có thẩm quyền."""
    __tablename__ = "visa_waiver_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    checklist_item_id: Mapped[int] = mapped_column(ForeignKey("visa_checklist_items.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(50))
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    decision: Mapped[str] = mapped_column(String(20), default="PENDING")   # PENDING / APPROVED / REJECTED
    decided_by: Mapped[str] = mapped_column(String(50), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str] = mapped_column(Text, default="")


class VisaTask(Base):
    """Công việc: đúng MỘT người nhận chính, có hạn, có lý do chờ."""
    __tablename__ = "visa_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))              # trùng khóa bước, hoặc xac_minh_lich_hen…
    title: Mapped[str] = mapped_column(String(200))
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    collaborators: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="thuong")   # thuong / cao / gap
    waiting_reason: Mapped[str] = mapped_column(String(200), default="")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evidence: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")


class VisaApplication(Base):
    """Lần khai/nộp hồ sơ chính thức lên hệ thống LSQ/ĐSQ – ghi nhận người thực hiện và bằng chứng.

    Giai đoạn đầu KHÔNG tự đăng nhập hay tự nộp hộ (mục 1); hệ thống chỉ lưu mã tham chiếu và chứng từ."""
    __tablename__ = "visa_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    reference_code: Mapped[str] = mapped_column(String(80), index=True)
    portal: Mapped[str] = mapped_column(String(60), default="")
    form_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_by: Mapped[str] = mapped_column(String(50))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    evidence: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class VisaAppointment(Base):
    """Lịch hẹn. Đổi lịch tạo bản ghi MỚI trỏ về bản cũ – không ghi đè mất lịch cũ (nghiệm thu 6)."""
    __tablename__ = "visa_appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)      # lưu theo giờ địa điểm hẹn
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Ho_Chi_Minh")
    location: Mapped[str] = mapped_column(String(200), default="")
    escort: Mapped[str] = mapped_column(String(120), default="")
    confirmation_ref: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", index=True)
    # SCHEDULED / ATTENDED / RESCHEDULED / MISSED / CANCELLED
    biometrics_done: Mapped[bool] = mapped_column(Boolean, default=False)
    biometrics_note: Mapped[str] = mapped_column(Text, default="")
    replaces_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reschedule_reason: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaResult(Base):
    """Kết quả của TỪNG đương đơn – không áp kết quả đương đơn chính cho cả nhà."""
    __tablename__ = "visa_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(20))            # GRANTED / REFUSED
    received_on: Mapped[date] = mapped_column(Date)
    visa_valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    visa_valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    entries: Mapped[str] = mapped_column(String(30), default="")
    refusal_reason: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(String(300), default="")
    recorded_by: Mapped[str] = mapped_column(String(50))
    verified_by: Mapped[str] = mapped_column(String(50), default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaHandover(Base):
    """Giao – nhận giấy tờ gốc và kết quả. Phân biệt đã xác nhận với mới dự kiến."""
    __tablename__ = "visa_handovers"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20))       # NHAN_TU_KHACH / TRA_KHACH / GUI_DOI_TAC / NHAN_DOI_TAC
    item_type: Mapped[str] = mapped_column(String(60))       # ho_chieu / ket_qua / ho_so_goc
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    from_party: Mapped[str] = mapped_column(String(120), default="")
    to_party: Mapped[str] = mapped_column(String(120), default="")
    method: Mapped[str] = mapped_column(String(60), default="")
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)   # False = mới dự kiến
    evidence: Mapped[str] = mapped_column(String(300), default="")
    recorded_by: Mapped[str] = mapped_column(String(50))
    note: Mapped[str] = mapped_column(Text, default="")


class VisaAccessLink(Base):
    """Liên kết cho khách khai/tải tài liệu. Chỉ lưu BĂM của mã, kiểm quyền mỗi lần truy cập."""
    __tablename__ = "visa_access_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)   # view / fill / upload / confirm
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VisaAiSuggestion(Base):
    """Đề xuất của AI. Ba trạng thái tách bạch và chỉ người có quyền chấp nhận mới cập nhật dữ liệu."""
    __tablename__ = "visa_ai_suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("visa_cases.id"), index=True)
    agent: Mapped[str] = mapped_column(String(40))            # ai_tiep_nhan / ai_kiem_tra_tai_lieu…
    target: Mapped[str] = mapped_column(String(60), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source_ref: Mapped[str] = mapped_column(String(200), default="")   # tài liệu nguồn + vị trí trích
    state: Mapped[str] = mapped_column(String(20), default="NEW", index=True)  # NEW / ACCEPTED / REJECTED
    decided_by: Mapped[str] = mapped_column(String(50), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
