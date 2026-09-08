"""Ma trận nhìn thấy dữ liệu theo vai trò.

NGUYÊN TẮC HIỆN HÀNH (chỉ đạo của anh Trần Tuấn ngày 07/9/2026, bảng phân quyền đã duyệt):
- Chủ tịch HĐQT và Tổng giám đốc: xem TẤT CẢ. Đúng hai người, không ai khác.
- Ban Kiểm soát: ĐỌC tất cả, bị chặn mọi thao tác ghi (nghĩa vụ Luật Doanh nghiệp với công ty đại chúng).
- Mọi vai trò còn lại: xem theo PHẠM VI CÔNG VIỆC, mỗi vai trò một danh sách màn hình.

Nhóm ALL_SEEING cũ – gồm bảy vai trò: Chủ tịch, TGĐ, hai Phó TGĐ, Kế toán, CNTT, Ban Kiểm soát – đã được
GIẢI THỂ. Nó là gốc của một lỗi lặp lại: mỗi lần thêm màn hình mới, viết "ALL_SEEING + ai đó" là xong,
nên bảy vai trò cứ tự động nhìn thấy mọi thứ mới mà không ai quyết định điều đó. Hai Phó TGĐ vì vậy đang
xem được dòng tiền, tài khoản ngân hàng, sổ kế toán và nhật ký nghiệp vụ.

Điều KHÔNG đổi trong bản này, để không ai hiểu nhầm là đã nới:
- Nhân viên kinh doanh vẫn chỉ thấy booking của mình, trưởng nhóm thấy nhóm mình (sales_ids_visible).
- Khối Kinh doanh vẫn không thấy cơ cấu chi phí nhà cung cấp (mask_product).
- Tài xế & HDV, Chuyên viên Visa vẫn dùng DANH SÁCH CHO PHÉP: màn hình mới thêm vào hệ thống sẽ không
  tự động mở cho họ.
"""
from fastapi import HTTPException
from app.models.core import User

LEADERSHIP = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt")
CONTROL = ("ketoan", "cntt", "bks")
OPERATIONS = ("tp_dh", "nv_dh")
SALES = ("gd_kd", "tp_kd", "tn_kd", "nv_kd")
MARKETING = ("nv_mkt",)
FIELD = ("xe_hdv",)                                     # tài xế & HDV: người ở hiện trường, chỉ xem việc của chính mình
FLEET_MGR = ("gd_doi_xe",)                              # GĐ điều hành đội xe: toàn bộ phần đội xe, KHÔNG xem
                                                        # dữ liệu khách, booking, bảng lương hay ngân hàng
GUIDE_MGR = ("tp_hd",)                                  # Trưởng phòng Hướng dẫn: điều phối đội HDV cộng tác
                                                        # viên; KHÔNG xem khách, booking, bảng lương, ngân hàng
VISA_STAFF = ("nv_visa",)                               # chuyên viên visa: chỉ phân hệ Visa
ADMIN_STAFF = ("hanh_chinh",)                           # bảo vệ, pháp chế, quan hệ nhà đầu tư: thuộc HCNS
                                                        # nhưng KHÔNG xem bảng lương (chỉ đạo 07/9/2026)

FULL_VIEW = ("chutich", "tgd")                          # xem tất cả – đúng hai người
READ_ALL = ("bks",)                                     # đọc tất cả, bị chặn mọi thao tác ghi
BASE_VIEW = FULL_VIEW + READ_ALL                        # nền của MỌI dòng trong ma trận dưới đây

