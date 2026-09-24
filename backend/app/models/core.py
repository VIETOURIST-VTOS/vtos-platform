"""Mô hình dữ liệu VTOS (SQLAlchemy 2.0)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.kieu_tien import TIEN

# ---------- Pháp nhân trong tập đoàn ----------
COMPANY_KINDS = {
    "me": "Công ty mẹ",
    "con": "Công ty con",                    # hợp nhất toàn bộ
    "lien_ket": "Công ty liên kết",          # phương pháp vốn chủ sở hữu, không cộng gộp
    "doc_lap": "Công ty độc lập",            # cùng nhóm quản trị nhưng NGOÀI phạm vi hợp nhất
    "chi_nhanh": "Chi nhánh / đơn vị trực thuộc",
}


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
        """Nằm trong phạm vi hợp nhất: mẹ, công ty con, chi nhánh.

        Công ty liên kết áp dụng phương pháp vốn chủ sở hữu; công ty độc lập cùng nhóm quản trị nhưng
        không hợp nhất – cả hai loại này giao dịch với công ty mẹ là giao dịch với BÊN LIÊN QUAN,
        phải thuyết minh chứ không loại trừ.
        """
        return self.kind in ("me", "con", "chi_nhanh")

    def related_party(self) -> bool:
        """Bên liên quan cần thuyết minh trên báo cáo tài chính."""
        return self.kind in ("lien_ket", "doc_lap")


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
    # Mở 24/9/2026 theo Bản mô tả công việc Sale Admin — Phòng Kinh doanh Đoàn, hiệu lực 01/9/2026.
    # Vị trí này KHÔNG bán hàng và KHÔNG điều hành tour, nên nó không nằm trong nhóm SALES của
    # access.py: nhóm ấy mang theo quyền GỬI yêu cầu đặt dịch vụ và quyền giữ chỗ, hai thứ Phần V
    # bản mô tả cấm đích danh. Một vai trò mới tốn một dòng; nhét nhờ vào nhóm có sẵn thì rẻ hơn
    # hôm nay và sai vĩnh viễn — mọi quyền nhóm ấy nhận về sau sẽ tự chảy sang vị trí này.
    "sales_admin": "Sale Admin phòng Đoàn",
    "nv_mkt": "Nhân viên Marketing",
    "ketoan": "Kế toán",
    "hcns": "Nhân sự Hành chính",
    "cntt": "Công nghệ thông tin",
    "bks": "Ban Kiểm soát (chỉ đọc)",
    # Hai vai trò mở ngày 07/9/2026 theo bảng lương T07-08: người ở hiện trường và ban visa cần đăng nhập,
    # nhưng không được thấy hàng đợi điều hành hay dữ liệu khách của phòng khác.
    "xe_hdv": "Tài xế & Hướng dẫn viên",
    # Mở 07/9/2026. Trước bản này Giám đốc điều hành đội xe mang chung vai trò xe_hdv với tài xế, nên bị
    # khoá ngoài đúng ba màn hình đội xe mà chính ông phụ trách – và vì tham số xe_nguoi_lap_lenh chỉ định
    # ông là người duy nhất được lập lệnh điều xe, kết quả là KHÔNG AI lập được lệnh: người có quyền theo
    # chỉ đạo thì không vào được cửa, người vào được cửa thì không có quyền theo chỉ đạo.
    "gd_doi_xe": "Giám đốc điều hành đội xe",
    # Mở 07/9/2026 cùng với việc toàn bộ HDV chuyển sang cộng tác viên. Người điều phối chuyến là người
    # DUY NHẤT trong phòng Hướng dẫn còn ký hợp đồng lao động – điều phối là công việc quản lý, và một
    # cộng tác viên phân việc cho cộng tác viên khác thì vừa không có thẩm quyền, vừa là bằng chứng cho
    # thấy quan hệ "cộng tác" thực chất là quan hệ lao động. Trước bản này chưa có vai trò cho vị trí đó.
    "tp_hd": "Trưởng phòng Hướng dẫn",
    "nv_visa": "Chuyên viên Visa",
    "hanh_chinh": "Hành chính (không xem bảng lương)",
    # Ba VAI TRÒ MÁY, mở 08/9/2026 (Đợt 2 mục P8). Trước bản này ba robot dùng chung tài khoản người:
    # robot Kiểm soát mượn vai trò bks, robot Phân quyền và robot Viết phần mềm mượn vai trò cntt. Hậu
    # quả không nằm ở quyền mà nằm ở NHẬT KÝ: mọi việc ba robot làm đều mang tên một con người, nên khi
    # cần biết ai đã đổi cái gì thì câu trả lời là "cntt" – đúng nhưng vô dụng. Người vận hành bị ghi
    # tên cho việc mình không làm, và robot thì không ai truy được.
    "robot_pq": "Robot Phân quyền",
    "robot_ks": "Robot Kiểm soát",
    "robot_vpm": "Robot Viết phần mềm",
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
    # Bổ sung 07/9/2026 (đặc tả Tài khoản & phân quyền, mục B3)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    # rỗng = CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ – giữ đúng quy ước đã dùng ở tours, bookings, vehicles
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Không có trường này thì không phát hiện được tài khoản bỏ hoang, hay người đã nghỉ mà tài khoản chưa khóa.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # Mật khẩu mặc định là MÃ NHÂN VIÊN, mà mã nhân viên nằm công khai trên bảng lương và danh bạ. Ai biết mã
    # là đăng nhập được người khác, và mọi thao tác sau đó mang tên người bị mượn.
    ngoai_bien_che: Mapped[bool] = mapped_column(Boolean, default=False)
    # Kế toán trưởng thuê ngoài, kiểm toán, tư vấn: có tài khoản nhưng không có trong bảng lương – đánh dấu
    # để danh sách đối chiếu không báo lệch, và để rà quyền hằng tháng nhìn ra ngay ai là người ngoài.
    role_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    role_changed_by: Mapped[str] = mapped_column(String(50), default="")
    # TC-74 (19/9/2026) – anh Tuấn: "ngoài khối kinh doanh em mở thêm cho nhân viên sau này nhập tay
    # vào, ví dụ hdv, dh... cũng được quyền bán khách".
    #
    # QUYỀN BÁN THÀNH DỮ LIỆU, KHÔNG CÒN LÀ MỘT TUPLE TRONG MÃ. Trước đây "ai bán được" là bốn vai
    # Kinh doanh viết chết trong services; hướng dẫn viên bán một chuyến là phải sửa mã. Đo 19/9:
    # Điều hành đã bán 4,24 tỷ và Visa 2,64 tỷ trong chín tháng – việc có thật, chỉ là hệ thống
    # không có chỗ ghi.
    #
    # CỘT NÀY KHÔNG ÁP CHO KHỐI KINH DOANH: bốn vai ấy bán hàng là đương nhiên và luôn có chỉ tiêu.
    # Ô tick chỉ dành cho người bộ phận khác, và bật nó KHÔNG kéo người ta vào bảng xếp hạng kinh
    # doanh – quyền BÁN khác nghĩa vụ ĐẠT CHỈ TIÊU. Xem services/nguoi_ban_hang.py.
    duoc_ban_hang: Mapped[bool] = mapped_column(Boolean, default=False)
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # GIAO DIỆN RIÊNG CỦA TỪNG NGƯỜI – TC-67, anh Tuấn giao 18/9/2026
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # Anh Tuấn viết: "Lưu lựa chọn riêng theo tài khoản nhân viên, giữ nguyên khi chuyển trang và
    # đăng nhập lại." Chữ ĐĂNG NHẬP LẠI là chỗ quyết định nó phải nằm ở đây chứ không nằm trong
    # localStorage của trình duyệt: localStorage đi theo MÁY, không đi theo NGƯỜI – chỉnh ở máy
    # tính thì mở điện thoại vẫn về mặc định, và xoá bộ nhớ trình duyệt là mất. Trình duyệt vẫn
    # giữ một BẢN CHÉP, nhưng chỉ để vẽ ngay khỏi loé nền; bản CẤT nằm ở đây.
    #
    # HAI CỘT CHỨ KHÔNG MỘT: hai câu trả lời khác nhau thì kiểm từng cái một, và đếm được riêng
    # ("bao nhiêu người đang để nền sáng"). Nhét "sang/18" vào một cột là sớm muộn có người ghi
    # vào đó một chuỗi thứ ba.
    #
    # RỖNG KHÁC MẶC ĐỊNH – đây là lý do `gd_nen` để "" và `gd_co_chu` để NULL chứ không điền sẵn
    # "toi" và 16. "" nghĩa là NGƯỜI NÀY CHƯA CHỌN GÌ, còn "toi" nghĩa là người này đã chọn nền
    # tối. Hai điều ấy khác nhau ở đúng cái ngày ai đó đổi mặc định của hệ thống: người chưa chọn
    # phải đi theo mặc định mới, người đã chọn thì không. Điền sẵn giá trị mặc định vào cột là
    # xoá mất sự khác biệt ấy, và không cách nào lấy lại.
    gd_nen: Mapped[str] = mapped_column(String(8), default="")          # "" | "toi" | "sang" | "may"
    gd_co_chu: Mapped[int | None] = mapped_column(Integer, nullable=True)   # NULL | 14..20


# Bộ giá trị hợp lệ của giao diện, khai MỘT CHỖ để cửa ghi, phép thử và màn hình cùng đọc một
# nguồn. Đổi dải cỡ chữ thì đổi ở đây, không đi sửa ba nơi.
GIAO_DIEN_NEN = ("toi", "sang", "may")   # navy tối · trắng sáng · theo cài đặt máy
GIAO_DIEN_CO_MIN, GIAO_DIEN_CO_MAX = 14, 20
GIAO_DIEN_MAC_DINH_NEN, GIAO_DIEN_MAC_DINH_CO = "toi", 16


GRANT_KINDS = {"menu": "Màn hình", "capability": "Năng lực"}
# Năng lực cấp lẻ được cho một người, không đi kèm vai trò.
CAPABILITIES = {
    "bang_luong": "Xem bảng lương toàn công ty",
    # Cấp 09/9/2026 theo chỉ đạo "tất cả báo cáo về Trưởng phòng Điều hành". Cấp bằng NĂNG LỰC THEO
    # NGƯỜI chứ không sửa vai trò tp_dh: sửa vai trò là mở cho mọi Trưởng phòng Điều hành từ nay về
    # sau, kể cả người kế nhiệm mà chưa ai quyết định gì. Đây là quyền cấp cho MỘT NGƯỜI vì việc của
    # người đó, nên nó phải hết hạn và phải nhìn thấy được ở màn hình ngoại lệ – y hệt bảng lương.
    "bao_cao_moi_phong": "Xem báo cáo tự động của MỌI phòng ban và toàn công ty",
}
GRANT_MAX_DAYS = 90


class UserGrant(Base):
    """Ngoại lệ quyền CÓ THỜI HẠN cho một người (chỉ đạo 07/9/2026).

    Vì sao phải có bảng này chứ không sửa vai trò: quyền xem bảng lương toàn công ty được cấp cho RIÊNG
    Kế toán trưởng, trong khi vai trò "ketoan" có nhiều người. Nếu chỉ có vai trò làm công cụ thì mở cho
    một người là mở cho cả nhóm.

    Vì sao BẮT BUỘC có hạn: không có hạn thì quyền chỉ nở ra chứ không co lại – người ta nhớ lúc cấp và
    quên lúc thu. Hết hạn là tự mất hiệu lực, không chờ ai nhớ.
    """
    __tablename__ = "user_grants"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12))            # menu / capability
    value: Mapped[str] = mapped_column(String(80))           # đường dẫn màn hình, hoặc khóa trong CAPABILITIES
    from_date: Mapped[date] = mapped_column(Date)
    # Rỗng = KHÔNG THỜI HẠN. Mặc định vẫn là có hạn (tối đa GRANT_MAX_DAYS ngày) vì quyền có hạn thì tự
    # co lại, còn quyền vô hạn thì chỉ nở ra. Chỉ Chủ tịch cấp được loại không thời hạn, và loại đó luôn
    # nổi lên ở danh sách rà quyền hằng tháng – đổi "tự hết hạn" lấy "không bao giờ bị quên".
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(String(300))         # lý do bằng lời, bắt buộc
    granted_by: Mapped[str] = mapped_column(String(50), default="")
    approved_by: Mapped[str] = mapped_column(String(50), default="")   # chỉ Chủ tịch hoặc TGĐ
    active: Mapped[bool] = mapped_column(Boolean, default=True)        # thu hồi sớm thì tắt cờ, không xóa
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def hieu_luc(self, hom_nay: date | None = None) -> bool:
        d = hom_nay or date.today()
        if not (self.active and self.approved_by and self.from_date <= d): return False
        return self.to_date is None or d <= self.to_date

    def vo_han(self) -> bool:
        return self.to_date is None


# ---------- Tham số chính sách (rules engine) ----------
class Param(Base):
    """Tham số có hiệu lực theo ngày. Bản ghi mới chỉ có hiệu lực khi đủ 2 chữ ký."""
    __tablename__ = "params"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    # RỖNG LÀ MỘT TRẠNG THÁI HỢP LỆ, không phải dữ liệu thiếu — nên cột khai default="".
    #
    # Hai mốc `ngay_van_hanh_that` và `ngay_du_lieu_that_vietrip` cố ý để trống: chúng chờ hai chữ
    # ký, và điền sẵn một ngày vào đó là ký thay Chủ tịch bằng một dòng mã. Trước 11/9/2026 cột này
    # không khai mặc định, nên bộ kiểm độ dài (K11) đọc mô hình ra "cột bắt buộc phải có người
    # điền" và báo hai dòng ấy là dữ liệu thiếu. Hai lane nói ngược nhau vì MÔ HÌNH không nói rõ.
    # Khai default="" là để mô hình nói đúng điều hệ thống đang làm: chưa chốt thì trống, và trống
    # đọc ra "chưa chốt" chứ không đọc ra số 0 hay một ngày ai đó đoán hộ.
    value: Mapped[str] = mapped_column(String(200), default="", server_default="")
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
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
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
    reference_price: Mapped[float | None] = mapped_column(TIEN, nullable=True)
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
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    tour_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))      # người điều hành duy nhất
    # Dự toán
    price_per_pax: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    fixed_cost: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    var_cost_per_pax: Mapped[float | None] = mapped_column(TIEN, nullable=True)
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
    actual_revenue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    promo_value: Mapped[float | None] = mapped_column(TIEN)          # giảm giá/mã KM → dòng giá vốn, nullable=True
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # pháp nhân chủ quản – rỗng là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ
    kt_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cntt_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    settlement_version: Mapped[int] = mapped_column(Integer, default=1)    # V.01, V.02… mỗi lần Kế toán trả lại
    # trong_nuoc / nuoc_ngoai – Chủ tịch chốt 11/9/2026, hai hình thức quyết toán.
    #
    # DÒNG NÀY TỪNG BIẾN MẤT, và đó là lý do nó được ghi chú dài. Bản nâng cấp x1c7d2e9f4a86 có tạo
    # cột tours.hinh_thuc trong cơ sở dữ liệu, và MƯỜI chỗ trong mã đọc t.hinh_thuc, nhưng dòng khai
    # cột ở mô hình thì không còn trên nhánh chính – mất trong một lần hai phiên cùng ghi đè
    # models/core.py. Cột có trong CSDL mà không có trong mô hình thì SQLAlchemy không biết nó tồn
    # tại: mọi lời gọi t.hinh_thuc ném AttributeError, và cả phân hệ quyết toán lớp 3 chết ngay khi
    # có người mở – trong khi phép thử nào không chạm tới chuyến thật vẫn xanh.
    #
    # KHÁC HẲN cột tour_type ở trên: tour_type phân biệt tour trọn gói với dịch vụ lẻ (package /
    # non_package). Cột này phân biệt trong nước với nước ngoài – hai trục khác nhau, và một chuyến
    # mang cả hai giá trị cùng lúc (tour lẻ nước ngoài là package + nuoc_ngoai).
    #
    # Hình thức quyết định phép kiểm nào chạy: nước ngoài thì bắt buộc khai tỷ giá và NGÀY tỷ giá cho
    # mọi khoản ngoại tệ, trong nước thì không; giá trẻ em cũng soát theo tỷ lệ khác nhau. Rỗng nghĩa
    # là chưa ai xếp – suy từ cột country được, nhưng suy ngầm rồi tính tiền theo cái suy ấy là chỗ
    # sinh lỗi lặng.
    hinh_thuc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Đ-2c · Chủ tịch chốt 14/9/2026: "tour châu Âu là tour nước ngoài nên tính 0%, nhưng em cứ viết
    # cấu trúc và thuật toán, còn tỷ lệ % để cho Điều hành nhập vào."
    #
    # Hai ô này là hai thuế suất CỦA CHÍNH CHUYẾN NÀY, do Điều hành gõ. Rỗng thì lùi về tham số công
    # ty đang hiệu lực — không bao giờ về một hằng số viết trong mã.
    #
    # HẬU TỐ `_pt` LÀ PHẦN CỦA TÊN, KHÔNG PHẢI TRANG TRÍ. Đơn vị là PHẦN TRĂM: 8 nghĩa là 8%. Tham số
    # công ty thì là số thập phân (0.08). Hai cách viết cùng một thứ, lệch nhau 100 lần, và bài học
    # ấy đã phải trả giá một lần ở ô % chia tip (12/9) — nên đơn vị nằm ngay trong tên cột.
    thue_suat_ra_pt: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Dòng "dịch vụ tiêu dùng ngoài Việt Nam" của hoá đơn tour nước ngoài. Mặc định 0%, nhưng là 0%
    # ĐỌC TỪ THAM SỐ chứ không phải số 0 viết cứng trong mã: chính sách thuế đổi thì đổi tham số.
    thue_suat_ngoai_vn_pt: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    seats_promo: Mapped[int | None] = mapped_column(Integer, default=0)   # số chỗ khuyến mãi – KHÔNG phải tiền, ngoài phạm vi K2
    price_chd: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    price_inf: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    price_promo: Mapped[float | None] = mapped_column(TIEN, nullable=True)
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
    discount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour: Mapped["Tour"] = relationship()
    sales: Mapped["User"] = relationship()


class Booking(Base):
    __tablename__ = "bookings"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    request_id: Mapped[int] = mapped_column(Integer)
    sales_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # TC-74 – booking do ĐỐI TÁC bán (J Travel, JTV…). Rỗng = do nhân viên bán, không phải "chưa rõ".
    #
    # KHÔNG thay `sales_id` bằng đối tác: cột ấy NOT NULL và vẫn phải trỏ vào người tiếp nhận hồ sơ
    # bên trong công ty – ai đó phải chịu trách nhiệm chuyến ấy. Cột này nói THÊM rằng nguồn khách
    # đến từ đối tác, nên doanh thu KHÔNG vào chỉ tiêu của người tiếp nhận.
    doi_tac_id: Mapped[int | None] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(60))
    care_note: Mapped[str] = mapped_column(Text, default="")
    pax: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    discount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    promo_code: Mapped[str] = mapped_column(String(40), default="")
    campaign_code: Mapped[str] = mapped_column(String(40), default="")
    counts_for_target: Mapped[bool] = mapped_column(Boolean, default=True)  # cờ tính chỉ tiêu
    sla_minutes: Mapped[int] = mapped_column(Integer, default=0)            # phút từ yêu cầu → booking
    sla_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    paid: Mapped[float | None] = mapped_column(TIEN, nullable=True)
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
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # pháp nhân chủ quản – rỗng là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ
    deposit_pct: Mapped[float] = mapped_column(Float, default=30)           # % cọc theo sản phẩm
    locked: Mapped[bool] = mapped_column(Boolean, default=False)            # khóa cập nhật thông tin khách (đóng tour / thu đủ)
    lock_reason: Mapped[str] = mapped_column(String(120), default="")
    cancel_reason: Mapped[str] = mapped_column(String(200), default="")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_charge: Mapped[float | None] = mapped_column(TIEN)          # phí hủy giữ lại làm doanh thu, nullable=True
    service_type: Mapped[str] = mapped_column(String(20), default="")       # non-package: VISA/FLIGHT/HOTEL/VEHICLE/RESTAURANT/LAND/GUIDE/OTHER
    country: Mapped[str] = mapped_column(String(60), default="")
    customer_email: Mapped[str] = mapped_column(String(120), default="")
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(TIEN)            # giá vốn NCC của dịch vụ lẻ, nullable=True
    supplier_name: Mapped[str] = mapped_column(String(160), default="")
    # VPM-7 – giữ chỗ có thời hạn. Xem app/models/giu_cho.py để biết vì sao.
    # `giu_cho_den` rỗng nghĩa là CHƯA ĐẶT HẠN (booking cũ có từ trước 11/9/2026), không phải "hết hạn
    # ngay". Robot đặt hạn cho chúng ở lần chạy đầu; ở giữa hai thời điểm ấy chúng vẫn giữ chỗ bình thường.
    giu_cho_den: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    giu_cho_het: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    giu_cho_het_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gia_han_lan: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    tour: Mapped["Tour"] = relationship(back_populates="bookings")
    sales: Mapped["User"] = relationship(foreign_keys=[sales_id])


# ---------- Cảnh báo (robot) ----------
# KS-4 · Vòng đời cảnh báo, khai ra cho máy đọc được (bộ kiểm tools/ks4_canh_bao.py đối chiếu).
ALERT_TRANG_THAI: dict[str, str] = {
    "moi": "vừa sinh, chưa ai nhận",
    "dang_xu_ly": "đã có người nhận",
    "da_xu_ly": "người nhận báo xong, chờ xác nhận",
    "dong": "đã xác nhận xong",
    "bo_qua": "quyết định không xử lý — phải có lý do, đây là nhánh cho dữ liệu lịch sử",
}

# Chuyển trạng thái hợp lệ. KHÔNG cho nhảy thẳng mới → đóng: đóng khi chưa ai nhận là đóng để cho
# sạch màn hình, đúng cái đang làm 1.703 dòng trở nên vô nghĩa.
ALERT_CHUYEN: dict[str, tuple[str, ...]] = {
    "moi": ("dang_xu_ly", "bo_qua"),
    "dang_xu_ly": ("da_xu_ly", "bo_qua"),
    "da_xu_ly": ("dong", "dang_xu_ly"),
    "dong": (),
    "bo_qua": ("dang_xu_ly",),
}


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
    # PQ-9 (11/9/2026) · MỘT cảnh báo MỘT người. to_roles ở trên là danh sách được BÁO TIN; nó
    # không phải người chịu trách nhiệm, và trước hôm nay hệ thống không phân biệt hai thứ ấy.
    #
    # Đo bản đang chạy: 1.557 trên 1.703 cảnh báo chưa xử lý, 146 cái từng được xử lý. Nhìn vào
    # to_roles thì hiểu ngay vì sao – một cảnh báo đỏ quá hạn thu tiền gửi cho
    # "nv_kd,gd_kd,tp_dh,ketoan", tức gửi cho bốn vai trò, tức không gửi cho ai.
    #
    # Để trống là hợp lệ và phải đếm được: có loại cảnh báo không suy ra được chủ (cảnh báo dòng
    # tiền gửi Ban lãnh đạo). Chỗ nguy hiểm không phải là ô trống, mà là ô trống không ai đếm.
    nguoi_phu_trach: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    giao_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---------------------------------------------------------------------------------------
    # KS-4 (11/9/2026) · VÒNG ĐỜI CẢNH BÁO. Chín cột dưới đây trả lời câu hỏi "vì sao 1.703 dòng
    # đỏ này không ai xử lý". Cột `resolved` đúng/sai ở trên gộp BA trạng thái khác nhau vào một ô:
    # chưa ai nhận · đang có người làm · đã xong. Hệ quả đo được: hai người cùng làm một việc mà
    # không ai biết, và "đóng vì đã xử lý" không phân biệt được với "đóng vì là dữ liệu lịch sử".
    #
    # `resolved` GIỮ NGUYÊN, không bỏ: mọi màn hình và robot đang đọc nó. Hai cột đi cùng nhau —
    # trang_thai là sự thật đầy đủ, resolved là hình chiếu đúng/sai của nó cho mã cũ.
    # ---------------------------------------------------------------------------------------
    trang_thai: Mapped[str] = mapped_column(String(20), default="moi", server_default="moi", index=True)
    # Người CỤ THỂ phải làm. to_roles ở trên trả lời "ai được xem", không trả lời "ai phải làm" –
    # gửi cho bốn vai trò là gửi cho không ai.
    nguoi_nhan_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Mốc phải xong. Không có cột này thì câu "cảnh báo đang trễ" không đo được, và 1.310 dòng đỏ
    # đứng ngang nhau dù có dòng mở từ tháng trước.
    han_xu_ly: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dong_boi_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Đóng mà không phải nói dựa vào đâu thì nút đóng là nút giấu việc.
    bang_chung: Mapped[str] = mapped_column(Text, default="", server_default="")
    # 'lich_su' hay 'phat_sinh'. Dữ liệu cũ đổ sang sinh cảnh báo là việc DỌN DỮ LIỆU; vi phạm sau
    # ngày vận hành thật là việc KỶ LUẬT. Trộn hai thứ vào một danh sách là cách chắc chắn nhất để
    # không xử lý được thứ nào.
    nguon: Mapped[str] = mapped_column(String(20), default="", server_default="", index=True)
    # Khoá gom trùng: cùng một vấn đề sinh lại mỗi lượt quét thì cộng dồn vào một dòng, không đẻ
    # dòng mới. Trước đây mỗi robot tự dò theo (kind, ref) bằng tay — nơi nào quên là nơi ấy ngập.
    gom_khoa: Mapped[str] = mapped_column(String(100), default="", server_default="", index=True)


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



# ---------- Nhật ký AI (chỉ đạo 07/9/2026) ----------
AI_TASKS = {
    "hoi_dap": "Hỏi–đáp trên dữ liệu",
    "tin_khach": "Tin nhắn gửi khách",
    "tin_khach_nhap": "Soạn nháp tin cho khách",
    "vb_noi_bo": "Soạn văn bản nội bộ",
    "doc_chung_tu": "Đọc chứng từ",
    "cham_diem": "Nhận xét & chấm điểm",
    "canh_bao": "Cảnh báo & nhắc việc",
}
# 1 quan sát · 2 soạn nháp (người bấm gửi) · 3 tự động trong hạn mức (người hậu kiểm) · 4 robot mã xác định
AI_LEVELS = {1: "Quan sát", 2: "Soạn nháp", 3: "Tự động trong hạn mức", 4: "Tự động toàn phần (mã xác định)"}
AI_REVIEW_STATES = {
    "khong_can": "Không cần hậu kiểm",
    "cho_hau_kiem": "Chờ hậu kiểm",
    "chap_nhan": "Đã hậu kiểm – chấp nhận",
    "da_sua": "Đã hậu kiểm – người sửa lại",
    "thu_hoi": "Đã thu hồi",
}


class AiRun(Base):
    """Mỗi lần phần mềm gọi mô hình ngôn ngữ hoặc gửi nội dung do AI sinh ra.

    Trước bản này, ba chỗ dùng mô hình ngôn ngữ – trả lời khách trong hộp thư, chấm câu trả lời của tư vấn
    viên, viết nhận xét báo cáo cho lãnh đạo – KHÔNG để lại vết nào. Trong đó chỗ thứ nhất gửi tin cho khách
    hàng thật. Không có bảng này thì không trả lời được ba câu: AI đã nói gì với ai, ai chịu trách nhiệm hậu
    kiểm, và có bao nhiêu nội dung bị người sửa lại (tỷ lệ bị sửa tăng là tín hiệu phải hạ mức, không phải
    tín hiệu huấn luyện thêm).

    `dau_vao_hash` là mã băm của dữ liệu đưa vào mô hình, lấy đúng khuôn mẫu đã dùng cho đội xe
    (fleet_ai_runs): nó biến câu "chạy lại cùng dữ liệu phải ra cùng kết quả" thành điều kiểm chứng được
    thay vì một lời hứa. Không lưu nguyên văn dữ liệu vào vì trong đó có tên và số điện thoại khách.
    """
    __tablename__ = "ai_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    tac_vu: Mapped[str] = mapped_column(String(20), index=True)          # AI_TASKS
    muc: Mapped[int] = mapped_column(Integer, default=1)                 # AI_LEVELS – mức TẠI THỜI ĐIỂM CHẠY
    ref: Mapped[str] = mapped_column(String(60), default="")             # conv:12, tour:DL001…
    phuc_vu_vai_tro: Mapped[str] = mapped_column(String(30), default="")  # phục vụ vai trò nào
    phuc_vu_nguoi: Mapped[str] = mapped_column(String(50), default="")    # tài khoản được phục vụ; rỗng = robot
    mo_hinh: Mapped[str] = mapped_column(String(60), default="")          # tên mô hình, rỗng khi chạy theo quy tắc
    nguon: Mapped[str] = mapped_column(String(12), default="")            # claude / quy_tac
    dau_vao_hash: Mapped[str] = mapped_column(String(64), default="")
    so_ban_ghi: Mapped[int] = mapped_column(Integer, default=0)
    ket_qua: Mapped[str] = mapped_column(Text, default="")                # nội dung đã sinh, cắt ngắn
    tokens_vao: Mapped[int] = mapped_column(Integer, default=0)
    tokens_ra: Mapped[int] = mapped_column(Integer, default=0)
    trang_thai: Mapped[str] = mapped_column(String(16), default="khong_can", index=True)   # AI_REVIEW_STATES
    hau_kiem_boi: Mapped[str] = mapped_column(String(50), default="")
    hau_kiem_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hau_kiem_ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    loi: Mapped[str] = mapped_column(String(300), default="")


# ---------- Quyền AI theo vị trí (chỉ đạo 07/9/2026, đặc tả phần C) ----------
# Sáu nhóm việc AI có thể làm. Chia theo VIỆC chứ không theo công cụ: cùng một mô hình ngôn ngữ, nhưng
# soạn tin gửi khách và tóm tắt số liệu nội bộ là hai mức rủi ro hoàn toàn khác nhau.
AI_GROUPS = {
    "hoi_dap": "Hỏi–đáp trên dữ liệu",
    "tin_khach": "Soạn và gửi tin cho khách",
    "vb_noi_bo": "Soạn văn bản nội bộ",
    "doc_chung_tu": "Đọc chứng từ",
    "cham_diem": "Nhận xét & chấm điểm con người",
    "canh_bao": "Cảnh báo & nhắc việc",
}
# Bốn việc AI KHÔNG được làm ở bất kỳ mức nào – ghi vào mã để không ai phải nhớ:
AI_CAM = (
    "Quyết định cho tiền ra: duyệt đề nghị chi, lập lệnh chi, duyệt dự toán, mở cổng biên",
    "Ghi hoặc sửa số kế toán đã xác nhận; khóa hoặc mở kỳ",
    "Đổi tài khoản, vai trò, giá bán hoặc chính sách",
    "Cam kết với khách những điều không có trong dữ liệu VTOS: giảm giá, giữ chỗ, hoàn tiền",
)
AI_HAN_MUC_BAT_BUOC = ("khung_gio", "so_luot_ngay", "loai_noi_dung", "nguoi_hau_kiem")


class AiPosition(Base):
    """Mức quyền AI của một VỊ TRÍ trên một NHÓM VIỆC.

    Bảng này phải điều khiển hành vi thật, không phải bảng trang trí: robot trả lời khách đọc thẳng mức
    ở đây để quyết định tự gửi hay chỉ để nháp. Một bảng phân quyền mà hệ thống không đọc thì đến lúc
    có chuyện, nó chỉ chứng minh rằng người ta đã tưởng là mình kiểm soát được.

    Mức 3 (tự động trong hạn mức) BẮT BUỘC khai đủ hạn mức – xem AI_HAN_MUC_BAT_BUOC. Mức 3 không hạn
    mức chính là tình trạng trước ngày 07/9/2026: AI gửi tin cho khách thật, không giới hạn, không ai
    hậu kiểm, không để lại vết.
    """
    __tablename__ = "ai_positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vai_tro: Mapped[str] = mapped_column(String(30), index=True)
    tac_vu: Mapped[str] = mapped_column(String(20), index=True)      # AI_GROUPS
    muc: Mapped[int] = mapped_column(Integer, default=0)             # 0 không dùng … 4 robot mã xác định
    han_muc: Mapped[dict] = mapped_column(JSON, default=dict)        # {khung_gio, so_luot_ngay, gia_tri_toi_da, loai_noi_dung, nguoi_hau_kiem}
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(50), default="")


class AiPause(Base):
    """Nút tắt khẩn AI đối ngoại. Một dòng duy nhất (id = 1).

    Hạ MỌI ô mức 3 xuống mức 2 ngay lập tức, không cần phát hành lại phần mềm. Trước bản này chỉ có một
    tham số ai_tra_loi_bat nằm lẫn giữa bảng chính sách – không ai biết nó ở đó, và nó chỉ tắt được đúng
    một việc.
    """
    __tablename__ = "ai_pause"
    id: Mapped[int] = mapped_column(primary_key=True)
    tam_dung: Mapped[bool] = mapped_column(Boolean, default=False)
    ly_do: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
