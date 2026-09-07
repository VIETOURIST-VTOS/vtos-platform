"""Ma trận nhìn thấy dữ liệu theo vai trò (rà phân quyền tuần 3).

Nguyên tắc (Mô hình quản trị 27/8/2026 + Thiết kế v1.7 mục 6):
- Lãnh đạo (Chủ tịch, TGĐ, hai Phó TGĐ), Kế toán, CNTT, Ban Kiểm soát: xem toàn bộ.
- Điều hành (TP/NV): xem tour, booking, chi phí, quyết toán, dòng tiền tour.
- Kinh doanh: NV chỉ thấy booking/yêu cầu/dịch vụ lẻ/phiếu thu do mình phụ trách; GĐ KD thấy toàn bộ khối
  kinh doanh; KHÔNG xem cơ cấu chi phí NCC, quyết toán, giao dịch ngân hàng.
- HCNS: nhân sự, lương, báo cáo ngày, sự vụ; không xem chi phí tour / ngân hàng.
- Ban Kiểm soát: chỉ đọc – mọi thao tác ghi bị chặn (trừ đổi mật khẩu).
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
VISA_STAFF = ("nv_visa",)                               # chuyên viên visa: chỉ phân hệ Visa
ADMIN_STAFF = ("hanh_chinh",)                           # bảo vệ, pháp chế, quan hệ nhà đầu tư: thuộc HCNS
                                                        # nhưng KHÔNG xem bảng lương (chỉ đạo 07/9/2026)

ALL_SEEING = LEADERSHIP + CONTROL                       # xem mọi dữ liệu

# Chỉ đạo 07/9/2026: nhóm "xem tất cả" thu về ĐÚNG hai người, Ban Kiểm soát đọc tất cả nhưng không ghi được;
# các vai trò khác xem theo phạm vi công việc. Đợt này mới áp cho ba màn hình đội xe vừa khai quyền – phần
# còn lại của ma trận chuyển sang BASE_VIEW ở đợt sau, làm một lần kèm thông báo cho từng phòng, vì đổi cả
# ma trận cùng lúc là lấy mất màn hình quen tay của nhiều người mà không ai được báo trước.
FULL_VIEW = ("chutich", "tgd")                          # toàn quyền xem
READ_ALL = ("bks",)                                     # đọc tất cả, bị chặn mọi thao tác ghi
BASE_VIEW = FULL_VIEW + READ_ALL

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
COST_ROLES = ALL_SEEING + OPERATIONS                    # cơ cấu chi phí NCC, quyết toán, dòng tiền tour
FINANCE_ROLES = ALL_SEEING + ("tp_dh",)                 # giao dịch ngân hàng, tổng hợp thu tiền toàn công ty
AUDIT_ROLES = LEADERSHIP + CONTROL                      # nhật ký kiểm toán
PARAM_ROLES = ALL_SEEING + ("tp_dh", "gd_kd", "hcns")   # bảng tham số chính sách
BOOKING_ROLES = ALL_SEEING + OPERATIONS + SALES         # booking, yêu cầu đặt dịch vụ, bảo lưu (xem)
REQUEST_CREATE_ROLES = OPERATIONS + SALES               # được GỬI yêu cầu đặt dịch vụ: Điều hành + toàn khối Kinh doanh
                                                        # (nguồn duy nhất – máy chủ và giao diện dùng chung, tránh lệch vai trò)
PAYMENT_REQUEST_ROLES = ALL_SEEING + OPERATIONS + ("gd_kd", "ptgd_mkt", "hcns")   # đề nghị chi / lệnh chi
READ_ONLY_ROLES = ("bks",)
WRITE_ALLOWED_FOR_READ_ONLY = ("/api/v1/auth/password", "/api/v1/auth/login", "/api/v1/robot/r9")   # BKS được chạy robot giám sát R9 (chỉ sinh cảnh báo)


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
    "xe_hdv": ("/api/v1/auth/", "/api/v1/xe-hdv/"),
    # GĐ điều hành đội xe: cả phân hệ đội xe và lệnh điều xe, cộng danh mục xe để chọn trong form. Không có
    # /tours, /bookings, /banks, /payroll – phạm vi công việc của ông là chiếc xe, không phải khách hàng và
    # dòng tiền công ty.
    "gd_doi_xe": ("/api/v1/auth/", "/api/v1/fleet", "/api/v1/xe-hdv/", "/api/v1/dispatch",
                  "/api/v1/vehicles"),
    "nv_visa": ("/api/v1/auth/", "/api/v1/visa"),
}


def check_restricted_scope(u: User, path: str) -> None:
    cho_phep = RESTRICTED_API_PREFIXES.get(u.role)
    if cho_phep is None: return
    if not any(path.startswith(p) for p in cho_phep):
        raise HTTPException(403, f"Vai trò {u.role} chỉ dùng được màn hình của mình, không truy cập được dữ liệu này")


# Ma trận công bố cho giao diện / tài liệu (vai trò → nhóm màn hình được xem)
MATRIX = {
    "tours": BOOKING_ROLES + ("hcns",),
    "bookings": BOOKING_ROLES,
    "cost": COST_ROLES,
    "finance": FINANCE_ROLES,
    "audit": AUDIT_ROLES,
    "params": PARAM_ROLES,
    "payment_requests": PAYMENT_REQUEST_ROLES,
}


PRODUCT_COST_KEYS = ("cost_structure", "cost_lines", "fixed_cost", "var_cost_per_pax", "cost_items")


def mask_product(out: dict, u: User) -> dict:
    """Kinh doanh / HCNS thấy sản phẩm, giá bán, chương trình – không thấy cơ cấu chi phí NCC."""
    if not can_see_cost(u):
        for k in PRODUCT_COST_KEYS: out[k] = None
    return out


# Menu giao diện web theo vai trò (đường dẫn trang → vai trò được thấy). Trang không liệt kê = mọi vai trò đã đăng nhập.
MENU_ROLES = {
    "/products": BOOKING_ROLES + ("hcns",),
    "/tours": BOOKING_ROLES + ("hcns",),
    "/requests": BOOKING_ROLES,
    "/bookings": BOOKING_ROLES,
    "/non-package": BOOKING_ROLES,
    "/collections": BOOKING_ROLES,
    "/expenses": PAYMENT_REQUEST_ROLES,
    "/accounting": ALL_SEEING + ("tp_dh",),
    "/finance": LEADERSHIP + CONTROL,
    "/params": PARAM_ROLES,
    "/hr": HR_TAB_ROLES["payroll"] + HR_TAB_ROLES["employees"] + HR_TAB_ROLES["incidents"],
    "/ops": ALL_SEEING + OPERATIONS + ("hcns",),          # visa, HDV & phân chuyến, đội xe – nghiệp vụ của Điều hành

    "/inbox": ALL_SEEING + SALES + OPERATIONS + MARKETING,
    "/leads": ALL_SEEING + SALES + OPERATIONS + MARKETING,
    "/sales-reports": ALL_SEEING + SALES + OPERATIONS + ("hcns",),
    "/robot-reports": ALL_SEEING + ("tp_dh", "gd_kd", "hcns"),
    "/vietrip": ("cntt", "tgd", "chutich", "tp_dh", "ketoan"),
    "/audit": AUDIT_ROLES,
    "/companies": ALL_SEEING + ("tp_dh", "hcns"),   # danh mục pháp nhân và đối chiếu công ty chủ quản
    "/xe-hdv": ALL_SEEING + OPERATIONS + FIELD + ("hcns",),   # xe Vietrip & HDV – màn hình duy nhất của vai trò xe_hdv
    "/visa": ALL_SEEING + OPERATIONS + VISA_STAFF + ("hcns",),
    # Trang này trước đây không liệt kê, nghĩa là ai đăng nhập cũng thấy – trong khi nó là sổ tiền gửi và
    # danh sách tài khoản ngân hàng của công ty. (/payroll chỉ là lối chuyển hướng sang /hr nên không liệt kê.)
    "/bank-accounts": ALL_SEEING,

    # Ba màn hình đội xe (chỉ đạo 07/9/2026). Cùng một lỗi với /bank-accounts ở trên: chưa liệt kê thì theo
    # quy ước "trang không liệt kê = mọi người đăng nhập đều thấy", nên tới hôm nay một nhân viên kinh doanh
    # vẫn mở được hồ sơ xe, lệnh điều xe và bảng giá vốn – lợi nhuận đội xe. Khai quyền theo bảng phân quyền
    # anh Tuấn duyệt ngày 07/9: giá vốn và hiệu quả chỉ dành cho người phải chịu trách nhiệm về con số đó.
    "/doi-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("ketoan", "hcns", "cntt"),
    "/lenh-dieu-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("hcns", "cntt"),
    "/hieu-qua-doi-xe": BASE_VIEW + FLEET_MGR + ("tp_dh", "ketoan", "hcns"),
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
    "gd_doi_xe": ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe", "/xe-hdv", "/doi-mat-khau"),
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
