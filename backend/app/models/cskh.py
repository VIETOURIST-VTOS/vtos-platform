"""Chăm sóc khách hàng – Đợt 3 (Phản hồi & khiếu nại) và Đợt 4 (Chăm sóc sau bán).

Vì sao khiếu nại của khách phải có bảng riêng chứ không dùng chung bảng "Sự vụ": sự vụ là hồ sơ kỷ luật
NỘI BỘ của một nhân viên, có thời hiệu và quy trình khiếu nại riêng theo nội quy lao động. Khiếu nại của
khách là quan hệ với người mua dịch vụ. Trộn hai thứ vào một bảng thì mọi câu hỏi "tháng này bao nhiêu
khách phàn nàn" sẽ lẫn cả số lần nhân viên bị lập biên bản. Hai đầu vẫn nối được với nhau bằng cột
`incident_id` – khi khiếu nại của khách xác định được lỗi thuộc về một người cụ thể.

Điều bảng này CỐ TÌNH không có: ô số tiền bồi thường. Chỉ ghi ĐỀ NGHỊ CỦA KHÁCH bằng nguyên văn. Số tiền
công ty thực trả sinh ra ở Đề nghị chi nhóm "hoan_tien" và đi đúng cấp duyệt theo ngưỡng hiện hành. Đặt
một ô số tiền ở đây là mở đường tiền thứ hai song song với cổng chi – hai đường sẽ lệch nhau, và con số
nào là thật thì không ai biết.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# ---------- Đợt 3: PHẢN HỒI & KHIẾU NẠI ----------
KN_NGUON = {"hop_thu": "Hộp thư đa kênh", "dien_thoai": "Điện thoại", "cham_soc": "Phiếu chăm sóc sau bán",
            "mang_xa_hoi": "Mạng xã hội", "truc_tiep": "Trực tiếp", "co_quan": "Cơ quan quản lý"}
KN_NHOM = {"chat_luong": "Chất lượng dịch vụ", "hdv": "Hướng dẫn viên", "xe": "Xe",
           "luu_tru": "Lưu trú", "an_uong": "Ăn uống", "tien": "Tiền – hoàn huỷ",
           "thai_do": "Thái độ nhân viên", "thong_tin_sai": "Thông tin sai", "khac": "Khác"}
# Nhóm vấn đề gắn với một chuyến cụ thể thì BẮT BUỘC chọn booking: không có chuyến thì không quy được
# trách nhiệm về hướng dẫn viên, xe hay nhà cung cấp nào, và hồ sơ chỉ còn là một lời than chung chung.
KN_NHOM_CAN_BOOKING = ("chat_luong", "hdv", "xe", "luu_tru", "an_uong")
KN_MUC = {1: "Mức 1 – góp ý", 2: "Mức 2 – khiếu nại có thiệt hại",
          3: "Mức 3 – nghiêm trọng (báo chí, cơ quan quản lý, đòi bồi thường lớn)"}
KN_TRANG_THAI = {"moi": "Mới", "dang_xu_ly": "Đang xử lý", "cho_khach": "Chờ khách xác nhận",
                 "da_dong": "Đã đóng", "tai_mo": "Tái mở"}
KN_NGUYEN_NHAN = {"do_ta": "Do ta", "do_ncc": "Do nhà cung cấp", "do_khach": "Do khách",
                  "bat_kha_khang": "Bất khả kháng"}
KN_HUONG = {"xin_loi": "Xin lỗi", "uu_dai": "Tặng ưu đãi lần sau", "hoan_mot_phan": "Hoàn tiền một phần",
            "hoan_toan_bo": "Hoàn tiền toàn bộ", "khong_boi_thuong": "Không bồi thường"}
KN_HUONG_CO_TIEN = ("hoan_mot_phan", "hoan_toan_bo")
KN_HAN_THAM_SO = {1: "kn_han_muc1_gio", 2: "kn_han_muc2_gio", 3: "kn_han_muc3_gio"}


class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)                 # KN2609-007
    source: Mapped[str] = mapped_column(String(20))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(30), default="", index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    nhom: Mapped[str] = mapped_column(String(20))
    level: Mapped[int] = mapped_column(Integer, default=1)
    noi_dung: Mapped[str] = mapped_column(Text)                                # NGUYÊN VĂN lời khách
    # Thay cho ô số tiền. Ghi nguyên văn khách yêu cầu gì: xin lỗi, đổi lịch, hoàn bao nhiêu…
    de_nghi_khach: Mapped[str] = mapped_column(Text, default="")
    received_by: Mapped[str] = mapped_column(String(50), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    handler: Mapped[str] = mapped_column(String(50), default="")               # người xử lý
    han_phan_hoi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nguyen_nhan_nhom: Mapped[str] = mapped_column(String(20), default="")
    nguyen_nhan: Mapped[str] = mapped_column(Text, default="")
    huong_xu_ly: Mapped[list] = mapped_column(JSON, default=list)
    # Chứng từ hoàn tiền. Cột này là SỐ HIỆU đề nghị chi, không phải số tiền – số tiền nằm ở chứng từ đó.
    payment_request_id: Mapped[int | None] = mapped_column(ForeignKey("payment_requests.id"), nullable=True)
    # Ba ô dưới dùng chuỗi "" / "co" / "khong" chứ không dùng kiểu luận lý: chưa hỏi khách và khách trả lời
    # "không" là hai việc khác nhau, mà một ô Có/Không thì không phân biệt được.
    khach_chap_nhan: Mapped[str] = mapped_column(String(6), default="")
    status: Mapped[str] = mapped_column(String(12), default="moi")
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    # Hai cột nối chéo (care_id ở đây và complaint_id ở phiếu chăm sóc) CỐ Ý không khai khoá ngoại:
    # khai cả hai chiều thì hai bảng tham chiếu vòng nhau, và lệnh tạo bảng sẽ bí ở bảng nào đi trước.
    care_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    closed_by: Mapped[str] = mapped_column(String(120), default="")            # mức 3: hai chữ ký, ngăn bởi dấu phẩy
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reopen_reason: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------- Đợt 4: CHĂM SÓC SAU BÁN ----------
CS_HINH_THUC = {"goi": "Gọi điện", "zalo": "Zalo", "email": "Email", "truc_tiep": "Gặp trực tiếp"}
CS_DIEM = {"hdv": "Hướng dẫn viên", "xe": "Xe", "khach_san": "Khách sạn", "an_uong": "Ăn uống",
           "lich_trinh": "Lịch trình", "dieu_hanh": "Điều hành", "gia": "Giá"}
CS_TRANG_THAI = {"moi": "Chưa liên hệ", "hen_lai": "Hẹn liên hệ lại", "xong": "Đã ghi kết quả",
                 "khong_lien_he_duoc": "Không liên hệ được"}


class CareTicket(Base):
    """Phiếu chăm sóc – MỖI BOOKING MỘT PHIẾU, hệ thống tự sinh khi tour kết thúc.

    Không có nút "thêm phiếu" nhập tay cho từng khách. Danh sách nhập tay sẽ đầy đủ trong hai tuần đầu
    rồi thưa dần và bỏ hẳn, còn phiếu tự sinh thì tồn tại kể cả khi không ai nhớ – và chính số phiếu chưa
    ai đụng tới mới là con số đo được việc chăm sóc có làm thật hay không.
    """
    __tablename__ = "care_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True, index=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    customer_phone: Mapped[str] = mapped_column(String(30), default="", index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    han_lien_he: Mapped[date] = mapped_column(Date)
    hinh_thuc: Mapped[str] = mapped_column(String(12), default="")
    lien_he_duoc: Mapped[str] = mapped_column(String(8), default="")           # "" / co / khong / hen_lai
    ly_do_khong: Mapped[str] = mapped_column(String(300), default="")
    hai_long: Mapped[int] = mapped_column(Integer, default=0)                  # 0 = chưa chấm, 1..5
    diem_chua_hai_long: Mapped[list] = mapped_column(JSON, default=list)
    nhu_cau_tiep: Mapped[str] = mapped_column(String(6), default="")           # "" / co / khong
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    complaint_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Chưa đồng ý thì tuyệt đối không đưa lời khách lên kênh truyền thông. Một ô Có/Không ở đây rẻ hơn
    # nhiều so với một lần phải gỡ bài và xin lỗi.
    dong_y_dung_danh_gia: Mapped[str] = mapped_column(String(6), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="moi")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
