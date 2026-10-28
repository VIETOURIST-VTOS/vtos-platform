# -*- coding: utf-8 -*-
"""Đơn khách sạn — ĐI THEO ĐÚNG CÁC BƯỚC AGODA GHI TRONG TÀI LIỆU DEMAND API.

Đọc trên developer.agoda.com ngày 29-10-2026. Sáu bước, và thứ nối chúng lại là một CHUỖI MÃ:

    Search        → trả `searchId` (sống 1 giờ), `blockId`, `rate.inclusive`, `surcharges[].id`
    Precheck      → mang cả bốn thứ trên sang; trả 200 / 501 đổi giá / 502-503 hết phòng
    Book          → mang cả bốn thứ trên + `tag` (số của MÌNH); trả `id` = mã đơn Agoda, `processing`
    Booking Detail→ tra bằng mã đơn; trả `status` và `hotelConfirmationNumber`
    Cancel preview→ tra bằng mã đơn; trả `reference` và `refundRate`
    Confirm cancel→ phải gửi lại ĐÚNG mã đơn + reference + refundRate.inclusive, lệch là lỗi 914

Mỗi mã trong chuỗi ấy là một CỘT ở đây. Thiếu một mã là đứt một bước, và chỗ đứt chỉ lộ ra lúc
khách đã trả tiền — nên chúng được ghi ngay từ bước đầu chứ không đợi.

HAI THỨ KHÔNG CÓ Ở ĐÂY, CỐ Ý:

  1. Không có ô nào nhận số thẻ. Mô hình đã chọn là Fulfill Assisted — «Agoda will directly
     charge your customers». Vietourist không thu tiền khách.
  2. KS-6 · Không có cột nào chép con số `totalPayment`. Tài liệu Book API nói thẳng: dùng
     `rate.inclusive`. Chép cả hai rồi có ngày ai đó cộng nhầm cột.

MỌI MÃ CỦA AGODA LÀ SỐ 64 BIT. Trang Content API nói rõ mọi định danh «must be stored and
processed using a 64-bit integer type», và `searchId` mẫu trong tài liệu là 633141408144250000 —
vượt 32 bit. Dùng Integer ở đây là một lỗi tràn số nằm chờ.
"""
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Sáu bước, đúng tên Agoda đặt. Giữ nguyên tên tiếng Anh ở vế phải để tra tài liệu không phải đoán.
BUOC_DON = {
    "tim": "Search",
    "soat_truoc": "Precheck",
    "dat": "Book",
    "tra_don": "Booking Detail",
    "xem_huy": "Cancel preview",
    "huy": "Confirm cancel",
}

# Đúng mười giá trị Agoda trả ở trường `status`. Không thêm, không bớt, không dịch: đây là chữ
# của họ, mình chỉ chép lại. Dịch ra tiếng Việt rồi đối chiếu là tự tạo ra một chỗ sai chính tả.
TRANG_THAI_NGUON = ("BookingReceived", "BookingCharged", "BookingConfirmed", "Departed",
                    "BookingRejected", "BookingCancelled", "BookingCancelledByCustomer",
                    "BookingTest", "TechnicalError", "AllotmentAlert")

# Đơn còn sống bên nguồn.
NGUON_SONG = ("BookingReceived", "BookingCharged", "BookingConfirmed", "Departed")
# Đơn đã chết bên nguồn.
NGUON_CHET = ("BookingRejected", "BookingCancelled", "BookingCancelledByCustomer", "TechnicalError")
# Đơn THỬ của Agoda. Có thật trong danh sách trả về, và không bao giờ được vào báo cáo tiền.
NGUON_THU = ("BookingTest",)

# Trạng thái của đơn BÊN MÌNH — khác trạng thái bên nguồn, vì hai bên có thể lệch nhau một lúc.
TRANG_THAI_DON = {
    "moi": "Mới dựng",
    "da_hoi_gia": "Đã hỏi giá",
    "cho_tra_cuu": "Quá hạn — phải tra bằng thẻ tham chiếu",
    "da_dat": "Đã đặt",
    "da_huy": "Đã huỷ",
    "that_bai": "Thất bại",
}

DON_DONG = ("da_huy", "that_bai")

# Mã lý do huỷ của Agoda, chép nguyên. Gửi số ngoài bảng này là một lỗi 400 lúc huỷ — tức là
# lúc khách đang chờ được huỷ, chỗ tệ nhất để phát hiện mình gõ sai một con số.
LY_DO_HUY = {
    0: "Không nêu lý do",
    13: "Khách tự đặt thẳng với khách sạn",
    14: "Buộc phải huỷ hoặc hoãn chuyến",
    15: "Chọn khách sạn khác ngoài Agoda",
    16: "Chọn khách sạn khác trên Agoda",
    17: "Tìm được giá rẻ hơn trên mạng",
    18: "Tìm được giá rẻ hơn qua đại lý địa phương",
    19: "Không ưng điều khoản thanh toán",
    20: "Không ưng điều khoản huỷ",
    22: "Lo ngại về độ tin cậy",
    23: "Lo ngại về an toàn",
    25: "Đơn xác nhận quá chậm",
    44: "Thiên tai",
}