# Màn hình Nhân sự tách quyền theo TAB (chỉ đạo 07/9/2026). Trước bản này, ai mở được màn hình là thấy cả
# ba tab – nên không có cách nào cho một người xem hồ sơ nhân sự mà không xem luôn bảng lương.
# Bảng lương chỉ còn HCNS theo vai trò; Kế toán trưởng xem toàn công ty bằng NGOẠI LỆ THEO NGƯỜI
# (năng lực "bang_luong"), vì vai trò "ketoan" có nhiều người mà quyền chỉ cấp cho một.
HR_TABS = {"payroll": "Bảng lương", "employees": "Hồ sơ nhân sự", "incidents": "Đánh giá & sự vụ"}
HR_TAB_ROLES = {
    "payroll": BASE_VIEW + ("hcns",),
    "employees": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    "incidents": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "hcns", "cntt"),
}
HR_TAB_CAPABILITY = {"payroll": "bang_luong"}     # tab mở thêm được bằng ngoại lệ theo người
# Cơ cấu chi phí NCC, quyết toán, dòng tiền tour. Phó TGĐ tour đoàn GIỮ quyền này vì phải duyệt dự toán
# đoàn; Phó TGĐ Marketing mất, vì duyệt chi marketing không cần nhìn giá vốn nhà cung cấp của tour.
COST_ROLES = BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "cntt")
# Giao dịch ngân hàng và tổng hợp thu tiền toàn công ty: thu về Kế toán. Trưởng phòng Điều hành mất quyền
# này – điều hành cần dòng tiền TỪNG TOUR (COST_ROLES ở trên), không cần sổ tiền gửi của công ty.
FINANCE_ROLES = BASE_VIEW + ("ketoan",)
AUDIT_ROLES = BASE_VIEW + ("ketoan", "cntt")            # nhật ký kiểm toán
PARAM_ROLES = BASE_VIEW + ("ptgd_doan", "ptgd_mkt", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt")
# Dữ liệu booking (danh sách, phiếu thu, bảo lưu, dịch vụ lẻ). Rộng hơn từng màn hình một vì đây là lớp
# DỮ LIỆU; màn hình nào ai mở được thì xem ở MENU_ROLES.
BOOKING_ROLES = BASE_VIEW + OPERATIONS + SALES + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt")
REQUEST_CREATE_ROLES = OPERATIONS + SALES               # được GỬI yêu cầu đặt dịch vụ: Điều hành + toàn khối Kinh doanh
                                                        # (nguồn duy nhất – máy chủ và giao diện dùng chung, tránh lệch vai trò)
PAYMENT_REQUEST_ROLES = (BASE_VIEW + OPERATIONS +
                         ("ptgd_doan", "ptgd_mkt", "gd_kd", "ketoan", "hcns", "hanh_chinh", "cntt"))
# hanh_chinh mới được thêm: nhóm chi "hành chính" là việc của họ, mà trước nay họ không có màn hình nào
READ_ONLY_ROLES = ("bks",)
# Chặn-mặc-định vẫn giữ nguyên: Ban Kiểm soát không ghi được gì trừ đúng những đường dẫn dưới đây.
#
# Ngày 07/9/2026 anh Trần Tuấn giao vị trí Kiểm soát cho AI: kiểm tra, thử, giám sát và báo cáo mọi
# phòng ban về Chủ tịch. Việc "mở ngoại lệ và yêu cầu phòng ban giải trình" là thao tác GHI, nên
# danh sách này phải nới – nhưng nới đúng ba cửa, không nới nguyên tắc:
#   /kiem-soat/quet     : chạy vòng quét (chỉ đọc dữ liệu nghiệp vụ, chỉ ghi bản ghi phát hiện của
#                         chính robot)
#   /kiem-soat/cham-diem: chấm điểm phòng ban – kết quả luôn ở trạng thái CHỜ HẬU KIỂM của Chủ tịch,
#                         không phải kết luận
#   /ngoai-le/ghi       : ghi giải trình vào ngoại lệ. KHÔNG có /ngoai-le/dong – robot mở việc ra
#                         được, nhưng đóng lại là quyền của người.
# Cố ý KHÔNG có: mọi đường dẫn nghiệp vụ. Robot kiểm soát không sửa được một con số nào của phòng ban
# mà nó đang giám sát – đó là điều làm cho báo cáo của nó có giá trị.
WRITE_ALLOWED_FOR_READ_ONLY = ("/api/v1/auth/password", "/api/v1/auth/login", "/api/v1/robot/r9",
                               "/api/v1/kiem-soat/quet", "/api/v1/kiem-soat/cham-diem",
                               "/api/v1/hach-toan/thieu-gia-von/quet",
                               "/api/v1/ngoai-le/ghi")


def require(u: User, roles: tuple, what: str = "dữ liệu này") -> None:
    if u.role not in roles:
        raise HTTPException(403, f"Vai trò của bạn không được xem {what}")


def sees_all_sales(u: User) -> bool:
    """True nếu người dùng thấy mọi booking/khách; NV kinh doanh chỉ thấy phần mình, trưởng nhóm thấy nhóm mình."""
    return u.role not in ("nv_kd", "tn_kd")


def own_only(u: User) -> bool:
    return u.role == "nv_kd"


def group_only(u: User) -> bool:
    return u.role == "tn_kd" and bool(u.sales_group)


def sales_ids_visible(db, u: User) -> list[int] | None:
    """None = thấy tất cả; danh sách id sale = chỉ thấy booking/phiếu thu của các sale này."""
    from sqlalchemy import select
    if u.role == "nv_kd": return [u.id]
    if u.role == "tn_kd":
        if not u.sales_group: return [u.id]
        return [x for x in db.execute(select(User.id).where(User.sales_group == u.sales_group)).scalars()] or [u.id]
    return None


def can_see_cost(u: User) -> bool:
    return u.role in COST_ROLES


def check_readonly_write(u: User, method: str, path: str) -> None:
    if u.role in READ_ONLY_ROLES and method not in ("GET", "HEAD", "OPTIONS") and path not in WRITE_ALLOWED_FOR_READ_ONLY:
        raise HTTPException(403, "Ban Kiểm soát chỉ có quyền đọc, không được thực hiện thao tác ghi")


# Đường dẫn API mà vai trò bị giới hạn được gọi. Chặn ở MỘT chỗ thay vì sửa từng endpoint: phần lớn endpoint
# chỉ yêu cầu "đã đăng nhập", nên mở một vai trò mới mà không có lớp này là vô tình cho họ đọc cả danh sách
# tour kèm dự toán. Đây là danh sách CHO PHÉP – endpoint mới mặc định nằm ngoài, không phải nằm trong.
RESTRICTED_API_PREFIXES = {
    # /incidents có mặt vì màn hình sự vụ lọc sẵn về đúng người đăng nhập: người ở hiện trường phải đọc
    # được sự vụ ghi cho CHÍNH MÌNH – bị ghi nhận một sự vụ mà không được xem nó là không đối chất được.
    "xe_hdv": ("/api/v1/auth/", "/api/v1/xe-hdv/", "/api/v1/incidents"),
    # GĐ điều hành đội xe: cả phân hệ đội xe và lệnh điều xe, cộng danh mục xe để chọn trong form. Không có
    # /tours, /bookings, /banks, /payroll – phạm vi công việc của ông là chiếc xe, không phải khách hàng và
    # dòng tiền công ty.
    # /nap-du-lieu và /tep có mặt vì ma trận menu ĐÃ cho vai trò này hai màn hình đó (bộ nạp nhật trình
    # chuyến xe và kho chứng từ của xe). Thiếu hai prefix này thì menu hiện ra mà bấm vào là 403 – một
    # cánh cửa vẽ trên tường còn khó chịu hơn không có cửa.
    "gd_doi_xe": ("/api/v1/auth/", "/api/v1/fleet", "/api/v1/xe-hdv/", "/api/v1/dispatch",
                  "/api/v1/vehicles", "/api/v1/nap-du-lieu", "/api/v1/tep"),
    "nv_visa": ("/api/v1/auth/", "/api/v1/visa"),
    # Trưởng phòng Hướng dẫn: phần hướng dẫn, chào chuyến, bảng giá tuyến, tệp đính kèm và bộ nạp dữ
    # liệu của phòng. Không có /bookings, /tours, /payroll, /banks – ông chọn người cho chuyến, không
    # quản khách và không quản tiền công ty.
    "tp_hd": ("/api/v1/auth/", "/api/v1/huong-dan", "/api/v1/guide-assignments", "/api/v1/guide-rates",
              "/api/v1/incidents", "/api/v1/tep", "/api/v1/nap-du-lieu", "/api/v1/xe-hdv/"),
}


def check_restricted_scope(u: User, path: str) -> None:
    cho_phep = RESTRICTED_API_PREFIXES.get(u.role)
    if cho_phep is None: return
    if not any(path.startswith(p) for p in cho_phep):
        raise HTTPException(403, f"Vai trò {u.role} chỉ dùng được màn hình của mình, không truy cập được dữ liệu này")


# Ma trận công bố cho giao diện / tài liệu (vai trò → nhóm màn hình được xem)


PRODUCT_COST_KEYS = ("cost_structure", "cost_lines", "fixed_cost", "var_cost_per_pax", "cost_items")


def mask_product(out: dict, u: User) -> dict:
    """Kinh doanh / HCNS thấy sản phẩm, giá bán, chương trình – không thấy cơ cấu chi phí NCC."""
    if not can_see_cost(u):
        for k in PRODUCT_COST_KEYS: out[k] = None
    return out


# Menu giao diện web theo vai trò (đường dẫn trang → vai trò được thấy). Trang không liệt kê = mọi vai trò đã đăng nhập.
MENU_ROLES = {
    # Mỗi dòng = BASE_VIEW (Chủ tịch, TGĐ, Ban Kiểm soát) + đúng những vai trò có việc trên màn hình đó.
    # Viết thẳng tên vai trò thay vì cộng các nhóm lớn: nhóm lớn là thứ đã làm bảy vai trò tự động nhìn
    # thấy mọi màn hình mới mà không ai quyết định. Dài hơn, nhưng đọc là biết ai xem được gì.

    # --- Kinh doanh & sản phẩm ---
    "/products": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/tours": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/requests": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "cntt"),
    "/bookings": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/non-package": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    "/sales-reports": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "hcns", "cntt"),

    # --- Marketing & CSKH. Kế toán và CNTT KHÔNG có mặt: đây là dữ liệu khách của Marketing. ---
    "/inbox": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "cntt"),
    "/leads": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "cntt"),
    "/marketing": BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt"),   # chiến dịch: Marketing lập, Kế toán đối chiếu chi phí
    # Nội dung & thương hiệu là SỔ DUYỆT, không phải thư viện ảnh: hanh_chinh có mặt vì pháp chế nằm ở khối
    # đó và là người ký thứ hai cho nội dung có cam kết với khách hoặc có số liệu tài chính.
    "/noi-dung": BASE_VIEW + MARKETING + ("ptgd_mkt", "hanh_chinh", "cntt"),
    # Khiếu nại của KHÁCH. Mở cho cả Kinh doanh và Điều hành vì họ là người tiếp nhận và người xử lý;
    # Kế toán có mặt để đối chiếu chứng từ hoàn tiền gắn trên hồ sơ.
    "/khieu-nai": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "ptgd_doan", "ketoan", "cntt"),
    # Chăm sóc sau bán: phiếu tự sinh giao cho chính nhân viên đã bán, nên khối Kinh doanh phải mở được.
    "/cham-soc": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "ptgd_doan", "cntt"),

    # --- Điều hành ---
    "/ops": BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "hcns", "cntt"),
    "/visa": BASE_VIEW + OPERATIONS + VISA_STAFF + ("ptgd_doan", "ketoan", "hcns", "cntt"),

    # --- Vận tải & Hướng dẫn viên ---
    "/xe-hdv": BASE_VIEW + OPERATIONS + FIELD + ("hcns", "cntt"),
    # Ba màn hình dưới trước 07/9/2026 KHÔNG khai quyền, nên theo quy ước "trang không liệt kê = ai đăng
    # nhập cũng thấy", một nhân viên kinh doanh vẫn mở được hồ sơ xe và bảng giá vốn – lợi nhuận đội xe.
    "/doi-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("ketoan", "hcns", "cntt"),
    "/lenh-dieu-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("hcns", "cntt"),
    "/hieu-qua-doi-xe": BASE_VIEW + FLEET_MGR + ("tp_dh", "ketoan", "hcns"),
    # Lãi lỗ đội xe gồm lãi vay và chi phí cố định của cả đội – đây là kết quả kinh doanh của một trung
    # tâm lợi nhuận, không phải bảng theo dõi vận hành. Điều hành và HCNS không xem.
    "/lai-lo-doi-xe": BASE_VIEW + FLEET_MGR + ("ketoan", "cntt"),

    # --- Tài chính & Kế toán. Ba màn hình tiền thu về Kế toán; hai Phó TGĐ và CNTT không còn xem. ---
    "/collections": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    "/expenses": PAYMENT_REQUEST_ROLES,
    "/accounting": BASE_VIEW + ("ketoan", "tp_dh", "cntt"),
    "/finance": FINANCE_ROLES,
    "/bank-accounts": FINANCE_ROLES,
    # Sổ công nợ toàn hệ thống: phải thu của khách và phải trả nhà cung cấp là số tiền của cả công ty.
    # Nhân viên kinh doanh theo dõi booking của mình ở màn hình bán hàng, không mở sổ công nợ toàn công ty.
    "/cong-no": BASE_VIEW + ("ketoan", "ptgd_doan", "tp_dh", "cntt"),
    # Nhà cung cấp & đặt dịch vụ: Điều hành đặt dịch vụ, Kế toán xác nhận đổi tài khoản. Khối Kinh doanh
    # không xem – đây là cơ cấu chi phí nhà cung cấp.
    "/nha-cung-cap": BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    # Nạp dữ liệu: màn hình mở cho các phòng có dữ liệu để nạp, còn CHẶN THEO TỪNG BỘ NẠP nằm ở
    # app/services/intake.VAI_TRO – mở được trang không có nghĩa là nạp được sổ của phòng khác.
    "/nap-du-lieu": BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + ("ketoan", "hcns", "cntt",
                                                                              "nv_mkt"),
    # Tệp & hình ảnh: chứng từ đi kèm gần như mọi nghiệp vụ nên mở rộng; gỡ tệp thì hẹp hơn (xem API).
    "/tep": BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + ("ketoan", "hcns", "cntt", "nv_mkt",
                                                                      "nv_visa", "hanh_chinh"),
    # Phòng Hướng dẫn: màn hình riêng của người điều phối. KHÔNG mở /ops cho vai trò này – màn hình đó
    # lấy danh sách người từ /employees, tức là kèm luôn lương của mọi phòng.
    "/huong-dan": BASE_VIEW + OPERATIONS + GUIDE_MGR + ("ptgd_doan", "hcns", "ketoan", "cntt"),

    # Hợp đồng lao động: hồ sơ cá nhân của từng người, kèm bản scan trong nhóm 06_Nhan_su. HCNS giữ hồ
    # sơ, Ban TGĐ và Chủ tịch điều hành, Ban Kiểm soát rà soát. Kế toán KHÔNG xem – lương lấy từ bảng
    # lương, không cần đọc hợp đồng của từng người.
    "/hop-dong-lao-dong": BASE_VIEW + ("hcns", "cntt"),
    # Tài sản & mua sắm: nguyên giá, khấu hao và ghi sổ – việc của Kế toán. Hành chính xem để theo dõi
    # tài sản đang ở bộ phận nào.
    "/tai-san": BASE_VIEW + ("ketoan", "cntt", "hanh_chinh", "hcns"),

    # --- Hành chính & Nhân sự (tách quyền theo tab, xem HR_TAB_ROLES) ---
    "/hr": HR_TAB_ROLES["payroll"] + HR_TAB_ROLES["employees"] + HR_TAB_ROLES["incidents"],

    # --- Kiểm soát & Chính sách ---
    "/params": PARAM_ROLES,
    "/audit": AUDIT_ROLES,
    # Bàn làm việc của robot Kiểm soát. Trưởng phòng KHÔNG có mặt: đây là chỗ đọc kết quả giám sát
    # chính phòng mình, việc phải làm thì hiện ở màn hình Ngoại lệ của họ.
    "/kiem-soat": BASE_VIEW + ("cntt",),
    # Bảng quy ước hạch toán + cổng chặn giá vốn. Điều hành (tp_dh) xem được vì hàng đợi thiếu giá vốn
    # đứng tên phòng họ – bắt một phòng trả lời mà không cho họ nhìn thấy việc là cách chắc chắn để không ai trả lời.
    "/hach-toan": BASE_VIEW + ("ketoan", "cntt", "tp_dh"),
    # Ngoại lệ cần xử lý: nơi gom mọi lần một quy tắc bị bẻ. Mở cho những vai trò CÓ THỂ trả lời được
    # câu "vì sao lúc đó phải bẻ": Kế toán (tiền), Điều hành (chuyến), hai Phó TGĐ (duyệt), CNTT (tham số
    # và AI). Khối Kinh doanh không có mặt – họ là bên xin ngoại lệ, không phải bên rà.
    "/ngoai-le": BASE_VIEW + ("ketoan", "cntt", "tp_dh", "ptgd_doan", "ptgd_mkt"),

    # --- Điều hành Holdings & Hệ thống ---
    "/robot-reports": BASE_VIEW + ("ptgd_doan", "ptgd_mkt", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    "/companies": BASE_VIEW + ("ketoan", "tp_dh", "hcns", "hanh_chinh", "cntt"),
    "/vietrip": BASE_VIEW + ("tp_dh", "ketoan", "cntt"),
    # Màn hình quản trị tài khoản: HCNS và CNTT thao tác, Chủ tịch và TGĐ quyết, Ban Kiểm soát chỉ đọc.
    "/access": BASE_VIEW + ("hcns", "cntt"),
    # Vị trí AI & quyền hạn: Phó TGĐ Marketing có mặt vì kiêm chỉ đạo CNTT và là người chủ quản hộp thư
    # đa kênh – nơi AI tiếp xúc khách hàng.
    "/ai-roles": BASE_VIEW + ("ptgd_mkt", "cntt"),
}

