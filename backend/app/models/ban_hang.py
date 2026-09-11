"""V6 – chuỗi bán hàng: bảng giá → báo giá → hợp đồng khách → booking.

Lệnh Đợt 2, việc V6. Chuỗi đang ĐỨT Ở ĐẦU: hệ thống có booking nhưng không có bảng báo giá và không
có hợp đồng khách. Hệ quả đo được: 754 chuyến đã bán mà chưa đủ cơ sở tính biên.

────────────────────────────────────────────────────────────────────────────────
ĐIỀU QUAN TRỌNG NHẤT: CỔNG BIÊN ĐỨNG Ở BƯỚC BÁO GIÁ
────────────────────────────────────────────────────────────────────────────────

Trước V6, cổng biên đứng ở bước TRÌNH DỰ TOÁN TOUR. Nhưng cam kết với khách không xảy ra ở đó – nó
xảy ra lúc gửi báo giá. Khi dự toán đi qua cổng thì con số đã nằm trong tay khách từ lâu, và mọi
việc còn lại chỉ là hợp thức hóa một lời hứa đã lỡ.

Nên cổng chuyển lên đây. Dự toán tour vẫn giữ cổng của nó (bước sản xuất), còn báo giá có cổng riêng
(bước cam kết). Hai cổng canh hai việc khác nhau, không phải một cổng đặt hai chỗ.

────────────────────────────────────────────────────────────────────────────────
MỘT BẢNG CHO CẢ LẺ VÀ ĐOÀN
────────────────────────────────────────────────────────────────────────────────

Báo giá lẻ và báo giá đoàn dùng CHUNG một bảng, phân biệt bằng cột `mang`, lọc ở màn hình. Tách đôi
thì mọi phép tính biên, mọi báo cáo doanh số, mọi cổng chặn phải viết hai lần – và hai bản sẽ lệch
nhau, thường là ở bản ít người nhìn hơn.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO BÁO GIÁ CẦN BẢN ĐÓNG BĂNG RIÊNG
────────────────────────────────────────────────────────────────────────────────

Gửi khách rồi thì con số đó là một cam kết, kể cả khi hôm sau sale sửa báo giá. Nếu chỉ có một bảng
`bao_gia` bị ghi đè thì câu hỏi "hôm ấy ta hứa với khách bao nhiêu" không trả lời được – mà đó đúng
là câu hỏi được hỏi lúc tranh chấp. Mỗi lần GỬI sinh một dòng `bao_gia_ban` chép lại toàn bộ số và
dòng dịch vụ tại thời điểm đó. Bản đã gửi KHÔNG BAO GIỜ sửa; sửa là sinh bản mới.

Đây khác với cột `phien_ban` của V10: V10 chặn hai người ghi đè nhau trong lúc cùng sửa; bản đóng
băng ở đây giữ LỊCH SỬ CAM KẾT. Hai việc khác nhau, và bảng này có cả hai.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

# Mảng kinh doanh. Dùng đúng mã phòng ban đã có để không sinh thêm một bộ từ vựng thứ hai.
MANG = ("kd_le", "kd_doan")

TRANG_THAI_BAO_GIA = {
    "nhap": "Nháp",
    "cho_duyet_bien": "Chờ duyệt biên mỏng",
    "da_gui": "Đã gửi khách",
    "khach_chot": "Khách chốt",
    "khach_tu_choi": "Khách từ chối",
    "het_han": "Hết hạn",
    "huy": "Hủy",
}


class BangGia(Base):
    """Chính sách bán của MỘT sản phẩm trong MỘT khoảng hiệu lực.

    Giá không phải một con số trên sản phẩm mà là một chính sách có thời hạn: cao điểm khác thấp
    điểm, và khi tranh chấp thì câu hỏi là "ngày ấy giá niêm yết bao nhiêu". Giữ chính sách theo
    khoảng hiệu lực trả lời được câu đó; ghi đè một con số thì không.
    """
    __tablename__ = "bang_gia"
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(200))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    mang: Mapped[str] = mapped_column(String(20), default="kd_le", index=True)
    hieu_luc_tu: Mapped[date] = mapped_column(Date, index=True)
    # Để RỖNG = còn hiệu lực, KHÔNG phải hết hạn hôm nay. Đây là chỗ dễ viết nhầm thành ngày hôm nay
    # và làm mọi bảng giá tự tắt sau một đêm.
    hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)
    tien_te: Mapped[str] = mapped_column(String(3), default="VND")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(20), default="hieu_luc")   # hieu_luc / ngung
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BangGiaDong(Base):
    """Một dòng giá: hạng khách, giá bán, và giá vốn tương ứng.

    GIÁ VỐN NẰM CÙNG DÒNG VỚI GIÁ BÁN, cố ý. Cổng biên cần cả hai con số tại cùng một chỗ; để giá vốn
    ở bảng khác thì lúc tính biên phải đi ghép, và mỗi lần ghép hụt là một lần cổng mở oan.

    Giá vốn để RỖNG nghĩa là CHƯA BIẾT, không phải bằng 0 – xem `co_du_co_so()`.
    """
    __tablename__ = "bang_gia_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    bang_gia_id: Mapped[int] = mapped_column(ForeignKey("bang_gia.id"), index=True)
    hang_khach: Mapped[str] = mapped_column(String(20), default="nguoi_lon")  # nguoi_lon / tre_em / em_be / phu_thu_phong_don
    mo_ta: Mapped[str] = mapped_column(String(200), default="")
    # K2 09/9: chưa nhập thì để RỖNG, không phải 0.
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chiet_khau_toi_da: Mapped[float] = mapped_column(Float, default=0)        # tỷ lệ, 0,05 = 5%
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)


class BaoGia(Base):
    """Báo giá gửi khách. MỘT bảng cho cả lẻ và đoàn, lọc bằng cột `mang`."""
    __tablename__ = "bao_gia"
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    mang: Mapped[str] = mapped_column(String(20), default="kd_le", index=True)
    khach_ten: Mapped[str] = mapped_column(String(200))
    khach_dien_thoai: Mapped[str] = mapped_column(String(30), default="")
    khach_email: Mapped[str] = mapped_column(String(120), default="")
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    bang_gia_id: Mapped[int | None] = mapped_column(ForeignKey("bang_gia.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    ngay_khoi_hanh: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_khach: Mapped[int] = mapped_column(Integer, default=1)
    han_hieu_luc: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap", index=True)
    # Cổng biên: ghi lại KẾT QUẢ tại thời điểm gửi, không tính lại lúc đọc. Tính lại thì báo cáo hôm
    # nay sẽ nói về ngưỡng hôm nay, còn quyết định thì đã ra theo ngưỡng hôm ấy.
    bien_luc_gui: Mapped[float | None] = mapped_column(Float, nullable=True)
    nguong_luc_gui: Mapped[float | None] = mapped_column(Float, nullable=True)
    duoi_bien: Mapped[bool] = mapped_column(Boolean, default=False)
    giai_trinh: Mapped[str] = mapped_column(Text, default="")
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_tu_choi: Mapped[str] = mapped_column(Text, default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BaoGiaDong(Base):
    """Dòng của báo giá đang soạn. Sửa thoải mái; bản GỬI KHÁCH nằm ở bao_gia_ban."""
    __tablename__ = "bao_gia_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    bao_gia_id: Mapped[int] = mapped_column(ForeignKey("bao_gia.id"), index=True)
    hang_khach: Mapped[str] = mapped_column(String(20), default="nguoi_lon")
    mo_ta: Mapped[str] = mapped_column(String(200), default="")
    so_luong: Mapped[int] = mapped_column(Integer, default=1)
    # K2 09/9: chưa nhập thì để RỖNG, không phải 0.
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_von_don_vi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chiet_khau: Mapped[float] = mapped_column(TIEN, default=0)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)


class BaoGiaBan(Base):
    """Bản ĐÓNG BĂNG của một lần gửi khách. Không sửa, không xóa.

    `noi_dung` chép nguyên các dòng tại thời điểm gửi thay vì trỏ sang bao_gia_dong: trỏ thì sửa dòng
    hôm sau là bản đã gửi đổi theo, và bản đóng băng không còn đóng băng.
    """
    __tablename__ = "bao_gia_ban"
    id: Mapped[int] = mapped_column(primary_key=True)
    bao_gia_id: Mapped[int] = mapped_column(ForeignKey("bao_gia.id"), index=True)
    lan: Mapped[int] = mapped_column(Integer, default=1)
    # K2 09/9: chưa nhập thì để RỖNG, không phải 0.
    tong_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    bien: Mapped[float | None] = mapped_column(Float, nullable=True)
    nguong: Mapped[float | None] = mapped_column(Float, nullable=True)
    du_co_so: Mapped[bool] = mapped_column(Boolean, default=False)
    noi_dung: Mapped[list] = mapped_column(JSON, default=list)
    gui_boi: Mapped[str] = mapped_column(String(50), default="")
    gui_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HopDongKhach(Base):
    """Hợp đồng khách – mắt xích giữa báo giá đã chốt và booking.

    Số hợp đồng và ngày ký là thứ kiểm toán hỏi đầu tiên khi đối chiếu doanh thu, và trước V6 hệ
    thống không có chỗ nào giữ chúng.
    """
    __tablename__ = "hop_dong_khach"
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    so_hop_dong: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    bao_gia_id: Mapped[int | None] = mapped_column(ForeignKey("bao_gia.id"), nullable=True, index=True)
    bao_gia_ban_id: Mapped[int | None] = mapped_column(ForeignKey("bao_gia_ban.id"), nullable=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    khach_ten: Mapped[str] = mapped_column(String(200))
    khach_dai_dien: Mapped[str] = mapped_column(String(120), default="")
    khach_ma_so_thue: Mapped[str] = mapped_column(String(20), default="")
    khach_dia_chi: Mapped[str] = mapped_column(String(300), default="")
    ngay_ky: Mapped[date | None] = mapped_column(Date, nullable=True)
    gia_tri: Mapped[float] = mapped_column(TIEN, default=0)
    # K2 09/9: chưa nhập thì để RỖNG, không phải 0.
    dat_coc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    han_thanh_toan: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap", index=True)  # nhap / da_ky / thanh_ly / huy
    tep_dinh_kem: Mapped[str] = mapped_column(String(300), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ────────────────────────────── VPM-9: LỊCH THANH TOÁN THEO TIẾN ĐỘ ──────────────────────────────
MOC_HAN = {
    "ngay_ky":         "sau ngày ký hợp đồng",
    "truoc_khoi_hanh": "trước ngày khởi hành",
    "sau_khoi_hanh":   "sau ngày khởi hành",
    "co_dinh":         "ngày cố định do người nhập",
}


class LichThanhToanHD(Base):
    """Một hợp đồng khách trả làm NHIỀU ĐỢT – mỗi dòng là một đợt, có hạn riêng và số tiền riêng.

    VẤN ĐỀ BẢNG NÀY SINH RA ĐỂ GIẢI

    Trước 11/9/2026 `hop_dong_khach` chỉ có MỘT `han_thanh_toan` và MỘT `dat_coc`. Hợp đồng đoàn vài
    trăm triệu trong thực tế trả làm ba bốn đợt – ký 30%, trước khởi hành 40%, sau tour phần còn lại –
    và hệ thống không có chỗ nào nói được điều đó. Hệ quả: không ai trả lời được câu hỏi đơn giản nhất
    của người thu công nợ – "ĐẾN HÔM NAY khách phải trả bao nhiêu?". Chỉ có tổng giá trị hợp đồng và
    tổng đã thu; phần đến hạn nằm trong đầu người phụ trách, hoặc trong một tệp Excel riêng.

    BA QUYẾT ĐỊNH ĐÁNG GHI LẠI

    MỘT — SỐ TIỀN CỦA ĐỢT ĐƯỢC CHỐT THÀNH TIỀN, KHÔNG ĐỂ LÀ PHẦN TRĂM. `ty_le` vẫn lưu, nhưng chỉ để
    kể lại con số từ đâu ra. Lý do: nếu đợt giữ dạng %, thì sửa giá trị hợp đồng sẽ lặng lẽ đổi số
    tiền đòi khách – trong khi khách đã cầm bản hợp đồng ghi con số cũ. Số đã cam kết phải nằm yên.

    HAI — HẠN ĐÃ BÁO CHO KHÁCH THÌ KHÔNG TỰ DỜI. Hạn tính một lần từ mốc (`moc` + `moc_so_ngay`) rồi
    lưu thành NGÀY THẬT. Đổi ngày khởi hành thì hệ thống KÊU LÊN để người quyết định có dời hạn hay
    không, chứ không âm thầm đẩy hạn đi – một cái hạn tự đổi là một lời hứa bị sửa sau lưng cả hai bên.

    BA — KHÔNG LƯU "ĐÃ THU" THEO TỪNG ĐỢT. Tiền vào không mang nhãn ghi nó trả cho đợt nào; lưu một
    con số đã-thu cho mỗi đợt là tạo ra câu trả lời thứ hai cho "hợp đồng này đã thu bao nhiêu", và
    hai câu trả lời ấy sẽ lệch nhau. Thay vào đó, tổng đã thu (từ phiếu thu của booking) được RẢI vào
    các đợt theo thứ tự hạn khi hiển thị. Đó là một phép chia để đọc, và màn hình nói rõ như vậy.
    """
    __tablename__ = "lich_thanh_toan_hd"

    id: Mapped[int] = mapped_column(primary_key=True)
    hop_dong_id: Mapped[int] = mapped_column(ForeignKey("hop_dong_khach.id"), index=True)
    dot: Mapped[int] = mapped_column(Integer, default=1)
    ten: Mapped[str] = mapped_column(String(120), default="")

    ty_le: Mapped[float | None] = mapped_column(Float, nullable=True)   # % tham chiếu – KHÔNG dùng để tính lại
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)  # K2: rỗng là CHƯA NHẬP, không phải 0

    moc: Mapped[str] = mapped_column(String(20), default="co_dinh")
    moc_so_ngay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    han: Mapped[date | None] = mapped_column(Date, nullable=True)
    han_goc: Mapped[date | None] = mapped_column(Date, nullable=True)   # hạn lần đầu – giữ lại để thấy đã dời bao nhiêu

    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
