"""Nhân sự – lương (robot R6): hồ sơ nhân sự, hồ sơ visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.kieu_tien import TIEN

DEPARTMENTS = {"kd_le": "Kinh doanh Lẻ", "kd_doan": "Kinh doanh Đoàn", "dieu_hanh": "Điều hành", "visa": "Ban Visa", "marketing": "Marketing",
               "cntt": "CNTT", "ketoan": "Kế toán", "hcns": "HCNS", "huong_dan": "Hướng dẫn", "doi_xe": "Đội xe", "ban_tgd": "Ban TGĐ"}
POSITIONS = {"nv": "Nhân viên", "tl": "Team Leader", "tp": "Trưởng phòng", "gd_kd": "Giám đốc Kinh doanh", "ptgd_doan": "Phó TGĐ tour đoàn",
             "sale_admin": "Sale Admin", "visa": "Chuyên viên visa", "hdv": "Hướng dẫn viên", "tai_xe": "Tài xế", "khac": "Khác"}
OFFICES = {"hcm": "TP.HCM", "cantho": "Cần Thơ", "binhduong": "Bình Dương", "hanoi": "Hà Nội", "haiphong": "Hải Phòng"}
SALES_GROUPS = {"KD1": "Nhóm KD 1", "KD2": "Nhóm KD 2", "KD3": "Nhóm KD 3", "KD4": "Nhóm KD 4", "KD5": "Nhóm KD 5", "VPCT": "VP Cần Thơ", "VPHN": "VP Hà Nội", "VPHP": "VP Hải Phòng", "VPBD": "VP Bình Dương", "DOAN_OB": "Đoàn Outbound", "DOAN_ND": "Đoàn Nội địa"}


class Employee(Base):
    __tablename__ = "employees"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)                 # NS0001
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(20))
    position: Mapped[str] = mapped_column(String(20), default="nv")
    title: Mapped[str] = mapped_column(String(60), default="")             # chức vụ ghi trên bảng lương (NVKD 2, TL Team KD 1, ĐH…)
    duties: Mapped[str] = mapped_column(Text, default="")                 # công việc chính: tuyến/thị trường người này phụ trách
    bhxh_base: Mapped[float | None] = mapped_column(TIEN)            # tiền lương làm căn cứ đóng BHXH bắt buộc (khác lương hợp đồng, nullable=True)
    sales_group: Mapped[str] = mapped_column(String(20), default="")      # KD1–KD5, VPCT, VPHN, VPBD, VPHP, DOAN_OB, DOAN_ND
    office: Mapped[str] = mapped_column(String(20), default="hcm")
    contract_type: Mapped[str] = mapped_column(String(10), default="hdld")   # hdld / ctv / doi_tac
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)   # pháp nhân chủ quản (HDV cộng tác viên ghi theo công ty ký hợp đồng)
    base_salary: Mapped[float | None] = mapped_column(TIEN)             # lương công việc (gắn chức vụ, nullable=True)
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
    advance_limit: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # VB-1 · 09/10/2026 — NGÀY NGHỈ VIỆC, nền của mục 5.8 Báo cáo biến động nhân sự.
    #
    # `active` trả lời "còn làm hay không"; ba cột này trả lời "nghỉ từ hôm nào và vì sao". Một báo
    # cáo biến động chỉ có đúng một phép tính — đầu kỳ + tăng − giảm = cuối kỳ — và không có ngày
    # nghỉ thì vế "giảm trong kỳ" không tính được, cả báo cáo rút xuống còn con số đầu người hôm nay.
    #
    # KHÔNG dùng `labor_contracts.terminated_on` thay: đó là ngày chấm dứt một HỢP ĐỒNG, không phải
    # ngày rời công ty (hết hạn rồi ký tiếp là chấm dứt một bản mà người vẫn ở lại), và phần lớn
    # người phải đếm — HDV cộng tác, tài xế khoán — không có bản hợp đồng lao động nào.
    #
    # ĐỂ RỖNG VỚI NGƯỜI ĐÃ `active = False`, không đoán ngược: một ngày đoán nằm trong báo cáo trông
    # y hệt một ngày thật, và nó đi thẳng vào tỷ lệ nghỉ việc HCNS báo cáo lên.
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_kind: Mapped[str] = mapped_column(String(20), default="")      # xem bien_dong_ns.LY_DO_GIAM
    end_reason: Mapped[str] = mapped_column(String(300), default="")
    # Đội xe Đợt 2: bốn số cuối thẻ dầu gắn với TÀI XẾ, không gắn với xe – đổi tài xế thì đổi luôn
    # ánh xạ, nếu gắn vào xe thì mọi giao dịch thẻ sau ngày bàn giao sẽ gán nhầm chi phí sang người khác.
    fuel_card_last4: Mapped[str] = mapped_column(String(8), default="")
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
    revenue: Mapped[float | None] = mapped_column(TIEN)                  # doanh thu visa, nullable=True
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
    rate_per_day: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    rate_id: Mapped[int | None] = mapped_column(ForeignKey("guide_rates.id"), nullable=True)   # tuyến trong bảng giá HDV
    holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_by: Mapped[str] = mapped_column(String(50), default="")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # HDV xác nhận trong 24 giờ
    report_submitted: Mapped[bool] = mapped_column(Boolean, default=False)          # báo cáo tour 4 phần
    advance_settled: Mapped[bool] = mapped_column(Boolean, default=True)            # hoàn ứng xong
    # cho_xac_nhan / da_xac_nhan / tu_choi / het_han / huy.
    # "tu_choi" và "het_han" thêm ngày 07/9/2026 khi toàn bộ HDV thành cộng tác viên: từ chối một lời chào
    # là quyền của người cung cấp dịch vụ, và phải ghi lại ĐƯỢC mà không kèm chế tài – nếu hệ thống chỉ có
    # "chưa xác nhận" thì mọi lần từ chối trông như một lần chậm trễ, và đó là hồ sơ bất lợi cho chính công ty.
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")
    ly_do: Mapped[str] = mapped_column(String(200), default="")                     # lý do từ chối, nếu có
    han_tra_loi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # lời chào hết hiệu lực lúc nào
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # nhận hoặc từ chối lúc nào

    # ─────────── Phòng HDV Đợt 1 · 06/10/2026 ───────────
    # V10 – phân công là bản ghi mà Điều hành, phòng HDV và Kế toán cùng chạm: một bên đổi người, một
    # bên sửa giờ, một bên đánh dấu đã hoàn ứng. Trước Đợt 1 bảng này không có cột phiên bản, nên ba
    # bên vẫn đè lên nhau lặng lẽ.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    yeu_cau_id: Mapped[int | None] = mapped_column(ForeignKey("yeu_cau_hdv.id"), nullable=True, index=True)
    # KHOẢNG CẦN NGƯỜI, tính cả chuẩn bị và di chuyển. Chủ tịch chốt 06/10: không xếp một hướng dẫn
    # viên vào hai chuyến chồng giờ. Muốn so hai khoảng thì phải có hai đầu mốc — `days` là một con
    # số, không có đầu mốc nào, nên tám tuần qua hệ thống chặn được một chiếc xe bị đặt hai lần
    # (lệnh điều xe có date_from/date_to) mà không chặn được một con người.
    #
    # RỖNG VẪN LÀ RỖNG: hàng trăm phân công cũ không có giờ. Suy giờ từ ngày khởi hành của tour thì
    # mỗi bản ghi đều có một khoảng trông như thật, xếp gọn trên màn hình, và không ai còn nhớ đó là
    # số đoán. Phân công thiếu giờ KHÔNG tham gia phép chặn trùng và hiện ở danh sách việc còn thiếu.
    bat_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Một tour vẫn có thể có nhiều hướng dẫn viên; phân biệt bằng VAI TRÒ chứ không bằng chặng —
    # Chủ tịch chốt 06/10: mỗi hướng dẫn viên đi xuyên suốt hết tour, không chia chặng theo người.
    vai_tro: Mapped[str] = mapped_column(String(10), default="chinh")
    gio_boi: Mapped[str] = mapped_column(String(50), default="")
    gio_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Vehicle(Base):
    __tablename__ = "vehicles"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True)
    seats: Mapped[int] = mapped_column(Integer, default=45)
    kind: Mapped[str] = mapped_column(String(10), default="noi_bo")            # noi_bo (Vietrip) / hop_tac (xe hợp tác hỗ trợ)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)   # pháp nhân sở hữu xe
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    internal_rate_per_day: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # dùng khi tuyến không có trong bảng giá
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # --- Đợt 1 đội xe (đặc tả 06/9/2026). Xem app/models/fleet.py để hiểu vì sao tách làm ba trục. ---
    code: Mapped[str] = mapped_column(String(20), default="")                # mã xe cố định suốt vòng đời
    vin: Mapped[str] = mapped_column(String(40), default="")                 # số khung – dùng để nhận ra xe cũ khi đổi biển
    lifecycle: Mapped[str] = mapped_column(String(20), default="dang_khai_thac")   # vòng đời TÀI SẢN
    op_right: Mapped[str] = mapped_column(String(20), default="so_huu")      # quyền KHAI THÁC (khác vòng đời)
    operator_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    partner_name: Mapped[str] = mapped_column(String(120), default="")       # đối tác khai thác/chủ xe ngoài
    # Đợt 3: trỏ về hồ sơ chủ xe hợp tác. Tên đối tác dạng chữ ở trên chỉ để hiển thị và giữ nguyên văn
    # nguồn; cấn trừ và quyết toán đi theo ID này vì phải đúng đối tác và đúng pháp nhân.
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_partners.id"), nullable=True)
    contract_ref: Mapped[str] = mapped_column(String(60), default="")        # số hợp đồng hợp tác
    contract_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    # HX-1 (11/10/2026) — bốn trường hồ sơ xe mà sheet `THEO DÕI CP` của Vietrip có đủ cho 23 xe mà
    # VTOS không có chỗ giữ. Nạp qua cửa `ho_so_xe`.
    engine_no: Mapped[str] = mapped_column(String(40), default="")           # số máy
    # KHÔNG thêm cột thẻ dầu vào đây, dù sheet nguồn `THEO DÕI CP` xếp thẻ theo từng DÒNG XE.
    # Đợt 2 đội xe đã quyết ngược lại và ghi lý do ngay tại `Employee.fuel_card_last4`: thẻ gắn với
    # TÀI XẾ, vì đổi tài xế mà thẻ gắn vào xe thì mọi giao dịch thẻ sau ngày bàn giao gán nhầm chi
    # phí sang người khác. Thêm cột ở đây là tạo chỗ khai thứ hai cho cùng một việc, và hai chỗ khai
    # thì sẽ có ngày nói khác nhau. Câu "ở Vietourist thẻ cấp theo xe hay theo người" đang chờ
    # Chủ tịch trả lời — xem mục HX-1 trong sổ.
    # AI XÁC NHẬN SỐ GHẾ — Chủ tịch chọn 11/10/2026.
    #
    # `seats` mặc định 45 và không cho rỗng, nên một chiếc chưa ai nhập ghế đọc ra ĐÚNG Y một chiếc
    # 45 chỗ thật. Không sửa cột (đổi cột là việc có migration và nhiều chỗ đọc), mà ghi RIÊNG ai đã
    # xác nhận: có tên người là con số đã có người chịu trách nhiệm, rỗng là chưa ai khai. Nhờ vậy
    # một chiếc 45 chỗ THẬT đã xác nhận thì không bị gắn nhãn "chưa biết" mãi — đó là chỗ phương án
    # "cảnh báo khi đúng bằng 45" sai, và là lý do Chủ tịch chọn khác.
    seats_xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    seats_xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    odo_km: Mapped[int] = mapped_column(Integer, default=0)                   # số km đồng hồ đã xác nhận
    odo_at: Mapped[date | None] = mapped_column(Date, nullable=True)          # thời điểm của số km đó
    source_note: Mapped[str] = mapped_column(String(200), default="")


class VehicleRate(Base):
    """Bảng giá xe nội bộ theo tuyến (giá trọn chuyến): cột xe Vietrip – VTD và cột xe hợp tác. Master data, Chủ tịch + TGĐ duyệt, hiệu lực theo ngày."""
    __tablename__ = "vehicle_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    route: Mapped[str] = mapped_column(String(80))
    days: Mapped[int] = mapped_column(Integer, default=0)
    internal_price: Mapped[float | None] = mapped_column(TIEN)          # xe nội bộ Vietrip – VTD, nullable=True
    partner_price: Mapped[float | None] = mapped_column(TIEN)           # xe hợp tác hỗ trợ (0 = không áp dụng, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")       # pending / active / rejected
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GuideRate(Base):
    """Bảng giá thù lao HDV theo tuyến (đồng/ngày) – master data, Chủ tịch + TGĐ ký, hiệu lực theo ngày; lễ Tết ×2.

    Đợt 3 phòng HDV · 07/10/2026 – THÊM `loai_tour`. Chủ tịch chốt 06/10: "thù lao theo ngày × chặng
    tour, và tuỳ LOẠI TOUR có phí khác nhau". Trước đó bảng chỉ khoá theo tuyến, nên một tuyến chỉ có
    đúng một đơn giá — không nói được rằng dẫn đoàn nước ngoài tuyến ấy trả khác dẫn khách lẻ.

    `loai_tour` RỖNG nghĩa là "áp cho mọi loại tour", KHÔNG phải "chưa biết": đó là bản giá chung, và
    hàng trăm bản giá cũ đều thuộc loại này. Phép tra lấy bản KHỚP ĐÚNG loại trước, không có mới rơi
    về bản chung — nếu làm ngược thì một bản chung mới ký sẽ che mất bản riêng đã có.
    """
    __tablename__ = "guide_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    route: Mapped[str] = mapped_column(String(80))
    loai_tour: Mapped[str] = mapped_column(String(20), default="", server_default="", index=True)
    days: Mapped[float] = mapped_column(Float, default=0)
    rate_per_day: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    old_rate_per_day: Mapped[float | None] = mapped_column(TIEN, nullable=True)
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
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    # DL-1 (11/10/2026) — lệnh này ra từ ĐỀ NGHỊ nào. Chuỗi Chủ tịch đặc tả: Điều hành đề nghị →
    # Giám đốc đội xe lập lệnh → tài xế nhận.
    #
    # Để RỖNG ĐƯỢC, và đó là cố ý: bắt buộc ngay thì mười tệp phép kiểm của các làn khác đỏ, và
    # quan trọng hơn là Điều hành chưa kịp chuyển sang dùng cửa đề nghị. Nhưng chỗ hở không đếm
    # được là chỗ hở sẽ ở lại mãi — nên `de_nghi_xe.lenh_khong_qua_de_nghi()` đếm nó, cùng khuôn
    # với `misa.thieu_tai_khoan()`. Con số về 0 thì siết thành bắt buộc là một dòng.
    de_nghi_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_vehicle_requests.id"),
                                                   nullable=True, index=True)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    rate_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_rates.id"), nullable=True)   # tuyến trong bảng giá
    internal_price: Mapped[float | None] = mapped_column(TIEN)         # giá thuê nội bộ cả chuyến, nullable=True
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")  # cho_xac_nhan / da_xac_nhan / hoan_thanh / huy
    incident_note: Mapped[str] = mapped_column(String(300), default="")
    # Đợt 4: ghi vết gợi ý điều xe. Lưu CẢ phương án máy đề xuất lẫn phương án người chọn, và lý do khi chọn
    # khác – đó là dữ liệu duy nhất để sau này biết thuật toán gợi ý có tốt lên hay không. Không có nó thì
    # mỗi quý lại tranh luận bằng cảm nhận.
    phuong_an_ai_goi_y: Mapped[str] = mapped_column(Text, default="")
    phuong_an_da_chon: Mapped[str] = mapped_column(String(60), default="")
    ly_do_khac_goi_y: Mapped[str] = mapped_column(String(300), default="")


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
    # Đợt A2 – khúc cuối của chuỗi. BẢN GỐC của việc đã trả là các dòng `chi_ky_luong`; hai cột
    # dưới đây là BẢN TÓM cho báo cáo đọc, và chỉ được ghi trong cùng giao dịch với nơi sinh ra nó
    # (services/chi_luong.py::ghi_nhan). Rỗng nghĩa là chưa chi lần nào – khác "đã chi 0 đồng".
    tra_trang_thai: Mapped[str] = mapped_column(String(16), default="")   # dang_chi/da_tra_du/loi_chi
    tra_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)     # đầu vào do HCNS nhập: công chuẩn, công thực tế theo mã NV
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