MATRIX = {
    "tours": MENU_ROLES["/tours"],
    "bookings": BOOKING_ROLES,
    "cost": COST_ROLES,
    "finance": FINANCE_ROLES,
    "audit": AUDIT_ROLES,
    "params": PARAM_ROLES,
    "payment_requests": PAYMENT_REQUEST_ROLES,
    "payroll": HR_TAB_ROLES["payroll"],
}

# Mọi trang có trong giao diện – kể cả trang không đặt điều kiện vai trò – để dựng danh sách ẩn cho vai trò bị giới hạn.
ALL_MENU_PATHS = tuple(MENU_ROLES) + ("/", "/alerts", "/reports", "/payroll", "/doi-mat-khau")


# Vai trò bị giới hạn: chỉ được thấy đúng những trang liệt kê ở đây.
# Quy ước mặc định "trang không liệt kê trong MENU_ROLES = mọi người đăng nhập đều thấy" là an toàn với nhân
# viên văn phòng, nhưng SAI với tài xế, HDV và chuyên viên visa: nó cho họ thấy cả Bảng lương và Tài khoản
# ngân hàng chỉ vì hai trang đó chưa được liệt kê. Với các vai trò dưới đây, danh sách là DANH SÁCH CHO PHÉP.
RESTRICTED_ROLE_MENUS = {
    # Màn hình đổi mật khẩu có mặt ở cả hai danh sách: đây là danh sách CHO PHÉP, mà tài xế, HDV và chuyên
    # viên visa cũng phải đổi được mật khẩu tạm của mình – thiếu dòng này là họ bị khóa ngoài hệ thống.
    "xe_hdv": ("/xe-hdv", "/doi-mat-khau"),
    "nv_visa": ("/visa", "/doi-mat-khau"),
    "gd_doi_xe": ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe", "/lai-lo-doi-xe", "/xe-hdv",
                  "/nap-du-lieu", "/tep", "/doi-mat-khau"),
    "tp_hd": ("/huong-dan", "/xe-hdv", "/tep", "/nap-du-lieu", "/doi-mat-khau"),
}


