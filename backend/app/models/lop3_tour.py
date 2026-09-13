"""Lớp 3 quyết toán tour: hai hình thức, dòng khách, dòng doanh thu, phương tiện, HDV chi, dấu vết sửa.

HAI HÌNH THỨC, KHÔNG PHẢI BA – Chủ tịch chốt 11/9/2026

    trong_nuoc  : tour lẻ nội địa và tour đoàn nội địa
    nuoc_ngoai  : tour lẻ và tour đoàn outbound

Đo trên bốn mẫu quyết toán thật thì "đoàn" KHÔNG phải một hình thức riêng. Đoàn Phú Quốc là tour
trong nước đi MÁY BAY; tour lẻ Nha Trang là tour trong nước đi Ô TÔ. Cái khác giữa chúng là phương
tiện, không phải hình thức – nên phương tiện là một trục riêng (bảng TourPhuongTien), và dựng "đoàn"
thành hình thức thứ ba là nhầm hai trục làm một.

Cái thật sự chia đôi là biên giới: trong nước thì một đồng tiền, không visa, không vé quốc tế; nước
ngoài thì nhiều đồng tiền có tỷ giá, phí lãnh sự quán từng khách một giá, vé quốc tế từng khách một
giá, và khách của đại lý ngồi ghép.

BỐN MẪU ĐÃ ĐỌC, VÀ MỖI MẪU DẠY MỘT THỨ

    NHA TRANG 10.07.26        lẻ, trong nước, ô tô   -> doanh thu là 42 DÒNG KHÁCH có tên
    ĐOÀN ĐÀ LẠT 3N3D 04.06    đoàn, trong nước       -> doanh thu là 4 DÒNG HỢP ĐỒNG cho 37 người,
                                                        có VAT 8%, và có DÒNG ÂM từ biên bản thanh lý
    SM000.05260226 (SIN/MAL)  lẻ, nước ngoài         -> ngoại tệ, vé máy bay, khách của đại lý ghép
    QuyetToan_27052026_UK     lẻ, nước ngoài         -> ba đồng tiền, phí lãnh sự quán từng khách
                                                        một giá, hai pháp nhân cùng thu

HAI GRAIN DOANH THU, MỘT BẢNG

Tour lẻ ghi doanh thu theo từng khách có tên; tour đoàn ghi theo dòng hợp đồng ("NGƯỜI LỚN × 25").
Cùng một hình – đơn giá, số lượng, thuế suất – nên cùng một bảng TourDoanhThuDong. Dòng nào ứng với
một khách có tên thì nối vào khach_id, dòng hợp đồng đoàn thì để trống. Nhờ vậy báo cáo toàn công ty
cộng được cả hai mà không phải cộng từ hai nguồn.

BẢNG LỚP 2 VÀ BẢNG LỚP 3 KHÁC NHAU CHỖ NÀO

Lớp 2 (app/models/quyet_toan.py) là BẢN SAO Y TỆP: giữ nguyên những gì tệp Excel viết, kể cả khi tệp
viết sai, để còn đối chiếu được với bản gốc đã có chữ ký. Nó treo vào tour_settlements – tức treo vào
CỬA NẠP.

Lớp 3 ở đây là bảng VẬN HÀNH: treo vào tours, mang quy tắc của công ty, mang luồng duyệt. Hai lớp trả
lời hai câu khác nhau – "tệp viết gì" và "công ty quyết gì". Mẫu Nha Trang cho thấy vì sao không gộp
được: tệp viết HDV mua 44 suất Tháp Bà trong khi chiết tính tính 40. Bản sao y tệp phải giữ CẢ HAI
con số; bảng vận hành phải sinh ra một khoản chờ người duyệt.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Numeric, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

HINH_THUC = {
    "trong_nuoc": "Tour trong nước",
    "nuoc_ngoai": "Tour nước ngoài",
}

# AI TRẢ TIỀN. Chủ tịch chốt 11/9/2026: ghi hết mọi người ngồi trên chuyến, tách bốn nhóm.
# Tách khỏi bậc tuổi vì đây là hai trục: một cột không nói được "trẻ em của đại lý".
NHOM_KHACH = {
    "tra_tien": "Khách trả tiền – doanh thu của Vietourist",
    "mien_phi": "Suất miễn phí – khách được tặng, hoặc miễn phí theo tuổi",
    "noi_bo": "Nhân viên công ty đi cùng, kể cả trưởng đoàn công ty cử",
    "dai_ly": "Khách của đại lý ngồi ghép – doanh thu không thuộc Vietourist",
}

# TÍNH GIÁ BAO NHIÊU. Ngưỡng tuổi và tỷ lệ là tham số có hiệu lực theo ngày (tuoi_em_be, tuoi_tre_em,
# ty_le_tre_em_* và ty_le_em_be_* trong rules.DEFAULT_PARAMS – TÁCH THEO HÌNH THỨC TOUR), không
# viết cứng ở đây: đổi chính sách thì đổi tham số,
# còn các chuyến cũ giữ nguyên tỷ lệ của ngày chúng khởi hành.
LOAI_TUOI = {
    "nguoi_lon": "Người lớn – giá đầy đủ",
    "tre_em": "Trẻ em – theo tỷ lệ phần trăm giá người lớn",
    "em_be": "Em bé – theo tỷ lệ riêng của bậc em bé (trong nước 10%, nước ngoài 30%)",
}

LOAI_PHUONG_TIEN = {
    "o_to": "Ô tô",
    "may_bay": "Máy bay",
    "tau_hoa": "Tàu hoả",
    "tau_thuy": "Tàu thuỷ / ca nô",
    "khac": "Khác",
}

LOAI_DOANH_THU = {
    "hop_dong": "Theo hợp đồng / giá bán",
    "thanh_ly": "Điều chỉnh theo biên bản thanh lý – thường là số ÂM",
    "phu_thu": "Phụ thu phát sinh",
    "charge_huy": "Tiền phạt huỷ giữ lại",
    # Đ-6 · Chủ tịch chốt 12/9/2026: "tiền tip tour châu Âu chia 1 phần với công ty".
    #
    # Chỉ PHẦN CÔNG TY GIỮ LẠI SAU KHI CHIA mới là doanh thu. Toàn bộ tiền tip khách trả là tiền của
    # khách trả cho hướng dẫn viên, công ty giữ hộ; phần của trưởng đoàn đi vào bản chốt công nợ TL,
    # không đi vào bảng lãi lỗ. Ghi cả cục vào đây là thổi doanh thu lên bằng tiền của người khác.
    #
    # Tiền tip hoàn cho đại lý là dòng ÂM loại này, và như mọi dòng âm thì bắt buộc khai `chung_tu`.
    "tip_cong_ty": "Phần tiền tip thuộc công ty sau khi chia – xem app/services/tip_tour.py",
    # Đ-7 · TIỀN ĐI NGANG QUA, KHÔNG PHẢI DOANH THU.
    #
    # Nó nằm trong sổ doanh thu vì đó là nơi ghi tiền vào, nhưng MỌI phép cộng doanh thu phải loại
    # nó ra — xem thu_ho_chi_ho.la_doanh_thu(). Mẫu visa lẻ T5/2026 có hẳn cột "Thu hộ chi hộ"
    # (821.500 đ, 1.200.000 đ) nằm ngoài cả cột Tổng thu lẫn Tổng chi.
    "thu_ho": "Thu hộ khách – KHÔNG phải doanh thu, phải trả lại hoặc chi đúng việc",
    "thu_khac": "Thu khác",
}

TRANG_THAI_DUYET = {
    "cho_duyet": "Chờ Trưởng phòng Điều hành duyệt",
    "da_duyet": "Đã duyệt – công ty chịu phần vượt",
    "tu_choi": "Không duyệt – hướng dẫn viên bù phần vượt",
}

TY_GIA = Numeric(18, 4)


class BookingKhach(Base):
    """Một người ngồi trên chuyến.

    VÌ SAO PHẢI CÓ BẢNG NÀY

    Bảng bookings đếm đầu người bằng ba cột adl/chd/inf. Nó biết CÓ BAO NHIÊU trẻ em; nó không biết
    trẻ nào, và tuyệt nhiên không biết tuổi. Quy tắc giá theo tuổi vì thế không kiểm được: nhìn vào
    tờ quyết toán đã có bốn chữ ký, không ai xác minh được cháu nào thật sự dưới 2 tuổi.

    Và nó không có chỗ nào cho người KHÔNG phải khách. Mẫu thật có đủ cả: đoàn Phú Quốc "46 NGƯỜI LỚN
    + 3 TRẺ EM + 1 FREE + 4 NỘI BỘ"; SIN/MAL có 30 khách cộng 22 người của hai đại lý SGS và VV ngồi
    cùng chuyến mà doanh thu không thuộc Vietourist. Những người ấy ăn suất ăn thật, ngồi ghế thật,
    chịu bảo hiểm thật. Không ghi họ thì số khách trên tờ quyết toán không bao giờ khớp số ghế.

    NGÀY SINH THU Ở KHÂU ĐĂNG KÝ, KHÔNG PHẢI Ở QUYẾT TOÁN

    Đến lúc quyết toán thì khách đã đi rồi; hỏi tuổi lúc ấy là hỏi để hợp thức hoá, không phải để tính
    giá. Nên bảng này treo vào bookings, không treo vào tour_settlements.
    """
    __tablename__ = "booking_khach"
    __table_args__ = (Index("ix_bk_booking", "booking_id"), Index("ix_bk_tour", "tour_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    # Lặp lại tour_id để hỏi "42 khách của chuyến này" không phải nối qua bookings. Dịch vụ ghi cả
    # hai; lệch nhau là lỗi và có phép kiểm bắt.
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ho_ten: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nhom_khach: Mapped[str | None] = mapped_column(String(20), nullable=True)
    loai_tuoi: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # NULL = CHƯA HỎI ngày sinh. Cột quyết định của quy tắc giá theo tuổi, nên NULL phải kêu lên chứ
    # không lặng lẽ tính thành người lớn: tính nhầm em bé thành người lớn là thu thừa tiền của khách,
    # và bảng vẫn cân nên không ai phát hiện.
    ngay_sinh: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Hệ thống xếp loại tại NGÀY KHỞI HÀNH rồi GHI LẠI, không tính lại mỗi lần đọc. Đứa trẻ 11 tuổi
    # rưỡi lúc đi tour sẽ 12 tuổi khi kế toán mở lại tờ quyết toán ba tháng sau; tờ đã ký không được
    # đổi số.
    tuoi_luc_di: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Giá hệ thống tính từ quy tắc, và giá thực bán. Hai cột riêng, vì chênh nhau là DỮ LIỆU chứ không
    # phải lỗi – đó là tín hiệu bảng giá đang lệch quy tắc ở đâu.
    gia_chuan: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ly_do_khac_chuan: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Tour nước ngoài. Mã đặt chỗ là khoá tra ngược duy nhất về hãng bay khi cần đối chiếu vé – mẫu
    # SIN/MAL ghi nó ngay trên dòng khách (KCLWRD/H7ZDSV).
    so_ho_chieu: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ma_dat_cho: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # ---- Bản nâng cấp y2d8e3f0a5b97 (11/9/2026) ----
    #
    # Bốn ô mẫu ĐANG THU mà trước đây không có chỗ chứa: nhân viên gõ xong thì bộ nạp đọc rồi bỏ.
    # CCCD tách riêng khỏi so_ho_chieu – mẫu trong nước thu CCCD, mẫu nước ngoài thu hộ chiếu, và
    # hai loại giấy tờ chung một ô thì không lọc được, cũng không kiểm được độ dài.
    #
    # KHÔNG có cột "sale" ở đây: sale thuộc về PHIẾU ĐẶT (bookings.sales_id). Từ bản nâng cấp này
    # dòng khách treo đúng phiếu đặt nên tra ra được. Chép sang đây là hai chỗ giữ cùng một sự thật.
    gioi_tinh: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dien_thoai: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cccd: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nguoi_sua: Mapped[str | None] = mapped_column(String(60), nullable=True)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def lech_chuan(self) -> float | None:
        """Bán khác giá chuẩn bao nhiêu. None khi thiếu một trong hai số – rỗng không phải 0."""
        if self.gia_ban is None or self.gia_chuan is None:
            return None
        return self.gia_ban - self.gia_chuan

    def co_thu(self) -> bool:
        """Người này có mang doanh thu cho Vietourist không.

        Dùng làm mẫu số của quy tắc phân bổ 'chia đều khách có thu'. Khách đại lý và khách nội bộ
        KHÔNG mang doanh thu dù họ vẫn ngồi ghế và vẫn ăn suất ăn.
        """
        return self.nhom_khach == "tra_tien" and (self.gia_ban or 0) > 0


class KhachChiPhi(Base):
    """Chi phí ĐÍCH DANH của một khách – không chia, không phân bổ.

    Tour trong nước chia chi phí chung cho từng khách bằng phép chia. Tour nước ngoài thì không chia
    được. Đo trên tệp UK: cùng một chuyến mà vé máy bay của khách này 22.435.959 đ còn khách kia
    21.903.700 đ; phí lãnh sự quán chạy từ 7.875.750 đến 8.290.750; và bốn khách không mua visa vì
    đã có sẵn.

    Ép những khoản ấy vào phép chia là làm hỏng cả hai đầu: khách đã có visa phải gánh tiền visa của
    người khác, còn người mua visa đắt thì được gánh hộ. Nên chúng là chi phí đích danh, nằm ở đây.
    """
    __tablename__ = "khach_chi_phi"
    __table_args__ = (Index("ix_kcp_khach", "khach_id"), Index("ix_kcp_tour", "tour_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    khach_id: Mapped[int] = mapped_column(ForeignKey("booking_khach.id", ondelete="CASCADE"))
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    # Mã khoản mục chi phí – cùng danh mục với dòng chi chung, xem app/services/khoan_muc_chi.py.
    # Những mã có dich_danh=True (vé máy bay, phí lãnh sự quán, dịch thuật) thuộc về bảng này.
    ma_khoan_muc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # ve_may_bay / visa / dich_thuat / qua_tang / bao_hiem / khac
    loai: Mapped[str | None] = mapped_column(String(30), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mst_ncc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    so_hoa_don: Mapped[str | None] = mapped_column(String(30), nullable=True)


class TourDoanhThuDong(Base):
    """Một dòng doanh thu của chuyến.

    HAI CÁCH GHI, MỘT HÌNH DẠNG

        Tour lẻ  : mỗi khách một dòng, có tên  (Nha Trang: 42 dòng cho 42 người)
        Tour đoàn: mỗi khoản hợp đồng một dòng (Đà Lạt: 4 dòng cho 37 người)

    Cả hai đều có đơn giá, số lượng, thuế suất – nên cùng một bảng. Dòng ứng với một khách có tên thì
    nối khach_id; dòng hợp đồng đoàn để trống.

    THU ÂM LÀ CHUYỆN BÌNH THƯỜNG, KHÔNG PHẢI LỖI NHẬP

    Mẫu Đà Lạt có "HOÀN SUẤT ĂN NGÀY CUỐI −899.999" và "HOÀN VÉ THAM QUAN −539.999", cả hai đến từ
    biên bản thanh lý hợp đồng đã ký. Chặn số âm ở đây là buộc Điều hành phải trừ lén vào dòng dương,
    và thế là mất dấu vết của việc thanh lý. Số âm được phép; cái BẮT BUỘC là cột chung_tu.

    VAT NẰM TRÊN DÒNG, KHÔNG PHẢI Ở CUỐI BẢNG

    Đoàn bán cho doanh nghiệp thì có hoá đơn GTGT: mẫu Đà Lạt ghi 100.592.592,59 trước thuế + 8% =
    108.640.000. Tour lẻ bán cho khách lẻ thì không. Cùng một hệ thống phải đỡ được cả hai, nên thuế
    suất là một cột của dòng và để rỗng được.
    """
    __tablename__ = "tour_doanh_thu_dong"
    __table_args__ = (Index("ix_tdd_tour", "tour_id"), Index("ix_tdd_khach", "khach_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    khach_id: Mapped[int | None] = mapped_column(ForeignKey("booking_khach.id"), nullable=True)
    loai: Mapped[str | None] = mapped_column(String(20), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    doi_tuong: Mapped[str | None] = mapped_column(String(20), nullable=True)
    don_gia_truoc_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien_truoc_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thue_suat: Mapped[float | None] = mapped_column(Float, nullable=True)
    tien_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Số hiệu biên bản thanh lý / phụ lục hợp đồng làm căn cứ. Dòng âm mà không có căn cứ thì phép
    # kiểm chặn – xem app/services/quyet_toan_lop3.py.
    chung_tu: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # ---- Đ-7 (13/9/2026) · chỉ có nghĩa với dòng loại `thu_ho` ----
    #
    # CHỦ TIỀN rỗng = CHƯA AI XÁC ĐỊNH, không phải "của công ty". Một khoản thu hộ không biết của ai
    # thì không trả lại được cho ai — đó là chỗ DUY NHẤT Đ-7 chặn đóng số.
    # HẠN XỬ LÝ rỗng = chưa đặt hạn; số dư không có hạn thì nằm đó mãi và không thành việc của ai.
    chu_tien: Mapped[str | None] = mapped_column(String(200), nullable=True)
    han_xu_ly: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TourPhuongTien(Base):
    """Một chặng phương tiện của chuyến.

    VÌ SAO LÀ BẢNG CHỨ KHÔNG PHẢI MỘT CỘT

    Bảng tours đã có cột `transport` dạng chữ. Một cột không đủ: đoàn Phú Quốc đi máy bay SGN–PQC rồi
    dùng HAI xe 29 chỗ tại đảo (biển 68H04420 và 68F00897, hai tài xế khác nhau); tour UK có vé quốc
    tế cộng xe tại Anh. Mỗi chặng có nhà cung cấp riêng, giá riêng, số chỗ riêng và chứng từ riêng.

    XE NHÀ KHÁC XE THUÊ NGOÀI

    Mẫu đoàn Đà Lạt có dòng "VIETRIP 45s – 3N3D  18.000.000  CÔNG NỢ VIETRIP" nằm hẳn một sheet
    riêng. Đó là xe của đội xe trong nhóm, nên khoản ấy là công nợ nội bộ chứ không phải tiền trả cho
    bên thứ ba – hai đường hạch toán khác nhau, và khi hợp nhất báo cáo thì nó phải loại trừ. Cột
    xe_nha + vehicle_id giữ đúng chỗ đó.
    """
    __tablename__ = "tour_phuong_tien"
    __table_args__ = (Index("ix_tpt_tour", "tour_id"), Index("ix_tpt_loai", "loai"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    loai: Mapped[str] = mapped_column(String(20))
    chang: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    gio_di: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gio_den: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Xe: biển số. Máy bay: số hiệu chuyến (9G1951). Tàu: số hiệu tàu/toa.
    so_hieu: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ma_dat_cho: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mst_ncc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    xe_nha: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    so_cho: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_khach_su_dung: Mapped[int | None] = mapped_column(Integer, nullable=True)
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Chặng không có dòng chi là chặng chưa vào giá vốn – phép kiểm bắt được.
    dong_chi_phi_id: Mapped[int | None] = mapped_column(ForeignKey("tour_cost_lines.id"), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TourHdvChi(Base):
    """Một khoản hướng dẫn viên chi trên đường, và hai phép so của khoản ấy.

    Chủ tịch chốt 10/9/2026: HDV chi vượt so với dự toán của Điều hành mà KHÔNG ĐƯỢC DUYỆT thì HDV bù
    tiền vào.

    HAI PHÉP SO KHÁC NHAU, ĐỪNG LẪN

        vuot    = thực chi − chiết tính   -> vượt DỰ TOÁN. Đây là cái Chủ tịch chốt.
        con_lai = tiền ứng − thực chi     -> thừa/thiếu so với khoản đã ứng. Âm nghĩa là HDV bỏ tiền
                  túi ra trước và CÔNG TY nợ lại HDV.

    Hai chiều ngược nhau và cùng xảy ra thật. Nha Trang: HDV chi vượt chiết tính 120.000 nhưng ứng vừa
    đủ nên "Dư 0". Đoàn Đà Lạt: công ty ứng 3.300.000, HDV chi 3.696.000, còn lại −396.000 – công ty
    nợ HDV. Gộp hai cột làm một là có lúc đi đòi tiền người đang được công ty nợ.

    IM LẶNG KHÔNG ĐƯỢC TÍNH LÀ ĐỒNG Ý

    Mặc định trang_thai_duyet là "cho_duyet", và tờ quyết toán không đóng được khi còn dòng chờ duyệt.
    Nếu im lặng mặc nhiên thành đã duyệt thì quy định chỉ có hiệu lực với những người có ai đó chịu
    bấm nút – tức là không có hiệu lực.

    PHẦN MỀM KHÔNG TỰ TRỪ LƯƠNG

    Từ chối thì sinh phai_thu_hdv – một con số chờ, mang tên người. Kế toán mới là người trừ, và phải
    có điều khoản trong quy chế hướng dẫn viên thì mới cưỡng chế được.
    """
    __tablename__ = "tour_hdv_chi"
    __table_args__ = (Index("ix_thc_tour", "tour_id"), Index("ix_thc_duyet", "trang_thai_duyet"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    phan_cong_id: Mapped[int | None] = mapped_column(ForeignKey("guide_assignments.id"), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_ung: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Tiền của KHÁCH, không phải của công ty. Mẫu UK: "TL thu của khách 126 GBP (mua dùm khách vé
    # tham quan)". Khoản ấy không được vào giá vốn, và cũng không được vào doanh thu.
    thu_ho_khach: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    # ---- Đ-7 (13/9/2026) · CỜ NÀY TRƯỚC ĐÂY LÀ CỜ CHẾT ----
    #
    # `thu_ho_khach` đã có từ trước và đúng về ý, nhưng KHÔNG chỗ nào cộng trừ nó vào bản chốt – nó
    # chỉ nằm đó. Tức là hệ thống biết khoản này là tiền của khách mà vẫn không trả lời được câu
    # "vậy giờ ai đang cầm bao nhiêu tiền của ai".
    #
    # Hai cột dưới đây biến nó thành một số dư THẬT, có chủ và có hạn.
    #
    # CHỦ TIỀN – rỗng nghĩa là CHƯA AI XÁC ĐỊNH, khác hẳn "của công ty". Một khoản thu hộ mà không
    # biết của ai thì không trả lại được cho ai; để trống rồi mặc định là tiền công ty là cách biến
    # tiền của khách thành doanh thu mà không ai bấm nút nào.
    chu_tien: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # HẠN XỬ LÝ – ngày phải trả lại hoặc nộp về. Số dư giữ hộ không có hạn thì nó nằm đó mãi và
    # không bao giờ thành việc của ai. Rỗng = chưa đặt hạn, và bộ soát nói ra điều đó.
    han_xu_ly: Mapped[date | None] = mapped_column(Date, nullable=True)
    # NULL nghĩa là HDV chi một khoản KHÔNG CÓ trong chiết tính – nặng hơn chi vượt, vì không có gì
    # để so. Trường hợp ấy phải duyệt toàn bộ số tiền, không phải phần chênh.
    dong_chiet_tinh_id: Mapped[int | None] = mapped_column(ForeignKey("tour_cost_lines.id"), nullable=True)
    thanh_tien_chiet_tinh: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    vuot: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    con_lai: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # phieu_thu / hoa_don / khong_co. Mẫu Đà Lạt ghi rõ từng dòng, và đó là căn cứ để kế toán hoàn ứng.
    loai_chung_tu: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trang_thai_duyet: Mapped[str] = mapped_column(String(20), default="cho_duyet",
                                                  server_default="cho_duyet", nullable=False)
    nguoi_duyet: Mapped[str | None] = mapped_column(String(60), nullable=True)
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_duyet: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phai_thu_hdv: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SuaSauKy(Base):
    """Một lần sửa tờ quyết toán sau khi tờ ấy đã có chữ ký.

    Chủ tịch chốt 10/9/2026: chỉ Trưởng phòng Điều hành (tp_dh) và Phó Tổng Giám đốc đoàn (ptgd_doan)
    sửa được, và phải để lại dấu vết cùng lý do.

    MỖI LẦN MỘT DÒNG, KHÔNG GHI ĐÈ, KHÔNG XOÁ

    Kể cả Chủ tịch cũng không xoá dòng ở bảng này. Sửa sai thì sửa tiếp và ghi tiếp. Một sổ dấu vết mà
    người có quyền cao nhất xoá được thì không phải sổ dấu vết.

    VÌ SAO gia_tri_cu / gia_tri_moi LÀ Text CHỨ KHÔNG PHẢI TIEN

    Bảng này ghi được cả sửa số lẫn sửa chữ, và sửa chữ mới là phần hay sai. Đo trên hai mẫu: tờ Nha
    Trang sai ngày đi (07/07 trong khi ba nguồn khác nói 10/07) và sai số khách (ghi 44, đếm được 42).
    Tờ đoàn Đà Lạt mang HAI mã tour khác nhau trong cùng một tệp (MICEDL3N2D.03300526 ở đầu bảng,
    MICEDL3N3D.04040626 ở sheet chi phí) và các dòng chi ghi ngày 30/05–01/06 trong khi đầu bảng ghi
    khởi hành 04/06 – dấu vết của một tệp chép lại từ chuyến trước mà chưa sửa hết.

    Ép kiểu tiền là tự loại bỏ đúng những lỗi đã tìm thấy trên mẫu thật.
    """
    __tablename__ = "sua_sau_ky"
    __table_args__ = (Index("ix_ssk_tour", "tour_id"), Index("ix_ssk_bang", "bang", "ban_ghi_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    bang: Mapped[str] = mapped_column(String(60))
    ban_ghi_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truong: Mapped[str | None] = mapped_column(String(60), nullable=True)
    gia_tri_cu: Mapped[str | None] = mapped_column(Text, nullable=True)
    gia_tri_moi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bắt buộc, và dịch vụ từ chối lý do dưới 10 ký tự: "sửa" không phải một lý do, "sửa lại" cũng
    # không. Ô lý do nhận được một chữ thì sổ dấu vết đầy những chữ vô nghĩa, và người đọc thôi mở.
    ly_do: Mapped[str] = mapped_column(String(300))
    nguoi_sua: Mapped[str] = mapped_column(String(60))
    vai_tro: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sua_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-8 (13/9/2026) · VÉ MÁY BAY THEO MÃ ĐẶT CHỖ
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# Đo trên hai tệp thật:
#
#   QuyetToan_27052026_UK, sheet Ve_MB — HAI khối cho cùng một số tiền 952.112.888:
#       khối trên  : 7 dòng theo MÃ ĐẶT CHỖ (2ZB8A1 · SGN-LGW-SGN · 32 chỗ · 22.435.959 · 717.950.688)
#       khối dưới  : 44 dòng theo TỪNG KHÁCH có tên, mỗi dòng mang mã đặt chỗ của mình
#
#   SM000.05260226 (SIN/MAL), sheet VMB — 4 dòng, trong đó:
#       "Phí loby  350.000  ko VAT"      -> KHÔNG phải một cái vé
#       "TVO230.pdf  4.742.047  hoá đơn 82" -> ô "CODE" đang chứa TÊN TỆP
#
# BA ĐIỀU BA TỆP ẤY DẠY
#
# 1. SỐ CHỐT LÀ DÒNG TỪNG KHÁCH, không phải dòng theo mã. Chủ tịch chốt 12/9/2026: "số chi tiết là
#    số chốt, tự cộng lại từ dòng". Nên bảng TourVeKhach giữ số; khối theo mã do máy cộng ra và
#    KHÔNG có cột nào cho người gõ tổng của một mã.
#
# 2. NHƯNG MÃ ĐẶT CHỖ VẪN LÀ MỘT BẢN GHI THẬT, không phải một nhãn. Một mã tồn tại TRƯỚC khi có tên
#    khách: giữ 32 chỗ hôm nay, điền tên dần trong hai tuần, quá hạn xuất vé thì huỷ chỗ. Cột
#    so_cho_giu KHÔNG phải bản sao của "đếm số dòng khách" – nó là một sự kiện khác (đã giữ bao
#    nhiêu), và khoảng cách giữa hai con số chính là việc phải làm.
#
# 3. HOÀN VÉ LÀ MỘT DÒNG ÂM CÓ TÊN NGƯỜI, không phải một dòng bị xoá. Tệp UK ghi khoản hoàn hai chỗ
#    khác nhau: khối theo mã ghi thành dòng riêng (−9.210.459 × 2), khối theo khách trừ thẳng vào
#    cột "Giá vé nội địa" của PHAM DUNG và NGUYEN THI KIM MY. Hai cách ghi cùng ra một tổng, nên
#    không ai phát hiện. Ở đây chỉ có MỘT cách: một dòng loại `hoan_ve`, mang tên khách, mang mã,
#    số tiền âm, và bắt buộc có lý do.


LOAI_VE = {
    "ve": "Vé xuất cho khách",
    "hoan_ve": "Hoàn vé – số tiền ÂM, phải có tên khách và lý do",
    "phi_khac": "Phí đi kèm không phải vé (phí lobby, phí đổi tên, phí hành lý mua thêm)",
}

TRANG_THAI_MA = {
    "giu_cho": "Đang giữ chỗ – chưa xuất vé",
    "da_xuat": "Đã xuất vé",
    "huy": "Đã huỷ chỗ",
}


class TourVeMa(Base):
    """Một MÃ ĐẶT CHỖ của chuyến – khối chỗ giữ ở hãng, chưa chắc đã có tên ai.

    Bảng này KHÔNG giữ tiền. Mọi con số tiền nằm ở TourVeKhach; ở đây chỉ có chỗ giữ và hạn.

    Vì sao vẫn cần bảng riêng dù "số chốt là dòng khách": vì một mã có ba thứ mà dòng khách không
    có chỗ nào để mang – hãng bay, hành trình chung, và HẠN XUẤT VÉ. Hạn xuất vé là thứ làm mất
    tiền thật khi quên: quá hạn thì hãng huỷ chỗ và giá mua lại là giá hôm huỷ.
    """
    __tablename__ = "tour_ve_ma"
    __table_args__ = (Index("ix_tvm_tour", "tour_id"), Index("ix_tvm_ma", "ma_dat_cho"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    # Mã đặt chỗ của hãng (PNR). KHÔNG ép định dạng: mẫu SIN/MAL đang để "TVO230.pdf" ở ô này, và
    # ép sáu ký tự chữ-số sẽ chặn đúng những chuyến mà điều hành cần ghi lại nhất.
    ma_dat_cho: Mapped[str] = mapped_column(String(40))
    hang_bay: Mapped[str | None] = mapped_column(String(60), nullable=True)
    hanh_trinh: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Số chỗ ĐÃ GIỮ ở hãng. Khác với số dòng khách đã điền tên – xem chú thích đầu khối.
    so_cho_giu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    han_xuat_ve: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="giu_cho",
                                            server_default="giu_cho", nullable=False)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TourVeKhach(Base):
    """Một dòng vé của MỘT khách – đây là số chốt của khối vé.

    Năm ô tiền tách riêng đúng như tệp UK: giá vé quốc tế, giá vé nội địa nối chuyến, phí khác, phí
    nâng hạng. Gộp làm một ô thì sang tháng không ai trả lời được "phần tăng là do vé hay do nâng
    hạng", mà đó là câu Kế toán hỏi mỗi kỳ.

    `thanh_tien` do MÁY CHỦ cộng bốn ô ấy – không có cửa nào cho người gõ nó.
    """
    __tablename__ = "tour_ve_khach"
    __table_args__ = (Index("ix_tvk_tour", "tour_id"), Index("ix_tvk_ma", "ve_ma_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    ve_ma_id: Mapped[int | None] = mapped_column(ForeignKey("tour_ve_ma.id"), nullable=True)
    khach_id: Mapped[int | None] = mapped_column(ForeignKey("booking_khach.id"), nullable=True)
    # Tên khách trên vé. Vé máy bay quốc tế ghi tên theo hộ chiếu và KHÁC tên trong danh sách đoàn
    # (dấu, thứ tự họ tên đệm). Nên đây là một ô riêng chứ không lấy từ khach_id.
    ho_ten_ve: Mapped[str | None] = mapped_column(String(200), nullable=True)
    loai: Mapped[str] = mapped_column(String(20), default="ve", server_default="ve", nullable=False)
    gia_ve: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_ve_noi_dia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_khac: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_nang_hang: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    # Số hoá đơn của đại lý vé. Mẫu SIN/MAL ghi "14 - Việt Việt", "82", và "ko VAT" ở cùng một cột –
    # nên đây là ô CHỮ, và "ko VAT" được giữ nguyên chứ không đổi thành rỗng: "không có hoá đơn" là
    # một câu trả lời, "chưa nhập" là một câu khác.
    so_hoa_don: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Bắt buộc với dòng `hoan_ve`. Dịch vụ chặn khi thiếu.
    ly_do: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TourVeThanhToan(Base):
    """Một ĐỢT THANH TOÁN cho đại lý vé / hãng bay.

    ────────────────────────────────────────────────────────────────────────────────────────────
    CHỖ BẢN ĐỀ XUẤT SÁNG 12/9 CỦA ROBOT A VIẾT SAI, VÀ LÀN RÀ SOÁT BÁC ĐÚNG
    ────────────────────────────────────────────────────────────────────────────────────────────

    Bản ấy viết phép kiểm: "Σ giá vé = Σ các đợt thanh toán, lệch là CHẶN".

    Sai. Các đợt thanh toán KHÔNG phải một cách ghi khác của tổng tiền vé – chúng chỉ TRỪ DẦN vào
    khoản nợ. Đặt cọc 30% hôm nay thì hai con số lệch nhau 70%, và đó là tình trạng đúng của gần như
    mọi chuyến ở thời điểm đang làm quyết toán. Chặn ở đó là chặn mọi chuyến chưa trả hết tiền vé.

    Quan hệ đúng là một SỐ DƯ, không phải một đẳng thức:

        còn nợ đại lý vé = Σ tiền vé (kể cả dòng hoàn, vốn âm) − Σ đã thanh toán

    Số dư ấy có thể dương (còn nợ), bằng 0 (xong), hoặc âm (đã trả thừa – cũng là chuyện phải biết,
    vì tiền thừa nằm ở đại lý là tiền của công ty đang nằm ngoài két).
    """
    __tablename__ = "tour_ve_thanh_toan"
    __table_args__ = (Index("ix_tvtt_tour", "tour_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    ve_ma_id: Mapped[int | None] = mapped_column(ForeignKey("tour_ve_ma.id"), nullable=True)
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    hinh_thuc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    so_chung_tu: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-9 (13/9/2026) · CÔNG NỢ TRƯỞNG ĐOÀN
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# QUY ƯỚC DẤU – Chủ tịch chốt 12/9/2026, và bảng này chỉ có MỘT quy ước:
#
#       DƯƠNG  =  CÔNG TY CÒN PHẢI TRẢ TRƯỞNG ĐOÀN
#       ÂM     =  TRƯỞNG ĐOÀN CÒN PHẢI NỘP LẠI CHO CÔNG TY
#
# Phải chốt vì HAI TỆP MẪU DÙNG HAI QUY ƯỚC NGƯỢC NHAU CHO CÙNG MỘT Ý:
#
#   QuyetToan_27052026_UK, sheet CongNo_HDV
#       "Vậy Cty hoàn lại cho TL:  −3.427.560  /  −95,21 (gbp)  —  (TL nộp lại)"
#       Số âm, chú thích "TL nộp lại". ĐÚNG quy ước trên.
#
#   QUYẾT TOÁN TL (tour châu Âu 27/05)
#       "12 · CTY HOÀN TIỀN CHO TL + CTP   −60   CTY TT"
#       Số âm, nhãn "CTY HOÀN TIỀN CHO TL". NGƯỢC quy ước trên.
#
#   Và số học của chính tờ châu Âu chứng minh nhãn mới là cái đúng, còn dấu thì sai:
#       CTP HDV 270 + city tax 120 + Riepilogo 480 = 870 €  (công ty nợ TL)
#       trừ tiền tip nộp công ty 810 €                      (TL nợ công ty)
#       còn lại  +60 €  -> công ty trả TL 60 €, đúng như nhãn viết, ngược dấu tờ ghi.
#
# Nên khi Điều hành chép tờ châu Âu vào hệ thống, dòng cuối phải ĐỔI DẤU. Biểu nhập in quy ước ngay
# cạnh ô số, và bộ soát chặn khi dấu mâu thuẫn với loại khoản – xem services/cong_no_truong_doan.py.
#
# ──────────────────────────────────────────────────────────────────────────────────────────────
# NHIỀU ĐỒNG TIỀN CHẠY SONG SONG, KHÔNG QUY VỀ MỘT
# ──────────────────────────────────────────────────────────────────────────────────────────────
#
# Tờ UK có ba đồng tiền cùng lúc và KHÔNG cộng chúng lại trước khi ra kết quả:
#
#       GBP :  30,79 (TL trả dịch vụ)  −  126 (TL thu của khách)  =  −95,21 GBP  -> TL nộp lại
#       USD :  450 (công tác phí)                                  =  +450 USD    -> công ty trả TL
#       quy về VND, mỗi đồng một tỷ giá riêng ghi ngay trên tờ:
#              −95,21 × 36.000  =  −3.427.560
#              +450   × 26.500  =  +11.925.000
#              cộng lại          =  +8.497.440  -> công ty còn phải trả TL 8.497.440 đ
#
# Người ta trả cho trưởng đoàn bằng từng đồng tiền một, nên số dư phải giữ theo từng đồng tiền.
# Cộng gộp sớm là làm mất chính thông tin cần để đi trả tiền.


LOAI_CONG_NO_TL = {
    # Dấu DƯƠNG – công ty nợ trưởng đoàn
    "tl_chi_ho":       (+1, "Trưởng đoàn ứng tiền túi trả dịch vụ cho đoàn"),
    "cong_tac_phi":    (+1, "Công tác phí của trưởng đoàn"),
    "thuong":          (+1, "Thưởng / phụ cấp khác của trưởng đoàn"),
    # Dấu ÂM – trưởng đoàn nợ công ty
    "cty_tam_ung":     (-1, "Công ty đã tạm ứng trước cho trưởng đoàn"),
    "tip_nop_cong_ty": (-1, "Tiền tip phần của công ty, trưởng đoàn thu và phải nộp về"),
    "tl_thu_ho_khach": (-1, "Trưởng đoàn đang giữ tiền của KHÁCH – không phải tiền công ty"),
    "cty_da_tra":      (-1, "Công ty đã thanh toán khoản này rồi"),
}


class TourTlCongNo(Base):
    """Một dòng trên tờ quyết toán trưởng đoàn.

    Mỗi dòng mang MỘT đồng tiền. Muốn ghi cùng một việc bằng hai đồng tiền thì ghi hai dòng – ép
    một dòng mang hai đồng tiền là chỗ tỷ giá bị nhét vào giữa và không ai lần ra được nữa.

    `so_tien` mang DẤU theo quy ước ở đầu khối. `loai` khai chiều mà khoản ấy đáng lẽ phải có, và bộ
    soát chặn khi hai thứ mâu thuẫn – đó là cái lưới bắt đúng lỗi đổi dấu khi chép từ tờ châu Âu.
    """
    __tablename__ = "tour_tl_cong_no"
    __table_args__ = (Index("ix_ttcn_tour", "tour_id"), Index("ix_ttcn_pc", "phan_cong_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    phan_cong_id: Mapped[int | None] = mapped_column(ForeignKey("guide_assignments.id"), nullable=True)
    # Tên trưởng đoàn ghi thẳng, vì tờ quyết toán có thể tới trước khi phân công được nhập.
    ten_truong_doan: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(300), nullable=True)
    loai: Mapped[str] = mapped_column(String(30))
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # Tỷ giá để quy về VND. RỖNG nghĩa là chưa có tỷ giá, và khi ấy bản quy đổi VND KHÔNG được sinh
    # ra với số 0 – nó phải không có, và nói ra là vì sao.
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Nối sang sổ thu hộ (Đ-7) khi khoản này chính là tiền của khách mà trưởng đoàn đang giữ. Cùng
    # một khoản 126 GBP xuất hiện ở hai sổ theo hai góc nhìn; nối lại để không ai gõ nó hai lần với
    # hai con số khác nhau.
    hdv_chi_id: Mapped[int | None] = mapped_column(ForeignKey("tour_hdv_chi.id"), nullable=True)
    da_thanh_toan: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    ngay_thanh_toan: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-4 (13/9/2026) · NHIỀU BÊN BÁN TRÊN MỘT CHUYẾN  ·  và Đ-6b hoàn tip cho bên bán
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# Đo trên tour PHÁP – THỤY SĨ – Ý – ĐỨC khởi hành 27/05/2026 (tệp AU), đầu bảng ghi "Ghép land",
# "30A+1TL". Ba bên bán cùng ngồi trên một chuyến:
#
#       J TRAVEL      3 người lớn
#       VTOURIST      5 người lớn
#       VIETOURIST   22 người lớn      -> 3 + 5 + 22 = 30, khớp đầu bảng
#
# Mỗi bên có MỘT TỜ QUYẾT TOÁN RIÊNG, cùng đơn giá, khác số lượng. Đã cộng lại và khớp đến từng đồng:
#
#       J TRAVEL   tổng 168.955.150,6  −  đã cọc 30.000.000     =  còn 138.955.150,6
#       VTOURIST   tổng 277.000.584,33 −  đã cọc 177.327.068    =  còn  99.673.516,33
#
# ──────────────────────────────────────────────────────────────────────────────────────────────
# BA ĐIỀU TỆP ẤY DẠY, VÀ CẢ BA ĐỀU NGƯỢC VỚI TRỰC GIÁC
# ──────────────────────────────────────────────────────────────────────────────────────────────
#
# 1. SỐ LƯỢNG CỦA DÒNG KHÔNG PHẢI SỐ KHÁCH CỦA BÊN. Tờ J TRAVEL có 3 khách, nhưng dòng "VISA người
#    lớn 4 pax" ghi số lượng 4, và "Phí điều hành + Dịch thuật" cũng 4. Tờ VTOURIST có 5 khách,
#    dòng VISA ghi 6. Lý do đơn giản: có khách đã sẵn visa, có người mua visa mà không đi.
#
#    Nên hệ thống KHÔNG tự điền số lượng từ số khách. Nó chỉ CẢNH BÁO khi hai con số khác nhau —
#    tự điền là biến một sự thật nghiệp vụ thành một lỗi lặng lẽ.
#
# 2. HAI KIỂU CHIA TIỀN NẰM CẠNH NHAU TRONG CÙNG MỘT TỜ:
#       · "Chi phí chung HDV" 30.979.080,84 chia theo ĐẦU KHÁCH toàn chuyến:
#             × 3/30 = 3.097.908,08   (J TRAVEL)
#             × 5/30 = 5.163.180,14   (VTOURIST)
#       · "Vé máy bay" 22.425.780,84 là đơn giá MỖI KHÁCH, nhân thẳng:
#             × 3    = 67.277.342,52
#    Gộp hai kiểu vào một công thức là sai một trong hai, và sai ở chỗ tổng vẫn cân.
#
# 3. DÒNG ÂM LÀ MỘT DÒNG BÌNH THƯỜNG Ở ĐÂY. "TIP HDV hoàn cho JTR −837.000" là Đ-6b: tiền tip công
#    ty thu của khách đại lý thì phải hoàn về đại lý. Và 837.000 = 27 € × 31.000 — đúng bằng đơn giá
#    tip cả chuyến của tờ châu Âu (3 €/khách/ngày × 9 ngày). Hai tệp khác nhau, cùng một con số.


LOAI_DONG_BEN_BAN = {
    "phan_bo": "Khoản Vietourist tính cho bên bán – LÀM TĂNG nợ của họ",
    "hoan_tip": "Hoàn tiền tip về bên bán – số ÂM, làm GIẢM nợ của họ",
    "giam_tru": "Khoản giảm trừ khác – số ÂM",
    "thanh_toan": "Bên bán đã trả tiền – làm GIẢM nợ của họ",
}

# Cách con số của dòng được hình thành. KHÔNG dùng để máy tự tính – dùng để người đọc lại tờ quyết
# toán biết vì sao dòng này nhân 3 còn dòng kia nhân 3/30.
CACH_CHIA = {
    "moi_khach": "Đơn giá MỖI KHÁCH – nhân thẳng với số lượng của dòng",
    "chia_dau_khach": "Chi phí CHUNG của chuyến – chia theo đầu khách trên tổng khách",
    "khoan_gon": "Khoán gọn cho bên này – không nhân theo khách",
}


class TourBenBan(Base):
    """Một BÊN BÁN cùng ngồi trên chuyến – đại lý ghép land, hoặc chính Vietourist.

    Vietourist cũng là MỘT DÒNG ở đây, không phải phần còn lại sau khi trừ các đại lý. Để nó là
    "phần còn lại" thì lúc số khách lệch, phần thiếu tự chảy vào Vietourist mà không ai thấy.
    """
    __tablename__ = "tour_ben_ban"
    __table_args__ = (Index("ix_tbb_tour", "tour_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    ten_ben: Mapped[str] = mapped_column(String(200))
    # 1 = đây là Vietourist (bên nhà). Dùng để báo cáo tách "doanh thu của mình" và "thu hộ ghép".
    la_vietourist: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    supplier_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mst: Mapped[str | None] = mapped_column(String(20), nullable=True)
    so_khach_nguoi_lon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_khach_tre_em: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_khach_em_be: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TourBenBanDong(Base):
    """Một dòng trên tờ quyết toán của MỘT bên bán.

    `thanh_tien` do MÁY nhân đơn giá × số lượng – không có cửa nào cho người gõ nó, và cũng không có
    ô "tổng của bên". Tổng do máy cộng từ các dòng, đúng nguyên tắc 1 của cả phân hệ.
    """
    __tablename__ = "tour_ben_ban_dong"
    __table_args__ = (Index("ix_tbbd_ben", "ben_ban_id"), Index("ix_tbbd_tour", "tour_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    ben_ban_id: Mapped[int] = mapped_column(ForeignKey("tour_ben_ban.id"))
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(300), nullable=True)
    loai: Mapped[str] = mapped_column(String(20), default="phan_bo",
                                      server_default="phan_bo", nullable=False)
    cach_chia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Số lượng của DÒNG – cố ý tách khỏi số khách của bên. Xem điều 1 ở đầu khối.
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_chung_tu: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-12 (13/9/2026) · ĐỀ NGHỊ CHI PHÍ LÃNH SỰ
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# Đo trên tệp AU, sheet "PHÍ LSQ": mỗi khách MỘT DÒNG, và dòng mang họ tên, giới tính, ngày sinh,
# tên sale, ba ô phí, mã số thuế đơn vị thu.
#
#       18 khách  ·  phí TLS cơ bản 780.000 × 18            = 14.040.000
#                 ·  phí LSQ 2.807.000 × 17 + 1.403.500 × 1 = 49.122.500
#                 ·  tổng thanh toán                        = 63.162.500   (khớp tệp)
#
# MỘT KHÁCH TRẢ ĐÚNG MỘT NỬA. NGUYEN CAT MAI ANH sinh 30.10.2015 trả 1.403.500 = 2.807.000 / 2.
# Nhưng NGUYEN LE NGUYEN sinh 23.09.2013 trả NGUYÊN GIÁ. Tức là mốc tuổi nằm đâu đó giữa 11 và 13,
# và đó là quy định của LÃNH SỰ QUÁN, thay đổi theo từng thị trường và từng thời kỳ.
#
# NÊN HỆ THỐNG KHÔNG CÀI MỐC TUỔI NÀO. Biểu phí sống ở `bang_gia` / `bang_gia_dong` (đã có sẵn, có
# khoảng hiệu lực và có hạng khách) và do NHÂN VIÊN TEAM VISA khai. Đoán một con số rồi áp cho mọi
# thị trường là cách chắc chắn để sai ở thị trường thứ hai mà không ai kiểm.
#
# Chỗ hệ thống ĐƯỢC PHÉP soi là chuyện khác hẳn và rõ ràng hơn: MỘT NGƯỜI XUẤT HIỆN HAI LẦN trong
# cùng một đề nghị. Nộp trùng thì chi trùng, và ở mức 2,8 triệu một suất thì một dòng lặp là một
# khoản tiền thật đi ra khỏi công ty.


class DeNghiLanhSu(Base):
    """Một tờ đề nghị chi phí lãnh sự – gộp nhiều khách, gửi lên duyệt một lần."""
    __tablename__ = "de_nghi_lanh_su"
    __table_args__ = (Index("ix_dnls_tour", "tour_id"), Index("ix_dnls_ngay", "ngay"))

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # RỖNG là hợp lệ: visa lẻ không thuộc chuyến nào. Ép phải có tour là chặn đúng mảng visa lẻ.
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    thi_truong: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    don_vi_thu: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mst_don_vi_thu: Mapped[str | None] = mapped_column(String(30), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap",
                                            server_default="nhap", nullable=False)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeNghiLanhSuDong(Base):
    """Một khách trên tờ đề nghị. Ba ô phí tách riêng đúng như tệp, và tổng do máy cộng."""
    __tablename__ = "de_nghi_lanh_su_dong"
    __table_args__ = (Index("ix_dnlsd_to", "de_nghi_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    de_nghi_id: Mapped[int] = mapped_column(ForeignKey("de_nghi_lanh_su.id"))
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ho_ten: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gioi_tinh: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ngay_sinh: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Cột SALE của tệp thật có cả "JTRAVEL" – tức một bên bán, không phải một nhân viên. Nối sang
    # Đ-4 để khoản phí ấy chảy đúng về tờ công nợ của đại lý thay vì tính vào giá vốn của Vietourist.
    ben_ban_id: Mapped[int | None] = mapped_column(ForeignKey("tour_ben_ban.id"), nullable=True)
    khach_id: Mapped[int | None] = mapped_column(ForeignKey("booking_khach.id"), nullable=True)
    phi_tls_cao_cap: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_tls_co_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phi_lsq: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    mst: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)
