"""Quyết toán tour theo điều hành – nguồn số lớn nhất của công ty.

495 chuyến trong hai tháng 7–8/2026 với 48.042.594.678 đ doanh thu. Trước bản này số đó vào VTOS bằng
đồng bộ Vietrip hoặc gõ tay.

Vì sao KHÔNG ghi thẳng vào bảng tours mà để một bảng riêng:

    Cột giá vốn ở bảng tours là Float mặc định 0 – nó không có cách nào nói "chưa có số". Mà đúng chỗ
    đó là chỗ hỏng: trong hai tệp thật có 76 dòng doanh thu 2.654.940.111 đ mà giá vốn để 0. Ghi thẳng
    vào một cột không phân biệt được "0 đồng" với "chưa ai điền" là sổ báo lãi 100% trên 2,65 tỷ, và
    bảng vẫn cân nên không ai nhìn ra.

    Ở bảng này gia_von để NULL được. Rỗng là rỗng. Ô 0 trong tệp nguồn cũng đọc thành rỗng, vì theo chỉ
    đạo 08/9 của Chủ tịch mọi đơn đều có giá vốn – "giá vốn bằng 0" không phải một bản chất nghiệp vụ,
    nó là ô chưa ai điền.

Và vì sao có cột phan_loai: 60 trong 76 dòng ấy là khách lẻ – bảo lưu do hủy tour, gia hạn visa, vé.
Xếp tất cả vào một hàng đợi "thiếu giá vốn" thì hàng đợi lúc nào cũng đầy những dòng không ai sửa
được, và người ta thôi mở nó – đúng kiểu một bộ kiểm báo oan 26 việc thì không ai đọc lần thứ hai.
Máy KHÔNG tự đoán dòng nào là bảo lưu; nó tách riêng và chờ người phân loại.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

LOAI_DON = {"tour": "Tour đoàn / tour ghép", "khach_le": "Khách lẻ do sale tự xử lý"}

TRANG_THAI_QT = {"da_qt": "Đã quyết toán", "du_toan": "Dự toán (chưa QT)"}

# Phân loại do NGƯỜI đặt cho dòng có doanh thu mà chưa có giá vốn. Mặc định là chưa phân loại: máy đọc
# tệp không biết một khoản 93 triệu là doanh thu khách lẻ hay là vé công tác của ban lãnh đạo.
PHAN_LOAI = {
    "": "Chưa phân loại",
    "cho_gia_von": "Chờ Điều hành nhập giá vốn",
    "bao_luu_huy_tour": "Bảo lưu do hủy tour – giá vốn chưa phát sinh",
    "chi_phi_noi_bo": "Không phải doanh thu – chi phí nội bộ, ghi nhầm vào đơn",
    "khong_phat_sinh_gia_von": "Dịch vụ không phát sinh giá vốn (đã xác nhận)",
}


class TourSettlement(Base):
    __tablename__ = "tour_settlements"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    __table_args__ = (
        Index("ux_tour_settlements_ma", "ma_tour", unique=True),
        Index("ix_tour_settlements_ky", "ky"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7))                        # kỳ tour KẾT THÚC, YYYY-MM
    ma_tour: Mapped[str] = mapped_column(String(60))
    # Khoá nối vào chuyến thật trong VTOS. Thêm 10/9/2026 theo chốt của Chủ tịch: bảng này là CỬA
    # NẠP, không phải nguồn sự thật thứ hai. Trước đó nó khớp với tours bằng CHUỖI ma_tour – chuỗi
    # thì sai chính tả được, thừa dấu cách được, và không có gì bắt lỗi.
    #
    # NULL nghĩa là chưa tra ra chuyến thật, KHÁC HẲN "không có chuyến". Tệp Điều hành vẫn nạp được
    # khi chưa tra ra; việc tra là một bước riêng, xem app/services/noi_quyet_toan.py.
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    ten_tour: Mapped[str] = mapped_column(String(300), default="")
    loai: Mapped[str] = mapped_column(String(20), default="tour")
    # Điều hành viên giữ NGUYÊN VĂN tên trong tệp, và operator_id khi tra ra người thật. Không bao giờ
    # điền tên tài khoản đã nạp tệp vào đây – người nạp không phải người chịu trách nhiệm về chuyến.
    dieu_hanh: Mapped[str] = mapped_column(String(120), default="")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sale: Mapped[str] = mapped_column(String(120), default="")
    ngay_kh: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_kt: Mapped[date | None] = mapped_column(Date, nullable=True)
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # NULL nghĩa là CHƯA CÓ SỐ. Đây là lý do tồn tại của cả bảng này.
    gia_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    trang_thai_qt: Mapped[str] = mapped_column(String(20), default="du_toan")
    phan_loai: Mapped[str] = mapped_column(String(30), default="")
    phan_loai_boi: Mapped[str] = mapped_column(String(50), default="")
    phan_loai_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    han_bao_luu: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # ---- Lớp 1, phần đầu tệp quyết toán: những ô nằm trên bảng khách trong tệp Điều hành ----
    # Tên chương trình ("NHA TRANG", "PHAN THIẾT – ĐÀ LẠT") tách khỏi ten_tour vì ten_tour trong tệp
    # thường là cả câu tiêu đề ("QUYẾT TOÁN TOUR NHA TRANG 10/07/2026"), không lọc được để nhóm.
    ten_chuong_trinh: Mapped[str] = mapped_column(String(200), default="")
    so_khach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hdv: Mapped[str] = mapped_column(String(120), default="")
    bien_so_xe: Mapped[str] = mapped_column(String(30), default="")
    # Giá bán NIÊM YẾT của chương trình. Không phải doanh thu chia đầu khách: trong một chuyến có nhiều
    # mức giá (người lớn 1.790.000, trẻ em 1.500.000, khách huỷ charge 895.000). Máy lấy mức PHỔ BIẾN
    # nhất và bật cờ nhieu_muc_gia; nó không tự bình quân, vì bình quân che mất chuyện có bao nhiêu mức.
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nhieu_muc_gia: Mapped[bool] = mapped_column(Integer, default=0, server_default="0")
    # Chênh giữa lớp 1 và tổng lớp 2. GHI LẠI, không sửa số nào cả – vị thế đã chốt: số tổng là số
    # chốt, lớp chi tiết chỉ là lớp dưới, và chỗ hai lớp không khớp là chỗ phải có người nhìn.
    chenh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chenh_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguon: Mapped[str] = mapped_column(String(30), default="nap_tep")
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def loi_nhuan(self):
        """Chưa có giá vốn thì KHÔNG có lợi nhuận – trả None, không trả doanh thu."""
        return None if self.gia_von is None else (self.doanh_thu or 0) - (self.gia_von or 0)


# ---------------------------------------------------------------------------------------------
# LỚP 2 – từng khách trong một bản quyết toán
# ---------------------------------------------------------------------------------------------
# Lớp 1 trả lời "chuyến này lãi bao nhiêu". Lớp 2 trả lời "lãi ấy đến từ đâu, và ai trả bao nhiêu".
# Hai lớp phải cộng khớp nhau; chỗ không khớp được GHI LẠI ở chenh_thu / chenh_chi chứ không san bằng.

class TourSettlementLine(Base):
    """Một dòng khách trong bảng QT của tệp Điều hành.

    Vì sao KHÔNG dựng cột cứng cho từng khoản chi:

        Tour lẻ chia chi phí thành LAND, BH, PHÍ TL, NƯỚC SUỐI, PHÍ KHÁC. Đoàn MICE chia thành LAND
        UK, VMB XUẤT LẺ, TIỄN SÂN BAY, VISA UK, PHÍ KHÁCH CHI TIỀN MẶT, CTP HDV + TIPPING. Không có
        tập cột nào phủ được cả hai, và mỗi lần Điều hành thêm một khoản là một lần phải sửa bảng.
        Dựng cột cứng thì hoặc bảng đầy cột rỗng, hoặc khoản mới bị dồn hết vào "phí khác" – và
        "phí khác" phình to là cách nhanh nhất để mất dấu chi phí.

    Nên các khoản chi nằm ở bảng con TourSettlementCost, mỗi khoản một dòng, giữ NGUYÊN VĂN nhãn
    trong tệp. tong_chi ở đây là số tệp GHI, không phải số máy cộng lại – hai số ấy phải bằng nhau,
    và nếu lệch thì đó là phát hiện, không phải chuyện để máy tự chọn bên nào.
    """
    __tablename__ = "tour_settlement_lines"
    __table_args__ = (Index("ix_tsl_settlement", "settlement_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("tour_settlements.id", ondelete="CASCADE"))
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales: Mapped[str] = mapped_column(String(120), default="")
    # Dữ liệu cá nhân theo Nghị định 13/2023. Chủ tịch chốt 10/9/2026: ai xem được lớp 1 thì xem được
    # lớp 2. Quyền không hẹp hơn, nhưng mỗi lần mở lớp 2 đều ghi nhật ký – để trả lời được câu
    # "ai đã đọc danh sách khách" khi có người hỏi, mà không chặn ai cả.
    ten_khach: Mapped[str] = mapped_column(String(200), default="")
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thu_khac: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    loi_nhuan_tep: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Cờ do bộ đọc đặt khi phép cộng trong chính dòng ấy không khớp. Giữ nguyên số của tệp.
    co_lech: Mapped[str] = mapped_column(Text, default="")

    def lech_thu(self):
        """Tổng thu tệp ghi có bằng giá bán cộng thu khác không? None nghĩa là thiếu số để so."""
        if self.tong_thu is None or self.gia_ban is None:
            return None
        return self.tong_thu - (self.gia_ban + (self.thu_khac or 0))  # k2-doc-an-toan: đã chặn None ngay trên


class TourSettlementCost(Base):
    """Một khoản chi của MỘT dòng khách. Nhãn giữ nguyên văn tệp; mã khoản do người ánh xạ.

    ma_khoan rỗng nghĩa là CHƯA AI XẾP MÃ cho nhãn ấy – không phải "khoản khác". Máy không tự đoán
    "PHÍ TL" là phí tham quan hay phí thủ tục; nó để trống và đẩy nhãn lạ vào một hàng đợi ngắn cho
    người xếp một lần, rồi mọi tệp sau đó dùng lại. Đoán bừa một lần là sai vĩnh viễn ở mọi báo cáo
    cộng theo khoản, và không ai nhìn ra vì tổng vẫn cân.
    """
    __tablename__ = "tour_settlement_costs"
    __table_args__ = (Index("ix_tsc_line", "line_id"), Index("ix_tsc_ma", "ma_khoan"))
    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("tour_settlement_lines.id", ondelete="CASCADE"))
    ma_khoan: Mapped[str] = mapped_column(String(30), default="")
    nhan: Mapped[str] = mapped_column(String(120), default="")
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)


# Từ điển ánh xạ nhãn cột chi trong tệp sang mã khoản. Chỉ chứa những nhãn ĐÃ được xác nhận nghĩa;
# nhãn chưa có ở đây thì vào hàng đợi chờ người xếp, KHÔNG rơi vào một mã mặc định nào.
MA_KHOAN = {
    "LAND": "land", "LAND TOUR": "land",
    "BH": "bao_hiem", "BAO HIEM": "bao_hiem",
    "NUOC SUOI": "nuoc", "NUOC": "nuoc",
    "VMB": "ve_may_bay", "VMB XUAT LE": "ve_may_bay", "VE MAY BAY": "ve_may_bay",
    "VISA": "visa",
    "TIEN SAN BAY": "tien_san_bay",
    "PHI KHAC": "phi_khac",
}
# CỐ Ý KHÔNG có "PHI TL" trong từ điển trên, dù nó là nhãn xuất hiện ở mọi tệp tour lẻ.
#
# Bản nháp đầu ngày 10/9 xếp "PHI TL" -> phi_tham_quan, vì đọc tắt là "phí tham quan". Đối chiếu với
# sheet CTT của chính tệp Nha Trang 10/07/2026 thì sai: cột PHÍ TL cộng lại đúng 1.500.000 đ, mà
# trong chiết tính 1.500.000 đ ấy là HDV 1.200.000 + ăn nội bộ 300.000. Phí tham quan thật (Tháp Bà,
# 1.200.000 đ) nằm TRONG khối LAND, không nằm ở cột này.
#
# Xếp nhầm một nhãn thì mọi báo cáo cộng theo khoản đều sai, tổng vẫn cân nên không ai nhìn ra, và
# sai vĩnh viễn vì về sau không còn ai nhớ nhãn gốc là gì. Nên nhãn nào chưa xác nhận nghĩa thì để
# TRỐNG mã và vào hàng đợi chờ người xếp – một lần, rồi mọi tệp sau dùng lại.

TEN_KHOAN = {
    "land": "Land tour", "bao_hiem": "Bảo hiểm", "phi_tham_quan": "Phí tham quan",
    "nuoc": "Nước uống", "ve_may_bay": "Vé máy bay", "visa": "Visa",
    "tien_san_bay": "Tiễn sân bay", "ctp_hdv": "Chi trên tour / HDV", "phi_khac": "Phí khác",
    "": "Chưa xếp mã – chờ người ánh xạ",
}


# ---------------------------------------------------------------------------------------------
# LỚP 2, MẶT THỨ HAI – CHIẾT TÍNH (sheet CTT). Đây là mặt giàu chứng từ nhất, và là mặt VTOS
# đang thiếu hẳn.
# ---------------------------------------------------------------------------------------------

class TourSettlementCostLine(Base):
    """Một dòng chiết tính: chi cho ai, bao nhiêu, chứng từ nào, mã số thuế nào.

    Vì sao mặt này quan trọng hơn cột chi ở sheet QT:

        Cột chi trong sheet QT chỉ là PHÂN BỔ của chiết tính xuống đầu khách. Đo trên tệp Nha Trang
        10/07/2026: cột LAND chỉ có đúng hai giá trị – 1.343.030 cho 33 người lớn và 570.000 cho 7
        trẻ em. Nó không mang thêm thông tin nào ngoài phép chia. Còn sheet CTT mang tên đối tác, số
        hoá đơn và mã số thuế: 13 dòng có số chứng từ, 6 dòng có MST (Đồng Tiến 4201910983, Marina
        Beach 4202041278, Ô Vương 4500645645, Tháp Bà 4200330404, bảo hiểm 0304422444-021).

        Đó chính là bảng kê thuế GTGT đầu vào. Dựng lớp 2 chỉ từ sheet QT là bỏ mất toàn bộ lớp
        chứng từ, và sau đó không cách nào đối chiếu tour với tờ khai thuế được nữa.

    Phép tính bắt buộc: thành tiền = đơn giá × số lượng × hệ số. Đo trên tệp thật đúng 20/20 dòng.
    Cột "DIỄN GIẢI" trong tệp chính là hệ số (số đêm lưu trú, số bữa ăn) – tên cột không nói ra điều
    đó, nên bộ đọc phải kiểm bằng phép nhân chứ không tin tên cột.
    """
    __tablename__ = "tour_settlement_cost_lines"
    __table_args__ = (Index("ix_tscl_settlement", "settlement_id"),
                      Index("ix_tscl_mst", "mst_ncc"))
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("tour_settlements.id", ondelete="CASCADE"))
    # "thu" cho khối I/GIÁ TOUR, "chi" cho khối II/CHI PHÍ. Một tệp có cả hai, và cộng nhầm hai khối
    # vào nhau là ra một con số không có nghĩa gì cả.
    ve: Mapped[str] = mapped_column(String(10), default="chi")
    # Nhóm trong tệp: "A. LAND TOUR", "B. TRẺ EM", "C. CHI PHÍ KHÁC". Giữ nguyên văn – nó là cách
    # Điều hành chia chi phí, và nó khác nhau giữa tour lẻ với đoàn MICE.
    nhom: Mapped[str] = mapped_column(String(80), default="")
    ngay: Mapped[str] = mapped_column(String(60), default="")      # ô "NGÀY" hay ghi chữ, không phải ngày
    noi_dung: Mapped[str] = mapped_column(String(200), default="")
    doi_tac: Mapped[str] = mapped_column(String(200), default="")
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    he_so: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_chung_tu: Mapped[str] = mapped_column(String(60), default="")   # ô "GHI CHÚ": HD 2153, BILL 85454, TM
    mst_ncc: Mapped[str] = mapped_column(String(30), default="")
    co_lech: Mapped[str] = mapped_column(Text, default="")

    def lech_nhan(self):
        """Thành tiền tệp ghi trừ đơn giá × số lượng × hệ số. None khi thiếu số để nhân."""
        if self.thanh_tien is None or self.don_gia is None:
            return None
        return self.thanh_tien - self.don_gia * (self.so_luong or 1) * (self.he_so or 1)  # k2-doc-an-toan: đã chặn None ngay trên


class TourGuideAdvance(Base):
    """Sheet HDV CHI – tiền ứng cho hướng dẫn viên và bảng chi trên tour.

    Mặt này bắt được một loại chênh mà ba sheet kia không thấy: HDV chi theo số khách THỰC ĐI, còn
    chiết tính lập theo số khách ĐÃ ĐẶT. Tệp Nha Trang 10/07/2026: HDV tính vé Tháp Bà cho 44 khách
    (1.320.000 đ), chiết tính tính cho 40 (1.200.000 đ). Tiền ứng 1.620.000, dư 0 – nghĩa là công ty
    đã chi thật 1.620.000 trong khi giá vốn chỉ ghi 1.500.000.

    120.000 đ ấy không nằm ở đâu cả: không trong giá vốn, không trong công nợ, không trong hoàn ứng.
    Không có bảng này thì khoản chênh đó vô hình, và nó vô hình ở MỌI chuyến chứ không riêng chuyến này.
    """
    __tablename__ = "tour_guide_advances"
    __table_args__ = (Index("ix_tga_settlement", "settlement_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("tour_settlements.id", ondelete="CASCADE"))
    noi_dung: Mapped[str] = mapped_column(String(200), default="")
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    tong_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(120), default="")
    # Ba ô ở chân bảng, chỉ điền ở DÒNG TỔNG của mỗi bản – để trống ở các dòng chi tiết.
    tien_ung: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ctp: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    la_dong_tong: Mapped[bool] = mapped_column(Integer, default=0, server_default="0")


class TourSettlementBooking(Base):
    """Sheet DT – doanh thu theo booking. Cầu nối duy nhất sang bảng bookings của VTOS.

    Sheet này có BookingID (115069, 115884, ...) trùng khoá với hệ đặt chỗ. Nhờ nó, một bản quyết
    toán Excel gắn được vào đúng booking trong VTOS mà không phải dò theo tên khách – dò theo tên là
    cách sai, vì cùng một người viết hoa/không dấu mỗi tệp một kiểu (tệp này có cả "NGUYEN HONG DEN"
    lẫn các tên có dấu đầy đủ).

    booking_id để NULL khi chưa tra ra booking thật: rỗng nghĩa là chưa nối được, không phải không có.
    """
    __tablename__ = "tour_settlement_bookings"
    __table_args__ = (Index("ix_tsb_settlement", "settlement_id"),
                      Index("ix_tsb_ma_nguon", "ma_booking_nguon"))
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("tour_settlements.id", ondelete="CASCADE"))
    ma_booking_nguon: Mapped[str] = mapped_column(String(40), default="")
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    ten_nguoi_book: Mapped[str] = mapped_column(String(200), default="")
    dien_thoai: Mapped[str] = mapped_column(String(30), default="")
    gia_tour: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_khach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tong_gia_tour: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_visa: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_khac: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    khuyen_mai: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_dong: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguoi_ban: Mapped[str] = mapped_column(String(120), default="")

    def con_phai_thu(self):
        """Rỗng khi thiếu một trong hai số – không suy ra 0."""
        if self.tong_thu is None or self.da_dong is None:
            return None
        return self.tong_thu - self.da_dong  # k2-doc-an-toan: đã chặn None ngay trên


VE_CTT = {"thu": "I/ Giá tour (thu)", "chi": "II/ Chi phí"}

# Bốn mặt của lớp 2, mỗi mặt trả lời một câu khác nhau. Tên ở đây dùng chung cho API và màn hình để
# không có chỗ nào tự đặt lại tên khác.
MAT_LOP_2 = {
    "khach": "Từng khách – ai trả bao nhiêu, chi phí phân bổ đầu khách",
    "chiet_tinh": "Chiết tính – chi cho ai, chứng từ nào, mã số thuế nào",
    "hdv": "Chi trên tour của HDV – ứng bao nhiêu, chi bao nhiêu, dư bao nhiêu",
    "booking": "Doanh thu theo booking – nối sang hệ đặt chỗ, thu đủ chưa",
}