def _grants(db, u: User) -> list:
    """Ngoại lệ còn hiệu lực của một người. db=None thì coi như không có – mọi chỗ gọi không có phiên
    cơ sở dữ liệu vẫn chạy đúng theo vai trò, chỉ là không thấy phần cấp lẻ."""
    if db is None: return []
    try:
        from sqlalchemy import select
        from app.models.core import UserGrant
        return [g for g in db.execute(select(UserGrant).where(UserGrant.user_id == u.id,
                                                              UserGrant.active == True)).scalars() if g.hieu_luc()]
    except Exception:      # noqa – bảng chưa có (cơ sở dữ liệu cũ) không được làm hỏng đăng nhập
        return []


def co_quyen(db, u: User, nang_luc: str) -> bool:
    """Năng lực cấp lẻ cho một người. Chủ tịch và TGĐ có sẵn mọi năng lực; Ban Kiểm soát ĐỌC được
    nhưng lớp chặn ghi chung vẫn giữ nguyên, nên ở đây không phải kể ra riêng."""
    if u.role in BASE_VIEW: return True
    return any(g.kind == "capability" and g.value == nang_luc for g in _grants(db, u))


def hr_tabs_for(db, u: User) -> list[str]:
    """Tab nào của màn hình Nhân sự người này mở được."""
    ra = []
    for tab, roles in HR_TAB_ROLES.items():
        cap = HR_TAB_CAPABILITY.get(tab)
        if u.role in roles or (cap and co_quyen(db, u, cap)): ra.append(tab)
    return ra


def menus_for(u: User, db=None) -> list[str]:
    ra = (list(RESTRICTED_ROLE_MENUS[u.role]) if u.role in RESTRICTED_ROLE_MENUS
          else [path for path, roles in MENU_ROLES.items() if u.role in roles])
    # Ngoại lệ cộng thêm cho CẢ vai trò bị giới hạn: nếu chỉ cộng ở một trong hai hàm thì danh sách hiện
    # và danh sách ẩn sẽ nói hai điều khác nhau về cùng một người.
    them = [g.value for g in _grants(db, u) if g.kind == "menu"]
    return ra + [p for p in them if p not in ra]


def hidden_menus_for(u: User, db=None) -> list[str]:
    if u.role in RESTRICTED_ROLE_MENUS:
        cho_phep = set(RESTRICTED_ROLE_MENUS[u.role]) | {g.value for g in _grants(db, u) if g.kind == "menu"}
        return [p for p in ALL_MENU_PATHS if p not in cho_phep]
    mo = set(menus_for(u, db))
    return [path for path in MENU_ROLES if path not in mo]
