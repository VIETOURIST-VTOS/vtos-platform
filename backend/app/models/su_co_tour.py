"""Sự cố tour – V7 Đợt 3 (10/9/2026).

VÌ SAO CÓ BẢNG RIÊNG CHỨ KHÔNG DÙNG BẢNG `incidents`
----------------------------------------------------
`incidents` không phải "sự cố tour". Nó là **Sự vụ** – hồ sơ KỶ LUẬT NỘI BỘ của một nhân viên: mức 1–3,
chế tài trừ hoa hồng, HCNS xác nhận, cấp có thẩm quyền duyệt, người bị lập được khiếu nại trong 3 ngày.
Cột bắt buộc của nó là `employee_id`; `tour_id` chỉ là cột phụ có thể rỗng.

Sự cố tour là chuyện xảy ra VỚI MỘT CHUYẾN ĐANG CHẠY – xe hỏng giữa đèo, chuyến bay dời, khách sạn không
nhận phòng, khách ốm. Phần lớn sự cố KHÔNG có ai sai: thời tiết, bất khả kháng, lỗi nhà cung cấp. Ép nó
vào bảng kỷ luật nghĩa là mỗi lần trời mưa lại có một người bị ghi biên bản.

Đây đúng là lập luận đã dùng cho `complaints` (xem app/models/cskh.py): khiếu nại của khách tách khỏi sự
vụ nhân viên, nối lại bằng `incident_id` khi xác định được lỗi thuộc về một người cụ thể. Sự cố tour
theo đúng khuôn đó, và có thêm một chân nữa: `complaint_id`, vì một sự cố nặng thường kéo theo khiếu nại
của khách. Ba bảng, ba câu hỏi khác nhau, nối được với nhau mà không trộn vào nhau:

    su_co_tour ──incident_id──▶ incidents   (nếu lỗi thuộc về một người)
        │
        └──────complaint_id───▶ complaints  (nếu khách khiếu nại)

Trộn chung thì câu hỏi "quý này bao nhiêu chuyến gặp sự cố" trả về lẫn cả số lần nhân viên bị lập biên
bản, và câu "nhà cung cấp nào hay gây sự cố nhất" không trả lời được vì bảng kỷ luật không có cột NCC.

ĐIỀU BẢNG NÀY CỐ TÌNH KHÔNG CÓ: ô số tiền chi phí phát sinh
-----------------------------------------------------------
Sự cố thường đẻ ra chi phí – thuê xe thay, đổi vé, đặt phòng khác. Số tiền ấy đi qua ĐÚNG MỘT đường:
Đề nghị chi (payment_requests), qua đúng cấp duyệt theo ngưỡng. Bảng này chỉ giữ SỐ HIỆU chứng từ đó
(`payment_request_id`). Đặt một ô "chi phí phát sinh" ở đây là mở đường tiền thứ hai song song với cổng
chi: hai con số sẽ lệch nhau, và lúc quyết toán tour không ai biết con số nào là thật.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Nhóm sự cố. Phân theo THỨ HỎNG chứ không theo ai chịu trách nhiệm: lúc hướng dẫn viên gọi về báo thì
# chưa ai biết lỗi của bên nào, mà vẫn phải ghi được ngay. Quy trách nhiệm là cột `nguyen_nhan_nhom`,
# điền sau, khi đã rõ.
SC_NHOM = {
    "xe": "Xe & vận chuyển đường bộ",
    "hang_khong": "Hàng không / tàu / phà",
    "luu_tru": "Lưu trú",
    "an_uong": "Ăn uống",
    "diem_den": "Điểm tham quan & dịch vụ tại điểm",
    "hdv": "Hướng dẫn viên",
    "y_te": "Y tế & tai nạn",
    "giay_to": "Giấy tờ (hộ chiếu, visa, vé)",
    "thoi_tiet": "Thời tiết & bất khả kháng",
    "an_ninh": "An ninh, mất mát tài sản",
    "khach": "Từ phía khách",
    "khac": "Khác",
}

# Ba mức, và mức quyết định HẠN XỬ LÝ chứ không quyết định chế tài – khác hẳn ba mức của Sự vụ.
SC_MUC = {
    1: "Mức 1 – xử lý tại chỗ, lịch trình không đổi",
    2: "Mức 2 – lịch trình phải đổi hoặc phát sinh chi phí",
    3: "Mức 3 – khách mất chuyến, tai nạn, cấp cứu, an ninh",
}
# Hạn xử lý theo giờ. Mức càng nặng hạn càng NGẮN – ngược chiều với trực giác "mức cao thì thong thả
# hơn", nên viết rõ ra đây. Số giờ lấy từ tham số chính sách để Ban TGĐ đổi được mà không sửa phần mềm.
SC_HAN_THAM_SO = {1: "sc_han_muc1_gio", 2: "sc_han_muc2_gio", 3: "sc_han_muc3_gio"}
SC_HAN_MAC_DINH = {1: 24.0, 2: 8.0, 3: 2.0}

SC_TRANG_THAI = {
    "moi": "Mới báo",
    "dang_xu_ly": "Đang xử lý",
    "da_xu_ly": "Đã xử lý – chờ kết luận",
    "dong": "Đã đóng",
}
SC_CHUYEN = {"moi": ("dang_xu_ly",), "dang_xu_ly": ("da_xu_ly",), "da_xu_ly": ("dong", "dang_xu_ly"),
             "dong": ()}

# Cùng bộ từ vựng với khiếu nại khách (cskh.KN_NGUYEN_NHAN). Giống nhau là CỐ Ý: một sự cố và khiếu nại
# sinh ra từ nó phải quy về cùng một nguyên nhân, nếu không thì hai báo cáo nói hai chuyện khác nhau về
# cùng một chuyến.
SC_NGUYEN_NHAN = {"do_ta": "Do ta", "do_ncc": "Do nhà cung cấp", "do_khach": "Do khách",
                  "bat_kha_khang": "Bất khả kháng"}


class SuCoTour(Base):
    """Một sự cố của một chuyến đang chạy."""
    __tablename__ = "su_co_tour"
    __table_args__ = (Index("ix_su_co_tour_tour", "tour_id", "trang_thai"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)          # SC2609-001
    # BẮT BUỘC có chuyến. Sự cố không gắn chuyến thì không quy được về nhà cung cấp nào, không vào được
    # quyết toán chuyến nào, và không ai trả lời được "chuyến này đã gặp chuyện gì".
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    # Booking chỉ điền khi sự cố chạm tới một nhóm khách cụ thể (mất hành lý, khách ốm). Sự cố của cả
    # đoàn thì để rỗng – điền bừa một booking làm báo cáo theo khách sai lệch.
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    nhom: Mapped[str] = mapped_column(String(20))
    muc: Mapped[int] = mapped_column(Integer, default=1)
    xay_ra_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    noi_xay_ra: Mapped[str] = mapped_column(String(160), default="")
    so_khach_anh_huong: Mapped[int] = mapped_column(Integer, default=0)
    # Nguyên văn lời người ở hiện trường. Tóm tắt lại theo ý người trực là mất chứng cứ – y như quy ước
    # của hồ sơ khiếu nại khách.
    mo_ta: Mapped[str] = mapped_column(Text)
    nguoi_bao: Mapped[str] = mapped_column(String(120), default="")     # tên người gọi về (HDV, tài xế, khách)
    nguoi_bao_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)

    trang_thai: Mapped[str] = mapped_column(String(12), default="moi", index=True)
    han_xu_ly: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Lúc có người NHẬN việc, không phải lúc xong. Đo được "bao lâu thì có người cầm" là đo được thứ
    # quyết định trải nghiệm của khách đang đứng ngoài đường.
    nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nguoi_xu_ly: Mapped[str] = mapped_column(String(50), default="")
    huong_xu_ly: Mapped[str] = mapped_column(Text, default="")
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    nguyen_nhan_nhom: Mapped[str] = mapped_column(String(20), default="")
    nguyen_nhan: Mapped[str] = mapped_column(Text, default="")

    # Ba chân nối ra ngoài. Cả ba đều RỖNG cho tới khi có căn cứ – rỗng là "chưa xác định", không phải
    # "không có".
    payment_request_id: Mapped[int | None] = mapped_column(ForeignKey("payment_requests.id"), nullable=True)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)

    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    closed_by: Mapped[str] = mapped_column(String(50), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SuCoTourXuLy(Base):
    """Từng bước xử lý, ghi theo thời gian.

    Vì sao không gộp vào một ô ghi chú dài trên bảng chính: sự cố mức 3 kéo nhiều giờ và qua nhiều người
    – tài xế báo, điều hành gọi xe thay, kế toán ứng tiền. Một ô văn bản thì người sau ghi đè lên người
    trước, và lúc rà lại không biết ai làm gì lúc mấy giờ. Dòng thời gian là thứ duy nhất trả lời được
    câu "khách phải chờ bao lâu, và trong lúc đó ta đã làm gì".
    """
    __tablename__ = "su_co_tour_xu_ly"

    id: Mapped[int] = mapped_column(primary_key=True)
    su_co_id: Mapped[int] = mapped_column(ForeignKey("su_co_tour.id"), index=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    nguoi: Mapped[str] = mapped_column(String(50), default="")
    noi_dung: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
