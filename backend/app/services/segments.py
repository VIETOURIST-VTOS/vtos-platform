"""Mảng kinh doanh: Kinh doanh Lẻ và Kinh doanh Đoàn (chỉ đạo 07/9/2026).

Hai phòng bán hai loại hàng khác nhau, nên mỗi phòng cần thấy đúng dữ liệu của mình. Vấn đề là "thuộc mảng
nào" hiện được ghi ở HAI chỗ và không chỗ nào là chân lý tuyệt đối:

  1. Trường `tour_type` – dữ liệu nghiệp vụ chính thức: doan_noi_dia / doan_nuoc_ngoai / le_noi_dia / le_nuoc_ngoai.
  2. Quy ước đặt mã của phòng Đoàn – mã tour bắt đầu bằng "MICE" (Chủ tịch, 07/9/2026).

Đo trên dữ liệu thật ngày 07/9/2026 trước khi viết dòng nào:
  - 115 tour có chữ MICE trong mã → cả 115 đều là doan_noi_dia, và cả 115 đều BẮT ĐẦU bằng MICE.
  - doan_noi_dia có 116 tour; đúng 1 tour không bắt đầu bằng MICE là DN-HCM-0820 (tour mẫu của bản demo).
  - doan_nuoc_ngoai: 0 tour.
Nói cách khác hai quy tắc hiện TRÙNG NHAU trên dữ liệu thật.

Vậy vì sao không chọn đại một cái? Vì chúng trùng nhau HÔM NAY, không có gì bảo đảm ngày mai vẫn trùng: chỉ
cần một người nhập tour MICE mà quên đặt loại chuyến là tour đó biến mất khỏi màn hình phòng Đoàn, và không
ai biết cho tới lúc đối chiếu doanh số cuối tháng. Nên ở đây lấy HỢP của hai quy tắc (không bỏ sót), và mở
thêm một đường đối chiếu chỉ đích danh những tour mà hai quy tắc bất đồng để Kinh doanh sửa dữ liệu gốc.
Hệ thống nói ra chỗ nó không chắc, thay vì im lặng chọn một bên.
"""
from sqlalchemy import or_, and_, select
from sqlalchemy.orm import Session
from app.models.core import Tour

MANG = {"le": "Kinh doanh Lẻ", "doan": "Kinh doanh Đoàn"}
DOAN_TYPES = ("doan_noi_dia", "doan_nuoc_ngoai")
LE_TYPES = ("le_noi_dia", "le_nuoc_ngoai")
MICE_PREFIX = "MICE"          # quy ước đặt mã của phòng Đoàn


def valid(mang: str) -> str:
    m = (mang or "").strip().lower()
    if m and m not in MANG:
        raise ValueError(f"Mảng không hợp lệ: {mang}. Chỉ nhận {', '.join(MANG)}")
    return m


def _is_doan():
    """Điều kiện SQL: tour thuộc mảng Đoàn theo BẤT KỲ quy tắc nào trong hai quy tắc."""
    return or_(Tour.tour_type.in_(DOAN_TYPES), Tour.code.ilike(f"{MICE_PREFIX}%"))


def tour_cond(mang: str):
    """Điều kiện lọc theo mảng, áp lên bảng tours. Trả None nếu không lọc.

    Mảng Lẻ = tour bán lẻ và KHÔNG thuộc mảng Đoàn. Dịch vụ lẻ (non_package) không nằm trong mảng nào ở đây:
    nó là loại hàng riêng, có màn hình riêng, và cả hai phòng đều có thể bán."""
    m = valid(mang)
    if not m:
        return None
    if m == "doan":
        return _is_doan()
    return and_(Tour.tour_type.in_(LE_TYPES), ~_is_doan())


def mang_of(tour: Tour) -> str:
    """Mảng của một tour, dùng để hiển thị. Cùng quy tắc với bộ lọc để hai nơi không nói khác nhau."""
    if not tour:
        return ""
    if tour.tour_type in DOAN_TYPES or (tour.code or "").upper().startswith(MICE_PREFIX):
        return "doan"
    if tour.tour_type in LE_TYPES:
        return "le"
    return ""                                        # dịch vụ lẻ (non_package) và các loại khác


def lech_quy_tac(db: Session, limit: int = 200) -> dict:
    """Những tour mà hai quy tắc bất đồng – cần Kinh doanh sửa dữ liệu gốc, hệ thống không tự đoán.

    Hai kiểu lệch, và mỗi kiểu có hậu quả khác nhau nên tách ra chứ không gộp một con số:
      - mã MICE nhưng loại chuyến ghi là lẻ  → báo cáo theo loại chuyến sẽ tính nhầm sang phòng Lẻ.
      - loại chuyến là đoàn nhưng mã không MICE → phòng Đoàn tìm theo mã sẽ không thấy tour của mình.
    """
    mice_ma_le = [t.code for t in db.execute(
        select(Tour).where(Tour.code.ilike(f"{MICE_PREFIX}%"), Tour.tour_type.in_(LE_TYPES))
        .limit(limit)).scalars()]
    doan_ma_khong_mice = [t.code for t in db.execute(
        select(Tour).where(Tour.tour_type.in_(DOAN_TYPES), ~Tour.code.ilike(f"{MICE_PREFIX}%"))
        .limit(limit)).scalars()]
    return {"ma_MICE_nhung_loai_chuyen_ghi_le": mice_ma_le,
            "loai_chuyen_doan_nhung_ma_khong_MICE": doan_ma_khong_mice,
            "tong_lech": len(mice_ma_le) + len(doan_ma_khong_mice),
            "ghi_chu": "Hệ thống lấy HỢP của hai quy tắc nên không bỏ sót tour nào khỏi màn hình phòng Đoàn. "
                       "Danh sách này để Kinh doanh sửa dữ liệu gốc cho hai quy tắc khớp lại, "
                       "không phải lỗi chặn nghiệp vụ."}
