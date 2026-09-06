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

ALL_SEEING = LEADERSHIP + CONTROL                       # xem mọi dữ liệu
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
    "/hr": ALL_SEEING + ("hcns", "tp_dh", "gd_kd"),
    "/ops": ALL_SEEING + OPERATIONS + ("hcns",),          # visa, HDV & phân chuyến, đội xe – nghiệp vụ của Điều hành

    "/inbox": ALL_SEEING + SALES + OPERATIONS + MARKETING,
    "/leads": ALL_SEEING + SALES + OPERATIONS + MARKETING,
    "/sales-reports": ALL_SEEING + SALES + OPERATIONS + ("hcns",),
    "/robot-reports": ALL_SEEING + ("tp_dh", "gd_kd", "hcns"),
    "/vietrip": ("cntt", "tgd", "chutich", "tp_dh", "ketoan"),
    "/audit": AUDIT_ROLES,
}


def menus_for(u: User) -> list[str]:
    return [path for path, roles in MENU_ROLES.items() if u.role in roles]


def hidden_menus_for(u: User) -> list[str]:
    return [path for path, roles in MENU_ROLES.items() if u.role not in roles]