# Kiểu thanh toán Agoda trả ở `paymentModel`.
KIEU_THANH_TOAN = {
    "agency": "Khách trả tại khách sạn",
    "merchant": "Trả trước",
    "merchantcommission": "Trả trước, hoa hồng",
}


class DonKhachSanOta(Base):
    """Một đơn phòng, mang đủ chuỗi mã của sáu bước."""

    __tablename__ = "don_khach_san_ota"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # ── thẻ tham chiếu CỦA MÌNH ────────────────────────────────────────────────────────────
    # Agoda gọi là `tag`. Đây là cột quan trọng nhất của cả bảng và lý do rất cụ thể: khi gọi
    # Book mà quá 120 giây không thấy trả lời, KHÔNG được gửi lại — tài liệu nói thẳng «should
    # not immediately resend the same booking request». Cách duy nhất biết Agoda đã nhận hay
    # chưa là tra Booking List bằng chính thẻ này. Không có thẻ thì không có cách nào biết, và
    # «đặt lại cho chắc» nghĩa là khách bị tính tiền hai lần.
    the_tham_chieu: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    ota_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ota.id"), index=True)
    # Môi trường ĐÓNG DẤU lúc dựng đơn, không đọc lại từ nguồn về sau. Nguồn đổi từ Sandbox sang
    # Chạy thật thì những đơn thử cũ vẫn phải là đơn thử.
    moi_truong: Mapped[str] = mapped_column(String(8), default="tat")

    trang_thai: Mapped[str] = mapped_column(String(16), default="moi", index=True)
    trang_thai_nguon: Mapped[str] = mapped_column(String(32), default="")

    # ── bước 1 · Search ────────────────────────────────────────────────────────────────────
    ma_tim: Mapped[int] = mapped_column(BigInteger, default=0)          # searchId
    tim_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ma_khoi: Mapped[str] = mapped_column(String(500), default="")       # blockId
    the_chao: Mapped[str] = mapped_column(String(500), default="")      # offerToken
    ma_khach_san: Mapped[int] = mapped_column(BigInteger, default=0)    # propertyId
    ma_phong: Mapped[int] = mapped_column(BigInteger, default=0)        # roomId
    ma_goi_gia: Mapped[int] = mapped_column(BigInteger, default=0)      # ratePlanId
    kieu_thanh_toan: Mapped[str] = mapped_column(String(20), default="")

    # ── điều kiện phải KHỚP y nguyên qua cả ba bước Search → Precheck → Book ────────────────
    ngay_nhan: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_tra: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_phong: Mapped[int] = mapped_column(Integer, default=1)
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=1)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    tuoi_tre_em: Mapped[str] = mapped_column(String(60), default="")
    nuoc_khach: Mapped[str] = mapped_column(String(2), default="")      # userCountry
    ngon_ngu: Mapped[str] = mapped_column(String(10), default="vi-vn")
    tien_te: Mapped[str] = mapped_column(String(3), default="VND")

    # Giá ĐÃ GỒM THUẾ, lấy ở `rate.inclusive`. Không chép `totalPayment`: tài liệu cấm dùng.
    gia_gom_thue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    phu_thu: Mapped[str] = mapped_column(Text, default="")              # surcharges, dạng JSON

    # ── bước 3 · Book ──────────────────────────────────────────────────────────────────────
    ma_don_nguon: Mapped[int] = mapped_column(BigInteger, default=0)    # bookingDetails.id
    ma_hanh_trinh: Mapped[int] = mapped_column(BigInteger, default=0)   # itineraryId
    dang_xu_ly: Mapped[bool] = mapped_column(Boolean, default=False)    # processing
    dat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── bước 4 · Booking Detail ────────────────────────────────────────────────────────────
    # Tài liệu bảo dò tới khi có số xác nhận khách sạn, muộn nhất tới 23:59:59 giờ địa phương
    # ngày nhận phòng; không có thì lùi về `supplierReference`, rồi mới tới mã đơn.
    so_xac_nhan_ks: Mapped[str] = mapped_column(String(64), default="")
    tham_chieu_nguon: Mapped[str] = mapped_column(String(64), default="")

    # ── bước 5-6 · Cancel ──────────────────────────────────────────────────────────────────
    tham_chieu_huy: Mapped[int] = mapped_column(Integer, default=0)     # cancellationSummary.reference
    ly_do_huy: Mapped[int] = mapped_column(Integer, default=0)
    hoan_gom_thue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    sua_boi: Mapped[str] = mapped_column(String(80), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BuocDonOta(Base):
    """Nhật ký từng bước. Một dòng cho mỗi lần gọi, kể cả lần quá hạn.

    Không có bảng này thì câu «Agoda đã nhận đơn chưa» không có chỗ nào trả lời được, và người
    trực đêm sẽ trả lời bằng cách bấm đặt lại.
    """

    __tablename__ = "buoc_don_ota"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_khach_san_ota.id"), index=True)
    buoc: Mapped[str] = mapped_column(String(16))
    luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ma_tra_ve: Mapped[int] = mapped_column(Integer, default=0)          # status / mã lỗi Agoda
    qua_han: Mapped[bool] = mapped_column(Boolean, default=False)
    tom_tat: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(80), default="")
