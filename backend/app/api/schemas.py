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
    # Ô bắt buộc của dự toán ĐOÀN (Chủ tịch quyết 24/9/2026): "" chưa trả lời · "co" · "khong".
    # Mặc định là "" chứ không phải "khong": mặc định một câu trả lời là trả lời hộ người chưa hỏi.
    hoa_hong_khach: str = ""
    hoa_hong_khach_tien: float = 0


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
    # Xem chú thích ở TourCreate. Để RỖNG khi sửa nghĩa là "không đụng tới ô này", không phải
    # "xoá câu trả lời" — `tours.edit` chỉ gán khi giá trị gửi lên khác rỗng.
    hoa_hong_khach: str = ""
    hoa_hong_khach_tien: float = 0


class TourClose(BaseModel):
    actual_revenue: float | None = None
    actual_cost: float | None = None
    promo_value: float | None = None
    note: str = ""


class ActionNote(BaseModel):
    note: str = ""          # lời giải trình / ghi chú của bước (hiển thị ở Quy trình & Lịch sử)


class MoThemCho(BaseModel):
    """Mở thêm chỗ trên chuyến đang bán — Chủ tịch quyết 25/9/2026.

    `fixed_cost` để RỖNG nghĩa là chi phí cố định KHÔNG ĐỔI, không phải bằng 0. Mở 29 lên 45 chỗ
    mà vẫn dùng xe cũ thì đúng là không đổi; đổi xe to hơn thì gõ số mới, và cổng sẽ đo lại lợi
    nhuận trước khi cho qua.
    """
    so_cho: int
    fixed_cost: float | None = None
    ly_do: str = ""


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
