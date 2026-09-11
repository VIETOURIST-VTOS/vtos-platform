"""Pydantic schemas cho API v1."""
from datetime import date, datetime
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    role_name: str
    department: str
    hidden_menus: list[str] = []
    can_see_cost: bool = True
    read_only: bool = False


class TourCreate(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    name: str
    tour_type: str
    start_date: date
    end_date: date
    operator_id: int
    price_per_pax: float | None = None
    fixed_cost: float | None = None
    var_cost_per_pax: float | None = None
    planned_pax: int = 0
    rest_stops: str = ""
    company_id: int | None = None      # pháp nhân chủ quản; bỏ trống thì tour vào danh sách đối chiếu


class TourEdit(BaseModel):
    # V10 – phiên bản người gọi đang cầm. Để RỖNG = màn hình chưa gửi, máy chủ cho qua (xem
    # app/services/ghi_mot_lan.kiem_phien_ban). Gửi số lệch = từ chối kèm nội dung mới.
    phien_ban: int | None = None
    price_per_pax: float | None = None
    fixed_cost: float | None = None
    var_cost_per_pax: float | None = None
    planned_pax: int = 0
    rest_stops: str = ""
    justification: str = ""


class TourClose(BaseModel):
    actual_revenue: float | None = None
    actual_cost: float | None = None
    promo_value: float | None = None
    note: str = ""


class ActionNote(BaseModel):
    note: str = ""          # lời giải trình / ghi chú của bước (hiển thị ở Quy trình & Lịch sử)


class ProductIn(BaseModel):
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm
    code: str
    name: str
    tour_type: str = "le_noi_dia"
    departure_point: str = "TP HCM"
    region: str = ""
    country: str = ""
    sale_point: str = "TP HCM"
    transport: str = "Xe"
    vehicle_type: str = ""
    length_text: str = ""
    days: int = 1
    reference_price: float | None = None
    deposit_pct: float = 30
    days_to_close: int = 3
    requires_confirmation: bool = False
    cost_structure: dict = {}
    cost_lines: list = []
    program: str = ""
    services: str = ""
    status: str = "active"
    operator_id: int | None = None


class OpenTourIn(BaseModel):
    start_date: date
    seats: int = 0
    price_adl: float | None = None
    price_chd: float | None = None
    price_inf: float | None = None
    seats_promo: int = 0
    price_promo: float | None = None
    operator_id: int | None = None
    note: str = ""
    date_to: date | None = None          # có → mở theo lịch lặp
    weekdays: list[int] = []             # 0 = Thứ Hai … 6 = Chủ nhật


class D7Decision(BaseModel):
    decision: str  # ghep | doi | huy | chay
    note: str = ""


class RequestCreate(BaseModel):
    tour_id: int
    customer_name: str = ""
    customer_phone: str = ""
    source: str = ""
    care_note: str = ""
    pax: int = 1
    campaign_code: str = ""
    promo_code: str = ""
    discount: float | None = None


class BookingCustomerIn(BaseModel):
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm; rỗng = màn hình cũ, vẫn cho qua
    customer_name: str | None = None
    customer_phone: str | None = None
    care_note: str | None = None
    services_note: str | None = None
    adl: int | None = None
    chd: int | None = None
    inf: int | None = None


class BookingCancelIn(BaseModel):
    reason: str
    charge: float = 0            # phí hủy giữ lại (đ)
    retain: bool = True          # True: bảo lưu phần còn lại; False: đề nghị hoàn tiền
    expires_days: int | None = None


class GiaHanGiuChoIn(BaseModel):
    """VPM-7 – dời hạn giữ chỗ. Lý do là BẮT BUỘC: một chỗ giữ thêm là một chỗ không bán cho khách khác."""
    den: datetime
    ly_do: str


class RetentionApplyIn(BaseModel):
    booking_id: int
    amount: float | None = None  # mặc định: min(còn lại, còn phải thu)


class RetentionRefundIn(BaseModel):
    amount: float | None = None
    note: str = ""


class ParamPropose(BaseModel):
    key: str
    value: str
    effective_from: date
    source: str = ""


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
